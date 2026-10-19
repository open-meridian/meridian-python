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
    }


def price(
    subject: str, kind: str, amount: str, currency: str, dataset: str, at: str = FRESH
) -> dict[str, Any]:
    return {
        "subject_id": subject,
        "kind": kind,
        "amount": amount,
        "instrument_id": currency,
        "dataset": dataset,
        "valid_at_ns": at,
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
    }
    base.update(given)
    return base


CASH = instrument(USD, "cash", "cash", USD, template="TPL-cash")
CASH_EUR = instrument(EUR, "cash", "cash", EUR, template="TPL-cash")
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
    """`pnl` version 2 (v27's, ruling 320; never asked of v26's component):
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


CASES = {
    "valuation": (valuation, "v26's universe valued: net, gross, broken down, weights and P&L"),
    "stale-and-unconverted": (stale, "a stale price and a missing conversion, never zero"),
    "event-group": (event_group, "an exhaustive group: distribution, payoffs and marks"),
    "event-group-not-exhaustive": (open_group, "a group not exhaustive: raw prices, none of the named"),
    "resolved-in-a-stablecoin": (resolved, "a final 50/50 outcome in USDC, leg by leg"),
    "historical-var-and-es": (historical, "500 days by full revaluation, gaps carried, events beside"),
    "what-if": (what_if, "a pre-trade what-if beside the base"),
    "pnl-v2-realized": (realized_v2, "pnl version 2 (v27): unrealized beside realized since the account opened"),
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
