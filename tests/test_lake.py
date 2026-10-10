"""The lake's 1a through the SDK (contract v18): a dgm's catalogue, prices and
bars recorded in batches, wants heard, recorded against and declined, the
readers' reads by business date, as of and side by side, the rows heard
latest value first with their dataset, venues resolved, a Money naming its
instrument, dates typed, and the dgm suite a data plugin holds itself to.

Against the fake sidecar (conftest), which mirrors the lake, money
resolution and venue resolution as core's sidecar and lake answer them.
"""

from __future__ import annotations

import asyncio
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
)
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder, check, names, run, suite

INSTANCE = "dgm-coinbase-1"
DAILY = f"{INSTANCE}:daily"
LIVE = f"{INSTANCE}:live"
BTC = "LCL-01JA00000000000000BTC1"
ETH = "LCL-01JA00000000000000ETH1"
USDC = "LCL-01JA0000000000000USDC1"
COINBASE = "VEN-01JA0000000000000CBEXC"
DAY = 1_791_331_200_000_000_000  # 2026-10-08 00:00 UTC
NS_A_DAY = 86_400_000_000_000

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
    """A daily close as a crypto dgm records one: its candle's day."""
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


async def dgm(sidecar: tuple[FakeSidecar, str]) -> meridian.Plugin:
    service, address = sidecar
    service.instance_id = INSTANCE
    service.roles = ("dgm",)
    return await meridian.connect(
        address, heartbeat=False, declaration=Declaration(catalogue=CATALOGUE)
    )


# ── The catalogue ───────────────────────────────────────────────────────────


async def test_a_dgm_declares_its_catalogue_from_code(sidecar) -> None:
    service, _ = sidecar
    plugin = await dgm(sidecar)
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


def test_a_catalogue_holds_each_key_once_and_only_a_dgm_declares_one() -> None:
    with pytest.raises(ValueError, match="declared twice"):
        Declaration(catalogue=[CATALOGUE[0], CATALOGUE[0]])
    with pytest.raises(ValueError, match="no entry of the data dictionary"):
        DatasetLicence(default_fields=["meridian.v1.Bar.nothing"])
    declared = Declaration(catalogue=CATALOGUE)
    assert declared.refused_for(["dgm"]) is None
    assert "only a dgm" in (declared.refused_for(["custody"]) or "")


async def test_a_catalogue_from_a_plugin_not_holding_dgm_is_refused_by_the_sidecar(
    sidecar,
) -> None:
    _, address = sidecar
    with pytest.raises(meridian.Refused, match="dgm"):
        await meridian.connect(
            address, heartbeat=False, declaration=Declaration(catalogue=CATALOGUE)
        )


# ── Recording ───────────────────────────────────────────────────────────────


async def test_a_batch_is_refused_outside_1_to_500_before_anything_is_sent(sidecar) -> None:
    service, _ = sidecar
    plugin = await dgm(sidecar)
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
    plugin = await dgm(sidecar)
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
    plugin = await dgm(sidecar)
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
    plugin = await dgm(sidecar)
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
    plugin = await dgm(sidecar)
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
    plugin = await dgm(sidecar)

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
    plugin = await dgm(sidecar)
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
    plugin = await dgm(sidecar)
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
    plugin = await dgm(sidecar)
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
    plugin = await dgm(sidecar)
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
    plugin = await dgm(sidecar)
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


# ── Hearing ─────────────────────────────────────────────────────────────────


WANT = ops.ObservationsWantedEvent(
    want_id="WNT-1",
    dataset=DAILY,
    data_type="meridian.v1.Price",
    subjects=[ops.SubjectRef(entity_id=BTC), ops.SubjectRef(entity_id="LCL-NOT-COVERED")],
    kinds=[ops.PRICE_KIND_CLOSE],
    business_date="2026-10-08",
)


