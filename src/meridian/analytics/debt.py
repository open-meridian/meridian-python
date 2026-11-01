"""The reference computations v29's curve and bond measures are held to
(spec/the-analytics-engine-answers-behind-one-api, requirement 36;
spec/the-analytics-engines-first-release, §3 "v29: bonds" and §4; W12.1;
rulings 688 and 994).

Nothing here is the engine. It is the reference an implementation is
checked against, written from the contract's text and the published
formulas, slow on purpose and easy to read beside them:

- **The templates' packages, exactly** (`package_answer`): a Treasury
  note's or bond's price per 100 from its auction's high yield under 31 CFR
  356 Appendix B (`treasury_price`: the coupons and principal discounted a
  half-year at a time from the next coupon date, and simple interest over
  the fraction of the half-year to it), a bill's from its discount rate
  (`bill_price`), accrued interest by the record's day count (MSRB G-33's
  30/360; actual/365 fixed for a CD), a pool's or a class's month (interest
  on the prior factor's face at 30/360, principal the factor's fall, each
  rounded once to the cent) and a TBA's market value in percent of par. In
  `decimal` and `fractions`, exact, each rounded once, half to even, to the
  places the package states.
- **The bond functions, to their tolerances** (`Bond`): yield from a clean
  price by the street's formula, compounded at the coupon frequency on the
  bond's day count (a Treasury's on Appendix B's, a municipal's rounded as
  MSRB G-33 asks: truncated to four places, then rounded to three); Macaulay
  and modified duration, convexity and DV01 per 100 of face (modified
  duration times the dirty price over 10,000); the Z-spread over a fitted
  zero curve, semi-annual on actual/365 fixed from the curve's date; the
  G-spread over its par curve at the bond's maturity. In binary floating
  point, as the measures are model measures held to tolerances.
- **The Treasury curve** (`Curve.fit`, `monotone_convex` v1): Hagan and
  West's monotone convex forward (2006, section 4), each interval's average
  the discrete forward, fitted so a par bond at each tenor -- issued on the
  curve's date, half its par yield twice a year on a half-year grid back
  from maturity, a first period short on actual/actual (ICMA) -- prices to
  100; time actual/365 fixed from the date, zero rates continuous.
- **`expected_move`** (639): 0.85 times the at-the-money straddle's mid,
  the strike whose call and put mids are closest.

The tolerances an implementation is held to against QuantLib, the oracle
(565; core's `crates/analytics-engine/oracle_cases/`, its SOURCE and
`src/bonds/oracle.rs`), are named here (`TOLERANCES`), so this reference
and the engine answer to the same bounds.

Not here, for want of an oracle case to hold them to: key-rate durations,
historical prepayment, WAL at a CPR and the make-whole amount.
"""

from __future__ import annotations

import calendar
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from typing import Any

from ..roles import debt

__all__ = [
    "TOLERANCES",
    "Bond",
    "Curve",
    "bill_price",
    "expected_move",
    "package_answer",
    "treasury_price",
]

#: The tolerances against QuantLib (core's oracle, `src/bonds/oracle.rs`):
#: a yield in percent on the street's formula, a Treasury's on Appendix B's
#: simple interest over the fractional half-year (QuantLib compounds it), a
#: municipal's rounded by G-33; a duration in years; convexity relative;
#: DV01 relative with a floor; the Z-spread in basis points; the curve's
#: continuous zero rates in basis points against QuantLib's fit and against
#: the Board's (Gurkaynak, Sack and Wright's Svensson curve); a par yield's
#: round trip in percent.
TOLERANCES: Mapping[str, float] = {
    "street_yield_percent": 5e-7,
    "treasury_yield_percent": 1e-3,
    "municipal_yield_percent": 1e-3,
    "duration_years": 1e-6,
    "treasury_duration_years": 2e-3,
    "convexity_relative": 1e-4,
    "dv01_relative": 1e-4,
    "z_spread_bp": 0.5,
    "curve_vs_quantlib_bp": 0.5,
    "curve_vs_board_bp": 10.0,
    "par_round_trip_percent": 1e-9,
}


