"""A venue's whole work by what it lists (0.30.0): `meridian.roles.data.pairs`
and `.event_contracts`, run against two made-up venues (tests/fake_venues.py)
through the data suite's producers a plugin runs (`meridian.roles.data.
testing`), and their pages drawn from the SDK's kind templates. The four
plugins that kept this work byte for byte now run the same checks against
their own conversions."""

from __future__ import annotations

import re
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest

import meridian
from fake_venues import NOW_NS, contracts_venue, pairs_venue
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles.data import event_contracts, pairs
from meridian.roles.data.testing import (
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
    report = run("data", pairs_producers(v), not_presented=v.NOT_PRESENTED, instance_id=v.VENUE)
    assert report.passed, report.failures
    assert len(report.passed_cases) == len(list(names("data"))) - len(v.NOT_PRESENTED)
    assert set(names("data")) == set(pairs_producers(v)) | set(v.NOT_PRESENTED) | set(
        ANSWERED_BY_SDK
    )


def test_an_event_contract_venue_passes_every_case_it_presents() -> None:
    v = contracts_venue
    made = event_contract_producers(v)
    report = run("data", made, not_presented=v.NOT_PRESENTED, instance_id=v.VENUE)
    assert report.passed, report.failures
    assert set(names("data")) == set(made) | set(v.NOT_PRESENTED) | set(ANSWERED_BY_SDK)


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
    assert re.findall(r"<h2>([^<]*)</h2>", connection) == ["Key", "Limits and use", "Stream"]
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
