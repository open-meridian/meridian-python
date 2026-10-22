"""Write the analytics reference cases (tests/reference_cases/*.json):
each a job and every input it reads, with the reference computations'
answer and hash (meridian.analytics.reference; requirement 36).

    python3 tools/write_reference_cases.py          # from the repository root

The cases are pinned: `tests/test_v26.py` holds every file to its own
canonical form and to the answer the reference computes now, so a change
to a reference computation shows as a changed file in review. Run this
only for a deliberate change, and read the diff. v26's analytics engine
answers the same cases with the same figures and hashes (core's identity
test reads these files at the SDK's pinned commit).
"""

from __future__ import annotations

import sys
import types
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# The reference computations need nothing but the standard library: loaded
# alone, without the package's gRPC bindings, so this runs on any Python.
for name, path in (("meridian", "src/meridian"), ("meridian.analytics", "src/meridian/analytics")):
    module = types.ModuleType(name)
    module.__path__ = [str(ROOT / path)]
    sys.modules[name] = module

from meridian.analytics import reference  # noqa: E402
from meridian.analytics._canonical import canonical  # noqa: E402

OUT = ROOT / "tests" / "reference_cases"
ENGINE = "0.1.0"
AS_OF = "1792300000000000000"
FRESH = "1792299990000000000"
OLD = "1792000000000000000"
WATERMARK = [{"partition": "P0", "sequence": "81234"}]

USD = "INS-01J8XQ4M7K00000000CASHUSD"
EUR = "INS-01J8XQ4M7K00000000CASHEUR"
CHF = "INS-01J8XQ4M7K00000000CASHCHF"
NESN = "INS-01J8XQ4M7K0000000000NESN"
SAP = "INS-01J8XQ4M7K00000000000SAP"
USDT = "INS-01J8XQ4M7K0000000000USDT"
USDC = "INS-01J8XQ4M7K0000000000USDC"
AAPL = "INS-01J8XQ4M7K0000000000AAPL"
SPY = "INS-01J8XQ4M7K00000000000SPY"
VFIAX = "INS-01J8XQ4M7K000000000VFIAX"
SPAXX = "INS-01J8XQ4M7K000000000SPAXX"
BTC = "INS-01J8XQ4M7K00000000000BTC"
LOCAL = "LCL-01J8XQ4M7K0000000000ZZTP"
K89, K91, K93 = (f"INS-01JAG0K000000000KXHIGHT{n}" for n in (89, 91, 93))
PM_YES, PM_NO = "INS-01JAG0P0000000000PMYES01", "INS-01JAG0P00000000000PMNO01"
GROUP = "EVG-01JAG0K0000000000000000001"
OPEN_GROUP = "EVG-01JAG0K0000000000000000002"


def instrument(
    instrument_id: str,
    model: str,
    asset_class: str,
    currency: str,
    kind: str = "",
    template: str = "",
    payout: tuple[str, str] | None = None,
    country: str = "",
    code: str = "",
) -> dict[str, Any]:
    return {
        "instrument_id": instrument_id,
        "record_version": "3",
        "template_id": template or f"TPL-{asset_class}",
        "template_version": "2",
        "calculation_version": "1",
        "model_id": model,
        "model_version": 1,
        "asset_class": asset_class,
        "currency_instrument_id": currency,
        "price_kind": kind,
        "payout": None if payout is None else {"amount": payout[0], "instrument_id": payout[1]},
        "country": country,
        "currency_code": code,
    }


def price(
    subject: str, kind: str, amount: str, currency: str, dataset: str, at: str = FRESH
) -> dict[str, Any]:
    """A lake price at the as-of, with the row it came from (contract v27,
    ruling 460): its row key, version and source time."""
    return {
        "subject_id": subject,
        "kind": kind,
        "amount": amount,
        "instrument_id": currency,
        "dataset": dataset,
        "valid_at_ns": at,
        "row_key": f"{dataset}/{subject}/{kind}",
        "version": "1",
        "source_ns": at,
    }


def position(
    account: str, instrument_id: str, quantity: str, cost: str = "", sleeve: str = ""
) -> dict[str, Any]:
    return {
        "account_id": account,
        "instrument_id": instrument_id,
        "quantity": quantity,
        "cost": cost,
        "sleeve": sleeve,
    }