def _day(value: date | str) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def _round(value: Fraction | Decimal, places: int) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
    return debt._half_even(value, places)


# ── The packages' cases, exactly ─────────────────────────────────────────


def treasury_price(
    coupon_rate: Decimal | str,
    yield_percent: Decimal | str,
    *,
    dated: date | str,
    first_coupon: date | str,
    maturity: date | str,
    settlement: date | str,
    frequency: int = 2,
    places: int = 6,
) -> tuple[Decimal, Decimal]:
    """A Treasury note's or bond's clean price and accrued interest per 100
    from a yield, by 31 CFR 356 Appendix B: each coupon and the principal
    discounted a period at a time back to the next coupon date, then over
    the fraction of the period to it at simple interest; the accrued the
    coupon times the period's elapsed fraction, rounded to `places` as
    Treasury announces it, and the price the dirty price less that accrued,
    rounded once to `places`, half to even."""
    with localcontext() as ctx:
        ctx.prec = 60
        c = Decimal(coupon_rate) / frequency
        i = Decimal(yield_percent) / 100 / frequency
        start, pay, (ref_start, ref_end) = debt.coupon_period(
            settlement, maturity, frequency, dated=dated, first_coupon=first_coupon
        )
        dates = debt.coupon_dates(maturity, frequency, dated=dated, first_coupon=first_coupon)
        remaining = [d for d in dates if d > _day(settlement)]
        n = len(remaining)
        r = Decimal((pay - _day(settlement)).days)
        s = Decimal((ref_end - ref_start).days)
        v = 1 / (1 + i)
        at_next = c + sum((c * v**k for k in range(1, n)), Decimal(0)) + 100 * v ** (n - 1)
        dirty = at_next / (1 + i * r / s)
        elapsed = Decimal((_day(settlement) - start).days)
        accrued = _round(c * elapsed / s, places)
        return _round(dirty - accrued, places), accrued


def bill_price(
    discount_rate: Decimal | str,
    *,
    settlement: date | str,
    maturity: date | str,
    places: int = 6,
) -> Decimal:
    """A Treasury bill's price per 100 from its discount rate, by Appendix
    B: 100 times one less the rate times the days to maturity over 360."""
    days = (_day(maturity) - _day(settlement)).days
    exact = 100 * (1 - Fraction(Decimal(discount_rate)) / 100 * Fraction(days, 360))
    return _round(exact, places)


def _text(value: Decimal) -> str:
    return format(value, "f")


def package_answer(inputs: Mapping[str, Any]) -> dict[str, str]:
    """What a debt template's calculation package answers for one of its
    test cases (W1.24; the platform's `test_cases`), by the inputs it names:
    an auction's price and accrued from its high yield or a bill's from its
    discount rate; accrued interest from an accrual start; a pool's or a
    class's month from its factors; a TBA's market value from its close in
    percent of par."""

    def get(name: str, default: str = "") -> str:
        held = inputs.get(name, default)
        return str(held)

    if "high_discount_rate" in inputs:
        price = bill_price(
            get("high_discount_rate"), settlement=get("settlement_date"),
            maturity=get("maturity_date"),
        )  # fmt: skip
        return {"price_per100": _text(price)}
    if "high_yield" in inputs:
        price, accrued = treasury_price(
            get("coupon_rate"), get("high_yield"), dated=get("dated_date"),
            first_coupon=get("first_coupon_date"), maturity=get("maturity_date"),
            settlement=get("settlement_date"), frequency=int(get("coupon_frequency", "2")),
        )  # fmt: skip
        return {"accrued_per100": _text(accrued), "price_per100": _text(price)}
    if "accrual_start_date" in inputs:
        exact = debt.accrued_per100(
            get("coupon_rate"), get("day_count"), get("accrual_start_date"),
            get("settlement_date"),
        )  # fmt: skip
        return {"accrued_per100": _text(_round(exact, 6).normalize())}
    if "original_face" in inputs:
        face = Fraction(Decimal(get("original_face")))
        prior, now = Fraction(Decimal(get("prior_factor"))), Fraction(Decimal(get("factor")))
        rate = Fraction(Decimal(get("pass_through_rate", get("coupon_rate"))))
        # A month at 30/360 is 30/360 of a year: interest on the face
        # outstanding before the month's payment.
        interest = face * prior * rate / 100 * Fraction(30, 360)
        principal = face * (prior - now)
        return {
            "interest": _text(_round(interest, 2)),
            "principal": _text(_round(principal, 2)),
        }
    if "close" in inputs and get("basis") == "PRICE_BASIS_PERCENT_OF_PAR":
        value = (
            Fraction(Decimal(get("quantity")))
            * Fraction(Decimal(get("close")))
            / 100
            * Fraction(Decimal(get("fx", "1")))
        )
        return {"market_value": _text(_round(value, 2))}
    raise ValueError(f"no package case reads these inputs: {sorted(inputs)}")


