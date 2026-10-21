"""The lake's 1a through the SDK (contract v18): a data plugin's catalogue, prices and
bars recorded in batches, wants heard, recorded against and declined, the
readers' reads by business date, as of and side by side, the rows heard
latest value first with their dataset, venues resolved, a Money naming its
instrument, dates typed, and the data suite a data plugin holds itself to,
with its 1b cases from contract v19 (tests/test_trades_and_quotes.py has the
rest of the 1b).

Against the fake sidecar (conftest), which mirrors the lake, money
resolution and venue resolution as core's sidecar and lake answer them.
"""

from __future__ import annotations

import asyncio
import dataclasses
from datetime import UTC, date, datetime
from decimal import Decimal

import grpc
import pytest

import meridian
from conftest import FakeSidecar, Stream
from meridian import (
    Bar,
    CallFailed,
    DatasetDeclaration,
    DatasetLicence,
    Declaration,
    Money,
    ObservationMeta,
    Price,
    Source,
    SourceChoice,
    SourceTime,
    SubjectRef,
    Trade,
)
from meridian.edge import as_reported
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles.data import backfill_restart
from meridian.roles.data.testing import RATES_CASES, feed_delay, rates_producers
from meridian.suites import Recorder, check, names, run, suite
from order_path_cases import PRODUCERS
from rates_cases import PUBLISHED, RATES

INSTANCE = "data-coinbase-1"
DAILY = f"{INSTANCE}:daily"
LIVE = f"{INSTANCE}:live"
BTC = "LCL-01JA00000000000000BTC1"
ETH = "LCL-01JA00000000000000ETH1"
USDC = "LCL-01JA0000000000000USDC1"
COINBASE = "VEN-01JA0000000000000CBEXC"
DAY = 1_791_331_200_000_000_000  # 2026-10-08 00:00 UTC
NS_A_DAY = 86_400_000_000_000
#: An instrument the deployment holds from a custodian, which the toy data plugin
#: never resolved: its record carries the custodian's symbol and a CUSIP.
ELSEWHERE = "LCL-01JA0000000000000QQQ1"
RECORD_ELSEWHERE = ops.ResolveInstrumentResult(
    found=True,
    instrument=ops.InstrumentRecord(
        instrument_id=ELSEWHERE,
        identifiers=[
            ops.Identifier(scheme="cusip", value="46090E103"),
            ops.Identifier(scheme="symbol", value="QQQ", source="snaptrade"),
        ],
    ),
)

CATALOGUE = [
    DatasetDeclaration(
        key="daily",
        vendor="Coinbase",
        data_types=["meridian.v1.Price", "meridian.v1.Bar", "meridian.v1.Bar.trade_count"],
        modes=["pull", "push"],
        cadence=86_400,
        history=3650,
        licence_default=DatasetLicence(kept=True, personal_use=True),
        day_time_zone="Etc/UTC",
        venue_id=COINBASE,
    ),
    DatasetDeclaration(
        key="live",
        vendor="Coinbase",
        data_types=["meridian.v1.Price"],
        modes=["stream"],
        cadence=1,
        licence_default=DatasetLicence(kept=False, personal_use=True),
        venue_id=COINBASE,
    ),
]


def close(
    amount: str,
    *,
    subject: str = BTC,
    dataset: str = DAILY,
    day: date = date(2026, 10, 8),
    money: Money | None = None,
    row_key: str | None = None,
    forming: bool = False,
) -> Price:
    """A daily close as a crypto data plugin records one: its candle's day."""
    start = int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp()) * 10**9
    return Price(
        meta=ObservationMeta(
            row_key=row_key or f"{subject}:1d:{start // 10**9}",
            subjects=[SubjectRef(entity_id=subject)],
            source=Source(dataset=dataset, venue_id=COINBASE),
            valid_from_ns=start,
            valid_until_ns=start + NS_A_DAY,
            business_date=day,
            source_times=[SourceTime(kind="published", at_ns=start + NS_A_DAY)],
            raw=meridian.RawRecordRef(instance_id=INSTANCE, key=f"candles/{start}"),
        ),
        kind="close",
        price=money or Money(Decimal(amount), "USD"),
        basis="per_unit",
    )


async def data_plugin(sidecar: tuple[FakeSidecar, str]) -> meridian.Plugin:
    service, address = sidecar
    service.instance_id = INSTANCE
    service.roles = ("data",)
    return await meridian.connect(
        address, heartbeat=False, declaration=Declaration(catalogue=CATALOGUE)
    )


# ── The catalogue ───────────────────────────────────────────────────────────


async def test_a_data_plugin_declares_its_catalogue_from_code(sidecar) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    await plugin.leave()
    (sent,) = service.registered
    datasets = sent.declaration.catalogue.datasets
    assert [d.key for d in datasets] == ["daily", "live"]
    daily = datasets[0]
    assert list(daily.modes) == [meridian.ObservationMode.Value("OBSERVATION_MODE_PULL"), 2]
    assert daily.day_time_zone == "Etc/UTC" and daily.day_end_minute == 0
    assert daily.venue_id == COINBASE
    assert daily.licence_default.kept and daily.licence_default.personal_use
    assert not daily.licence_default.dataset  # empty in a catalogue's default
    upload = Declaration(catalogue=CATALOGUE).to_json()["catalogue"]["datasets"][0]
    assert upload["modes"] == ["pull", "push"]
    assert upload["licence_default"]["personal_use"] is True
    # A version declaring none uploads what it did before v18.
    assert "catalogue" not in Declaration().to_json()


@pytest.mark.parametrize(
    ("change", "said"),
    [
        ({"key": "Daily"}, "lowercase"),
        ({"key": "x" * 41}, "1 to 40"),
        ({"vendor": ""}, "vendor is 1 to 64"),
        ({"data_types": []}, "1 to 32"),
        ({"data_types": ["meridian.v1.Nothing"]}, "no data type or field"),
        ({"data_types": ["meridian.v1.Price", "meridian.v1.Price"]}, "twice"),
        ({"modes": []}, "1 to 3 modes"),
        ({"modes": ["pull", "pull"]}, "a mode twice"),
        ({"modes": ["sometimes"]}, "does not define"),
        ({"day_time_zone": "Mars/Olympus_Mons"}, "no IANA time zone"),
        ({"day_end_minute": 1440}, "0 to 1439"),
        ({"venue_id": "XNAS"}, "no venue master ID"),
        ({"cadence": -1}, "0 or more"),
    ],
)
def test_a_dataset_past_the_dictionarys_bounds_is_refused_here(change, said) -> None:
    given = {
        "key": "daily",
        "vendor": "Coinbase",
        "data_types": ["meridian.v1.Price"],
        "modes": ["pull"],
        **change,
    }
    with pytest.raises(ValueError, match=said):
        DatasetDeclaration(**given)


def test_a_catalogue_holds_each_key_once_and_only_a_data_plugin_declares_one() -> None:
    with pytest.raises(ValueError, match="declared twice"):
        Declaration(catalogue=[CATALOGUE[0], CATALOGUE[0]])
    with pytest.raises(ValueError, match="no entry of the data dictionary"):
        DatasetLicence(default_fields=["meridian.v1.Bar.nothing"])
    declared = Declaration(catalogue=CATALOGUE)
    assert declared.refused_for(["data"]) is None
    assert "only a data plugin" in (declared.refused_for(["custody"]) or "")


