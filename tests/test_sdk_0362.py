"""SDK 0.36.2: the row-key rule in the SDK's helpers (spec/the-lake rule 5,
ruled 2026-11-12): a row key fixes its valid time and its first subject, so
no helper restates a key under another valid time."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from meridian.helpers import chains
from meridian.helpers.calendars import DayClock
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.roles.data import option_chains
from meridian.suites import Recorder

NS = 1_000_000_000
OSI = "SPY   261120C00500000"
#: Midnight beginning 2026-11-11 in New York (EST, UTC-5), in ns.
NOV_11_NY = int(dt.datetime(2026, 11, 11, 5, tzinfo=dt.UTC).timestamp()) * NS


# ── 1. helpers.statistic: valid from the start of the day it describes ──


def _stat(**more: Any) -> Any:
    return chains.statistic(
        "INS-SPY", chains.osi_key(OSI), "open_interest", 1200, "2026-11-11",
        dataset="tradier-1:options", **more,
    )  # fmt: skip


def test_a_statistic_is_valid_from_the_start_of_its_day_in_new_york() -> None:
    stat = _stat()
    assert stat.meta is not None and stat.meta.valid_from_ns == NOV_11_NY
    assert stat.meta.row_key == f"{OSI}:2026-11-11:OI"


def test_a_statistic_read_or_published_later_keeps_its_valid_time() -> None:
    """A re-read or a republication restates the value only: whatever the
    plugin passes as `valid_from_ns` (the read's or the publication's time,
    0.36.1's plugins), the row's valid time is its day's start."""
    read = _stat(valid_from_ns=NOV_11_NY + 30 * 3600 * NS)
    republished = _stat(valid_from_ns=NOV_11_NY + 55 * 3600 * NS)
    assert read.meta is not None and republished.meta is not None
    assert read.meta.valid_from_ns == republished.meta.valid_from_ns == NOV_11_NY


def test_a_statistic_takes_its_datasets_day() -> None:
    tokyo = _stat(day_clock=DayClock("Asia/Tokyo"))
    midnight = int(dt.datetime(2026, 11, 10, 15, tzinfo=dt.UTC).timestamp()) * NS
    assert tokyo.meta is not None and tokyo.meta.valid_from_ns == midnight


class _Days:
    """A calendar open every day, in New York's day."""

    day_clock = DayClock("America/New_York")

    async def previous_open(self, day: dt.date) -> dt.date:
        return day - dt.timedelta(days=1)

    async def is_open(self, day: dt.date) -> bool:
        return True


class _Chain:
    def __init__(self) -> None:
        self.options = [
            option_chains.ChainOption(
                OSI, dt.date(2026, 11, 20), open_interest=Decimal(1200), volume=Decimal(40)
            )
        ]

    def expirations(self, symbol: str) -> list[dt.date]:
        return [dt.date(2026, 11, 20)]

    def chain(self, symbol: str, expiration: dt.date) -> list[option_chains.ChainOption]:
        return self.options


def _want(data_type: str, want_id: str = "WNT-1") -> Heard[ops.ObservationsWantedEvent]:
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset="chains-1:options",
            data_type=data_type,
            subjects=[ops.SubjectRef(entity_id="INS-SPY")],
        ),
    )


def _feed(clock: list[int], source: Any = None, **more: Any) -> tuple[Any, Recorder]:
    recorder = Recorder("chains-1")

    async def symbol_of(subject: str) -> str:
        return "SPY"

    feed = recorder.bind(
        option_chains.Feed(
            source or _Chain(), market_days=_Days(), symbol_of=symbol_of,
            clock_ns=lambda: clock[0], **more,
        )
    )  # fmt: skip
    return feed, recorder


async def test_the_chains_feed_dates_a_statistic_by_its_day_never_its_read() -> None:
    """Read at 10:00 and again at 15:00 New York on 2026-11-12: open interest
    for 2026-11-11 and volume for 2026-11-12, each valid from its day's
    start, the second read the same valid times."""
    clock = [NOV_11_NY + 34 * 3600 * NS]
    feed, recorder = _feed(clock)
    await feed.on_observations_wanted(_want(option_chains.STATISTIC))
    clock[0] += 5 * 3600 * NS
    await feed.on_observations_wanted(_want(option_chains.STATISTIC))
    sent = [s for call in recorder.on("RecordStatistics") for s in call.statistics]
    assert len(sent) == 4, "a reader waiting is answered each time"
    starts = {s.meta.row_key: s.meta.valid_from_ns for s in sent}
    assert starts == {
        f"{OSI}:2026-11-11:OI": NOV_11_NY,
        f"{OSI}:2026-11-12:VOL": NOV_11_NY + 24 * 3600 * NS,
    }
    assert {s.meta.row_key: s.meta.valid_from_ns for s in sent[2:]} == starts
