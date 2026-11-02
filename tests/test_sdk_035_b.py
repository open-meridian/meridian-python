"""SDK 0.35, part B (spec/each-role-is-one-generated-class, section 4;
rulings 924, 1009, 1016 to 1018, 1023, 1027 and 1028): 924's helpers past
what their behaviour cases hold, against the recorder and the stand-in
sidecar, and part A's follow-ups.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

import meridian
from conftest import FakeSidecar
from meridian.helpers.calendars import DayClock, MarketDays
from meridian.helpers.sessions import Backoff, SessionState, Supervisor
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.roles import data, pricing
from meridian.roles.data import listings, option_chains
from meridian.suites import Recorder
from test_role_classes import _running
from test_v26 import _batch, _unit

NS = 1_000_000_000


# ── Part A's follow-up: a Pricer answers a batch once ───────────────────


async def test_a_pricer_answers_a_batch_waiting_on_start_once(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The catch-up on start answers the batch waiting, and the stream's
    seeding hands the same batch on again: it is not answered twice."""
    service, address = sidecar
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    service.roles = ("pricing",)
    service.operations.price_batches = [_batch(_unit("227.50"), sequence=1)]
    pricer = pricing.Pricer({"quoted_price": pricing.reference_model})

    # Until the stream's seeding has read the batches waiting again (the
    # catch-up reads twice, the seeding twice after it).
    def seeded() -> bool:
        reads = service.operations.reads
        return sum(isinstance(r, ops.ListPriceBatchesParams) for r in reads) >= 4

    await _running(address, [pricer], seeded)
    assert [b.batch_id for b in service.operations.answered_batches] == ["PBT-1"]
    assert pricer.answered == 1


async def test_a_pricer_answers_a_later_batch_heard() -> None:
    recorder = Recorder("pricing-1")
    pricer = recorder.bind(pricing.Pricer({"quoted_price": pricing.reference_model}))
    await pricer.answer(_batch(_unit("1.00"), sequence=4))
    await pricer.on_price_batch(
        Heard(row="PriceBatch", message=_batch(_unit("1.00"), sequence=4))
    )
    await pricer.on_price_batch(
        Heard(row="PriceBatch", message=_batch(_unit("1.00"), sequence=5))
    )
    assert [p.batch_id for p in recorder.on("AnswerPriceBatch")] == ["PBT-4", "PBT-5"]


# ── helpers.sessions.Supervisor, past its behaviour cases ──────────────


class _Link:
    """A link answering what it is told: statements, then a break."""

    name = "fake"

    def __init__(self, said: list[list[Any]], breaks: bool = True) -> None:
        self.said, self.breaks = said, breaks
        self.subscribed: list[tuple[str, ...]] = []

    async def open(self) -> None:
        return None

    async def subscribe(self, wanted: Any) -> None:
        self.subscribed.append(tuple(wanted))

    async def receive(self) -> list[Any]:
        if self.said:
            return self.said.pop(0)
        if self.breaks:
            raise ConnectionError("the source dropped the session")
        await asyncio.Event().wait()
        return []

    async def close(self) -> None:
        return None


async def test_a_supervisor_counts_its_reconnects_and_signs_of_life_on_latency() -> None:
    from meridian.roles import Latency

    recorder = Recorder("lake-1")
    latency = Latency(recorder)
    heard: list[Any] = []

    async def hear(stated: list[Any]) -> None:
        heard.extend(stated)
        raise RuntimeError("a statement did not convert")  # said, the session goes on

    supervisor = Supervisor(
        lambda: _Link([[1], [2]]),
        heard=hear,
        latency=latency,
        session="stocks",
        backoff=Backoff(1, 60, 0, 60),
        flush_seconds=0.001,
    )
    supervisor.want(["SPY"])
    await supervisor.run(once=True)
    assert heard == [1, 2]
    state: SessionState = supervisor.state
    assert (state.opened, state.dropped, state.messages, state.reconnects) == (1, 1, 2, 1)
    assert "ConnectionError" in state.last_error
    held = latency.session("stocks")
    assert held.counters["reconnects"] == 1 and held.alive_at_ns > 0


async def test_a_supervisor_with_nothing_wanted_opens_nothing() -> None:
    made: list[Any] = []

    def link() -> _Link:
        made.append(1)
        return _Link([])

    async def hear(stated: list[Any]) -> None:
        return None

    supervisor = Supervisor(link, heard=hear)
    await supervisor.run(once=True)
    assert made == [] and supervisor.state.state == "off"


# ── helpers.calendars, past their behaviour cases ──────────────────────


async def test_market_days_say_why_the_calendar_was_not_read() -> None:
    recorder = Recorder("lake-1")
    recorder.answer("ReadCalendar", lambda _: ops.ReadCalendarResult(found=False))
    days = MarketDays(recorder, "CAL-NONE")
    assert await days.is_open(dt.date(2026, 11, 2)) is None
    assert days.error == "the calendar CAL-NONE is not held"
    with pytest.raises(ValueError, match="CAL- ID"):
        MarketDays(recorder, "")


