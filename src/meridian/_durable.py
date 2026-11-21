"""A kept file written whole: fsync and rename.

``write_whole(path, data)`` puts ``data`` at ``path`` so that once it returns
the file is the new one, whole, whatever happens next: a crash, a lost node,
or a filesystem that keeps only what it was told to sync. A crash while it
runs leaves the old file whole or the new one, never a mix, an empty file or
one of zeros.

Each step is needed:

1. The data goes to a temporary file beside the target, created exclusively
   under a name of its own, so two writers of one file never write into one
   temporary file. Two holders of a shard write at once in a takeover's lapse
   (a deposed holder and the new one): with a fixed temporary name, one
   truncates the other's file mid-write and the other's rename puts the torn
   result in place.
2. The temporary file is synced, so its data is on disk before any name
   points at it.
3. It is renamed over the target, which is atomic: a reader sees the old file
   or the new.
4. The directory is synced, so the rename itself is on disk before the call
   returns. A directory this makes is synced into its parent the same way.

The file is made 0o600, readable and writable by its owner only.

Two writers in a lapse still end with one of them: the last rename wins,
whole. Which one is the role's to settle, by its epoch or the book.

Only ``os`` is used, so a test can stand a filesystem in for it that drops
whatever was not synced.
"""

from __future__ import annotations

import contextlib
import os
import secrets
from pathlib import Path

_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)


def write_whole(path: str | os.PathLike[str], data: bytes | str) -> None:
    """``data`` (text as UTF-8) at ``path``, whole and synced before this
    returns; the old file whole or the new one after a crash during it."""
    target = Path(path)
    body = data.encode("utf-8") if isinstance(data, str) else data
    _make_directory(target.parent)
    temporary = target.with_name(f".{target.name}.{secrets.token_hex(8)}.part")
    # Read and write for its owner only: a kept file holds a plugin's state.
    # The rename keeps this mode, so a target that was wider ends 0o600 too.
    handle = os.open(temporary, _OPEN_FLAGS, 0o600)
    try:
        try:
            left = memoryview(body)
            while left:
                left = left[os.write(handle, left) :]
            os.fsync(handle)
        finally:
            os.close(handle)
        os.replace(temporary, target)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise
    _sync_directory(target.parent)


def _make_directory(directory: Path) -> None:
    """``directory`` and any parent it lacks, each made synced into its
    parent."""
    try:
        os.mkdir(directory)
    except FileExistsError:
        return
    except FileNotFoundError:
        _make_directory(directory.parent)
        try:
            os.mkdir(directory)
        except FileExistsError:
            return
    _sync_directory(directory.parent)


def _sync_directory(directory: Path) -> None:
    handle = os.open(directory, _DIRECTORY_FLAGS)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)
