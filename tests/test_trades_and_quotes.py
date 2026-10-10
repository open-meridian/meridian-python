"""The lake's 1b through the SDK (contract v19): trades and quotes recorded in
batches, read over a range, after a watermark or at the latest, and heard --
every trade in full, caught up after the watermark last seen, the latest
quote per subject, dataset, venue and asset -- and the reading suites that
hold `signal` and `ems` to them.

Against the fake sidecar (conftest), which mirrors the lake as core's sidecar
and lake answer it. The dgm suite's 1b cases are in tests/test_lake.py, with
its 1a.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

import meridian
from conftest import FakeSidecar, Stream
from meridian import (
    DatasetDeclaration,
    DatasetLicence,
    Declaration,
    Eligibility,
    Money,
    ObservationMeta,
    Quote,
    Source,
    SourceChoice,
    SubjectRef,
    Trade,
    TradeAttributes,
)
from meridian.operations import UNCONFLATED
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import HEARD, Recorder, run, suite

INSTANCE = "dgm-coinbase-1"
LIVE = f"{INSTANCE}:live"
BTC = "LCL-01JA00000000000000BTC1"
USDC = "LCL-01JA0000000000000USDC1"
COINBASE = "VEN-01JA0000000000000CBEXC"
HOUR = 1_791_334_800_000_000_000  # 2026-10-08 01:00 UTC
SECOND = 10**9
NS_A_DAY = 86_400 * SECOND

CATALOGUE = [
    DatasetDeclaration(
        key="live",
        vendor="Coinbase",
        data_types=["meridian.v1.Trade", "meridian.v1.Quote"],
        modes=["stream"],
        cadence=1,
        licence_default=DatasetLicence(kept=False, personal_use=True),
        venue_id=COINBASE,
    ),
]

EVERY = Eligibility(high_low="eligible", open="eligible", close="eligible", volume="eligible")


def trade(n: int, *, at: int = HOUR, price: str = "62431.27", cancelled: bool = False) -> Trade:
    """A match on the venue's stream, as a crypto dgm records one."""
    return Trade(
        meta=ObservationMeta(
            row_key=f"BTC-USD:match:{n}",
            subjects=[SubjectRef(entity_id=BTC)],
            source=Source(dataset=LIVE, venue_id=COINBASE),
            valid_from_ns=at,
            raw=meridian.RawRecordRef(instance_id=INSTANCE, key=f"matches/{n}"),
        ),
        price=Money(Decimal(price), "USD"),
        quantity=Decimal("0.0153"),
        attributes=TradeAttributes(consolidated=EVERY, market_centre=EVERY),
        aggressor="buy",
        source_sequence=n,
        cancelled=cancelled,
    )


def quote(
    row_key: str, bid: str, *, at: int = HOUR, ask: str | None = None, in_usdc: bool = False
) -> Quote:
    def money(amount: str) -> Money:
        return (
            Money(Decimal(amount), instrument_id=USDC)
            if in_usdc
            else Money(Decimal(amount), "USD")
        )

    return Quote(
        meta=ObservationMeta(
            row_key=row_key,
            subjects=[SubjectRef(entity_id=BTC)],
            source=Source(dataset=LIVE, venue_id=COINBASE),
            valid_from_ns=at,
            raw=meridian.RawRecordRef(instance_id=INSTANCE, key=f"ticker/{row_key}"),
        ),
        bid=money(bid),
        ask=None if ask is None else money(ask),
        bid_quantity=Decimal("1.2"),
    )


async def dgm(sidecar: tuple[FakeSidecar, str]) -> meridian.Plugin:
    service, address = sidecar
    service.instance_id = INSTANCE
    service.roles = ("dgm",)
    return await meridian.connect(
        address, heartbeat=False, declaration=Declaration(catalogue=CATALOGUE)
    )


async def heard_until(
    service: FakeSidecar,
    reader: meridian.Plugin,
    done: object,
    **handlers: object,
) -> None:
    """Receive with `handlers` until `done()` holds, then stop."""
    task = asyncio.create_task(reader.receive(**handlers))  # type: ignore[arg-type]
    try:
        for _ in range(200):
            if done():  # type: ignore[operator]
                break
            await asyncio.sleep(0.02)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


# ── Recording ───────────────────────────────────────────────────────────────


