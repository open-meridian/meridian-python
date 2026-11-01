"""Fixed income's common role logic (contract v29,
sdk-contract/fixed-income-contract; rulings 680 to 688 and 986 to 997;
W9.16, W9.17, W10.4, W10.6, W11.11, W11.27).

What every plugin of a role must do the same with a debt record, written
once here and generic over the source: the contract's money rules, a
coupon's accrual by its day count, the factor as a dated fact and a yield as
its source quotes it. Nothing here re-derives the book: what the book
decides -- the factor a fill was taken at, whether it is provisional, a
revision's differences, the lots' cost -- is read from its records
(`taken`, `awaited`, `open_claims`), never computed beside them.

**Money** (W11.11, W9.16; rulings 987, 988, 993). A debt record's quantity
is face; a price is per 100 of face (`Execution.price` always the dollar
price, 987), so its cash is `percent_of_par(face, price)`, face times price
times 0.01, exact. A pool's or a tranche's lots stay in original face, its
current face `current_face(original_face, factor)`, read and never stored;
its fill's cash is `fill_cash(original_face, price, factor)`, rounded to the
cent half-even (`to_cent`, 993), as is a paydown's principal
(`paydown_cash`). A lot's cost relieved by a paydown is `relief` (W9.16's
rule, for reconciling a custodian's stated cost against the book's, never
written to it). A coupon is booked as two cash lines, the purchased accrued
returned and the income (988): `coupon_split` says which is which for a
custodian that states them apart.

**Accrual** (W1.24's package; FIX CouponDayCount, 1950). `year_fraction`
by the record's day count, exact, `accrued_per100` and `coupon_dates` for
the schedule, backward from maturity. A day count v29's engine does not
compute (BUS/252, actual/actual AFB, ICMA ultimo; ruling 997) is refused
naming it (`NOT_SUPPORTED`), never approximated.

**The data role** (W10.4). An agency's factor for a pool or a REMIC class,
as published (`factor`, a `Factor` row under the pool's `INS-` record,
keyed by its month; `wac`, `wam` and `wala` where the disclosure states
them, 995) for the records the deployment names alone, never a whole file;
a yield as its source quotes it beside a price (`quoted_yield`, a
`QuotedYield`, semi-annual bond-equivalent); a capped size as at least
(`capped`, TRACE's 5MM+); and the platform's fixed-income trade
characteristics by meaning (`characteristics`).

**Readers** (W10.6). A pool's factor history, every page (`read_factors`),
the row in force for a month (`latest`), the month a settlement takes its
factor from (`settlement_month`, 991: the month before it settles); and the
book's own words on a pool's fill (`taken`, `awaited`) and on its factor
revisions (`open_claims`).
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from fractions import Fraction
from typing import Any

from ..operations import (
    Factor,
    Money,
    ObservationMeta,
    QuotedYield,
    RateConvention,
    SubjectRef,
    UnitValue,
)
from ..plugin.v1 import operations_pb2 as ops

__all__ = [
    "CENT",
    "NOT_SUPPORTED",
    "CouponSplit",
    "accrued_per100",
    "awaited",
    "capped",
    "characteristics",
    "coupon_dates",
    "coupon_period",
    "coupon_split",
    "current_face",
    "factor",
    "factor_month",
    "fill_cash",
    "latest",
    "open_claims",
    "paydown_cash",
    "percent_of_par",
    "quoted_yield",
    "read_factors",
    "relief",
    "settlement_month",
    "taken",
    "to_cent",
    "year_fraction",
]

#: The book's money rule for a pool's or a tranche's cash (993): the cent,
#: half-even.
CENT = Decimal("0.01")
_PER_100 = Decimal("0.01")

#: The day counts v29's engine does not compute (ruling 997), named
#: NOT_EVALUATED_REASON_NOT_SUPPORTED in an answer and refused here.
NOT_SUPPORTED = frozenset(
    {"DAY_COUNT_BUS_252", "DAY_COUNT_ACT_ACT_AFB", "DAY_COUNT_ACT_ACT_ICMA_ULTIMO"}
)


# ── Money ────────────────────────────────────────────────────────────────


def _d(value: Decimal | int | str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal | int | str):
        raise TypeError(
            f"an amount is a Decimal, an int or its text, not {type(value).__name__}"
        )
    return Decimal(value)


def to_cent(amount: Decimal | int | str | Fraction) -> Decimal:
    """An amount rounded to the cent, half to even (993); a `Fraction`
    rounded from its exact value."""
    if isinstance(amount, Fraction):
        return _half_even(amount, 2)
    return _d(amount).quantize(CENT, rounding=ROUND_HALF_EVEN)


def percent_of_par(face: Decimal | int | str, price_per100: Decimal | int | str) -> Decimal:
    """Face at a price per 100 of face: face times price times 0.01, exact
    (W11.11, amended at core stage B)."""
    return _d(face) * _d(price_per100) * _PER_100


def current_face(original_face: Decimal | int | str, factor: Decimal | int | str) -> Decimal:
    """A pool's or a tranche's current face: original face times its factor,
    exact; read, never stored (680)."""
    return _d(original_face) * _d(factor)


def fill_cash(
    original_face: Decimal | int | str,
    price_per100: Decimal | int | str,
    factor: Decimal | int | str,
) -> Decimal:
    """A pool's or a tranche's fill's cash: original face times its factor
    times the price over 100, rounded to the cent half-even
    (`Execution.factor_used`, 993)."""
    return to_cent(current_face(original_face, factor) * _d(price_per100) * _PER_100)


def paydown_cash(
    original_face: Decimal | int | str,
    prior_factor: Decimal | int | str,
    factor: Decimal | int | str,
) -> Decimal:
    """A paydown's principal: the factor's fall times original face, rounded
    to the cent half-even (W9.16; 993). Negative where the factor rose, an
    accretion, which moves no cash."""
    return to_cent((_d(prior_factor) - _d(factor)) * _d(original_face))


def relief(
    cost: Decimal | int | str,
    prior_factor: Decimal | int | str,
    factor: Decimal | int | str,
) -> Decimal:
    """A lot's cost relieved by a paydown (W9.16, amended at core stage B):
    its cost times the factor's fall over the prior factor, exact where the
    quotient ends within the cost's places and half-even at them otherwise,
    the remainder kept in the lot. For a plugin reconciling a custodian's
    stated cost basis with the book's; the book relieves its own lots."""
    held, prior = _d(cost), _d(prior_factor)
    if prior <= 0:
        raise ValueError(f"a paydown's prior factor is above zero, not {prior}")
    exact = Fraction(held) * (Fraction(prior) - Fraction(_d(factor))) / Fraction(prior)
    places = max(-int(held.as_tuple().exponent), 0)
    return _half_even(exact, places)