# ── The Treasury curve: monotone convex (Hagan and West 2006, §4) ────────


def _g(g0: float, g1: float, x: float) -> float:
    """The forward's departure from the interval's average at x in [0, 1]
    (Hagan and West's g, its four regions)."""
    if g0 == 0 and g1 == 0:
        return 0.0
    if (g0 < 0 and -0.5 * g0 <= g1 <= -2 * g0) or (g0 > 0 and -0.5 * g0 >= g1 >= -2 * g0):
        return g0 * (1 - 4 * x + 3 * x * x) + g1 * (-2 * x + 3 * x * x)
    if (g0 < 0 and g1 > -2 * g0) or (g0 > 0 and g1 < -2 * g0):
        eta = (g1 + 2 * g0) / (g1 - g0)
        return g0 if x <= eta else g0 + (g1 - g0) * ((x - eta) / (1 - eta)) ** 2
    if (g0 > 0 and 0 > g1 > -0.5 * g0) or (g0 < 0 and 0 < g1 < -0.5 * g0):
        eta = 3 * g1 / (g1 - g0)
        return g1 + (g0 - g1) * ((eta - x) / eta) ** 2 if x < eta else g1
    eta = g1 / (g1 + g0)
    a = -g0 * g1 / (g0 + g1)
    if x <= eta:
        return a + (g0 - a) * ((eta - x) / eta) ** 2
    return a + (g1 - a) * ((x - eta) / (1 - eta)) ** 2


def _g_integral(g0: float, g1: float, x: float) -> float:
    """The integral of `_g` from 0 to x, in closed form per region."""
    if g0 == 0 and g1 == 0:
        return 0.0
    if (g0 < 0 and -0.5 * g0 <= g1 <= -2 * g0) or (g0 > 0 and -0.5 * g0 >= g1 >= -2 * g0):
        return g0 * (x - 2 * x * x + x**3) + g1 * (-x * x + x**3)
    if (g0 < 0 and g1 > -2 * g0) or (g0 > 0 and g1 < -2 * g0):
        eta = (g1 + 2 * g0) / (g1 - g0)
        if x <= eta:
            return g0 * x
        return g0 * x + (g1 - g0) * (x - eta) ** 3 / (3 * (1 - eta) ** 2)
    if (g0 > 0 and 0 > g1 > -0.5 * g0) or (g0 < 0 and 0 < g1 < -0.5 * g0):
        eta = 3 * g1 / (g1 - g0)
        if x < eta:
            return g1 * x + (g0 - g1) * (eta**3 - (eta - x) ** 3) / (3 * eta * eta)
        return g1 * x + (g0 - g1) * eta / 3
    eta = g1 / (g1 + g0)
    a = -g0 * g1 / (g0 + g1)
    if x <= eta:
        return a * x + (g0 - a) * (eta**3 - (eta - x) ** 3) / (3 * eta * eta)
    return a * x + (g0 - a) * eta / 3 + (g1 - a) * (x - eta) ** 3 / (3 * (1 - eta) ** 2)


