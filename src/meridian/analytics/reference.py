"""The reference computations v26's analytics engine must equal exactly,
answers and hashes (spec/the-analytics-engine-answers-behind-one-api,
requirement 36; spec/the-analytics-engines-first-release, §1 and §4):
v26's three models and its eight measure definitions, in Python's `decimal`
and `fractions`, over a **reference case** -- a job and every input it reads,
written out as canonical JSON (RFC 8785) -- so the component's answer to the
same case is checked against these figures, digit for digit, and against
the same answer hash.

    from meridian.analytics import reference

    case = reference.load(path)            # {"case", "says", "inputs", "answer"}
    answer = reference.compute(case["inputs"])
    assert answer.to_json() == case["answer"]

Nothing here is the engine: it is slow on purpose, every value a `Decimal`
or a `Fraction`, nothing cached, so it is easy to read against the spec.

**The case's inputs** (`inputs`), every number a string in its stated form
and every 64-bit integer a string, as protobuf's JSON writes one:

- `engine_version`: the component's version the answer names; it is among
  the inputs, so the hash names the code that answered (Q7: a node's hash
  covers its code's version).
- `job`: the job as `RunJobRequest.job` carries it -- `account_ids`,
  `measures` (`definition`, `version`, `breakdowns`, `event_group_id`) and
  `what_if` (`account_id`, `trades`: `instrument_id`, `side` by its enum
  name, `quantity`, `price` or null).
- `book_watermark`: `[{"partition", "sequence"}]`, the watermark the book was
  read at; `lake_as_of_ns`; `routing_version`.
- `accounts`: `[{"account_id", "base_currency_instrument_id"}]`.
- `positions`: `[{"account_id", "instrument_id", "quantity", "cost", "sleeve"}]`
  -- `cost` the open lots' cost in the account's base currency (empty where
  the book holds none), `sleeve` empty where the position is in none.
- `closed_lots`: `[{"account_id", "instrument_id", "quantity", "proceeds",
  "cost", "sleeve"}]`, for `pnl` version 2 alone: each lot the book closed
  up to its watermark (since the account opened), its
  proceeds and cost in the account's base currency.
- `instruments`: `[{"instrument_id", "record_version", "template_id",
  "template_version", "calculation_version", "model_id", "model_version",
  "asset_class", "currency_instrument_id", "price_kind", "payout", "country"}]`
  -- `price_kind` the lake kind the template's pricing input names (`close`,
  `nav`, `last`, `mid`); `payout` an event contract's
  (`{"amount", "instrument_id"}`), null for any other.
- `market`: `[{"subject_id", "kind", "amount", "instrument_id", "dataset",
  "valid_at_ns"}]`, each a lake price at the job's as-of: the price of one
  unit of `subject_id` in `instrument_id`. An FX rate is the price of one
  currency's cash instrument in another (spec/the-lake, Q3).
- `history`: `{"dates": [business dates, oldest first], "closes":
  [{"subject_id", "amount", "instrument_id", "business_date"}]}` -- the
  daily closes at the definition's cut, for historical VaR and ES.
- `outcomes`: `[{"instrument_id", "final", "settlement_value", "dataset"}]`,
  each an event contract's latest outcome row.
- `event_groups`: `[{"event_group_id", "version", "member_instrument_ids",
  "mutually_exclusive", "exhaustive"}]`, each at the version in force, the
  flags by their enum names.
- `stale_after_ns`: `{dataset: nanoseconds}`, the client's setting per
  source; a dataset not named is never stale.

**The hash** (Q7): `sha256:` and the hex of SHA-256 over the RFC 8785
canonical JSON of `inputs`, exactly as the case holds them.

**The models** (the first release's §1; Q1, Q2, Q10). Each gives a value per
unit in the account's base currency, or says why not:

- `cash`: exactly 1 for the base currency; any other cash instrument (a
  stablecoin's included, never at par by assumption) at its own conversion.
- `quoted_price`: the price of the template's kind times its conversion.
- `binary_event`: before a final determination, the price times its
  conversion; after it, the settlement value per contract the outcome states
  times the conversion. A proposed or disputed outcome keeps the price.
- **A conversion** is leg by leg, each leg a market price of the currency in
  hand in another instrument, of kind `close`, then `mid`, then `last`; the
  shortest chain to the base, at most three legs, ties to the lowest kind
  and then to the instrument IDs' order. No rate is inverted or crossed. No
  chain is the figure not evaluated, `CONVERSION_MISSING`.
- An `LCL-` record is never priced: `LOCAL_RECORD`, never zero.

**The measures, version 1** (requirement 15, Q15; the first release's Q3
to Q6). Each value is a sum over unrounded terms, rounded once, half to
even, to the definition's scale (`DEFINITIONS`); each figure is per account
but `implied_distribution`'s, which is the group's.

- `market_value`: Σ quantity × value per unit.
- `exposure`: per bucket, two figures under the breakdown `component`:
  `gross`, Σ |quantity × value per unit|, and `net`, Σ quantity × value per
  unit, long minus short (ruling 301).
- `concentration`: each instrument's market value in the account, as a
  weight -- its numerator the instrument's market value, its denominator the
  account's -- broken down by instrument.
- `pnl`, version 1 (ruling 320; shown to people as "Unrealized P&L"): per
  bucket, one figure under the breakdown `component`, `unrealized`, Σ
  (quantity × value per unit − the open lots' cost). Version 2, v27's, once
  the book records each closed lot's proceeds (`LATER_DEFINITIONS`: computed
  here and pinned, never asked of 0.31.0's component) adds `realized`, Σ (a
  closed lot's proceeds − its cost) over every lot the book closed up to its
  watermark -- since the account opened, labelled so wherever it is shown
  (rulings 303, 320; `REALIZED_SINCE`).
- `historical_var` and `expected_shortfall`: full revaluation over the
  history's last `window_days` relative returns of every market object a
  position reads, each scenario's value quantity × Π(object now × close on
  the day ÷ close the day before), its P&L the scenario's value less the
  base's. A close missing is carried forward from the day before, up to
  five days running, then the position is `HISTORY_INSUFFICIENT`. The P&Ls
  are sorted, worst first; k = max(1, ⌊N × (1 − confidence)⌋); VaR is minus
  the k-th, ES minus the mean of the first k. Binary event contracts are
  left out (Q6), and beside the figure a second, keyed
  `SCENARIO_KIND_OUTCOME` with no outcome named, gives their exact
  resolution worst case: the least of each mutually exclusive group's
  resolution payoffs, and each other contract's worse of paying or not.
- `resolution_payoff`: per account holding a member of the group, for each
  member resolving YES (and, for a group mutually exclusive and not
  exhaustive, none of the named): Σ quantity × (the payout if the member
  pays, else 0) × conversion − cost, over the account's positions in the
  group's members.
- `implied_distribution`: each member's price -- the mid where the market
  is two-sided and its spread at most the definition's threshold, else the
  last trade -- over the sum of the members' prices, as numerator and
  denominator, beside the raw sum (`SCENARIO_KIND_BASE`). A group not
  exhaustive in the version in force answers the raw prices and their sum
  and is `GROUP_NOT_EXHAUSTIVE`.

**Breakdowns** (requirement 17): `account`, `asset_class`, `currency`,
`instrument`, `sleeve` and `country`, each from the position or its record;
a position with no value for one is `SCHEME_NOT_HELD`, naming it, and a
breakdown by any other name is a scheme the reference holds none of.

**A what-if** (W12.5): the trades added to their account's positions, the
cost of each its quantity times its assumed price, or the as-of price, in
the base currency, with its cash leg -- the base currency paid or received,
a position of the account's base cash instrument -- beside it; every figure
of that account is answered under `SCENARIO_KIND_BASE` and again under
`SCENARIO_KIND_WHAT_IF`, side by side. An event measure answers the base
alone.

**The answer's JSON** (a case's `answer`): `figures`, each with its
`measure` (`definition`, `version`, `breakdowns`, `event_group_id`),
`account_id`, `breakdown`, `scenario_key`, `value` or `numerator` and
`denominator` (each a decimal's stated text, rounded to the definition's
scale, or null), `currency_instrument_id` and `computed_as`; within one
measure, by account, breakdown and scenario. `not_evaluated`, within one
measure by account, instrument, reason and detail. `provenance`: the
watermark and as-of, the datasets read, the instruments read (by ID, each
with its record's and template's versions), the models (`built-in`, at the
engine's version), the measures asked, the event groups read, the routing
version, the engine's version and the answer's hash.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

from ._canonical import answer_hash, canonical, decimal_text

__all__ = [
    "BUILT_IN",
    "DEFINITIONS",
    "COMPONENT",
    "COMPONENTS",
    "MODELS",
    "LATER_DEFINITIONS",
    "REALIZED_SINCE",
    "UNREALIZED_PNL",
    "definition_of",
    "Answer",
    "AnswerFigure",
    "Definition",
    "Unevaluated",
    "compute",
    "load",
    "round_half_even",
    "value_per_unit",
]

#: The implementation every model id has (requirement 19).
BUILT_IN = "built-in"
#: v26's model ids, each at version 1 (the first release's §1).
MODELS = ("cash", "quoted_price", "binary_event")

# ── Version-1 choices, as the product owner ruled them (301, 2026-10-18) ──
# Each is one line here; the definitions' parameter text and the
# computations below read them, so a different ruling changes nothing else
# (and the pinned cases are rewritten with tools/write_reference_cases.py).

#: The breakdown a figure's component is named under (ruling 301,
#: 2026-10-18): `exposure` answers each bucket's `gross` (Σ |quantity ×
#: value per unit|) and `net` (long minus short); `pnl` its `unrealized`
#: (market value less the open lots' cost) and `realized` (closed lots'
#: proceeds less their cost, every lot closed to the book's watermark: since
#: the account opened). The vocabulary is ruling 302's, the period 303's;
#: from ruling 320 `pnl` version 1 is unrealized alone and realized is
#: version 2's, v27's.
COMPONENT = "component"
#: How version 2's realized P&L's period is labelled wherever it is shown
#: (rulings 303, 320).
REALIZED_SINCE = "since the account opened"
#: What people call `pnl` version 1 (ruling 320).
UNREALIZED_PNL = "Unrealized P&L"
COMPONENTS: Mapping[tuple[str, int], tuple[str, ...]] = {
    ("exposure", 1): ("gross", "net"),
    ("pnl", 1): ("unrealized",),
    ("pnl", 2): ("unrealized", "realized"),
}
#: `concentration` v1: each instrument's market value over the account's
#: market value ("account_market_value"), or over its gross exposure
#: ("account_gross_exposure").
CONCENTRATION_DENOMINATOR = "account_market_value"
#: A what-if trade adds its cash leg (the base currency paid or received)
#: beside the position it adds; False adds the position alone.
WHAT_IF_CASH_LEG = True

#: Conversion legs' kinds, in the order a leg is taken.
CONVERSION_KINDS = ("close", "mid", "last")
#: The longest conversion chain.
MOST_LEGS = 3
#: A close carried forward at most this many days running (historical VaR's
#: `missing_days`).
MOST_CARRIED = 5


@dataclass(frozen=True)
class Definition:
    """A measure's version-1 definition, as the component serves it
    (ListMeasureDefinitions): its parameters, fixed by the version, the
    breakdowns it allows and the scale it is rounded to, once."""

    definition: str
    version: int
    parameters: tuple[tuple[str, str], ...]
    breakdowns: tuple[str, ...]
    scale: int
    description: str

    def parameter(self, name: str) -> str:
        for key, value in self.parameters:
            if key == name:
                return value
        raise KeyError(f"{self.definition} v{self.version} has no parameter {name!r}")


_BY = ("account", "asset_class", "currency", "instrument", "sleeve", "country")

#: v26's standard definitions, version 1 (requirement 14; the v26 plan's
#: question 226). `historical_var`'s and `implied_distribution`'s parameters
#: are design's fixture's (fixtures/analytics/list-measure-definitions.yaml).
DEFINITIONS: Mapping[str, Definition] = {
    d.definition: d
    for d in (
        Definition(
            "market_value",
            1,
            (("valuation", "quantity_times_value_per_unit"),),
            _BY,
            2,
            "Each position's quantity times its model's value per unit, net",
        ),
        Definition(
            "exposure",
            1,
            (
                ("valuation", "quantity_times_value_per_unit"),
                ("components", "gross_absolute_and_net_signed"),
            ),
            _BY,
            2,
            "Each bucket's market value gross (without its sign) and net",
        ),
        Definition(
            "concentration",
            1,
            (("weight", f"instrument_market_value_over_{CONCENTRATION_DENOMINATOR}"),),
            ("instrument",),
            2,
            "Each instrument's weight in its account, as a numerator and a denominator",
        ),
        Definition(
            "pnl",
            1,
            (("unrealized", "market_value_less_open_lots_cost"),),
            _BY,
            2,
            "Unrealized P&L: each bucket's market value less its open lots' cost",
        ),
        Definition(
            "historical_var",
            1,
            (
                ("confidence", "0.99"),
                ("horizon_days", "1"),
                ("window_days", "500"),
                ("return_type", "relative"),
                ("missing_days", "carry_forward_then_not_evaluated_after_5"),
                ("quantile", "order_statistic_lower"),
                ("daily_cut", "16:00 America/New_York"),
                ("event_contracts", "excluded_with_resolution_worst_case"),
            ),
            ("account", "asset_class", "currency", "sleeve"),
            2,
            "Historical value at risk by full revaluation over the lake's history",
        ),
        Definition(
            "expected_shortfall",
            1,
            (
                ("confidence", "0.99"),
                ("horizon_days", "1"),
                ("window_days", "500"),
                ("return_type", "relative"),
                ("missing_days", "carry_forward_then_not_evaluated_after_5"),
                ("quantile", "order_statistic_lower"),
                ("daily_cut", "16:00 America/New_York"),
                ("event_contracts", "excluded_with_resolution_worst_case"),
            ),
            ("account", "asset_class", "currency", "sleeve"),
            2,
            "The mean loss beyond historical value at risk, by full revaluation",
        ),
        Definition(
            "resolution_payoff",
            1,
            (("none_of_the_named", "mutually_exclusive_not_exhaustive"),),
            ("account",),
            2,
            "Each account's P&L if each member of an event group resolves YES",
        ),
        Definition(
            "implied_distribution",
            1,
            (
                ("price", "mid_or_last_past_spread"),
                ("spread_threshold", "0.10"),
                ("normalisation", "price_over_sum_of_prices"),
            ),
            (),
            18,
            "Each outcome's price over the sum of the group's prices, as a numerator "
            "and a denominator",
        ),
        Definition(
            "execution_cost",
            1,
            (
                ("benchmarks", "decision_arrival_placement_arrival_mid_at_fill"),
                ("sign", "side_adjusted_positive_cost"),
                ("units", "bps"),
                ("staleness_bound_ns", str(5_000_000_000)),
            ),
            ("account",),
            4,
            "Each execution's cost against each benchmark in bps, side-adjusted, "
            "positive a cost; each account's notional-weighted mean per benchmark",
        ),
    )
}

#: The definitions at a version after 1: `pnl` version 2, realized P&L
#: beside unrealized, served from contract v27 now the book records each
#: closed lot's proceeds (rulings 320 and 396; `Lot.reliefs`).
LATER_DEFINITIONS: Mapping[tuple[str, int], Definition] = {
    ("pnl", 2): Definition(
        "pnl",
        2,
        (
            ("unrealized", "market_value_less_open_lots_cost"),
            ("realized", "closed_lots_proceeds_less_cost_since_the_account_opened"),
        ),
        _BY,
        2,
        "Each bucket's unrealized P&L (open lots) and realized P&L since the account "
        "opened (closed lots)",
    ),
}


def definition_of(name: str, version: int) -> Definition | None:
    """A definition the reference computes: v26's, or a later one's."""
    served = DEFINITIONS.get(name)
    if served is not None and served.version == version:
        return served
    return LATER_DEFINITIONS.get((name, version))


# The enum names the answer's JSON carries, as the wire's mirrors name them.
BASE, WHAT_IF, HISTORICAL_DAY = (
    "SCENARIO_KIND_BASE",
    "SCENARIO_KIND_WHAT_IF",
    "SCENARIO_KIND_HISTORICAL_DAY",
)
OUTCOME, NONE_OF_THE_NAMED = "SCENARIO_KIND_OUTCOME", "SCENARIO_KIND_NONE_OF_THE_NAMED"
EXACT = "COMPUTED_AS_EXACT"
PRICE_MISSING = "NOT_EVALUATED_REASON_PRICE_MISSING"
PRICE_STALE = "NOT_EVALUATED_REASON_PRICE_STALE"
CONVERSION_MISSING = "NOT_EVALUATED_REASON_CONVERSION_MISSING"
LOCAL_RECORD = "NOT_EVALUATED_REASON_LOCAL_RECORD"
SCHEME_NOT_HELD = "NOT_EVALUATED_REASON_SCHEME_NOT_HELD"
GROUP_NOT_EXHAUSTIVE = "NOT_EVALUATED_REASON_GROUP_NOT_EXHAUSTIVE"
HISTORY_INSUFFICIENT = "NOT_EVALUATED_REASON_HISTORY_INSUFFICIENT"
FLAG_TRUE = "EVENT_GROUP_FLAG_TRUE"
COST_MISSING = "NOT_EVALUATED_REASON_COST_MISSING"
DIRECT = "CONVERSION_DERIVATION_DIRECT"
INVERTED = "CONVERSION_DERIVATION_INVERTED"
CROSSED = "CONVERSION_DERIVATION_CROSSED"
_DERIVATION_RANK = {DIRECT: 0, INVERTED: 1, CROSSED: 2}


def round_half_even(value: Fraction | Decimal, scale: int) -> Decimal:
    """`value`, exact, rounded once half to even to `scale` places (Q11): a
    sum of unrounded terms, or a quotient, never rounded before."""
    exact = Fraction(value)
    shifted = exact * 10**scale
    whole, rest = divmod(shifted.numerator, shifted.denominator)
    twice = 2 * rest
    if twice > shifted.denominator or (twice == shifted.denominator and whole % 2 == 1):
        whole += 1
    with localcontext() as context:
        context.prec = 100
        return (
            Decimal(whole).scaleb(-scale).quantize(Decimal(1).scaleb(-scale), ROUND_HALF_EVEN)
        )


# ── The case, read ──────────────────────────────────────────────────────────


def _d(text: Any) -> Decimal:
    if not isinstance(text, str) or not text:
        raise ValueError(f"a number in a reference case is a non-empty string, not {text!r}")
    value = Decimal(text)
    if not value.is_finite():
        raise ValueError(f"{text!r} is not a finite number")
    return value


@dataclass(frozen=True)
class _Price:
    subject_id: str
    kind: str
    amount: Decimal
    instrument_id: str
    dataset: str
    valid_at_ns: int
    row_key: str = ""
    version: int = 0
    source_ns: int = 0


@dataclass(frozen=True)
class _Leg:
    """One conversion leg as the answer names it (contract v27, ruling 462):
    from one cash instrument to another at a rate -- the lake's own, its
    inverse rounded half to even to 18 places, or a cross through a pivot,
    its two sub-legs' rates multiplied and rounded so -- with the lake's
    prices it moves with, each with its exponent (1, or -1 inverted)."""

    from_id: str
    to_id: str
    rate: Decimal
    derivation: str
    via: str
    dataset: str
    factors: tuple[tuple[_Price, int], ...]
    subs: tuple[_Leg, ...] = ()
    kind_rank: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "from_instrument_id": self.from_id,
            "to_instrument_id": self.to_id,
            "rate": decimal_text(self.rate),
            "derivation": self.derivation,
            "via_instrument_id": self.via,
            "dataset": self.dataset,
        }


@dataclass(frozen=True)
class _Instrument:
    instrument_id: str
    record_version: str
    template_id: str
    template_version: str
    calculation_version: str
    model_id: str
    model_version: int
    asset_class: str
    currency_instrument_id: str
    price_kind: str
    payout: tuple[Decimal, str] | None
    country: str
    #: Its ISO 4217 code: a fiat currency's cash instrument, whose legs alone
    #: may be inverted or crossed (ruling 462); empty for a token.
    currency_code: str = ""


@dataclass(frozen=True)
class _Position:
    account_id: str
    instrument_id: str
    quantity: Decimal
    cost: Decimal | None
    sleeve: str


@dataclass(frozen=True)
class _ClosedLot:
    account_id: str
    instrument_id: str
    quantity: Decimal
    proceeds: Decimal
    cost: Decimal | None
    sleeve: str


@dataclass(frozen=True)
class _Group:
    event_group_id: str
    version: str
    members: tuple[str, ...]
    mutually_exclusive: str
    exhaustive: str


@dataclass(frozen=True)
class _Outcome:
    instrument_id: str
    final: bool
    settlement_value: Decimal
    dataset: str


def _measure_json(key: tuple[str, int, str, tuple[str, ...]]) -> dict[str, Any]:
    definition, version, group, breakdowns = key
    return {
        "definition": definition,
        "version": version,
        "breakdowns": list(breakdowns),
        "event_group_id": group,
    }


@dataclass(frozen=True)
class AnswerFigure:
    """One figure of a reference answer, in the answer's JSON words."""

    measure: tuple[str, int, str, tuple[str, ...]]
    account_id: str
    breakdown: tuple[tuple[str, str], ...]
    scenario: tuple[str, str, str]
    value: Decimal | None = None
    numerator: Decimal | None = None
    denominator: Decimal | None = None
    currency_instrument_id: str = ""

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "measure": _measure_json(self.measure),
            "account_id": self.account_id,
            "breakdown": [{"breakdown": b, "value": v} for b, v in self.breakdown],
            "scenario_key": {
                "kind": self.scenario[0],
                "business_date": self.scenario[1],
                "outcome_instrument_id": self.scenario[2],
            },
            "currency_instrument_id": self.currency_instrument_id,
            "computed_as": EXACT,
        }
        for name in ("value", "numerator", "denominator"):
            held = getattr(self, name)
            out[name] = None if held is None else decimal_text(held)
        return out


