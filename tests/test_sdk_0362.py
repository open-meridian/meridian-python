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


# ── 2. helpers.option_series: terms keep their first valid time ─────────


def _series(**more: Any) -> Any:
    return chains.option_series(
        "INS-SPY", OSI, template_id="TPL-listed-option", template_version="1",
        dataset="chains-1:options", currency="USD", exercise_style="EXERCISE_STYLE_AMERICAN",
        settlement_method="SETTLEMENT_METHOD_PHYSICAL", **more,
    )  # fmt: skip


def test_an_adjusted_series_is_a_new_key_from_its_date() -> None:
    first = _series(valid_from_ns=7, deliverable=[("INS-SPY", 100)])
    adjusted = _series(
        valid_from_ns=99, deliverable=[("INS-SPY", 150)], adjusted_on=dt.date(2026, 11, 11)
    )
    assert first.meta is not None and adjusted.meta is not None
    assert (first.meta.row_key, first.meta.valid_from_ns) == (OSI, 7)
    assert adjusted.meta.row_key == f"{OSI}:2026-11-11:ADJ"
    assert adjusted.meta.valid_from_ns == NOV_11_NY, "the date's start, never the time passed"
    assert adjusted.meta.series_key == first.meta.series_key
    tokyo = _series(adjusted_on="2026-11-11", day_clock=DayClock("Asia/Tokyo"))
    assert tokyo.meta is not None and tokyo.meta.valid_from_ns == NOV_11_NY - 14 * 3600 * NS


def _sent_series(recorder: Recorder) -> list[Any]:
    return [s for call in recorder.on("RecordSeries") for s in call.series]


async def test_a_series_sent_again_after_a_restart_keeps_its_first_valid_time(
    tmp_path: Any,
) -> None:
    kept = tmp_path / "series.json"
    clock = [NOV_11_NY + 34 * 3600 * NS]
    feed, recorder = _feed(clock, series_path=kept)
    await feed.on_observations_wanted(_want(option_chains.SERIES))
    first = clock[0]
    # Restarted the next day: nothing sent unasked, a reader waiting answered
    # under the first valid time.
    clock[0] += 24 * 3600 * NS
    again, recorder2 = _feed(clock, series_path=kept)
    await again.on_observations_wanted(_want(option_chains.SERIES, want_id=""))
    assert _sent_series(recorder2) == [], "the terms as last sent"
    await again.on_observations_wanted(_want(option_chains.SERIES))
    (sent,) = _sent_series(recorder2)
    assert (sent.meta.row_key, sent.meta.valid_from_ns) == (OSI, first)
    assert [s.meta.valid_from_ns for s in _sent_series(recorder)] == [first]


async def test_a_series_whose_terms_change_is_adjusted_under_a_new_key(tmp_path: Any) -> None:
    source = _Chain()
    clock = [NOV_11_NY + 34 * 3600 * NS]
    feed, recorder = _feed(clock, source, series_path=tmp_path / "series.json")
    await feed.on_observations_wanted(_want(option_chains.SERIES))
    from dataclasses import replace

    clock[0] += 24 * 3600 * NS
    source.options = [replace(source.options[0], standard=False, multiplier=Decimal(150))]
    await feed.on_observations_wanted(_want(option_chains.SERIES, want_id=""))
    first, adjusted = _sent_series(recorder)
    assert first.meta.row_key == OSI
    assert adjusted.meta.row_key == f"{OSI}:2026-11-13:ADJ"
    assert adjusted.meta.valid_from_ns == NOV_11_NY + 2 * 24 * 3600 * NS
    # Read again, the adjusted terms are as last sent.
    await feed.on_observations_wanted(_want(option_chains.SERIES, want_id=""))
    assert len(_sent_series(recorder)) == 2


async def test_a_resend_refused_for_its_valid_time_is_taken_as_recorded(caplog: Any) -> None:
    """The plugin's storage lost: the lake holds the series under another
    first valid time and refuses the re-send naming it (stage H); the feed
    takes it as recorded, says so once and sends the rest of the batch."""
    from meridian.errors import CallFailed

    source = _Chain()
    other = "SPY   261120P00500000"
    source.options = [*source.options, option_chains.ChainOption(other, dt.date(2026, 11, 20))]
    feed, recorder = _feed([NOV_11_NY + 34 * 3600 * NS], source)
    answered: list[list[str]] = []

    def refuse(params: Any) -> Any:
        keys = [s.meta.row_key for s in params.series]
        answered.append(keys)
        if OSI in keys:
            at = keys.index(OSI)
            raise CallFailed(
                "RecordSeries", "invalid", "a row key fixes its valid time",
                fields=(f"series[{at}].meta.valid_from_ns",),
            )  # fmt: skip
        return ops.RecordSeriesResult(recorded=len(keys))

    recorder.answer("RecordSeries", refuse)
    for _ in range(2):
        await feed.on_observations_wanted(_want(option_chains.SERIES))
    assert answered == [[OSI, other], [other], [OSI, other], [other]]
    assert feed.counts.unchanged == 2 and feed.counts.recorded == 2
    said = [r for r in caplog.records if "taken as recorded" in r.getMessage()]
    assert len(said) == 1, "said once per series"


