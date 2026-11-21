"""A kept file written whole (meridian._durable): under a filesystem that keeps
only what was synced, a crash during write_whole leaves the old file whole or
the new one, and a crash after it returns leaves the new one; and two writers
of one file in a takeover's lapse each put a whole file in place, never a torn
one.

The filesystem is a model standing in for ``os``: what is written is held in
memory until synced; a directory's entries (made, renamed, removed) reach the
disk in the order made, any prefix of them by a crash, and all of them up to
a sync of that directory. A crash is taken after every call write_whole
makes, and every disk it could leave is read."""

from __future__ import annotations

import errno
import json
import os
import stat
import threading
import zlib
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any

import pytest

from meridian import _durable


class _Disk:
    """A model filesystem: a tree of directories, files by inode, and what a
    crash keeps."""

    def __init__(self) -> None:
        self.dirs: dict[PurePosixPath, dict[str, Any]] = {PurePosixPath("/"): {}}
        self.data: dict[int, bytes] = {}
        # What is on disk: the directories as of the last sync of each, and
        # each file's bytes as of its last fsync.
        self.kept_dirs: dict[PurePosixPath, dict[str, Any]] = {PurePosixPath("/"): {}}
        self.kept_data: dict[int, bytes] = {}
        # Directory changes made and not yet on disk, in order.
        self.pending: list[tuple[str, tuple[Any, ...]]] = []
        self.handles: dict[int, tuple[str, Any]] = {}
        self.inodes = 0
        self.after: Callable[[], None] = lambda: None

    # -- setup ---------------------------------------------------------------

    def keep_file(self, path: str, body: bytes) -> None:
        """A file already there and synced, as an earlier write left it."""
        at = PurePosixPath(path)
        for directory in reversed(at.parents):
            if directory not in self.dirs:
                self.dirs[directory] = {}
                self.kept_dirs[directory] = {}
                self.dirs[directory.parent][directory.name] = ("dir", directory)
                self.kept_dirs[directory.parent][directory.name] = ("dir", directory)
        self.inodes += 1
        self.dirs[at.parent][at.name] = ("file", self.inodes)
        self.kept_dirs[at.parent][at.name] = ("file", self.inodes)
        self.data[self.inodes] = body
        self.kept_data[self.inodes] = body

    # -- what a crash leaves -------------------------------------------------

    def crashes(self, path: str) -> set[bytes | None]:
        """What reading ``path`` gives on each disk a crash now could leave:
        any prefix of the pending directory changes on disk, and of each
        file only what was synced."""
        found: set[bytes | None] = set()
        for upto in range(len(self.pending) + 1):
            dirs = {d: dict(entries) for d, entries in self.kept_dirs.items()}
            for change, args in self.pending[:upto]:
                _apply(dirs, change, args)
            at = PurePosixPath(path)
            entry = dirs.get(at.parent, {}).get(at.name)
            found.add(None if entry is None else self.kept_data.get(entry[1], b""))
        return found

    # -- os ------------------------------------------------------------------

    def _change(self, change: str, *args: Any) -> None:
        _apply(self.dirs, change, args)
        self.pending.append((change, args))

    def open(self, path: Any, flags: int, mode: int = 0o777) -> int:
        at = PurePosixPath(os.fspath(path))
        if at.parent not in self.dirs:
            raise FileNotFoundError(errno.ENOENT, "no such directory", str(at))
        if at in self.dirs:
            handle = len(self.handles) + 100
            self.handles[handle] = ("dir", at)
            return handle
        entry = self.dirs[at.parent].get(at.name)
        if entry is not None and flags & os.O_EXCL:
            raise FileExistsError(errno.EEXIST, "exists", str(at))
        if entry is None:
            if not flags & os.O_CREAT:
                raise FileNotFoundError(errno.ENOENT, "no such file", str(at))
            self.inodes += 1
            entry = ("file", self.inodes)
            self.data[self.inodes] = b""
            self._change("link", at.parent, at.name, entry)
        if flags & os.O_TRUNC:
            self.data[entry[1]] = b""
        handle = len(self.handles) + 100
        self.handles[handle] = ("file", entry[1])
        self.after()
        return handle

    def write(self, handle: int, data: Any) -> int:
        kind, inode = self.handles[handle]
        # A short write, as a real one may be, so the caller must loop.
        part = bytes(data[: max(1, len(data) // 2)])
        self.data[inode] += part
        self.after()
        return len(part)

    def fsync(self, handle: int) -> None:
        kind, held = self.handles[handle]
        if kind == "file":
            self.kept_data[held] = self.data[held]
        else:
            # The directory's changes, and every one before them, are on disk.
            last = max(
                (n for n, (_, args) in enumerate(self.pending) if held in _dirs_of(args)),
                default=-1,
            )
            for change, args in self.pending[: last + 1]:
                _apply(self.kept_dirs, change, args)
            del self.pending[: last + 1]
        self.after()

    def close(self, handle: int) -> None:
        self.handles[handle] = ("closed", None)

    def replace(self, source: Any, target: Any) -> None:
        a, b = PurePosixPath(os.fspath(source)), PurePosixPath(os.fspath(target))
        entry = self.dirs[a.parent][a.name]
        self._change("rename", a.parent, a.name, b.parent, b.name, entry)
        self.after()

    def unlink(self, path: Any) -> None:
        at = PurePosixPath(os.fspath(path))
        if at.name not in self.dirs.get(at.parent, {}):
            raise FileNotFoundError(errno.ENOENT, "no such file", str(at))
        self._change("unlink", at.parent, at.name)
        self.after()

    def mkdir(self, path: Any, mode: int = 0o777) -> None:
        at = PurePosixPath(os.fspath(path))
        if at in self.dirs:
            raise FileExistsError(errno.EEXIST, "exists", str(at))
        if at.parent not in self.dirs:
            raise FileNotFoundError(errno.ENOENT, "no such directory", str(at))
        self._change("mkdir", at.parent, at.name)
        self.after()

    def as_os(self) -> SimpleNamespace:
        return SimpleNamespace(
            open=self.open,
            write=self.write,
            fsync=self.fsync,
            close=self.close,
            replace=self.replace,
            unlink=self.unlink,
            mkdir=self.mkdir,
            O_WRONLY=os.O_WRONLY,
            O_CREAT=os.O_CREAT,
            O_EXCL=os.O_EXCL,
            O_TRUNC=os.O_TRUNC,
            O_RDONLY=os.O_RDONLY,
            fspath=os.fspath,
        )


def _dirs_of(args: tuple[Any, ...]) -> set[PurePosixPath]:
    return {a for a in args if isinstance(a, PurePosixPath)}


def _apply(
    dirs: dict[PurePosixPath, dict[str, Any]], change: str, args: tuple[Any, ...]
) -> None:
    if change == "link":
        parent, name, entry = args
        dirs[parent][name] = entry
    elif change == "rename":
        a_dir, a_name, b_dir, b_name, entry = args
        dirs[a_dir].pop(a_name, None)
        dirs[b_dir][b_name] = entry
    elif change == "unlink":
        parent, name = args
        dirs[parent].pop(name, None)
    elif change == "mkdir":
        parent, name = args
        dirs[parent][name] = ("dir", parent / name)
        dirs.setdefault(parent / name, {})


OLD = b'{"sequence": 7}'
NEW = b'{"sequence": 8, "and": "' + b"x" * 300 + b'"}'


def _crash_everywhere(
    write: Callable[[str, bytes], None], disk: _Disk, path: str
) -> tuple[set[bytes | None], set[bytes | None]]:
    """Every content a crash during ``write`` could leave at ``path``, and
    every one a crash just after it returned could."""
    during: set[bytes | None] = set()
    disk.after = lambda: during.update(disk.crashes(path))
    write(path, NEW)
    disk.after = lambda: None
    return during, disk.crashes(path)


def _with(disk: _Disk, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_durable, "os", disk.as_os())


def test_a_crash_during_the_write_leaves_the_old_file_or_the_new_and_after_it_the_new(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disk = _Disk()
    disk.keep_file("/storage/kept/state.json", OLD)
    _with(disk, monkeypatch)

    during, after = _crash_everywhere(_durable.write_whole, disk, "/storage/kept/state.json")

    assert during <= {OLD, NEW}, during
    assert OLD in during and NEW in during
    assert after == {NEW}, after


def test_a_first_write_into_a_directory_it_makes_is_there_after_it_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disk = _Disk()
    disk.keep_file("/storage/other", b"")
    _with(disk, monkeypatch)

    during, after = _crash_everywhere(_durable.write_whole, disk, "/storage/a/b/state.json")

    assert during <= {None, NEW}, during
    assert after == {NEW}, after


def test_the_model_finds_a_rename_without_its_syncs(monkeypatch: pytest.MonkeyPatch) -> None:
    """The model is not vacuous: the kept files the SDK wrote before
    write_whole (data renamed into place, nothing synced) lose the file."""
    disk = _Disk()
    disk.keep_file("/storage/kept/state.json", OLD)
    model = disk.as_os()

    def unsynced(path: str, data: bytes) -> None:
        temporary = path + ".tmp"
        handle = model.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        left = memoryview(data)
        while left:
            left = left[model.write(handle, left) :]
        model.close(handle)
        model.replace(temporary, path)

    during, after = _crash_everywhere(unsynced, disk, "/storage/kept/state.json")

    assert b"" in during | after, (during, after)
    assert OLD in after, (
        "the rename was never synced, so the old file may be all a crash leaves"
    )


def test_a_failed_write_leaves_the_old_file_and_no_part(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "state.json"
    target.write_bytes(OLD)

    class Refused(Exception):
        pass

    class Refusing:
        """The real os, but for an fsync that fails, as a full disk's does."""

        def __getattr__(self, name: str) -> Any:
            return getattr(os, name)

        @staticmethod
        def fsync(handle: int) -> None:
            raise Refused

    monkeypatch.setattr(_durable, "os", Refusing())
    with pytest.raises(Refused):
        _durable.write_whole(target, NEW)

    assert target.read_bytes() == OLD
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]


def test_a_kept_file_is_readable_and_writable_by_its_owner_only(tmp_path: Path) -> None:
    """A kept file holds a plugin's state (the trader's originated orders, a
    listing map, a pricing sequence): write_whole makes it 0o600 whatever the
    umask allows, and a file it replaces that was wider ends 0o600 too."""
    made = tmp_path / "kept" / "state.json"
    _durable.write_whole(made, NEW)
    assert stat.S_IMODE(os.lstat(made).st_mode) == 0o600

    wider = tmp_path / "originated.json"
    wider.write_bytes(OLD)
    os.chmod(wider, 0o644)
    old_umask = os.umask(0)
    try:
        _durable.write_whole(wider, NEW)
    finally:
        os.umask(old_umask)
    assert stat.S_IMODE(os.lstat(wider).st_mode) == 0o600
    assert wider.read_bytes() == NEW


# -- two writers in a takeover's lapse ---------------------------------------


def _body(writer: str, n: int) -> bytes:
    """A large body, as a kept file of a busy plugin is, that says whose it is
    and checks itself whole."""
    filler = (writer * 40_000)[:200_000]
    inner = json.dumps({"writer": writer, "n": n, "filler": filler}, sort_keys=True)
    return json.dumps({"crc": zlib.crc32(inner.encode()), "inner": inner}).encode()


def _whole(read: bytes) -> str:
    """The writer of a body read whole; AssertionError otherwise."""
    outer = json.loads(read)
    assert zlib.crc32(outer["inner"].encode()) == outer["crc"], "torn"
    return str(json.loads(outer["inner"])["writer"])


def test_two_writers_in_a_lapse_each_put_a_whole_file_in_place(tmp_path: Path) -> None:
    """A deposed holder and the new one write the same kept file at once, on
    the one shared storage: every read finds one writer's whole file, both
    writers' calls succeed, and no temporary file is left."""
    target = tmp_path / "kept" / "originated.json"
    rounds = 60
    go = threading.Barrier(3)
    done = threading.Event()
    failures: list[BaseException] = []
    seen: set[str] = set()

    def writer(name: str) -> None:
        try:
            go.wait()
            for n in range(rounds):
                _durable.write_whole(target, _body(name, n))
        except BaseException as failed:
            failures.append(failed)

    def reader() -> None:
        go.wait()
        while not done.is_set():
            try:
                read = target.read_bytes()
            except FileNotFoundError:
                continue
            try:
                seen.add(_whole(read))
            except BaseException as failed:
                failures.append(failed)
                return

    threads = [threading.Thread(target=writer, args=(w,)) for w in ("deposed", "new")]
    watching = threading.Thread(target=reader)
    for thread in [*threads, watching]:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    done.set()
    watching.join(timeout=30)

    assert not failures, failures
    assert _whole(target.read_bytes()) in {"deposed", "new"}
    assert seen <= {"deposed", "new"}
    assert sorted(p.name for p in target.parent.iterdir()) == ["originated.json"]