async def test_a_dgm_hears_a_want_records_against_it_and_declines_what_it_cannot_cover(
    sidecar,
) -> None:
    service, _ = sidecar
    service.operations.streams = [Stream(deliveries=[ops.Delivery(observations_wanted=WANT)])]
    plugin = await dgm(sidecar)
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
    writer = await dgm(sidecar)
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


# ── The dgm suite ───────────────────────────────────────────────────────────


class ToyDgm:
    """A dgm as a data plugin writes one: its own conversion from its
    source's synthetic exchange, against whatever operations it is given."""

    def __init__(
        self, plugin: object, *, through_float: bool = False, forming_as_new: bool = False
    ) -> None:
        self.plugin = plugin
        self.through_float = through_float
        self.forming_as_new = forming_as_new

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

    async def on_want(self, heard: meridian.Heard[ops.ObservationsWantedEvent]) -> None:
        want = heard.message
        covered = [s for s in want.subjects if s.entity_id != "LCL-NOT-COVERED"]
        if covered:
            await self.plugin.record_prices(  # type: ignore[attr-defined]
                prices=[self.price(s.entity_id, Decimal("62431.27")) for s in covered],
                want_id=want.want_id,
            )
        declined = [s for s in want.subjects if s.entity_id == "LCL-NOT-COVERED"]
        if declined:
            await self.plugin.decline_want(
                want_id=want.want_id, subjects=declined, reason="not_covered"
            )  # type: ignore[attr-defined]

    async def on_withdrawn(self, heard: meridian.Heard[ops.WantWithdrawnEvent]) -> None:
        return None  # the standing want stops being kept current


def producers(**mutations: bool) -> dict[str, object]:
    def made(step: str):  # type: ignore[no-untyped-def]
        async def produce(recorder: Recorder) -> None:
            await getattr(ToyDgm(recorder, **mutations), step)()

        return produce

    def wanted(subjects: list[str]):  # type: ignore[no-untyped-def]
        async def produce(recorder: Recorder) -> None:
            toy = ToyDgm(recorder, **mutations)
            want = ops.ObservationsWantedEvent()
            want.CopyFrom(WANT)
            del want.subjects[:]
            want.subjects.extend(ops.SubjectRef(entity_id=s) for s in subjects)
            recorder.answer("ObservationsWanted", lambda _: want)
            await recorder.receive(observations_wanted=toy.on_want)

        return produce

    async def withdrawn(recorder: Recorder) -> None:
        toy = ToyDgm(recorder, **mutations)
        recorder.answer(
            "WantWithdrawn", lambda _: [ops.WantWithdrawnEvent(want_id="WNT-1", dataset=DAILY)]
        )
        await recorder.receive(want_withdrawn=toy.on_withdrawn)

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
        "a-subject-declined": wanted(["LCL-NOT-COVERED"]),
        "a-standing-want-withdrawn": withdrawn,
    }


def test_the_dgm_suite_is_carried_with_its_twelve_cases() -> None:
    held = suite("dgm")
    assert held.since == "v18"
    assert len(held.cases) == 12
    assert "a-want-recorded-against" in names("dgm")


def test_a_dgm_converting_exactly_passes_every_case_of_its_suite() -> None:
    report = run("dgm", producers(), instance_id="toy-1")
    assert report.passed, report.failures
    assert len(report.passed_cases) == 12


def test_a_candle_read_through_a_float_fails_the_suite() -> None:
    report = run("dgm", producers(through_float=True))
    assert not report.passed
    assert "decimal places" in report.failures["an-exact-price"]


def test_a_forming_day_recorded_as_a_new_row_fails_the_suite() -> None:
    report = run("dgm", producers(forming_as_new=True))
    assert "matches no element of prices" in report.failures["the-forming-day-restated"]


async def test_a_heard_row_is_kept_on_its_row_and_a_case_hearing_nothing_fails() -> None:
    recorder = Recorder("toy-1")
    toy = ToyDgm(recorder)
    await recorder.receive(observations_wanted=toy.on_want)  # nothing delivered
    case = suite("dgm").case("a-want-recorded-against")
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
        },
    )
    assert report.passed, report.failures
