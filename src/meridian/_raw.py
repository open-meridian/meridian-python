"""An edge plugin's raw records as files in its storage, one unit a UTC day
(decisions/028; contract v16's archive), re-exported by `meridian.edge`.

Every answer a vendor sends -- an error and a rate limit as much as a price --
is kept before anything is read from it, exactly as its bytes arrived, with
the request that asked for it and when it was received. A row converted from
it names it by a `RawRecordRef` whose key is the record's path in storage,
then `#` and where in it the row came from (`#1791417600`, a candle's start;
`#41`, a line of a day's live answers), so a person auditing a row follows it
here and finds what the vendor said.

    store = RawStore(storage_root(), kind="responses")
    key = store.keep("candles", "BTC-USD", {"received_at_ns": now, "body": text, ...})
    key = store.keep_line("ticker", "BTC-USD", {"received_at_ns": now, "body": text})
    await store.tend(plugin, window_days=30, past="archived", today=today)
    await store.tend(plugin, settings=config, today=today)   # the kind's own settings

One kind of raw record (`kind`, the plugin's `RecordKind` key), kept in units
of a UTC day: `<kind>/2026-10-09/`, holding that day's answers as one file
each, and its live answers -- asked as often as once a second -- as a line
each of one file per call and name, a line added only when the answer
changed, so a row read from an answer that did not change names the line it
was first read from and the time it first arrived (`received`). A line is in
its file when `keep_line` returns -- written and flushed, as a closed file's
would be -- so a process that dies loses none it was told was kept; the
files a stream writes are held open meanwhile, and what is remembered of the
lines is the current day's and bounded, so a stream's memory stays flat.

Past the kind's window a day's unit is archived, kept or deleted as its
`<kind>_past_window` setting says, through the SDK's `archive_unit` and
`delete_unit`, each reporting the move before anything is removed (`tend`);
what storage holds is said on every heartbeat (`plugin.stored`). Given the
settings as delivered (`settings=`, from 0.35.2: a `@meridian.settings`
instance, `meridian.Settings` or their values), `tend` reads the kind's
window and past-window settings from them, so the plugin copies neither.

On a shard of its instance (step 3d, item 30) a store on the granted
storage (`storage_root()`) writes in the shard's own folder once the plugin
has registered, made before or after, and its keys name the record across
the instance, `shard-<n>/<kind>/...`; `get` reads any shard's record by its
key, and one with no prefix under `shard-0/`, where the instance's storage
was copied when it began running as shards. A takeover's pod resumes a live
file's lines where the shard's last pod left them.

How the plugin reaches its vendor is its own: this keeps what came back,
whatever the transport.
"""

from __future__ import annotations

import errno
import fcntl
import json
import logging
import os
import re
import struct
import tempfile
import threading
import time
from collections import OrderedDict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, TextIO

from .errors import MeridianError
from .v1 import sidecar_pb2

log = logging.getLogger(__name__)

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")
#: What is done with a unit past its kind's window: the `<kind>_past_window`
#: setting's three choices, the SDK's for every kind.
_PAST_WINDOW = ("archived", "kept", "deleted")
_NANOS_PER_SECOND = 1_000_000_000
_SECONDS_PER_DAY = 86_400
#: The day's line files held open for appending at once; one more opened
#: closes the one written least lately, which is reopened when next written.
_HELD_OPEN = 128
#: The live lines whose first arrival is remembered, the latest; any other's
#: is read from its line.
_REMEMBERED = 10_000
#: How long `keep_line` waits, at most, for the store while another thread is
#: in `keep_line` and then for its file's lock while another pod holds it, the
#: two together: past it the line is refused (TimeoutError), never waited for
#: without end on the loop the heartbeat runs on. Under a heartbeat's period.
_LINE_WAIT_SECONDS = 2.0

#: Open-file-description locks where the platform has them (Linux 3.15+, and
#: NFS through it): held by the descriptor that took them, so closing any other
#: descriptor on the file in this process -- a read on a worker thread, another
#: `RawStore` -- never lets one go, and two descriptors in one process
#: conflict as two processes do. Elsewhere (macOS, a developer's machine),
#: POSIX record locks (`lockf`), which are the whole process's.
_OFD_SETLK: int | None = getattr(fcntl, "F_OFD_SETLK", None)


def _flock(kind: int) -> bytes:
    """A `struct flock` over the whole file, as Linux lays it out on 64 bits:
    `l_type`, `l_whence`, `l_start`, `l_len`, `l_pid` (0, as an OFD lock's is)."""
    return struct.pack("hhqqixxxx", kind, os.SEEK_SET, 0, 0, 0)


