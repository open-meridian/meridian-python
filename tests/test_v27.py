"""SDK 0.32.0, contract v27: the analytics component's v27 answer -- realized
P&L served (pnl version 2), a quoted price rounded once per unit (rulings
453 and 486), fiat legs inverted and crossed through the deployment's
pivots (462, 483), a reporting currency (459), a lot's cost missing (325)
and execution costs against the standard benchmarks (W12.1) -- and the
order path's, the rates slice's and the latency track's SDK parts."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

import meridian
from meridian import analytics
from meridian.analytics import reference
from meridian.plugin.v1 import operations_pb2 as ops

CASES = Path(__file__).parent / "reference_cases"
USD = "INS-01J8XQ4M7K00000000CASHUSD"
EUR = "INS-01J8XQ4M7K00000000CASHEUR"
CHF = "INS-01J8XQ4M7K00000000CASHCHF"


def _answer(name: str) -> dict[str, Any]:
    return dict(reference.load(CASES / f"{name}.json")["answer"])


def _value(name: str, account: str, instrument: str) -> Decimal:
    for figure in _answer(name)["figures"]:
        if figure["account_id"] == account and figure["breakdown"][0]["value"] == instrument:
            return Decimal(figure["value"])
    raise KeyError((name, account, instrument))


# ── Analytics (W12) ─────────────────────────────────────────────────────────


def test_pnl_version_2_is_served_and_its_realized_case_is_live() -> None:
    """Rulings 320 and 396: the realized cases kept as v2 tests are live --
    asked of the component, the reference answering them."""
    job = analytics.job(analytics.measure("pnl", 2, by=["sleeve"]), accounts=["ACC-1"])
    assert job.measures[0].version == 2
    assert analytics.SERVED_VERSIONS["pnl"] == 2
    assert reference.definition_of("pnl", 2) is reference.LATER_DEFINITIONS[("pnl", 2)]
    answer = _answer("pnl-v2-realized")
    missing = [n for n in answer["not_evaluated"] if n["reason"].endswith("COST_MISSING")]
    assert [(n["account_id"], n["detail"]) for n in missing] == [("ACC-2", "")]


def test_a_quoted_price_past_18_places_is_rounded_once_per_unit() -> None:
    """Rulings 453 and 486: 12.345678 EUR × 1.085012345678901234 runs to 24
    places; rounded half to even to 18 per unit, then times 1000.5, exact,
    then once to the definition's scale."""
    per_unit = reference.round_half_even(
        Fraction(Decimal("12.345678")) * Fraction(Decimal("1.085012345678901234")), 18
    )
    # Exactly 13.395213045776406028766652: rounded up at the 18th place.
    assert per_unit == Decimal("13.395213045776406029")
    expected = reference.round_half_even(Fraction(per_unit) * Fraction(Decimal("1000.5")), 2)
    assert _value("quoted-price-past-18-places", "ACC-1", "INS-01J8XQ4M7K00000000000SAP") == (
        expected
    )
    # The built-in model a pricing plugin's answer is held to rounds alike.
    value, held = reference.value_per_unit(
        "quoted_price",
        "SAP",
        [("SAP", "close", "12.345678", "EUR"), ("EUR", "close", "1.085012345678901234", "USD")],
    )
    assert (value, held) == (per_unit, "USD")
    # A value within 18 places keeps its stated form.
    assert reference.value_per_unit("quoted_price", "X", [("X", "close", "2.50", "USD")]) == (
        Decimal("2.50"),
        "USD",
    )


def test_fiat_legs_are_inverted_and_crossed_through_the_pivot() -> None:
    """Ruling 462: a euro account's dollars through EURUSD inverted (1 ÷
    1.0850 to 18 places); bitcoin's own dollar price kept, its dollar leg
    inverted; francs to dollars crossed through the euro, the first pivot
    that is neither end, its franc leg inverted."""
    answer = _answer("inverted-and-crossed")
    assert answer["not_evaluated"] == []
    legs = {(leg["from_instrument_id"], leg["to_instrument_id"]): leg for leg in
            answer["provenance"]["conversion_legs"]}  # fmt: skip
    inverted = legs[(USD, EUR)]
    assert inverted["derivation"] == "CONVERSION_DERIVATION_INVERTED"
    assert Decimal(inverted["rate"]) == reference.round_half_even(1 / Fraction("1.0850"), 18)
    crossed = legs[(CHF, USD)]
    assert (crossed["derivation"], crossed["via_instrument_id"], crossed["dataset"]) == (
        "CONVERSION_DERIVATION_CROSSED",
        EUR,
        "",
    )
    sub = reference.round_half_even(1 / Fraction("0.9412"), 18)
    assert legs[(CHF, EUR)]["derivation"] == "CONVERSION_DERIVATION_INVERTED"
    assert Decimal(crossed["rate"]) == reference.round_half_even(
        Fraction(sub) * Fraction("1.0850"), 18
    )
    assert _value("inverted-and-crossed", "ACC-US", CHF) == reference.round_half_even(
        Fraction(Decimal(crossed["rate"])) * 1000, 2
    )
    # Each position's own price is named (ruling 460).
    prices = {p["instrument_id"]: p for p in answer["provenance"]["input_prices"]}
    assert prices["INS-01J8XQ4M7K0000000000NESN"]["row_key"].endswith("/close")


