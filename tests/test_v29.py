"""SDK 0.34.0's helpers for contract v29, past what the suites ask: the
contract's money rules on a debt record, a coupon's accrual by its day
count, an agency's factor recorded and read, a yield as quoted, a capped
size and the trade characteristics, the seven fixed-income records reported
and servicing's expectations, the book's provisional factor and its open
claims read, and Track E's items (an assessment's data type, a derived value
in money, every account's lifecycle events, the measures served, the
not-evaluated reason NOT_SUPPORTED, DatasetRef's quality counts and the
quarantined unanswered reason)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

import meridian
from meridian import analytics
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import debt, lifecycle, signal
from meridian.roles.data import Wants
from meridian.roles.data.quality import assessment
from meridian.suites import Recorder

POOL = "INS-01JC29POOL0000000000000001"
BOND = "INS-01JC29BOND0000000000000001"
ACCOUNT = "ACC-1"


def usd(amount: str) -> meridian.Money:
    return meridian.Money(Decimal(amount), "USD")


def wire_factor(month: str, value: str, version: int = 1, paid: str = "") -> ops.Factor:
    return ops.Factor(
        meta=ops.ObservationMeta(row_key=f"{POOL}:factor:{month}", version=version),
        factor=meridian.operations._decimal(Decimal(value), "factor"),
        factor_month=month,
        payment_date=paid,
    )


# ── Money ────────────────────────────────────────────────────────────────


def test_percent_of_par_is_face_times_price_times_a_hundredth_exactly() -> None:
    assert debt.percent_of_par(1_000_000, "101.15625") == Decimal("1011562.50000")
    assert debt.current_face(1_000_000, "0.84") == Decimal("840000.00")


def test_a_pools_cash_and_paydown_round_to_the_cent_half_even() -> None:
    # 993: original face times its factor times the price over 100.
    assert debt.fill_cash(1_000_000, "100.5", "0.123456785") == Decimal("124074.07")
    assert debt.to_cent("0.125") == Decimal("0.12") and debt.to_cent("0.135") == Decimal("0.14")
    # The platform package's month: 1,000,000 at 0.85 to 0.84.
    assert debt.paydown_cash(1_000_000, "0.85", "0.84") == Decimal("10000.00")
    assert debt.to_cent(Fraction(1, 8)) == Decimal("0.12")


def test_a_lots_relief_is_exact_within_its_places_and_half_even_past_them() -> None:
    assert debt.relief(Decimal("85000.00"), "0.85", "0.84") == Decimal("1000.00")
    # 1000.00 x 0.01/0.03 = 333.333...: half-even at the cost's places.
    assert debt.relief(Decimal("1000.00"), "0.03", "0.02") == Decimal("333.33")
    with pytest.raises(ValueError, match="above zero"):
        debt.relief(Decimal(1), 0, 0)


def test_a_coupon_splits_into_the_purchased_accrued_returned_and_income() -> None:
    split = debt.coupon_split(usd("23125.00"), usd("8169.16"))
    assert split.returned == usd("8169.16") and split.income == usd("14955.84")
    # At most the coupon (988).
    assert debt.coupon_split(usd("100"), usd("150")).income.amount == 0
    with pytest.raises(ValueError, match="one currency"):
        debt.coupon_split(usd("1"), meridian.Money(Decimal(1), "EUR"))


# ── Accrual ──────────────────────────────────────────────────────────────


def test_thirty_360_follows_msrb_g33() -> None:
    # The platform package's G-33 cases: 72 and 60 days.
    assert debt.accrued_per100("5", "THIRTY_360_BOND_BASIS", "2026-05-15", "2026-07-27") == 1
    assert debt.accrued_per100(
        "4.5", "DAY_COUNT_THIRTY_360_BOND_BASIS", "2026-01-31", "2026-03-31"
    ) == Fraction(3, 4)
    assert debt.year_fraction("THIRTY_E_360", "2026-01-31", "2026-03-31") == Fraction(60, 360)


def test_actual_actual_icma_reads_the_coupon_period() -> None:
    # QuantLib's accruedAmount for Treasury's 10-year note settled 2026-10-19.
    start, pay, period = debt.coupon_period(
        "2026-10-19", "2036-08-15", 2, dated="2026-08-15", first_coupon="2027-02-15"
    )
    assert (start, pay) == (date(2026, 8, 15), date(2027, 2, 15))
    accrued = debt.accrued_per100(
        "4.625", ops.DAY_COUNT_ACT_ACT_ICMA, start, "2026-10-19", period=period
    )
    assert round(Decimal(accrued.numerator) / accrued.denominator, 12) == Decimal(
        "0.816915760870"
    )
    with pytest.raises(ValueError, match="coupon period"):
        debt.year_fraction("ACT_ACT_ICMA", "2026-08-15", "2026-10-19")


def test_a_cd_accrues_on_actual_365_fixed() -> None:
    accrued = debt.accrued_per100("4.5", "ACT_365_FIXED", "2026-01-15", "2026-07-15")
    assert accrued == Fraction(Decimal("4.5")) * Fraction(181, 365)


def test_a_day_count_the_engine_does_not_compute_is_refused_by_name() -> None:
    for kind in ("BUS_252", "ACT_ACT_AFB", "ACT_ACT_ICMA_ULTIMO"):
        with pytest.raises(ValueError, match="not supported"):
            debt.year_fraction(kind, "2026-01-01", "2026-07-01")


def test_a_schedule_runs_back_from_maturity_on_month_ends() -> None:
    dates = debt.coupon_dates("2036-08-15", 2, dated="2026-08-15", first_coupon="2027-02-15")
    assert dates[0] == date(2027, 2, 15) and dates[-1] == date(2036, 8, 15) and len(dates) == 20
    eom = debt.coupon_dates("2028-08-31", 2, dated="2026-08-31")
    assert eom[:2] == [date(2027, 2, 28), date(2027, 8, 31)]


# ── The data role ────────────────────────────────────────────────────────


def test_a_factor_is_keyed_by_its_month_under_the_pools_record() -> None:
    row = debt.factor(
        POOL, "0.84123456", "2026-10", dataset="gse-1:factors", published="2026-11-04",
        payment_date="2026-11-25", wac="6.512", wam=331, wala=0,
    )  # fmt: skip
    assert row.meta is not None and row.meta.row_key == f"{POOL}:factor:202610"
    wire = meridian.operations._factor(row, "factor")
    assert wire.factor_month == "202610" and wire.wam == 331 and wire.HasField("wala")
    assert not wire.HasField("coupon_rate")
    with pytest.raises(ValueError, match="pool's or a class's record"):
        debt.factor("CUSIP-1", "1", "202610", dataset="gse-1:factors")
    with pytest.raises(ValueError, match="YYYYMM"):
        debt.factor_month("2026-13")


async def test_wants_record_an_agencys_factors_in_the_lakes_batches() -> None:
    recorder = Recorder("gse-1")
    wants = Wants(recorder, ("factors",))
    rows = [debt.factor(POOL, "0.84", "202610", dataset="gse-1:factors")]
    assert await wants.record("factors", rows, "factors") == 1
    (sent,) = recorder.on("RecordFactors")
    assert sent.factors[0].factor_month == "202610"


def test_a_fill_takes_the_factor_of_the_month_before_it_settles() -> None:
    assert debt.settlement_month("2026-11-13") == "202610"
    assert debt.settlement_month(date(2027, 1, 14)) == "202612"


def test_the_factor_in_force_is_the_latest_version_of_the_latest_month() -> None:
    rows = [
        wire_factor("202609", "0.86"),
        wire_factor("202610", "0.85"),
        wire_factor("202610", "0.849", version=2),
        wire_factor("202611", "0.84"),
    ]
    held = debt.latest(rows)
    assert held is not None and held.factor_month == "202611"
    held = debt.latest(rows, month="202610")
    assert held is not None and held.meta.version == 2
    assert debt.latest([], month="202610") is None


async def test_a_factor_read_reads_every_page() -> None:
    recorder = Recorder("servicing-1")
    pages = {
        "": ops.ListFactorsResult(factors=[wire_factor("202609", "0.86")], next_cursor="p2"),
        "p2": ops.ListFactorsResult(factors=[wire_factor("202610", "0.85")]),
    }
    recorder.answer("ListFactors", lambda p: pages[p.cursor])
    rows = await debt.read_factors(recorder, [POOL], "2026-09-01", "2026-10-31")
    assert [r.factor_month for r in rows] == ["202609", "202610"]
    with pytest.raises(ValueError, match="names the pools"):
        await debt.read_factors(recorder, [])


def test_a_yield_is_quoted_in_percent_semi_annual_bond_equivalent() -> None:
    quoted = debt.quoted_yield("4.312", "to_worst", day_count="THIRTY_360_BOND_BASIS")
    wire = meridian.operations._quoted_yield(quoted, "yield")
    assert wire.kind == ops.YIELD_KIND_TO_WORST
    assert wire.convention.compounding == ops.COMPOUNDING_COMPOUNDED
    assert wire.convention.periods_per_year == 2
    assert wire.value.unit == ops.VALUE_UNIT_PERCENT
    with pytest.raises(ValueError, match="names the date"):
        debt.quoted_yield("4.4", "to_call")
    price = meridian.Price(
        meta=meridian.ObservationMeta(row_key="r"), price=usd("99.5"),
        basis="percent_of_par", yield_=quoted,
    )  # fmt: skip
    wire_price = meridian.operations._price(price, "p")
    assert getattr(wire_price, "yield").kind == ops.YIELD_KIND_TO_WORST
    assert wire_price.basis == ops.PRICE_BASIS_PERCENT_OF_PAR


def test_a_capped_size_is_at_least_its_floor() -> None:
    assert debt.capped("5MM+") == (Decimal(5_000_000), True)
    assert debt.capped("1MM+") == (Decimal(1_000_000), True)
    assert debt.capped("250M") == (Decimal(250_000), False)
    assert debt.capped("1,000") == (Decimal(1000), False)
    with pytest.raises(ValueError, match="not a size"):
        debt.capped("lots")


def test_characteristics_are_named_by_meaning() -> None:
    found = debt.characteristics(
        contra_party="customer", capacity="principal", traded_flat=True
    )
    assert found == [
        "TRADE_CHARACTERISTIC_CONTRA_CUSTOMER",
        "TRADE_CHARACTERISTIC_PRINCIPAL_CAPACITY",
        "TRADE_CHARACTERISTIC_TRADED_FLAT",
    ]
    attributes = meridian.TradeAttributes(characteristics=found)
    assert attributes.characteristics == found
    with pytest.raises(ValueError, match="contra party"):
        debt.characteristics(contra_party="C")


# ── The book's own words ─────────────────────────────────────────────────


def test_the_factor_taken_and_a_provisional_month_are_read_from_the_book() -> None:
    d = meridian.operations._decimal
    taken = ops.Execution(factor_taken=d(Decimal("0.84"), "f"), factor_month_awaited="202610")
    assert debt.taken(taken) == Decimal("0.84") and debt.awaited(taken) == "202610"
    stated = ops.Execution(factor_used=d(Decimal("0.85"), "f"))
    assert debt.taken(stated) == Decimal("0.85") and debt.awaited(stated) == ""
    assert debt.taken(ops.Execution()) is None
    assert debt.awaited(ops.Lot(factor_month_awaited="202611")) == "202611"


async def test_an_open_claim_is_marked_settled_by_a_person_with_a_note() -> None:
    claim = ops.LifecycleEvent(
        event_id="LCE-1", kind=ops.LIFECYCLE_EVENT_KIND_FACTOR_REVISION,
        state=ops.LIFECYCLE_EVENT_STATE_CLAIM_OPEN,
    )  # fmt: skip
    booked = ops.LifecycleEvent(
        event_id="LCE-2", kind=ops.LIFECYCLE_EVENT_KIND_FACTOR_REVISION,
        state=ops.LIFECYCLE_EVENT_STATE_BOOKED,
    )  # fmt: skip
    assert debt.open_claims([claim, booked]) == [claim]
    recorder = Recorder("operations-1")
    await lifecycle.settle_claim(
        recorder, claim, "Received from the counterparty on 2026-11-30"
    )
    (sent,) = recorder.on("ReleaseLifecycleEvent")
    assert sent.event_id == "LCE-1"
    with pytest.raises(ValueError, match="no open factor revision claim"):
        await lifecycle.settle_claim(recorder, booked, "paid")


# ── The seven records and servicing's expectations ──────────────────────


async def test_a_custodians_coupon_and_redemption_are_reported_once() -> None:
    recorder = Recorder("custody-1")
    coupon = lifecycle.coupon_received(
        ACCOUNT, BOND, 1_000_000, "2027-02-15", usd("23125.00"), period_start="2026-08-15",
        period_end="2027-02-15", record_date="2027-02-14", external_event_id="CPN-1",
    )  # fmt: skip
    await lifecycle.report(recorder, coupon)
    called = lifecycle.redemption(
        ACCOUNT, BOND, 250_000, "2027-03-20", "partial_call", 100, external_event_id="RED-1"
    )
    await lifecycle.report(recorder, called)
    first, second = recorder.on("RecordLifecycleEvent")
    assert first.event.kind == ops.LIFECYCLE_EVENT_KIND_COUPON_RECEIVED
    assert first.event.period_end_date == "2027-02-15"
    assert second.event.redemption_kind == ops.REDEMPTION_EVENT_KIND_PARTIAL_CALL
    assert first.idempotency_key == "custody-1:CPN-1"
    with pytest.raises(ValueError, match="cash received"):
        lifecycle.coupon_received(
            ACCOUNT, BOND, 1, "2027-02-15", usd("0"), period_start="a", period_end="b"
        )


def test_a_paydown_falls_and_an_accretion_carries_its_face_change() -> None:
    down = lifecycle.paydown(ACCOUNT, POOL, 1_000_000, "2026-11-25", "0.85", "0.84",
                             usd("10000.00"), external_event_id="PD-1")  # fmt: skip
    assert down.kind == "paydown" and down.cash == usd("10000.00")
    with pytest.raises(ValueError, match="accretion"):
        lifecycle.paydown(ACCOUNT, POOL, 1, "2026-11-25", "0.84", "0.85", usd("1"))
    up = lifecycle.accretion(ACCOUNT, POOL, 2_000_000, "2026-11-25", "1.02", "1.0251")
    assert up.face_change == Decimal("10200.0000") and up.cash is None


def test_a_tba_allocation_names_each_pool_delivered() -> None:
    event = lifecycle.tba_allocation(
        ACCOUNT, "INS-TBA", 1_000_000, "2026-11-12",
        [(POOL, Decimal("600000"), usd("101.15625")), ("INS-POOL2", 400000, None)],
        external_event_id="ALLOC-1",
    )  # fmt: skip
    assert event.kind == "tba_allocation" and len(event.deliveries) == 2
    with pytest.raises(ValueError, match="names what it delivered"):
        lifecycle.strip(ACCOUNT, BOND, 1, "2026-11-12", [])
    with pytest.raises(ValueError, match="at most 512"):
        lifecycle.reconstitution(ACCOUNT, BOND, 1, "2026-11-12", [(POOL, 1, None)] * 513)


def test_servicing_expects_a_coupon_from_the_terms_and_the_face_held() -> None:
    icma = lifecycle.expected_coupon(
        ACCOUNT, BOND, 1_000_000, coupon_rate="4.625", day_count="ACT_ACT_ICMA",
        period_start="2026-08-15", period_end="2027-02-15", payment_date="2027-02-15",
        currency="USD",
    )  # fmt: skip
    assert icma.cash == usd("23125.00")
    thirty = lifecycle.expected_coupon(
        ACCOUNT, BOND, 333_333, coupon_rate="4.65", day_count="THIRTY_360_BOND_BASIS",
        period_start="2026-08-23", period_end="2027-02-23", payment_date="2027-02-23",
        currency="USD",
    )  # fmt: skip
    # 333,333 x 4.65% x 180/360 = 7749.99225: the cent, half-even.
    assert thirty.cash == usd("7749.99")
    maturity = lifecycle.expected_maturity(
        ACCOUNT, BOND, 1_000_000, "2036-08-15", currency="USD"
    )
    assert maturity.redemption_kind == "maturity" and maturity.cash == usd("1000000.00")


def test_servicing_expects_a_paydown_or_an_accretion_from_the_published_factors() -> None:
    prior = wire_factor("202609", "0.85", paid="2026-10-27")
    current = wire_factor("202610", "0.84", paid="2026-11-25")
    paid = lifecycle.expected_paydown(ACCOUNT, POOL, 1_000_000, prior, current, currency="USD")
    assert paid is not None and paid.kind == "paydown" and paid.cash == usd("10000.00")
    assert paid.event_date == "2026-11-25" and paid.prior_factor == Decimal("0.85")
    io = lifecycle.expected_paydown(
        ACCOUNT, POOL, 1_000_000, prior, current, currency="USD", interest_only=True
    )
    assert io is not None and io.kind == "accretion" and io.cash is None
    same = wire_factor("202610", "0.85", paid="2026-11-25")
    assert lifecycle.expected_paydown(ACCOUNT, POOL, 1, prior, same, currency="USD") is None
    with pytest.raises(ValueError, match="not after"):
        lifecycle.expected_paydown(ACCOUNT, POOL, 1, current, prior, currency="USD")


async def test_lifecycle_events_of_every_account_in_scope_are_read_by_naming_none() -> None:
    recorder = Recorder("reporting-1")
    await lifecycle.read_events(recorder, "", "2026-11-01", "2026-11-30")
    (sent,) = recorder.on("ListLifecycleEvents")
    assert sent.account_id == ""


# ── Track E ──────────────────────────────────────────────────────────────


def test_an_assessment_names_the_kind_of_row_it_assesses() -> None:
    close = ops.Price(meta=ops.ObservationMeta(source=ops.Source(dataset="d"), row_key="k"))
    bar = ops.Bar(meta=ops.ObservationMeta(source=ops.Source(dataset="d"), row_key="k"))
    assert assessment(close, "suspicious", ["price_outlier"]).data_type == "meridian.v1.Price"
    assert assessment(bar, "suspicious", ["price_outlier"]).data_type == "meridian.v1.Bar"


def test_a_derived_value_in_money_carries_its_cash_instrument() -> None:
    value = signal.derived(
        "INS-AAPL", "expected_move", usd("7.42"), "2026-10-23", dataset="sig-1:derived",
        definition="expected_move", version=1, inputs=[("tradier-1:options", 1)],
    )  # fmt: skip
    assert value.value is None and value.money_value == usd("7.42")
    wire = meridian.operations._derived_series(value, "values[0]")
    assert wire.HasField("money_value") and not wire.HasField("value")
    with pytest.raises(ValueError, match="names its unit"):
        signal.derived(
            "INS-AAPL", "iv30", Decimal("27"), "2026-10-23", dataset="d", definition="x",
            version=1, inputs=[("d", 1)],
        )  # fmt: skip


def test_the_curve_and_bond_measures_are_served_at_version_1() -> None:
    assert len(analytics.DEBT_MEASURES) == 10
    assert "expected_move" in analytics.STANDARD_MEASURES
    ref = analytics.measure("bond_yield", by=["instrument", "yield_kind", "to_date"])
    assert ref.definition == "bond_yield"
    with pytest.raises(ValueError, match="not served"):
        analytics.measure("bond_risk", 2)


def test_a_term_the_engine_does_not_compute_is_not_evaluated_by_name() -> None:
    answer = ops.ReadJobAnswerResult(
        not_evaluated=[
            ops.NotEvaluated(
                instrument_id=BOND,
                reason=ops.NOT_EVALUATED_REASON_NOT_SUPPORTED,
                detail="day_count DAY_COUNT_BUS_252",
            )  # fmt: skip
        ]
    )
    (unevaluated,) = analytics.answer_json(answer)["not_evaluated"]
    assert unevaluated["reason"] == "NOT_EVALUATED_REASON_NOT_SUPPORTED"


def test_a_listing_counts_each_datasets_rows_by_state_and_a_quarantined_read_says_so() -> None:
    listed = ops.DatasetRef(dataset="d", valid_count=3, suspicious_count=1, invalid_count=2)
    assert (listed.valid_count, listed.suspicious_count, listed.invalid_count) == (3, 1, 2)
    assert ops.UNANSWERED_REASON_QUARANTINED != ops.UNANSWERED_REASON_SOURCE_SILENT