async def test_a_catalogue_from_a_plugin_not_holding_data_is_refused_by_the_sidecar(
    sidecar,
) -> None:
    _, address = sidecar
    with pytest.raises(meridian.Refused, match="data"):
        await meridian.connect(
            address, heartbeat=False, declaration=Declaration(catalogue=CATALOGUE)
        )


# ── Recording ───────────────────────────────────────────────────────────────


async def test_a_batch_is_refused_outside_1_to_500_before_anything_is_sent(sidecar) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    try:
        with pytest.raises(ValueError, match="prices holds 0 rows; a batch is 1 to 500"):
            await plugin.record_prices(prices=[])
        many = [close("1", row_key=f"r{n}") for n in range(501)]
        with pytest.raises(ValueError, match="prices holds 501 rows"):
            await plugin.record_prices(prices=many)
        assert service.operations.sent == []
        done = await plugin.record_prices(prices=many[:500])
        assert done.recorded == 500
        assert done.watermark.partitions[0].sequence == 500
    finally:
        await plugin.leave()


async def test_a_close_is_recorded_its_money_resolved_dated_to_the_cash_instrument(
    sidecar,
) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    try:
        done = await plugin.record_prices(prices=[close("62431.27")])
        assert (done.recorded, done.restated, done.unchanged) == (1, 0, 0)
        (kept,) = service.operations.lake.rows
        assert kept.price.currency_code == "USD"
        assert kept.price.instrument_id == "LCL-CASH-USD"
        assert kept.meta.source.instance == INSTANCE  # the sidecar's, stamped
        assert kept.meta.business_date == "2026-10-08"  # a date, as its ISO text
        assert (kept.meta.version, kept.meta.sequence) == (1, 1)
        # A code that names a new instrument from a date resolves by the row's.
        await plugin.record_prices(
            prices=[
                close("1", day=date(2026, 6, 30), money=Money(Decimal(1), "XTS"), row_key="a"),
                close("1", day=date(2026, 7, 1), money=Money(Decimal(1), "XTS"), row_key="b"),
            ]
        )
        assert [r.price.instrument_id for r in service.operations.lake.rows[1:]] == [
            "LCL-CASH-XTS-1",
            "LCL-CASH-XTS-2",
        ]
    finally:
        await plugin.leave()


async def test_a_token_is_named_by_its_instrument_never_by_a_code(sidecar) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    try:
        stable = close(
            "2410.5", subject=ETH, money=Money(Decimal("2410.5"), instrument_id=USDC)
        )
        await plugin.record_prices(prices=[stable])
        assert service.operations.lake.rows[0].price.instrument_id == USDC
        assert not service.operations.lake.rows[0].price.currency_code
        with pytest.raises(CallFailed, match=r"prices\[0\]\.price\.currency_code: USDC"):
            await plugin.record_prices(prices=[close("1", money=Money(Decimal(1), "USDC"))])
        with pytest.raises(CallFailed, match="two assets"):
            await plugin.record_prices(
                prices=[close("1", money=Money(Decimal(1), "USD", instrument_id=USDC))]
            )
        with pytest.raises(ValueError, match="names no asset"):
            await plugin.record_prices(prices=[close("1", money=Money(Decimal(1)))])
    finally:
        await plugin.leave()


async def test_the_forming_day_is_restated_and_a_repeat_by_value_changes_nothing(
    sidecar,
) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    try:
        await plugin.record_prices(prices=[close("764.2")])
        again = await plugin.record_prices(prices=[close("764.20")])
        assert (again.recorded, again.unchanged) == (0, 1)
        filled = await plugin.record_prices(prices=[close("765.01")])
        assert filled.restated == 1
        first, second = service.operations.lake.rows
        assert first.meta.row_key == second.meta.row_key
        assert (first.meta.version, second.meta.version) == (1, 2)
        assert second.meta.previous_sequence == first.meta.sequence
    finally:
        await plugin.leave()


async def test_a_row_the_sidecar_refuses_is_named_by_its_item_and_field(sidecar) -> None:
    plugin = await data_plugin(sidecar)
    try:
        with pytest.raises(CallFailed, match=r"prices\[1\]\.meta\.source\.dataset"):
            await plugin.record_prices(
                prices=[close("1"), close("1", dataset=f"{INSTANCE}:hourly", row_key="x")]
            )
        stranger = close("1")
        stranger = Price(
            meta=ObservationMeta(
                row_key="v",
                subjects=[SubjectRef(entity_id=BTC)],
                source=Source(dataset=DAILY, venue_id="VEN-NOT-HELD"),
                business_date="2026-10-08",
            ),
            kind="close",
            price=Money(Decimal(1), "USD"),
        )
        with pytest.raises(CallFailed, match=r"prices\[0\]\.meta\.source\.venue_id"):
            await plugin.record_prices(prices=[stranger])
    finally:
        await plugin.leave()


async def test_a_bar_without_a_vwap_is_recorded_and_one_in_two_assets_refused(sidecar) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)

    def bar(close_in: Money, vwap: Money | None = None) -> Bar:
        return Bar(
            meta=ObservationMeta(
                row_key="BTC-USD:1d",
                subjects=[SubjectRef(entity_id=BTC)],
                source=Source(dataset=DAILY),
                valid_from_ns=DAY,
                valid_until_ns=DAY + NS_A_DAY,
                business_date=date(2026, 10, 8),
                raw=meridian.RawRecordRef(instance_id=INSTANCE, key="candles/1"),
            ),
            open=Money(Decimal("61000"), "USD"),
            high=Money(Decimal("62900"), "USD"),
            low=Money(Decimal("60500.5"), "USD"),
            close=close_in,
            volume=Decimal("1234.56789012"),
            vwap=vwap,
        )

    try:
        done = await plugin.record_bars(bars=[bar(Money(Decimal("62431.27"), "USD"))])
        assert done.recorded == 1
        (kept,) = service.operations.lake.rows
        assert not kept.HasField("vwap") and not kept.HasField("trade_count")
        with pytest.raises(CallFailed, match="one asset"):
            await plugin.record_bars(bars=[bar(Money(Decimal(1), instrument_id=USDC))])
    finally:
        await plugin.leave()


# ── Dates ───────────────────────────────────────────────────────────────────


async def test_a_date_is_a_date_and_text_that_is_no_date_is_refused_naming_it(sidecar) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    try:
        for given in ("2026-02-30", "20261008", "2026-W41-4", "8 Oct 2026"):
            bad = close("1")
            bad = Price(
                meta=ObservationMeta(
                    row_key="d",
                    subjects=bad.meta.subjects,
                    source=bad.meta.source,  # type: ignore[union-attr]
                    business_date=given,
                ),
                kind="close",
                price=Money(Decimal(1), "USD"),
            )
            with pytest.raises(
                ValueError, match=r"prices\[0\]\.meta\.business_date .* no date"
            ):
                await plugin.record_prices(prices=[bad])
        moment = datetime(2026, 10, 8, 16, 0, tzinfo=UTC)
        with pytest.raises(TypeError, match="business_date is a date, not a moment"):
            await plugin.list_prices(subjects=[SubjectRef(entity_id=BTC)], business_date=moment)
        assert service.operations.sent == []
        # A date, or its ISO text, crosses as the text.
        await plugin.list_prices(
            subjects=[SubjectRef(entity_id=BTC)], business_date=date(2026, 10, 8)
        )
        await plugin.list_prices(
            subjects=[SubjectRef(entity_id=BTC)], business_date="2026-10-08"
        )
        assert [r.business_date for r in service.operations.reads] == ["2026-10-08"] * 2
    finally:
        await plugin.leave()


