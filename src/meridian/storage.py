"""`meridian-storage`: an instance's own storage claim copied into its shared
storage's `shard-0/`, once, before its first launch as several pods; and the
wait its pods make for that copy (step 3d, checkpoint 5, item 30; PO 86 and
88).

The launcher's copy pod runs the plugin's own image, as the plugin's own
user -- no pinned uid, no added capabilities, so it runs under restricted Pod
Security and OpenShift -- with the instance's own claim mounted read only at
`/var/lib/meridian/copy/from` and its shared storage at
`/var/lib/meridian/copy/to`:

    meridian-storage copy <claim>

copies everything under the one into the other's `shard-0/` and, once the
copy is whole and on disk, writes a marker naming the claim it copied,
`.meridian/copied-from-<claim>` at the shared storage's root. The instance's
pods wait for that marker in an init container, the shared storage mounted
read only at `/var/lib/meridian/storage`, before their plugin starts, so no
plugin reads or writes a partial copy:

    meridian-storage copied <claim>

The copy is made again whole by a pod that failed part way, and not at all
once the marker is there. The instance's own claim is never written: it is
mounted read only, and kept. A claim is a name: one empty, or holding `/`
or `..`, is refused; and only files, folders and links are copied -- a FIFO,
a socket or a device is refused, never opened.

Each exits 0 once done and 1, saying why, otherwise; core's launcher reads the
pod's phase and the init container's exit, nothing else. What each says goes
to standard error, a line at a time, as core's launcher said it, each
`<level> meridian-storage: <message>` and its fields:

    INFO  copied into the shared storage's shard-0/
          claim=<claim> copied=now files=<n> bytes=<n>, or copied=before
    INFO  the instance's own storage is still being copied into its shared
          storage claim=<claim> waited_seconds=<n>
    INFO  its own storage is in its shared storage claim=<claim>
    ERROR <why>

The wait looks every 2 seconds, says so once a minute, and past 15 minutes
ends, refused, so the pod shows that its copy has not come; the kubelet
starts it again.

The behaviour is core's launcher's (`crates/runtime/src/launcher/copy.rs`),
which ran it as root before; this is its port, held to those tests
(tests/test_step_3d_storage_copy.py). Run as the plugin's own user, the copy
keeps every file's and folder's mode, and its owner as far as that user can
give it: one it cannot is left the user's own."""

from __future__ import annotations

import contextlib
import errno
import os
import shutil
import stat
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# Where the copy pod mounts the instance's own claim, read only.
_FROM = "/var/lib/meridian/copy/from"
# Where the copy pod mounts the instance's shared storage.
_TO = "/var/lib/meridian/copy/to"
# Where an instance's pods mount its storage (MERIDIAN_STORAGE_DIR).
_STORAGE = "/var/lib/meridian/storage"
# The folder of the shared storage the instance's own records go to: the
# first shard's, as a one-pod instance is shard 0 of one.
_SHARD_0 = "shard-0"
# The folder a copy is made in before it is renamed `shard-0/` whole (review
# c5c L3).
_COPYING = "shard-0.copying"
# How long an instance's pod waits for its copy before its init container
# ends, failed, saying why (review c5c M1); how often it looks, and says so.
_WAIT_LIMIT = 15 * 60.0
_WAIT_EVERY = 2.0
_SAY_EVERY = 60.0

_NAME = "meridian-storage"
_USAGE = f"usage: {_NAME} copy <claim> | {_NAME} copied <claim>"


class _Refused(Exception):
    """Why the copy, or the wait, did not end done."""


@dataclass(frozen=True)
class _Copied:
    """What `_copy` did: copied now, so many files and bytes, or before --
    the marker was there, and nothing was written."""

    files: int = 0
    bytes: int = 0
    before: bool = False


def _marker(root: Path, claim: str) -> Path:
    """The marker in a shared storage `root` saying `claim` was copied into
    its `shard-0/` whole. A claim names it, so a claim is a name: empty, or
    holding a path's separator, `..` or a NUL, it is refused, by the copy
    and the wait alike, before anything is written (review of #57)."""
    if not claim or "/" in claim or ".." in claim or "\0" in claim:
        raise _Refused(
            f"{claim!r} is not a claim's name: the marker it names would not be "
            f"{root / '.meridian'}'s own"
        )
    return root / ".meridian" / f"copied-from-{claim}"


def _copied(root: Path, claim: str) -> bool:
    """Whether `claim` was copied into the shared storage at `root`."""
    return _marker(root, claim).exists()