@dataclass(frozen=True)
class Unevaluated:
    """A position or a measure not evaluated, and why (requirement 9)."""

    account_id: str
    instrument_id: str
    measure: tuple[str, int, str, tuple[str, ...]]
    reason: str
    detail: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "instrument_id": self.instrument_id,
            "measure": _measure_json(self.measure),
            "reason": self.reason,
            "detail": self.detail,
        }


@dataclass
class Answer:
    """A reference answer: its figures, what was not evaluated, and its
    provenance with the answer's hash (requirement 4)."""

    figures: list[AnswerFigure] = field(default_factory=list)
    not_evaluated: list[Unevaluated] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    #: The `ExecutionCost` rows an `execution_cost` job records (contract
    #: v27, W10.11), in the answer's JSON only where the job asks for it.
    execution_costs: list[dict[str, Any]] = field(default_factory=list)
    asks_execution_cost: bool = False

    @property
    def answer_hash(self) -> str:
        return str(self.provenance["answer_hash"])

    def to_json(self) -> dict[str, Any]:
        """The answer as a reference case's `answer` holds it."""
        out: dict[str, Any] = {
            "figures": [each.to_json() for each in self.figures],
            "not_evaluated": [each.to_json() for each in self.not_evaluated],
            "provenance": self.provenance,
        }
        if self.asks_execution_cost:
            out["execution_costs"] = self.execution_costs
        return out