def measure(
    definition: str, by: tuple[str, ...] = (), group: str = "", version: int = 1
) -> dict[str, Any]:
    return {
        "definition": definition,
        "version": version,
        "breakdowns": list(by),
        "event_group_id": group,
    }


def inputs(**given: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "engine_version": ENGINE,
        "job": {"account_ids": [], "measures": [], "what_if": None},
        "book_watermark": WATERMARK,
        "lake_as_of_ns": AS_OF,
        "routing_version": "1",
        "accounts": [],
        "positions": [],
        "instruments": [],
        "market": [],
        "history": {"dates": [], "closes": []},
        "outcomes": [],
        "event_groups": [],
        "stale_after_ns": {},
        # Contract v27 (rulings 462 and 483): the deployment's pivot order,
        # USD's then EUR's by default.
        "fx_pivot_currencies": [USD, EUR],
    }
    base.update(given)
    return base


CASH = instrument(USD, "cash", "cash", USD, template="TPL-cash", code="USD")
CASH_EUR = instrument(EUR, "cash", "cash", EUR, template="TPL-cash", code="EUR")
CASH_CHF = instrument(CHF, "cash", "cash", CHF, template="TPL-cash", code="CHF")
CASH_USDT = instrument(USDT, "cash", "cash", USDT, template="TPL-cash")
CASH_USDC = instrument(USDC, "cash", "cash", USDC, template="TPL-cash")


def valuation() -> dict[str, Any]:
    """v26's universe valued at the as-of: cash in the base and another
    currency, an equity, an ETF at its close, a mutual fund at its NAV, a
    money-market fund whose NAV is missing, a crypto asset quoted in a
    stablecoin, a local record, a stale price; net and gross, broken down,
    concentration and Unrealized P&L (pnl version 1, the open lots' cost),
    across two accounts with different bases."""
    return inputs(
        job={
            "account_ids": ["ACC-1", "ACC-2"],
            "measures": [
                measure("market_value"),
                measure("market_value", ("asset_class", "currency")),
                measure("exposure", ("instrument",)),
                measure("concentration", ("instrument",)),
                measure("pnl", ("sleeve",)),
            ],
            "what_if": None,
        },
        accounts=[
            {"account_id": "ACC-1", "base_currency_instrument_id": USD},
            {"account_id": "ACC-2", "base_currency_instrument_id": EUR},
        ],
        positions=[
            position("ACC-1", USD, "10500.25", "10500.25", "core"),
            position("ACC-1", EUR, "2000.00", "2150.00", "core"),
            position("ACC-1", AAPL, "10", "2000.00", "core"),
            position("ACC-1", SPY, "-3", "-1700.10", "hedge"),
            position("ACC-1", VFIAX, "12.345", "6500.00", "core"),
            position("ACC-1", SPAXX, "1000", "1000.00", "core"),
            position("ACC-1", BTC, "0.12345678", "7000.00", "satellite"),
            position("ACC-1", LOCAL, "100", "250.00", "core"),
            position("ACC-2", EUR, "5000", "5000", "core"),
            position("ACC-2", AAPL, "4", "800.00", "core"),
            position("ACC-2", USD, "100.00", "92.00", "core"),
        ],
        instruments=[
            CASH,
            CASH_EUR,
            CASH_USDT,
            instrument(AAPL, "quoted_price", "equity", USD, "close", country="US"),
            instrument(SPY, "quoted_price", "etf", USD, "close", country="US"),
            instrument(VFIAX, "quoted_price", "mutual_fund", USD, "nav", country="US"),
            instrument(SPAXX, "quoted_price", "money_market_fund", USD, "nav", country="US"),
            instrument(BTC, "quoted_price", "crypto_asset", USDT, "close"),
        ],
        market=[
            price(AAPL, "close", "227.50", USD, "alpaca-1:daily"),
            price(SPY, "close", "571.47", USD, "alpaca-1:daily"),
            price(VFIAX, "nav", "531.18", USD, "tiingo-1:funds"),
            price(BTC, "close", "60000.50", USDT, "coinbase-1:daily"),
            price(USDT, "close", "0.9998", USD, "coinbase-1:daily"),
            price(EUR, "close", "1.0850", USD, "fed-h10-1:rates"),
            price(USD, "close", "0.9217", EUR, "fed-h10-1:rates"),
            # A stale close of the ETF from another source, never preferred:
            # the lake read answers one row per subject and kind.
        ],
        stale_after_ns={"tiingo-1:funds": "86400000000000"},
    )