def _half_even(value: Fraction, places: int) -> Decimal:
    """`value` to `places`, exact where it ends within them, half to even at
    them otherwise."""
    scaled = value * 10**places
    floor = scaled.numerator // scaled.denominator
    rest = scaled - floor
    if rest > Fraction(1, 2) or (rest == Fraction(1, 2) and floor % 2 == 1):
        floor += 1
    return Decimal(floor).scaleb(-places)


@dataclass(frozen=True)
class CouponSplit:
    """A coupon received as the book books it (988): the purchased accrued
    returned -- the accrued interest the account's purchases settling within
    the period paid, at most the coupon -- and the income, the rest."""

    returned: Money
    income: Money


def coupon_split(coupon: Money, purchased_accrued: Money) -> CouponSplit:
    """A coupon's two cash lines (988): what of it returns the accrued its
    purchases paid, and the income. The coupon's cash is what a custody
    plugin reports (`LifecycleEvent.cash`), the two lines added back where
    its custodian states them apart."""
    if coupon.currency_code != purchased_accrued.currency_code or (
        coupon.instrument_id != purchased_accrued.instrument_id
    ):
        raise ValueError("a coupon and the accrued its purchases paid are in one currency")
    paid, whole = _d(purchased_accrued.amount), _d(coupon.amount)
    if paid < 0:
        raise ValueError(f"the purchased accrued is what purchases paid, not {paid}")
    returned = min(paid, whole) if whole > 0 else Decimal(0)
    return CouponSplit(
        returned=Money(returned, coupon.currency_code, coupon.instrument_id),
        income=Money(whole - returned, coupon.currency_code, coupon.instrument_id),
    )


# ── Day counts and accrual ───────────────────────────────────────────────