async def test_every_date_field_takes_a_date(sidecar) -> None:
    """Not the lake's alone: the dictionary types each of these `date`."""
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        await plugin.record_holdings_statement(
            source="toy", external_statement_id="S", as_of_date=date(2026, 9, 12)
        )
        assert service.operations.sent[-1].as_of_date == "2026-09-12"
        with pytest.raises(ValueError, match="as_of_date is '2026-13-01', which is no date"):
            await plugin.record_holdings_statement(source="toy", as_of_date="2026-13-01")
    finally:
        await plugin.leave()


# ── Reading ─────────────────────────────────────────────────────────────────


async def recorded_two_datasets(plugin: meridian.Plugin) -> None:
    await plugin.record_prices(prices=[close("62431.27")])
    live = close("62440.00", dataset=LIVE, row_key="live-1")
    await plugin.record_prices(prices=[live])


async def test_a_reader_reads_by_business_date_by_default_named_or_side_by_side(
    sidecar,
) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    subjects = [SubjectRef(entity_id=BTC), SubjectRef(entity_id="LCL-NOBODY")]
    try:
        await recorded_two_datasets(plugin)
        by_date = await plugin.list_prices(
            subjects=subjects, kinds=["close"], business_date=date(2026, 10, 8)
        )
        assert [p.meta.source.dataset for p in by_date.prices] == [DAILY]
        assert by_date.datasets[0].vendor == "Coinbase"
        (missed,) = by_date.unanswered
        assert missed.subject.entity_id == "LCL-NOBODY"
        assert missed.reason == ops.UNANSWERED_REASON_NOT_COVERED
        service.operations.lake.priority["meridian.v1.Price"] = [LIVE, DAILY]
        default = await plugin.list_prices(subjects=subjects[:1])
        assert [p.meta.source.dataset for p in default.prices] == [LIVE]
        named = await plugin.list_prices(
            subjects=subjects[:1], sources=SourceChoice(named=[DAILY])
        )
        assert [p.meta.source.dataset for p in named.prices] == [DAILY]
        both = await plugin.list_prices(
            subjects=subjects[:1], sources=SourceChoice(side_by_side=True)
        )
        assert sorted(p.meta.source.dataset for p in both.prices) == [DAILY, LIVE]
        assert sorted(d.dataset for d in both.datasets) == [DAILY, LIVE]
    finally:
        await plugin.leave()


async def test_a_read_as_of_a_recorded_time_answers_what_the_lake_knew_then(sidecar) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    try:
        await plugin.record_prices(prices=[close("764.2")])
        then = service.operations.lake.rows[0].meta.recorded_at_ns
        await plugin.record_prices(prices=[close("765.01")])
        asked = {"subjects": [SubjectRef(entity_id=BTC)], "business_date": date(2026, 10, 8)}
        now = await plugin.list_prices(**asked)
        before = await plugin.list_prices(**asked, as_of_ns=then)
        assert [(p.meta.version, meridian.as_money(p.price).amount) for p in now.prices] == [
            (2, Decimal("765.01"))
        ]
        assert [(p.meta.version, meridian.as_money(p.price).amount) for p in before.prices] == [
            (1, Decimal("764.2"))
        ]
        bars = await plugin.list_bars(
            subjects=[SubjectRef(entity_id=BTC)], valid_from_ns=DAY, valid_until_ns=DAY + 1
        )
        assert list(bars.bars) == [] and bars.unanswered
    finally:
        await plugin.leave()


async def test_a_reader_learns_the_datasets_it_may_read_with_their_catalogue_entries(
    sidecar,
) -> None:
    plugin = await data_plugin(sidecar)
    try:
        listed = await plugin.list_datasets()
        assert [d.dataset for d in listed.datasets] == [DAILY, LIVE]
        assert listed.datasets[0].declaration.day_time_zone == "Etc/UTC"
        assert {licence.dataset: licence.kept for licence in listed.licences} == {
            DAILY: True,
            LIVE: False,
        }
    finally:
        await plugin.leave()


# ── Venues ──────────────────────────────────────────────────────────────────


async def test_a_venue_resolves_by_its_mic_and_one_not_held_is_reported(sidecar) -> None:
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    try:
        found = await plugin.resolve_venue(
            identifiers=[meridian.Identifier(scheme="iso10383", value="XNAS")], as_of_ns=DAY
        )
        assert found.found and found.venue.venue_id == "VEN-01JA00000000000000XNAS"
        missed = await plugin.resolve_venue(
            identifiers=[meridian.Identifier(scheme="iso10383", value="XXXX")], as_of_ns=DAY
        )
        assert not missed.found and missed.miss_reason == ops.MISS_REASON_NOT_FOUND
        await plugin.report_missing_venue(
            source="coinbase",
            identifiers=[meridian.Identifier(scheme="iso10383", value="XXXX")],
            as_of_ns=DAY,
            reason="not_found",
        )
        assert service.operations.lake.missed_venues[0].identifiers[0].value == "XXXX"
    finally:
        await plugin.leave()


async def test_a_data_plugin_reads_the_record_of_an_instrument_another_source_resolved(
    sidecar,
) -> None:
    # Contract v18, ruled 2026-10-10: a data plugin asks ResolveInstrument (W3.6) to
    # name to its vendor an instrument the book holds from a custodian.
    service, _ = sidecar
    plugin = await data_plugin(sidecar)
    try:
        found = await plugin.resolve_instrument(instrument_id=ELSEWHERE, as_of_ns=DAY)
        assert found.found
        assert [(i.scheme, i.value, i.source) for i in found.instrument.identifiers] == [
            ("cusip", "46090E103", ""),
            ("symbol", "QQQ", "snaptrade"),
        ]
        missing = await plugin.resolve_instrument(instrument_id="LCL-NOT-HELD", as_of_ns=DAY)
        assert not missing.found
        assert [r.instrument_id for r in service.operations.sent[-2:]] == [
            ELSEWHERE,
            "LCL-NOT-HELD",
        ]
    finally:
        await plugin.leave()


# ── Hearing ─────────────────────────────────────────────────────────────────


WANT = ops.ObservationsWantedEvent(
    want_id="WNT-1",
    dataset=DAILY,
    data_type="meridian.v1.Price",
    subjects=[ops.SubjectRef(entity_id=BTC), ops.SubjectRef(entity_id="LCL-NOT-COVERED")],
    kinds=[ops.PRICE_KIND_CLOSE],
    business_date="2026-10-08",
)


