"""`meridian-storage` (step 3d, checkpoint 5, item 30; PO 86 and 88): an
instance's own storage claim copied into its shared storage's `shard-0/`,
once, before its first launch as several pods, by a pod running the plugin's
own image as the plugin's own user; and the instance's pods' init container
waiting for that copy's marker.

The behaviour is core's launcher's, `crates/runtime/src/launcher/copy.rs`
(c30d), ported: one test here for each of its tests, under the same name,
then the command itself end to end on real folders -- a copy interrupted, a
`shard-0/` with no marker, a second run, modes kept -- run as the plugin's
user (65532) where the tests run as root, as the copy pod runs."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from meridian import storage
from meridian.storage import _Copied, _copied, _copy, _marker, _Refused, _wait

PLUGIN_USER = 65532


def tree(root: Path, files: dict[str, str]) -> None:
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)


def read(root: Path, path: str) -> str:
    return (root / path).read_text()


def mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


@pytest.fixture
def two(tmp_path: Path) -> tuple[Path, Path]:
    source, to = tmp_path / "from", tmp_path / "to"
    source.mkdir()
    to.mkdir()
    return source, to


# -- copy.rs's tests, one for one ---------------------------------------------


def test_an_own_claim_is_copied_into_shard_0_once_and_marked_last(
    two: tuple[Path, Path],
) -> None:
    """Item 30: the instance's own records land under shard-0/ as they were,
    the volume's lost+found left; the marker is written last, and a copy
    made again finds it and writes nothing."""
    source, to = two
    tree(
        source,
        {
            "responses/2026-11-15/quotes/q.jsonl": "a\nb\n",
            ".meridian/archive/index.json": "{}",
            "lost+found/x": "not the plugin's",
        },
    )
    assert not _copied(to, "rel-storage-feed-1")
    assert _copy(source, to, "rel-storage-feed-1") == _Copied(files=2, bytes=6)
    assert read(to, "shard-0/responses/2026-11-15/quotes/q.jsonl") == "a\nb\n"
    assert read(to, "shard-0/.meridian/archive/index.json") == "{}"
    assert not (to / "shard-0/lost+found").exists()
    assert _copied(to, "rel-storage-feed-1")
    assert _marker(to, "rel-storage-feed-1") == to / ".meridian/copied-from-rel-storage-feed-1"
    # Its own claim untouched.
    assert read(source, "responses/2026-11-15/quotes/q.jsonl") == "a\nb\n"
    # Made again -- a launch after -- it writes nothing over what the shards
    # wrote since.
    tree(to, {"shard-0/responses/2026-11-15/quotes/q.jsonl": "a\nb\nc\n"})
    assert _copy(source, to, "rel-storage-feed-1") == _Copied(before=True)
    assert read(to, "shard-0/responses/2026-11-15/quotes/q.jsonl") == "a\nb\nc\n"


def test_a_copy_failed_part_way_leaves_no_marker_and_is_made_again_whole(
    two: tuple[Path, Path],
) -> None:
    """A copy that failed part way left no marker, so it is made again whole,
    and the pods kept waiting meanwhile."""
    source, to = two
    tree(source, {"a/one": "1", "b/two": "2"})
    # Part way: one file there, half written, one not the copy's, and no
    # marker; made in shard-0.copying/, never in shard-0/ (review c5c L3).
    tree(to, {"shard-0.copying/a/one": "", "shard-0.copying/z/left": "x"})
    assert not _copied(to, "c")
    _copy(source, to, "c")
    assert read(to, "shard-0/a/one") == "1"
    assert read(to, "shard-0/b/two") == "2"
    assert not (to / "shard-0/z").exists(), "made again whole"
    assert not (to / "shard-0.copying").exists()
    assert _copied(to, "c")
    # The marker of another claim is not this one's.
    assert not _copied(to, "d")


def test_a_shard_0_with_no_marker_is_never_copied_over(tmp_path: Path) -> None:
    """Review c5c L3: a shard-0/ with no marker -- the marker removed by hand
    -- holds what the shards wrote since, so nothing is copied over it:
    refused, every file as it was. A copy stopped after its rename, marked
    whole but not yet marked, is finished, not refused."""
    source, to = tmp_path / "from", tmp_path / "to"
    tree(source, {"responses/q.jsonl": "a\n"})
    tree(to, {"shard-0/responses/q.jsonl": "a\nb\nc\n"})
    with pytest.raises(_Refused) as refused:
        _copy(source, to, "c")
    assert "no mark that c was copied" in str(refused.value), refused.value
    assert read(to, "shard-0/responses/q.jsonl") == "a\nb\nc\n"
    assert not _copied(to, "c")
    # Stopped after the rename: the `.writing` mark there, shard-0/ whole,
    # no marker.
    source, to = tmp_path / "from2", tmp_path / "to2"
    tree(source, {"responses/q.jsonl": "a\n"})
    tree(
        to,
        {
            "shard-0/responses/q.jsonl": "a\n",
            ".meridian/.copied-from-c.writing": "1 files, 2 bytes\n",
        },
    )
    _copy(source, to, "c")
    assert _copied(to, "c")
    assert read(to, "shard-0/responses/q.jsonl") == "a\n"


def test_copied_folders_and_files_keep_their_modes(two: tuple[Path, Path]) -> None:
    """Review c5c H1: every folder keeps its mode, setgid bit and all, and
    every file its own, so what was the plugin's to write on stays so, and
    its private files stay private; `shard-0/` is the own claim's root as it
    was."""
    source, to = two
    tree(source, {".meridian/archive/index.json": "{}", "responses/d/x.jsonl": "a\n"})
    os.chmod(source / ".meridian/archive/index.json", 0o600)
    os.chmod(source / ".meridian/archive", 0o700)
    os.chmod(source / "responses", 0o2770)
    os.chmod(source, 0o2775)
    _copy(source, to, "c")
    into = to / "shard-0"
    assert mode(into) == 0o2775, "shard-0/"
    assert mode(into / ".meridian/archive") == 0o700
    assert mode(into / "responses") == 0o2770
    assert mode(into / ".meridian/archive/index.json") == 0o600
    assert (
        mode(into / "responses/d/x.jsonl") & 0o777
        == mode(source / "responses/d/x.jsonl") & 0o777
    )


def test_a_wait_for_a_copy_that_never_comes_ends_saying_so(tmp_path: Path) -> None:
    """Review c5c M1: a pod's wait for a copy that never comes ends, saying
    which claim and that the instance's next launch makes the copy again, so
    the pod shows the failure; once the marker is there it passes at once."""
    with pytest.raises(_Refused) as said:
        _wait(tmp_path, "own-claim", 0.01, 0.1)
    assert "own-claim" in str(said.value) and "launch" in str(said.value), said.value
    (tmp_path / ".meridian").mkdir()
    _marker(tmp_path, "own-claim").write_text("")
    assert _wait(tmp_path, "own-claim", 0.01, 0.1) is None


# -- beyond copy.rs: what the plugin's own user can and cannot do -----------


def test_owners_are_kept_as_far_as_the_user_can(
    two: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """PO 86: the copy runs as the plugin's own user, never root, so an owner
    it cannot give is left as its own, and the copy goes on; one it can is
    kept. Where the tests run as root, owners are given as they were."""
    source, to = two
    tree(source, {"responses/q.jsonl": "a\n", "keys/k": "k"})
    os.chmod(source / "keys/k", 0o2640)
    if os.geteuid() == 0:
        for path in (source / "responses", source / "responses/q.jsonl"):
            os.lchown(path, 1234, 5678)
        _copy(source, to, "c")
        for path in ("responses", "responses/q.jsonl"):
            held = os.lstat(to / "shard-0" / path)
            assert (held.st_uid, held.st_gid) == (1234, 5678), path
        shutil.rmtree(to)
        to.mkdir()

    def refused(*_: object, **__: object) -> None:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "chown", refused)
    monkeypatch.setattr(os, "lchown", refused)
    monkeypatch.setattr(os, "fchown", refused)
    assert _copy(source, to, "c") == _Copied(files=2, bytes=3)
    # The mode given after the owner, so a setgid bit a change of owner
    # clears is there.
    assert mode(to / "shard-0/keys/k") == 0o2640
    assert _copied(to, "c")


def test_symlinks_are_copied_as_links(two: tuple[Path, Path]) -> None:
    source, to = two
    tree(source, {"responses/q.jsonl": "a\n"})
    os.symlink("responses/q.jsonl", source / "latest")
    assert _copy(source, to, "c") == _Copied(files=1, bytes=2)
    assert os.readlink(to / "shard-0/latest") == "responses/q.jsonl"


def test_the_wait_says_so_once_a_minute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    now = [0.0]
    monkeypatch.setattr(storage.time, "monotonic", lambda: now[0])

    def sleep(seconds: float) -> None:
        now[0] += seconds
        if now[0] >= 150:
            (tmp_path / ".meridian").mkdir(exist_ok=True)
            _marker(tmp_path, "c").write_text("")

    monkeypatch.setattr(storage.time, "sleep", sleep)
    _wait(tmp_path, "c", 2.0, 900.0)
    said = [line for line in capsys.readouterr().err.splitlines() if line]
    assert len(said) == 2, said
    assert all(
        "the instance's own storage is still being copied into its shared storage" in line
        and "claim=c" in line
        for line in said
    ), said


# -- the command, end to end on real folders --------------------------------


class Folders:
    """The copy pod's two mounts and an instance pod's storage, under a
    folder of their own the plugin's user can reach."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.source = base / "from"
        self.to = base / "to"
        self.source.mkdir()
        self.to.mkdir()

    def owned(self) -> None:
        """Every file the plugin's: as the plugin wrote its own claim, and as
        the shared claim is given to the plugin's group."""
        if os.geteuid() != 0:
            return
        for top in (self.source, self.to):
            for path in [top, *top.rglob("*")]:
                os.lchown(path, PLUGIN_USER, PLUGIN_USER)

    def run(
        self, *args: str, fail_after: int | None = None, fail_marker: bool = False
    ) -> subprocess.CompletedProcess[str]:
        """`meridian-storage <args>`, as the plugin's user where the tests run
        as root, with the pod's mounts here; `fail_after` files copied, or at
        the marker's rename, it fails as a pod stopped there would."""
        code = "\n".join(
            [
                "import os, sys",
                "import meridian.storage as s",
                f"s._FROM, s._TO = {str(self.source)!r}, {str(self.to)!r}",
                f"s._STORAGE = {str(self.to)!r}",
                "s._WAIT_EVERY, s._WAIT_LIMIT = 0.01, 0.3",
                f"fail_after, fail_marker = {fail_after!r}, {fail_marker!r}",
                "if fail_after is not None:",
                "    copied, done = s._copy_file, [0]",
                "    def stopping(*args):",
                "        if done[0] == fail_after:",
                "            raise OSError(5, 'stopped part way')",
                "        done[0] += 1",
                "        return copied(*args)",
                "    s._copy_file = stopping",
                "if fail_marker:",
                "    renamed = os.rename",
                "    def stopping_at_marker(a, b):",
                "        if str(b).endswith('/.meridian/copied-from-c'):",
                "            raise OSError(5, 'stopped after the rename')",
                "        return renamed(a, b)",
                "    os.rename = stopping_at_marker",
                f"sys.exit(s.main({list(args)!r}))",
            ]
        )
        return subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=60,
            user=PLUGIN_USER if os.geteuid() == 0 else None,
            cwd=self.base,
        )