async def test_a_trade_is_recorded_its_price_resolved_and_a_withdrawal_a_new_version(
    sidecar,
) -> None:
    service, _ = sidecar
    plugin = await dgm(sidecar)
    try:
        first = await plugin.record_trades(trades=[trade(1)])
        withdrawn = await plugin.record_trades(trades=[trade(1, cancelled=True)])
        again = await plugin.record_trades(trades=[trade(1, cancelled=True)])
    finally:
        await plugin.leave()
    assert (first.recorded, withdrawn.restated, again.unchanged) == (1, 1, 1)
    (sent, *_) = [s for s in service.operations.sent if isinstance(s, ops.RecordTradesParams)]
    held = sent.trades[0]
    assert held.aggressor == ops.AGGRESSOR_BUY
    assert held.attributes.consolidated.close == ops.ELIGIBLE_ELIGIBLE
    assert held.meta.business_date == ""  # keyed by UTC instants
    kept = service.operations.lake.rows
    assert [r.cancelled for r in kept] == [False, True]
    assert kept[0].price.instrument_id == "LCL-CASH-USD"
    assert [type(e) for e in service.operations.lake.published] == [ops.TradesRecordedEvent] * 2


async def test_a_batch_of_trades_or_quotes_is_refused_outside_1_to_500_before_sending(
    sidecar,
) -> None:
    service, _ = sidecar
    plugin = await dgm(sidecar)
    try:
        with pytest.raises(ValueError, match="trades"):
            await plugin.record_trades(trades=[])
        with pytest.raises(ValueError, match="quotes"):
            await plugin.record_quotes(quotes=[quote(f"q{n}", "1") for n in range(501)])
        with pytest.raises(ValueError, match=r"trades\[0\]\.aggressor"):
            await plugin.record_trades(
                trades=[
                    Trade(meta=trade(1).meta, price=trade(1).price, quantity=1, aggressor="up")
                ]
            )
    finally:
        await plugin.leave()
    assert not [
        s
        for s in service.operations.sent
        if isinstance(s, ops.RecordTradesParams | ops.RecordQuotesParams)
    ]


async def test_a_one_sided_quote_is_recorded_and_one_in_two_assets_refused(sidecar) -> None:
    service, _ = sidecar
    plugin = await dgm(sidecar)
    try:
        answered = await plugin.record_quotes(quotes=[quote("q1", "62431.26")])
        mixed = Quote(
            meta=quote("q2", "1").meta,
            bid=Money(Decimal("62431.26"), "USD"),
            ask=Money(Decimal("62431.27"), instrument_id=USDC),
        )
        with pytest.raises(meridian.CallFailed, match=r"quotes\[0\]: a quote's two sides"):
            await plugin.record_quotes(quotes=[mixed])
    finally:
        await plugin.leave()
    assert answered.recorded == 1
    (held,) = service.operations.lake.rows
    assert held.HasField("bid") and not held.HasField("ask")


# ── Reading ─────────────────────────────────────────────────────────────────


async def test_trades_are_read_over_a_range_within_a_day_or_after_a_watermark(sidecar) -> None:
    service, address = sidecar
    writer = await dgm(sidecar)
    reader = await meridian.connect(address, heartbeat=False)
    try:
        first = await writer.record_trades(trades=[trade(1), trade(2, at=HOUR + SECOND)])
        # A late print: recorded after, valid before the range a reader read.
        await writer.record_trades(trades=[trade(3, at=HOUR - 60 * SECOND)])
        ranged = await reader.list_trades(
            subjects=[SubjectRef(entity_id=BTC)],
            valid_from_ns=HOUR,
            valid_until_ns=HOUR + 60 * SECOND,
        )
        caught = await reader.list_trades(
            subjects=[SubjectRef(entity_id=BTC)],
            sources=SourceChoice(side_by_side=True),
            after_watermark=first.watermark,
        )
        with pytest.raises(meridian.CallFailed, match="within one day"):
            await reader.list_trades(
                subjects=[SubjectRef(entity_id=BTC)],
                valid_from_ns=HOUR,
                valid_until_ns=HOUR + NS_A_DAY + 1,
            )
    finally:
        await reader.leave()
        await writer.leave()
    assert [t.source_sequence for t in ranged.trades] == [1, 2]
    assert [t.source_sequence for t in caught.trades] == [3]
    assert [d.dataset for d in caught.datasets] == [LIVE]


async def test_the_latest_quotes_are_one_per_venue_and_asset(sidecar) -> None:
    service, address = sidecar
    writer = await dgm(sidecar)
    reader = await meridian.connect(address, heartbeat=False)
    try:
        await writer.record_quotes(
            quotes=[
                quote("usd-1", "62431.26"),
                quote("usd-2", "62431.50", at=HOUR + SECOND),
                quote("usdc-1", "62440.10", in_usdc=True),
            ]
        )
        latest = await reader.list_quotes(subjects=[SubjectRef(entity_id=BTC)])
    finally:
        await reader.leave()
        await writer.leave()
    assert sorted(q.meta.row_key for q in latest.quotes) == ["usd-2", "usdc-1"]