async def test_a_batch_the_lake_has_keeps_its_times_when_a_later_one_fails(
    monkeypatch: Any,
) -> None:
    """The review of #51: series sent in two batches, the second failing.
    The first batch's first valid times are kept, the lake having them; the
    second's are not, so its series are first seen again next pass."""
    from meridian.errors import CallFailed

    monkeypatch.setattr(option_chains, "BATCH", 1)
    source = _Chain()
    other = "SPY   261120P00500000"
    source.options = [*source.options, option_chains.ChainOption(other, dt.date(2026, 11, 20))]
    clock = [NOV_11_NY + 34 * 3600 * NS]
    feed, recorder = _feed(clock, source)
    calls: list[list[str]] = []

    def second_fails(params: Any) -> Any:
        calls.append([s.meta.row_key for s in params.series])
        if len(calls) == 2:
            raise CallFailed("RecordSeries", "unavailable", "the lake is restarting")
        return ops.RecordSeriesResult(recorded=len(params.series))

    recorder.answer("RecordSeries", second_fails)
    import pytest

    with pytest.raises(CallFailed):
        await feed.on_observations_wanted(_want(option_chains.SERIES, want_id=""))
    kept = feed._first_times
    assert kept.get("chains-1:options", OSI)["valid_from_ns"] == clock[0]
    assert kept.get("chains-1:options", other) is None and not kept.staged
    clock[0] += 3600 * NS
    await feed.on_observations_wanted(_want(option_chains.SERIES, want_id=""))
    assert calls[2:] == [[other]], "only the series the lake did not have"


async def test_another_refusal_of_a_series_is_raised() -> None:
    from meridian.errors import CallFailed

    feed, recorder = _feed([NOV_11_NY + 34 * 3600 * NS])

    def refuse(params: Any) -> Any:
        raise CallFailed("RecordSeries", "invalid", "no", fields=("series[0].template_id",))

    recorder.answer("RecordSeries", refuse)
    import pytest

    with pytest.raises(CallFailed):
        await feed.record(
            await feed.underlying("INS-SPY"), option_chains.SERIES,
            frozenset({dt.date(2026, 11, 20)}), frozenset(), "WNT-1",
        )  # fmt: skip
    assert feed._first_times.get("chains-1:options", OSI) is None, "staged, not kept"


# ── 3. event_contracts.Feed.outcome: the first determination's valid time ─


async def test_an_amended_outcome_keeps_its_first_determinations_valid_time() -> None:
    """Proposed, then determined, an amendment, a dispute and final: each a
    new version of `<code>:outcome`, every one valid from the first
    determination, each its own determination's time as its event time."""
    from fake_venues import NOW_NS, ContractsMarket, contracts_venue
    from meridian.roles.data import event_contracts as ec
    from meridian.roles.data.testing import Lake

    first, amended = NOW_NS - 3600 * NS, NOW_NS - 600 * NS
    yes = ("fakev:result", "yes", "Yes")
    stages = [
        ec.Resolution(ec.PROPOSED, Decimal(1), *yes, determined_at_ns=first),
        ec.Resolution(ec.DETERMINED, Decimal(1), *yes, determined_at_ns=first),
        ec.Resolution(
            ec.DETERMINED, Decimal(0), "fakev:result", "no", "No", determined_at_ns=amended
        ),
        ec.Resolution(ec.DISPUTED, None),
        ec.Resolution(ec.FINAL, Decimal(0), "fakev:result", "no", "No"),
    ]

    class Staged(ContractsMarket):
        def _resolved(self) -> ec.Resolution:
            return stages[0]

    lake = Lake(contracts_venue.VENUE)
    market = Staged(NOW_NS)
    feed = lake.bind(ec.Feed(market, ec.ContractMap(), clock_ns=lambda: NOW_NS))
    subject = await lake.held(feed, "RESOLVED-1")
    await feed.record_live([subject], data_type="meridian.v1.Price")
    while len(stages) > 1:
        stages.pop(0)
        assert await feed.watch_outcomes() == 1
    rows = lake.rows("RecordOutcomes")
    assert [ops.OutcomeStage.Name(r.stage)[14:] for r in rows] == [
        "PROPOSED", "DETERMINED", "DETERMINED", "DISPUTED", "FINAL",
    ]  # fmt: skip
    assert {r.meta.row_key for r in rows} == {"RESOLVED-1:outcome"}
    assert {r.meta.valid_from_ns for r in rows} == {first}, "the first determination's"
    events = [[t.at_ns for t in r.meta.source_times] for r in rows]
    assert events == [[first], [first], [amended], [amended], [amended]]
    held = feed.contracts.outcomes["RESOLVED-1"]
    assert (held.valid_from_ns, held.determined_at_ns) == (first, amended)