@dataclass
class _Forwards:
    """A monotone convex forward over knots `times` (0 first), each interval's
    average forward `discrete[i]` on (times[i], times[i+1]]."""

    times: list[float]
    discrete: list[float]
    nodes: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        t, fd = self.times, self.discrete
        n = len(fd)
        nodes = [0.0] * (n + 1)
        for i in range(1, n):
            left, right = t[i] - t[i - 1], t[i + 1] - t[i]
            nodes[i] = (left * fd[i] + right * fd[i - 1]) / (left + right)
        nodes[0] = fd[0] - 0.5 * (nodes[1] - fd[0]) if n > 1 else fd[0]
        nodes[n] = fd[n - 1] - 0.5 * (nodes[n - 1] - fd[n - 1]) if n > 1 else fd[0]
        # The positivity collar (Hagan and West, §4.2).
        nodes[0] = min(max(nodes[0], 0.0), 2 * fd[0])
        for i in range(1, n):
            nodes[i] = min(max(nodes[i], 0.0), 2 * min(fd[i - 1], fd[i]))
        nodes[n] = min(max(nodes[n], 0.0), 2 * fd[n - 1])
        self.nodes = nodes

    def integral(self, tau: float) -> float:
        """The forward's integral from 0 to `tau`, flat past the last knot."""
        t, fd, f = self.times, self.discrete, self.nodes
        total = 0.0
        for i in range(len(fd)):
            lo, hi = t[i], t[i + 1]
            if tau <= lo:
                break
            width = hi - lo
            g0, g1 = f[i] - fd[i], f[i + 1] - fd[i]
            if tau >= hi:
                total += fd[i] * width + width * _g_integral(g0, g1, 1.0)
            else:
                x = (tau - lo) / width
                total += fd[i] * (tau - lo) + width * _g_integral(g0, g1, x)
        if tau > t[-1]:
            total += (fd[-1] + (f[-1] - fd[-1])) * (tau - t[-1])
        return total


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def maturity_of(on: date, tenor: str) -> date:
    """A tenor's maturity from a date: months and years by calendar months,
    weeks and days by days (`10Y`, `3M`, `6W`)."""
    count, unit = int(tenor[:-1]), tenor[-1].upper()
    if unit == "M":
        return _add_months(on, count)
    if unit == "Y":
        return _add_months(on, 12 * count)
    if unit == "W":
        return on + timedelta(days=7 * count)
    if unit == "D":
        return on + timedelta(days=count)
    raise ValueError(f"{tenor!r} is no tenor")


def _par_bond(on: date, maturity: date, par_percent: float) -> list[tuple[date, float]]:
    """A par bond issued on `on`: half its coupon twice a year back from
    maturity, a first period short accrued on actual/actual (ICMA) against
    its notional half-year; 100 at maturity."""
    dates = []
    k = 0
    while True:
        at = _add_months(maturity, -6 * k)
        if at <= on:
            break
        dates.append(at)
        k += 1
    dates.sort()
    flows = []
    for j, pay in enumerate(dates):
        start = dates[j - 1] if j else on
        reference = _add_months(pay, -6)
        fraction = (pay - start).days / (pay - reference).days * 0.5
        flows.append((pay, par_percent * fraction))
    last = flows[-1]
    flows[-1] = (last[0], last[1] + 100.0)
    return flows


