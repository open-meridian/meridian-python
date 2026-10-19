"""A `pricing` plugin's common part (contract v26; W12.3;
spec/the-analytics-engine-answers-behind-one-api, requirements 18 to 23,
and spec/the-analytics-engines-first-release, §3).

A pricing plugin answers the batches the analytics component routes to it:
for each pricing model id a deployment admin routed to its instance, one
batch per model of every instrument and scenario a job needs, each unit
carrying exactly the market objects the model declares -- observed, or a
scenario's shocked values in their place. It answers a value per unit for
every unit, in the base currency the unit's inputs convert to, and reads
nothing else for the job. It is never called by a client; a batch reaches
the instance it names alone (matrix/directed.tsv).

    pricer = pricing.Pricer(plugin, {"quoted_price": my_model})
    await pricer.run()           # the batches waiting, then each one heard

**A model** is a function of one unit -- `(batch, unit) -> Money` -- its value
per unit; `reference_model` is the built-in models' own computation
(`meridian.analytics.reference`), so a plugin implementing a v26 model id
equals the built-in implementation exactly on every input, as its suite's
`equals-the-built-in-model` asks. A model raising for a unit leaves the
whole batch unanswered: the component then answers a figure for display by
the built-in model, saying so, and leaves a figure a compliance rule reads
not evaluated (requirement 22) -- never a half-answered batch.

**Sensitivities** are carried empty until a model declares one, from v28
(the first release's §3 rule 4): a v26 plugin stays valid when they arrive.

**After a restart** it reads the batches still waiting after the last
sequence it saw (ListPriceBatches), kept in `Sequence`: in memory, since
`pricing` is not a role at the edge and holds no storage (decisions/028), so
a restart reads every batch still waiting; a batch answered twice is
harmless, named by its hash.

The plugin declares the role `pricing`; nothing else is the SDK's: which
instruments it prices is the deployment admin's routing.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections.abc import Awaitable, Callable, Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

from ..operations import Money, PricedUnit, ScenarioKey, as_money
from ..plugin.v1 import operations_pb2 as ops
from ..receive import Heard

__all__ = ["Model", "Pricer", "Sequence", "reference_model", "scenario_of"]

log = logging.getLogger("meridian.roles.pricing")

#: A model: one unit's value per unit, from the batch and the unit alone.
Model = Callable[[ops.PriceBatchRequest, ops.PricingUnit], Money | Awaitable[Money]]


def reference_model(batch: ops.PriceBatchRequest, unit: ops.PricingUnit) -> Money:
    """The built-in models' own value per unit for `cash`, `quoted_price` and
    `binary_event` (the reference computations, requirement 36): the
    instrument's price (or, for `binary_event`, the settlement value an
    `outcome` input carries) times each conversion leg the unit's inputs
    hold, until none leads further."""
    from ..analytics.reference import value_per_unit

    rows = []
    codes: set[str] = set()
    for each in unit.inputs:
        money = as_money(each.value)
        if not money.instrument_id:
            codes.add(money.currency_code)
        rows.append(
            (
                each.subject_id,
                each.kind,
                money.amount,
                money.instrument_id or money.currency_code,
            )
        )
    value, held = value_per_unit(batch.model_id, unit.instrument_id, rows)
    if held in codes:
        return Money(amount=value, currency_code=held)
    return Money(amount=value, instrument_id=held)


def scenario_of(unit: ops.PricingUnit) -> ScenarioKey:
    """The unit's scenario key, as the answer names it back."""
    key = unit.scenario_key
    return ScenarioKey(
        kind=key.kind or ops.SCENARIO_KIND_BASE,
        business_date=key.business_date,
        outcome_instrument_id=key.outcome_instrument_id,
    )


class Sequence:
    """The last batch sequence answered: in memory with no path, as a
    pricing plugin keeps it (0.31.1; `pricing` holds no storage,
    decisions/028); or in a file at `path`, read back on a restart."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.value = 0
        if path is not None and path.exists():
            self.value = int(json.loads(path.read_text() or "{}").get("sequence", 0))

    def note(self, sequence: int) -> None:
        if sequence <= self.value:
            return
        self.value = sequence
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent)
        with os.fdopen(fd, "w") as out:
            json.dump({"sequence": sequence}, out)
        os.replace(temporary, self.path)


class Pricer:
    """A pricing plugin's work: every batch answered, from its models, by
    model id. `plugin` is a `meridian.Plugin`, or the suites' `Recorder`."""

    def __init__(
        self,
        plugin: Any,
        models: Mapping[str, Model],
        *,
        sequence: Sequence | None = None,
    ) -> None:
        if not models:
            raise ValueError("a pricing plugin implements at least one model id")
        self.plugin = plugin
        self.models = dict(models)
        self.sequence = sequence or Sequence()
        self.answered = 0
        self.unanswered: dict[str, str] = {}

    async def answer(self, batch: ops.PriceBatchRequest) -> ops.AnswerPriceBatchResult | None:
        """One batch answered whole (AnswerPriceBatch): a value per unit for
        every unit, under its scenario, and no sensitivity. None, nothing
        sent, where its model id is not one this plugin implements or the
        model raised for a unit; the component's deadline then passes."""
        model = self.models.get(batch.model_id)
        if model is None:
            self.unanswered[batch.batch_id] = f"model {batch.model_id} is not implemented here"
            log.warning("batch %s: %s", batch.batch_id, self.unanswered[batch.batch_id])
            self.sequence.note(int(batch.sequence))
            return None
        values: list[PricedUnit] = []
        try:
            for unit in batch.units:
                worth = model(batch, unit)
                if not isinstance(worth, Money):
                    worth = await worth
                values.append(
                    PricedUnit(
                        instrument_id=unit.instrument_id,
                        scenario_key=scenario_of(unit),
                        value_per_unit=worth,
                    )
                )
        except Exception as failed:  # noqa: BLE001 - the batch left unanswered, said so
            self.unanswered[batch.batch_id] = f"{type(failed).__name__}: {failed}"
            log.warning("batch %s left unanswered: %s", batch.batch_id, failed)
            self.sequence.note(int(batch.sequence))
            return None
        answered: ops.AnswerPriceBatchResult = await self.plugin.answer_price_batch(
            batch_id=batch.batch_id, values=values, sensitivities=()
        )
        self.answered += 1
        self.sequence.note(int(batch.sequence))
        return answered

    async def heard(self, heard: Heard[ops.PriceBatchRequest]) -> None:
        """A `receive` handler for the price-batch row."""
        await self.answer(heard.message)

    async def catch_up(self) -> int:
        """The batches still waiting after the last sequence answered
        (ListPriceBatches, W12.3), each answered; how many."""
        count = 0
        after = self.sequence.value
        while True:
            page = await self.plugin.list_price_batches(after_sequence=after)
            batches = sorted(page.batches, key=lambda each: each.sequence)
            for batch in batches:
                await self.answer(batch)
                count += 1
            if not batches or int(page.sequence) <= after:
                return count
            after = int(page.sequence)

    async def run(self) -> None:
        """The batches waiting, then each one heard, until cancelled."""
        await self.catch_up()
        await self.plugin.receive(price_batch=self.heard)


def per_unit(value: Decimal, instrument_id: str) -> Money:
    """A value per unit in a cash instrument, as a model answers one."""
    return Money(amount=value, instrument_id=instrument_id)