def _day_count(value: Any) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(ops.DayCount.Name(value))
    text = str(value)
    if text.startswith("DAY_COUNT_"):
        return text
    return "DAY_COUNT_" + text.upper()


def _day(value: date | str) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def _last_of_month(d: date) -> bool:
    return d.day == calendar.monthrange(d.year, d.month)[1]


def _thirty(d1: date, d2: date, kind: str, maturity: date | None) -> int:
    y1, m1, a = d1.year, d1.month, d1.day
    y2, m2, b = d2.year, d2.month, d2.day
    if kind == "DAY_COUNT_THIRTY_360_SIA":
        # The SIA's 30/360 (US): February's last day is the 30th, at both
        # ends where both are; then the bond basis.
        feb1 = m1 == 2 and _last_of_month(d1)
        feb2 = m2 == 2 and _last_of_month(d2)
        if feb1 and feb2:
            b = 30
        if feb1:
            a = 30
    if kind in ("DAY_COUNT_THIRTY_E_360",):
        a, b = min(a, 30), min(b, 30)
    elif kind == "DAY_COUNT_THIRTY_E_360_ISDA":
        if _last_of_month(d1):
            a = 30
        if _last_of_month(d2) and not (m2 == 2 and maturity is not None and d2 == maturity):
            b = 30
    else:
        # The bond basis (ISDA 2006 4.16(f); MSRB G-33(b)(i)(B)).
        if a == 31:
            a = 30
        if b == 31 and a == 30:
            b = 30
    return 360 * (y2 - y1) + 30 * (m2 - m1) + (b - a)


def _no_leap_days(d1: date, d2: date) -> int:
    days = (d2 - d1).days
    for year in range(d1.year, d2.year + 1):
        if calendar.isleap(year):
            leap = date(year, 2, 29)
            if d1 < leap <= d2:
                days -= 1
    return days


def year_fraction(
    day_count: Any,
    start: date | str,
    end: date | str,
    *,
    period: tuple[date | str, date | str] | None = None,
    frequency: int = 2,
    maturity: date | str | None = None,
) -> Fraction:
    """The fraction of a year from `start` to `end` by `day_count` (its
    `DayCount` value, name, or name without the prefix), exact. Actual/actual
    (ICMA) needs the coupon `period` the dates fall in and the `frequency`;
    the 30E/360 (ISDA) rule's February end the `maturity`. A day count v29's
    engine does not compute, or none this reference knows, is refused
    naming it."""
    kind = _day_count(day_count)
    d1, d2 = _day(start), _day(end)
    if kind in NOT_SUPPORTED:
        raise ValueError(f"{kind} is not supported (ruling 997)")
    if kind in (
        "DAY_COUNT_THIRTY_360",
        "DAY_COUNT_THIRTY_360_BOND_BASIS",
        "DAY_COUNT_THIRTY_360_SIA",
        "DAY_COUNT_THIRTY_E_360",
        "DAY_COUNT_THIRTY_E_360_ISDA",
    ):
        held = _day(maturity) if maturity is not None else None
        return Fraction(_thirty(d1, d2, kind, held), 360)
    if kind == "DAY_COUNT_ACT_360":
        return Fraction((d2 - d1).days, 360)
    if kind == "DAY_COUNT_ACT_365_FIXED":
        return Fraction((d2 - d1).days, 365)
    if kind == "DAY_COUNT_ACT_364":
        return Fraction((d2 - d1).days, 364)
    if kind == "DAY_COUNT_NL_365":
        return Fraction(_no_leap_days(d1, d2), 365)
    if kind == "DAY_COUNT_NL_360":
        return Fraction(_no_leap_days(d1, d2), 360)
    if kind == "DAY_COUNT_ONE_ONE":
        return Fraction(1)
    if kind == "DAY_COUNT_ACT_ACT_ICMA" or (kind == "DAY_COUNT_ACT_ACT" and period):
        if not period:
            raise ValueError(f"{kind} reads the coupon period the dates fall in")
        ps, pe = _day(period[0]), _day(period[1])
        return Fraction((d2 - d1).days, frequency * (pe - ps).days)
    if kind in ("DAY_COUNT_ACT_ACT_ISDA", "DAY_COUNT_ACT_ACT"):
        total = Fraction(0)
        cursor = d1
        while cursor < d2:
            year_end = date(cursor.year + 1, 1, 1)
            stop = min(year_end, d2)
            total += Fraction(
                (stop - cursor).days, 366 if calendar.isleap(cursor.year) else 365
            )
            cursor = stop
        return total
    raise ValueError(f"{kind} is not a day count this reference computes")