@dataclass
class Curve:
    """A Treasury curve at a date: monotone convex forwards fitted to par
    yields, time actual/365 fixed from the date."""

    on: date
    forwards: _Forwards

    def t(self, day: date) -> float:
        return (day - self.on).days / 365.0

    def discount(self, on: date) -> float:
        return math.exp(-self.forwards.integral(self.t(on)))

    def zero(self, on: date) -> float:
        """The continuous zero rate to a date, a fraction."""
        t = self.t(on)
        return self.forwards.integral(t) / t

    def par(self, maturity: date) -> float:
        """The par yield, in percent, of a bond issued on the curve's date
        maturing on `maturity`, as the fit's bonds are built."""
        unit = _par_bond(self.on, maturity, 1.0)
        annuity = sum(
            self.discount(d) * (c - (100.0 if d == maturity else 0.0)) for d, c in unit
        )
        return (100.0 - 100.0 * self.discount(maturity)) / annuity

    @classmethod
    def fit(cls, on: date | str, par: Sequence[tuple[str, float | str]]) -> Curve:
        """Fitted to each tenor's par yield (percent): every knot's discrete
        forward found so its par bond prices to 100, pass after pass until
        none moves by more than 1e-13."""
        day = _day(on)
        points = sorted(((maturity_of(day, tenor), float(y)) for tenor, y in par))
        times = [0.0] + [(m - day).days / 365.0 for m, _ in points]
        bonds = [_par_bond(day, m, y) for m, y in points]
        discrete = [y / 100.0 for _, y in points]

        def priced(fd: list[float], k: int) -> float:
            curve = _Forwards(times, fd)
            return sum(
                c * math.exp(-curve.integral((d - day).days / 365.0)) for d, c in bonds[k]
            )

        for _ in range(200):
            moved = 0.0
            for k in range(len(points)):

                def error(value: float, k: int = k) -> float:
                    trial = discrete.copy()
                    trial[k] = value
                    return priced(trial, k) - 100.0

                solved = _secant(error, discrete[k], discrete[k] + 1e-4)
                moved = max(moved, abs(solved - discrete[k]))
                discrete[k] = solved
            if moved < 1e-13:
                break
        return cls(day, _Forwards(times, discrete))


def _secant(f: Callable[[float], float], a: float, b: float) -> float:
    fa, fb = f(a), f(b)
    for _ in range(100):
        if fb == fa:
            return b
        c = b - fb * (b - a) / (fb - fa)
        a, fa = b, fb
        b, fb = c, f(c)
        if abs(b - a) < 1e-16:
            break
    return b


def _bisect(f: Callable[[float], float], lo: float, hi: float) -> float:
    flo = f(lo)
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
        if hi - lo < 1e-15:
            break
    return (lo + hi) / 2


# ── The bond functions ───────────────────────────────────────────────────