def _say(level: str, message: str, **fields: object) -> None:
    said = "".join(f" {name}={value}" for name, value in fields.items())
    print(f"{level} {_NAME}: {message}{said}", file=sys.stderr, flush=True)


def _sync(path: Path) -> None:
    held = os.open(path, os.O_RDONLY)
    try:
        os.fsync(held)
    finally:
        os.close(held)


def _copy(source: Path, to: Path, claim: str) -> _Copied:
    """Copy everything under `source` into `to`'s `shard-0/`, then write the
    marker for `claim`, each file synced to disk first. A volume's own
    `lost+found` at the top is not the plugin's, and is left.

    The copy is made in `shard-0.copying/`, made again whole where one failed
    part way, and renamed `shard-0/` only where there is none: a `shard-0/`
    with no marker -- the marker removed by hand, say -- holds records the
    shards wrote, and is never written over (review c5c L3). The marker's
    `.writing` file is written once the copy is whole and before the rename,
    so a copy stopped after the rename is finished, not refused."""
    if _copied(to, claim):
        return _Copied(before=True)
    into, copying = to / _SHARD_0, to / _COPYING
    marked = _marker(to, claim)
    folder = marked.parent
    writing = folder / f".copied-from-{claim}.writing"
    counted = [0, 0]
    if writing.exists() and not into.exists() and not copying.exists():
        # Marked whole, and the copy since removed by hand: made again.
        try:
            writing.unlink()
        except OSError as failed:
            raise _Refused(f"{writing} could not be removed: {failed}") from failed
    if not writing.exists():
        if into.exists():
            raise _Refused(
                f"{into} is there with no mark that {claim} was copied into it: it holds what "
                "the shards wrote, and nothing is copied over it"
            )
        if copying.exists():
            _remove(copying)
        _copy_tree(source, copying, True, counted)
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as failed:
            raise _Refused(f"{folder} could not be made: {failed}") from failed
        try:
            with open(writing, "w") as marking:
                marking.write(f"{counted[0]} files, {counted[1]} bytes\n")
                marking.flush()
                os.fsync(marking.fileno())
            _sync(folder)
        except OSError as failed:
            raise _Refused(f"the marker {writing} was not written: {failed}") from failed
    if not into.exists():
        try:
            os.rename(copying, into)
            _sync(to)
        except OSError as failed:
            raise _Refused(f"{copying} was not renamed {into}: {failed}") from failed
    try:
        os.rename(writing, marked)
        _sync(folder)
    except OSError as failed:
        raise _Refused(f"the marker {marked} was not written: {failed}") from failed
    return _Copied(files=counted[0], bytes=counted[1])


def _remove(copying: Path) -> None:
    """A copy that failed part way, removed whole. The folders it copied
    whole hold their own modes, one only readable among them, and the
    plugin's own user is not root: each is opened to that user first, so it
    can be emptied (PO 86)."""

    def opened(folder: str) -> None:
        os.chmod(folder, stat.S_IMODE(os.lstat(folder).st_mode) | stat.S_IRWXU)
        with os.scandir(folder) as entries:
            inner = [entry.path for entry in entries if entry.is_dir(follow_symlinks=False)]
        for path in inner:
            opened(path)

    try:
        opened(str(copying))
        shutil.rmtree(copying)
    except OSError as failed:
        raise _Refused(f"{copying} could not be removed: {failed}") from failed


def _owned(path: Path, held: os.stat_result) -> None:
    """`path` given `held`'s owner, as far as this user can: an owner it
    cannot give is left its own, and a group it is not in, its own."""
    try:
        os.lchown(path, held.st_uid, held.st_gid)
    except OSError as failed:
        if failed.errno not in (errno.EPERM, errno.EINVAL):
            raise
        try:
            os.lchown(path, -1, held.st_gid)
        except OSError as again:
            if again.errno not in (errno.EPERM, errno.EINVAL):
                raise


def _copy_file(source: Path, target: Path) -> int:
    """A file copied and synced to disk, given its owner as far as this user
    can and then its mode -- a change of owner clears a setgid bit -- and its
    size returned."""
    with open(source, "rb") as reading, open(target, "wb") as written:
        shutil.copyfileobj(reading, written, 1 << 20)
        written.flush()
        os.fsync(written.fileno())
        size = written.tell()
    held = os.stat(source)
    _owned(target, held)
    os.chmod(target, stat.S_IMODE(held.st_mode))
    return size