def realized_v2() -> dict[str, Any]:
    """`pnl` version 2 (served from contract v27; rulings 320 and 396):
    the valuation's accounts, each bucket's unrealized P&L from its open
    lots beside its realized P&L from the lots the book closed up to its
    watermark, since the account opened."""
    given = valuation()
    given["job"] = {
        "account_ids": ["ACC-1", "ACC-2"],
        "measures": [measure("pnl", ("sleeve",), version=2)],
        "what_if": None,
    }
    given["closed_lots"] = [
        {"account_id": "ACC-1", "instrument_id": AAPL, "quantity": "5", "proceeds": "1100.00",
         "cost": "1000.00", "sleeve": "core"},
        {"account_id": "ACC-1", "instrument_id": SPY, "quantity": "-2", "proceeds": "-1150.40",
         "cost": "-1120.00", "sleeve": "hedge"},
        {"account_id": "ACC-2", "instrument_id": AAPL, "quantity": "1", "proceeds": "195.10",
         "cost": "200.00", "sleeve": "core"},
        # A lot whose cost the book does not record (an opening balance
        # stated without one): not evaluated, never zero (ruling 325).
        {"account_id": "ACC-2", "instrument_id": AAPL, "quantity": "2", "proceeds": "390.00",
         "cost": "", "sleeve": "core"},
    ]  # fmt: skip
    return given


def stale() -> dict[str, Any]:
    """A price older than the client's setting for its source allows: not
    evaluated, never zero; and a conversion with no leg to the base."""
    return inputs(
        job={"account_ids": ["ACC-1"], "measures": [measure("market_value")], "what_if": None},
        accounts=[{"account_id": "ACC-1", "base_currency_instrument_id": USD}],
        positions=[
            position("ACC-1", VFIAX, "10", "5000.00"),
            position("ACC-1", BTC, "1", "60000.00"),
            position("ACC-1", AAPL, "1", "200.00"),
        ],
        instruments=[
            CASH,
            instrument(AAPL, "quoted_price", "equity", USD, "close", country="US"),
            instrument(VFIAX, "quoted_price", "mutual_fund", USD, "nav", country="US"),
            instrument(BTC, "quoted_price", "crypto_asset", USDT, "close"),
        ],
        market=[
            price(AAPL, "close", "227.50", USD, "alpaca-1:daily"),
            price(VFIAX, "nav", "531.18", USD, "tiingo-1:funds", at=OLD),
            price(BTC, "close", "60000.50", USDT, "coinbase-1:daily"),
        ],
        stale_after_ns={"tiingo-1:funds": "86400000000000"},
    )


def kalshi_group(exhaustive: str, group: str) -> dict[str, Any]:
    return {
        "event_group_id": group,
        "version": "2",
        "member_instrument_ids": [K89, K91, K93],
        "mutually_exclusive": "EVENT_GROUP_FLAG_TRUE",
        "exhaustive": exhaustive,
    }


def kalshi_instruments() -> list[dict[str, Any]]:
    return [
        CASH,
        *(
            instrument(k, "binary_event", "event_contract", USD, "last", payout=("1.00", USD))
            for k in (K89, K91, K93)
        ),
    ]


def kalshi_market() -> list[dict[str, Any]]:
    out = []
    for subject, bid, ask, last in (
        (K89, "0.41", "0.43", "0.42"),
        (K91, "0.30", "0.36", "0.33"),
        (K93, "0.18", "0.40", "0.30"),
    ):
        out += [
            price(subject, "bid", bid, USD, "kalshi-1:quotes"),
            price(subject, "ask", ask, USD, "kalshi-1:quotes"),
            price(subject, "last", last, USD, "kalshi-1:live"),
        ]
    return out


def event_group() -> dict[str, Any]:
    """An exhaustive group (fixtures/analytics/read-job-answer.yaml's): each
    outcome's mid over the sum, the wide one at its last trade; each
    account's payoff if each member resolves YES; the contracts marked at
    their prices."""
    return inputs(
        job={
            "account_ids": ["ACC-1"],
            "measures": [
                measure("implied_distribution", group=GROUP),
                measure("resolution_payoff", group=GROUP),
                measure("market_value", ("instrument",)),
            ],
            "what_if": None,
        },
        accounts=[{"account_id": "ACC-1", "base_currency_instrument_id": USD}],
        positions=[
            position("ACC-1", K89, "100", "42.00"),
            position("ACC-1", K91, "-50", "-17.50"),
        ],
        instruments=kalshi_instruments(),
        market=kalshi_market(),
        event_groups=[kalshi_group("EVENT_GROUP_FLAG_TRUE", GROUP)],
    )


