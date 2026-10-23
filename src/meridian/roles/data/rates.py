"""The lake's rates slice, for a data plugin and its readers (0.32.0;
contract v27, sdk-contract/the-lake-holds-researchs-kinds; ruling 345:
the shared rates and curve conversion is the SDK's, each publisher's client
staying in its own plugin; spec/a-public-rates-and-filings-data-plugin,
items 1 to 5).

A **rate** is a fixing, an average, an index level or a curve's point, for
one subject -- a referential `INS-` record: a reference rate (SOFR, €STR),
a rate curve (Treasury's par curve, the Board's zero curve) or an index
(the SOFR Index). A curve is one record and its points are rows, each with
its tenor; a bill's discount rate and its coupon-equivalent yield for one
tenor are two rows, told apart by kind and convention. A value is a
`UnitValue` -- 3.87 per cent is 3.87 `percent`, never a Money -- and what
the source does not publish is no row, never a zero.

    from meridian.roles.data import rates

    feed = rates.Feed(plugin, "ust", wants=wants)
    curve = await feed.subject(("symbol", "PAR_NOMINAL", "ust"))   # the curve's record
    rows = feed.curve(curve, "ust_par", "par_yield",
                      {"1 Mo": "4.12", "3 Mo": "4.09", "10 Yr": "4.21", "20 Yr": None},
                      business_date=day, published_ns=at, convention=rates.BOND_EQUIVALENT,
                      raw_key=raw)
    await feed.record("ust_par", rows)

**Row keys**: a rate's row key names its series, kind, tenor or maturity,
convention and business date, and the record it is about (`@INS-...`), never
its published time, so a same-day revision -- a later published time, a new
value, a preliminary fixing made final -- is the next version of the same
row key, and an identical repeat is answered unchanged.

**Subjects** (`Feed.subject`): resolved by the identifiers the publisher
states (a FIGI, an ISIN, the administrator's code as a `symbol` at its
source), once per process; a record not held is reported as a miss
(W3.2), once a day, and its rows not recorded -- a plugin never mints. A
single-point series that is another source's curve point (FRED's DGS10,
Treasury's 10-year) is recorded against the curve's record with its tenor
(`Feed.rate(..., tenor="10Y")`), so both sit under the deployment's source
priority.

**Reading** (`read_curve`): a curve's points for a business date, every
page read, in tenor order.

**The data suite** (0.32.1; ruling 537): a plugin recording rates and no
prices maps the rates cases (`data.testing.rates_producers`) and the cases
every data plugin answers, and names the rest not presented with why --
`data.testing.RATES_NOT_PRESENTED`, among them `an-exact-price` and
`a-want-recorded-against`, about `closes`: "it records rates, never
prices". From 0.32.2 a plugin recording each poll as its dataset's
liveness (`Wants.liveness`, or `record_liveness` where it keeps no
`Wants`) presents `records-a-datasets-liveness`, which the list no longer
names; one recording none adds it, with why.

**Tenors** (`tenor`, `tenor_label`): a publisher's label -- `1 Mo`, `13
WEEKS`, `10 Yr`, `3M`, `ON` -- as the wire's `Tenor`, a count and a unit; a
fractional tenor is refused, for the plugin to name its maturity instead.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
import re
import time
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from ...bounds import OBSERVATION_META_ROW_KEY_LENGTH
from ...operations import (
    Money,
    ObservationMeta,
    Rate,
    RateConvention,
    RatePercentile,
    SourceTime,
    Tenor,
    UnitValue,
)
from ...plugin.v1 import operations_pb2 as ops

__all__ = [
    "BOND_EQUIVALENT",
    "CONTINUOUS",
    "DISCOUNT",
    "MONEY_MARKET",
    "Feed",
    "index_level",
    "percent",
    "read_curve",
    "tenor",
    "tenor_days",
    "tenor_label",
]

log = logging.getLogger("meridian.roles.data.rates")

#: The conventions the US and euro publishers state: a money-market rate
#: (SOFR, EFFR, €STR: actual/360, simple), a bond-equivalent par yield
#: (semi-annual compounding), a bill's bank discount (actual/360) and a
#: continuously compounded zero rate.
MONEY_MARKET = RateConvention(day_count="act_360", compounding="simple")
BOND_EQUIVALENT = RateConvention(
    day_count="act_act", compounding="compounded", periods_per_year=2
)
DISCOUNT = RateConvention(day_count="act_360", compounding="discount")
CONTINUOUS = RateConvention(day_count="act_365_fixed", compounding="continuous")

_UNITS = {
    "d": "day", "day": "day", "days": "day",
    "w": "week", "wk": "week", "wks": "week", "week": "week", "weeks": "week",
    "m": "month", "mo": "month", "mos": "month", "mth": "month", "month": "month",
    "months": "month",
    "y": "year", "yr": "year", "yrs": "year", "year": "year", "years": "year",
}  # fmt: skip
_SHORT = {
    "on": "overnight", "o/n": "overnight", "overnight": "overnight",
    "tn": "tom_next", "t/n": "tom_next", "sn": "spot_next", "s/n": "spot_next",
}  # fmt: skip
_LABEL: dict[int, str] = {
    ops.TENOR_UNIT_DAY: "D",
    ops.TENOR_UNIT_WEEK: "W",
    ops.TENOR_UNIT_MONTH: "M",
    ops.TENOR_UNIT_YEAR: "Y",
}
_SHORT_LABEL: dict[int, str] = {
    ops.TENOR_UNIT_OVERNIGHT: "ON",
    ops.TENOR_UNIT_TOM_NEXT: "TN",
    ops.TENOR_UNIT_SPOT_NEXT: "SN",
}
_DAYS: dict[int, int | Decimal] = {
    ops.TENOR_UNIT_DAY: 1,
    ops.TENOR_UNIT_WEEK: 7,
    ops.TENOR_UNIT_MONTH: Decimal("30.4375"),
    ops.TENOR_UNIT_YEAR: Decimal("365.25"),
    ops.TENOR_UNIT_OVERNIGHT: 1,
    ops.TENOR_UNIT_TOM_NEXT: 2,
    ops.TENOR_UNIT_SPOT_NEXT: 3,
}


def tenor(label: str | Tenor) -> Tenor:
    """A publisher's tenor label as the wire's `Tenor`: `1 Mo`, `13 WEEKS`,
    `10 Yr`, `3M`, `1W`, `ON`, `TN`, `SN`. A fraction (`1.5 Month`) or a
    label it cannot read is refused naming it."""
    if isinstance(label, Tenor):
        return label
    text = str(label).strip().lower()
    if text in _SHORT:
        return Tenor(count=1, unit=_SHORT[text])
    found = re.fullmatch(r"(\d+(?:\.\d+)?)[\s-]*([a-z/]+)", text)
    if found is None or found.group(2) not in _UNITS:
        raise ValueError(f"{label!r} is not a tenor this SDK reads; name its maturity instead")
    count = Decimal(found.group(1))
    if count != count.to_integral_value() or count < 1:
        raise ValueError(
            f"{label!r} is not a whole number of its unit; name its maturity instead"
        )
    return Tenor(count=int(count), unit=_UNITS[found.group(2)])


_tenor_of = tenor


def _unit(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value or "")
    name = (
        text.upper() if text.upper().startswith("TENOR_UNIT_") else f"TENOR_UNIT_{text.upper()}"
    )
    return int(ops.TenorUnit.Value(name)) if name in ops.TenorUnit.keys() else 0  # noqa: SIM118


def tenor_label(held: Tenor | ops.Tenor) -> str:
    """A tenor's one label: `3M`, `10Y`, `ON`."""
    unit = _unit(held.unit)
    if unit in _SHORT_LABEL:
        return _SHORT_LABEL[unit]
    return f"{held.count}{_LABEL.get(unit, '?')}"


