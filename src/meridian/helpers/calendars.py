"""A market's days and a dataset's day, shared by every role (SDK 0.35;
spec/each-role-is-one-generated-class, section 4, rulings 924, 1009, 1017
and 1023; the data-plugin fit review's section 1.6).

**A dataset's day** (`DayClock`): the declaration already states the day a
daily value's business date is in -- its `day_time_zone` and
`day_end_minute` -- so a plugin never recomputes 16:00 New York or 17:00 for
FX by hand. `DayClock.of(declaration)` reads them: business date D runs from
the end of D-1 to the end of D, its end `day_end_minute` minutes after local
midnight of D (0 for the next midnight, a UTC day's):

    clock = DayClock.of(DAILY)                 # America/New_York, 960
    clock.business_date_of(at_ns)              # the date a moment counts to
    clock.close_of(day), clock.opened_at(day)  # the day's end and start, ns

**A market's days** (`MarketDays`): the deployment's calendar
(`read_calendar`, W3.19), read through the role object the plugin gives it
(ruling 1023) -- whether a day is open, the open day before or after one,
and a moment's business date rolled to the next open day. A failed read is
said (`error`, for the Connection page) and read again after a `Backoff`
wait: never every call, and never not at all (three plugins' copies did one
or the other). An EU or Asian market is a declaration and a calendar ID,
never a code change.
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from collections.abc import Callable
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .sessions import Backoff

__all__ = ["DayClock", "MarketDays"]

log = logging.getLogger("meridian.helpers.calendars")

NS = 1_000_000_000
DAY_MINUTES = 24 * 60


class DayClock:
    """A dataset's business day: its zone and the minute it ends (see the
    module)."""

    def __init__(self, time_zone: str, end_minute: int = 0) -> None:
        if not time_zone:
            raise ValueError("a day clock names its day_time_zone")
        try:
            self.zone = ZoneInfo(time_zone)
        except (ZoneInfoNotFoundError, ValueError) as unknown:
            raise ValueError(f"the day_time_zone {time_zone!r} is no IANA zone") from unknown
        if not 0 <= end_minute < DAY_MINUTES:
            raise ValueError(f"the day_end_minute is 0 to {DAY_MINUTES - 1}: {end_minute}")
        self.time_zone = time_zone
        self.end_minute = end_minute

    @classmethod
    def of(cls, declaration: Any) -> DayClock:
        """The day a dataset's declaration states (its `day_time_zone` and
        `day_end_minute`); refused where it states no zone."""
        zone = getattr(declaration, "day_time_zone", "")
        if not zone:
            key = getattr(declaration, "key", "?")
            raise ValueError(f"the dataset {key!r} states no day_time_zone")
        return cls(zone, int(getattr(declaration, "day_end_minute", 0)))

    def _end_minute(self) -> int:
        return self.end_minute or DAY_MINUTES

    def close_of(self, day: dt.date) -> int:
        """The moment business date `day` ends, in ns."""
        midnight = dt.datetime(day.year, day.month, day.day, tzinfo=self.zone)
        local = midnight.replace(tzinfo=None) + dt.timedelta(minutes=self._end_minute())
        return int(local.replace(tzinfo=self.zone).timestamp()) * NS

    def opened_at(self, day: dt.date) -> int:
        """The moment business date `day` begins: the previous date's end."""
        return self.close_of(day - dt.timedelta(days=1))

    def business_date_of(self, at_ns: int) -> dt.date:
        """The business date a moment counts to: the day whose span holds it,
        a moment at a day's end being the next day's first."""
        local = dt.datetime.fromtimestamp(at_ns / NS, self.zone)
        day = local.date()
        if self.end_minute and at_ns >= self.close_of(day):
            return day + dt.timedelta(days=1)
        return day


class MarketDays:
    """The deployment's calendar `calendar_id`, read through `role` -- any
    role object holding `read_calendar` (see the module). Days are read a
    span at a time around the day asked and kept; `day_clock` dates a
    moment (UTC dates without one)."""

    #: How far around the day asked a read reaches, in days.
    SPAN_DAYS = 31

    def __init__(
        self,
        role: Any,
        calendar_id: str,
        *,
        day_clock: DayClock | None = None,
        backoff: Backoff | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not calendar_id:
            raise ValueError("market days name their calendar (its CAL- ID)")
        self.role = role
        self.calendar_id = calendar_id
        self.day_clock = day_clock
        self.backoff = backoff or Backoff(first_s=5, most_s=600, jitter=0.2, steady_s=0)
        self._clock = clock
        #: Each day read, open or not.
        self.days: dict[dt.date, bool] = {}
        #: Why the last read failed, "" once one answers.
        self.error = ""
        self._again_at = 0.0

    async def _read(self, day: dt.date) -> bool:
        """The span around `day` read; whether it was."""
        now = self._clock()
        if now < self._again_at:
            return False
        first = day - dt.timedelta(days=self.SPAN_DAYS)
        last = day + dt.timedelta(days=self.SPAN_DAYS)
        try:
            answer = await self.role.read_calendar(
                calendar_id=self.calendar_id, from_date=first, to_date=last
            )
        except Exception as failed:  # noqa: BLE001 - said, and read again later
            self.error = f"the calendar {self.calendar_id} was not read: {failed}"[:300]
            self._again_at = now + self.backoff.failed()
            log.warning("%s", self.error)
            return False
        if not answer.found:
            self.error = f"the calendar {self.calendar_id} is not held"
            self._again_at = now + self.backoff.failed()
            return False
        from ..plugin.v1 import operations_pb2 as ops

        self.error = ""
        self.backoff.steady()
        self._again_at = 0.0
        weekends = {int(w) for weekend in answer.weekends for w in weekend.weekdays}
        closed = {c.date for c in answer.days if c.kind == ops.CALENDAR_DAY_KIND_CLOSED}
        opened = {c.date for c in answer.days if c.kind == ops.CALENDAR_DAY_KIND_OPEN}
        each = first
        while each <= last:
            text = each.isoformat()
            weekday = ops.WEEKDAY_MONDAY + each.weekday()
            self.days[each] = text in opened or (text not in closed and weekday not in weekends)
            each += dt.timedelta(days=1)
        return True

    async def is_open(self, day: dt.date) -> bool | None:
        """Whether `day` is a business day; None where the calendar has not
        answered (said in `error`)."""
        if day not in self.days and not await self._read(day):
            return None
        return self.days.get(day)

    async def _step(self, day: dt.date, step: int) -> dt.date | None:
        each = day
        for _ in range(self.SPAN_DAYS * 2):
            each += dt.timedelta(days=step)
            held = await self.is_open(each)
            if held is None:
                return None
            if held:
                return each
        return None

    async def previous_open(self, day: dt.date) -> dt.date | None:
        """The last business day before `day`; None where not known."""
        return await self._step(day, -1)

    async def next_open(self, day: dt.date) -> dt.date | None:
        """The first business day after `day`; None where not known."""
        return await self._step(day, 1)

    async def business_date_of(self, at_ns: int) -> dt.date | None:
        """The business date a moment counts to: its date by the day clock,
        or the next business day where that is closed; None where not
        known."""
        if self.day_clock is not None:
            day = self.day_clock.business_date_of(at_ns)
        else:
            day = dt.datetime.fromtimestamp(at_ns / NS, dt.UTC).date()
        held = await self.is_open(day)
        if held is None:
            return None
        return day if held else await self.next_open(day)
