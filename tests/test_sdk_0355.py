"""SDK 0.35.5 (ruling 1072, question 455): the FX week, once, in
`helpers.sessions`, as the step 3a samples kept it (plugin-sample-fx's
`model.FX_WEEK`, plugin-sample-multi-asset's `desk.FX_WEEK`).

Sunday 17:00 to Friday 17:00 New York, the 17:00 roll at each edge, in New
York's own time: on both sides of daylight saving the edges stay at 17:00
there and move in UTC. Usable wherever trading sessions are: a live value
out of it is closed, never stale; the pre-trade check counts nothing there.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from meridian import LiveValue
from meridian.helpers import sessions
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import ems, in_session

S = 1_000_000_000
NEW_YORK = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def ny(*when: int) -> int:
    return int(datetime(*when, tzinfo=NEW_YORK).timestamp()) * S


def utc(*when: int) -> int:
    return int(datetime(*when, tzinfo=UTC).timestamp()) * S


@pytest.mark.parametrize(
    ("at", "open_"),
    [
        (ny(2026, 11, 4, 12), True),  # Wednesday noon
        (ny(2026, 11, 7, 12), False),  # Saturday
        (ny(2026, 11, 6, 16, 59), True),  # Friday before the roll
        (ny(2026, 11, 6, 17, 0), False),  # Friday at the roll: closed
        (ny(2026, 11, 8, 16, 59), False),  # Sunday before the roll
        (ny(2026, 11, 8, 17, 0), True),  # Sunday at the roll: open
        (ny(2026, 11, 9, 0, 0), True),  # Monday's midnight, the week running
        (ny(2026, 11, 5, 23, 59), True),  # Thursday night into Friday
    ],
)
def test_the_fx_week_is_sunday_to_friday_17_00_new_york(at: int, open_: bool) -> None:
    assert in_session(sessions.FX_WEEK, at) is open_


def test_the_roll_stays_at_17_00_new_york_on_both_sides_of_daylight_saving() -> None:
    # Summer (EDT, UTC-4): the week opens at 21:00 UTC, closes at 21:00 UTC.
    assert not in_session(sessions.FX_WEEK, utc(2026, 3, 8, 20, 59))  # DST began 03-08
    assert in_session(sessions.FX_WEEK, utc(2026, 3, 8, 21, 0))
    assert in_session(sessions.FX_WEEK, utc(2026, 10, 30, 20, 59))
    assert not in_session(sessions.FX_WEEK, utc(2026, 10, 30, 21, 0))
    # Winter (EST, UTC-5): at 22:00 UTC.
    assert in_session(sessions.FX_WEEK, utc(2026, 3, 6, 21, 59))
    assert not in_session(sessions.FX_WEEK, utc(2026, 3, 6, 22, 0))
    assert not in_session(sessions.FX_WEEK, utc(2026, 11, 1, 21, 59))  # DST ended 11-01
    assert in_session(sessions.FX_WEEK, utc(2026, 11, 1, 22, 0))


def test_a_live_value_out_of_the_fx_week_is_closed_never_stale() -> None:
    wednesday, saturday = ny(2026, 11, 4, 12), ny(2026, 11, 7, 12)
    weekday = LiveValue(
        "pair:EUR/USD",
        {"mid": "1.16010"},
        confirmed_ns=wednesday - 60 * S,
        stale_at_ns=wednesday - 50 * S,
        sessions=sessions.FX_WEEK,
    )
    assert weekday.stale(wednesday) and not weekday.closed(wednesday)
    weekend = LiveValue(
        "pair:EUR/USD",
        {"mid": "1.16010"},
        confirmed_ns=saturday - 60 * S,
        stale_at_ns=saturday - 50 * S,
        sessions=sessions.FX_WEEK,
    )
    assert weekend.closed(saturday) and not weekend.stale(saturday)
    assert weekend.to_json(saturday)["closed"] is True
    # Through LiveValue.of, as a page gives it.
    quote = ops.Quote(
        meta=ops.ObservationMeta(
            source=ops.Source(dataset="quotes"), valid_from_ns=saturday - 3600 * S
        )
    )
    made = LiveValue.of("pair:EUR/USD", {}, [quote], sessions=sessions.FX_WEEK)
    assert made.sessions is sessions.FX_WEEK and made.closed(saturday)


def test_the_pre_trade_check_counts_nothing_out_of_the_fx_week() -> None:
    saturday = ny(2026, 11, 7, 12)
    old = ops.Quote(meta=ops.ObservationMeta(valid_from_ns=saturday - 3600 * S))
    ref = ops.DatasetRef(dataset="quotes", stale_after_ns=5 * S)
    check = ems.ReferenceCheck(clock_ns=lambda: saturday)
    assert check.stale(old, dataset=ref, sessions=sessions.FX_WEEK) is None
    tuesday = ny(2026, 11, 10, 12)
    check = ems.ReferenceCheck(clock_ns=lambda: tuesday)
    stale = check.stale(old, dataset=ref, sessions=sessions.FX_WEEK)
    assert stale is not None
