"""A venue's whole work by what it lists (0.30.0): `meridian.roles.data.pairs`
and `.event_contracts`, run against two made-up venues (tests/fake_venues.py)
through the data suite's producers a plugin runs (`meridian.roles.data.
testing`), and their pages drawn from the SDK's kind templates. The four
plugins that kept this work byte for byte now run the same checks against
their own conversions."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import meridian
from fake_venues import (
    HOUR,
    NOW_NS,
    BarsMarket,
    ContractsMarket,
    candle,
    contracts_catalogue,
    contracts_venue,
    contracts_venue_with,
    ny_day_starts,
    pairs_venue,
)
from fake_venues import (
    contracts_page as fake_page,
)
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles.data import event_contracts, pairs
from meridian.roles.data.testing import (
    EVENT_CONTRACTS_NOT_PRESENTED,
    PAIRS_NOT_PRESENTED,
    EventContractsChecks,
    Lake,
    event_contract_producers,
    hear,
    pairs_producers,
    wanted,
)
from meridian.suites import ANSWERED_BY_SDK, Recorder, names, run
from meridian.testing import PageClient

# ── The data suite, unchanged ───────────────────────────────────────────


def test_a_pairs_venue_passes_every_case_it_presents() -> None:
    v = pairs_venue
    skipped = {**PAIRS_NOT_PRESENTED, **v.NOT_PRESENTED}
    report = run("data", pairs_producers(v), not_presented=skipped, instance_id=v.VENUE)
    assert report.passed, report.failures
    assert len(report.passed_cases) == len(list(names("data"))) - len(skipped)
    assert set(names("data")) == set(pairs_producers(v)) | set(skipped) | set(ANSWERED_BY_SDK)


def test_an_event_contract_venue_passes_every_case_it_presents() -> None:
    v = contracts_venue
    made = event_contract_producers(v)
    skipped = {**EVENT_CONTRACTS_NOT_PRESENTED, **v.NOT_PRESENTED}
    report = run("data", made, not_presented=skipped, instance_id=v.VENUE)
    assert report.passed, report.failures
    assert set(names("data")) == set(made) | set(skipped) | set(ANSWERED_BY_SDK)


@pytest.mark.parametrize(
    ("case", "name", "mutated"),
    [
        (
            "an-exact-price",
            "close",
            lambda feed, mapped, candle: type(feed).close(
                feed, mapped, replace(candle, close=Decimal(float(candle.close)))
            ),
        ),
        (
            "a-stablecoin-quote",
            "_money",
            lambda feed, amount, mapped: meridian.Money(amount, "USD"),
        ),
        ("the-makers-side-inverted", "aggressor", lambda feed, seen: seen.side),
        (
            "a-one-sided-quote",
            "quote",
            lambda feed, mapped, best: type(feed).quote(
                feed, mapped, replace(best, ask=Decimal(0))
            ),
        ),
    ],
)
def test_a_pairs_plugin_doing_the_wrong_thing_fails_the_suite(
    case: str, name: str, mutated: Any
) -> None:
    v = pairs_venue
    made = pairs_producers(v, **{name: mutated})
    assert (
        case in run("data", made, not_presented=v.NOT_PRESENTED, instance_id=v.VENUE).failures
    )


@pytest.mark.parametrize(
    ("case", "name", "mutated"),
    [
        (
            "an-exact-price",
            "price",
            lambda feed, mapped, kind, amount, seen: type(feed).price(
                feed, mapped, kind, Decimal(float(amount)), seen
            ),
        ),
        (
            "a-quote-recorded",
            "quote",
            lambda feed, mapped, top: type(feed).quote(
                feed, mapped, replace(top, bid_size=None, ask_size=None)
            ),
        ),
        ("records-a-partial-payout", "_determination", lambda feed, value, contract: "pays"),
    ],
)
def test_an_event_contract_plugin_doing_the_wrong_thing_fails_the_suite(
    case: str, name: str, mutated: Any
) -> None:
    v = contracts_venue
    made = event_contract_producers(v, **{name: mutated})
    assert (
        case in run("data", made, not_presented=v.NOT_PRESENTED, instance_id=v.VENUE).failures
    )


# ── The work past the suite's cases ─────────────────────────────────────


def _pairs(lake: Recorder) -> pairs.Feed:
    return pairs.Feed(
        lake,
        pairs_venue.market(),
        pairs.ProductMap(),
        clock_ns=lambda: NOW_NS,
        stream_factory=pairs_venue.STREAM,
    )


async def test_a_pairs_feed_names_resolves_and_records_against_a_want() -> None:
    lake = Lake(pairs_venue.VENUE)
    feed = _pairs(lake)
    btc = await lake.held(feed, "BTC")
    await hear(
        lake,
        feed,
        wanted(feed, "WNT-1", pairs.DAILY, [btc, "LCL-NONE"], day=pairs_venue.CLOSED),
    )
    keys = sorted(r.meta.row_key for r in lake.rows())
    assert keys == ["BTC-USD:1d:1791417600", "BTC-USDC:1d:1791417600"]
    [declined] = lake.on("DeclineWant")
    assert [s.entity_id for s in declined.subjects] == ["LCL-NONE"]
    assert [h.want_id for h in feed.heard] == ["WNT-1"] and feed.heard[0].recorded == 2
    assert feed.sent_to(pairs.DAILY).recorded == 2 and feed.counts.declined == 1


async def test_a_pairs_feed_streams_what_stands_and_stops_when_withdrawn() -> None:
    lake = Lake(pairs_venue.VENUE)
    feed = _pairs(lake)
    btc = await lake.held(feed, "BTC")
    event = wanted(
        feed, "WNT-S", pairs.TRADES, [btc], data_type="meridian.v1.Trade", standing=True
    )
    await hear(lake, feed, event)
    assert sorted(feed.streams) == ["BTC-USD", "BTC-USDC"]
    assert feed.stream.health.state == "off" and feed.backfilled == {btc}
    lake.answer("WantWithdrawn", lambda _: [ops.WantWithdrawnEvent(want_id="WNT-S")])
    await lake.receive(want_withdrawn=feed.on_withdrawn)
    assert feed.streams == {} and not feed.standing


async def test_an_event_contract_feed_records_an_outcome_once_and_its_later_stages() -> None:
    lake = Lake(contracts_venue.VENUE)
    feed = event_contracts.Feed(
        lake, contracts_venue.market(), event_contracts.ContractMap(), clock_ns=lambda: NOW_NS
    )
    subject = await lake.held(feed, "RESOLVED-1")
    await feed.record_live([subject], data_type="meridian.v1.Price")
    assert await feed.watch_outcomes() == 0, "stated again unchanged: nothing sent"
    for stage in ("disputed", "final"):
        feed.market = contracts_venue.market(directory=stage)
        assert await feed.watch_outcomes() == 1
    stages = [ops.OutcomeStage.Name(r.stage) for r in lake.rows("RecordOutcomes")]
    assert stages == [
        "OUTCOME_STAGE_DETERMINED",
        "OUTCOME_STAGE_DISPUTED",
        "OUTCOME_STAGE_FINAL",
    ]
    assert feed.outcome_counts.recorded == 1 and feed.outcome_counts.restated == 2
    assert feed.counts.recorded == 3, "the live rows alone, apart from the outcomes"


class ChallengedMarket(ContractsMarket):
    """The made-up venue, its RESOLVED-1 proposed with a window to challenge
    it that ends at a time the venue reports."""

    CHALLENGE_ENDS_NS = NOW_NS + 2 * 3600 * 10**9

    def _resolved(self) -> event_contracts.Resolution:
        return replace(
            super()._resolved(),
            stage=event_contracts.PROPOSED,
            challenge_ends_at_ns=self.CHALLENGE_ENDS_NS,
        )


async def test_an_outcome_carries_the_venues_challenge_deadline_where_it_reports_one() -> None:
    """0.32.3: a resolution's `challenge_ends_at_ns`, where the venue reports
    one, reaches the Outcome recorded; unset by default."""
    assert event_contracts.Resolution(event_contracts.FINAL, None).challenge_ends_at_ns == 0
    ends_ns = ChallengedMarket.CHALLENGE_ENDS_NS
    for market, ends in ((ContractsMarket(NOW_NS), 0), (ChallengedMarket(NOW_NS), ends_ns)):
        lake = Lake(contracts_venue.VENUE)
        feed = event_contracts.Feed(
            lake, market, event_contracts.ContractMap(), clock_ns=lambda: NOW_NS
        )
        subject = await lake.held(feed, "RESOLVED-1")
        await feed.record_live([subject], data_type="meridian.v1.Price")
        (row,) = lake.rows("RecordOutcomes")
        assert row.challenge_ends_at_ns == ends


# ── A range market's bounds, and a record already complete (0.31.1) ────

FLOOR = event_contracts.Bound(Decimal("71.5"), inclusive=False)
CAP = event_contracts.Bound(Decimal("72.4900"), inclusive=True)


class RangeMarket(ContractsMarket):
    """The made-up venue, its BASE-1 a range market: 71.5 exclusive to 72.4900
    inclusive, in degrees, as Kalshi's `greater` and `less_or_equal` read."""

    def contract(self, code: str, watching: bool = False) -> event_contracts.Contract | None:
        read = super().contract(code, watching)
        if read is None or code != "BASE-1":
            return read
        return replace(read, floor=FLOOR, cap=CAP, bound_unit="degrees_f")


