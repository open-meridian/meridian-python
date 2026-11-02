"""The option chains, as the plugin kept them by hand: the rows sent only
when changed, and the market's days read from the deployment's calendar."""

import datetime as dt
from collections import OrderedDict
from typing import Any

from meridian.errors import MeridianError
from meridian.plugin.v1 import operations_pb2 as ops

#: How many rows' last sendings are remembered, to send only what changed.
REMEMBERED = 200_000
SERIES = "meridian.v1.ListedSeries"


class Chains:
    """The chains wanted of `lake`, read from its source and recorded."""

    def __init__(self, lake: Any) -> None:
        self.lake = lake
        #: Each row's last sending, by (data type, dataset, row key).
        self.sent: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        self.days: dict[dt.date, bool] = {}
        self.calendar_error = ""

    def fresh(self, dataset: str, rows: list[tuple[str, str]]) -> list[str]:
        """The series whose terms changed since they were last sent."""
        return [key for key, terms in rows if self._changed(SERIES, dataset, key, terms)]

    async def is_open(self, day: dt.date) -> bool | None:
        """Whether a day is a market day by the deployment's calendar."""
        if day in self.days:
            return self.days[day]
        try:
            answer = await self.lake.plugin.read_calendar(
                calendar_id="CAL-1", from_date=day, to_date=day
            )
        except MeridianError as failed:
            self.calendar_error = f"the calendar was not read: {failed}"
            return None
        weekends = {int(w) for weekend in answer.weekends for w in weekend.weekdays}
        self.days[day] = ops.WEEKDAY_MONDAY + day.weekday() not in weekends
        return self.days[day]

    # ── Recording (W10.4) ────────────────────────────────────────────────

    def _changed(self, data_type: str, dataset: str, row_key: str, said: str) -> bool:
        """Whether a row says something other than its last sending."""
        mark = (data_type, dataset, row_key)
        if self.sent.get(mark) == said:
            return False
        self.sent[mark] = said
        self.sent.move_to_end(mark)
        while len(self.sent) > REMEMBERED:
            self.sent.popitem(last=False)
        return True