# ── Hearing ─────────────────────────────────────────────────────────────────


def test_trades_are_heard_in_full_and_quotes_latest_value_first() -> None:
    assert [(row.name, row.caught_up_by) for row in UNCONFLATED] == [
        ("TradesRecorded", "list_trades")
    ]
    assert {"TradesRecorded", "QuotesRecorded"} <= HEARD


async def test_every_trade_is_heard_and_a_loss_caught_up_after_the_watermark_last_seen(
    sidecar,
) -> None:
    service, address = sidecar
    writer = await dgm(sidecar)
    await writer.record_trades(trades=[trade(1), trade(2)])
    one, two = service.operations.lake.published
    # Lost on the stream: recorded while the reader was too slow, one a late
    # print valid before what it had heard.
    await writer.record_trades(trades=[trade(3), trade(4, at=HOUR - 60 * SECOND)])
    three, four = service.operations.lake.published[2:]
    service.operations.streams = [
        Stream(
            deliveries=[
                ops.Delivery(trades_recorded=one),
                # The same subject, dataset and venue: never dropped for a later one.
                ops.Delivery(trades_recorded=two),
                ops.Delivery(lost=ops.Lost(rows=["TradesRecorded"], dropped=2)),
                # Delivered after the catch-up read had it: handed on once.
                ops.Delivery(trades_recorded=four),
            ]
        )
    ]
    heard: list[meridian.Heard[ops.TradesRecordedEvent]] = []

    async def traded(row: meridian.Heard[ops.TradesRecordedEvent]) -> None:
        heard.append(row)

    reader = await meridian.connect(address, heartbeat=False)
    try:
        await heard_until(
            service, reader, lambda: len(heard) >= 4, trades_recorded=traded, subjects=[BTC]
        )
    finally:
        await reader.leave()
        await writer.leave()
    (asked,) = service.operations.received
    assert list(asked.rows) == ["TradesRecorded"] and list(asked.subjects) == [BTC]
    # Nothing is read on start: there is no latest trade to seed with.
    (read,) = [r for r in service.operations.reads if isinstance(r, ops.ListTradesParams)]
    assert read.sources.side_by_side and [s.entity_id for s in read.subjects] == [BTC]
    assert [(p.partition, p.sequence) for p in read.after_watermark.partitions] == [(LIVE, 2)]
    assert [(h.message.trade.source_sequence, h.caught_up) for h in heard] == [
        (1, False),
        (2, False),
        (3, True),
        (4, True),
    ]
    assert all(h.dataset is not None and h.dataset.vendor == "Coinbase" for h in heard)
    assert three.trade.meta.sequence == 3


async def test_quotes_are_heard_latest_first_per_asset_never_one_asset_for_another(
    sidecar,
) -> None:
    service, address = sidecar
    writer = await dgm(sidecar)
    await writer.record_quotes(quotes=[quote("usd-1", "62431.26")])
    await writer.record_quotes(quotes=[quote("usdc-1", "62440.10", in_usdc=True)])
    await writer.record_quotes(quotes=[quote("usd-2", "62431.50", at=HOUR + SECOND)])
    usd_1, usdc_1, usd_2 = service.operations.lake.published
    service.operations.streams = [
        Stream(
            deliveries=[
                ops.Delivery(quotes_recorded=usd_2),
                # Superseded under its key, by asset: dropped.
                ops.Delivery(quotes_recorded=usd_1),
                # In USDC: its own key, never superseded by a quote in USD.
                ops.Delivery(quotes_recorded=usdc_1),
            ]
        )
    ]
    heard: list[meridian.Heard[ops.QuotesRecordedEvent]] = []

    async def quoted(row: meridian.Heard[ops.QuotesRecordedEvent]) -> None:
        heard.append(row)

    reader = await meridian.connect(address, heartbeat=False)
    try:
        await heard_until(
            service,
            reader,
            lambda: len(heard) >= 2,
            quotes_recorded=quoted,
            subjects=[BTC],
            seed=False,
        )
    finally:
        await reader.leave()
        await writer.leave()
    assert [h.message.quote.meta.row_key for h in heard] == ["usd-2", "usdc-1"]