class RangeMarketWithoutMic(RangeMarket):
    """The same venue holding no ISO 10383 MIC: its ticker's source is its
    VEN- ID."""

    venue_identifiers = (("symbol", "fakev", "fakev"),)


def _ranged(market: type[ContractsMarket]) -> EventContractsChecks:
    checks = EventContractsChecks()
    checks.venue = SimpleNamespace(
        **{**vars(contracts_venue), "PAYOUT": "1.0000"},
    )
    checks.venue.market = lambda now_ns=NOW_NS, directory=None: market(now_ns, directory)
    return checks


@pytest.mark.parametrize("market", [RangeMarket, RangeMarketWithoutMic])
async def test_a_range_markets_bounds_are_kept_and_read_back_exactly(
    market: type[ContractsMarket], tmp_path: Path
) -> None:
    await _ranged(market).test_the_contract_map_is_kept_and_read_back(tmp_path)
    kept = json.loads((tmp_path / "contracts-synthetic.json").read_text())
    [held] = [c for c in kept["contracts"] if c["code"] == "BASE-1"]
    assert held["floor"] == {"value": "71.5", "inclusive": False}
    assert held["cap"] == {"value": "72.4900", "inclusive": True}
    assert held["bound_unit"] == "degrees_f"
    again = event_contracts.ContractMap(tmp_path / "contracts-synthetic.json")
    assert again.load()
    read = again.contracts["BASE-1"]
    assert (read.floor, read.cap, read.bound_unit) == (FLOOR, CAP, "degrees_f")
    assert str(read.cap.value) == "72.4900", "the bound's exact text, trailing zeros kept"


