"""Contract v23's FX additions (the OANDA batch, approved 2026-10-13): the
suite format's `any_of`, the cases' new markers, a value-date roll, the fee
kinds financing and commission, and an FX order's quote currency."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import meridian
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Case, Expectation, Recorder, check, run, suite

EUR = "INS-01J8XQ4M7K00000000CASHEUR"
USD = "INS-01J8XQ4M7K00000000CASHUSD"
AAPL = "INS-01J8XQ4M7K0000000000AAPL"
RAW = ops.RawRecordRef(instance_id="sim-venue-1", key="sim:exec-report:1")


async def _a_fill_after(recorder: Recorder, **inputs: object) -> Recorder:
    """A fill whose settlement date the plugin asked the date read for with
    `inputs`, then reported with the answer and its basis."""
    await recorder.compute_date(**inputs)  # type: ignore[arg-type]
    await recorder.report_execution(
        placement_id="PLC-1",
        venue_execution_id="SIM-EXE-1",
        quantity=Decimal("10000"),
        price=meridian.Money(Decimal("1.0925"), "USD"),
        trade_date=date(2026, 10, 13),
        computed_settlement_date=date(2026, 10, 15),
        settlement_date_basis=meridian.DateBasis(
            rule=meridian.DateRuleRef(kind="spot", subject="EUR/USD", version=1)
        ),
        raw_record=RAW,
    )
    return recorder


# ── The suite format's any_of ────────────────────────────────────────────────


async def test_a_fills_settlement_date_passes_on_any_one_markets_inputs_named_in_full() -> None:
    case = suite("connectivity").case("reports-a-fill-with-its-settlement-date")
    asked = case.expect[0]
    assert asked.row == "ComputeDate" and asked.fields is None and len(asked.any_of) == 3

    for inputs in (
        {
            "settlement": meridian.SettlementDateInputs(
                instrument_id=AAPL, trade_date="2026-10-13"
            )
        },
        {"spot": meridian.SpotDateInputs(pair=[EUR, USD], trade_date="2026-10-13")},
        {"spot": meridian.SpotDateInputs(pair=[EUR, USD], at_ns=1791898262000000000)},
    ):
        assert check(case, await _a_fill_after(Recorder("sim-venue-1"), **inputs)) is None, (
            inputs
        )

    # Fewer fields than one market's inputs need passes none of the ways.
    for inputs in (
        {"spot": meridian.SpotDateInputs(pair=[EUR, USD])},
        {"spot": meridian.SpotDateInputs(at_ns=1791898262000000000)},
        {"settlement": meridian.SettlementDateInputs(instrument_id=AAPL)},
    ):
        why = check(case, await _a_fill_after(Recorder("sim-venue-1"), **inputs)) or ""
        assert "matches none of its ways" in why, inputs
        assert "any_of[0]" in why and "any_of[2]" in why


async def test_an_expectation_of_ways_passes_when_one_message_matches_one_way_in_full() -> None:
    """A message matching parts of two ways matches neither; one matching
    one way in full passes, whatever else was sent on the row."""
    case = Case(
        name="a-made-up-case",
        given="a fill on a placement",
        expect=(
            Expectation(
                row="ReportExecution",
                any_of=(
                    {"quantity": "10", "venue_execution_id": "<set>"},
                    {"quantity": "20", "supersedes": "<set>"},
                ),
            ),
        ),
    )

    async def reported(**fields: object) -> Recorder:
        recorder = Recorder("sim-venue-1")
        await recorder.report_execution(
            placement_id="PLC-1", price=meridian.Money(Decimal("1"), "USD"), **fields
        )  # type: ignore[arg-type]
        return recorder

    assert check(case, await reported(quantity=Decimal("10"), venue_execution_id="V:1")) is None
    assert check(case, await reported(quantity=Decimal("20"), supersedes="EXE-1")) is None
    mixed = await reported(quantity=Decimal("20"), venue_execution_id="V:1")
    assert "matches none of its ways" in (check(case, mixed) or "")
    # Another message on the row that matches a way passes the expectation.
    await mixed.report_execution(
        placement_id="PLC-1",
        price=meridian.Money(Decimal("1"), "USD"),
        quantity=Decimal("10"),
        venue_execution_id="V:2",
    )
    assert check(case, mixed) is None


# ── The cases' markers ───────────────────────────────────────────────────────


def test_busts_currencies_not_stated_and_value_date_rolls_are_marked_about() -> None:
    connectivity = suite("connectivity")
    assert connectivity.case("reports-a-bust").about == "busts"
    assert connectivity.case("reports-a-value-date-roll").about == "value-date rolls"
    assert suite("custody").case("currency-not-stated").about == "currencies not stated"
    roll = connectivity.case("reports-a-value-date-roll")
    assert [each.row for each in roll.expect] == [
        "ComputeDate",
        "ReportCharge",
        "ReportValueDateRoll",
    ]

    why = "this venue's trades settle; it never rolls a spot position"
    report = run(
        "connectivity",
        {},
        not_presented={
            "reports-a-value-date-roll": why,
            "reports-a-bust": "this venue never busts or corrects a fill",
        },
    )
    assert report.not_presented["reports-a-value-date-roll"] == why
    assert "reports-a-value-date-roll" not in report.failures
    assert "reports-a-bust" not in report.failures


# ── A value-date roll, the fee kinds and the quote currency ─────────────────


async def test_a_roll_is_reported_with_its_date_reads_answer_and_never_an_account() -> None:
    from order_path_cases import PRODUCERS

    recorder = Recorder("sim-venue-1")
    await PRODUCERS["reports-a-value-date-roll"](recorder)
    assert check(suite("connectivity").case("reports-a-value-date-roll"), recorder) is None
    (rolled,) = recorder.on("ReportValueDateRoll")
    assert isinstance(rolled, ops.ReportValueDateRollParams)
    assert list(rolled.pair) == [EUR, USD]
    assert (rolled.from_value_date, rolled.to_value_date) == ("2026-10-15", "2026-10-16")
    assert rolled.value_date_basis.rule.kind == ops.DATE_RULE_KIND_SPOT
    # The account is the sidecar's to stamp from the ems's map.
    assert "account_id" not in ops.ReportValueDateRollParams.DESCRIPTOR.fields_by_name
    (charged,) = recorder.on("ReportCharge")
    assert charged.fee.kind == ops.FEE_KIND_FINANCING


async def test_a_commission_is_its_own_fee_kind_and_an_fx_order_names_its_quote_currency() -> (
    None
):
    recorder = Recorder("sim-venue-1")
    await recorder.report_execution(
        placement_id="PLC-1",
        quantity=Decimal("4"),
        price=meridian.Money(Decimal("227.41"), "USD"),
        fees=[meridian.Fee(kind="commission", amount=meridian.Money(Decimal("0.35"), "USD"))],
    )
    (reported,) = recorder.on("ReportExecution")
    assert reported.fees[0].kind == ops.FEE_KIND_COMMISSION

    await recorder.propose_order(
        account_id="ACC-1",
        instrument_id=EUR,
        side="buy",
        quantity=Decimal("10000"),
        order_type="market",
        dealt_currency=EUR,
        quote_currency=USD,
    )
    (proposed,) = recorder.on("ProposeOrder")
    assert (proposed.instrument_id, proposed.quote_currency) == (EUR, USD)
    assert ops.Order.DESCRIPTOR.fields_by_name["quote_currency"].number == 44
    assert ops.Execution.DESCRIPTOR.fields_by_name["venue_client_order_id"].number == 40
