"""Event groups, read and heard (contract v26; W3.29, W3.30;
spec/the-contract-gaps-v26-and-v27-close, A1 to A9).

An event's contracts are grouped in the instrument master, `EventGroup`,
with whether its members are mutually exclusive and whether they are
exhaustive -- each `EVENT_GROUP_FLAG_TRUE`, `_FALSE` or `_NOT_STATED`, an
unknown never false -- and each change of a flag or a member a new version
dated by when it took effect. Every role that reads instruments reads them
(`list_event_groups`) and hears each new version (`event_group_changed`).
A reader computing over a group -- a set's sum, an implied distribution --
reads the version in force at its moment:

    groups = meridian.EventGroups()
    await groups.catch_up(plugin)                     # on start, and after a loss
    await plugin.receive(event_group_changed=groups.heard, ...)
    group = groups.holding("INS-...", at_ns=moment)   # the version in force then
    if groups.exhaustive(group): ...

The reader is the SDK's, so a plugin that keeps no groups passes its suite's
`hears-and-reads-an-event-group` without code: the suite runner answers the
case through a reader of its own (`meridian.suites`).

Core checks nothing about outcomes (A7): that exactly one member of a
mutually exclusive and exhaustive group pays is a reader's check.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ...plugin.v1 import operations_pb2 as ops
from ...receive import Heard

__all__ = ["EventGroups", "flag", "stated"]

#: The flags' names, as a case and a page say them.
TRUE, FALSE, NOT_STATED = (
    ops.EVENT_GROUP_FLAG_TRUE,
    ops.EVENT_GROUP_FLAG_FALSE,
    ops.EVENT_GROUP_FLAG_NOT_STATED,
)


def flag(stated_by_venue: bool | None) -> int:
    """A venue's statement as an `EventGroupFlag`: true, false, or -- where
    the venue states nothing -- not stated, never false (A2)."""
    if stated_by_venue is None:
        return NOT_STATED
    return TRUE if stated_by_venue else FALSE


def stated(value: int) -> bool | None:
    """An `EventGroupFlag` read back: True, False, or None for not stated
    (unspecified is read as not stated)."""
    if value == TRUE:
        return True
    if value == FALSE:
        return False
    return None


class EventGroups:
    """The event groups read (`catch_up`, `read`) and heard (`heard`), every
    version kept, so the version in force at any moment can be read. `sequence`
    is the last version applied, where the next `catch_up` reads after."""

    def __init__(self) -> None:
        self._versions: dict[str, list[ops.EventGroup]] = {}
        self.sequence = 0

    def apply(self, group: ops.EventGroup) -> bool:
        """One version, as its delivery or a read carried it; whether it is
        new. A version held already changes nothing."""
        if not group.event_group_id:
            return False
        held = self._versions.setdefault(group.event_group_id, [])
        if any(each.version == group.version for each in held):
            return False
        kept = ops.EventGroup()
        kept.CopyFrom(group)
        held.append(kept)
        held.sort(key=lambda each: (each.valid_from_ns, each.version))
        self.sequence = max(self.sequence, int(group.sequence))
        return True

    async def heard(self, heard: Heard[ops.EventGroup]) -> None:
        """A `receive` handler for the event-group-changed row:
        `plugin.receive(event_group_changed=groups.heard, ...)`."""
        self.apply(heard.message)

    async def catch_up(self, operations: Any, *, instrument_ids: Sequence[str] = ()) -> int:
        """Every version after the last applied, read until a read answers
        none (`list_event_groups` after a sequence, W3.30): on start, and
        after a loss. Narrowed to the groups holding `instrument_ids` where
        given. How many were new."""
        changed = 0
        after = self.sequence
        while True:
            page = await operations.list_event_groups(
                instrument_ids=list(instrument_ids), after_sequence=after
            )
            groups = sorted(page.event_groups, key=lambda each: each.sequence)
            for group in groups:
                changed += int(self.apply(group))
            if not groups or int(page.sequence) <= after:
                break
            after = int(page.sequence)
            self.sequence = max(self.sequence, after)
        return changed

    async def read(
        self,
        operations: Any,
        *,
        instrument_ids: Sequence[str] = (),
        event_group_ids: Sequence[str] = (),
        as_of_ns: int = 0,
    ) -> list[ops.EventGroup]:
        """The groups holding `instrument_ids`, or named, in force at
        `as_of_ns` (0 for now), every page read; each kept."""
        out: list[ops.EventGroup] = []
        cursor = ""
        while True:
            page = await operations.list_event_groups(
                instrument_ids=list(instrument_ids),
                event_group_ids=list(event_group_ids),
                as_of_ns=as_of_ns,
                cursor=cursor,
            )
            for group in page.event_groups:
                self.apply(group)
                out.append(group)
            cursor = str(page.next_cursor)
            if not cursor:
                return out

    def group(self, event_group_id: str, *, at_ns: int = 0) -> ops.EventGroup | None:
        """The version of a group in force at `at_ns` (0: the latest held),
        or None where none was in force then or none is held."""
        held = self._versions.get(event_group_id) or []
        in_force = [each for each in held if not at_ns or each.valid_from_ns <= at_ns]
        return in_force[-1] if in_force else None

    def holding(self, instrument_id: str, *, at_ns: int = 0) -> list[ops.EventGroup]:
        """Every group whose version in force at `at_ns` holds the
        instrument."""
        out = []
        for event_group_id in sorted(self._versions):
            group = self.group(event_group_id, at_ns=at_ns)
            if group is not None and instrument_id in group.member_instrument_ids:
                out.append(group)
        return out

    def versions(self, event_group_id: str) -> list[ops.EventGroup]:
        """Every version held of a group, oldest first."""
        return list(self._versions.get(event_group_id) or [])

    @property
    def ids(self) -> Iterable[str]:
        return sorted(self._versions)

    @staticmethod
    def exhaustive(group: ops.EventGroup) -> bool:
        """Whether the group states its members exhaustive: only a true flag
        is; not stated is not (the first release's Q5)."""
        return group.exhaustive == TRUE

    @staticmethod
    def mutually_exclusive(group: ops.EventGroup) -> bool:
        """Whether the group states its members mutually exclusive."""
        return group.mutually_exclusive == TRUE