def tenor_days(held: Tenor | ops.Tenor) -> Decimal:
    """A tenor's length in days, approximately, to order a curve's points:
    a month 30.4375 days, a year 365.25."""
    return Decimal(held.count) * Decimal(_DAYS.get(_unit(held.unit), 0))


def percent(value: Decimal | str | int) -> UnitValue:
    """A rate in per cent, as the publisher states it: `3.87` is 3.87%."""
    return UnitValue(value=_number(value), unit="percent")


def index_level(value: Decimal | str | int, base: str = "") -> UnitValue:
    """An index's level, with its base period as the publisher states it
    (`2018-04-02=1.00000000`)."""
    return UnitValue(value=_number(value), unit="index", index_base=base)


def _number(value: Decimal | str | int) -> Decimal | int:
    if isinstance(value, float):
        raise TypeError("a rate is read from the publisher's text, never a float")
    return value if isinstance(value, int) else Decimal(str(value))


def _convention_label(convention: RateConvention | None) -> str:
    if convention is None:
        return "-"
    periods = f"/{convention.periods_per_year}" if convention.periods_per_year else ""
    return f"{convention.day_count or '-'}:{convention.compounding or '-'}{periods}"


def _row_key(said: str, day: str, subject: str) -> str:
    """A rate's row key: what the source said of it, its business date and
    its record (`@INS-...`), within the contract's 128 characters
    (OBSERVATION_META_ROW_KEY_LENGTH): where the words run past, they are
    named by their SHA-256 instead, so the key stays the same for every
    version and never collides by truncation."""
    key = f"{said}:{day}@{subject}"
    if OBSERVATION_META_ROW_KEY_LENGTH.admits(len(key)):
        return key
    digest = hashlib.sha256(said.encode()).hexdigest()[:32]
    key = f"{digest}:{day}@{subject}"
    if not OBSERVATION_META_ROW_KEY_LENGTH.admits(len(key)):
        raise ValueError(
            f"a rate's row key for {subject!r} runs past "
            f"{OBSERVATION_META_ROW_KEY_LENGTH.most} characters"
        )
    return key


