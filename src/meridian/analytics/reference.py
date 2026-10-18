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
  "cost", "sleeve"}]`, each lot the book closed up to its watermark, its
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
- `pnl`: per bucket, two figures under the breakdown `component`:
  `unrealized`, Σ (quantity × value per unit − the open lots' cost), and
  `realized`, Σ (a closed lot's proceeds − its cost) over the lots the book
  closed up to its watermark (ruling 301; v26's job names no period, so
  version 1 fixes it).
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
    "MODELS",
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
#: proceeds less their cost, to the book's watermark).
COMPONENT = "component"
COMPONENTS: Mapping[str, tuple[str, ...]] = {
    "exposure": ("gross", "net"),
    "pnl": ("unrealized", "realized"),
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
            (
                ("unrealized", "market_value_less_open_lots_cost"),
                ("realized", "closed_lots_proceeds_less_cost_to_the_watermark"),
            ),
            _BY,
            2,
            "Each bucket's unrealized P&L (open lots) and realized P&L (closed lots)",
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
    )
}

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
    cost: Decimal
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

    @property
    def answer_hash(self) -> str:
        return str(self.provenance["answer_hash"])

    def to_json(self) -> dict[str, Any]:
        """The answer as a reference case's `answer` holds it."""
        return {
            "figures": [each.to_json() for each in self.figures],
            "not_evaluated": [each.to_json() for each in self.not_evaluated],
            "provenance": self.provenance,
        }


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
                cost=_d(c["cost"]),
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
        # What the answer read, for its provenance.
        self.datasets: set[str] = set()
        self.read_instruments: set[str] = set()
        self.models: set[tuple[str, int]] = set()
        self.read_groups: set[str] = set()

    # ── Market objects ───────────────────────────────────────────────────

    def price(self, subject: str, kind: str) -> _Price | None:
        held = self.market.get((subject, kind)) or []
        # One row per subject and kind at the as-of; the latest valid where a
        # case states more.
        return max(held, key=lambda p: (p.valid_at_ns, p.dataset)) if held else None

    def stale(self, price: _Price) -> bool:
        limit = self.stale_after.get(price.dataset)
        return limit is not None and self.lake_as_of_ns - price.valid_at_ns > limit

    def conversion(self, held: str, base: str) -> tuple[list[_Price], str] | tuple[None, str]:
        """The legs from `held` to `base`, or None and why."""
        if held == base:
            return [], ""
        chains: list[tuple[tuple[int, ...], tuple[str, ...], list[_Price]]] = []

        def walk(at: str, legs: list[_Price], seen: frozenset[str]) -> None:
            if at == base:
                ranks = tuple(CONVERSION_KINDS.index(p.kind) for p in legs)
                chains.append((ranks, tuple(p.instrument_id for p in legs), list(legs)))
                return
            if len(legs) == MOST_LEGS:
                return
            for kind in CONVERSION_KINDS:
                leg = self.price(at, kind)
                if leg is None or leg.instrument_id in seen:
                    continue
                walk(leg.instrument_id, [*legs, leg], seen | {leg.instrument_id})

        walk(held, [], frozenset({held}))
        if not chains:
            return None, CONVERSION_MISSING
        chains.sort(key=lambda c: (len(c[2]), c[0], c[1]))
        legs = chains[0][2]
        for leg in legs:
            if self.stale(leg):
                return None, PRICE_STALE
        return legs, ""


# ── The models ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Valued:
    """A position's value per unit in its base, the market objects it read,
    and how its scenarios move them."""

    per_unit: Fraction
    objects: tuple[_Price, ...]


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
        return _Valued(_product(legs), tuple(legs)), "", ""
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
            return (
                _Valued(Fraction(outcome.settlement_value) * _product(legs), tuple(legs)),
                "",
                "",
            )
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
    return _Valued(Fraction(price.amount) * _product(legs), (price, *legs)), "", ""


def _product(legs: Iterable[_Price]) -> Fraction:
    out = Fraction(1)
    for leg in legs:
        out *= Fraction(leg.amount)
    return out


def value_per_unit(
    model_id: str, instrument_id: str, inputs: Sequence[Any]
) -> tuple[Decimal, str]:
    """A built-in model's value per unit for one pricing unit (W12.3), from
    exactly the market objects a batch carries: the instrument's own price
    (or, for `binary_event`, its `outcome` where one is carried), times each
    conversion leg the inputs hold from the currency in hand, until none
    leads further. The value and the cash instrument (or ISO 4217 code) it
    is in. `inputs` are `(subject_id, kind, amount, instrument_id or code)`
    tuples."""
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
    components = COMPONENTS.get(definition.definition, ("",))
    for account in case.account_ids:
        base = case.bases[account]
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
                    add(group, "unrealized", _unrealized(position, worth))
                else:
                    add(group, "", worth)
            if definition.definition == "pnl":
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
                                held.get(component, Fraction(0)), definition.scale
                            ),
                            currency_instrument_id=base,
                        )
                    )


def _unrealized(position: _Position, worth: Fraction) -> Fraction:
    """One open position's unrealized P&L: its market value less its open
    lots' cost."""
    if position.cost is None:
        raise ValueError(
            f"pnl asks {position.instrument_id}'s lots' cost, and the case states none"
        )
    return worth - Fraction(position.cost)


def _read(case: _Case, valued: _Valued) -> None:
    for each in valued.objects:
        if each.dataset:
            case.datasets.add(each.dataset)


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
        for leg in legs:
            if leg.dataset:
                case.datasets.add(leg.dataset)
        if position.cost is None:
            raise ValueError(f"{position.instrument_id}'s payoff needs its lots' cost")
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
                    value=round_half_even(total, definition.scale),
                    currency_instrument_id=base,
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
                for each in valued.objects:
                    series = _series(case, each.subject_id, dates)
                    if series is None or any(v == 0 for v in series[:-1]):
                        short = True
                        break
                    moves.append(
                        [
                            Fraction(series[i]) / Fraction(series[i - 1])
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
                        value=round_half_even(figure, definition.scale),
                        currency_instrument_id=base,
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
                        value=round_half_even(-worst, definition.scale),
                        currency_instrument_id=base,
                    )
                )


_MEASURES = {
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
        definition = DEFINITIONS.get(key[0])
        if definition is None or definition.version != key[1]:
            raise ValueError(f"the reference holds no definition {key[0]} v{key[1]}")
        before = len(run.answer.figures)
        unevaluated = len(run.answer.not_evaluated)
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
