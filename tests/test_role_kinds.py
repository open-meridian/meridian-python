"""A venue's whole work by what it lists (0.30.0): `meridian.roles.data.pairs`
and `.event_contracts`, run against two made-up venues (tests/fake_venues.py)
through the data suite's producers a plugin runs (`meridian.roles.data.
testing`), and their pages drawn from the SDK's kind templates. The four
plugins that kept this work byte for byte now run the same checks against
their own conversions."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import meridian
from fake_venues import NOW_NS, ContractsMarket, contracts_venue, pairs_venue
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