class _Case:
    """A reference case's inputs, read once."""

    def __init__(self, inputs: Mapping[str, Any]) -> None:
        self.inputs = inputs
        self.engine_version = str(inputs["engine_version"])
        job = inputs["job"]
        self.account_ids: tuple[str, ...] = tuple(job.get("account_ids") or ())
        self.measures: tuple[Mapping[str, Any], ...] = tuple(job.get("measures") or ())
        self.what_if: Mapping[str, Any] | None = job.get("what_if")
        self.lake_as_of_ns = int(inputs.get("lake_as_of_ns") or 0)
        self.business_date = str(job.get("business_date") or "")
        self.reporting_currency = str(job.get("reporting_currency") or "")
        #: The deployment's pivot order (ruling 483), each a fiat cash
        #: instrument's ID, tried in order for a cross.
        self.pivots: tuple[str, ...] = tuple(inputs.get("fx_pivot_currencies") or ())
        self.bases = {
            a["account_id"]: a["base_currency_instrument_id"] for a in inputs["accounts"]
        }
        self.instruments = {
            i["instrument_id"]: _Instrument(
                instrument_id=i["instrument_id"],
                record_version=str(i.get("record_version", "")),
                template_id=i.get("template_id", ""),
                template_version=i.get("template_version", ""),
                calculation_version=i.get("calculation_version", ""),
                model_id=i.get("model_id", ""),
                model_version=int(i.get("model_version", 1)),
                asset_class=i.get("asset_class", ""),
                currency_instrument_id=i.get("currency_instrument_id", ""),
                price_kind=i.get("price_kind", ""),
                payout=None
                if not i.get("payout")
                else (_d(i["payout"]["amount"]), i["payout"]["instrument_id"]),
                country=i.get("country", ""),
                currency_code=i.get("currency_code", ""),
            )
            for i in inputs.get("instruments", [])
        }
        self.positions = [
            _Position(
                account_id=p["account_id"],
                instrument_id=p["instrument_id"],
                quantity=_d(p["quantity"]),
                cost=_d(p["cost"]) if p.get("cost") else None,
                sleeve=p.get("sleeve", ""),
            )
            for p in inputs.get("positions", [])
        ]
        self.closed_lots = [
            _ClosedLot(
                account_id=c["account_id"],
                instrument_id=c["instrument_id"],
                quantity=_d(c["quantity"]),
                proceeds=_d(c["proceeds"]),
                cost=_d(c["cost"]) if c.get("cost") else None,
                sleeve=c.get("sleeve", ""),
            )
            for c in inputs.get("closed_lots", [])
        ]
        self.market: dict[tuple[str, str], list[_Price]] = {}
        for m in inputs.get("market", []):
            price = _Price(
                subject_id=m["subject_id"],
                kind=m["kind"],
                amount=_d(m["amount"]),
                instrument_id=m["instrument_id"],
                dataset=m.get("dataset", ""),
                valid_at_ns=int(m.get("valid_at_ns") or 0),
                row_key=m.get("row_key", ""),
                version=int(m.get("version") or 0),
                source_ns=int(m.get("source_ns") or m.get("valid_at_ns") or 0),
            )
            self.market.setdefault((price.subject_id, price.kind), []).append(price)
        history = inputs.get("history") or {}
        self.dates: tuple[str, ...] = tuple(history.get("dates") or ())
        self.closes: dict[tuple[str, str], tuple[Decimal, str]] = {
            (c["subject_id"], c["business_date"]): (_d(c["amount"]), c["instrument_id"])
            for c in history.get("closes") or ()
        }
        self.outcomes = {
            o["instrument_id"]: _Outcome(
                instrument_id=o["instrument_id"],
                final=bool(o.get("final")),
                settlement_value=_d(o["settlement_value"]),
                dataset=o.get("dataset", ""),
            )
            for o in inputs.get("outcomes", [])
        }
        self.groups = {
            g["event_group_id"]: _Group(
                event_group_id=g["event_group_id"],
                version=str(g["version"]),
                members=tuple(g.get("member_instrument_ids") or ()),
                mutually_exclusive=g.get("mutually_exclusive", ""),
                exhaustive=g.get("exhaustive", ""),
            )
            for g in inputs.get("event_groups", [])
        }
        self.stale_after = {k: int(v) for k, v in (inputs.get("stale_after_ns") or {}).items()}
        self.executions: list[Mapping[str, Any]] = list(inputs.get("executions") or ())
        # What the answer read, for its provenance.
        self.datasets: set[str] = set()
        self.read_instruments: set[str] = set()
        self.models: set[tuple[str, int]] = set()
        self.read_groups: set[str] = set()
        self.input_prices: dict[str, _Price] = {}
        self.legs: dict[tuple[str, str, str, str], _Leg] = {}

    # ── Market objects ───────────────────────────────────────────────────

    def price(self, subject: str, kind: str) -> _Price | None:
        held = self.market.get((subject, kind)) or []
        # One row per subject and kind at the as-of; the latest valid where a
        # case states more.
        return max(held, key=lambda p: (p.valid_at_ns, p.dataset)) if held else None

    def price_in(self, subject: str, kind: str, instrument_id: str) -> _Price | None:
        """The price of `subject` in one instrument: an FX rate is the price
        of one cash instrument in another, and a currency may be priced in
        several (EURUSD and EURCHF), each its own row."""
        held = [
            p
            for p in self.market.get((subject, kind)) or []
            if p.instrument_id == instrument_id
        ]
        return max(held, key=lambda p: (p.valid_at_ns, p.dataset)) if held else None

    def quoted_in(self, subject: str, kind: str) -> list[_Price]:
        """The latest price of `subject` of `kind` in each instrument it is
        priced in, by instrument ID."""
        ins = sorted({p.instrument_id for p in self.market.get((subject, kind)) or []})
        return [p for p in (self.price_in(subject, kind, i) for i in ins) if p is not None]

    def stale(self, price: _Price) -> bool:
        limit = self.stale_after.get(price.dataset)
        return limit is not None and self.lake_as_of_ns - price.valid_at_ns > limit

    def fiat(self, instrument_id: str) -> bool:
        """Whether a cash instrument is a fiat currency's (it has an ISO 4217
        code): only a fiat leg is inverted or crossed (ruling 462)."""
        record = self.instruments.get(instrument_id)
        return record is not None and bool(record.currency_code)

    def _direct(self, at: str, to: str) -> _Leg | None:
        """The lake's own rate from `at` to `to`, by kind in order."""
        for rank, kind in enumerate(CONVERSION_KINDS):
            price = self.price_in(at, kind, to)
            if price is not None:
                return _Leg(at, to, price.amount, DIRECT, "", price.dataset, ((price, 1),),
                            kind_rank=rank)  # fmt: skip
        return None

    def _inverted(self, at: str, to: str) -> _Leg | None:
        """The lake's rate the other way (`to` priced in `at`), inverted: 1 ÷
        x, rounded half to even to 18 places (ruling 462)."""
        for rank, kind in enumerate(CONVERSION_KINDS):
            price = self.price_in(to, kind, at)
            if price is not None and price.amount != 0:
                rate = round_half_even(1 / Fraction(price.amount), 18)
                return _Leg(at, to, rate, INVERTED, "", price.dataset, ((price, -1),),
                            kind_rank=rank)  # fmt: skip
        return None

    def _either(self, at: str, to: str) -> _Leg | None:
        return self._direct(at, to) or self._inverted(at, to)

    def _derived(self, at: str, to: str) -> _Leg | None:
        """A fiat leg with no direct rate in the lake's direction: inverted,
        else crossed through the first pivot both sub-legs reach, each
        direct or inverted, its rate their product rounded half to even to
        18 places (rulings 462 and 483). None for a token's leg."""
        if not (self.fiat(at) and self.fiat(to)):
            return None
        inverted = self._inverted(at, to)
        if inverted is not None:
            return inverted
        for pivot in self.pivots:
            if pivot in (at, to) or not self.fiat(pivot):
                continue
            first, second = self._either(at, pivot), self._either(pivot, to)
            if first is None or second is None:
                continue
            rate = round_half_even(Fraction(first.rate) * Fraction(second.rate), 18)
            return _Leg(
                at,
                to,
                rate,
                CROSSED,
                pivot,
                "",
                first.factors + second.factors,
                subs=(first, second),
                kind_rank=max(first.kind_rank, second.kind_rank),
            )
        return None

    def conversion(self, held: str, base: str) -> tuple[list[_Leg], str] | tuple[None, str]:
        """The legs from `held` to `base`, or None and why: the shortest
        chain of the lake's own rates, at most `MOST_LEGS` (a cross counting
        as its two sub-legs), its last leg from a fiat currency to a fiat
        base inverted or crossed where the lake has no direct rate (contract
        v27, ruling 462); a token's leg only ever the lake's own.
        Ties go by each leg's derivation (direct, then inverted, then
        crossed), then the lowest kinds, then the instrument IDs' order."""
        if held == base:
            return [], ""
        chains: list[
            tuple[int, tuple[int, ...], tuple[int, ...], tuple[str, ...], list[_Leg]]
        ] = []

        def keep(legs: list[_Leg]) -> None:
            chains.append(
                (
                    _counted(legs),
                    tuple(_DERIVATION_RANK[leg.derivation] for leg in legs),
                    tuple(leg.kind_rank for leg in legs),
                    tuple(leg.to_id for leg in legs),
                    list(legs),
                )
            )

        def walk(at: str, legs: list[_Leg], seen: frozenset[str]) -> None:
            if at == base:
                keep(legs)
                return
            if len(legs) == MOST_LEGS:
                return
            if self._direct(at, base) is None:
                derived = self._derived(at, base)
                if derived is not None and _counted([*legs, derived]) <= MOST_LEGS:
                    keep([*legs, derived])
            for rank, kind in enumerate(CONVERSION_KINDS):
                for price in self.quoted_in(at, kind):
                    if price.instrument_id in seen:
                        continue
                    leg = _Leg(at, price.instrument_id, price.amount, DIRECT, "", price.dataset,
                               ((price, 1),), kind_rank=rank)  # fmt: skip
                    walk(leg.to_id, [*legs, leg], seen | {leg.to_id})

        walk(held, [], frozenset({held}))
        if not chains:
            return None, CONVERSION_MISSING
        chains.sort(key=lambda c: c[:4])
        legs = chains[0][4]
        for leg in legs:
            for price, _ in leg.factors:
                if self.stale(price):
                    return None, PRICE_STALE
        return legs, ""