def test_a_contract_that_is_no_range_keeps_no_bounds(tmp_path: Path) -> None:
    kept = event_contracts.ContractMap(tmp_path / "contracts.json")
    plain = ContractsMarket().contract("BASE-1")
    assert plain is not None
    kept.contracts = {"BASE-1": plain, "TAIL-1": replace(plain, code="TAIL-1", floor=FLOOR)}
    kept.save()
    again = event_contracts.ContractMap(tmp_path / "contracts.json")
    assert again.load() and again.contracts == kept.contracts
    assert again.contracts["BASE-1"].floor is None and again.contracts["BASE-1"].cap is None
    assert again.contracts["TAIL-1"].cap is None, "an open tail has one bound only"


@pytest.mark.parametrize("market", [ContractsMarket, RangeMarket, RangeMarketWithoutMic])
async def test_a_record_holding_every_stated_identifier_is_not_resolved_again(
    market: type[ContractsMarket],
) -> None:
    await _ranged(market).test_a_record_already_complete_is_not_resolved_again()


async def test_a_mic_venues_record_holding_the_symbol_alone_is_not_complete() -> None:
    lake = Lake(contracts_venue.VENUE)
    feed = event_contracts.Feed(
        lake, contracts_venue.market(), event_contracts.ContractMap(), clock_ns=lambda: NOW_NS
    )
    contract = await feed.contract("BASE-1")
    assert contract is not None
    stated = await feed.stated_identifiers(contract)
    assert [(i.scheme, i.value, i.source) for i in stated] == [
        ("symbol", "BASE-1", "fakev"),
        ("ticker", "BASE-1", "XFKE"),
    ]
    subject = lake.instruments.hold(
        "INS-HALF", *feed.identifiers(contract),
        asset_class=ops.ASSET_CLASS_EVENT_CONTRACT,
        instrument_type=ops.INSTRUMENT_TYPE_BINARY_EVENT_CONTRACT,
    )  # fmt: skip
    await feed.record_live([subject], data_type="meridian.v1.Price")
    assert [r for r in lake.on("ResolveIdentifier") if r.stated_instrument_type], (
        "the ticker is reported beside the symbol the record holds"
    )