@dataclass(frozen=True)
class Bond:
    """A fixed-coupon bond's terms: its coupon (percent a year), day count,
    dates and frequency; `treasury` priced by Appendix B, `municipal` its
    yield rounded by G-33."""

    coupon: Decimal
    day_count: str
    dated: date
    maturity: date
    first_coupon: date | None = None
    frequency: int = 2
    treasury: bool = False
    municipal: bool = False

    def _flows(self, settlement: date) -> tuple[float, list[float], float]:
        """The fraction of a period to the next coupon (`f`), each remaining
        cash flow per 100 (the coupon, the last with principal), and the
        accrued per 100."""
        start, pay, period = debt.coupon_period(
            settlement, self.maturity, self.frequency, dated=self.dated,
            first_coupon=self.first_coupon,
        )  # fmt: skip
        dates = debt.coupon_dates(
            self.maturity, self.frequency, dated=self.dated, first_coupon=self.first_coupon
        )
        remaining = [d for d in dates if d > settlement]
        per = float(self.coupon) / self.frequency
        flows = [per] * len(remaining)
        flows[-1] += 100.0
        to_next = debt.year_fraction(
            self.day_count, settlement, pay, period=period, frequency=self.frequency
        )
        f = float(to_next) * self.frequency
        accrued = debt.accrued_per100(
            self.coupon, self.day_count, start, settlement, period=period,
            frequency=self.frequency,
        )  # fmt: skip
        return f, flows, float(accrued)

    def accrued(self, settlement: date | str, places: int = 12) -> Decimal:
        """Accrued interest per 100 at settlement, exact, rounded once."""
        on = _day(settlement)
        start, _, period = debt.coupon_period(
            on, self.maturity, self.frequency, dated=self.dated, first_coupon=self.first_coupon
        )
        exact = debt.accrued_per100(
            self.coupon, self.day_count, start, on, period=period, frequency=self.frequency
        )
        return _round(exact, places)

    def dirty(self, yield_percent: float, settlement: date | str) -> float:
        """The dirty price per 100 at a yield: compounded a period at a time,
        and for a Treasury at simple interest over the first fraction
        (Appendix B)."""
        f, flows, _ = self._flows(_day(settlement))
        i = yield_percent / 100.0 / self.frequency
        if self.treasury:
            at_next = sum(c * math.pow(1 + i, -k) for k, c in enumerate(flows))
            return at_next / (1 + i * f)
        total: float = sum(c * math.pow(1 + i, -(f + k)) for k, c in enumerate(flows))
        return total

    def yield_from_clean(self, clean: float | str, settlement: date | str) -> float:
        """The yield, in percent, at which the bond's dirty price is the clean
        price plus accrued; a municipal's then truncated to four places and
        rounded to three (MSRB G-33)."""
        on = _day(settlement)
        target = float(clean) + self._flows(on)[2]
        solved = _bisect(lambda y: self.dirty(y, on) - target, -5.0, 50.0)
        if self.municipal:
            cut = Decimal(repr(solved)).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
            return float(cut.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
        return solved

    def risk(self, yield_percent: float, settlement: date | str) -> dict[str, float]:
        """Macaulay and modified duration (years), convexity, and DV01 per 100
        (modified duration times the dirty price over 10,000), at a yield
        compounded at the coupon frequency."""
        f, flows, _ = self._flows(_day(settlement))
        m = self.frequency
        y = yield_percent / 100.0
        base = 1 + y / m
        times = [(f + k) / m for k in range(len(flows))]
        pv = [c * base ** (-m * t) for c, t in zip(flows, times, strict=True)]
        dirty = sum(pv)
        macaulay = sum(t * p for t, p in zip(times, pv, strict=True)) / dirty
        modified = macaulay / base
        convexity = (
            sum(
                c * t * (t + 1 / m) * base ** (-m * t - 2)
                for c, t in zip(flows, times, strict=True)
            )
            / dirty
        )
        return {
            "macaulay_duration": macaulay,
            "modified_duration": modified,
            "convexity": convexity,
            "dv01_per_100": modified * dirty / 10_000,
        }

    def z_spread(self, clean: float | str, settlement: date | str, curve: Curve) -> float:
        """The spread, in basis points, over the curve's zero rates
        compounded semi-annually on actual/365 fixed, at which the bond's cash
        flows, discounted to settlement, are its dirty price."""
        on = _day(settlement)
        _, flows, accrued = self._flows(on)
        dates = [
            d
            for d in debt.coupon_dates(
                self.maturity, self.frequency, dated=self.dated, first_coupon=self.first_coupon
            )
            if d > on
        ]
        target = float(clean) + accrued

        def discount(d: date, s: float) -> float:
            t = curve.t(d)
            semi = 2 * (math.exp(curve.zero(d) / 2) - 1) if t > 0 else 0.0
            return math.pow(1 + (semi + s) / 2, -2 * t)

        def price(s: float) -> float:
            at = discount(on, s)
            return sum(c * discount(d, s) for c, d in zip(flows, dates, strict=True)) / at

        return _bisect(lambda s: price(s) - target, -0.5, 0.5) * 10_000

    def g_spread(self, yield_percent: float, curve: Curve) -> float:
        """The yield less the curve's par yield at the bond's maturity, in
        basis points."""
        return (yield_percent - curve.par(self.maturity)) * 100


# ── expected_move (639) ──────────────────────────────────────────────────


def expected_move(strikes: Mapping[Decimal, tuple[Decimal, Decimal]]) -> Decimal:
    """An expiration's expected move: 0.85 times the at-the-money straddle's
    mid, at the strike whose call and put mids are closest (`strikes` maps
    each strike to its call's and put's mids), rounded once to 4 places."""
    if not strikes:
        raise ValueError("an expected move reads at least one strike")
    strike = min(strikes, key=lambda k: (abs(strikes[k][0] - strikes[k][1]), k))
    call, put = strikes[strike]
    return _round(Fraction(Decimal("0.85")) * (Fraction(call) + Fraction(put)), 4)


def load(path: str) -> Any:
    """An oracle case file, as core keeps it."""
    with open(path, encoding="utf-8") as held:
        return json.load(held)
