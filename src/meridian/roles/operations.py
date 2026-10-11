"""An operations plugin's common part (spec/plugin-pages-follow-their-role,
"operations, an operations plugin"). Candidates until a second operations
plugin needs them (the spec's Q4), except what the role's duties name:
opening balances, reconciliation, breaks.

**First-use path.** Choose its settings (Settings); have access and a street
source (a deployment admin: a group holds write on the plugin with accounts,
and a custody plugin has a linked account among them); confirm opening
balances (Opening balances); reconcile (Reconciliations); work the breaks
(Breaks, daily work).

**Settings:** `reconcile()` ("Reconcile", off until turned on: it acts with
no person), `due_business_days()` ("A break is due"),
`street_fresh_within_hours()` ("Reconcile against a statement no older
than").

**Pages,** Open and View, the daily page first: Breaks (`read_breaks`),
Reconciliations (`read_reconciliations`), Opening balances
(`read_opening_balances`; `confirm_opening_balance`, checked by its own read
tool so it can be prepared). Verbs: "Reconcile now", "Confirm", and a
break's "Handle", "Resolve" and "Close". Templates:
`meridian/roles/operations/breaks.html`, `reconciliations.html`,
`opening_balances.html`.

**Figures:** "Open breaks", "Overdue breaks", "Awaiting an opening balance",
"Street missing" (only when any), "Last reconciliation" (`figures(...)`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..client import Setting
from ..figures import Figure
from ._figures import Value, ordered

__all__ = [
    "BreaksRead",
    "OpeningBalancesRead",
    "ReconciliationsRead",
    "due_business_days",
    "figures",
    "reconcile",
    "street_fresh_within_hours",
]


def reconcile(*, description: str = "", roles: tuple[str, ...] = ()) -> Any:
    """ "Reconcile": compare the book with each completed statement and record
    what is found; off until an admin turns it on, since it acts with no
    person behind it."""
    return Setting(
        "reconcile",
        bool,
        label="Reconcile",
        default=False,
        description=description
        or "Compare the book with each completed statement and record the breaks found.",
        roles=roles,
    )


def due_business_days(
    *, default: int = 3, description: str = "", roles: tuple[str, ...] = ()
) -> Any:
    """ "A break is due": the due date suggested for a break nobody set one
    for."""
    return Setting(
        "due_business_days",
        int,
        label="A break is due",
        default=default,
        unit="business days after it is first seen",
        description=description or "The due date suggested for a break nobody has set one for.",
        roles=roles,
    )


def street_fresh_within_hours(
    *, default: int = 96, description: str = "", roles: tuple[str, ...] = ()
) -> Any:
    """ "Reconcile against a statement no older than": past it, the street is
    missing for the account and nothing is reconciled against it."""
    return Setting(
        "street_fresh_within_hours",
        int,
        label="Reconcile against a statement no older than",
        default=default,
        unit="hours past the day it is as of",
        description=description
        or "A statement older than this is the street missing for its account.",
        roles=roles,
    )


@dataclass(frozen=True)
class BreaksRead:
    """Breaks' common fields (`read_breaks`'s answer), which a plugin extends
    with its breaks: how many are open and overdue, for the accounts the
    person may read."""

    open_breaks: int = 0
    overdue_breaks: int = 0


@dataclass(frozen=True)
class ReconciliationsRead:
    """Reconciliations' common fields (`read_reconciliations`'s answer): when
    the last reconciliation ran, ISO 8601, empty for never."""

    last_reconciliation: str = ""


@dataclass(frozen=True)
class OpeningBalancesRead:
    """Opening balances' common fields (`read_opening_balances`'s answer):
    how many accounts in the plugin's scope await an opening balance."""

    awaiting_an_opening_balance: int = 0


def figures(
    *,
    open_breaks: Value,
    overdue_breaks: Value = None,
    awaiting_an_opening_balance: Value = None,
    street_missing: Value = None,
    last_reconciliation: Value = None,
) -> list[Figure]:
    """The operations role's figures, in its order; "Street missing" only
    when given; each a plain value or a `meridian.Figure` carrying its state
    and why."""
    return ordered(
        [
            ("Open breaks", open_breaks, None),
            ("Overdue breaks", overdue_breaks, None),
            ("Awaiting an opening balance", awaiting_an_opening_balance, None),
            ("Street missing", street_missing, None),
            ("Last reconciliation", last_reconciliation, None),
        ]
    )