def _try_lock(fd: int) -> bool:
    """`fd`'s file locked for writing without waiting: False while another
    holds it. By the descriptor where the platform can (`_OFD_SETLK`); a
    storage that refuses such a lock is locked by `lockf` from then on."""
    global _OFD_SETLK
    try:
        if _OFD_SETLK is not None:
            try:
                fcntl.fcntl(fd, _OFD_SETLK, _flock(fcntl.F_WRLCK))
                return True
            except OSError as refused:
                if refused.errno not in (errno.EINVAL, errno.ENOSYS, errno.EOPNOTSUPP):
                    raise
                log.warning(
                    "the storage refuses a descriptor's lock (%s); using lockf", refused
                )
                _OFD_SETLK = None
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as busy:
        if busy.errno in (errno.EACCES, errno.EAGAIN):
            return False
        raise


def _unlock(fd: int) -> None:
    """`fd`'s lock let go, whichever kind `_try_lock` took."""
    if _OFD_SETLK is not None:
        fcntl.fcntl(fd, _OFD_SETLK, _flock(fcntl.F_UNLCK))
    fcntl.lockf(fd, fcntl.LOCK_UN)


def _lock_waiting(fd: int, within: float, what: str, ends: float | None = None) -> None:
    """`fd`'s file locked, waited for while another holds it, at most
    `within` seconds, or until the monotonic time `ends` where given (what is
    left of a wait begun earlier): past that, TimeoutError naming `what` and
    `within`, nothing done. Blocks its thread meanwhile."""
    if ends is None:
        ends = time.monotonic() + within
    wait = 0.002
    while not _try_lock(fd):
        left = ends - time.monotonic()
        if left <= 0:
            raise TimeoutError(
                f"{what} is locked by another pod past {within:g} s: nothing was written; "
                "ask again"
            )
        time.sleep(min(wait, left))
        wait = min(wait * 2, 0.05)


def storage_root(prefix: str = "meridian-raw-") -> Path:
    """The instance's granted storage (`storage_dir()`), else a temporary
    directory, which a restart loses.

    Read before Register it answers the instance's storage as a whole, with
    no refusal: a `RawStore` made on it follows to its shard's folder once
    the plugin registered, so it is for a `RawStore` alone then. A plugin's
    own files go under `storage_dir()`, read from its class's `on_start`."""
    from .edge import _storage_dir

    # Before Register, the storage as a whole, which a RawStore made on it
    # follows to its shard's folder once registered.
    granted = _storage_dir()
    if granted is not None:
        return granted
    return Path(tempfile.mkdtemp(prefix=prefix))


def _generation() -> int:
    from . import edge

    return edge._generation


def _safe(part: str) -> str:
    return _UNSAFE.sub("_", part) or "_"


def _day_of(received_ns: int) -> str:
    seconds = received_ns // _NANOS_PER_SECOND
    return date.fromordinal(
        date(1970, 1, 1).toordinal() + seconds // _SECONDS_PER_DAY
    ).isoformat()


@dataclass(frozen=True)
class StoredUnit:
    """One UTC day's raw records: its path in storage, how many records it
    holds and when the first and last arrived."""

    unit: str
    day: date
    records: int
    first_ns: int
    last_ns: int