# ── The models ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Valued:
    """A position's value per unit in its base, the market objects it read
    with how each moves it (its exponent), its own price where its model
    read one, and its conversion legs."""

    per_unit: Fraction
    factors: tuple[tuple[_Price, int], ...]
    own: _Price | None = None
    legs: tuple[_Leg, ...] = ()


def _valued(per_unit: Fraction, legs: Sequence[_Leg], own: _Price | None = None) -> _Valued:
    factors = tuple(f for leg in legs for f in leg.factors)
    if own is not None:
        factors = ((own, 1), *factors)
    return _Valued(per_unit, factors, own, tuple(legs))


def _value(case: _Case, instrument_id: str, base: str) -> tuple[_Valued | None, str, str]:
    """A value per unit in `base`, or None, the reason and its detail."""
    if instrument_id.startswith("LCL-"):
        return None, LOCAL_RECORD, "local record: not priced"
    record = case.instruments.get(instrument_id)
    if record is None:
        raise ValueError(f"the case names {instrument_id} and holds no record of it")
    case.read_instruments.add(instrument_id)
    case.models.add((record.model_id, record.model_version))
    if record.model_id == "cash":
        legs, why = case.conversion(instrument_id, base)
        if legs is None:
            return None, why, ""
        return _valued(_product(legs), legs), "", ""
    if record.model_id == "binary_event":
        outcome = case.outcomes.get(instrument_id)
        if outcome is not None and outcome.final:
            if outcome.dataset:
                case.datasets.add(outcome.dataset)
            if record.payout is None:
                raise ValueError(f"{instrument_id} is a binary event contract with no payout")
            legs, why = case.conversion(record.payout[1], base)
            if legs is None:
                return None, why, ""
            return _valued(Fraction(outcome.settlement_value) * _product(legs), legs), "", ""
    elif record.model_id != "quoted_price":
        raise ValueError(f"{instrument_id}'s model {record.model_id!r} is not one of v26's")
    price = case.price(instrument_id, record.price_kind)
    if price is None:
        return None, PRICE_MISSING, record.price_kind
    if case.stale(price):
        return None, PRICE_STALE, price.dataset
    legs, why = case.conversion(price.instrument_id, base)
    if legs is None:
        return None, why, ""
    per_unit = Fraction(price.amount) * _product(legs)
    if record.model_id == "quoted_price":
        # Contract v27 (rulings 453 and 486): a quoted price's value per unit
        # rounded half to even to 18 places; its market value that times the
        # quantity, exact.
        per_unit = Fraction(round_half_even(per_unit, 18))
    return _valued(per_unit, legs, price), "", ""