async def test_a_data_plugin_hears_a_want_records_against_it_and_declines_what_it_cannot_cover(
    sidecar,
) -> None:
    service, _ = sidecar
    service.operations.streams = [Stream(deliveries=[ops.Delivery(observations_wanted=WANT)])]
    plugin = await data_plugin(sidecar)
    answered = asyncio.Event()

    async def wanted(heard: meridian.Heard[ops.ObservationsWantedEvent]) -> None:
        want = heard.message
        day = date.fromisoformat(want.business_date)
        await plugin.record_prices(prices=[close("62431.27", day=day)], want_id=want.want_id)
        await plugin.decline_want(
            want_id=want.want_id,
            subjects=[ops.SubjectRef(entity_id="LCL-NOT-COVERED")],
            reason="not_covered",
        )
        answered.set()

    task = asyncio.create_task(plugin.receive(observations_wanted=wanted))
    try:
        await asyncio.wait_for(answered.wait(), 5)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await plugin.leave()
    (asked,) = service.operations.received
    assert list(asked.rows) == ["ObservationsWanted"] and list(asked.subjects) == []
    recorded = [s for s in service.operations.sent if isinstance(s, ops.RecordPricesParams)]
    assert recorded[0].want_id == "WNT-1"
    (declined,) = service.operations.lake.declined
    assert declined.reason == ops.UNANSWERED_REASON_NOT_COVERED


async def test_a_reader_hears_prices_latest_first_for_its_subjects_with_their_dataset(
    sidecar,
) -> None:
    service, address = sidecar
    writer = await data_plugin(sidecar)
    await writer.record_prices(prices=[close("764.2")])
    await writer.record_prices(prices=[close("765.01")])
    await writer.record_prices(prices=[close("770", day=date(2026, 10, 9))])
    first, restated, day_9 = service.operations.lake.published
    # Recorded after the read, under the same key: heard.
    day_10 = ops.PricesRecordedEvent()
    day_10.CopyFrom(day_9)
    day_10.price.meta.row_key, day_10.price.meta.sequence = "day-10", 9
    service.operations.streams = [
        Stream(
            deliveries=[
                # Recorded before what the read handed on, under its key: never after it.
                ops.Delivery(prices_recorded=first),
                ops.Delivery(prices_recorded=restated),
                ops.Delivery(prices_recorded=day_10),
                ops.Delivery(lost=ops.Lost(rows=["PricesRecorded"], dropped=3)),
            ]
        )
    ]
    heard: list[meridian.Heard[ops.PricesRecordedEvent]] = []

    async def price(row: meridian.Heard[ops.PricesRecordedEvent]) -> None:
        heard.append(row)

    reader = await meridian.connect(address, heartbeat=False)
    task = asyncio.create_task(reader.receive(prices_recorded=price, subjects=[BTC, BTC]))
    try:
        for _ in range(100):
            reads = [r for r in service.operations.reads if isinstance(r, ops.ListPricesParams)]
            if len(reads) >= 2:
                break
            await asyncio.sleep(0.05)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await reader.leave()
        await writer.leave()
    (asked,) = service.operations.received
    assert list(asked.rows) == ["PricesRecorded"] and list(asked.subjects) == [BTC]
    reads = [r for r in service.operations.reads if isinstance(r, ops.ListPricesParams)]
    assert reads[0].sources.side_by_side and [s.entity_id for s in reads[0].subjects] == [BTC]
    assert len(reads) == 2  # seeded, then read again after the loss
    assert [(h.message.price.meta.row_key, h.caught_up) for h in heard] == [
        (day_9.price.meta.row_key, True),
        ("day-10", False),
    ]
    assert all(h.dataset is not None and h.dataset.vendor == "Coinbase" for h in heard)
    assert heard[0].dataset.declaration.venue_id == COINBASE  # type: ignore[union-attr]


async def test_more_than_500_subjects_are_refused_before_the_stream_opens(sidecar) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)

    async def price(_: object) -> None:
        return None

    try:
        with pytest.raises(ValueError, match="subjects names 501; at most 500"):
            await plugin.receive(prices_recorded=price, subjects=[f"S{n}" for n in range(501)])
        with pytest.raises(TypeError, match="not one string"):
            await plugin.receive(prices_recorded=price, subjects=BTC)
        assert service.operations.received == []
    finally:
        await plugin.leave()


async def test_a_reader_refused_a_read_is_told_so(sidecar) -> None:
    service, address = sidecar
    service.operations.refuse = (grpc.StatusCode.PERMISSION_DENIED, "not entitled")
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(meridian.NotGranted):
            await plugin.list_prices(subjects=[SubjectRef(entity_id=BTC)])
    finally:
        await plugin.leave()


# ── The data suite ───────────────────────────────────────────────────────────


