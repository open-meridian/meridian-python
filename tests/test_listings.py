"""A broker's US equity listings in the lake (0.31.0; ruling 213):
`meridian.roles.data.listings`, generic over the broker, tested once here
against a made-up broker; Alpaca's and Tradier's plugins run their own
tests on it."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from meridian.operations import as_decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.roles.data import listings
from meridian.suites import Recorder

DAY = dt.date(2026, 10, 9)
#: 17:00 New York on DAY: its close is final.
EVENING = listings.close_of(DAY) + 3600 * listings.NS
SPY, QQQ = "INS-01J8XQ4M7K00000000000SPY", "INS-01J8XQ4M7K00000000000QQQ"


@dataclass(frozen=True)
class Bar:
    symbol: str
    business_date: dt.date
    close: Decimal | None
    open: Decimal | None = Decimal("570")
    high: Decimal | None = Decimal("575")
    low: Decimal | None = Decimal("569")
    volume: Decimal | None = Decimal("1000")
    vwap: Decimal | None = None
    trade_count: int | None = None
    raw_key: str = "daily/1"
    unconverted: tuple[Any, ...] = ()

    @property
    def row_key(self) -> str:
        return f"{self.symbol}:1d:{self.business_date.isoformat()}"

    @property
    def complete(self) -> bool:
        return self.close is not None and None not in (self.open, self.high, self.low)


@dataclass(frozen=True)
class Tick:
    symbol: str
    at_ns: int
    venue_code: str
    price: Decimal | None
    quantity: Decimal | None
    sequence: int
    raw_key: str = "stream/1"
    cancelled: bool = False
    unconverted: tuple[Any, ...] = ()

    @property
    def row_key(self) -> str:
        return f"{self.symbol}:t:{self.sequence}"


@dataclass
class Broker:
    bars: list[Bar] = field(default_factory=list)
    invalid: set[str] = field(default_factory=set)
    asked: list[tuple[str, ...]] = field(default_factory=list)

    def daily(self, symbols: Any, first: dt.date, last: dt.date) -> list[Any]:
        self.asked.append(tuple(symbols))
        return [b for b in self.bars if b.symbol in symbols]

    def live(self, symbols: Any) -> list[Any]:
        return []

    def quotes(self, symbols: Any) -> list[Any]:
        return []


@dataclass
class Historian(Broker):
    history: list[Tick] = field(default_factory=list)

    def trades(self, symbols: Any, start_ns: int, end_ns: int) -> list[Any]:
        return [
            t for t in self.history if t.symbol in symbols and start_ns <= t.at_ns <= end_ns
        ]


class Lake(listings.Feed):
    source_name = "brokerage"

    def attributes(self, stated: Any) -> listings.Attributes:
        return listings.Attributes(("odd_lot",), (True,) * 4, (True,) * 4)


class Sequenced(Lake):
    settles_declines = False

    def withdrawn_unrecorded(self, stated: Any) -> listings.Attributes | None:
        return None

    def sequence_of(self, stated: Any) -> int | None:
        return int(stated.sequence)


def lake(
    source: Any, kind: type[Lake] = Lake, tmp: Path | None = None
) -> tuple[Lake, Recorder]:
    recorder = Recorder("brokerage-1")
    made = kind(recorder, source, listings.Listings(tmp), clock_ns=lambda: EVENING)
    made.products.put(SPY, "SPY")
    return made, recorder


def test_a_feed_names_its_source() -> None:
    try:
        listings.Feed(Recorder(), None)
    except TypeError as refused:
        assert "source_name" in str(refused)
    else:
        raise AssertionError("a feed naming no source was made")


def test_a_symbol_is_spelled_once_and_days_cut_at_new_yorks_close() -> None:
    assert [listings.spelled(s) for s in ("brk/b", "BRK-B", "SPY", "TOOLONGX")] == [
        "BRK.B",
        "BRK.B",
        "SPY",
        None,
    ]
    assert listings.new_york_date(listings.close_of(DAY)) == DAY
    assert listings.previous_close_of(DAY) == listings.close_of(DAY - dt.timedelta(days=1))


async def test_a_days_close_and_bar_are_recorded_final_under_the_records_key() -> None:
    feed, recorder = lake(Broker(bars=[Bar("SPY", DAY, Decimal("571.47"))]))
    await feed.daily([SPY], DAY, DAY)
    await feed.daily([SPY], DAY, DAY, data_type=listings.BAR)
    (prices,) = recorder.on("RecordPrices")
    (price,) = prices.prices
    assert price.meta.row_key == f"SPY:1d:2026-10-09@{SPY}"
    assert as_decimal(price.price.amount) == Decimal("571.47")
    published = [ops.SourceTimeKind.Name(t.kind) for t in price.meta.source_times]
    assert published == ["SOURCE_TIME_KIND_PUBLISHED"], "final past the close"
    assert len(recorder.on("RecordBars")) == 1


async def test_a_subject_with_no_symbol_is_declined_once_for_the_date() -> None:
    feed, recorder = lake(Broker())
    feed.reads_instruments = False
    for _ in range(2):
        await feed.daily([QQQ], DAY, DAY, want_id="WNT-1")
    (declined,) = recorder.on("DeclineWant")
    assert declined.reason == ops.UNANSWERED_REASON_NOT_COVERED


async def test_a_plugin_not_settling_declines_sends_each() -> None:
    feed, recorder = lake(Broker(), Sequenced)
    feed.reads_instruments = False
    for _ in range(2):
        await feed.daily([QQQ], DAY, DAY, want_id="WNT-1")
    assert len(recorder.on("DeclineWant")) == 2


async def test_a_symbol_the_source_cannot_take_is_declined_not_covered() -> None:
    feed, recorder = lake(Broker(invalid={"SPY"}))
    await feed.daily([SPY], DAY, DAY, want_id="WNT-1")
    (declined,) = recorder.on("DeclineWant")
    assert declined.reason == ops.UNANSWERED_REASON_NOT_COVERED


async def test_a_trade_withdrawn_unrecorded_is_sent_not_known_or_counted() -> None:
    gone = Tick("SPY", EVENING, "", Decimal("1"), Decimal("1"), 7, cancelled=True)
    feed, _ = lake(Broker())
    row = await feed.trade_row(gone, SPY)
    assert row is not None and row.cancelled
    assert row.attributes is not None and row.attributes.consolidated is not None
    sequenced, _ = lake(Broker(), Sequenced)
    assert await sequenced.trade_row(gone, SPY) is None
    assert sequenced.counts[listings.TRADES].unmatched == 1


async def test_a_trade_carries_the_plugins_attributes_and_sequence() -> None:
    feed, _ = lake(Broker(), Sequenced)
    row = await feed.trade_row(Tick("SPY", EVENING, "", Decimal("571"), Decimal("5"), 42), SPY)
    assert row is not None and row.source_sequence == 42
    assert row.attributes is not None and row.attributes.characteristics == ["odd_lot"]


async def test_a_range_of_trades_is_read_only_from_a_source_with_history() -> None:
    def want() -> Heard[ops.ObservationsWantedEvent]:
        return Heard(
            row="ObservationsWanted",
            message=ops.ObservationsWantedEvent(
                want_id="WNT-T",
                dataset="brokerage-1:trades",
                data_type=listings.TRADE,
                subjects=[ops.SubjectRef(entity_id=SPY)],
                valid_from_ns=EVENING - 60 * listings.NS,
                valid_until_ns=EVENING,
            ),
        )

    streamed_only, recorder = lake(Broker())
    assert not streamed_only.reads_history
    await streamed_only.on_want(want())
    (declined,) = recorder.on("DeclineWant")
    assert declined.reason == ops.UNANSWERED_REASON_NOT_COVERED
    tick = Tick("SPY", EVENING - listings.NS, "", Decimal("571"), Decimal("5"), 1)
    historian, recorder = lake(Historian(history=[tick]))
    assert historian.reads_history
    await historian.on_want(want())
    (recorded,) = recorder.on("RecordTrades")
    assert len(recorded.trades) == 1


def test_the_listing_map_is_kept_in_storage(tmp_path: Path) -> None:
    kept = listings.Listings(tmp_path / "products.json")
    kept.put(SPY, "SPY")
    assert listings.Listings(tmp_path / "products.json").symbols == {SPY: "SPY"}


async def test_a_source_that_does_not_stream_streams_none() -> None:
    feed, _ = lake(Broker())
    feed.standing["WNT-S"] = listings.Standing(
        "WNT-S", (SPY,), (), 0, listings.LIVE, listings.QUOTE
    )
    assert feed.restream() == set() and feed.streamed == ["SPY"]
    feed.streaming = False
    feed.restream()
    assert feed.streamed == []
