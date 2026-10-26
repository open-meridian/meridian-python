"""A `signal` plugin's common part for contract v28: derived series, saved
scenarios and a row's quality escalated.

**Derived series** (G5, sdk-contract/signal-derives-data-from-sources;
W10.4): what a signal computes from the lake and records back as a row of
its own dataset -- an underlying's 30-day IV, an index's level, a
positioning summary's part -- each value naming its `series`, the rule it
was computed by (a definition and version, an analytics measure's where one
was used) and every dataset it read with the as-of it read at, so licences
and counts follow it (`derived`, `RecordDerivedSeries`). Any reader reads
them by subject and series (`ListDerivedSeries`).

**Saved scenarios** (the common scenario format,
sdk-contract/the-common-scenario-format-contract; ruling 109): a scenario
set is named axes of steps, each step a scenario of shocks; a person's grid
saved on a plugin's page is one row of the plugin's own dataset, an edit the
next version of its row key (`saved`, `RecordScenarios`), named in a job by
that row key and read back by it (`ListScenarios`). `spot_steps` and
`date_steps` build the grid's usual axes.

**Quality escalated** (W10.12): `quality.Baseline` judges a close against
its subject's robust rolling baseline, and `escalate` records each row it
found suspicious or invalid as its own `QualityAssessment`, states only
escalating; the thresholds are the admin's `quality_thresholds`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from ..operations import (
    DerivedSeries,
    ObservationMeta,
    SavedScenario,
    Scenario,
    ScenarioAxis,
    ScenarioSet,
    Shock,
    SubjectRef,
    UnitValue,
)
from ..plugin.v1 import operations_pb2 as ops
from .data.quality import Baseline, OutlierThresholds, assessment

__all__ = [
    "Baseline",
    "OutlierThresholds",
    "date_steps",
    "derived",
    "escalate",
    "read_derived",
    "read_scenarios",
    "saved",
    "spot_steps",
]


def derived(
    subject_id: str,
    series: str,
    value: Decimal | int,
    business_date: date | str,
    *,
    dataset: str,
    unit: str,
    definition: str,
    version: int,
    inputs: Iterable[tuple[str, int]],
    valid_from_ns: int = 0,
) -> DerivedSeries:
    """One value of a derived series for a business date: its subject, its
    own name for the series, the value and its unit, the rule (definition
    and version) and each dataset read with the as-of it was read at."""
    day = business_date if isinstance(business_date, str) else business_date.isoformat()
    read = [ops.DerivedInput(dataset=d, as_of_ns=at) for d, at in inputs]
    if not read:
        raise ValueError("a derived value names every dataset it read")
    return DerivedSeries(
        meta=ObservationMeta(
            row_key=f"{subject_id}:{series}:{day}"[:128],
            subjects=[SubjectRef(entity_id=subject_id)],
            source=ops.Source(dataset=dataset),
            valid_from_ns=valid_from_ns,
            business_date=day,
        ),
        series=series,
        value=UnitValue(value=value, unit=unit),
        rule=ops.MeasureRef(definition=definition, version=version),
        inputs=read,
    )


async def read_derived(
    plugin: Any,
    subject_id: str,
    series: Sequence[str],
    from_date: date | str = "",
    to_date: date | str = "",
) -> list[ops.DerivedSeries]:
    """A subject's derived series by name over a range of business dates."""
    answer = await plugin.list_derived_series(
        subjects=[SubjectRef(entity_id=subject_id)], series=list(series),
        from_date=from_date, to_date=to_date,
    )  # fmt: skip
    return list(answer.values)


# ── The scenario format ──────────────────────────────────────────────────


def _relative(name: str, kind: str, percent: Decimal | int) -> Scenario:
    if Decimal(percent) == 0:
        return Scenario(name=name)
    return Scenario(
        name=name,
        shocks=[
            Shock(object=kind, target=ops.ShockTarget(every=True), form="relative",
                  unit="percent", value=percent)
        ],
    )  # fmt: skip


def spot_steps(percents: Sequence[Decimal | int], name: str = "spot") -> ScenarioAxis:
    """A grid's price axis: each step every subject's spot moved by a
    percentage, 0 the unshocked step."""
    return ScenarioAxis(
        name=name,
        steps=[_relative(f"{Decimal(p):+}%" if p else "0%", "spot", p) for p in percents],
    )


def date_steps(
    days: Sequence[int], *, to_settlement: bool = True, name: str = "date"
) -> ScenarioAxis:
    """A grid's date axis: today, each step forward by whole days, and, where
    asked, to each position's settlement."""
    steps = [
        Scenario(name="today")
        if d == 0
        else Scenario(
            name=f"+{d} days",
            shocks=[Shock(object="time", form="absolute", unit="days", value=d)],
        )
        for d in days
    ]
    if to_settlement:
        steps.append(
            Scenario(name="to settlement", shocks=[Shock(object="time", form="to_settlement")])
        )
    return ScenarioAxis(name=name, steps=steps)


def saved(
    row_key: str,
    *,
    dataset: str,
    scenario_set: ScenarioSet | None = None,
    scenario: Scenario | None = None,
    description: str = "",
    valid_from_ns: int = 0,
) -> SavedScenario:
    """A scenario set's axes, or one scenario, as a row of the plugin's own
    dataset under its row key; saving the same key again is its next
    version."""
    if (scenario_set is None) == (scenario is None):
        raise ValueError("a saved scenario is a scenario set or one scenario")
    return SavedScenario(
        meta=ObservationMeta(
            row_key=row_key[:128],
            source=ops.Source(dataset=dataset),
            valid_from_ns=valid_from_ns,
        ),
        scenario=scenario,
        scenario_set=scenario_set,
        description=description,
    )


async def read_scenarios(
    plugin: Any, row_keys: Sequence[str], version: int = 0
) -> list[ops.SavedScenario]:
    """Saved scenarios by their row keys; `version` with one row key reads
    that version rather than the latest."""
    answer = await plugin.list_scenarios(row_keys=list(row_keys), version=version)
    return list(answer.scenarios)


# ── Quality escalated ────────────────────────────────────────────────────


async def escalate(
    plugin: Any, baseline: Baseline, rows: Iterable[Any], *, value_of: Any = None
) -> int:
    """Judge each recorded price row (heard or read) against its subject's
    baseline and record an assessment of each found suspicious or invalid,
    in the lake's batches; how many were recorded. `value_of` reads a row's
    value, its price's amount by default."""

    def amount(row: Any) -> Decimal:
        price = row.price
        held = getattr(price, "amount", price)
        if isinstance(held, ops.Decimal):
            from ..operations import as_decimal

            return as_decimal(held)
        return Decimal(held)

    read = value_of or amount
    found = []
    for row in rows:
        subject = row.meta.subjects[0].entity_id if row.meta.subjects else row.meta.row_key
        state, reasons = baseline.judge(subject, read(row))
        if reasons:
            found.append(assessment(row, state, reasons))
    for start in range(0, len(found), 500):
        await plugin.record_quality_assessments(assessments=found[start : start + 500])
    return len(found)