class ToyDataPlugin:
    """A data plugin as a data plugin writes one: its own conversion from its
    source's synthetic exchange, against whatever operations it is given."""

    def __init__(
        self,
        plugin: object,
        *,
        through_float: bool = False,
        forming_as_new: bool = False,
        reads_no_record: bool = False,
        keeps_makers_side: bool = False,
    ) -> None:
        self.plugin = plugin
        self.through_float = through_float
        self.forming_as_new = forming_as_new
        # The mutation: a subject the toy did not resolve itself declined,
        # its record never read.
        self.reads_no_record = reads_no_record
        # The mutation: the side of the resting order a source names sent as
        # the side that took liquidity.
        self.keeps_makers_side = keeps_makers_side

    def amount(self, text: str) -> Decimal:
        # The mutation: a candle's JSON number read through a float.
        return Decimal(float(text)) if self.through_float else Decimal(text)

    async def subject(self, symbol: str) -> str:
        found = await self.plugin.resolve_identifier(  # type: ignore[attr-defined]
            identifiers=[meridian.Identifier(scheme="symbol", value=symbol, source="toy")],
            as_of_ns=DAY,
        )
        return str(found.instrument_id)

    def price(
        self,
        subject: str,
        amount: Decimal,
        *,
        money: Money | None = None,
        venue: str = "",
        row_key: str = "BTC-USD:1d:1791331200",
        until: int = DAY + NS_A_DAY,
    ) -> Price:
        instance = self.plugin.identity.instance_id  # type: ignore[attr-defined]
        return Price(
            meta=ObservationMeta(
                row_key=row_key,
                subjects=[SubjectRef(entity_id=subject)],
                source=Source(dataset=f"{instance}:daily", venue_id=venue),
                valid_from_ns=DAY,
                valid_until_ns=until,
                business_date=date(2026, 10, 8),
                source_times=[SourceTime(kind="published", at_ns=DAY + NS_A_DAY)],
                raw=self.plugin.raw_record("candles/BTC-USD/86400/1791331200"),  # type: ignore[attr-defined]
            ),
            kind="close",
            price=money or Money(amount, "USD"),
            basis="per_unit",
        )

    async def daily_close(self) -> None:
        subject = await self.subject("BTC-USD")
        await self.plugin.record_prices(prices=[self.price(subject, self.amount("62431.27"))])  # type: ignore[attr-defined]

    async def forming_day(self) -> None:
        subject = await self.subject("BTC-USD")
        for n, text in enumerate(("62000.1", "62431.27")):
            key = (
                f"BTC-USD:1d:1791331200:{n}" if self.forming_as_new else "BTC-USD:1d:1791331200"
            )
            until = 0 if self.forming_as_new else DAY + NS_A_DAY
            await self.plugin.record_prices(
                prices=[self.price(subject, Decimal(text), row_key=key, until=until)]
            )  # type: ignore[attr-defined]

    async def exact(self) -> None:
        subject = await self.subject("SHIB-USD")
        await self.plugin.record_prices(
            prices=[self.price(subject, self.amount("0.000012345678901234"))]
        )  # type: ignore[attr-defined]

    async def bar(self) -> None:
        subject = await self.subject("BTC-USD")
        meta = self.price(subject, Decimal(1)).meta
        await self.plugin.record_bars(  # type: ignore[attr-defined]
            bars=[
                Bar(
                    meta=meta,
                    open=Money(Decimal("61000"), "USD"),
                    high=Money(Decimal("62900"), "USD"),
                    low=Money(Decimal("60500.5"), "USD"),
                    close=Money(Decimal("62431.27"), "USD"),
                    volume=Decimal("1234.56789012"),
                )
            ]
        )

    async def fx(self) -> None:
        eur = await self.subject("EUR")
        await self.plugin.record_prices(prices=[self.price(eur, Decimal("1.0921"))])  # type: ignore[attr-defined]

    async def stablecoin(self) -> None:
        eth, usdc = await self.subject("ETH"), await self.subject("USDC")
        money = Money(Decimal("2410.5"), instrument_id=usdc)
        await self.plugin.record_prices(prices=[self.price(eth, Decimal(0), money=money)])  # type: ignore[attr-defined]

    async def ambiguous(self) -> None:
        await self.plugin.report_missing_instrument(  # type: ignore[attr-defined]
            source="toy",
            identifiers=[meridian.Identifier(scheme="symbol", value="USDC", source="toy")],
            as_of_ns=DAY,
            reason="ambiguous",
        )

    async def venue(self) -> None:
        found = await self.plugin.resolve_venue(  # type: ignore[attr-defined]
            identifiers=[meridian.Identifier(scheme="iso10383", value="XNAS")], as_of_ns=DAY
        )
        subject = await self.subject("QQQ")
        await self.plugin.record_prices(
            prices=[self.price(subject, Decimal("501.2"), venue=found.venue.venue_id)]
        )  # type: ignore[attr-defined]

    async def venue_not_held(self) -> None:
        await self.plugin.report_missing_venue(  # type: ignore[attr-defined]
            source="toy",
            identifiers=[meridian.Identifier(scheme="symbol", value="toyx", source="toy")],
            as_of_ns=DAY,
            reason="not_found",
        )

    async def served(self, subject: str) -> bool:
        """Whether the toy's source serves `subject`: one it resolved itself,
        or one another source resolved whose record (W3.6) carries a symbol
        it can name to its source (contract v18, ruled 2026-10-10)."""
        if subject == "LCL-NOT-COVERED":
            return False
        if subject != ELSEWHERE:
            return True
        if self.reads_no_record:
            return False
        found = await self.plugin.resolve_instrument(instrument_id=subject, as_of_ns=DAY)  # type: ignore[attr-defined]
        return bool(found.found) and any(
            i.scheme == "symbol" for i in found.instrument.identifiers
        )

    async def on_want(self, heard: meridian.Heard[ops.ObservationsWantedEvent]) -> None:
        want = heard.message
        served = [await self.served(s.entity_id) for s in want.subjects]
        covered = [s for s, ok in zip(want.subjects, served, strict=True) if ok]
        if covered:
            await self.plugin.record_prices(  # type: ignore[attr-defined]
                prices=[self.price(s.entity_id, Decimal("62431.27")) for s in covered],
                want_id=want.want_id,
            )
        declined = [s for s, ok in zip(want.subjects, served, strict=True) if not ok]
        if declined:
            await self.plugin.decline_want(
                want_id=want.want_id, subjects=declined, reason="not_covered"
            )  # type: ignore[attr-defined]

    async def on_withdrawn(self, heard: meridian.Heard[ops.WantWithdrawnEvent]) -> None:
        return None  # the standing want stops being kept current

    # ── The 1b (contract v19): trades and quotes, from the source's stream ──

    def meta(
        self, subject: str, row_key: str, at_ns: int = DAY + 3_600 * 10**9
    ) -> ObservationMeta:
        instance = self.plugin.identity.instance_id  # type: ignore[attr-defined]
        return ObservationMeta(
            row_key=row_key,
            subjects=[SubjectRef(entity_id=subject)],
            source=Source(dataset=f"{instance}:live", venue_id=COINBASE),
            valid_from_ns=at_ns,
            raw=self.plugin.raw_record(f"matches/{row_key}"),  # type: ignore[attr-defined]
        )

    def trade(
        self,
        subject: str,
        *,
        row_key: str = "BTC-USD:match:1",
        aggressor: str = "buy",
        attributes: meridian.TradeAttributes | None = None,
        unconverted: tuple[ops.AsReported, ...] = (),
        cancelled: bool = False,
    ) -> Trade:
        every = meridian.Eligibility(
            high_low="eligible", open="eligible", close="eligible", volume="eligible"
        )
        meta = self.meta(subject, row_key)
        if unconverted:
            meta = dataclasses.replace(meta, unconverted=unconverted)
        return Trade(
            meta=meta,
            price=Money(Decimal("62431.27"), "USD"),
            quantity=Decimal("0.0153"),
            attributes=attributes
            or meridian.TradeAttributes(consolidated=every, market_centre=every),
            aggressor=aggressor,
            source_sequence=1,
            cancelled=cancelled,
        )

    async def a_trade(self) -> None:
        subject = await self.subject("BTC-USD")
        await self.plugin.record_trades(trades=[self.trade(subject)])  # type: ignore[attr-defined]

    async def makers_side(self) -> None:
        # The source names the resting order's side, a sell: the buyer took it.
        stated = "sell"
        taker = stated if self.keeps_makers_side else {"sell": "buy", "buy": "sell"}[stated]
        subject = await self.subject("BTC-USD")
        await self.plugin.record_trades(trades=[self.trade(subject, aggressor=taker)])  # type: ignore[attr-defined]

    async def condition_converted(self) -> None:
        # An odd lot: neither the high and low nor the close, its volume counted.
        rule = meridian.Eligibility(
            high_low="not_eligible",
            open="not_eligible",
            close="not_eligible",
            volume="eligible",
        )
        subject = await self.subject("QQQ")
        attributes = meridian.TradeAttributes(
            consolidated=rule, market_centre=rule, characteristics=["odd_lot"]
        )
        await self.plugin.record_trades(  # type: ignore[attr-defined]
            trades=[self.trade(subject, attributes=attributes)]
        )

    async def condition_not_converted(self) -> None:
        subject = await self.subject("QQQ")
        await self.plugin.record_trades(  # type: ignore[attr-defined]
            trades=[
                self.trade(
                    subject,
                    attributes=meridian.TradeAttributes(),
                    unconverted=(as_reported("toy:conditions", "Q7"),),
                )
            ]
        )

    async def withdrawn_trade(self) -> None:
        subject = await self.subject("BTC-USD")
        await self.plugin.record_trades(trades=[self.trade(subject)])  # type: ignore[attr-defined]
        await self.plugin.record_trades(trades=[self.trade(subject, cancelled=True)])  # type: ignore[attr-defined]

    def quote(self, subject: str, *, ask: bool = True) -> meridian.Quote:
        return meridian.Quote(
            meta=self.meta(subject, "BTC-USD:ticker:1"),
            bid=Money(Decimal("62431.26"), "USD"),
            ask=Money(Decimal("62431.27"), "USD") if ask else None,
            bid_quantity=Decimal("1.2"),
            ask_quantity=Decimal("0.4") if ask else None,
        )

    async def a_quote(self) -> None:
        subject = await self.subject("BTC-USD")
        await self.plugin.record_quotes(quotes=[self.quote(subject)])  # type: ignore[attr-defined]

    async def one_sided(self) -> None:
        subject = await self.subject("BTC-USD")
        await self.plugin.record_quotes(quotes=[self.quote(subject, ask=False)])  # type: ignore[attr-defined]

    async def backfilled(self) -> None:
        """On start (contract v20): the last trade this instance recorded of
        a streamed subject, as the lake answers it, and the two the venue's
        history states since, recorded before the stream resumes."""
        subject = await self.subject("BTC-USD")

        async def history(last: ops.Trade) -> list[Trade]:
            assert last.meta.subjects[0].entity_id == subject
            return [self.trade(subject, row_key=f"BTC-USD:match:{n}") for n in (2, 3)]

        await backfill_restart(self.plugin, [subject], history)

    async def licences(self) -> None:
        """On start (contract v20): its own declared datasets' licences."""
        await self.plugin.list_datasets()  # type: ignore[attr-defined]

    async def on_trades_wanted(
        self, heard: meridian.Heard[ops.ObservationsWantedEvent]
    ) -> None:
        """A standing want of the live dataset: its subjects kept current
        from the source's stream, which states a trade for one."""
        want = heard.message
        if want.standing and want.data_type == "meridian.v1.Trade":
            await self.plugin.record_trades(  # type: ignore[attr-defined]
                trades=[self.trade(s.entity_id) for s in want.subjects], want_id=want.want_id
            )