def open_group() -> dict[str, Any]:
    """A group mutually exclusive and not stated exhaustive (a Polymarket
    augmented event): the distribution not evaluated, its raw prices and
    their sum answered; the payoff under none of the named beside each
    member's."""
    return inputs(
        job={
            "account_ids": ["ACC-1"],
            "measures": [
                measure("implied_distribution", group=OPEN_GROUP),
                measure("resolution_payoff", group=OPEN_GROUP),
            ],
            "what_if": None,
        },
        accounts=[{"account_id": "ACC-1", "base_currency_instrument_id": USD}],
        positions=[position("ACC-1", K89, "100", "42.00"), position("ACC-1", K93, "20", "6.40")],
        instruments=kalshi_instruments(),
        market=kalshi_market(),
        event_groups=[kalshi_group("EVENT_GROUP_FLAG_NOT_STATED", OPEN_GROUP)],
    )


def resolved() -> dict[str, Any]:
    """A Polymarket market in USDC resolved 50/50 and final: marked at the
    settlement value per contract, converted leg by leg to the base; its NO
    token not yet final, at its price; the stablecoin never at par."""
    return inputs(
        job={"account_ids": ["ACC-1"], "measures": [measure("market_value", ("instrument",))],
             "what_if": None},
        accounts=[{"account_id": "ACC-1", "base_currency_instrument_id": USD}],
        positions=[
            position("ACC-1", PM_YES, "250", "120.00"),
            position("ACC-1", PM_NO, "100", "45.00"),
            position("ACC-1", USDC, "1000", "1000.00"),
        ],
        instruments=[
            CASH,
            CASH_USDC,
            instrument(PM_YES, "binary_event", "event_contract", USDC, "last",
                       payout=("1.00", USDC)),
            instrument(PM_NO, "binary_event", "event_contract", USDC, "last",
                       payout=("1.00", USDC)),
        ],
        market=[
            price(PM_YES, "last", "0.97", USDC, "polymarket-1:live"),
            price(PM_NO, "last", "0.48", USDC, "polymarket-1:live"),
            price(USDC, "close", "0.9999", USD, "coinbase-1:daily"),
        ],
        outcomes=[
            {"instrument_id": PM_YES, "final": True, "settlement_value": "0.50",
             "dataset": "polymarket-1:outcomes"},
            {"instrument_id": PM_NO, "final": False, "settlement_value": "0.50",
             "dataset": "polymarket-1:outcomes"},
        ],
    )  # fmt: skip


def _weekdays(last: date, count: int) -> list[date]:
    out: list[date] = []
    day = last
    while len(out) < count:
        if day.weekday() < 5:
            out.append(day)
        day -= timedelta(days=1)
    return out[::-1]


def _walk(start: str, seed: int, days: int, places: str) -> list[Decimal]:
    """A deterministic close series: each day's return a whole number of
    basis points from a linear congruential generator, the close rounded
    half to even."""
    out = [Decimal(start)]
    state = seed
    for _ in range(days - 1):
        state = (state * 1103515245 + 12345) % 2**31
        bps = (state % 401) - 200  # -2.00% to +2.00%
        out.append((out[-1] * (1 + Decimal(bps) / 10000)).quantize(Decimal(places), ROUND_HALF_EVEN))
    return out