class Feed:
    """A data plugin's rates (see the module): its subjects resolved, its
    rows built under one row-key scheme, and recorded through its `Wants`
    where it keeps one (counted, its edge age recorded), else directly."""

    def __init__(
        self,
        plugin: Any,
        source_name: str,
        *,
        wants: Any = None,
        day_zone: str = "UTC",
        clock_ns: Any = time.time_ns,
    ) -> None:
        self.plugin = plugin
        self.source_name = source_name
        self.wants = wants
        self.zone = ZoneInfo(day_zone)
        self.clock_ns = clock_ns
        self.subjects: dict[tuple[tuple[str, str, str], ...], str] = {}
        self.missed: dict[tuple[tuple[str, str, str], ...], str] = {}

    def dataset(self, key: str) -> str:
        return f"{self.plugin.identity.instance_id}:{key}"

    async def subject(
        self,
        *identifiers: tuple[str, str, str] | tuple[str, str],
        description: str = "",
        instrument_type: str = "",
    ) -> str:
        """The referential record the identifiers name (scheme, value and,
        for a source-scoped code, its source) -- an `interest_rate`, a
        `rate_curve` or an `index`, as `instrument_type` states it -- once
        per process; empty, and reported as a miss once a day, where the
        deployment holds none."""
        named = tuple(
            (each[0], each[1], each[2] if len(each) > 2 else "") for each in identifiers
        )
        held = self.subjects.get(named)
        if held:
            return held
        today = (
            dt.datetime.fromtimestamp(self.clock_ns() / 1e9, tz=self.zone).date().isoformat()
        )
        if self.missed.get(named) == today:
            return ""
        asked = [ops.Identifier(scheme=s, value=v, source=o) for s, v, o in named]
        found = await self.plugin.resolve_identifier(
            identifiers=asked,
            as_of_ns=self.clock_ns(),
            stated_asset_class="referential",
            stated_description=description,
            stated_instrument_type=instrument_type or None,
        )
        if found.found and found.instrument_id:
            self.subjects[named] = found.instrument_id
            return str(found.instrument_id)
        self.missed[named] = today
        await self.plugin.report_missing_instrument(
            source=self.source_name,
            identifiers=asked,
            as_of_ns=self.clock_ns(),
            reason=found.miss_reason or ops.MISS_REASON_NOT_FOUND,
        )
        log.info("a rate's record is not held: %s", named)
        return ""

    def rate(
        self,
        subject: str,
        key: str,
        kind: str,
        value: UnitValue | Decimal | str | int,
        *,
        business_date: dt.date | str,
        published_ns: int = 0,
        convention: RateConvention | None = None,
        tenor: str | Tenor | None = None,
        maturity_date: dt.date | str = "",
        preliminary: bool = False,
        volume: Money | None = None,
        transaction_count: int | None = None,
        percentiles: Mapping[int, Decimal | str] | None = None,
        series: str = "",
        raw_key: str = "",
    ) -> Rate:
        """One rate for `subject` under the dataset `key`: its kind (`fixing`,
        `average`, `index_level`, `par_yield`, `zero`, `discount`,
        `coupon_equivalent`), its value (a bare number is a percent), its
        business date and, where the publisher states them, its published
        time, convention, tenor or maturity, whether it is preliminary, its
        volume, transaction count and percentiles."""
        day = business_date if isinstance(business_date, str) else business_date.isoformat()
        held_tenor = None if tenor is None else _tenor_of(tenor)
        maturity = (
            maturity_date if isinstance(maturity_date, str) else maturity_date.isoformat()
        )
        point = tenor_label(held_tenor) if held_tenor is not None else (maturity or "-")
        row_key = _row_key(
            f"{series or self.source_name}:{kind}:{point}:{_convention_label(convention)}",
            day,
            subject,
        )
        start = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(), self.zone)
        valid_from = int(start.timestamp() * 1e9)
        valid_until = int((start + dt.timedelta(days=1)).timestamp() * 1e9)
        return Rate(
            meta=ObservationMeta(
                row_key=row_key,
                subjects=[ops.SubjectRef(entity_id=subject)],
                source=ops.Source(dataset=self.dataset(key)),
                valid_from_ns=valid_from,
                valid_until_ns=valid_until,
                business_date=day,
                source_times=(
                    [SourceTime(kind="published", at_ns=published_ns)] if published_ns else []
                ),
                raw=self.plugin.raw_record(raw_key[:256]) if raw_key else None,
            ),
            kind=kind,
            value=value if isinstance(value, UnitValue) else percent(value),
            convention=convention,
            tenor=held_tenor,
            maturity_date=maturity,
            preliminary=preliminary,
            volume=volume,
            transaction_count=transaction_count,
            percentiles=[
                RatePercentile(percentile=int(p), value=_number(v))
                for p, v in sorted((percentiles or {}).items())
            ],
        )

    def curve(
        self,
        subject: str,
        key: str,
        kind: str,
        points: Mapping[str | Tenor, UnitValue | Decimal | str | None],
        **given: Any,
    ) -> list[Rate]:
        """A curve's points for one date, one row per tenor the publisher
        published; a tenor it left empty (None or "") is no row, never a
        zero. `given` is `rate`'s."""
        return [
            self.rate(subject, key, kind, value, tenor=label, **given)
            for label, value in points.items()
            if value is not None and value != ""
        ]

    async def record(self, key: str, rows: Sequence[Rate], want_id: str = "") -> int:
        """Send `rows` in the lake's batches of 500, against a want where
        they answer one; how many were sent."""
        if self.wants is not None:
            return int(await self.wants.record("rates", rows, key, want_id))
        sent = 0
        for start in range(0, len(rows), 500):
            batch = list(rows[start : start + 500])
            await self.plugin.record_rates(rates=batch, want_id=want_id)
            sent += len(batch)
        return sent


async def read_curve(
    plugin: Any,
    subject: str,
    business_date: dt.date | str,
    *,
    kinds: Iterable[str] = (),
    tenors: Iterable[str | Tenor] = (),
    sources: ops.SourceChoice | None = None,
) -> list[ops.Rate]:
    """A curve's points for a business date (W10.6): every page of
    `list_rates` for `subject`, from the deployment's default sources
    unless `sources` names others, in tenor order (a point with an exact
    maturity after the tenors, by date)."""
    out: list[ops.Rate] = []
    cursor = ""
    while True:
        page = await plugin.list_rates(
            subjects=[ops.SubjectRef(entity_id=subject)],
            kinds=list(kinds),
            tenors=[tenor(t) for t in tenors],
            sources=sources,
            business_date=business_date,
            cursor=cursor,
        )
        out.extend(page.rates)
        cursor = page.next_cursor
        if not cursor:
            break

    def order(rate: ops.Rate) -> tuple[int, Decimal, str]:
        if rate.HasField("tenor") and rate.tenor.unit:
            return (0, tenor_days(rate.tenor), "")
        return (1, Decimal(0), rate.maturity_date)

    return sorted(out, key=order)