async def test_prices_in_two_assets_on_one_venue_are_two_keys(sidecar) -> None:
    """From contract v19 a price's key holds the asset it is in: BTC priced
    in USD and in USDC on one venue are two values, and neither supersedes
    the other (W10.5)."""
    from meridian.operations import CONFLATED
    from meridian.receive import _Latest

    (prices,) = [row for row in CONFLATED if row.name == "PricesRecorded"]
    in_usd = ops.Price(
        meta=ops.ObservationMeta(source=ops.Source(dataset=LIVE, venue_id=COINBASE)),
        kind=ops.PRICE_KIND_LAST,
        price=ops.Money(instrument_id="LCL-CASH-USD"),
    )
    in_usdc = ops.Price()
    in_usdc.CopyFrom(in_usd)
    in_usdc.price.instrument_id = USDC
    assert _Latest._key(prices, in_usd) != _Latest._key(prices, in_usdc)


# ── The reading suites ──────────────────────────────────────────────────────


def reading(role: str) -> dict[str, object]:
    """A reader as a signal or an ems plugin writes one: each case run
    through its own reads and handlers."""

    async def datasets(recorder: Recorder) -> None:
        await recorder.list_datasets()

    async def closes(recorder: Recorder) -> None:
        await recorder.list_prices(
            subjects=[SubjectRef(entity_id=BTC)], kinds=["close"], business_date="2026-10-08"
        )

    async def bars(recorder: Recorder) -> None:
        await recorder.list_bars(
            subjects=[SubjectRef(entity_id=BTC)],
            valid_from_ns=HOUR,
            valid_until_ns=HOUR + NS_A_DAY,
        )

    async def trades(recorder: Recorder) -> None:
        await recorder.list_trades(
            subjects=[SubjectRef(entity_id=BTC)],
            valid_from_ns=HOUR,
            valid_until_ns=HOUR + 60 * SECOND,
        )

    async def caught_up(recorder: Recorder) -> None:
        await recorder.list_trades(
            subjects=[SubjectRef(entity_id=BTC)],
            after_watermark=ops.Watermark(
                partitions=[ops.PartitionSequence(partition=LIVE, sequence=2)]
            ),
        )

    async def quotes(recorder: Recorder) -> None:
        await recorder.list_quotes(subjects=[SubjectRef(entity_id=BTC)])

    def hearing(row: str, message: object, arm: str):  # type: ignore[no-untyped-def]
        async def produce(recorder: Recorder) -> None:
            async def heard(_: object) -> None:
                return None

            recorder.answer(row, lambda _: message)
            await recorder.receive(**{arm: heard}, subjects=[BTC])

        return produce

    cases = {
        "reads-the-datasets-it-may-read": datasets,
        "reads-a-business-dates-closes": closes,
        "hears-a-price-recorded": hearing(
            "PricesRecorded", ops.PricesRecordedEvent(price=ops.Price()), "prices_recorded"
        ),
        "reads-daily-bars-over-a-range": bars,
        "hears-a-bar-recorded": hearing(
            "BarsRecorded", ops.BarsRecordedEvent(bar=ops.Bar()), "bars_recorded"
        ),
        "reads-trades-over-a-range": trades,
        "hears-a-trade-recorded": hearing(
            "TradesRecorded", ops.TradesRecordedEvent(trade=ops.Trade()), "trades_recorded"
        ),
        "catches-up-trades-after-a-watermark": caught_up,
        "reads-the-latest-quotes": quotes,
        "hears-a-quote-recorded": hearing(
            "QuotesRecorded", ops.QuotesRecordedEvent(quote=ops.Quote()), "quotes_recorded"
        ),
    }
    held = {case.name for case in suite(role).cases}
    return {name: made for name, made in cases.items() if name in held}


@pytest.mark.parametrize("role", ["signal", "ems"])
def test_a_reader_of_trades_and_quotes_passes_its_suite(role: str) -> None:
    report = run(role, reading(role))
    assert report.passed, report.failures


def test_the_ems_suite_is_carried_with_its_six_cases() -> None:
    held = suite("ems")
    assert held.since == "v19"
    assert [case.name for case in held.cases] == [
        "reads-the-datasets-it-may-read",
        "reads-trades-over-a-range",
        "hears-a-trade-recorded",
        "catches-up-trades-after-a-watermark",
        "reads-the-latest-quotes",
        "hears-a-quote-recorded",
    ]


def test_a_reader_catching_up_by_range_alone_fails_the_watermark_case() -> None:
    cases = reading("signal")
    cases["catches-up-trades-after-a-watermark"] = cases["reads-trades-over-a-range"]
    report = run("signal", cases)
    assert set(report.failures) == {"catches-up-trades-after-a-watermark"}