def historical() -> dict[str, Any]:
    """Historical VaR and ES over 500 days by full revaluation: an equity in
    USD and a euro balance, each shocked by its own relative returns, the
    euro's rate too; two closes missing and carried forward, one instrument
    missing six running and so not evaluated; an event contract left out,
    its resolution worst case beside the figure."""
    dates = _weekdays(date(2026, 10, 16), 501)
    aapl = _walk("150.00", 7, 501, "0.01")
    eur = _walk("1.0500", 11, 501, "0.0001")
    spy = _walk("400.00", 13, 501, "0.01")
    closes: list[dict[str, Any]] = []
    for i, day in enumerate(dates):
        iso = day.isoformat()
        if i not in (100, 101):  # two days missing, carried forward
            closes.append({"subject_id": AAPL, "amount": str(aapl[i]), "instrument_id": USD,
                           "business_date": iso})  # fmt: skip
        closes.append({"subject_id": EUR, "amount": str(eur[i]), "instrument_id": USD,
                       "business_date": iso})  # fmt: skip
        if not 200 <= i < 206:  # six running missing: past the five carried
            closes.append({"subject_id": SPY, "amount": str(spy[i]), "instrument_id": USD,
                           "business_date": iso})  # fmt: skip
    return inputs(
        job={
            "account_ids": ["ACC-1"],
            "measures": [measure("historical_var"), measure("expected_shortfall")],
            "what_if": None,
        },
        accounts=[{"account_id": "ACC-1", "base_currency_instrument_id": USD}],
        positions=[
            position("ACC-1", USD, "5000.00", "5000.00"),
            position("ACC-1", AAPL, "100", "15000.00"),
            position("ACC-1", EUR, "20000", "21000.00"),
            position("ACC-1", SPY, "10", "4000.00"),
            position("ACC-1", K89, "100", "42.00"),
        ],
        instruments=[
            CASH,
            CASH_EUR,
            instrument(AAPL, "quoted_price", "equity", USD, "close", country="US"),
            instrument(SPY, "quoted_price", "etf", USD, "close", country="US"),
            *kalshi_instruments()[1:2],
        ],
        market=[
            price(AAPL, "close", str(aapl[-1]), USD, "alpaca-1:daily"),
            price(SPY, "close", str(spy[-1]), USD, "alpaca-1:daily"),
            price(EUR, "close", str(eur[-1]), USD, "fed-h10-1:rates"),
            *kalshi_market()[:3],
        ],
        history={"dates": [d.isoformat() for d in dates], "closes": closes},
        event_groups=[kalshi_group("EVENT_GROUP_FLAG_TRUE", GROUP)],
    )


def what_if() -> dict[str, Any]:
    """A pre-trade what-if (W12.5): buying the ETF at an assumed price and the
    equity at the as-of price, each figure answered before and after."""
    return inputs(
        job={
            "account_ids": ["ACC-1"],
            "measures": [measure("market_value"), measure("concentration", ("instrument",))],
            "what_if": {
                "account_id": "ACC-1",
                "trades": [
                    {"instrument_id": SPY, "side": "SIDE_BUY", "quantity": "5",
                     "price": {"amount": "570.00", "instrument_id": USD}},
                    {"instrument_id": AAPL, "side": "SIDE_SELL", "quantity": "4", "price": None},
                ],
            },
        },  # fmt: skip
        accounts=[{"account_id": "ACC-1", "base_currency_instrument_id": USD}],
        positions=[position("ACC-1", USD, "5000.00", "5000.00"),
                   position("ACC-1", AAPL, "10", "2000.00")],  # fmt: skip
        instruments=[
            CASH,
            instrument(AAPL, "quoted_price", "equity", USD, "close", country="US"),
            instrument(SPY, "quoted_price", "etf", USD, "close", country="US"),
        ],
        market=[
            price(AAPL, "close", "227.50", USD, "alpaca-1:daily"),
            price(SPY, "close", "571.47", USD, "alpaca-1:daily"),
        ],
    )


def past_18_places() -> dict[str, Any]:
    """Contract v27 (rulings 453 and 486): a quoted price whose conversion
    chain runs past 18 places, its value per unit rounded half to even to
    18, its market value that times the quantity, exact -- an equity priced
    in euros and a crypto asset priced in a stablecoin."""
    return inputs(
        job={"account_ids": ["ACC-1"], "measures": [measure("market_value", ("instrument",))],
             "what_if": None},
        accounts=[{"account_id": "ACC-1", "base_currency_instrument_id": USD}],
        positions=[
            position("ACC-1", SAP, "1000.5", "12000.00"),
            position("ACC-1", BTC, "0.33333333", "20000.00"),
        ],
        instruments=[
            CASH,
            CASH_EUR,
            CASH_USDT,
            instrument(SAP, "quoted_price", "equity", EUR, "close", country="DE"),
            instrument(BTC, "quoted_price", "crypto_asset", USDT, "close"),
        ],
        market=[
            price(SAP, "close", "12.345678", EUR, "tiingo-1:daily"),
            price(EUR, "close", "1.085012345678901234", USD, "ecb-1:fx"),
            price(BTC, "close", "60000.123456789", USDT, "coinbase-1:daily"),
            price(USDT, "close", "0.999812345678901235", USD, "coinbase-1:daily"),
        ],
    )  # fmt: skip