def outcome_producer(determination: str, *stages: str):  # type: ignore[no-untyped-def]
    # Contract v23: the source's determination of an event contract,
    # each stage a new version under the contract's one row key.
    async def produce(recorder: Recorder) -> None:
        for stage in stages or ("determined",):
            await recorder.record_outcomes(
                outcomes=[
                    meridian.Outcome(
                        meta=meridian.ObservationMeta(
                            row_key="KXFEDDECISION-26OCT-H0:outcome",
                            subjects=[ops.SubjectRef(entity_id="INS-KXFED-H0")],
                            source=ops.Source(dataset=DAILY),
                            valid_from_ns=DAY,
                            raw=ops.RawRecordRef(instance_id=INSTANCE, key="market:1"),
                        ),
                        determination=determination,
                        stage=stage,
                        settlement_value=meridian.Money(
                            Decimal("1.00" if determination == "pays" else "0.50"), "USD"
                        ),
                        determination_as_reported=ops.AsReported(
                            scheme="venue",
                            code="yes" if determination == "pays" else "scalar",
                        ),
                    )
                ]
            )

    return produce


def producers(**mutations: bool) -> dict[str, object]:
    def made(step: str):  # type: ignore[no-untyped-def]
        async def produce(recorder: Recorder) -> None:
            await getattr(ToyDataPlugin(recorder, **mutations), step)()

        return produce

    def wanted(subjects: list[str]):  # type: ignore[no-untyped-def]
        async def produce(recorder: Recorder) -> None:
            toy = ToyDataPlugin(recorder, **mutations)
            want = ops.ObservationsWantedEvent()
            want.CopyFrom(WANT)
            del want.subjects[:]
            want.subjects.extend(ops.SubjectRef(entity_id=s) for s in subjects)
            recorder.answer("ObservationsWanted", lambda _: want)
            recorder.answer("ResolveInstrument", lambda _: RECORD_ELSEWHERE)
            await recorder.receive(observations_wanted=toy.on_want)

        return produce

    async def withdrawn(recorder: Recorder) -> None:
        toy = ToyDataPlugin(recorder, **mutations)
        recorder.answer(
            "WantWithdrawn", lambda _: [ops.WantWithdrawnEvent(want_id="WNT-1", dataset=DAILY)]
        )
        await recorder.receive(want_withdrawn=toy.on_withdrawn)

    async def streamed(recorder: Recorder) -> None:
        toy = ToyDataPlugin(recorder, **mutations)
        want = ops.ObservationsWantedEvent(
            want_id="WNT-2",
            dataset=LIVE,
            data_type="meridian.v1.Trade",
            subjects=[ops.SubjectRef(entity_id=BTC)],
            standing=True,
        )
        recorder.answer("ObservationsWanted", lambda _: want)
        await recorder.receive(observations_wanted=toy.on_trades_wanted)

    outcome = outcome_producer

    disputed = outcome("pays", "determined", "disputed")

    async def restarted(recorder: Recorder) -> None:
        last = ops.Trade(
            meta=ops.ObservationMeta(
                row_key="BTC-USD:match:1",
                subjects=[ops.SubjectRef(entity_id="INS-suite-1")],
                source=ops.Source(dataset=LIVE, venue_id=COINBASE),
                valid_from_ns=DAY,
            )
        )
        recorder.answer("ListTrades", lambda _: ops.ListTradesResult(trades=[last]))
        await ToyDataPlugin(recorder, **mutations).backfilled()

    return {
        "a-daily-close": made("daily_close"),
        "the-forming-day-restated": made("forming_day"),
        "an-exact-price": made("exact"),
        "a-daily-bar": made("bar"),
        "an-fx-rate": made("fx"),
        "a-stablecoin-quote": made("stablecoin"),
        "an-asset-that-does-not-resolve": made("ambiguous"),
        "a-venue-resolved": made("venue"),
        "a-venue-not-held": made("venue_not_held"),
        "a-want-recorded-against": wanted([BTC]),
        "a-subject-another-source-resolved": wanted([ELSEWHERE]),
        "a-subject-declined": wanted(["LCL-NOT-COVERED"]),
        "a-standing-want-withdrawn": withdrawn,
        "a-trade-recorded": made("a_trade"),
        "the-makers-side-inverted": made("makers_side"),
        "a-condition-converted": made("condition_converted"),
        "a-condition-not-converted": made("condition_not_converted"),
        "a-trade-withdrawn": made("withdrawn_trade"),
        "a-quote-recorded": made("a_quote"),
        "a-one-sided-quote": made("one_sided"),
        "a-standing-want-streamed": streamed,
        "the-takers-side-stated": made("a_trade"),
        "a-restarts-gap-backfilled": restarted,
        "reads-its-datasets-licences": made("licences"),
        # An event contract's outcome (contract v23, the lake's 1c).
        "records-an-outcome": outcome("pays"),
        "restates-a-disputed-outcome": disputed,
        "records-a-partial-payout": outcome("pays_part"),
        # The calendars' reads every role holds (contract v22).
        "reads-a-calendar": PRODUCERS["reads-a-calendar"],
        "asks-for-a-settlement-date": PRODUCERS["asks-for-a-settlement-date"],
        # Contract v26: the venue's event groups, and the lake's bounded query.
        "reports-an-event-group": event_group(exhaustive=True),
        "reports-a-flag-the-venue-does-not-state": event_group(exhaustive=None),
        "queries-the-lake-within-bounds": PRODUCERS["queries-the-lake-within-bounds"],
        # Contract v27: the rates slice, a stream's liveness and the feed delay.
        **rates_producers(RATES, source="ust", now_ns=PUBLISHED),
        "records-a-datasets-liveness": liveness,
        "reports-its-feed-delay": feed_delay(recorded_with_latency),
    }