def _counted(legs: Iterable[_Leg]) -> int:
    """A chain's length against `MOST_LEGS`: a cross counts as its two."""
    return sum(2 if leg.derivation == CROSSED else 1 for leg in legs)


def _product(legs: Iterable[_Leg]) -> Fraction:
    out = Fraction(1)
    for leg in legs:
        out *= Fraction(leg.rate)
    return out


def _past_18(value: Decimal) -> bool:
    exponent = value.as_tuple().exponent
    return isinstance(exponent, int) and -exponent > 18


def value_per_unit(
    model_id: str, instrument_id: str, inputs: Sequence[Any]
) -> tuple[Decimal, str]:
    """A built-in model's value per unit for one pricing unit (W12.3), from
    exactly the market objects a batch carries: the instrument's own price
    (or, for `binary_event`, its `outcome` where one is carried), times each
    conversion leg the inputs hold from the currency in hand, until none
    leads further. The value and the cash instrument (or ISO 4217 code) it
    is in; from contract v27 a quoted price's rounded half to even to 18
    places where it runs past them (rulings 453 and 486). `inputs` are
    `(subject_id, kind, amount, instrument_id or code)` tuples."""
    rows = [(str(s), str(k), Decimal(a), str(i)) for s, k, a, i in inputs]
    if model_id not in MODELS:
        raise ValueError(f"{model_id!r} is not one of v26's models {MODELS}")
    own = [r for r in rows if r[0] == instrument_id]
    if model_id == "cash":
        held, value = instrument_id, Decimal(1)
    else:
        chosen = [r for r in own if r[1] == "outcome"] if model_id == "binary_event" else []
        chosen = chosen or [r for r in own if r[1] != "outcome"]
        if not chosen:
            raise ValueError(f"no price of {instrument_id} among the batch's inputs")
        _, _, value, held = chosen[0]
    # Every row but the instrument's own price is a conversion leg; for
    # `cash` its own price to another currency is one.
    legs = [r for r in rows if model_id == "cash" or r[0] != instrument_id]
    visited: set[str] = set()
    while True:
        leg = next((r for r in legs if r[0] == held and r[0] not in visited), None)
        if leg is None:
            if model_id == "quoted_price" and _past_18(value):
                # Contract v27 (rulings 453 and 486): rounded half to even to
                # 18 places, as the engine rounds it, where it runs past them.
                value = round_half_even(value, 18)
            return value, held
        visited.add(held)
        with localcontext() as context:
            context.prec = 100
            value = value * leg[2]
        held = leg[3]


# ── The measures ────────────────────────────────────────────────────────────


Key = tuple[str, int, str, tuple[str, ...]]


def _measure_key(ref: Mapping[str, Any]) -> Key:
    """A measure as the answer names it back: its definition, version, event
    group and breakdowns, so two asks of one definition stay apart."""
    return (
        str(ref["definition"]),
        int(ref.get("version", 1)),
        str(ref.get("event_group_id", "")),
        tuple(str(b) for b in ref.get("breakdowns") or ()),
    )


def _breakdown_of(
    case: _Case, position: _Position, names: Sequence[str]
) -> tuple[tuple[tuple[str, str], ...] | None, str]:
    record = case.instruments.get(position.instrument_id)
    out: list[tuple[str, str]] = []
    for name in names:
        held = {
            "account": position.account_id,
            "asset_class": record.asset_class if record else "",
            "currency": record.currency_instrument_id if record else "",
            "instrument": position.instrument_id,
            "sleeve": position.sleeve,
            "country": record.country if record else "",
        }.get(name, "")
        if not held:
            return None, name
        out.append((name, held))
    return tuple(out), ""


@dataclass
class _Run:
    case: _Case
    answer: Answer


def _positions(case: _Case, account: str, scenario: str) -> list[_Position]:
    held = [p for p in case.positions if p.account_id == account]
    if scenario != WHAT_IF or case.what_if is None:
        return held
    base = case.bases[account]
    added: list[_Position] = []
    for trade in case.what_if.get("trades") or ():
        quantity = _d(trade["quantity"])
        if str(trade.get("side", "")).startswith("SIDE_SELL"):
            quantity = -quantity
        price = trade.get("price")
        if price:
            legs, _ = case.conversion(price["instrument_id"], base)
            per = Fraction(_d(price["amount"])) * (_product(legs) if legs is not None else 0)
        else:
            valued, _, _ = _value(case, trade["instrument_id"], base)
            per = valued.per_unit if valued is not None else Fraction(0)
        cost = round_half_even(per * Fraction(quantity), 18)
        added.append(
            _Position(
                account_id=account,
                instrument_id=trade["instrument_id"],
                quantity=quantity,
                cost=cost,
                sleeve="",
            )
        )
        if WHAT_IF_CASH_LEG:
            # Its cash leg: the base currency paid for it, or received.
            added.append(_Position(account, base, -cost, -cost, ""))
    return held + added


def _scenarios(case: _Case, account: str) -> list[str]:
    if case.what_if is not None and case.what_if.get("account_id") == account:
        return [BASE, WHAT_IF]
    return [BASE]


def _linear(run: _Run, ref: Mapping[str, Any], definition: Definition) -> None:
    """market_value, exposure and pnl: a sum per account and breakdown; for
    exposure and pnl one per component (`COMPONENT`, ruling 301): exposure's
    gross and net, pnl's unrealized and realized."""
    case, key = run.case, _measure_key(ref)
    names = [str(b) for b in ref.get("breakdowns") or ()]
    unknown = [n for n in names if n not in _BY]
    if unknown:
        for name in unknown:
            run.answer.not_evaluated.append(Unevaluated("", "", key, SCHEME_NOT_HELD, name))
        return
    components = COMPONENTS.get((definition.definition, definition.version), ("",))
    for account in case.account_ids:
        base = case.bases[account]
        reported = _reporting(run, account, key)
        if reported is None:
            continue
        rate, currency = reported
        for scenario in _scenarios(case, account):
            sums: dict[tuple[tuple[str, str], ...], dict[str, Fraction]] = {}

            def add(
                group: tuple[tuple[str, str], ...],
                component: str,
                worth: Fraction,
                sums: dict[tuple[tuple[str, str], ...], dict[str, Fraction]] = sums,
            ) -> None:
                held = sums.setdefault(group, {})
                held[component] = held.get(component, Fraction(0)) + worth

            for position in _positions(case, account, scenario):
                valued, why, detail = _value(case, position.instrument_id, base)
                if valued is None:
                    if scenario == BASE:
                        run.answer.not_evaluated.append(
                            Unevaluated(account, position.instrument_id, key, why, detail)
                        )
                    continue
                _read(case, valued)
                group, missing = _breakdown_of(case, position, names)
                if group is None:
                    if scenario == BASE:
                        run.answer.not_evaluated.append(
                            Unevaluated(
                                account, position.instrument_id, key, SCHEME_NOT_HELD, missing
                            )
                        )
                    continue
                worth = valued.per_unit * Fraction(position.quantity)
                if definition.definition == "exposure":
                    add(group, "gross", abs(worth))
                    add(group, "net", worth)
                elif definition.definition == "pnl":
                    if position.cost is None:
                        # Contract v27 (ruling 325): a lot's cost the book
                        # does not record, never zero.
                        if scenario == BASE:
                            run.answer.not_evaluated.append(
                                Unevaluated(account, position.instrument_id, key, COST_MISSING)
                            )
                        continue
                    add(group, "unrealized", worth - Fraction(position.cost))
                else:
                    add(group, "", worth)
            if "realized" in components:
                for lot in case.closed_lots:
                    if lot.account_id != account:
                        continue
                    as_position = _Position(
                        account, lot.instrument_id, lot.quantity, None, lot.sleeve
                    )
                    group, missing = _breakdown_of(case, as_position, names)
                    if group is None:
                        if scenario == BASE:
                            run.answer.not_evaluated.append(
                                Unevaluated(
                                    account, lot.instrument_id, key, SCHEME_NOT_HELD, missing
                                )
                            )
                        continue
                    if lot.cost is None:
                        if scenario == BASE:
                            run.answer.not_evaluated.append(
                                Unevaluated(account, lot.instrument_id, key, COST_MISSING)
                            )
                        continue
                    add(group, "realized", Fraction(lot.proceeds) - Fraction(lot.cost))
            if not sums and not names:
                sums[()] = {}
            for group, held in sorted(sums.items()):
                for component in components:
                    breakdown = group + (((COMPONENT, component),) if component else ())
                    run.answer.figures.append(
                        AnswerFigure(
                            measure=key,
                            account_id=account,
                            breakdown=breakdown,
                            scenario=(scenario, "", ""),
                            value=round_half_even(
                                held.get(component, Fraction(0)) * rate, definition.scale
                            ),
                            currency_instrument_id=currency,
                        )
                    )