async def _ticker_source(feed: event_contracts.Feed) -> str:
    """The source a venue's ticker carries: its MIC, or its VEN- ID."""
    return feed._mic() or await feed.venue_id()


@pytest.mark.parametrize("market", [ContractsMarket, RangeMarketWithoutMic])
async def test_the_stated_ticker_names_the_mic_or_else_the_venue_masters_id(
    market: type[ContractsMarket],
) -> None:
    lake = Lake(contracts_venue.VENUE)
    feed = event_contracts.Feed(
        lake, market(NOW_NS), event_contracts.ContractMap(), clock_ns=lambda: NOW_NS
    )
    contract = await feed.contract("BASE-1")
    assert contract is not None
    [_, ticker] = await feed.stated_identifiers(contract)
    expected = "XFKE" if market is ContractsMarket else await feed.venue_id()
    assert (ticker.scheme, ticker.value, ticker.source) == ("ticker", "BASE-1", expected)
    assert market is ContractsMarket or expected.startswith("VEN-"), "Polymarket's shape"


@pytest.mark.parametrize("market", [ContractsMarket, RangeMarketWithoutMic])
async def test_a_record_holding_the_venues_ticker_alone_is_named_by_it(
    market: type[ContractsMarket],
) -> None:
    """A record the platform minted with the ticker alone (ruling 312): the
    venue's own code, matched whether its source is the MIC or the VEN- ID,
    and the symbol reported beside it."""
    lake = Lake(contracts_venue.VENUE)
    feed = event_contracts.Feed(
        lake, market(NOW_NS), event_contracts.ContractMap(), clock_ns=lambda: NOW_NS
    )
    source = await _ticker_source(feed)
    subject = lake.instruments.hold(
        "INS-MINTED", ops.Identifier(scheme="ticker", value="BASE-1", source=source),
        asset_class=ops.ASSET_CLASS_EVENT_CONTRACT,
        instrument_type=ops.INSTRUMENT_TYPE_BINARY_EVENT_CONTRACT,
    )  # fmt: skip
    declined = await feed.record_live([subject], data_type="meridian.v1.Price")
    assert not declined and feed.contracts.subjects == {subject: "BASE-1"}
    [joined] = [r for r in lake.on("ResolveIdentifier") if r.stated_instrument_type]
    named = {(i.scheme, i.value, i.source) for i in joined.identifiers}
    assert ("symbol", "BASE-1", "fakev") in named and ("ticker", "BASE-1", source) in named


async def test_another_venues_ticker_is_not_this_venues_code() -> None:
    lake = Lake(contracts_venue.VENUE)
    feed = event_contracts.Feed(
        lake, contracts_venue.market(), event_contracts.ContractMap(), clock_ns=lambda: NOW_NS
    )
    subject = lake.instruments.hold(
        "INS-ELSEWHERE", ops.Identifier(scheme="ticker", value="BASE-1", source="XOTH"),
        asset_class=ops.ASSET_CLASS_EVENT_CONTRACT,
        instrument_type=ops.INSTRUMENT_TYPE_BINARY_EVENT_CONTRACT,
    )  # fmt: skip
    await feed.record_live([subject], data_type="meridian.v1.Price")
    assert feed.contracts.subjects == {}
    assert feed.unnamed[subject] == event_contracts.NOT_A_CONTRACT


# ── The pages, from the kind templates ──────────────────────────────────

CATALOGUE = [
    meridian.DatasetDeclaration(
        key=key,
        vendor="Fake",
        data_types=["meridian.v1.Price"],
        modes=["pull"],
        cadence=1,
        history=0,
        licence_default=meridian.DatasetLicence(kept=True),
        day_time_zone="Etc/UTC",
        day_end_minute=0,
    )
    for key in ("daily", "live", "trades")
]