async def liveness(recorder: Recorder) -> None:
    """A stream's heartbeat with no price changed: the dataset's liveness."""
    from meridian.roles import data

    wants = data.Wants(recorder, ("live",), clock_ns=lambda: DAY)
    assert await wants.liveness("live") == 0  # the recorder keeps nothing


async def recorded_with_latency(recorder: Recorder, latency: object) -> None:
    """A price recorded unasked, its age at the edge kept on the Wants."""
    from meridian.roles import data

    wants = data.Wants(recorder, ("daily",), clock_ns=lambda: DAY, latency=latency)
    price = meridian.Price(
        meta=meridian.ObservationMeta(
            row_key="BTC-USD:1d:2026-10-08",
            subjects=[ops.SubjectRef(entity_id=BTC)],
            source=ops.Source(dataset=DAILY),
            source_times=[meridian.SourceTime(kind="published", at_ns=DAY - 5_000_000_000)],
        ),
        kind="close",
        price=meridian.Money(Decimal("62000.10"), "USD"),
    )
    await wants.record("prices", [price], "daily")


def event_group(*, exhaustive: bool | None):  # type: ignore[no-untyped-def]
    """A venue's event, its members resolved and the grouping reported as the
    venue states it: a flag it does not state is not stated, never false."""
    from meridian.roles.data.event_contracts import flag

    async def produce(recorder: Recorder) -> None:
        members = []
        for code in ("KXHIGHNY-26OCT19-B89", "KXHIGHNY-26OCT19-B91"):
            found = await recorder.resolve_identifier(
                identifiers=[ops.Identifier(scheme="symbol", value=code, source="kalshi")],
                as_of_ns=DAY,
            )
            members.append(found.instrument_id)
        await recorder.report_event_group(
            venue_id="VEN-suite-kalshi",
            venue_event_ref="KXHIGHNY-26OCT19",
            title="Highest temperature in NYC on Oct 19",
            member_instrument_ids=members,
            mutually_exclusive=flag(True),
            exhaustive=flag(exhaustive),
            valid_from_ns=DAY,
            raw_record=recorder.raw_record("kalshi:event:KXHIGHNY-26OCT19"),
        )

    return produce


def test_the_data_suite_is_carried_with_its_forty_four_cases() -> None:
    held = suite("data")
    assert held.since == "v18"
    # Contract v24 adds the two every role's suite holds, which the SDK answers;
    # v26 a third, the venue's event groups reported (two, about outcomes) and
    # the lake's bounded query; v27 the rates slice's seven (about rates), a
    # stream's liveness (about streams) and the feed delay, and the bounded
    # query about trades.
    assert len(held.cases) == 44
    assert held.case("queries-the-lake-within-bounds").about == "trades"
    assert {held.case(name).about for name in RATES_CASES} == {"rates"}
    assert held.case("records-a-datasets-liveness").about == "streams"
    assert held.case("reports-its-feed-delay").about == ""
    assert held.case("reports-an-event-group").about == "outcomes"
    assert held.case("reports-a-flag-the-venue-does-not-state").about == "outcomes"
    assert "a-want-recorded-against" in names("data")
    assert "a-subject-another-source-resolved" in names("data")
    # The 1b's eight (contract v19), each about trades or quotes.
    later = [case for case in held.cases if case.name in V19_DATA_CASES]
    assert len(later) == 8
    assert {case.about for case in later} == {"trades", "quotes"}
    assert held.case("an-fx-rate").about == "a currency's rate against another currency"
    assert held.case("an-exact-price").about == ""
    # Contract v20: a field a source may never state, and a restart's gap.
    assert held.case("the-takers-side-stated").about_field == "meridian.v1.Trade.aggressor"
    assert held.case("a-restarts-gap-backfilled").about == "trades"
    assert "reads-its-datasets-licences" in names("data")
    # Contract v22: the settlement calendars' reads.
    assert {"reads-a-calendar", "asks-for-a-settlement-date"} <= set(names("data"))
    # Contract v23: an event contract's outcome, about outcomes, and a
    # disputed one about disputed outcomes (approved 2026-10-13).
    outcomes = [case for case in held.cases if case.name in V23_DATA_CASES]
    assert len(outcomes) == 3
    assert held.case("records-an-outcome").about == "outcomes"
    assert held.case("records-a-partial-payout").about == "outcomes"
    assert held.case("restates-a-disputed-outcome").about == "disputed outcomes"


async def test_an_outcome_is_recorded_at_its_determined_or_its_final_stage() -> None:
    """records-an-outcome's expectation is any_of the determined stage and
    the final one (approved 2026-10-13): a source stating only its final word
    passes; a proposed one passes neither way."""
    case = suite("data").case("records-an-outcome")
    (expected,) = case.expect
    assert expected.row == "RecordOutcomes" and expected.fields is None
    assert len(expected.any_of) == 2
    for stage in ("determined", "final"):
        recorder = Recorder(INSTANCE)
        await outcome_producer("pays", stage)(recorder)
        assert check(case, recorder) is None, stage
    recorder = Recorder(INSTANCE)
    await outcome_producer("pays", "proposed")(recorder)
    assert "matches none of its ways" in (check(case, recorder) or "")


def test_a_source_with_no_disputes_marks_the_disputed_case_not_presented() -> None:
    why = "this venue's determinations are final when made; it has no dispute process"
    cases = producers()
    del cases["restates-a-disputed-outcome"]
    report = run(
        "data",
        cases,
        instance_id="toy-1",
        not_presented={"restates-a-disputed-outcome": why},
    )
    assert report.passed, report.failures
    assert report.not_presented["restates-a-disputed-outcome"] == why


V23_DATA_CASES = {
    "records-an-outcome",
    "restates-a-disputed-outcome",
    "records-a-partial-payout",
}


V19_DATA_CASES = {
    "a-trade-recorded",
    "the-makers-side-inverted",
    "a-condition-converted",
    "a-condition-not-converted",
    "a-trade-withdrawn",
    "a-quote-recorded",
    "a-one-sided-quote",
    "a-standing-want-streamed",
}


def test_a_data_plugin_converting_exactly_passes_every_case_of_its_suite() -> None:
    report = run("data", producers(), instance_id="toy-1")
    assert report.passed, report.failures
    assert len(report.passed_cases) == 44
    assert report.answered_by_sdk == [
        "hears-and-reads-a-replacement",
        "reads-the-template-catalogue",
        "hears-and-reads-an-event-group",
    ]


