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
what storage holds is said on every heartbeat (`plugin.stored`).

How the plugin reaches its vendor is its own: this keeps what came back,
whatever the transport.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, TextIO

from .errors import MeridianError
from .v1 import sidecar_pb2

log = logging.getLogger(__name__)

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")
_NANOS_PER_SECOND = 1_000_000_000
_SECONDS_PER_DAY = 86_400
#: The day's line files held open for appending at once; one more opened
#: closes the one written least lately, which is reopened when next written.
_HELD_OPEN = 128
#: The live lines whose first arrival is remembered, the latest; any other's
#: is read from its line.
_REMEMBERED = 10_000


def storage_root(prefix: str = "meridian-raw-") -> Path:
    """The instance's granted storage (`storage_dir()`), else a temporary
    directory, which a restart loses."""
    from .edge import storage_dir

    granted = storage_dir()
    if granted is not None:
        return granted
    return Path(tempfile.mkdtemp(prefix=prefix))


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
    record is a JSON object holding at least `received_at_ns`."""

    def __init__(self, root: Path, kind: str = "responses") -> None:
        self.root = root
        self.kind = kind
        self._kept = 0
        #: The day the latest live line was kept on; what is remembered below
        #: is that day's, forgotten when a later day's first line arrives.
        self._day = ""
        #: Each file's last line kept: its body and its key.
        self._last: dict[str, tuple[str, str]] = {}
        #: The lines each day's file holds, counted once: a stream adds many.
        self._lines: dict[str, int] = {}
        #: When the answer each live line names first arrived, the latest
        #: `_REMEMBERED` of the day.
        self._first: OrderedDict[str, int] = OrderedDict()
        #: The files held open for appending, the one written least lately first.
        self._open: OrderedDict[str, TextIO] = OrderedDict()

    def keep(self, call: str, name: str, record: dict[str, Any]) -> str:
        """Keep one answer; its key. A key is never written twice."""
        self._kept += 1
        received = int(record["received_at_ns"])
        key = (
            f"{self.kind}/{_day_of(received)}/{_safe(call)}/"
            f"{_safe(name)}-{received}-{self._kept}.json"
        )
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as out:
            json.dump(record, out, indent=1, sort_keys=True)
        return key

    def keep_line(self, call: str, name: str, record: dict[str, Any]) -> str:
        """Keep one live answer as the next line of its day's file for `call`
        and `name`, unless its body is the one kept last for them, which the
        returned key then names again: `<file>#<line>`. The line is written
        and flushed before this returns."""
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
        lines = self._lines.get(key)
        if lines is None:
            path = self.root / key
            lines = sum(1 for _ in path.open(encoding="utf-8")) if path.exists() else 0
        out = self._appender(key)
        try:
            out.write(json.dumps(record, sort_keys=True) + "\n")
            out.flush()
        except OSError:
            self._close(key)
            raise
        self._lines[key] = lines + 1
        named = f"{key}#{lines}"
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

    def _appender(self, key: str) -> TextIO:
        """The file `key` names, held open for appending: its directory made
        when it is first opened, the file written least lately closed past
        `_HELD_OPEN`."""
        out = self._open.get(key)
        if out is not None:
            self._open.move_to_end(key)
            return out
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        out = path.open("a", encoding="utf-8")
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

        def earlier(key: str) -> bool:
            return key[len(prefix) : len(prefix) + 10] < before

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
        day's live answers. None once it has moved or gone."""
        key, _, where = ref_key.partition("#")
        path = self.root / key
        if not path.is_file():
            return None
        if path.suffix == ".jsonl":
            if not where.isdigit():
                return None
            lines = path.read_text(encoding="utf-8").splitlines()
            if int(where) >= len(lines):
                return None
            line: dict[str, Any] = json.loads(lines[int(where)])
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

    async def tend(self, plugin: Any, window_days: int, past: str, today: date) -> None:
        """Move each day's unit past the window as `past` says -- `archived` or
        `deleted` through the SDK, `kept` left -- never today's, which is still
        being written; then say what storage holds (`plugin.stored`). A move
        refused (no archive, a deletion inside the deployment's hold) keeps
        the unit, and the next pass tries again."""
        cutoff = today - timedelta(days=max(window_days, 0))
        self._forget(before=today.isoformat())
        for unit in self.units():
            if unit.day >= cutoff or unit.day >= today or past == "kept":
                continue
            try:
                if past == "archived":
                    await plugin.archive_unit(
                        self.kind,
                        unit.unit,
                        record_count=unit.records,
                        first_received_ns=unit.first_ns,
                        last_received_ns=unit.last_ns,
                    )
                elif past == "deleted":
                    await plugin.delete_unit(
                        self.kind,
                        unit.unit,
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