def _reporting(run: _Run, account: str, key: Key) -> tuple[Fraction, str] | None:
    """The rate from an account's base to the job's reporting currency
    (contract v27, ruling 459), its legs read, and the currency its figures
    are in: 1 and the base where the job names none, or its base. None, the
    account not evaluated with why, where no chain reaches it."""
    case = run.case
    base, reporting = case.bases[account], case.reporting_currency
    if not reporting or reporting == base:
        return Fraction(1), base
    legs, why = case.conversion(base, reporting)
    if legs is None:
        run.answer.not_evaluated.append(Unevaluated(account, "", key, why, reporting))
        return None
    _read_legs(case, legs)
    return _product(legs), reporting


def _read(case: _Case, valued: _Valued) -> None:
    """What a valued position read, for the provenance: its datasets, its
    own price (ruling 460) and its conversion legs (ruling 462)."""
    for price, _ in valued.factors:
        if price.dataset:
            case.datasets.add(price.dataset)
    if valued.own is not None:
        case.input_prices.setdefault(valued.own.subject_id, valued.own)
    _read_legs(case, valued.legs)


def _read_legs(case: _Case, legs: Iterable[_Leg]) -> None:
    for leg in legs:
        for price, _ in leg.factors:
            if price.dataset:
                case.datasets.add(price.dataset)
        case.legs.setdefault((leg.from_id, leg.to_id, leg.derivation, leg.via), leg)
        _read_legs(case, leg.subs)


def _concentration(run: _Run, ref: Mapping[str, Any], definition: Definition) -> None:
    case, key = run.case, _measure_key(ref)
    for account in case.account_ids:
        base = case.bases[account]
        for scenario in _scenarios(case, account):
            by: dict[str, Fraction] = {}
            for position in _positions(case, account, scenario):
                valued, why, detail = _value(case, position.instrument_id, base)
                if valued is None:
                    if scenario == BASE:
                        run.answer.not_evaluated.append(
                            Unevaluated(account, position.instrument_id, key, why, detail)
                        )
                    continue
                _read(case, valued)
                by[position.instrument_id] = by.get(position.instrument_id, Fraction(0)) + (
                    valued.per_unit * Fraction(position.quantity)
                )
            whole = (
                sum(by.values(), Fraction(0))
                if CONCENTRATION_DENOMINATOR == "account_market_value"
                else sum((abs(v) for v in by.values()), Fraction(0))
            )
            total = round_half_even(whole, definition.scale)
            for instrument, worth in sorted(by.items()):
                run.answer.figures.append(
                    AnswerFigure(
                        measure=key,
                        account_id=account,
                        breakdown=(("instrument", instrument),),
                        scenario=(scenario, "", ""),
                        numerator=round_half_even(worth, definition.scale),
                        denominator=total,
                    )
                )


def _group(case: _Case, key: Key) -> _Group:
    group = case.groups.get(key[2])
    if group is None:
        raise ValueError(f"{key[0]} names event group {key[2]!r}, and the case holds none")
    case.read_groups.add(group.event_group_id)
    for member in group.members:
        if member in case.instruments:
            case.read_instruments.add(member)
    return group


def _member_price(
    case: _Case, member: str, threshold: Decimal
) -> tuple[Decimal | None, str, list[_Price]]:
    bid, ask, last = (case.price(member, kind) for kind in ("bid", "ask", "last"))
    if bid is not None and ask is not None and ask.amount - bid.amount <= threshold:
        with localcontext() as context:
            context.prec = 100
            mid = (bid.amount + ask.amount) / 2
        return mid, bid.instrument_id, [bid, ask]
    if last is not None:
        return last.amount, last.instrument_id, [last]
    return None, "", []


def _implied_distribution(run: _Run, ref: Mapping[str, Any], definition: Definition) -> None:
    case, key = run.case, _measure_key(ref)
    group = _group(case, key)
    threshold = _d(definition.parameter("spread_threshold"))
    prices: list[tuple[str, Decimal]] = []
    cash: set[str] = set()
    missing = False
    for member in group.members:
        price, held, read = _member_price(case, member, threshold)
        if price is None:
            run.answer.not_evaluated.append(Unevaluated("", member, key, PRICE_MISSING, ""))
            missing = True
            continue
        for each in read:
            if each.dataset:
                case.datasets.add(each.dataset)
        cash.add(held)
        prices.append((member, price))
    if missing:
        return
    if len(cash) > 1:
        run.answer.not_evaluated.append(
            Unevaluated(
                "", "", key, CONVERSION_MISSING, "the members' prices are in different cash"
            )
        )
        return
    currency = cash.pop() if cash else ""
    total = sum((p for _, p in prices), Decimal(0))
    run.answer.figures.append(
        AnswerFigure(
            measure=key,
            account_id="",
            breakdown=(),
            scenario=(BASE, "", ""),
            value=round_half_even(total, definition.scale),
            currency_instrument_id=currency,
        )
    )
    exhaustive = group.exhaustive == FLAG_TRUE
    if not exhaustive:
        run.answer.not_evaluated.append(Unevaluated("", "", key, GROUP_NOT_EXHAUSTIVE, ""))
    for member, price in prices:
        if exhaustive:
            figure = AnswerFigure(
                measure=key,
                account_id="",
                breakdown=(),
                scenario=(OUTCOME, "", member),
                numerator=round_half_even(price, definition.scale),
                denominator=round_half_even(total, definition.scale),
            )
        else:
            figure = AnswerFigure(
                measure=key,
                account_id="",
                breakdown=(),
                scenario=(OUTCOME, "", member),
                value=round_half_even(price, definition.scale),
                currency_instrument_id=currency,
            )
        run.answer.figures.append(figure)


def _payoffs(
    case: _Case, group: _Group, positions: Sequence[_Position], base: str
) -> tuple[list[tuple[tuple[str, str, str], Fraction]] | None, list[tuple[str, str, str]]]:
    """Each resolution scenario's payoff over `positions` in the group's
    members, or None and each position's reason."""
    held = [p for p in positions if p.instrument_id in group.members]
    terms: list[tuple[_Position, Fraction]] = []
    failed: list[tuple[str, str, str]] = []
    for position in held:
        record = case.instruments.get(position.instrument_id)
        if position.instrument_id.startswith("LCL-") or record is None:
            failed.append((position.instrument_id, LOCAL_RECORD, "local record: not priced"))
            continue
        if record.payout is None:
            raise ValueError(f"{position.instrument_id} is in a group and states no payout")
        legs, why = case.conversion(record.payout[1], base)
        if legs is None:
            failed.append((position.instrument_id, why, ""))
            continue
        if position.cost is None:
            failed.append((position.instrument_id, COST_MISSING, ""))
            continue
        _read_legs(case, legs)
        terms.append((position, Fraction(record.payout[0]) * _product(legs)))
    if failed:
        return None, failed
    scenarios: list[tuple[str, str, str]] = [(OUTCOME, "", m) for m in group.members]
    if group.mutually_exclusive == FLAG_TRUE and group.exhaustive != FLAG_TRUE:
        scenarios.append((NONE_OF_THE_NAMED, "", ""))
    out = []
    for scenario in scenarios:
        total = Fraction(0)
        for position, paid in terms:
            pays = scenario[0] == OUTCOME and scenario[2] == position.instrument_id
            total += Fraction(position.quantity) * (paid if pays else 0) - Fraction(
                position.cost or 0
            )
        out.append((scenario, total))
    return out, []