def _add_months(d: date, months: int, end_of_month: bool) -> date:
    month = d.month - 1 + months
    year, month = d.year + month // 12, month % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, last if end_of_month else min(d.day, last))


def coupon_dates(
    maturity: date | str,
    frequency: int,
    *,
    dated: date | str,
    first_coupon: date | str | None = None,
) -> list[date]:
    """A fixed-coupon schedule's payment dates, unadjusted, oldest first:
    backward from maturity a period at a time (12 over `frequency` months),
    on the month's last day throughout where maturity is one, down to the
    first coupon (or the dated date, excluded)."""
    if frequency not in (1, 2, 4, 12):
        raise ValueError(f"a coupon frequency is 1, 2, 4 or 12 a year, not {frequency}")
    end, start = _day(maturity), _day(dated)
    first = _day(first_coupon) if first_coupon else None
    step = 12 // frequency
    eom = _last_of_month(end)
    dates, n = [], 0
    while True:
        at = _add_months(end, -step * n, eom)
        if at <= start or (first is not None and at < first):
            break
        dates.append(at)
        n += 1
    if first is not None and (not dates or dates[-1] != first):
        dates.append(first)
    return sorted(dates)


def coupon_period(
    settlement: date | str,
    maturity: date | str,
    frequency: int,
    *,
    dated: date | str,
    first_coupon: date | str | None = None,
) -> tuple[date, date, tuple[date, date]]:
    """The coupon period a settlement falls in: its accrual start (the last
    coupon date, or the dated date in the first period), its payment date,
    and the regular period of reference (a short first period's notional
    one) for actual/actual (ICMA)."""
    on = _day(settlement)
    dates = coupon_dates(maturity, frequency, dated=dated, first_coupon=first_coupon)
    step = 12 // frequency
    eom = _last_of_month(_day(maturity))
    for i, pay in enumerate(dates):
        if on < pay:
            start = dates[i - 1] if i else _day(dated)
            reference = start if i else _add_months(pay, -step, eom)
            return start, pay, (reference, pay)
    raise ValueError(f"{on} is on or after maturity {maturity}; nothing accrues")


def accrued_per100(
    coupon_rate: Decimal | int | str,
    day_count: Any,
    accrual_start: date | str,
    settlement: date | str,
    *,
    period: tuple[date | str, date | str] | None = None,
    frequency: int = 2,
) -> Fraction:
    """Accrued interest per 100 of face from the accrual start to settlement:
    the coupon rate (percent a year) times the day count's fraction, exact
    (W9.10: computed as of a date, never a stored balance)."""
    fraction = year_fraction(
        day_count, accrual_start, settlement, period=period, frequency=frequency
    )
    return Fraction(_d(coupon_rate)) * fraction


# ── The data role: factors, yields, capped sizes, characteristics ────────


def factor_month(value: date | str) -> str:
    """A factor month as the contract writes it, YYYYMM, from a date, a
    YYYY-MM or a YYYYMM."""
    if isinstance(value, date):
        return f"{value.year:04d}{value.month:02d}"
    text = str(value).strip()
    match = re.fullmatch(r"(\d{4})-?(\d{2})(?:-\d{2})?", text)
    if not match or not 1 <= int(match.group(2)) <= 12:
        raise ValueError(f"a factor month is YYYYMM, not {value!r}")
    return match.group(1) + match.group(2)


def settlement_month(settlement_date: date | str) -> str:
    """The factor month a pool's or a tranche's fill settling on a date takes
    its factor from: the month before the month it settles in (991)."""
    on = _day(settlement_date)
    before = on.replace(day=1) - timedelta(days=1)
    return factor_month(before)


