"""The reference computations for contract v29's curve and bond measures
(requirement 36; `meridian.analytics.debt`), held to core's oracle cases
(`crates/analytics-engine/oracle_cases/` at CORE_REV, read-only, handed to
the test image as the `core-oracle` context): the platform's packages'
cases exactly, QuantLib 1.40's bond functions and fitted curve, and the
Board's zero curve, each at the tolerance core's oracle holds the engine
to."""

from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from meridian.analytics import debt as reference

ORACLE = Path(os.environ.get("MERIDIAN_CORE_ORACLE", "/core-oracle"))
T = reference.TOLERANCES


def oracle(name: str) -> Any:
    path = ORACLE / name
    if not path.exists():
        raise AssertionError(
            f"core's oracle case {path} is not here: the test image takes it from "
            "meridian-core at CORE_REV (the core-oracle build context)"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_platform_package_case_is_answered_exactly() -> None:
    packages = oracle("platform-v29-packages.json")
    count = 0
    for template in packages:
        for case in template["calculation_package"]["test_cases"]:
            inputs = json.loads(case["inputs"])
            expected = json.loads(case["expected"])
            answered = reference.package_answer(inputs)
            for name, value in expected.items():
                assert Decimal(answered[name]) == Decimal(value), (case["name"], name, answered)
            count += 1
    # Nine auctions, a bill, two G-33 accruals, a pool's and a class's month,
    # a TBA's market value and a CD's accrual: sixteen, as core counts them.
    assert count == 16


def _curves() -> dict[str, Any]:
    return {case["date"]: case for case in oracle("treasury-curve.json")["cases"]}


def _fitted(case: Any) -> reference.Curve:
    return reference.Curve.fit(
        case["date"], [(p["tenor"], p["par_yield"]) for p in case["par"]]
    )


@pytest.mark.parametrize("on", ["2026-10-01", "2026-10-16"])
def test_the_curve_reprices_its_par_yields_and_stays_near_quantlibs_and_the_boards(
    on: str,
) -> None:
    case = _curves()[on]
    curve = _fitted(case)
    day = date.fromisoformat(on)
    for p in case["par"]:
        back = curve.par(reference.maturity_of(day, p["tenor"]))
        assert abs(back - float(p["par_yield"])) < T["par_round_trip_percent"], p
    worst = 0.0
    for tenor, zero in case["quantlib_convex_monotone_forward_zero"].items():
        ours = curve.zero(reference.maturity_of(day, tenor)) * 100
        worst = max(worst, abs(ours - float(zero)) * 100)
    assert worst < T["curve_vs_quantlib_bp"], f"{worst}bp from QuantLib's fit"
    worst = 0.0
    for tenor, zero in case["fed_zero"].items():
        ours = curve.zero(reference.maturity_of(day, tenor)) * 100
        worst = max(worst, abs(ours - float(zero)) * 100)
    assert worst < T["curve_vs_board_bp"], f"{worst}bp from the Board's"


def _bond(b: Any) -> reference.Bond:
    return reference.Bond(
        coupon=Decimal(b["coupon"]),
        day_count=b["dc"],
        dated=date.fromisoformat(b["dated"]),
        maturity=date.fromisoformat(b["maturity"]),
        first_coupon=date.fromisoformat(b["first"]) if b["first"] else None,
        treasury=b["security_type"] == "DEBT_SECURITY_TYPE_TNOTE",
        municipal=b["issuer_type"] == "ISSUER_TYPE_MUNICIPAL",
    )


#: QuantLib's settlement for the bond functions' close on 2026-10-16.
SETTLE = date(2026, 10, 19)


def _bonds() -> list[Any]:
    held: list[Any] = oracle("bond-functions.json")["bonds"]
    return held


@pytest.mark.parametrize("b", _bonds(), ids=lambda b: b["name"])
def test_accrued_interest_at_settlement_is_quantlibs_exactly(b: Any) -> None:
    assert _bond(b).accrued(SETTLE) == Decimal(b["quantlib"]["accrued"])


@pytest.mark.parametrize("b", _bonds(), ids=lambda b: b["name"])
def test_yield_risk_and_z_spread_are_quantlibs_within_their_tolerances(b: Any) -> None:
    bond, ql = _bond(b), {k: float(v) for k, v in b["quantlib"].items()}
    ytm = bond.yield_from_clean(b["clean"], SETTLE)
    tolerance = (
        T["treasury_yield_percent"]
        if bond.treasury
        else T["municipal_yield_percent"]
        if bond.municipal
        else T["street_yield_percent"]
    )
    assert abs(ytm - ql["yield_percent"]) <= tolerance, (ytm, ql["yield_percent"])
    # A municipal's duration is at its solved yield, unrounded.
    solved = ql["yield_percent"] if bond.municipal else ytm
    risk = bond.risk(solved, SETTLE)
    years = T["treasury_duration_years"] if bond.treasury else T["duration_years"]
    assert abs(risk["macaulay_duration"] - ql["macaulay"]) <= years
    assert abs(risk["modified_duration"] - ql["modified"]) <= years
    assert abs(risk["convexity"] - ql["convexity"]) <= ql["convexity"] * T["convexity_relative"]
    dv01 = risk["dv01_per_100"]
    assert abs(dv01 + ql["bps"]) <= T["dv01_relative"] * max(abs(dv01), 1e-6) + 1e-6
    curve = _fitted(_curves()["2026-10-16"])
    z = bond.z_spread(b["clean"], SETTLE, curve)
    assert abs(z - ql["z_spread_bp"]) <= T["z_spread_bp"], (z, ql["z_spread_bp"])


def test_a_yield_and_its_price_round_trip() -> None:
    bond = reference.Bond(
        coupon=Decimal("4.65"), day_count="DAY_COUNT_THIRTY_360_BOND_BASIS",
        dated=date(2026, 2, 23), maturity=date(2046, 2, 23),
    )  # fmt: skip
    y = bond.yield_from_clean("90.5", SETTLE)
    clean = bond.dirty(y, SETTLE) - float(bond.accrued(SETTLE))
    assert abs(clean - 90.5) < 1e-9
    curve = _fitted(_curves()["2026-10-16"])
    assert bond.g_spread(y, curve) == pytest.approx((y - curve.par(bond.maturity)) * 100)


def test_the_expected_move_is_085_times_the_at_the_money_straddle() -> None:
    chain = {
        Decimal("225"): (Decimal("10.20"), Decimal("2.35")),
        Decimal("230"): (Decimal("5.60"), Decimal("5.10")),
        Decimal("235"): (Decimal("4.25"), Decimal("6.40")),
    }
    # 230: |5.60 - 5.10| is the least; 0.85 x 10.70 = 9.095.
    assert reference.expected_move(chain) == Decimal("9.0950")
    with pytest.raises(ValueError, match="at least one strike"):
        reference.expected_move({})
