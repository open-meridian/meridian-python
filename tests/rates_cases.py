"""The data suite's rates cases (contract v27; ruling 345) as a plugin built
on `meridian.roles.data.rates` does them: each its own conversion of a
publisher's answer, through the SDK's `rates.Feed`, the subjects the
deployment's referential records. Imported by the tests that run the data
suite."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import meridian
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles.data import rates
from meridian.roles.data.testing import Instruments

DAY = "2026-10-20"
PUBLISHED = 1792540800000000000
SOFR = ("symbol", "SOFR", "nyfed")
PAR = ("symbol", "PAR_NOMINAL", "ust")
BILLS = ("symbol", "BILLS", "ust")
SOFR_INDEX = ("symbol", "SOFRINDEX", "nyfed")


def _referential(store: Instruments, instrument_id: str, *named: tuple[str, str, str]) -> str:
    return store.hold(
        instrument_id,
        *(ops.Identifier(scheme=s, value=v, source=o) for s, v, o in named),
        asset_class=ops.ASSET_CLASS_REFERENTIAL,
    )


async def _fixing(feed: rates.Feed, store: Instruments) -> None:
    _referential(store, "INS-SOFR", SOFR)
    subject = await feed.subject(SOFR, instrument_type="interest_rate")
    row = feed.rate(
        subject, "nyfed_rates", "fixing", "4.31", business_date=DAY, published_ns=PUBLISHED,
        convention=rates.MONEY_MARKET, volume=meridian.Money(Decimal("2512000000000"), "USD"),
        transaction_count=None, percentiles={1: "4.28", 25: "4.29", 75: "4.33", 99: "4.40"},
        series="SOFR", raw_key="nyfed/sofr/2026-10-20",
    )  # fmt: skip
    await feed.record("nyfed_rates", [row])


async def _revised(feed: rates.Feed, store: Instruments) -> None:
    _referential(store, "INS-SOFR", SOFR)
    subject = await feed.subject(SOFR)
    for value, at in (("4.31", PUBLISHED), ("4.32", PUBLISHED + 6 * 3600 * 10**9)):
        row = feed.rate(subject, "nyfed_rates", "fixing", value, business_date=DAY,
                        published_ns=at, convention=rates.MONEY_MARKET, series="SOFR",
                        raw_key=f"nyfed/sofr/{at}")  # fmt: skip
        await feed.record("nyfed_rates", [row])


def _curve(points: dict[str, str | None]) -> Any:
    async def case(feed: rates.Feed, store: Instruments) -> None:
        _referential(store, "INS-PAR", PAR)
        subject = await feed.subject(PAR, instrument_type="rate_curve")
        rows = feed.curve(subject, "ust_par", "par_yield", points, business_date=DAY,
                          published_ns=PUBLISHED, convention=rates.BOND_EQUIVALENT,
                          series="PAR", raw_key="ust/par/2026-10-20")  # fmt: skip
        await feed.record("ust_par", rows)

    return case


async def _bills(feed: rates.Feed, store: Instruments) -> None:
    _referential(store, "INS-BILLS", BILLS)
    subject = await feed.subject(BILLS)
    rows = [
        feed.rate(subject, "ust_bills", "discount", "4.05", tenor="13 WEEKS", business_date=DAY,
                  convention=rates.DISCOUNT, series="BILLS"),
        feed.rate(subject, "ust_bills", "coupon_equivalent", "4.15", tenor="13 WEEKS",
                  business_date=DAY, convention=rates.RateConvention(
                      day_count="act_365_fixed", compounding="simple"), series="BILLS"),
    ]  # fmt: skip
    await feed.record("ust_bills", rows)


async def _index(feed: rates.Feed, store: Instruments) -> None:
    _referential(store, "INS-SOFRINDEX", SOFR_INDEX)
    subject = await feed.subject(SOFR_INDEX, instrument_type="index")
    row = feed.rate(subject, "nyfed_rates", "index_level",
                    rates.index_level("1.18752336", base="2018-04-02=1.00000000"),
                    business_date=DAY, series="SOFRINDEX")  # fmt: skip
    await feed.record("nyfed_rates", [row])


async def _another_sources_point(feed: rates.Feed, store: Instruments) -> None:
    # FRED's DGS10 is Treasury's 10-year par yield: recorded against the
    # curve's record, with its tenor.
    _referential(store, "INS-PAR", PAR, ("symbol", "DGS10", "fred"))
    subject = await feed.subject(("symbol", "DGS10", "fred"))
    row = feed.rate(subject, "fred_public", "par_yield", "4.21", tenor="10Y", business_date=DAY,
                    series="DGS10")  # fmt: skip
    await feed.record("fred_public", [row])


RATES = {
    "a-rate-fixing": _fixing,
    "a-same-day-revision": _revised,
    "a-curve-for-a-date": _curve({"1 Mo": "4.12", "6 Wk": "4.11", "10 Yr": "4.21"}),
    "a-tenor-not-published": _curve({"1 Mo": "4.12", "2 Mo": None, "10 Yr": "4.21"}),
    "two-conventions-one-tenor": _bills,
    "an-index-level": _index,
    "a-curve-point-from-another-source": _another_sources_point,
}