def _pairs_pages(feed: pairs.Feed | None) -> meridian.Pages:
    pages = meridian.Pages("Fake Exchange", kit="0.12.0")

    @pages.page(
        "/", "Connection", levels="admin", answers=pairs.ConnectionRead, name="read_connection"
    )
    def connection(request: meridian.Request) -> meridian.Response:
        return pages.answer(
            "meridian/roles/data/pairs/connection.html",
            pairs.connection_read(feed, "Fake Exchange", "Public"),
        )

    @pages.page(
        "/datasets",
        "Datasets",
        levels="admin",
        answers=pairs.DatasetsRead,
        name="read_datasets",
    )
    def datasets(request: meridian.Request) -> meridian.Response:
        read = pairs.datasets_read(feed, CATALOGUE, "fakex", "Public")
        return pages.answer(
            "meridian/roles/data/pairs/datasets.html", read, venue="Fake Exchange"
        )

    return pages


def test_a_pairs_venues_pages_hold_the_roles_sections_and_its_own() -> None:
    import asyncio

    lake = Lake(pairs_venue.VENUE)
    feed = _pairs(lake)

    async def worked() -> None:
        btc = await lake.held(feed, "BTC")
        for want_id, key, standing in (
            ("WNT-1", pairs.DAILY, False),
            ("WNT-2", pairs.LIVE, True),
        ):
            day = None if standing else pairs_venue.CLOSED
            await hear(
                lake, feed, wanted(feed, want_id, key, [btc], day=day, standing=standing)
            )

    asyncio.run(worked())
    client = PageClient(_pairs_pages(feed))
    connection = client.get("/", "admin").text
    # A polled venue has no session: no "Sessions" section (0.32.2).
    assert re.findall(r"<h2>([^<]*)</h2>", connection) == [
        "Key",
        "Limits and use",
        "Stream",
    ]
    assert "No key needed" in connection and "Venue" in connection
    shown = client.get("/datasets", "admin").text
    assert re.findall(r"<h2>([^<]*)</h2>", shown) == [
        "Served",
        "Wants",
        "Subjects",
        "Fake Exchange",
    ]
    assert '<om-pager search="Search wants"><table class="one-line">' in shown
    assert "2 of 5 products mapped, for 1 subject" in shown and "Kept current" in shown
    data = client.call_tool("read_datasets", level="admin").data
    assert [(w["want_id"], w["kept_current"]) for w in data["wants"]] == [
        ("WNT-2", True),
        ("WNT-1", False),
    ]
    figures = pairs.figures_read(feed, CATALOGUE)
    assert [f.label for f in figures] == [
        "Connection",
        "Entitled at the vendor",
        "Stream",
        "Last recorded",
    ]


def test_a_plugin_not_started_shows_its_next_step() -> None:
    client = PageClient(_pairs_pages(None))
    shown = client.get("/datasets", "admin").text
    assert "No wants yet" in shown and "<om-pager" not in shown
    assert client.call_tool("read_connection", level="admin").data["mode"] == "Live"
    assert [f.value for f in event_contracts.figures_read(None, CATALOGUE)][:2] == [
        "Answering",
        "Does not stream",
    ]


# ── Bars, where a venue keeps them (0.33.1; rulings 624, 625, 629) ──────

DAY_BEFORE = date(2026, 10, 9)


def _checks(venue: SimpleNamespace) -> EventContractsChecks:
    checks = EventContractsChecks()
    checks.venue = venue
    return checks


def _bars_feed(lake: Lake, market: ContractsMarket | None = None) -> event_contracts.Feed:
    return event_contracts.Feed(
        lake, market or BarsMarket(), event_contracts.ContractMap(), clock_ns=lambda: NOW_NS,
        bars_declared=contracts_catalogue("bars")[0],
    )  # fmt: skip