@pytest.fixture
def folders() -> Iterator[Folders]:
    # Not under pytest's own temporary folder, which only its user can enter.
    base = Path(tempfile.mkdtemp(prefix="meridian-storage-"))
    os.chmod(base, 0o755)
    try:
        yield Folders(base)
    finally:
        for path in [base, *base.rglob("*")]:
            if path.is_dir() and not path.is_symlink():
                os.chmod(path, 0o700)
        shutil.rmtree(base)


def fingerprint(root: Path) -> dict[str, tuple[int, str]]:
    return {
        str(path.relative_to(root)): (
            mode(path),
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "",
        )
        for path in sorted(root.rglob("*"))
    }


def test_the_command_end_to_end_on_real_folders(folders: Folders) -> None:
    """An interrupted copy is made again whole; a copy stopped after its
    rename is finished; a second run writes nothing; the instance's pods
    wait until the marker is there; modes are kept, read-only folders
    among them; its own claim is untouched -- all as the plugin's user."""
    tree(
        folders.source,
        {
            "responses/2026-11-15/quotes/q.jsonl": "a\nb\n",
            "responses/2026-11-16/quotes/q.jsonl": "c\n",
            ".meridian/archive/index.json": "{}",
            "lost+found/x": "the volume's",
        },
    )
    # A folder only readable, a private file: the copy still writes into
    # the one and keeps the other private.
    os.chmod(folders.source / "responses/2026-11-15/quotes", 0o500)
    os.chmod(folders.source / ".meridian/archive/index.json", 0o600)
    os.chmod(folders.source / "responses", 0o2770)
    os.chmod(folders.source, 0o2775)
    folders.owned()
    before = fingerprint(folders.source)

    # The instance's pods wait, and with no copy their wait ends, saying so.
    waited = folders.run("copied", "c")
    assert waited.returncode == 1, waited
    assert "ERROR" in waited.stderr and "c was not copied" in waited.stderr, waited.stderr

    # Interrupted after one file: no marker, nothing in shard-0/.
    stopped = folders.run("copy", "c", fail_after=1)
    assert stopped.returncode == 1, stopped
    assert "stopped part way" in stopped.stderr, stopped.stderr
    assert (folders.to / "shard-0.copying").exists()
    assert not (folders.to / "shard-0").exists()
    assert not _copied(folders.to, "c")
    # Interrupted again, further in, with a read-only folder already copied
    # whole: the partial copy is still removed, as the plugin's user.
    stopped = folders.run("copy", "c", fail_after=2)
    assert stopped.returncode == 1, stopped
    assert mode(folders.to / "shard-0.copying/responses/2026-11-15/quotes") == 0o500

    # Made again whole.
    done = folders.run("copy", "c")
    assert done.returncode == 0, done
    assert "INFO" in done.stderr and "copied into the shared storage's shard-0/" in done.stderr
    assert "claim=c" in done.stderr and "files=3" in done.stderr, done.stderr
    assert not (folders.to / "shard-0.copying").exists()
    assert fingerprint(folders.to / "shard-0") == {
        name: held for name, held in before.items() if not name.startswith("lost+found")
    }
    assert mode(folders.to / "shard-0") == 0o2775
    assert _copied(folders.to, "c")
    assert fingerprint(folders.source) == before, "its own claim untouched"

    waited = folders.run("copied", "c")
    assert waited.returncode == 0, waited
    assert "its own storage is in its shared storage" in waited.stderr, waited.stderr

    # A second run -- a launch after -- writes nothing over what the shards
    # wrote since.
    os.chmod(folders.to / "shard-0/responses/2026-11-15/quotes", 0o700)
    tree(folders.to, {"shard-0/responses/2026-11-15/quotes/q.jsonl": "a\nb\nwritten since\n"})
    again = folders.run("copy", "c")
    assert again.returncode == 0, again
    assert "copied=before" in again.stderr, again.stderr
    assert (
        read(folders.to, "shard-0/responses/2026-11-15/quotes/q.jsonl")
        == "a\nb\nwritten since\n"
    )