def test_a_token_leg_is_never_inverted() -> None:
    inputs = reference.load(CASES / "inverted-and-crossed.json")["inputs"]
    given = dict(inputs)
    # Bitcoin priced in the euro account's base only the other way round.
    given["market"] = [
        {**row, "subject_id": EUR, "instrument_id": "INS-01J8XQ4M7K00000000000BTC",
         "amount": "0.0000180"} if row["subject_id"] == "INS-01J8XQ4M7K00000000000BTC" else row
        for row in inputs["market"]
    ]  # fmt: skip
    answer = reference.compute(given).to_json()
    assert any(
        n["instrument_id"].endswith("BTC") and n["reason"].endswith("PRICE_MISSING")
        for n in answer["not_evaluated"]
    )


def test_a_reporting_currency_converts_money_and_leaves_weights() -> None:
    answer = _answer("reporting-currency")
    money = [f for f in answer["figures"] if f["measure"]["definition"] != "concentration"]
    assert {f["currency_instrument_id"] for f in money} == {EUR}
    weights = [f for f in answer["figures"] if f["measure"]["definition"] == "concentration"]
    assert {f["denominator"] for f in weights} == {"7275.00"}  # dollars, unconverted


def test_execution_costs_are_measured_against_each_benchmark() -> None:
    """The gaps spec's C3, C4 and C8: s × (price − mid) ÷ mid × 10⁴, half to
    even at 4 places; a stale quote unanswered, never imputed; no moment,
    not measured; the rows the lake keeps beside each account's means."""
    answer = _answer("execution-cost")
    rows = answer["execution_costs"]
    first = [r for r in rows if r["execution_id"].endswith("001")]
    by = {r["benchmark"]: r for r in first}
    assert by["TCA_BENCHMARK_DECISION"]["unanswered"] == "TCA_UNANSWERED_NO_QUOTE"
    assert by["TCA_BENCHMARK_DECISION"]["cost_bps"] is None
    assert by["TCA_BENCHMARK_ARRIVAL"]["cost_bps"] == str(
        reference.round_half_even(
            (Fraction("227.55") - Fraction("227.20")) / Fraction("227.20") * 10_000, 4
        )
    )
    assert by["TCA_BENCHMARK_ARRIVAL"]["fees_bps"] == "0.5493"
    sold = [r for r in rows if r["execution_id"].endswith("003")]
    assert [r["unanswered"] for r in sold][:3] == ["TCA_UNANSWERED_NOT_MEASURED"] * 3
    assert Decimal(sold[3]["cost_bps"]) > 0, "a sale below the mid is a cost"
    assert {f["breakdown"][0]["value"] for f in answer["figures"]} == {
        "TCA_BENCHMARK_ARRIVAL",
        "TCA_BENCHMARK_PLACEMENT_ARRIVAL",
        "TCA_BENCHMARK_MID_AT_FILL",
    }
    assert "execution_costs" not in _answer("valuation")


def test_a_job_is_over_one_account_or_more_as_the_component_refuses() -> None:
    for wrong, why in (
        (
            lambda: analytics.job(analytics.measure("implied_distribution", event_group="EVG-1")),
            "one account or more",
        ),
        (lambda: analytics.job(analytics.measure("market_value"), accounts=[""]), "empty"),
        (
            lambda: analytics.job(
                analytics.measure("market_value"),
                accounts=["ACC-1"],
                business_date="2026-10-20",
                lake_as_of_ns=1,
            ),
            "business date",
        ),
    ):
        with pytest.raises(ValueError, match=why):
            wrong()
    job = analytics.job(
        analytics.measure("execution_cost"),
        accounts=["ACC-1"],
        business_date="2026-10-20",
        reporting_currency=EUR,
    )
    sent = ops.RunJobParams(job=meridian.operations._job(job, "job"))
    assert (sent.job.business_date, sent.job.reporting_currency) == ("2026-10-20", EUR)