@pytest.mark.parametrize(
    ("market", "keys"),
    [(ContractsMarket, ("live", "outcomes")), (BarsMarket, ("live", "outcomes", "bars"))],
)
def test_a_venue_with_and_without_bars_passes_every_case_it_presents(
    market: type[ContractsMarket], keys: tuple[str, ...]
) -> None:
    v = contracts_venue_with(market, *keys)
    checks = _checks(v)
    checks.test_every_case_is_mapped_or_said_not_presented_with_why()
    report = run("data", event_contract_producers(v), not_presented=checks.not_presented(),
                 instance_id=v.VENUE)  # fmt: skip
    assert report.passed, report.failures
    assert ("a-daily-bar" in report.passed_cases) == (market is BarsMarket)
    checks.test_it_serves_live_and_outcomes_and_bars_only_where_it_keeps_them()
    checks.test_the_roles_figures_in_its_order()
    checks.test_datasets_says_whether_a_deployment_admin_licensed_it()
    checks.test_an_outcome_recorded_counts_on_its_own_dataset()


async def test_the_bars_checks_pass_a_venue_keeping_bars_and_skip_one_keeping_none() -> None:
    for venue in (
        contracts_venue_with(BarsMarket, "live", "outcomes", "bars"),
        contracts_venue_with(ContractsMarket),
    ):
        await _checks(venue).test_bars_are_kept_hourly_and_daily_on_the_declared_day()
        await _checks(venue).test_a_bars_want_is_answered_from_the_venues_history()


@pytest.mark.parametrize(
    ("market", "keys"),
    [
        (ContractsMarket, ("live", "outcomes", "bars")),  # bars declared, none kept
        (BarsMarket, ("live", "outcomes")),  # bars kept, none declared
        (BarsMarket, ("live", "outcomes", "trades")),  # another dataset for the third
        (BarsMarket, ("live", "outcomes", "bars", "trades")),  # a fourth
        (ContractsMarket, ("live", "outcomes", "trades")),
    ],
)
def test_the_checks_refuse_any_dataset_but_bars_where_bars_are_kept(
    market: type[ContractsMarket], keys: tuple[str, ...]
) -> None:
    checks = _checks(contracts_venue_with(market, *keys))
    with pytest.raises(AssertionError, match="an event-contract venue serves"):
        checks.test_it_serves_live_and_outcomes_and_bars_only_where_it_keeps_them()


async def test_keep_bars_keeps_each_closed_hour_and_day_once() -> None:
    lake = Lake(contracts_venue.VENUE)
    feed = _bars_feed(lake)
    subject = await lake.held(feed, "BASE-1")
    await feed.record_live([subject], data_type="meridian.v1.Price")
    sent = await feed.keep_bars(once=True)
    bars = lake.rows("RecordBars")
    assert sent == len(bars) and bars
    days = [b for b in bars if b.meta.business_date]
    hours = [b for b in bars if not b.meta.business_date]
    # New York's days, the last closed the 9th (12:00 UTC is 08:00 there).
    assert days[-1].meta.business_date == "2026-10-09"
    assert (days[-1].meta.valid_from_ns, days[-1].meta.valid_until_ns) == (
        ny_day_starts(DAY_BEFORE), ny_day_starts(date(2026, 10, 10))
    )  # fmt: skip
    assert len(days) == 30, "BARS_FIRST_DAYS of days, first read"
    assert hours[-1].meta.valid_until_ns <= NOW_NS - 60 * 10**9
    assert days[-1].meta.row_key == f"BASE-1:1d:{ny_day_starts(DAY_BEFORE) // 10**9}"
    assert all(b.meta.source.dataset == "fakev:bars" for b in bars)
    assert all(not b.meta.source_times and not b.HasField("vwap") for b in bars)
    assert not any(b.meta.quality for b in bars), "a bar over another interval no duplicate"
    assert [b.meta.valid_until_ns for b in bars] == sorted(b.meta.valid_until_ns for b in bars)
    assert feed.bar_counts.recorded == len(bars) and feed.counts.recorded == 3
    # Nothing closed since: nothing asked or sent again.
    asked = len(feed.market.asked)  # type: ignore[attr-defined]
    assert await feed.keep_bars(once=True) == 0 and len(feed.market.asked) == asked  # type: ignore[attr-defined]