def test_a_data_plugin_sending_the_makers_side_as_the_aggressor_fails_the_suite() -> None:
    report = run("data", producers(keeps_makers_side=True))
    assert set(report.failures) == {"the-makers-side-inverted"}
    assert "matches no element of trades" in report.failures["the-makers-side-inverted"]


def test_a_case_about_a_kind_the_plugin_never_publishes_may_be_not_presented() -> None:
    # Contract v19, approved 2026-10-10: a source of daily closes states no
    # trades or quotes, and H.10 no bars; each is verified on the rest.
    every = producers()
    never = {
        name: "daily closes and bars only: this source states no trades or quotes"
        for name in V19_DATA_CASES
    }
    never["a-daily-bar"] = "this source states no bars"
    # Contract v27: the lake's bounded query is about trades, so a source
    # recording none marks it not presented rather than faking it.
    never["queries-the-lake-within-bounds"] = "it records no trades"
    mapped = {name: made for name, made in every.items() if name not in never}
    report = run("data", mapped, not_presented=never)
    assert report.passed, report.failures
    assert report.not_presented == never
    assert len(report.passed_cases) == 44 - 10


def test_a_case_about_a_field_the_source_never_states_may_be_not_presented() -> None:
    # Contract v20 (`about_field`): a source whose trades name no side.
    every = producers()
    why = "this source's trades name no side"
    mapped = {name: made for name, made in every.items() if name != "the-takers-side-stated"}
    report = run("data", mapped, not_presented={"the-takers-side-stated": why})
    assert report.passed, report.failures
    assert report.not_presented == {"the-takers-side-stated": why}


def test_a_restart_that_does_not_read_its_last_trades_fails_the_suite() -> None:
    async def from_the_stream(recorder: Recorder) -> None:
        toy = ToyDataPlugin(recorder)
        await toy.a_trade()

    mapped = dict(producers(), **{"a-restarts-gap-backfilled": from_the_stream})
    report = run("data", mapped)
    assert set(report.failures) == {"a-restarts-gap-backfilled"}
    assert "nothing was sent on ListTrades" in report.failures["a-restarts-gap-backfilled"]


def test_a_case_every_data_plugin_answers_is_never_not_presented_and_one_that_is_says_why() -> (
    None
):
    every = producers()
    mapped = {
        name: made
        for name, made in every.items()
        if name not in {"an-exact-price", "a-want-recorded-against", "a-trade-recorded"}
    }
    report = run(
        "data",
        mapped,
        not_presented={
            "an-exact-price": "this source rounds",
            "a-want-recorded-against": "this source is never asked",
            "a-trade-recorded": " ",
        },
    )
    assert "required" in report.failures["an-exact-price"]
    assert "required" in report.failures["a-want-recorded-against"]
    assert "says why" in report.failures["a-trade-recorded"]
    assert report.not_presented == {}


def test_a_data_plugin_declining_a_subject_another_source_resolved_fails_the_suite() -> None:
    # Contract v18, ruled 2026-10-10: a data plugin reads the record of an instrument
    # it did not resolve itself (W3.6) and names it to its source.
    report = run("data", producers(reads_no_record=True))
    assert set(report.failures) == {"a-subject-another-source-resolved"}


def test_a_candle_read_through_a_float_fails_the_suite() -> None:
    report = run("data", producers(through_float=True))
    assert not report.passed
    assert "decimal places" in report.failures["an-exact-price"]


def test_a_forming_day_recorded_as_a_new_row_fails_the_suite() -> None:
    report = run("data", producers(forming_as_new=True))
    assert "matches no element of prices" in report.failures["the-forming-day-restated"]


async def test_a_heard_row_is_kept_on_its_row_and_a_case_hearing_nothing_fails() -> None:
    recorder = Recorder("toy-1")
    toy = ToyDataPlugin(recorder)
    await recorder.receive(observations_wanted=toy.on_want)  # nothing delivered
    case = suite("data").case("a-want-recorded-against")
    assert check(case, recorder) == "expect[0]: nothing was heard on ObservationsWanted"
    recorder.answer("ObservationsWanted", lambda _: WANT)
    await recorder.receive(observations_wanted=toy.on_want)
    assert recorder.on("ObservationsWanted") == [WANT]
    assert check(case, recorder) is None


def test_a_reading_role_hears_and_reads_as_its_suite_asks() -> None:
    async def datasets(recorder: Recorder) -> None:
        await recorder.list_datasets()

    async def closes(recorder: Recorder) -> None:
        await recorder.list_prices(
            subjects=[SubjectRef(entity_id=BTC)],
            kinds=["close"],
            business_date=date(2026, 10, 8),
        )

    async def bars(recorder: Recorder) -> None:
        await recorder.list_bars(
            subjects=[SubjectRef(entity_id=BTC)],
            valid_from_ns=DAY,
            valid_until_ns=DAY + NS_A_DAY,
        )

    def hearing(row: str, message: object, arm: str):  # type: ignore[no-untyped-def]
        async def produce(recorder: Recorder) -> None:
            async def heard(_: object) -> None:
                return None

            recorder.answer(row, lambda _: message)
            await recorder.receive(**{arm: heard})

        return produce

    async def currency(recorder: Recorder) -> None:
        # Contract v19 (approved 2026-10-10): a reporting plugin names its
        # reporting currency by its ISO 4217 code, and core resolves it.
        found = await recorder.resolve_identifier(
            identifiers=[meridian.Identifier(scheme="iso4217", value="USD")], as_of_ns=DAY
        )
        assert found.found

    price = ops.PricesRecordedEvent(price=ops.Price(kind=ops.PRICE_KIND_CLOSE))
    bar = ops.BarsRecordedEvent(bar=ops.Bar())
    report = run(
        "reporting",
        {
            "reads-the-datasets-it-may-read": datasets,
            "reads-a-business-dates-closes": closes,
            "hears-a-price-recorded": hearing("PricesRecorded", price, "prices_recorded"),
            "reads-daily-bars-over-a-range": bars,
            "hears-a-bar-recorded": hearing("BarsRecorded", bar, "bars_recorded"),
            "resolves-its-reporting-currency": currency,
            # The order path's and the calendars' (contract v22).
            **{
                name: PRODUCERS[name]
                for name in (
                    "reads-orders-and-catches-up",
                    "hears-an-order-and-an-execution",
                    "reads-an-orders-history-for-the-person-roles",
                    "reads-a-calendar",
                    "asks-for-a-settlement-date",
                    # An event contract's outcome (contract v23).
                    "hears-and-reads-an-outcome",
                    # Bookings and alerts (contract v24).
                    "hears-and-reads-bookings",
                    "hears-and-reads-alerts",
                    # Jobs and the lake's bounded query (contract v26).
                    "runs-a-job-and-reads-its-answer",
                    "catches-up-finished-jobs",
                    "queries-the-lake-within-bounds",
                    # Rates, liveness and execution costs (contract v27).
                    "reads-a-curve-for-a-date",
                    "hears-a-rate-recorded",
                    "hears-a-datasets-liveness",
                    "reads-an-accounts-execution-costs",
                )
            },
        },
    )
    assert report.passed, report.failures