def _copy_tree(source: Path, into: Path, top: bool, counted: list[int]) -> None:
    try:
        into.mkdir(parents=True, exist_ok=True)
    except OSError as failed:
        raise _Refused(f"{into} could not be made: {failed}") from failed
    try:
        with os.scandir(source) as listed:
            entries = sorted(listed, key=lambda entry: entry.name)
    except OSError as failed:
        raise _Refused(f"{source} could not be read: {failed}") from failed
    for entry in entries:
        if top and entry.name == "lost+found":
            continue
        there, target = Path(entry.path), into / entry.name
        try:
            kind = entry.stat(follow_symlinks=False).st_mode
        except OSError as failed:
            raise _Refused(f"{there} could not be read: {failed}") from failed
        is_link, is_folder = stat.S_ISLNK(kind), stat.S_ISDIR(kind)
        if not (is_link or is_folder or stat.S_ISREG(kind)):
            # Never opened: a FIFO would hold the copy until something
            # writes it, and a device would be read as records (review of
            # #57). The copy is left unmarked, the instance's pods waiting.
            raise _Refused(
                f"{there} is not a file, a folder or a link (a FIFO, a socket or a device): "
                "it is not the plugin's records, and nothing is copied"
            )
        if is_folder:
            _copy_tree(there, target, False, counted)
        elif is_link:
            try:
                points = os.readlink(there)
            except OSError as failed:
                raise _Refused(f"{there} could not be read: {failed}") from failed
            with contextlib.suppress(OSError):
                target.unlink()
            try:
                os.symlink(points, target)
                _owned(target, os.lstat(there))
            except OSError as failed:
                raise _Refused(f"{target} could not be made: {failed}") from failed
        else:
            try:
                size = _copy_file(there, target)
            except OSError as failed:
                raise _Refused(f"{there} was not copied to {target}: {failed}") from failed
            counted[0] += 1
            counted[1] += size
    # The folder's own owner and mode last, setgid bit and all, so a folder
    # only readable is still written into first (review c5c H1). A file's
    # are given with it.
    try:
        held = os.stat(source)
        _owned(into, held)
        os.chmod(into, stat.S_IMODE(held.st_mode))
    except OSError as failed:
        raise _Refused(f"{into} could not be given {source}'s mode: {failed}") from failed
    try:
        _sync(into)
    except OSError as failed:
        raise _Refused(f"{into} could not be synced: {failed}") from failed


def _wait(root: Path, claim: str, every: float, limit: float) -> None:
    """Wait, every `every` seconds, until `claim` was copied into the shared
    storage at `root`: an instance's pods' init container, so its plugin
    never starts on a partial copy. Says so once a minute while it waits,
    and past `limit` ends, refused, so the pod shows that its copy has not
    come."""
    started = time.monotonic()
    said = started
    while not _copied(root, claim):
        now = time.monotonic()
        if now - started >= limit:
            raise _Refused(
                f"{claim} was not copied into the instance's shared storage within "
                f"{int(limit)} s: its copy pod failed or has not run; launching the instance "
                "again makes the copy again"
            )
        if now - said >= _SAY_EVERY:
            _say(
                "INFO",
                "the instance's own storage is still being copied into its shared storage",
                claim=claim,
                waited_seconds=int(now - started),
            )
            said = now
        time.sleep(every)


def main(argv: Sequence[str] | None = None) -> int:
    """`meridian-storage copy <claim>`, the copy pod's command, and
    `meridian-storage copied <claim>`, its instance's pods' wait: 0 once
    done, 1 saying why otherwise."""
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else None
    claim = args[1] if len(args) > 1 else None
    try:
        if command == "copy":
            if not claim:
                raise _Refused("copy names the claim it copies")
            done = _copy(Path(_FROM), Path(_TO), claim)
            said: dict[str, object] = (
                {"copied": "before"}
                if done.before
                else {"copied": "now", "files": done.files, "bytes": done.bytes}
            )
            _say("INFO", "copied into the shared storage's shard-0/", claim=claim, **said)
            return 0
        if command == "copied":
            if not claim:
                raise _Refused("copied names the claim it waits on")
            _wait(Path(_STORAGE), claim, _WAIT_EVERY, _WAIT_LIMIT)
            _say("INFO", "its own storage is in its shared storage", claim=claim)
            return 0
        raise _Refused(_USAGE)
    except _Refused as refused:
        _say("ERROR", str(refused))
        return 1


if __name__ == "__main__":
    sys.exit(main())