def _resolution_payoff(run: _Run, ref: Mapping[str, Any], definition: Definition) -> None:
    case, key = run.case, _measure_key(ref)
    group = _group(case, key)
    for account in case.account_ids:
        base = case.bases[account]
        positions = [p for p in case.positions if p.account_id == account]
        if not any(p.instrument_id in group.members for p in positions):
            continue
        reported = _reporting(run, account, key)
        if reported is None:
            continue
        rate, currency = reported
        payoffs, failed = _payoffs(case, group, positions, base)
        if payoffs is None:
            for instrument, why, detail in failed:
                run.answer.not_evaluated.append(
                    Unevaluated(account, instrument, key, why, detail)
                )
            continue
        for scenario, total in payoffs:
            run.answer.figures.append(
                AnswerFigure(
                    measure=key,
                    account_id=account,
                    breakdown=(),
                    scenario=scenario,
                    value=round_half_even(total * rate, definition.scale),
                    currency_instrument_id=currency,
                )
            )


def _series(case: _Case, subject: str, dates: Sequence[str]) -> list[Decimal] | None:
    """The closes of `subject` over `dates`, a missing one carried forward
    at most `MOST_CARRIED` days running; None past that."""
    out: list[Decimal] = []
    carried = 0
    for day in dates:
        held = case.closes.get((subject, day))
        if held is None:
            if not out or carried == MOST_CARRIED:
                return None
            carried += 1
            out.append(out[-1])
        else:
            carried = 0
            out.append(held[0])
    return out


def _worst_resolution(
    case: _Case, positions: Sequence[_Position], base: str
) -> Fraction | None:
    """The account's event contracts' exact resolution worst case: each
    mutually exclusive group's least payoff, and each other contract's worse
    of paying and not; None where one cannot be valued."""
    events = [
        p
        for p in positions
        if (r := case.instruments.get(p.instrument_id)) is not None
        and r.model_id == "binary_event"
    ]
    if not events:
        return Fraction(0)
    worst = Fraction(0)
    done: set[str] = set()
    for group in sorted(case.groups.values(), key=lambda g: g.event_group_id):
        if group.mutually_exclusive != FLAG_TRUE:
            continue
        inside = [
            p
            for p in events
            if p.instrument_id in group.members and p.instrument_id not in done
        ]
        if not inside:
            continue
        payoffs, _ = _payoffs(case, group, inside, base)
        if payoffs is None:
            return None
        case.read_groups.add(group.event_group_id)
        worst += min(total for _, total in payoffs)
        done |= {p.instrument_id for p in inside}
    for position in events:
        if position.instrument_id in done:
            continue
        record = case.instruments[position.instrument_id]
        if record.payout is None or position.cost is None:
            return None
        legs, _ = case.conversion(record.payout[1], base)
        if legs is None:
            return None
        paid = Fraction(position.quantity) * Fraction(record.payout[0]) * _product(legs)
        worst += min(paid, Fraction(0)) - Fraction(position.cost)
    return worst


def _historical(run: _Run, ref: Mapping[str, Any], definition: Definition) -> None:
    """historical_var and expected_shortfall, by full revaluation."""
    case, key = run.case, _measure_key(ref)
    window = int(definition.parameter("window_days"))
    confidence = Fraction(_d(definition.parameter("confidence")))
    names = [str(b) for b in ref.get("breakdowns") or ()]
    unknown = [n for n in names if n not in definition.breakdowns]
    if unknown:
        for name in unknown:
            run.answer.not_evaluated.append(Unevaluated("", "", key, SCHEME_NOT_HELD, name))
        return
    if len(case.dates) < window + 1:
        run.answer.not_evaluated.append(
            Unevaluated("", "", key, HISTORY_INSUFFICIENT, f"{len(case.dates)} business dates")
        )
        return
    dates = case.dates[-(window + 1) :]
    for account in case.account_ids:
        base = case.bases[account]
        reported = _reporting(run, account, key)
        if reported is None:
            continue
        rate, currency = reported
        for scenario in _scenarios(case, account):
            groups: dict[tuple[tuple[str, str], ...], list[Fraction]] = {}
            positions = _positions(case, account, scenario)
            for position in positions:
                record = case.instruments.get(position.instrument_id)
                if record is not None and record.model_id == "binary_event":
                    case.read_instruments.add(position.instrument_id)
                    case.models.add((record.model_id, record.model_version))
                    continue
                valued, why, detail = _value(case, position.instrument_id, base)
                if valued is None:
                    if scenario == BASE:
                        run.answer.not_evaluated.append(
                            Unevaluated(account, position.instrument_id, key, why, detail)
                        )
                    continue
                group, missing = _breakdown_of(case, position, names)
                if group is None:
                    if scenario == BASE:
                        run.answer.not_evaluated.append(
                            Unevaluated(
                                account, position.instrument_id, key, SCHEME_NOT_HELD, missing
                            )
                        )
                    continue
                moves: list[list[Fraction]] = []
                short = False
                for each, exponent in valued.factors:
                    series = _series(case, each.subject_id, dates)
                    if series is None or any(v == 0 for v in series):
                        short = True
                        break
                    # An inverted leg moves inversely with its lake price.
                    moves.append(
                        [
                            (Fraction(series[i]) / Fraction(series[i - 1])) ** exponent
                            for i in range(1, len(series))
                        ]
                    )
                if short:
                    if scenario == BASE:
                        run.answer.not_evaluated.append(
                            Unevaluated(
                                account, position.instrument_id, key, HISTORY_INSUFFICIENT, ""
                            )
                        )
                    continue
                _read(case, valued)
                now = valued.per_unit * Fraction(position.quantity)
                pnl = groups.setdefault(group, [Fraction(0)] * window)
                for day in range(window):
                    shocked = now
                    for series_moves in moves:
                        shocked *= series_moves[day]
                    pnl[day] += shocked - now
            if not groups and not names:
                groups[()] = [Fraction(0)] * window
            for group, pnl in sorted(groups.items()):
                ordered = sorted(pnl)
                k = max(1, math.floor(len(ordered) * (1 - confidence)))
                if definition.definition == "historical_var":
                    figure: Fraction = -ordered[k - 1]
                else:
                    figure = -sum(ordered[:k], Fraction(0)) / k
                run.answer.figures.append(
                    AnswerFigure(
                        measure=key,
                        account_id=account,
                        breakdown=group,
                        scenario=(scenario, "", ""),
                        value=round_half_even(figure * rate, definition.scale),
                        currency_instrument_id=currency,
                    )
                )
            worst = _worst_resolution(case, positions, base)
            events = any(
                (r := case.instruments.get(p.instrument_id)) is not None
                and r.model_id == "binary_event"
                for p in positions
            )
            if events and worst is not None and not names and scenario == BASE:
                run.answer.figures.append(
                    AnswerFigure(
                        measure=key,
                        account_id=account,
                        breakdown=(),
                        scenario=(OUTCOME, "", ""),
                        value=round_half_even(-worst * rate, definition.scale),
                        currency_instrument_id=currency,
                    )
                )


# ── execution_cost, version 1 (contract v27; the gaps spec's C1 to C10) ──────

#: The benchmarks version 1 measures, each with the execution's moment it is
#: taken at; FIX and INTERVAL_VWAP need a fixing or trades, which a v1 job
#: does not read.
TCA_MOMENTS = (
    ("TCA_BENCHMARK_DECISION", "decision_at_ns"),
    ("TCA_BENCHMARK_ARRIVAL", "arrival_at_ns"),
    ("TCA_BENCHMARK_PLACEMENT_ARRIVAL", "placement_arrival_at_ns"),
    ("TCA_BENCHMARK_MID_AT_FILL", "executed_at_ns"),
)
#: The quote's staleness bound by default (C4): 5 seconds.
TCA_STALENESS_BOUND_NS = 5_000_000_000
NO_QUOTE, NOT_MEASURED = "TCA_UNANSWERED_NO_QUOTE", "TCA_UNANSWERED_NOT_MEASURED"


def _money_json(amount: Decimal, instrument_id: str) -> dict[str, str]:
    return {"amount": decimal_text(amount), "instrument_id": instrument_id}


def _bps(value: Fraction) -> Decimal:
    return round_half_even(value * 10_000, 4)