def test_a_day_clock_is_read_from_a_datasets_declaration() -> None:
    declared = meridian.DatasetDeclaration(
        key="daily",
        vendor="Fake",
        data_types=["meridian.v1.Price"],
        modes=["pull"],
        licence_default=meridian.DatasetLicence(redistribution="not_allowed"),
        day_time_zone="America/New_York",
        day_end_minute=1020,
    )
    clock = DayClock.of(declared)
    assert (clock.time_zone, clock.end_minute) == ("America/New_York", 1020)
    with pytest.raises(ValueError, match="states no day_time_zone"):
        DayClock.of(SimpleNamespace(key="live", day_time_zone="", day_end_minute=0))


# ── data.Timetable's reads ──────────────────────────────────────────────


async def test_a_timetable_makes_each_read_due_and_a_failed_read_is_due_again() -> None:
    now = [0]
    read: list[tuple[str, ...]] = []

    async def tapes(subjects: Any) -> None:
        read.append(tuple(subjects))
        if len(read) == 1:
            raise RuntimeError("the vendor answered 500")

    table = data.Timetable(clock_ns=lambda: now[0])
    table.of(SimpleNamespace(key="tapes", cadence=30), tapes)
    table.want("tapes", ["INS-1"])
    assert await table.tick() == 1 and await table.tick() == 0
    now[0] = 30 * NS
    assert await table.tick() == 1 and read == [("INS-1",), ("INS-1",)]
    with pytest.raises(ValueError, match="declares no cadence"):
        table.of(SimpleNamespace(key="daily", cadence=0))


# ── the listings feed's pages (924's item 8) ───────────────────────────


def test_a_listings_sources_pages_draw_its_plan_its_streams_and_its_counts() -> None:
    from meridian.testing import PageClient

    recorder = Recorder("equities-1")

    class Lake(listings.Feed):
        source_name = "fake"

    lake = recorder.bind(
        Lake(
            None,
            timeliness="delayed",
            datasets_by_timeliness={"live": {"real_time": "live", "delayed": "live_delayed"}},
        )
    )
    lake.products.put("INS-1", "SPY")
    catalogue = [
        meridian.DatasetDeclaration(
            key=key,
            vendor="Fake",
            data_types=["meridian.v1.Price"],
            modes=["pull"],
            licence_default=meridian.DatasetLicence(redistribution="not_allowed"),
            day_time_zone="America/New_York",
            day_end_minute=960,
        )
        for key in ("daily", "live", "live_delayed")
    ]
    stocks = SessionState(state="waiting", subscribed=("SPY",), opened=2, dropped=1)
    pages = meridian.Pages("Fake", kit="0.12.0")

    @pages.page(
        "/",
        "Connection",
        levels="admin",
        answers=listings.ConnectionRead,
        name="read_connection",
    )
    def connection(request: meridian.Request) -> meridian.Response:
        read = listings.connection_read(lake, mode="Live", streams={"stocks": stocks})
        return pages.answer("meridian/roles/data/listings/connection.html", read)

    @pages.page(
        "/datasets",
        "Datasets",
        levels="admin",
        answers=listings.DatasetsRead,
        name="read_datasets",
    )
    def datasets(request: meridian.Request) -> meridian.Response:
        read = listings.datasets_read(lake, catalogue, "equities-1", "All", licensed={
            "equities-1:live_delayed"})  # fmt: skip
        return pages.answer("meridian/roles/data/listings/datasets.html", read, venue="Fake")

    client = PageClient(pages)
    shown = client.get("/", "admin").text
    assert "Delayed" in shown and "Stocks" in shown and "1 listing on it; 1 reconnect" in shown
    listed = client.get("/datasets", "admin").text
    assert "1 listing mapped" in listed and "equities-1:live_delayed" in listed
    figures = listings.figures_read(lake, catalogue, streams={"stocks": stocks})
    assert [f.label for f in figures][:3] == ["Connection", "Entitled at the vendor", "Stream"]
    assert figures[2].state == "warn"


# ── data.option_chains held by another data role class ─────────────────


async def test_a_chains_feed_held_by_a_listings_class_acts_through_its_connection() -> None:
    recorder = Recorder("equities-1")

    class Source:
        def expirations(self, symbol: str) -> list[dt.date]:
            return [dt.date(2026, 11, 20)]

        def chain(self, symbol: str, expiration: dt.date) -> list[option_chains.ChainOption]:
            return [
                option_chains.ChainOption(
                    "SPY   261120C00500000", expiration, bid=Decimal("5.1"), ask=Decimal("5.2")
                )
            ]

    class Lake(listings.Feed):
        source_name = "fake"

        def __init__(self) -> None:
            super().__init__(None, clock_ns=lambda: 1_793_660_400 * NS)
            self.chains = option_chains.Feed(Source(), role=self, clock_ns=self.clock_ns)

        async def on_observations_wanted(self, heard: Any) -> None:
            if self.chains.serves(heard.message.dataset):
                return await self.chains.on_observations_wanted(heard)
            await super().on_observations_wanted(heard)

    lake = recorder.bind(Lake())
    lake.products.put("INS-SPY", "SPY")
    want = ops.ObservationsWantedEvent(
        want_id="WNT-1",
        dataset="equities-1:options",
        data_type=option_chains.QUOTE,
        subjects=[ops.SubjectRef(entity_id="INS-SPY")],
    )
    await lake.on_observations_wanted(Heard(row="ObservationsWanted", message=want))
    (quotes,) = recorder.on("RecordQuotes")
    assert quotes.quotes[0].meta.series_key[0].value == "SPY   261120C00500000"
    assert lake.chains.plugin is recorder.plugin and lake.chains.counts.reads == 1
    # Read again, the same quote is not sent again.
    await lake.on_observations_wanted(
        Heard(row="ObservationsWanted", message=ops.ObservationsWantedEvent(
            want_id="", dataset="equities-1:options", data_type=option_chains.QUOTE,
            subjects=[ops.SubjectRef(entity_id="INS-SPY")]))
    )  # fmt: skip
    assert len(recorder.on("RecordQuotes")) == 1