def test_the_command_finishes_a_copy_stopped_after_its_rename(folders: Folders) -> None:
    tree(folders.source, {"responses/q.jsonl": "a\n"})
    folders.owned()
    stopped = folders.run("copy", "c", fail_marker=True)
    assert stopped.returncode == 1, stopped
    assert (folders.to / "shard-0/responses/q.jsonl").exists()
    assert (folders.to / ".meridian/.copied-from-c.writing").exists()
    assert not _copied(folders.to, "c")
    assert folders.run("copied", "c").returncode == 1
    finished = folders.run("copy", "c")
    assert finished.returncode == 0, finished
    assert _copied(folders.to, "c")
    assert folders.run("copied", "c").returncode == 0


def test_the_command_refuses_a_shard_0_with_no_marker(folders: Folders) -> None:
    tree(folders.source, {"responses/q.jsonl": "a\n"})
    tree(folders.to, {"shard-0/responses/q.jsonl": "a\nb\nc\n"})
    folders.owned()
    held = fingerprint(folders.to)
    refused = folders.run("copy", "c")
    assert refused.returncode == 1, refused
    assert "ERROR" in refused.stderr and "no mark that c was copied" in refused.stderr
    assert fingerprint(folders.to) == held, "every file as it was"


@pytest.mark.parametrize(
    ("args", "said"),
    [
        ([], "usage: meridian-storage"),
        (["copy"], "copy names the claim it copies"),
        (["copied"], "copied names the claim it waits on"),
        (["move", "c"], "usage: meridian-storage"),
    ],
)
def test_the_command_says_what_it_needs(
    args: list[str], said: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert storage.main(args) == 1
    assert said in capsys.readouterr().err


def test_the_command_is_a_console_script() -> None:
    from importlib.metadata import entry_points

    (script,) = [
        s for s in entry_points(group="console_scripts") if s.name == "meridian-storage"
    ]
    assert script.value == "meridian.storage:main"


# -- review of #57: a claim is a name, and only files, folders and links ----


@pytest.mark.parametrize("claim", ["../c", "a/b", "/c", "..", "c..d", "", "c\0d"])
def test_a_claim_that_is_not_a_name_is_refused_before_anything_is_written(
    two: tuple[Path, Path],
    claim: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A claim names the marker, `.meridian/copied-from-<claim>`: one with a
    path's separator or `..` would put it elsewhere, so it is refused, by
    the copy and the wait alike, with nothing written."""
    source, to = two
    tree(source, {"responses/q.jsonl": "a\n"})
    with pytest.raises(_Refused) as refused:
        _copy(source, to, claim)
    assert "is not a claim's name" in str(refused.value), refused.value
    with pytest.raises(_Refused):
        _wait(to, claim, 0.01, 0.1)
    assert list(to.iterdir()) == []
    monkeypatch.setattr(storage, "_FROM", str(source))
    monkeypatch.setattr(storage, "_TO", str(to))
    monkeypatch.setattr(storage, "_STORAGE", str(to))
    monkeypatch.setattr(storage, "_WAIT_LIMIT", 0.1)
    for command in ("copy", "copied"):
        assert storage.main([command, claim]) == 1
        assert "ERROR meridian-storage:" in capsys.readouterr().err
    assert list(to.iterdir()) == []


def special_files(source: Path) -> list[str]:
    """A FIFO, a socket and, where the tests run as root, a device in
    `source`, by their names."""
    import socket

    made = ["fifo"]
    os.mkfifo(source / "fifo")
    held = socket.socket(socket.AF_UNIX)
    held.bind(str(source / "sock"))
    held.close()
    made.append("sock")
    if os.geteuid() == 0:
        os.mknod(source / "null", 0o600 | stat.S_IFCHR, os.makedev(1, 3))
        made.append("null")
    return made


def test_a_fifo_socket_or_device_is_refused_and_never_opened(tmp_path: Path) -> None:
    """Only files, folders and links are the plugin's records. Anything
    else is refused, saying what it is, and never opened: a FIFO opened
    would hold the copy pod until no one writes it, and a device would be
    read as if it held records. The copy is left unmarked, the instance's
    pods still waiting."""
    import threading

    source = tmp_path / "from"
    tree(source, {"responses/q.jsonl": "a\n"})
    for name in special_files(source / "responses"):
        to = tmp_path / f"to-{name}"
        to.mkdir()
        held = source / "responses" / f"held-{name}"
        held.mkdir()
        os.rename(source / "responses" / name, held / name)
        ended: list[BaseException | None] = []

        def copying(to: Path = to, ended: list[BaseException | None] = ended) -> None:
            try:
                _copy(source, to, "c")
                ended.append(None)
            except BaseException as stopped:  # handed to the test
                ended.append(stopped)

        thread = threading.Thread(target=copying, daemon=True)
        thread.start()
        thread.join(10)
        assert ended, f"the copy opened {name} and is held there"
        failed = ended[0]
        assert isinstance(failed, _Refused), (name, failed)
        assert f"{held / name} is not a file, a folder or a link" in str(failed), failed
        assert not _copied(to, "c")
        assert not (to / "shard-0").exists()
        assert not (to / "shard-0.copying" / "responses" / f"held-{name}" / name).exists()
        shutil.rmtree(held)


def test_the_command_refuses_a_fifo_as_the_plugins_user(folders: Folders) -> None:
    tree(folders.source, {"responses/q.jsonl": "a\n"})
    os.mkfifo(folders.source / "responses/pipe")
    folders.owned()
    refused = folders.run("copy", "c")
    assert refused.returncode == 1, refused
    assert "ERROR" in refused.stderr and "is not a file, a folder or a link" in refused.stderr
    assert not _copied(folders.to, "c")
