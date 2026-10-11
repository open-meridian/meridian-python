"""A custody plugin's common part (spec/plugin-pages-follow-their-role,
"custody, a custody plugin"). Candidates until a second custody plugin needs
them (the spec's Q4), except what the role's duties name: statements, links,
raw records.

**First-use path.** Enter the credentials (Settings); connect (Connections);
have accounts granted (a deployment admin, from contract v20: a plugin links
only to the accounts granted to its instance, nothing by default); link
accounts (Account links); see statements (Statements).

**Settings**, in this order: the credentials; `poll_seconds()` ("Read every")
and `stale_after_hours()` ("Stale after") where the custodian is read on a
schedule; the vendor's own; `meridian.sample_data()`.

**Pages.** Manage: Connections (`read_connections`), then Account links
(`read_account_links`; linking with `link_account`). Open and View, the daily
page first: Statements (`read_statements`), History
(`read_account_activities`), Raw records (no tool of its own: a raw record is
followed from a row's reference, and restored with `restore_unit`).
Templates: `meridian/roles/custody/connections.html`, `account_links.html`,
`statements.html`, `history.html`, `raw_records.html`.

**Figures:** "Connections", "Accounts reached", "Last read" (`figures(...)`).

From contract v20 `read_accounts_for_linking` answers only the accounts the
deployment admin granted this instance, and a link naming another is refused
(`CommandRefused`, REFUSAL_REASON_ACCOUNT_NOT_LINKABLE): Account links says
"No accounts granted yet" until there are some.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..client import Setting
from ..figures import Figure
from ._figures import Value, ordered
from .data import Credential

__all__ = [
    "AccountLinksRead",
    "AccountRead",
    "ActivityRead",
    "ConnectionRead",
    "ConnectionsRead",
    "Credential",
    "ExternalAccountRead",
    "HistoryRead",
    "LinkRead",
    "StatementRead",
    "StatementsRead",
    "figures",
    "poll_seconds",
    "stale_after_hours",
]


def poll_seconds(
    *, default: int = 900, description: str = "", roles: tuple[str, ...] = ()
) -> Any:
    """ "Read every": how often the custodian is read, in seconds."""
    return Setting(
        "poll_seconds",
        int,
        label="Read every",
        default=default,
        unit="seconds",
        description=description or "How often to read the custodian.",
        roles=roles,
    )


def stale_after_hours(
    *, default: int = 36, description: str = "", roles: tuple[str, ...] = ()
) -> Any:
    """ "Stale after": how old the custodian's last sync of an account may be
    before it is reported stale, in hours."""
    return Setting(
        "stale_after_hours",
        int,
        label="Stale after",
        default=default,
        unit="hours",
        description=description
        or "How old the custodian's last sync of an account may be before it is stale.",
        roles=roles,
    )


@dataclass(frozen=True)
class ConnectionRead:
    """One connection ("Connections"): its name, its state (whose fix it is,
    as W2.1 says it), the accounts it reaches, and when it was last read."""

    connection: str
    state: str = ""
    accounts_reached: int = 0
    last_read: str = ""


@dataclass(frozen=True)
class ConnectionsRead:
    """Connections' common fields (`read_connections`'s answer): each
    credential, set or not, and each connection."""

    credentials: list[Credential] = field(default_factory=list)
    connections: list[ConnectionRead] = field(default_factory=list)


@dataclass(frozen=True)
class ExternalAccountRead:
    """One external account the plugin reports, as the kit's account map
    takes it."""

    external_account_id: str
    name: str = ""
    detail: str = ""


@dataclass(frozen=True)
class AccountRead:
    """One account granted to this instance, as `read_accounts_for_linking`
    answers it."""

    account_id: str
    name: str = ""


@dataclass(frozen=True)
class LinkRead:
    """One link, as the SDK gives it (`AccountScope.links`)."""

    external_account_id: str
    account_id: str
    account_name: str = ""


@dataclass(frozen=True)
class AccountLinksRead:
    """Account links' common fields (`read_account_links`'s answer): the
    external accounts reported, the accounts granted, and the links."""

    external_accounts: list[ExternalAccountRead] = field(default_factory=list)
    accounts: list[AccountRead] = field(default_factory=list)
    links: list[LinkRead] = field(default_factory=list)


@dataclass(frozen=True)
class StatementRead:
    """One account's statement, for a person who may read it: the account,
    its custodian, the day it is as of, and its state (open, closed, or
    withheld with why)."""

    account: str
    custodian: str = ""
    as_of: str = ""
    state: str = ""


@dataclass(frozen=True)
class StatementsRead:
    """Statements' common fields (`read_statements`'s answer), cut to the
    accounts the person may read."""

    statements: list[StatementRead] = field(default_factory=list)


@dataclass(frozen=True)
class ActivityRead:
    """One activity on an account as the custodian reported it, in
    `meridian.CustodialActivity`'s words, each value as text: its kind, its
    dates, its instrument, its units and amount, and its description."""

    account: str
    external_activity_id: str = ""
    kind: str = ""
    trade_date: str = ""
    settlement_date: str = ""
    instrument_id: str = ""
    units: str = ""
    amount: str = ""
    description: str = ""


@dataclass(frozen=True)
class HistoryRead:
    """History's common fields (`read_account_activities`'s answer), cut to
    the accounts the person may read."""

    activities: list[ActivityRead] = field(default_factory=list)


def figures(
    *, connections: Value, accounts_reached: Value = None, last_read: Value = None
) -> list[Figure]:
    """The custody role's figures, in its order: "Connections" (a count, warn
    when any needs attention), "Accounts reached", "Last read" (error with
    the reason when the last read failed); each a plain value or a
    `meridian.Figure` carrying its state and why."""
    return ordered(
        [
            ("Connections", connections, None),
            ("Accounts reached", accounts_reached, None),
            ("Last read", last_read, None),
        ]
    )