def inverted_and_crossed() -> dict[str, Any]:
    """Contract v27 (ruling 462): a euro account holding dollars, a US equity
    and bitcoin priced in dollars, where the lake holds only EURUSD -- the
    dollar leg inverted, bitcoin's own price kept and its dollar leg
    inverted -- and a dollar account holding a Swiss equity and francs,
    where the lake holds no CHF rate against the dollar either way: crossed
    through the euro, the second pivot (the dollar being the base), its
    franc leg inverted."""
    return inputs(
        job={"account_ids": ["ACC-EU", "ACC-US"],
             "measures": [measure("market_value", ("instrument",))], "what_if": None},
        accounts=[
            {"account_id": "ACC-EU", "base_currency_instrument_id": EUR},
            {"account_id": "ACC-US", "base_currency_instrument_id": USD},
        ],
        positions=[
            position("ACC-EU", USD, "2500.00", "2300.00"),
            position("ACC-EU", AAPL, "10", "2000.00"),
            position("ACC-EU", BTC, "0.5", "28000.00"),
            position("ACC-US", NESN, "40", "4100.00"),
            position("ACC-US", CHF, "1000.00", "1100.00"),
        ],
        instruments=[
            CASH,
            CASH_EUR,
            CASH_CHF,
            instrument(AAPL, "quoted_price", "equity", USD, "close", country="US"),
            instrument(BTC, "quoted_price", "crypto_asset", USD, "close"),
            instrument(NESN, "quoted_price", "equity", CHF, "close", country="CH"),
        ],
        market=[
            price(AAPL, "close", "227.50", USD, "alpaca-1:daily"),
            price(BTC, "close", "60000.50", USD, "coinbase-1:daily"),
            price(NESN, "close", "98.76", CHF, "tiingo-1:daily"),
            price(EUR, "close", "1.0850", USD, "fed-board-1:daily"),
            price(EUR, "close", "0.9412", CHF, "ecb-1:fx"),
        ],
    )  # fmt: skip


def reporting_currency() -> dict[str, Any]:
    """Contract v27 (ruling 459): a dollar account's figures in a reporting
    currency, the euro, its leg the lake's EURUSD inverted; Unrealized P&L
    beside its market value, weights left unconverted."""
    given = inputs(
        job={"account_ids": ["ACC-1"], "reporting_currency": EUR,
             "measures": [measure("market_value"), measure("pnl"),
                          measure("concentration", ("instrument",))], "what_if": None},
        accounts=[{"account_id": "ACC-1", "base_currency_instrument_id": USD}],
        positions=[position("ACC-1", USD, "5000.00", "5000.00"),
                   position("ACC-1", AAPL, "10", "2000.00")],
        instruments=[CASH, CASH_EUR,
                     instrument(AAPL, "quoted_price", "equity", USD, "close", country="US")],
        market=[price(AAPL, "close", "227.50", USD, "alpaca-1:daily"),
                price(EUR, "close", "1.0850", USD, "fed-board-1:daily")],
    )  # fmt: skip
    return given