async def test_kept_bars_are_read_on_from_where_the_map_left_them(tmp_path: Path) -> None:
    lake = Lake(contracts_venue.VENUE)
    feed = _bars_feed(lake)
    kept = tmp_path / "contracts-synthetic.json"
    feed.contracts = event_contracts.ContractMap(kept)
    subject = await lake.held(feed, "BASE-1")
    await feed.record_live([subject], data_type="meridian.v1.Price")
    await feed.keep_bars(once=True)
    later = NOW_NS + 2 * HOUR
    again = event_contracts.Feed(
        lake, BarsMarket(later), event_contracts.ContractMap(kept), clock_ns=lambda: later,
        bars_declared=contracts_catalogue("bars")[0],
    )  # fmt: skip
    assert again.contracts.load()
    await again.keep_bars(once=True)
    [(code, interval, first_ns, until_ns)] = again.market.asked  # type: ignore[attr-defined]
    assert (code, interval) == ("BASE-1", event_contracts.HOUR), "no day closed since"
    assert until_ns - first_ns == 2 * HOUR


async def test_a_bar_off_its_interval_or_past_the_payout_is_left_unrecorded() -> None:
    class Odd(BarsMarket):
        def days(self, code: str, first_ns: int, until_ns: int) -> list[event_contracts.Candle]:
            # A UTC day, where the plugin declares New York's.
            start = ny_day_starts(DAY_BEFORE) - 4 * HOUR
            return [candle(code, start, start + 24 * HOUR)]

        def hours(
            self, code: str, first_ns: int, until_ns: int
        ) -> list[event_contracts.Candle]:
            at = NOW_NS - 3 * HOUR
            return [
                candle(code, at, at + HOUR, high=Decimal("1.5")),
                candle(code, at - HOUR, at, low=Decimal("0.44")),  # above its open
                candle(code, at - 2 * HOUR, at - HOUR, volume=None),
                candle(code, at - 4 * HOUR, at - 2 * HOUR),  # two hours
            ]

    lake = Lake(contracts_venue.VENUE)
    feed = _bars_feed(lake, Odd())
    subject = await lake.held(feed, "BASE-1")
    await feed.record_live([subject], data_type="meridian.v1.Price")
    assert await feed.keep_bars(once=True) == 0
    assert not lake.rows("RecordBars") and feed.bar_counts.unread == 5


async def test_no_bar_is_read_past_a_contracts_close_once_kept_to_it() -> None:
    class Closed(BarsMarket):
        def contract(
            self, code: str, watching: bool = False
        ) -> event_contracts.Contract | None:
            read = super().contract(code, watching)
            return (
                None
                if read is None
                else replace(read, closes_at_ns=NOW_NS - 3 * 86_400 * 10**9)
            )

    lake = Lake(contracts_venue.VENUE)
    feed = _bars_feed(lake, Closed())
    subject = await lake.held(feed, "BASE-1")
    await feed.name([subject])
    await feed.cash_id()
    assert await feed.keep_bars(once=True) > 0
    later = NOW_NS + 86_400 * 10**9
    feed.clock_ns = lambda: later
    feed.wants.clock_ns = feed.clock_ns
    asked = len(feed.market.asked)  # type: ignore[attr-defined]
    assert await feed.keep_bars(once=True) == 0
    assert len(feed.market.asked) == asked, "kept to its close: not read again"  # type: ignore[attr-defined]


async def test_keep_bars_is_refused_without_the_hook_or_the_bars_dataset() -> None:
    lake = Lake(contracts_venue.VENUE)
    plain = event_contracts.Feed(lake, ContractsMarket(), event_contracts.ContractMap())
    assert not plain.keeps_bars and plain.wants.keys == ("live", "outcomes")
    with pytest.raises(TypeError, match="answers no bars"):
        await plain.keep_bars(contracts_catalogue("bars")[0], once=True)
    kept = event_contracts.Feed(lake, BarsMarket(), event_contracts.ContractMap())
    assert kept.wants.keys == ("live", "outcomes", "bars")
    with pytest.raises(ValueError, match="'bars'"):
        await kept.keep_bars(contracts_catalogue("trades")[0], once=True)
    with pytest.raises(ValueError, match="the day the plugin declares"):
        await kept.keep_bars(once=True)