def _execution_cost(run: _Run, ref: Mapping[str, Any], definition: Definition) -> None:
    """execution_cost v1: each execution of the job's accounts against each
    benchmark it is measured by, in bps, side-adjusted, positive a cost --
    s × (price − benchmark) ÷ benchmark × 10⁴ (C3) -- against the mid in
    force at the benchmark's moment within the staleness bound, never an
    imputed value (C4); fees and financing apart in bps of notional. Each
    row is the lake's `ExecutionCost`; the figures are each account's
    notional-weighted mean per benchmark, in its base (or the job's
    reporting currency)."""
    case, key = run.case, _measure_key(ref)
    bound_default = int(case.inputs.get("tca_staleness_bound_ns") or TCA_STALENESS_BOUND_NS)
    for account in case.account_ids:
        base = case.bases[account]
        reported = _reporting(run, account, key)
        if reported is None:
            continue
        rate, _currency = reported
        weighted: dict[str, tuple[Fraction, Fraction]] = {}
        for execution in case.executions:
            if execution["account_id"] != account:
                continue
            price = _d(execution["price"]["amount"])
            held = execution["price"]["instrument_id"]
            quantity = _d(execution["quantity"])
            notional = price * quantity
            sign = 1 if execution["side"] == "SIDE_BUY" else -1
            legs, _ = case.conversion(held, base)
            in_base = None if legs is None else Fraction(notional) * _product(legs) * rate
            if legs is not None:
                _read_legs(case, legs)
            charges = {}
            for name in ("fees", "financing"):
                charge = execution.get(name)
                charges[name] = (
                    None
                    if not charge or notional == 0
                    else _bps(Fraction(_d(charge["amount"])) / Fraction(notional))
                )
            for benchmark, moment_name in TCA_MOMENTS:
                moment = int(execution.get(moment_name) or 0)
                quotes = [
                    q
                    for q in case.market.get((execution["instrument_id"], "mid"), [])
                    if q.instrument_id == held and q.valid_at_ns <= moment
                ]
                quote = (
                    max(quotes, key=lambda q: (q.valid_at_ns, q.dataset)) if quotes else None
                )
                bound = bound_default
                if quote is not None and quote.dataset in case.stale_after:
                    bound = min(bound, case.stale_after[quote.dataset])
                unanswered = ""
                if moment == 0:
                    unanswered = NOT_MEASURED
                elif quote is None or moment - quote.valid_at_ns > bound or quote.amount == 0:
                    unanswered = NO_QUOTE
                cost = None
                if not unanswered and quote is not None:
                    case.datasets.add(quote.dataset)
                    exact = (
                        sign
                        * (Fraction(price) - Fraction(quote.amount))
                        / Fraction(quote.amount)
                    )
                    cost = _bps(exact)
                    if in_base is not None:
                        total, weight = weighted.get(benchmark, (Fraction(0), Fraction(0)))
                        weighted[benchmark] = (
                            total + exact * 10_000 * in_base,
                            weight + in_base,
                        )
                run.answer.execution_costs.append(
                    {
                        "execution_id": execution["execution_id"],
                        "order_id": execution.get("order_id", ""),
                        "placement_id": execution.get("placement_id", ""),
                        "account_id": account,
                        "benchmark": benchmark,
                        "benchmark_price": None
                        if unanswered or quote is None
                        else _money_json(quote.amount, quote.instrument_id),
                        "benchmark_at_ns": str(0 if unanswered == NOT_MEASURED else moment),
                        "benchmark_dataset": ""
                        if unanswered or quote is None
                        else quote.dataset,
                        "benchmark_row_key": ""
                        if unanswered or quote is None
                        else quote.row_key,
                        "execution_price": _money_json(price, held),
                        "side": execution["side"],
                        "notional": _money_json(notional, held),
                        "cost_bps": None if cost is None else decimal_text(cost),
                        "fees_bps": None
                        if charges["fees"] is None
                        else decimal_text(charges["fees"]),
                        "financing_bps": None
                        if charges["financing"] is None
                        else decimal_text(charges["financing"]),
                        "liquidity_indicator": execution.get("liquidity_indicator", ""),
                        "venue_id": execution.get("venue_id", ""),
                        "unanswered": unanswered,
                        "staleness_bound_ns": str(bound),
                        "time_precision": execution.get("time_precision", ""),
                        "reject_count": int(execution.get("reject_count") or 0),
                        "time_to_fill_ns": str(int(execution.get("time_to_fill_ns") or 0)),
                    }
                )
        for benchmark, _ in TCA_MOMENTS:
            if benchmark not in weighted or weighted[benchmark][1] == 0:
                continue
            total, weight = weighted[benchmark]
            run.answer.figures.append(
                AnswerFigure(
                    measure=key,
                    account_id=account,
                    breakdown=(("benchmark", benchmark),),
                    scenario=(BASE, "", ""),
                    value=round_half_even(total / weight, definition.scale),
                )
            )
    run.answer.execution_costs.sort(
        key=lambda r: (r["execution_id"], [b for b, _ in TCA_MOMENTS].index(r["benchmark"]))
    )


_MEASURES = {
    "execution_cost": _execution_cost,
    "market_value": _linear,
    "exposure": _linear,
    "pnl": _linear,
    "concentration": _concentration,
    "historical_var": _historical,
    "expected_shortfall": _historical,
    "resolution_payoff": _resolution_payoff,
    "implied_distribution": _implied_distribution,
}


def compute(inputs: Mapping[str, Any]) -> Answer:
    """The reference answer to a case's `inputs`: every measure the job
    names, in its order, and the provenance with the answer's hash."""
    case = _Case(inputs)
    run = _Run(case, Answer())
    for ref in case.measures:
        key = _measure_key(ref)
        definition = definition_of(key[0], key[1])
        if definition is None:
            raise ValueError(f"the reference holds no definition {key[0]} v{key[1]}")
        before = len(run.answer.figures)
        unevaluated = len(run.answer.not_evaluated)
        if key[0] == "execution_cost":
            run.answer.asks_execution_cost = True
        _MEASURES[key[0]](run, ref, definition)
        run.answer.not_evaluated[unevaluated:] = sorted(
            run.answer.not_evaluated[unevaluated:],
            key=lambda u: (u.account_id, u.instrument_id, u.reason, u.detail),
        )
        # Within one measure, figures by account, breakdown and scenario.
        run.answer.figures[before:] = sorted(
            run.answer.figures[before:],
            key=lambda f: (
                f.account_id,
                f.breakdown,
                _SCENARIO_ORDER.get(f.scenario[0], 9),
                f.scenario,
            ),
        )
    run.answer.provenance = {
        "book_watermark": list(inputs.get("book_watermark") or []),
        "business_date": case.business_date,
        "lake_as_of_ns": str(case.lake_as_of_ns),
        "datasets": sorted(case.datasets),
        "instruments": [
            {
                "instrument_id": i.instrument_id,
                "record_version": i.record_version,
                "template_id": i.template_id,
                "template_version": i.template_version,
                "calculation_version": i.calculation_version,
            }
            for i in sorted(
                (case.instruments[x] for x in case.read_instruments if x in case.instruments),
                key=lambda i: i.instrument_id,
            )
        ],
        "models": [
            {
                "model_id": model,
                "model_version": version,
                "implementation": BUILT_IN,
                "implementation_version": case.engine_version,
            }
            for model, version in sorted(case.models)
        ],
        "measures": _unique_measures(case.measures),
        "event_groups": [
            {"event_group_id": g, "version": case.groups[g].version}
            for g in sorted(case.read_groups)
        ],
        "routing_version": str(inputs.get("routing_version", "0")),
        "engine_version": case.engine_version,
        "answer_hash": answer_hash(inputs),
        "input_prices": [
            {
                "instrument_id": instrument,
                "price": {
                    "amount": decimal_text(price.amount),
                    "instrument_id": price.instrument_id,
                },
                "dataset": price.dataset,
                "row_key": price.row_key,
                "version": str(price.version),
                "source_ns": str(price.source_ns),
            }
            for instrument, price in sorted(case.input_prices.items())
        ],
        "conversion_legs": [
            case.legs[k].to_json()
            for k in sorted(case.legs, key=lambda k: (k[0], k[1], _DERIVATION_RANK[k[2]], k[3]))
        ],
    }
    return run.answer


_SCENARIO_ORDER = {BASE: 0, WHAT_IF: 1, HISTORICAL_DAY: 2, OUTCOME: 3, NONE_OF_THE_NAMED: 4}


def _unique_measures(refs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []
    for ref in refs:
        held = {"definition": str(ref["definition"]), "version": int(ref.get("version", 1))}
        if held not in seen:
            seen.append(held)
    return seen


def load(path: str | Path) -> dict[str, Any]:
    """A reference case from its file: canonical JSON, refused where it is
    not exactly its own canonical form, so a case is pinned byte for byte."""
    raw = Path(path).read_bytes()
    case: dict[str, Any] = json.loads(raw)
    if canonical(case) != raw.rstrip(b"\n"):
        raise ValueError(f"{path} is not in RFC 8785 canonical form")
    return case
