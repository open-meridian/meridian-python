"""An order's transitions, and from contract v23 an execution's, as data
(decisions/035).

The order lifecycle's states and transitions are one table, kept in
meridian-design's matrix/transitions.tsv and published by meridian-schema as
`boundaries/transitions.json`, which this package carries beside the role
suites and the data dictionary (`meridian/transitions.json`, vendored at the
schema revision the bindings are, by `make vendor-schema`). The book alone
enforces it; a plugin reads it to know, before it sends a command, whether
the order's state allows what its role would cause, and which refusal codes
the command may meet.

Each row names the states it applies in (`from`: OrderState names; `none`
for an order being created, `any` for every state), what causes it in the
contract's words (`cause`), who may cause it (`caused_by`: roles, `bor` for
the book's own derivation or clock, `dashboard`, or `any`), the states it
leads to (`to`; `unchanged` for one leaving the state as it was), and the
RefusalReason names a command meeting it may be refused with (`refusal`;
none for a venue's fact, which is never refused for its state).

From contract v23 the table holds an execution's rows too, keyed `e1`
onward, their states ExecutionState names (`execution_states`): a fill on a
placement or on no placement, its accept, its DK, its correction and its
bust. They are read apart from the order's, so an order's state never meets
an execution's row.

From contract v24 it holds a booking's rows too, keyed `b1` onward, their
states BookingState names (`booking_states`): booked, held, handed off,
corrected and cancelled (decisions/035 as amended for a booking's states).
They are read apart from the order's and the execution's
(`booking_table`).

Internal: `table()` reads the order's rows, `execution_table()` the
execution's, and `caused_from(state, role)` picks the order's rows a role may
cause from a state. Neither is a public name of the SDK;
the file itself is the published data, read with
`importlib.resources.files("meridian").joinpath("transitions.json")`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from importlib import resources

#: The words the table uses beside OrderState names.
NONE, ANY, UNCHANGED = "none", "any", "unchanged"

#: An execution's rows are keyed e1 onward (contract v23), a booking's b1
#: onward (contract v24).
_EXECUTION_ROW = re.compile(r"^e\d+$")
_BOOKING_ROW = re.compile(r"^b\d+$")


@dataclass(frozen=True)
class Transition:
    """One row of the table, as published."""

    row: str
    from_states: tuple[str, ...]
    cause: str
    caused_by: tuple[str, ...]
    to_states: tuple[str, ...]
    refusal: tuple[str, ...]


@cache
def _published() -> dict[str, object]:
    text = resources.files("meridian").joinpath("transitions.json").read_text(encoding="utf-8")
    loaded: dict[str, object] = json.loads(text)
    return loaded


def states() -> tuple[str, ...]:
    """Every OrderState the table names, in its order."""
    return tuple(str(state) for state in _published()["states"])  # type: ignore[attr-defined]


def execution_states() -> tuple[str, ...]:
    """Every ExecutionState the table names, in its order (contract v23)."""
    held = _published().get("execution_states", [])
    return tuple(str(state) for state in held)  # type: ignore[attr-defined]


def booking_states() -> tuple[str, ...]:
    """Every BookingState the table names, in its order (contract v24)."""
    held = _published().get("booking_states", [])
    return tuple(str(state) for state in held)  # type: ignore[attr-defined]


def _kind(row: str) -> str:
    if _EXECUTION_ROW.match(row):
        return "execution"
    if _BOOKING_ROW.match(row):
        return "booking"
    return "order"


def _rows(kind: str) -> tuple[Transition, ...]:
    rows = _published()["transitions"]
    return tuple(
        Transition(
            row=str(held["row"]),
            from_states=tuple(held["from"]),
            cause=str(held["cause"]),
            caused_by=tuple(held["caused_by"]),
            to_states=tuple(held["to"]),
            refusal=tuple(held["refusal"]),
        )
        for held in rows  # type: ignore[attr-defined]
        if _kind(str(held["row"])) == kind
    )


def table() -> tuple[Transition, ...]:
    """Every row of the order's table, in its order."""
    return _rows("order")


def execution_table() -> tuple[Transition, ...]:
    """Every row of an execution's table, in its order (contract v23)."""
    return _rows("execution")


def booking_table() -> tuple[Transition, ...]:
    """Every row of a booking's table, in its order (contract v24)."""
    return _rows("booking")


def caused_from(state: str, role: str) -> tuple[Transition, ...]:
    """The rows `role` (a role, `bor`, or `dashboard`) may cause from an
    order in `state` (an OrderState name, or `none` for one being created):
    none where the table gives it nothing to do there. A `ValueError` for a
    state the table does not name, so a misspelling is not read as nothing
    allowed."""
    if state != NONE and state not in states():
        raise ValueError(
            f"{state!r} is no state of the order's table; it names {', '.join(states())}"
        )
    return tuple(
        held
        for held in table()
        if (state in held.from_states or (ANY in held.from_states and state != NONE))
        and (role in held.caused_by or ANY in held.caused_by)
    )
