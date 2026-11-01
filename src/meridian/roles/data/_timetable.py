"""When a polled source's standing wants are read again (SDK 0.35;
spec/each-role-is-one-generated-class, section 4, 924's item 9; the
data-plugin fit review's section 1.9).

Every polling plugin kept its own due times: a chain every five minutes, a
tape every thirty seconds, hand-coded hours, a calendar copy. `Timetable`
keeps them once, per dataset and subject:

    timetable = data.Timetable(allowance=quota, reserve=500)
    timetable.of(TAPES, read_tapes, sessions=hours, market_days=days)  # its cadence
    timetable.want("tapes", ["INS-1", "INS-2"])     # due at once, then each cadence
    await timetable.tick()                          # each read due, made

- **Cadence** from the dataset's declaration (`cadence`, seconds), or given
  (`every`). A subject wanted is due at once, then every cadence after its
  last read; withdrawn, it is never read again.
- **Gated** by the venue's trading sessions (`roles.in_session`) and the
  market's days (`helpers.calendars.MarketDays`): out of session, or on a
  closed day, nothing is due. A calendar not answering gates nothing.
- **Within an allowance**: given one (anything with `allows(calls,
  reserve=)` and `spend(calls)`, a vendor's daily or monthly quota as the
  plugin keeps it), a read is due only while it fits leaving `reserve`
  unspent, so reads wanted now still have room. How fast each call goes is
  the plugin's own pacing.

Each due read is one `await read(subjects)` the plugin supplies, its
subjects every one of the dataset's due then.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

__all__ = ["Timetable"]

log = logging.getLogger("meridian.roles.data.timetable")

NS = 1_000_000_000

Read = Callable[[Sequence[str]], Awaitable[Any]]


@dataclass
class _Entry:
    dataset: str
    every_ns: int
    read: Read | None
    sessions: Any = None
    market_days: Any = None
    cost: int = 1
    #: Each subject wanted, and when it is next due.
    due_at: dict[str, int] = field(default_factory=dict)


class Timetable:
    """Each dataset's subjects, read at its cadence (see the module).
    `clock_ns` is for a test."""

    def __init__(
        self,
        *,
        allowance: Any = None,
        reserve: int = 0,
        clock_ns: Callable[[], int] = time.time_ns,
    ) -> None:
        if reserve < 0:
            raise ValueError(f"a timetable's reserve is 0 or more: {reserve}")
        self.allowance, self.reserve = allowance, reserve
        self._clock_ns = clock_ns
        self.entries: dict[str, _Entry] = {}
        #: Reads made, and those held back by the allowance, since start.
        self.reads = 0
        self.held_back = 0

    def every(
        self,
        dataset: str,
        every_s: float,
        read: Read | None = None,
        *,
        sessions: Any = None,
        market_days: Any = None,
        cost: int = 1,
    ) -> None:
        """Read `dataset`'s subjects every `every_s` seconds with `read`,
        gated by `sessions` (`TradingSessions`) and `market_days`, each read
        costing `cost` of the allowance. Its subjects wanted carry over."""
        if every_s <= 0:
            raise ValueError(f"the dataset {dataset!r} is read every so many seconds, above 0")
        if cost < 0:
            raise ValueError(f"a read's cost is 0 or more: {cost}")
        held = self.entries.get(dataset)
        self.entries[dataset] = _Entry(
            dataset,
            int(every_s * NS),
            read,
            sessions,
            market_days,
            cost,
            held.due_at if held is not None else {},
        )

    def of(self, declaration: Any, read: Read | None = None, **gates: Any) -> None:
        """Read a declared dataset at its declared `cadence` (by its key)."""
        cadence = int(getattr(declaration, "cadence", 0))
        if cadence <= 0:
            raise ValueError(f"the dataset {declaration.key!r} declares no cadence to poll at")
        self.every(declaration.key, cadence, read, **gates)

    def want(self, dataset: str, subjects: Sequence[str]) -> None:
        """Subjects to read, each due at once where not wanted already."""
        entry = self._entry(dataset)
        now = self._clock_ns()
        for subject in subjects:
            entry.due_at.setdefault(subject, now)

    def withdraw(self, dataset: str, subjects: Sequence[str] | None = None) -> None:
        """Subjects no longer read: these, or every one of the dataset's."""
        entry = self._entry(dataset)
        if subjects is None:
            entry.due_at.clear()
            return
        for subject in subjects:
            entry.due_at.pop(subject, None)

    def wanted(self, dataset: str) -> tuple[str, ...]:
        """The dataset's subjects wanted now."""
        return tuple(self._entry(dataset).due_at)

    def _entry(self, dataset: str) -> _Entry:
        entry = self.entries.get(dataset)
        if entry is None:
            raise KeyError(f"the timetable reads no dataset {dataset!r}: give it its cadence")
        return entry

    async def _open(self, entry: _Entry, now: int) -> bool:
        if entry.sessions is not None:
            from .._latency import in_session

            if not in_session(entry.sessions, now):
                return False
        days = entry.market_days
        if days is not None:
            clock = getattr(days, "day_clock", None)
            today = (
                clock.business_date_of(now)
                if clock is not None
                else datetime.fromtimestamp(now / NS, UTC).date()
            )
            # A calendar not answering (None) gates nothing.
            return await days.is_open(today) is not False
        return True

    async def due(self, now_ns: int | None = None) -> list[tuple[str, tuple[str, ...]]]:
        """Each dataset with subjects due now, and those subjects, each then
        due again a cadence later; the allowance spent for each read."""
        now = self._clock_ns() if now_ns is None else now_ns
        out: list[tuple[str, tuple[str, ...]]] = []
        for entry in self.entries.values():
            subjects = tuple(s for s, at in entry.due_at.items() if at <= now)
            if not subjects or not await self._open(entry, now):
                continue
            if self.allowance is not None and entry.cost:
                if not self.allowance.allows(entry.cost, reserve=self.reserve):
                    self.held_back += 1
                    continue
                self.allowance.spend(entry.cost)
            for subject in subjects:
                entry.due_at[subject] = now + entry.every_ns
            out.append((entry.dataset, subjects))
        return out

    async def tick(self) -> int:
        """Each read due, made; a read that fails is said and its subjects
        stay due at their cadence. How many reads were made."""
        made = 0
        for dataset, subjects in await self.due():
            read = self.entries[dataset].read
            if read is None:
                continue
            try:
                await read(subjects)
            except Exception as failed:  # noqa: BLE001 - said; due again at its cadence
                log.warning("the timetable's read of %s failed: %s", dataset, failed)
            made += 1
            self.reads += 1
        return made