def factor(
    subject_id: str,
    value: Decimal | int | str,
    month: date | str,
    *,
    dataset: str,
    published: date | str = "",
    record_date: date | str = "",
    payment_date: date | str = "",
    coupon_rate: Decimal | int | str | None = None,
    wac: Decimal | int | str | None = None,
    wam: int | None = None,
    wala: int | None = None,
    valid_from_ns: int = 0,
    raw: ops.RawRecordRef | None = None,
) -> Factor:
    """One month's factor of a pool or a REMIC class, as its agency publishes
    it (W10.4): under the record's `INS-` ID, keyed by its month, the factor
    an exact decimal as published, its business date the publication date;
    a floater's period `coupon_rate` from the reset file, and `wac` (percent
    a year), `wam` and `wala` (months) where the disclosure states them
    (995), unset otherwise. A republication is the next version of the same
    row key, which the lake numbers."""
    if not subject_id.startswith(("INS-", "LCL-")):
        raise ValueError(
            f"a factor's subject is a pool's or a class's record, not {subject_id!r}"
        )
    held = _d(value)
    if held < 0:
        raise ValueError(f"a factor is never below zero: {held}")
    month_text = factor_month(month)
    day = published if isinstance(published, str) else published.isoformat()
    return Factor(
        meta=ObservationMeta(
            row_key=f"{subject_id}:factor:{month_text}",
            subjects=[SubjectRef(entity_id=subject_id)],
            source=ops.Source(dataset=dataset),
            business_date=day,
            valid_from_ns=valid_from_ns,
            raw=raw,
        ),
        factor=held,
        factor_month=month_text,
        record_date=record_date,
        payment_date=payment_date,
        coupon_rate=None if coupon_rate is None else _d(coupon_rate),
        wac=None if wac is None else _d(wac),
        wam=wam,
        wala=wala,
    )


def quoted_yield(
    value: Decimal | int | str,
    kind: ops.YieldKind | str = "to_maturity",
    *,
    to_date: date | str = "",
    day_count: Any = None,
    periods_per_year: int = 2,
) -> QuotedYield:
    """A yield as its source quotes it, beside a price (W10.4, 987): in
    percent (4.312, never 0.04312), semi-annual bond-equivalent by default
    on the instrument's day count, its kind after FIX YieldType (235) and,
    to a call or a put, the date it is to. Never computed by the plugin."""
    kinds = {"to_call", "to_put", "YIELD_KIND_TO_CALL", "YIELD_KIND_TO_PUT"}
    if kind in kinds and not to_date:
        raise ValueError(f"a yield {kind} names the date it is to")
    return QuotedYield(
        value=UnitValue(value=_d(value), unit="percent"),
        convention=RateConvention(
            day_count=None if day_count is None else _day_count(day_count),
            compounding="discount"
            if kind in ("discount", "YIELD_KIND_DISCOUNT")
            else "compounded",
            periods_per_year=0
            if kind in ("discount", "YIELD_KIND_DISCOUNT")
            else periods_per_year,
        ),
        kind=kind,
        to_date=to_date,
    )


_SIZE = re.compile(r"^\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(MM|M|K)?\s*(\+)?\s*$", re.IGNORECASE)
_SCALE = {"": 1, "K": 1_000, "M": 1_000, "MM": 1_000_000}


def capped(size: str | Decimal | int) -> tuple[Decimal, bool]:
    """A size as a source disseminates it, and whether it is capped: TRACE's
    "5MM+" is at least 5,000,000 (`Trade.quantity_capped`,
    `Quote.bid_size_capped`, 685 and 900). MM is a million and M or K a
    thousand, as the bond market writes them; a plain number is exact."""
    if isinstance(size, Decimal | int) and not isinstance(size, bool):
        return Decimal(size), False
    match = _SIZE.match(str(size))
    if not match:
        raise ValueError(f"{size!r} is not a size")
    amount = Decimal(match.group(1).replace(",", "")) * _SCALE[(match.group(2) or "").upper()]
    return amount, match.group(3) is not None