async def test_a_standing_want_of_bars_is_kept_by_keep_bars_never_polled_live() -> None:
    lake = Lake(contracts_venue.VENUE)
    feed = _bars_feed(lake)
    subject = await lake.held(feed, "BASE-1")
    await hear(lake, feed, wanted(feed, "WNT-S", event_contracts.BARS, [subject],
                                  data_type="meridian.v1.Bar", standing=True))  # fmt: skip
    assert set(feed.standing) == {"WNT-S"} and lake.on("RecordBars")[0].want_id == "WNT-S"
    await feed.current()
    assert not lake.on("RecordPrices") and not lake.on("RecordQuotes")
    assert await feed.keep_bars(once=True) > 0, "its subject's contract is served"


def test_a_session_day_ending_after_midnight_is_the_date_it_ends_on() -> None:
    declared = replace(contracts_catalogue("bars")[0], day_end_minute=17 * 60)
    feed = event_contracts.Feed(
        Lake(contracts_venue.VENUE), BarsMarket(), event_contracts.ContractMap(),
        bars_declared=declared,
    )  # fmt: skip
    five_pm = ny_day_starts(DAY_BEFORE) + 17 * HOUR
    assert feed.business_date(five_pm - 1) == DAY_BEFORE
    assert feed.business_date(five_pm) == date(2026, 10, 10)
    assert feed.day_starts_ns(date(2026, 10, 10)) == five_pm
    midnight = replace(declared, day_end_minute=0)
    feed.bars_declared = midnight
    assert feed.business_date(ny_day_starts(DAY_BEFORE)) == DAY_BEFORE
    assert feed.day_starts_ns(DAY_BEFORE) == ny_day_starts(DAY_BEFORE)


# ── The feed delay on the quote (0.33.1; ruling 626) ────────────────────


class UntimedMarket(ContractsMarket):
    """A venue whose last trade states no time, its book its own."""

    def last(self, contract: event_contracts.Contract) -> event_contracts.Tick:
        return replace(super().last(contract), stated=False)


def _feed_delay(venue: SimpleNamespace) -> tuple[bool, list[Any], list[Any]]:
    recorder = Recorder(venue.VENUE)
    asyncio.run(event_contract_producers(venue)["reports-its-feed-delay"](recorder))
    snapshots = [s for r in recorder.on("ReportLatency") for s in r.snapshots]
    return bool(snapshots), list(recorder.on("RecordPrices")), list(recorder.on("RecordQuotes"))


def test_the_feed_delay_stands_on_the_last_price_where_its_trade_is_timed() -> None:
    reported, prices, quotes = _feed_delay(contracts_venue_with(ContractsMarket))
    assert reported and prices and not quotes


def test_the_feed_delay_stands_on_the_quote_where_the_last_trade_states_no_time() -> None:
    v = contracts_venue_with(UntimedMarket)
    reported, prices, quotes = _feed_delay(v)
    assert reported and quotes and not prices
    report = run("data", event_contract_producers(v), not_presented=_checks(v).not_presented(),
                 instance_id=v.VENUE)  # fmt: skip
    assert "reports-its-feed-delay" in report.passed_cases


def test_the_feed_delay_stands_on_the_quote_where_no_price_is_declared() -> None:
    v = contracts_venue_with(ContractsMarket)
    catalogue = contracts_catalogue("live", "outcomes")
    catalogue[0] = replace(catalogue[0], data_types=("meridian.v1.Quote",))
    v.page = fake_page(catalogue)
    reported, prices, quotes = _feed_delay(v)
    assert reported and quotes and not prices


async def test_an_interval_the_venue_did_not_answer_is_asked_again() -> None:
    class Down(BarsMarket):
        down = True

        def bars(
            self,
            contract: event_contracts.Contract,
            interval: str,
            first_ns: int,
            until_ns: int,
        ) -> list[event_contracts.Candle]:
            if self.down:
                raise OSError("down")
            return super().bars(contract, interval, first_ns, until_ns)

    lake = Lake(contracts_venue.VENUE)
    market = Down()
    feed = _bars_feed(lake, market)
    subject = await lake.held(feed, "BASE-1")
    await feed.record_live([subject], data_type="meridian.v1.Price")
    assert await feed.keep_bars(once=True) == 0 and not feed.contracts.bars
    market.down = False
    assert await feed.keep_bars(once=True) > 0 and set(feed.contracts.bars) == {
        "BASE-1:1h",
        "BASE-1:1d",
    }