# ── data.pairs (924's items 2 and 12) ──────────────────────────────────


class _Keyed:
    """The fake pairs venue keying its best bids and offers before reading
    them (`conflation_key`), counting what it read."""

    def __init__(self) -> None:
        from fake_venues import pairs_venue

        self.market = pairs_venue.market()
        self.read = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.market, name)

    def conflation_key(self, text: str) -> str | None:
        import json

        said = json.loads(text)
        return f"{said['product']}:top" if said["type"] == "top" else None

    def heard(self, text: str, received_ns: int) -> list[Any]:
        self.read += 1
        return self.market.heard(text, received_ns)


async def test_a_pairs_feed_conflating_first_reads_and_keeps_only_the_latest() -> None:
    from fake_venues import pairs_venue, top
    from meridian.roles.data import pairs
    from meridian.roles.data.testing import Lake, hear, wanted

    lake = Lake(pairs_venue.VENUE)
    market = _Keyed()
    feed = lake.bind(
        pairs.Feed(
            market,  # type: ignore[arg-type]
            pairs.ProductMap(),
            clock_ns=lambda: pairs_venue.NOW_NS,
            stream_factory=pairs_venue.STREAM,
            conflate_first=True,
        )
    )
    btc = await lake.held(feed, "BTC")
    await hear(lake, feed, wanted(feed, "WNT-Q", pairs.LIVE, [btc],
                                  data_type="meridian.v1.Quote", standing=True))  # fmt: skip
    before = len(lake.on("RecordQuotes"))
    await feed.on_message(top(1, bid="62500.00"))
    await feed.on_message(top(2, bid="62501.00"))
    await feed.on_message(top(3, bid="62502.00"))
    assert market.read == 0, "held, not read, until the pass"
    await feed.flush()
    assert market.read == 1, "only the latest read and kept"
    sent = [q for each in lake.on("RecordQuotes")[before:] for q in each.quotes]
    assert [q.meta.row_key.endswith(":3") for q in sent] == [True]


async def test_a_pairs_feed_records_the_mid_where_asked_and_dates_by_its_day_clock() -> None:
    from fake_venues import pairs_venue
    from meridian.roles.data import pairs
    from meridian.roles.data.testing import Lake

    lake = Lake(pairs_venue.VENUE)
    clock = DayClock("America/New_York", 1020)
    feed = lake.bind(
        pairs.Feed(
            pairs_venue.market(),
            pairs.ProductMap(),
            clock_ns=lambda: pairs_venue.NOW_NS,
            day_clock=clock,
        )
    )
    btc = await lake.held(feed, "BTC")
    await feed.record_live([btc], kinds=[ops.PRICE_KIND_MID])
    kinds = {
        ops.PriceKind.Name(p.kind) for each in lake.on("RecordPrices") for p in each.prices
    }
    assert kinds == {"PRICE_KIND_MID"}
    await feed.record_days([btc], pairs_venue.CLOSED, pairs_venue.CLOSED)
    closes = [p for each in lake.on("RecordPrices") for p in each.prices
              if p.kind == ops.PRICE_KIND_CLOSE]  # fmt: skip
    day = dt.date.fromisoformat(closes[0].meta.business_date)
    assert closes[0].meta.valid_until_ns == clock.close_of(day)


async def test_a_pairs_feed_supervised_opens_its_market_and_hears_what_it_says() -> None:
    from fake_venues import Replayed, pairs_venue, top
    from meridian.roles.data import pairs

    texts: list[str] = []
    opened: list[Any] = []

    async def connect(address: str) -> Replayed:
        return Replayed([top(1)])

    async def heard(text: str) -> None:
        texts.append(text)

    async def on_opened(names: Any) -> None:
        opened.append(tuple(names))

    stream = pairs.supervised(
        address=pairs_venue.market().stream_address,
        connect=connect,
        subscriptions=lambda names: [f"subscribe {n}" for n in names],
        heard=heard,
        opened=on_opened,
        silent_seconds=0,
    )
    stream.want(["BTC-USD"])
    await stream.run(once=True)
    assert texts == [top(1)] and opened == [("BTC-USD",)]
    assert stream.health.opened == 1 and stream.health.dropped == 1