def execution_costs() -> dict[str, Any]:
    """Contract v27 (W12.1's `execution_cost`; the gaps spec's C1 to C10):
    an order bought in two fills and a euro-priced sale, each against the
    mid at its decision, arrival, placement arrival and fill -- a quote past
    the 5-second bound unanswered `NO_QUOTE`, never imputed; a fill on no
    placement accepted to a new order with no decision or arrival time
    `NOT_MEASURED`; fees apart in bps of notional -- and each account's
    notional-weighted mean per benchmark, in its base."""
    t0 = 1792299000000000000
    s = 1_000_000_000

    def at(seconds: float) -> str:
        return str(t0 + int(seconds * s))

    def execution(n: int, **given: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "execution_id": f"EXE-01JAH000000000000000000{n:03d}",
            "order_id": "ORD-01JAH0000000000000000001",
            "placement_id": "PLC-01JAH0000000000000000001",
            "account_id": "ACC-1",
            "instrument_id": AAPL,
            "side": "SIDE_BUY",
            "price": {"amount": "227.55", "instrument_id": USD},
            "quantity": "100",
            "executed_at_ns": at(30),
            "time_precision": "TIME_PRECISION_NANOSECOND",
            "liquidity_indicator": "LIQUIDITY_INDICATOR_REMOVED",
            "venue_id": "VEN-01JAH00000000000000XNAS",
            "fees": None,
            "financing": None,
            "reject_count": 0,
            "time_to_fill_ns": str(25 * s),
            "decision_at_ns": at(0),
            "arrival_at_ns": at(5),
            "placement_arrival_at_ns": at(6),
        }
        base.update(given)
        return base

    return inputs(
        job={"account_ids": ["ACC-1"], "measures": [measure("execution_cost")],
             "what_if": None},
        accounts=[{"account_id": "ACC-1", "base_currency_instrument_id": USD}],
        instruments=[CASH, CASH_EUR,
                     instrument(AAPL, "quoted_price", "equity", USD, "close", country="US"),
                     instrument(SAP, "quoted_price", "equity", EUR, "close", country="DE")],
        market=[
            # The decision's quote is 8 seconds stale: unanswered.
            price(AAPL, "mid", "227.10", USD, "alpaca-1:quotes", at=at(-8)),
            price(AAPL, "mid", "227.20", USD, "alpaca-1:quotes", at=at(4)),
            price(AAPL, "mid", "227.30", USD, "alpaca-1:quotes", at=at(5.5)),
            price(AAPL, "mid", "227.50", USD, "alpaca-1:quotes", at=at(29)),
            price(AAPL, "mid", "227.60", USD, "alpaca-1:quotes", at=at(44)),
            price(SAP, "mid", "120.10", EUR, "tiingo-1:quotes", at=at(29)),
            price(EUR, "close", "1.0850", USD, "fed-board-1:daily"),
        ],
        executions=[
            execution(1, fees={"amount": "1.25", "instrument_id": USD}),
            execution(2, price={"amount": "227.65", "instrument_id": USD}, quantity="50",
                      executed_at_ns=at(45), time_to_fill_ns=str(40 * s), reject_count=1),
            # Accepted to a new order: no decision, arrival or placement time.
            execution(3, order_id="ORD-01JAH0000000000000000002", placement_id="",
                      instrument_id=SAP, side="SIDE_SELL",
                      price={"amount": "120.00", "instrument_id": EUR}, quantity="30",
                      decision_at_ns="0", arrival_at_ns="0", placement_arrival_at_ns="0",
                      time_to_fill_ns="0", venue_id="VEN-01JAH00000000000000XETR"),
        ],
    )  # fmt: skip


CASES = {
    "valuation": (valuation, "v26's universe valued: net, gross, broken down, weights and P&L"),
    "stale-and-unconverted": (stale, "a stale price and a missing conversion, never zero"),
    "event-group": (event_group, "an exhaustive group: distribution, payoffs and marks"),
    "event-group-not-exhaustive": (open_group, "a group not exhaustive: raw prices, none of the named"),
    "resolved-in-a-stablecoin": (resolved, "a final 50/50 outcome in USDC, leg by leg"),
    "historical-var-and-es": (historical, "500 days by full revaluation, gaps carried, events beside"),
    "what-if": (what_if, "a pre-trade what-if beside the base"),
    "pnl-v2-realized": (realized_v2, "pnl version 2 (v27): unrealized beside realized since the account opened"),
    "quoted-price-past-18-places": (past_18_places, "a quoted price's chain past 18 places, rounded once per unit (v27)"),
    "inverted-and-crossed": (inverted_and_crossed, "fiat legs inverted and crossed through a pivot (v27)"),
    "reporting-currency": (reporting_currency, "an account's figures in a reporting currency (v27)"),
    "execution-cost": (execution_costs, "execution costs against the standard benchmarks (v27)"),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (build, says) in CASES.items():
        given = build()
        answer = reference.compute(given)
        case = {"case": name, "says": says, "inputs": given, "answer": answer.to_json()}
        (OUT / f"{name}.json").write_bytes(canonical(case) + b"\n")
        print(f"{name}: {len(answer.figures)} figures, {answer.answer_hash}")


if __name__ == "__main__":
    main()
