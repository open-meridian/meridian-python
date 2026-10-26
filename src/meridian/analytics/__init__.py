"""The analytics component's API, for a plugin that asks it (contract v26;
W12; spec/the-analytics-engine-answers-behind-one-api, Q1 to Q20, and
spec/the-analytics-engines-first-release, both accepted).

Every analytic question is a job, answered inline or later; the component
decides by its size (Q5). A job names its inputs by reference -- the book at
one watermark, the lake at one as-of under one source choice -- and every
answer names what it was computed from, with a hash: two answers with the
same hash are the same answer. Submitting a job is a read, at the client's
role (`reporting`, `portfolio`, `compliance` and `signal`).

**Typed builders** (Q1: no text syntax). A job is composed as values, each
checked as it is built, and is the wire's `Job` when done:

    from meridian import analytics

    job = analytics.job(
        analytics.measure("exposure", by=["asset_class", "currency"]),
        analytics.measure("historical_var"),
        accounts=["ACC-12"],
    )
    answer = await analytics.Jobs().run(plugin, job)        # inline, or waited for
    for figure in answer.figures("exposure"):
        print(figure.breakdown, figure.value, figure.currency_instrument_id)

A what-if adds trades to one account (W12.5), answered beside the base:

    job = analytics.job(analytics.measure("market_value"), accounts=["ACC-12"],
                        what_if=analytics.what_if("ACC-12",
                            analytics.trade("INS-...", "buy", Decimal("10"))))

An event measure names its group: `measure("implied_distribution",
event_group="EVG-...")`.

**Reading an answer** (`Answer`): each figure as `JobFigure` -- its value, or
for a weight its numerator and denominator (`compare` decides a bound by
cross-multiplication, never by a rounded division) -- its scenario key and
how it was computed. A figure's `computed_as` is exact in v26, model from
v28; a reader handles both from now (the first release's Q14), and reads an
unset one as exact. A scenario key's kind unset is the base. What was not
evaluated is listed with why, never as a zero.

**Waiting for one answered later** (`Jobs`): a job the component answers
later finishes on `job_finished`, heard by the instance that ran it alone,
and caught up by sequence (`list_finished_jobs`) after a loss; its answer is
read by its ID (`read_job_answer`) while the component still caches it, and
run again when it is not (Q12).

**The reference computations** v26's engine must equal exactly, hashes
included, are `meridian.analytics.reference` (requirement 36).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any

from ..client import SCHEMA_VERSION
from ..operations import Job, Money, WhatIf, WhatIfTrade, _decimal, as_decimal
from ..plugin.v1 import operations_pb2 as ops
from ..receive import Heard
from ._canonical import answer_hash, canonical, decimal_text

__all__ = [
    "EVENT_MEASURES",
    "SERVED_VERSIONS",
    "STANDARD_MEASURES",
    "Answer",
    "JobFigure",
    "Jobs",
    "answer_hash",
    "answer_json",
    "answer_message",
    "canonical",
    "job",
    "measure",
    "measures_of",
    "trade",
    "what_if",
]

#: The standard measure definitions: v26's eight (the v26 plan's question
#: 226) and from contract v27 `execution_cost` (W12.1, the gaps spec's C).
STANDARD_MEASURES = (
    "market_value",
    "exposure",
    "concentration",
    "pnl",
    "historical_var",
    "expected_shortfall",
    "resolution_payoff",
    "implied_distribution",
    "execution_cost",
)
#: The latest version of each standard definition the component serves:
#: from contract v27 `pnl` version 2, realized P&L beside unrealized
#: (rulings 320 and 396), version 1 still served; a later one is refused as
#: a job is built.
SERVED_VERSIONS = {name: 1 for name in STANDARD_MEASURES} | {"pnl": 2}
#: The definitions over an event group, which name it.
EVENT_MEASURES = frozenset({"resolution_payoff", "implied_distribution"})
#: The breakdowns a standard definition may allow; a scheme the deployment
#: holds is named by its own name (requirement 17).
BREAKDOWNS = ("account", "asset_class", "currency", "instrument", "sleeve", "country")


def measure(
    definition: str, version: int = 1, *, by: Sequence[str] = (), event_group: str = ""
) -> ops.MeasureRef:
    """A measure by definition and version (requirement 14), broken down by
    `by`; an event measure (`resolution_payoff`, `implied_distribution`)
    names its event group, and no other names one. Refused as it is built:
    no definition, a version below 1, a breakdown named twice."""
    if not definition or definition != definition.strip():
        raise ValueError(f"a measure names its definition, not {definition!r}")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError(f"{definition}'s version is 1 or more, not {version!r}")
    names = [str(b) for b in by]
    twice = sorted({b for b in names if names.count(b) > 1})
    if twice:
        raise ValueError(f"{definition} is broken down by {', '.join(twice)} twice")
    if any(not b.strip() for b in names):
        raise ValueError(f"{definition} names an empty breakdown")
    served = SERVED_VERSIONS.get(definition)
    if served is not None and version > served:
        raise ValueError(
            f"{definition} v{version} is not served in contract {SCHEMA_VERSION};"
            f" up to v{served} is"
        )
    if definition in EVENT_MEASURES and not event_group:
        raise ValueError(f"{definition} is over an event group, and names none")
    if event_group and definition in STANDARD_MEASURES and definition not in EVENT_MEASURES:
        raise ValueError(f"{definition} is not over an event group; it names {event_group}")
    return ops.MeasureRef(
        definition=definition, version=version, breakdowns=names, event_group_id=event_group
    )


def trade(
    instrument_id: str,
    side: ops.Side | str,
    quantity: Decimal | int,
    price: Money | None = None,
) -> WhatIfTrade:
    """A trade added for a what-if (W12.5): bought or sold (`buy`, `sell`, or
    the Side's name), a quantity above zero, at an assumed price or, with
    none, the price at the job's as-of."""
    if not instrument_id:
        raise ValueError("a what-if trade names its instrument")
    if isinstance(quantity, bool) or not isinstance(quantity, Decimal | int) or quantity <= 0:
        raise ValueError(f"a what-if trade's quantity is above zero, not {quantity!r}")
    return WhatIfTrade(instrument_id=instrument_id, side=side, quantity=quantity, price=price)


def what_if(account_id: str, *trades: WhatIfTrade) -> WhatIf:
    """Trades added to one account's positions (W12.5): never a book record
    unless proposed. At least one."""
    if not account_id:
        raise ValueError("a what-if names its account")
    if not trades:
        raise ValueError("a what-if adds at least one trade")
    return WhatIf(account_id=account_id, trades=trades)


def job(
    *measures: ops.MeasureRef,
    accounts: Sequence[str] = (),
    book_at: ops.Watermark | None = None,
    lake_as_of_ns: int = 0,
    sources: ops.SourceChoice | None = None,
    what_if: WhatIf | None = None,
    business_date: str = "",
    reporting_currency: str = "",
) -> Job:
    """A job (W12.1): its measures, the accounts it is over, and its inputs by
    reference -- the book's watermark (none for now), the lake's as-of (0
    for now) and its source choice (none for the deployment's default);
    from contract v27 a business date (ISO 8601, the book at that date's end
    and the lake at its closes; ruling 458) in place of both, and a
    reporting currency by its cash instrument's `INS-` ID (ruling 459).
    Refused as it is built, as the component refuses it: no account (a job
    is over one account or more), an account empty or twice, no measure, a
    measure twice, a what-if on an account the job is not over, or a
    business date beside a watermark or an as-of."""
    if not measures:
        raise ValueError("a job asks at least one measure")
    seen: list[tuple[str, int, tuple[str, ...], str]] = []
    for each in measures:
        if not isinstance(each, ops.MeasureRef):
            raise TypeError(
                f"a job's measures are analytics.measure(...), not {type(each).__name__}"
            )
        held = (each.definition, each.version, tuple(each.breakdowns), each.event_group_id)
        if held in seen:
            raise ValueError(f"{each.definition} v{each.version} is asked twice")
        seen.append(held)
    named = list(accounts)
    twice = sorted({a for a in named if named.count(a) > 1})
    if twice:
        raise ValueError(f"the job names {', '.join(twice)} twice")
    if not named:
        raise ValueError("a job is over one account or more, and this names none")
    for i, account in enumerate(named):
        if not account:
            raise ValueError(f"the job's account {i} is empty")
    if business_date and (book_at is not None or lake_as_of_ns):
        raise ValueError(
            "a job for a business date reads the book at its end and the lake at its "
            "closes; it names no watermark and no as-of beside it"
        )
    if what_if is not None and what_if.account_id not in named:
        raise ValueError(f"the what-if's account {what_if.account_id} is not among the job's")
    return Job(
        account_ids=named,
        inputs=ops.InputRefs(book_at=book_at, lake_as_of_ns=lake_as_of_ns, sources=sources),
        measures=list(measures),
        what_if=what_if,
        business_date=business_date,
        reporting_currency=reporting_currency,
    )


# ── Reading an answer ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class JobFigure:
    """One figure of an answer, read: its measure, account, breakdown and
    scenario, its value or a weight's two parts, and how it was computed."""

    definition: str
    version: int
    event_group_id: str
    account_id: str
    breakdown: tuple[tuple[str, str], ...]
    #: The scenario's kind by its name, an unset one read as the base.
    scenario: str
    business_date: str
    outcome_instrument_id: str
    value: Decimal | None
    numerator: Decimal | None
    denominator: Decimal | None
    currency_instrument_id: str
    #: `exact` or `model`; an unset one read as exact (Q14), a value a
    #: later contract adds read as model, never as exact.
    computed_as: str

    @property
    def exact(self) -> bool:
        return self.computed_as == "exact"

    @property
    def weight(self) -> Fraction | None:
        """A weight as an exact fraction; None for a value, or a weight of
        nothing (a denominator of zero)."""
        if self.numerator is None or self.denominator is None or self.denominator == 0:
            return None
        return Fraction(self.numerator) / Fraction(self.denominator)

    def compare(self, bound: Decimal) -> int:
        """-1, 0 or 1 as the figure is below, at or above `bound`: a weight by
        cross-multiplication (requirement 5), a value directly."""
        if self.value is not None:
            left, right = Fraction(self.value), Fraction(bound)
        elif self.numerator is not None and self.denominator is not None:
            sign = -1 if self.denominator < 0 else 1
            left = Fraction(self.numerator) * sign
            right = Fraction(bound) * Fraction(self.denominator) * sign
        else:
            raise ValueError("the figure holds neither a value nor a weight")
        return (left > right) - (left < right)


def _read(figure: ops.Figure) -> JobFigure:
    # Q14: unset is read as exact; any value a later contract adds is read as
    # a model's, never as exact.
    exact = figure.computed_as in (ops.COMPUTED_AS_UNSPECIFIED, ops.COMPUTED_AS_EXACT)
    key = figure.scenario_key
    known = key.kind in ops.ScenarioKind.values() and key.kind != ops.SCENARIO_KIND_UNSPECIFIED
    scenario = ops.ScenarioKind.Name(key.kind) if known else "SCENARIO_KIND_BASE"
    return JobFigure(
        definition=figure.measure.definition,
        version=int(figure.measure.version),
        event_group_id=figure.measure.event_group_id,
        account_id=figure.account_id,
        breakdown=tuple((b.breakdown, b.value) for b in figure.breakdown),
        scenario=scenario,
        business_date=key.business_date,
        outcome_instrument_id=key.outcome_instrument_id,
        value=as_decimal(figure.value) if figure.HasField("value") else None,
        numerator=as_decimal(figure.numerator) if figure.HasField("numerator") else None,
        denominator=as_decimal(figure.denominator) if figure.HasField("denominator") else None,
        currency_instrument_id=figure.currency_instrument_id,
        computed_as="exact" if exact else "model",
    )


class Answer:
    """A job's answer, read (W12.1, W12.4): its figures, what was not
    evaluated and why, and its provenance (requirement 4)."""

    def __init__(self, message: Any) -> None:
        #: The answer as the wire carried it: `RunJobResult.answer` or
        #: `ReadJobAnswerResult`.
        self.message = message
        self.job_id: str = str(message.job_id)
        self._figures = [_read(each) for each in message.figures]

    def figures(
        self,
        definition: str = "",
        *,
        account_id: str | None = None,
        scenario: str = "",
    ) -> list[JobFigure]:
        """The figures, narrowed to a definition, an account and a scenario
        kind (`base`, `what_if`, `historical_day`, `outcome`,
        `none_of_the_named`, or the kind's name) where given."""
        want = scenario.upper()
        if want and not want.startswith("SCENARIO_KIND_"):
            want = "SCENARIO_KIND_" + want
        return [
            f
            for f in self._figures
            if (not definition or f.definition == definition)
            and (account_id is None or f.account_id == account_id)
            and (not want or f.scenario == want)
        ]

    @property
    def not_evaluated(self) -> list[Any]:
        """Each position or measure not evaluated, with its reason: never a
        zero (requirement 9)."""
        return list(self.message.not_evaluated)

    @property
    def provenance(self) -> Any:
        return self.message.provenance

    @property
    def answer_hash(self) -> str:
        return str(self.message.provenance.answer_hash)


def _decimal_or_none(message: Any, name: str) -> str | None:
    return decimal_text(as_decimal(getattr(message, name))) if message.HasField(name) else None


def answer_json(message: Any) -> dict[str, Any]:
    """An answer as the wire carries it (`JobAnswer`, or its mirror
    `ReadJobAnswerResult`), in the reference cases' JSON words, so the
    component's answer to a reference case is compared with the case's
    `answer` whole (requirement 36): every number in its stated form, every
    enum by its name, the job's ID left out (the component's own)."""

    def ref(m: Any) -> dict[str, Any]:
        return {
            "definition": m.definition,
            "version": int(m.version),
            "breakdowns": list(m.breakdowns),
            "event_group_id": m.event_group_id,
        }

    figures = []
    for f in message.figures:
        figures.append(
            {
                "measure": ref(f.measure),
                "account_id": f.account_id,
                "breakdown": [
                    {"breakdown": b.breakdown, "value": b.value} for b in f.breakdown
                ],
                "scenario_key": {
                    "kind": ops.ScenarioKind.Name(
                        f.scenario_key.kind or ops.SCENARIO_KIND_BASE
                    ),
                    "business_date": f.scenario_key.business_date,
                    "outcome_instrument_id": f.scenario_key.outcome_instrument_id,
                },
                "currency_instrument_id": f.currency_instrument_id,
                "computed_as": ops.ComputedAs.Name(f.computed_as or ops.COMPUTED_AS_EXACT),
                "value": _decimal_or_none(f, "value"),
                "numerator": _decimal_or_none(f, "numerator"),
                "denominator": _decimal_or_none(f, "denominator"),
            }
        )
    p = message.provenance
    return {
        "figures": figures,
        "not_evaluated": [
            {
                "account_id": n.account_id,
                "instrument_id": n.instrument_id,
                "measure": ref(n.measure),
                "reason": ops.NotEvaluatedReason.Name(n.reason),
                "detail": n.detail,
            }
            for n in message.not_evaluated
        ],
        "provenance": {
            "book_watermark": [
                {"partition": s.partition, "sequence": str(s.sequence)}
                for s in p.book_watermark.partitions
            ],
            "lake_as_of_ns": str(p.lake_as_of_ns),
            "datasets": list(p.datasets),
            "instruments": [
                {
                    "instrument_id": i.instrument_id,
                    "record_version": str(i.record_version),
                    "template_id": i.template_id,
                    "template_version": i.template_version,
                    "calculation_version": i.calculation_version,
                }
                for i in p.instruments
            ],
            "models": [
                {
                    "model_id": m.model_id,
                    "model_version": int(m.model_version),
                    "implementation": m.implementation,
                    "implementation_version": m.implementation_version,
                }
                for m in p.models
            ],
            "measures": [
                {"definition": m.definition, "version": int(m.version)} for m in p.measures
            ],
            "event_groups": [
                {"event_group_id": g.event_group_id, "version": str(g.version)}
                for g in p.event_groups
            ],
            "routing_version": str(p.routing_version),
            "engine_version": p.engine_version,
            "answer_hash": p.answer_hash,
            "business_date": p.business_date,
            "input_prices": [
                {
                    "instrument_id": i.instrument_id,
                    "price": {
                        "amount": decimal_text(as_decimal(i.price.amount)),
                        "instrument_id": i.price.instrument_id,
                    },
                    "dataset": i.dataset,
                    "row_key": i.row_key,
                    "version": str(i.version),
                    "source_ns": str(i.source_ns),
                }
                for i in p.input_prices
            ],
            "conversion_legs": [
                {
                    "from_instrument_id": c.from_instrument_id,
                    "to_instrument_id": c.to_instrument_id,
                    "rate": decimal_text(as_decimal(c.rate)),
                    "derivation": ops.ConversionDerivation.Name(c.derivation),
                    "via_instrument_id": c.via_instrument_id,
                    "dataset": c.dataset,
                }
                for c in p.conversion_legs
            ],
        },
    }


def answer_message(answer: Mapping[str, Any]) -> ops.ReadJobAnswerResult:
    """A reference case's `answer` as the wire's mirror carries it, the
    inverse of `answer_json`."""

    def ref(m: Mapping[str, Any]) -> ops.MeasureRef:
        return ops.MeasureRef(
            definition=m["definition"],
            version=int(m["version"]),
            breakdowns=list(m.get("breakdowns") or ()),
            event_group_id=m["event_group_id"],
        )

    def number(text: str | None) -> ops.Decimal | None:
        return None if text is None else _decimal(Decimal(text), "figure")

    p = answer["provenance"]
    return ops.ReadJobAnswerResult(
        figures=[
            ops.Figure(
                measure=ref(f["measure"]),
                account_id=f["account_id"],
                breakdown=[ops.BreakdownValue(**b) for b in f["breakdown"]],
                scenario_key=ops.ScenarioKey(
                    kind=f["scenario_key"]["kind"],
                    business_date=f["scenario_key"]["business_date"],
                    outcome_instrument_id=f["scenario_key"]["outcome_instrument_id"],
                ),
                value=number(f["value"]),
                numerator=number(f["numerator"]),
                denominator=number(f["denominator"]),
                currency_instrument_id=f["currency_instrument_id"],
                computed_as=f["computed_as"],
            )
            for f in answer["figures"]
        ],
        not_evaluated=[
            ops.NotEvaluated(
                account_id=n["account_id"],
                instrument_id=n["instrument_id"],
                measure=ref(n["measure"]),
                reason=n["reason"],
                detail=n["detail"],
            )
            for n in answer["not_evaluated"]
        ],
        provenance=ops.AnswerProvenance(
            book_watermark=ops.Watermark(
                partitions=[
                    ops.PartitionSequence(partition=s["partition"], sequence=int(s["sequence"]))
                    for s in p["book_watermark"]
                ]
            ),
            lake_as_of_ns=int(p["lake_as_of_ns"]),
            datasets=p["datasets"],
            instruments=[
                ops.InstrumentInput(
                    instrument_id=i["instrument_id"],
                    record_version=int(i["record_version"] or 0),
                    template_id=i["template_id"],
                    template_version=i["template_version"],
                    calculation_version=i["calculation_version"],
                )
                for i in p["instruments"]
            ],
            models=[ops.ModelRef(**m) for m in p["models"]],
            measures=[ops.MeasureRef(**m) for m in p["measures"]],
            event_groups=[
                ops.EventGroupInput(
                    event_group_id=g["event_group_id"], version=int(g["version"])
                )
                for g in p["event_groups"]
            ],
            routing_version=int(p["routing_version"]),
            engine_version=p["engine_version"],
            answer_hash=p["answer_hash"],
            business_date=p.get("business_date", ""),
            input_prices=[
                ops.InputPrice(
                    instrument_id=i["instrument_id"],
                    price=ops.Money(
                        amount=_decimal(Decimal(i["price"]["amount"]), "input price"),
                        instrument_id=i["price"]["instrument_id"],
                    ),
                    dataset=i["dataset"],
                    row_key=i["row_key"],
                    version=int(i["version"]),
                    source_ns=int(i["source_ns"]),
                )
                for i in p.get("input_prices") or ()
            ],
            conversion_legs=[
                ops.ConversionLeg(
                    from_instrument_id=c["from_instrument_id"],
                    to_instrument_id=c["to_instrument_id"],
                    rate=_decimal(Decimal(c["rate"]), "conversion leg"),
                    derivation=c["derivation"],
                    via_instrument_id=c["via_instrument_id"],
                    dataset=c["dataset"],
                )
                for c in p.get("conversion_legs") or ()
            ],
        ),
    )


# ── Running a job ──────────────────────────────────────────────────────────


class Jobs:
    """A client's jobs: run one and have its answer, inline or once it
    finishes (W12.1, W12.4); the finished heard (`heard`) and caught up after
    a loss (`catch_up`), by sequence.

        jobs = analytics.Jobs()
        await plugin.receive(job_finished=jobs.heard, ...)   # beside its other rows
        answer = await jobs.run(plugin, job)

    `run` waits for a job answered later by the finishing heard, or, every
    `poll_seconds`, by reading the finished after the last sequence seen, at
    most `timeout_seconds`; then reads its answer. `sequence` is the last
    finishing seen."""

    def __init__(self, *, poll_seconds: float = 1.0, timeout_seconds: float = 300.0) -> None:
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds
        self.sequence = 0
        self.finished: dict[str, ops.JobFinishedEvent] = {}
        self._waiting: dict[str, asyncio.Event] = {}

    def apply(self, event: ops.JobFinishedEvent) -> bool:
        """One finishing, heard or read; whether it is new."""
        if not event.job_id or event.job_id in self.finished:
            return False
        held = ops.JobFinishedEvent()
        held.CopyFrom(event)
        self.finished[event.job_id] = held
        self.sequence = max(self.sequence, int(event.sequence))
        waiting = self._waiting.get(event.job_id)
        if waiting is not None:
            waiting.set()
        return True

    async def heard(self, heard: Heard[ops.JobFinishedEvent]) -> None:
        """A `receive` handler for the job-finished row."""
        self.apply(heard.message)

    async def catch_up(self, operations: Any) -> int:
        """Every finishing after the last seen, read until a read answers
        none (`list_finished_jobs`, W12.4); how many were new."""
        changed = 0
        after = self.sequence
        while True:
            page = await operations.list_finished_jobs(after_sequence=after)
            events = sorted(page.finished, key=lambda each: each.sequence)
            for event in events:
                changed += int(self.apply(event))
            if not events or int(page.sequence) <= after:
                break
            after = int(page.sequence)
            self.sequence = max(self.sequence, after)
        return changed

    async def run(self, operations: Any, job: Job) -> Answer:
        """The job's answer: the reply's where it was answered inline, else
        read once it finished (`read_job_answer`)."""
        reply = await operations.run_job(job=job)
        if reply.answered_inline:
            return Answer(reply.answer)
        return await self.wait(operations, str(reply.job_id))

    async def wait(self, operations: Any, job_id: str) -> Answer:
        """A job answered later, once it finished: its answer, read."""
        waiting = self._waiting.setdefault(job_id, asyncio.Event())
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout_seconds
        try:
            while job_id not in self.finished:
                await self.catch_up(operations)
                if job_id in self.finished:
                    break
                left = deadline - loop.time()
                if left <= 0:
                    raise TimeoutError(f"{job_id} did not finish in {self.timeout_seconds}s")
                try:
                    await asyncio.wait_for(waiting.wait(), timeout=min(self.poll_seconds, left))
                except TimeoutError:
                    continue
        finally:
            self._waiting.pop(job_id, None)
        return Answer(await operations.read_job_answer(job_id=job_id))


def measures_of(definitions: Iterable[Any]) -> dict[str, Any]:
    """The definitions `list_measure_definitions` answered, by name: a client
    checks a breakdown is allowed before it asks."""
    return {each.definition: each for each in definitions}
