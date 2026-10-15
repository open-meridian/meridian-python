"""The record each instrument ID became, and the template catalogue (contract v24).

From contract v24 a deployment's provisional `LCL-` record resolves to the
platform's `INS-` record, a person merges two records, and the platform
merges two of its own; each is a replacement, heard by every role whatever
its scope (the instrument-replaced row, W3.8) and caught up by sequence
(`list_replacements`, W3.22). No stored ID is rewritten: an ID once given
names the record it was given to for as long as it survives (decisions/034),
and every same-instrument check compares the record each ID became (W11's
invariants). A plugin that holds instrument IDs in its own storage or state
follows each to the record it became with a `CurrentIdMap`; a plugin that
keeps none needs neither.

    ids = meridian.CurrentIdMap()
    await ids.catch_up(plugin)                       # on start: every replacement
    await plugin.receive(replace_merged_instrument=ids.heard, order_updated=...)
    ids.current("LCL-01J...")                        # "INS-..." once it resolved
    ids.same(held_id, order.instrument_id)           # one record now?

The map is the SDK's, so a plugin that keeps none passes its suite's
`hears-and-reads-a-replacement` without code: the suite runner answers the
case by following a replacement through a map of its own (`meridian.suites`).

A record names the platform's template it is held to (`template_id`,
`template_version`); the templates the store holds are unscoped reference
data (W3.24), each published version immutable. A `TemplateCatalogue` lists
them and reads one at a version, keeping each version read:

    catalogue = meridian.TemplateCatalogue()
    await catalogue.load(plugin, asset_class="equity")
    template = await catalogue.template(plugin, record.template_id, record.template_version)
    required = [field.path for field in template.fields if field.required]

`reads-the-template-catalogue`, in every role's suite, is answered by the
runner the same way, through a catalogue of its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .plugin.v1 import operations_pb2 as ops
from .receive import Heard


class CurrentIdMap:
    """The record each replaced instrument ID became, from the replacements
    read (`catch_up`) and heard (`heard`), in the store's sequence.

    `current(instrument_id)` follows an ID through every replacement after
    it to the record it names now: a provisional record resolved, then
    merged on the platform, is followed to the last. An ID never replaced is
    its own. `sequence` is the last replacement applied, where the next
    `catch_up` reads after."""

    def __init__(self) -> None:
        self._became: dict[str, str] = {}
        self._records: dict[str, ops.InstrumentRecord] = {}
        self.sequence = 0

    def apply(self, event: ops.InstrumentReplacedEvent) -> bool:
        """One replacement, as its delivery or `list_replacements` carried
        it; whether it changed the map. One at or below the sequence applied
        already changes nothing; one recorded before v24 carries no sequence,
        and is applied as it is."""
        sequence = int(event.sequence)
        if sequence and sequence <= self.sequence:
            return False
        if sequence:
            self.sequence = sequence
        replaced = event.replaced_instrument_id
        stays = event.instrument.instrument_id
        if not replaced or not stays or replaced == stays:
            return False
        if self.current(stays) == replaced:
            # A replacement naming the way back would loop; the later one
            # stands, the earlier undone.
            self._became.pop(stays, None)
        self._became[replaced] = stays
        held = ops.InstrumentRecord()
        held.CopyFrom(event.instrument)
        self._records[stays] = held
        return True

    async def heard(self, heard: Heard[ops.InstrumentReplacedEvent]) -> None:
        """A `receive` handler for the instrument-replaced row:
        `plugin.receive(replace_merged_instrument=ids.heard, ...)`."""
        self.apply(heard.message)

    async def catch_up(self, operations: Any) -> int:
        """Every replacement after the last applied, read until a read
        answers none (`list_replacements`, W3.22): on start, and after a loss
        a plugin's own handler learns of. How many changed the map."""
        changed = 0
        after = self.sequence
        while True:
            page = await operations.list_replacements(after_sequence=after)
            events = sorted(page.replacements, key=lambda event: event.sequence)
            for event in events:
                changed += int(self.apply(event))
            if not events or int(page.sequence) <= after:
                break
            after = int(page.sequence)
            self.sequence = max(self.sequence, after)
        return changed

    def current(self, instrument_id: str) -> str:
        """The ID of the record `instrument_id` names now: itself, unless it
        was replaced, followed through each replacement after."""
        seen = {instrument_id}
        at = instrument_id
        while at in self._became:
            at = self._became[at]
            if at in seen:
                break
            seen.add(at)
        return at

    def record(self, instrument_id: str) -> ops.InstrumentRecord | None:
        """The record `instrument_id` became, as the last replacement to it
        carried it; None where it was never replaced, or the record was
        never carried, so the plugin reads it (`resolve_instrument`)."""
        now = self.current(instrument_id)
        if now == instrument_id:
            return None
        return self._records.get(now)

    def same(self, one: str, other: str) -> bool:
        """Whether two IDs name one record now: the same-instrument check
        W11's invariants make through the replacement, never by the IDs'
        text."""
        return self.current(one) == self.current(other)

    @property
    def replaced(self) -> Mapping[str, str]:
        """Each replaced ID and the record it names now."""
        return {replaced: self.current(replaced) for replaced in self._became}


class TemplateCatalogue:
    """The templates the store holds (W3.24): listed at their latest
    versions, and one read at a version -- its fields and match rule as
    published -- each version kept once read, since none is ever changed."""

    def __init__(self) -> None:
        self._latest: dict[str, ops.SecurityTemplate] = {}
        self._versions: dict[tuple[str, str], ops.SecurityTemplate] = {}

    async def load(
        self, operations: Any, *, asset_class: Any = None
    ) -> list[ops.SecurityTemplate]:
        """The templates for one asset class, or every class for none, each
        at its latest version (`list_templates`)."""
        answer = await operations.list_templates(asset_class=asset_class)
        listed = list(answer.templates)
        for template in listed:
            self._latest[template.template_id] = template
        return listed

    async def template(
        self, operations: Any, template_id: str, template_version: str = ""
    ) -> ops.SecurityTemplate | None:
        """One template at a version, or its latest for none
        (`read_template`); None where the store holds no such template or
        version. A version read once is not read again."""
        if template_version and (template_id, template_version) in self._versions:
            return self._versions[(template_id, template_version)]
        answer: ops.ReadTemplateResult = await operations.read_template(
            template_id=template_id, template_version=template_version
        )
        if not answer.HasField("template") or not answer.template.template_id:
            return None
        read = answer.template
        self._keep(read)
        if not template_version:
            self._latest[template_id] = read
        return read

    def latest(self, template_id: str) -> ops.SecurityTemplate | None:
        """The latest version listed or read of `template_id`, if any."""
        return self._latest.get(template_id)

    def _keep(self, template: ops.SecurityTemplate) -> None:
        held = ops.SecurityTemplate()
        held.CopyFrom(template)
        self._versions[(template.template_id, template.template_version)] = held