def test_an_outcome_map_kept_before_0362_still_loads(tmp_path: Any) -> None:
    import json

    from meridian.roles.data import event_contracts as ec

    path = tmp_path / "contracts-live.json"
    before = {
        "stage": "final", "value": "1", "scheme": "s", "word": "yes", "text": "Yes",
        "settled_at_ns": 0, "valid_from_ns": 5, "stated": True, "raw_key": "r",
    }  # fmt: skip
    path.write_text(json.dumps({"outcomes": {"C-1": before}}), encoding="utf-8")
    kept = ec.ContractMap(path)
    assert kept.load() and kept.outcomes["C-1"].determined_at_ns == 0


# ── 4. listings.Feed.trade_row: a withdrawal keeps its trade's valid time ─


def _listings() -> tuple[Any, Recorder]:
    from meridian.roles.data import listings

    class Lake(listings.Feed):
        source_name = "brokerage"

        def attributes(self, stated: Any) -> Any:
            return listings.Attributes((), (True,) * 4, (True,) * 4)

    recorder = Recorder("brokerage-1")
    feed = recorder.bind(Lake(None, listings.Listings(None), clock_ns=lambda: AFTERNOON))
    return feed, recorder


SPY_ID = "INS-01J8XQ4M7K00000000000SPY"
#: 14:00 New York on 2026-11-12 (EST), in ns.
AFTERNOON = NOV_11_NY + 38 * 3600 * NS


def _withdrawal(at_ns: int) -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(
        symbol="SPY", at_ns=at_ns, venue_code="", price=Decimal(1), quantity=Decimal(1),
        cancelled=True, raw_key="stream/9", unconverted=(), row_key="SPY:t:7",
    )  # fmt: skip


async def test_a_withdrawal_of_a_trade_not_held_takes_the_trades_valid_time() -> None:
    """The trade printed at 13:20, recorded before a restart; its withdrawal
    heard at 14:00 is sent valid from 13:20, read from the lake by its key,
    the reads narrowed back from the withdrawal within one business day."""
    feed, recorder = _listings()
    printed = AFTERNOON - 40 * 60 * NS
    key = f"SPY:t:7@{SPY_ID}"
    others = [ops.Trade(meta=ops.ObservationMeta(row_key=f"SPY:t:{n}@{SPY_ID}")) for n in "12"]

    def held(params: Any) -> Any:
        if params.valid_from_ns <= printed < params.valid_until_ns:
            if not params.cursor:
                return ops.ListTradesResult(trades=others, next_cursor="2")
            found = ops.Trade(meta=ops.ObservationMeta(row_key=key, valid_from_ns=printed))
            return ops.ListTradesResult(trades=[found])
        return ops.ListTradesResult()

    recorder.answer("ListTrades", held)
    row = await feed.trade_row(_withdrawal(AFTERNOON), SPY_ID)
    assert row is not None and row.cancelled
    assert row.meta.valid_from_ns == printed, "the trade's, never the withdrawal's"
    asked = recorder.on("ListTrades")
    assert [a.valid_until_ns - a.valid_from_ns for a in asked[:2]] == [60 * NS + 1, 3540 * NS]
    assert list(asked[0].sources.named) == ["brokerage-1:trades"]
    assert all(a.valid_until_ns - a.valid_from_ns <= 24 * 3600 * NS for a in asked)


async def test_a_withdrawal_of_a_trade_the_lake_does_not_hold_is_unmatched() -> None:
    """Nothing is restated under a new valid time: the lake answering no
    such trade back to the business day before, or refusing the read, the
    withdrawal is counted unmatched and not sent."""
    from meridian.errors import CallFailed
    from meridian.roles.data import listings

    feed, recorder = _listings()
    assert await feed.trade_row(_withdrawal(AFTERNOON), SPY_ID) is None
    asked = recorder.on("ListTrades")
    earliest = min(a.valid_from_ns for a in asked)
    assert earliest == listings.previous_close_of(dt.date(2026, 11, 11))
    for a in asked:
        day = listings.previous_close_of(listings._business_date(a.valid_until_ns - 1))
        assert a.valid_from_ns >= day, "each read within one business day"

    def refuse(params: Any) -> Any:
        raise CallFailed("ListTrades", "refused", "not entitled")

    recorder.answer("ListTrades", refuse)
    assert await feed.trade_row(_withdrawal(AFTERNOON), SPY_ID) is None
    assert feed.counts[listings.TRADES].unmatched == 2
    assert recorder.on("RecordTrades") == []