class RawStore:
    """Raw records as files under the storage's `<kind>/`, one unit a day. Each
    record is a JSON object holding at least `received_at_ns`.

    Its records may be kept from several threads -- a market's REST
    answers on worker threads and its stream's messages on the loop: a
    `keep_line`, `keep` or `tend` while another thread is in `keep_line`
    waits its turn, at most `_LINE_WAIT_SECONDS`, then TimeoutError and
    nothing written or moved; none closes a file another thread is writing.
    The moves `tend` makes are the loop's, as the plugin registered on it.
    Its files' locks hold across the pods of a shard."""

    def __init__(self, root: Path, kind: str = "responses") -> None:
        self._given = root
        self.kind = kind
        self._kept = 0
        #: The day the latest live line was kept on; what is remembered below
        #: is that day's, forgotten when a later day's first line arrives.
        self._day = ""
        #: Each file's last line kept: its body and its key.
        self._last: dict[str, tuple[str, str]] = {}
        #: The lines each day's file held and its size in bytes, as last
        #: counted: counted again past that size, only the bytes added.
        self._lines: dict[str, tuple[int, int]] = {}
        #: When the answer each live line names first arrived, the latest
        #: `_REMEMBERED` of the day.
        self._first: OrderedDict[str, int] = OrderedDict()
        #: The files held open for appending, the one written least lately first.
        self._open: OrderedDict[str, TextIO] = OrderedDict()
        #: The Register it remembers its files under (`_fresh`).
        self._generation = _generation()
        #: Held while a thread reads or changes what the store remembers
        #: (`keep_line`, `keep`, `tend`): another waits for it.
        self._writing = threading.Lock()

    def _fresh(self) -> None:
        """What it remembers of its files forgotten, and its open files
        closed, when the plugin has registered again since: as another
        shard, or its own taken back after a standby wrote it."""
        now = _generation()
        if now == self._generation:
            return
        self._generation = now
        for out in self._open.values():
            out.close()
        self._open.clear()
        self._last.clear()
        self._lines.clear()
        self._first.clear()
        self._day = ""

    def _within(self) -> PurePosixPath | None:
        """Where it was given in the instance's granted storage -- the
        storage itself, a shard's folder, or a folder in either -- as a path
        below the shard's folder; None for a root elsewhere."""
        from .edge import _split, instance_storage_dir

        granted = instance_storage_dir()
        if granted is None:
            return None
        try:
            below = PurePosixPath(Path(self._given).relative_to(granted).as_posix())
        except ValueError:
            return None
        shard, rest = _split(below.as_posix() + "/")
        return PurePosixPath(rest or ".") if shard is not None else below

    def _sharded(self) -> PurePosixPath | None:
        """Where it is below its shard's folder, on the granted storage of
        an instance of shards; None where it writes the root it was given."""
        from .edge import _sharded

        return self._within() if _sharded() else None

    @property
    def root(self) -> Path:
        """Where it writes: on the granted storage of an instance of shards,
        its place in the shard's own folder (`storage_dir()`), whenever it
        was made; else the root it was given."""
        from .edge import storage_dir

        below = self._sharded()
        if below is None:
            return self._given
        # Registered as a shard, so its folder is known: never the refusal
        # a read before Register meets on shared storage.
        mine = storage_dir()
        if mine is None:
            return self._given
        return mine.joinpath(*below.parts)

    @root.setter
    def root(self, given: Path) -> None:
        self._given = given
        self._generation = -1

    def _prefix(self) -> str:
        """What its keys are prefixed with, so they name the record across
        the instance: its shard's folder and its place there, on the granted
        storage of an instance of shards; else nothing."""
        from .edge import _shard_prefix

        below = self._sharded()
        if below is None:
            return ""
        return _shard_prefix() + ("" if str(below) == "." else f"{below}/")

    def _path(self, key: str) -> Path:
        """The file a key names: on the granted storage of an instance of
        shards, in whichever shard's folder it names, or, with no prefix,
        shard 0's, where the copy put what the instance kept before; else
        under the root it was given."""
        from .edge import _split, instance_storage_dir

        below = self._sharded()
        granted = instance_storage_dir()
        if below is None or granted is None:
            return self._given / key
        if _split(key)[0] is not None:
            return granted / key
        return granted.joinpath("shard-0", *below.parts) / key

    def keep(self, call: str, name: str, record: dict[str, Any]) -> str:
        """Keep one answer; its key. A key is never written twice.

        What the store remembers is read and changed one thread at a time:
        while another thread is in `keep_line`, this waits for it, at most
        `_LINE_WAIT_SECONDS`, then TimeoutError and nothing written, rather
        than close a file the other is writing (0.37.1). The answer's own
        file is written after, with no wait."""
        received = int(record["received_at_ns"])
        self._take("nothing was written; ask again")
        try:
            self._fresh()
            self._kept += 1
            kept = self._kept
        finally:
            self._writing.release()
        key = (
            f"{self.kind}/{_day_of(received)}/{_safe(call)}/"
            f"{_safe(name)}-{received}-{kept}.json"
        )
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as out:
            json.dump(record, out, indent=1, sort_keys=True)
            out.flush()
            os.fsync(out.fileno())
        return self._prefix() + key

    def keep_line(self, call: str, name: str, record: dict[str, Any]) -> str:
        """Keep one live answer as the next line of its day's file for `call`
        and `name`, unless its body is the one kept last for them, which the
        returned key then names again: `<file>#<line>`. The line is written
        and synced before this returns. The file is locked while its lines
        are counted and the line written, so a pod still writing through a
        takeover's lapse and the shard's new holder each name their own; a
        line a crash left unfinished is ended first, and counted. Another
        pod's lock is waited for at most `_LINE_WAIT_SECONDS` (two seconds),
        then the line is refused, TimeoutError, and nothing written.

        Its lines are written by one thread at a time, as both would count
        the same lines through the one descriptor: a second thread's
        `keep_line` while one is in it waits for it -- a REST answer kept on
        a worker thread while a stream message is kept on the loop, say --
        within the same two seconds, the wait for the thread and for the
        pod together, then TimeoutError and nothing written (0.37.1; 0.37.0
        refused it at once, and the message was dropped). Blocks its thread
        meanwhile."""
        within = _LINE_WAIT_SECONDS
        ends = time.monotonic() + within
        self._take("nothing was written; ask again", within)
        try:
            return self._keep_line(call, name, record, within, ends)
        finally:
            self._writing.release()

    def _take(self, unless: str, within: float | None = None) -> None:
        """What the store remembers held for this thread, waited for while
        another thread is in it, at most `within` seconds
        (`_LINE_WAIT_SECONDS` where not given): past that, TimeoutError
        saying `unless`. Blocks its thread meanwhile; released by the
        caller."""
        if within is None:
            within = _LINE_WAIT_SECONDS
        if not self._writing.acquire(timeout=within):
            raise TimeoutError(
                f"this RawStore's live files are locked by another thread past {within:g} s: "
                f"{unless}"
            )

    def _keep_line(
        self, call: str, name: str, record: dict[str, Any], within: float, ends: float
    ) -> str:
        self._fresh()
        received = int(record["received_at_ns"])
        day = _day_of(received)
        if day > self._day:
            self._forget(before=day)
            self._day = day
        key = f"{self.kind}/{day}/{_safe(call)}/{_safe(name)}.jsonl"
        body = str(record.get("body", ""))
        held = self._last.get(key)
        if held is not None and held[0] == body:
            return held[1]
        out = self._appender(key)
        try:
            _lock_waiting(out.fileno(), within, f"the live file {key}", ends)
            try:
                lines = self._count(key, out)
                out.write(json.dumps(record, sort_keys=True) + "\n")
                out.flush()
                os.fsync(out.fileno())
                self._lines[key] = (lines + 1, os.fstat(out.fileno()).st_size)
            finally:
                try:
                    _unlock(out.fileno())
                except OSError as failed:
                    # Closing it lets the lock go all the same; a line
                    # written is not turned into a failure here.
                    log.warning("the lock on %s was let go by closing it: %s", key, failed)
                    self._close(key)
        except OSError:
            self._close(key)
            raise
        named = f"{self._prefix()}{key}#{lines}"
        self._last[key] = (body, named)
        self._first[named] = received
        if len(self._first) > _REMEMBERED:
            self._first.popitem(last=False)
        return named

    def received(self, ref_key: str, otherwise: int) -> int:
        """When the answer a key names first arrived, for a live line kept by
        this store: remembered, or read from its line; `otherwise` for
        anything else."""
        remembered = self._first.get(ref_key)
        if remembered is not None:
            return remembered
        if ref_key.partition("#")[0].endswith(".jsonl"):
            line = self.get(ref_key)
            if line is not None and "received_at_ns" in line:
                return int(line["received_at_ns"])
        return otherwise

    def _count(self, key: str, out: TextIO) -> int:
        """The lines the file holds now, its lock held: as last counted
        where its size is unchanged, else counted on from there, reading
        only what was added. A last line left unfinished is ended. Read
        through the appender's own descriptor: closing any other on the
        file would drop the process's lock on it."""
        size = os.fstat(out.fileno()).st_size
        lines, counted = self._lines.get(key, (0, 0))
        if counted == size:
            return lines
        if counted > size:
            lines, counted = 0, 0
        added = b""
        while counted + len(added) < size:
            got = os.pread(out.fileno(), size - counted - len(added), counted + len(added))
            if not got:
                break
            added += got
        lines += added.count(b"\n")
        if added and not added.endswith(b"\n"):
            out.write("\n")
            out.flush()
            lines += 1
        return lines

    def _appender(self, key: str) -> TextIO:
        """The file `key` names, held open for appending, and readable, so
        its lines are counted through it (`_count`): its directory made
        when it is first opened, the file written least lately closed past
        `_HELD_OPEN`."""
        out = self._open.get(key)
        if out is not None:
            self._open.move_to_end(key)
            return out
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        out = path.open("a+", encoding="utf-8")
        self._open[key] = out
        if len(self._open) > _HELD_OPEN:
            self._open.popitem(last=False)[1].close()
        return out

    def _close(self, key: str) -> None:
        out = self._open.pop(key, None)
        if out is not None:
            out.close()

    def _forget(self, before: str) -> None:
        """Close the files of days before `before` and forget their lines: a
        day's rollover, and a past day's unit about to move. Anything
        forgotten is still in its file, and read from it if asked again."""
        prefix = f"{self.kind}/"

        own = self._prefix()

        def earlier(key: str) -> bool:
            within = key[len(own) :] if own and key.startswith(own) else key
            return within[len(prefix) : len(prefix) + 10] < before

        for key in [k for k in self._open if earlier(k)]:
            self._close(key)
        for held in (self._last, self._lines):
            for key in [k for k in held if earlier(k)]:
                del held[key]
        for named in [k for k in self._first if earlier(k)]:
            del self._first[named]

    def __del__(self) -> None:
        for out in getattr(self, "_open", {}).values():
            out.close()

    def get(self, ref_key: str) -> dict[str, Any] | None:
        """The record a row's reference names: a whole answer, or one line of a
        day's live answers. None once it has moved or gone, or for a line a
        crash left unfinished. Read from its file, where its shard's is now:
        nothing the store remembers is read, and none of its files closed,
        so a line another thread is writing is let be (0.37.1)."""
        key, _, where = ref_key.partition("#")
        path = self._path(key)
        if not path.is_file():
            return None
        if path.suffix == ".jsonl":
            if not where.isdigit():
                return None
            lines = path.read_text(encoding="utf-8").splitlines()
            if int(where) >= len(lines):
                return None
            try:
                line: dict[str, Any] = json.loads(lines[int(where)])
            except ValueError:
                return None
            return line
        record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return record

    def records(self) -> Iterator[dict[str, Any]]:
        """Every record kept, oldest day first: what a recorded replay reads."""
        base = self.root / self.kind
        if not base.is_dir():
            return
        for path in sorted(base.rglob("*")):
            if path.suffix == ".json":
                yield json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix == ".jsonl":
                for line in path.read_text(encoding="utf-8").splitlines():
                    yield json.loads(line)

    def units(self) -> list[StoredUnit]:
        """Each day's unit in storage, oldest first."""
        base = self.root / self.kind
        found: list[StoredUnit] = []
        if not base.is_dir():
            return found
        for directory in sorted(p for p in base.iterdir() if p.is_dir()):
            try:
                day = date.fromisoformat(directory.name)
            except ValueError:
                continue
            count, first, last = 0, 0, 0
            for path in directory.rglob("*"):
                if path.suffix == ".json":
                    stamps = [
                        int(json.loads(path.read_text(encoding="utf-8"))["received_at_ns"])
                    ]
                elif path.suffix == ".jsonl":
                    stamps = [
                        int(json.loads(line)["received_at_ns"])
                        for line in path.read_text(encoding="utf-8").splitlines()
                    ]
                else:
                    continue
                for at in stamps:
                    count += 1
                    first = at if not first else min(first, at)
                    last = max(last, at)
            if count:
                found.append(
                    StoredUnit(f"{self.kind}/{directory.name}", day, count, first, last)
                )
        return found

    async def tend(
        self,
        plugin: Any,
        window_days: int | None = None,
        past: str | None = None,
        today: date | None = None,
        *,
        settings: Any = None,
    ) -> None:
        """Move each day's unit past the window as `past` says -- `archived` or
        `deleted` through the SDK, `kept` left -- never today's, which is still
        being written; then say what storage holds (`plugin.stored`). A move
        refused (no archive, a deletion inside the deployment's hold) keeps
        the unit, and the next pass tries again.

        From 0.35.2 `settings` -- the settings as delivered: an instance of
        the class decorated `@meridian.settings`, `meridian.Settings`, or
        their values -- gives the window and `past` not given, read from the
        kind's own settings, `<kind>_window_days` and `<kind>_past_window`,
        which the SDK declares; `today` is the UTC date where not given.

        From 0.35.3 only what is not given is read from `settings`, and a
        setting the settings do not hold is refused, naming it: the SDK
        fills both in every delivery for a kind its declaration names, so
        one missing is a kind not declared, never a default to guess -- what
        is done past the window is the plugin admin's to choose. Given a
        window alone, with no settings, nothing moves past it (`kept`, the
        default where no archive is granted, and never a deletion the admin
        did not choose). A window below 0, or a `past` other than
        `archived`, `kept` or `deleted`, is refused, naming it.

        From 0.37.1 it closes past days' files only once no other thread is
        in `keep_line`, waiting at most `_LINE_WAIT_SECONDS` (blocking the
        loop meanwhile, as a line kept there does); past that, TimeoutError
        and nothing moved, for the next pass."""
        if past is None and settings is None and window_days is not None:
            past = "kept"
        if window_days is None or past is None:
            window_days, past = self._window(settings, window_days, past)
        window_days, past = self._checked(window_days, past)
        if today is None:
            today = datetime.now(UTC).date()
        cutoff = today - timedelta(days=window_days)
        # Past days' files closed only once no other thread is writing one
        # (0.37.1): a line still being kept for yesterday is let finish.
        self._take("nothing moved; the next pass tries again")
        try:
            self._fresh()
            self._forget(before=today.isoformat())
        finally:
            self._writing.release()
        for unit in self.units():
            if unit.day >= cutoff or unit.day >= today or past == "kept":
                continue
            try:
                named = self._named(unit.unit)
                if past == "archived":
                    await plugin.archive_unit(
                        self.kind,
                        named,
                        record_count=unit.records,
                        first_received_ns=unit.first_ns,
                        last_received_ns=unit.last_ns,
                    )
                elif past == "deleted":
                    await plugin.delete_unit(
                        self.kind,
                        named,
                        record_count=unit.records,
                        first_received_ns=unit.first_ns,
                        last_received_ns=unit.last_ns,
                    )
            except (MeridianError, ValueError, RuntimeError, OSError) as refused:
                log.warning("%s kept, its move refused: %s", unit.unit, refused)
        held = self.units()
        if held:
            plugin.stored = [
                sidecar_pb2.StoredSpan(
                    record_kind=self.kind,
                    record_count=sum(u.records for u in held),
                    first_received_ns=min(u.first_ns for u in held),
                    last_received_ns=max(u.last_ns for u in held),
                )
            ]

    def _named(self, unit: str) -> str:
        """A unit as a move names it, as the instance does: with its shard's
        prefix on the granted storage of an instance of shards."""
        from .edge import _instance_key

        return _instance_key(unit) if self._sharded() is not None else unit

    def _window(
        self, settings: Any, window_days: int | None, past: str | None
    ) -> tuple[int, str]:
        """The window and what is done past it: as given, else the kind's own
        settings in `settings`."""
        if settings is None:
            raise TypeError(
                "tend is given the window and what is done past it, or the settings "
                "that hold them (settings=)"
            )
        values = (
            settings if isinstance(settings, Mapping) else getattr(settings, "values", None)
        )
        if not isinstance(values, Mapping):
            raise TypeError(
                f"settings is a {type(settings).__name__}: give the settings as delivered "
                "(a @meridian.settings instance, meridian.Settings) or their values"
            )
        named = (f"{self.kind}_window_days", f"{self.kind}_past_window")
        wanted = [
            n for n, given in zip(named, (window_days, past), strict=True) if given is None
        ]
        absent = [name for name in wanted if name not in values]
        if absent:
            raise ValueError(
                f"the settings hold no {' or '.join(absent)}: the SDK declares them for "
                f"each kind the declaration's Storage(kinds=...) names, and {self.kind} "
                "is not among them"
            )
        if window_days is None:
            window_days = values[named[0]]
        if past is None:
            past = values[named[1]]
        return window_days, past

    def _checked(self, window_days: Any, past: Any) -> tuple[int, str]:
        """The window a whole number of days, 0 or more, and `past` one of
        the three choices the SDK declares: else refused, naming it."""
        named = f"{self.kind}_window_days"
        if isinstance(window_days, bool) or not isinstance(window_days, int | str):
            raise ValueError(f"{named} is a whole number of days: {window_days!r}")
        try:
            days = int(window_days)
        except ValueError:
            raise ValueError(f"{named} is a whole number of days: {window_days!r}") from None
        if days < 0:
            raise ValueError(f"{named} is 0 or more days: {days}")
        if past not in _PAST_WINDOW:
            raise ValueError(
                f"{self.kind}_past_window is one of {', '.join(_PAST_WINDOW)}: {past!r}"
            )
        return days, str(past)