def characteristics(
    *,
    contra_party: str = "",
    capacity: str = "",
    ats: bool = False,
    when_issued: bool = False,
    primary_market: bool = False,
    special_price: bool = False,
    list_offering_price_takedown: bool = False,
    non_transaction_compensation: bool = False,
    traded_flat: bool = False,
) -> list[str]:
    """A fixed-income print's characteristics in the platform's list, by
    meaning (W10.4; 685, 900's R5): its contra party (`customer`, `dealer`,
    `affiliate`), its reporting party's capacity (`agency`, `principal`),
    executed on an ATS, when issued, primary market, a special price, and a
    municipal print's list offering price or takedown, non-transaction
    compensation and traded flat. None listed is none the source states."""
    found: list[str] = []
    if contra_party:
        if contra_party not in ("customer", "dealer", "affiliate"):
            raise ValueError(
                f"a contra party is customer, dealer or affiliate, not {contra_party!r}"
            )
        found.append(f"TRADE_CHARACTERISTIC_CONTRA_{contra_party.upper()}")
    if capacity:
        if capacity not in ("agency", "principal"):
            raise ValueError(f"a capacity is agency or principal, not {capacity!r}")
        found.append(f"TRADE_CHARACTERISTIC_{capacity.upper()}_CAPACITY")
    for flag, name in (
        (ats, "ATS_EXECUTED"),
        (when_issued, "WHEN_ISSUED"),
        (primary_market, "PRIMARY_MARKET"),
        (special_price, "SPECIAL_PRICE"),
        (list_offering_price_takedown, "LIST_OFFERING_PRICE_TAKEDOWN"),
        (non_transaction_compensation, "NON_TRANSACTION_COMPENSATION"),
        (traded_flat, "TRADED_FLAT"),
    ):
        if flag:
            found.append(f"TRADE_CHARACTERISTIC_{name}")
    return found


# ── Readers ──────────────────────────────────────────────────────────────


async def read_factors(
    plugin: Any,
    subject_ids: Sequence[str],
    from_date: date | str = "",
    to_date: date | str = "",
    *,
    sources: ops.SourceChoice | None = None,
    as_of_ns: int = 0,
) -> list[ops.Factor]:
    """Each named pool's or class's factors by payment date, every page read
    (W10.6): a pool no source covers is named unanswered by the lake, never
    a factor of 1."""
    if not subject_ids:
        raise ValueError("a factor read names the pools or classes it reads")
    rows: list[ops.Factor] = []
    cursor = ""
    while True:
        page = await plugin.list_factors(
            subjects=[SubjectRef(entity_id=s) for s in subject_ids], from_date=from_date,
            to_date=to_date, sources=sources, as_of_ns=as_of_ns, cursor=cursor,
        )  # fmt: skip
        rows.extend(page.factors)
        cursor = page.next_cursor
        if not cursor:
            return rows


def _version(row: Any) -> int:
    return int(row.meta.version) if row.HasField("meta") else 0


def latest(rows: Iterable[Any], *, month: date | str | None = None) -> Any | None:
    """The factor in force: the latest version of the row of the greatest
    factor month, or of the greatest at or before `month` (YYYYMM). None
    where no row is."""
    bound = factor_month(month) if month is not None else None
    best = None
    for row in rows:
        if bound is not None and row.factor_month > bound:
            continue
        if best is None or (row.factor_month, _version(row)) > (
            best.factor_month,
            _version(best),
        ):
            best = row
    return best


def taken(execution: Any) -> Decimal | None:
    """The factor a pool's or a tranche's fill is priced at, as the book
    says (991): the stated override (`factor_used`) where there is one,
    else the factor the book took (`factor_taken`); None for any other
    fill."""
    from ..operations import as_decimal

    for name in ("factor_used", "factor_taken"):
        if execution.HasField(name):
            return as_decimal(getattr(execution, name))
    return None


def awaited(record: Any) -> str:
    """The factor month a fill or a lot is provisional on, YYYYMM, as the
    book says (992: `factor_month_awaited`), empty where its factor is
    final."""
    return str(getattr(record, "factor_month_awaited", "") or "")


def open_claims(events: Iterable[Any]) -> list[Any]:
    """The book's factor revisions whose difference is still owed (992): each
    `LIFECYCLE_EVENT_KIND_FACTOR_REVISION` in
    `LIFECYCLE_EVENT_STATE_CLAIM_OPEN`, until a person marks it settled
    (`lifecycle.settle_claim`)."""
    return [
        e
        for e in events
        if e.kind == ops.LIFECYCLE_EVENT_KIND_FACTOR_REVISION
        and e.state == ops.LIFECYCLE_EVENT_STATE_CLAIM_OPEN
    ]
