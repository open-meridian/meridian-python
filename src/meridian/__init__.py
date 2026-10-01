"""Build Meridian plugins.

A plugin's entire contract with the platform is its sidecar, listening on
loopback. This package is a client for that surface and nothing more: it never
learns the bus address, never holds a broker credential, and never discovers
another plugin.

    async with await connect() as plugin:
        print(plugin.identity.roles)
        await plugin.report_sync_status(source="snaptrade", connection_healthy=True,
                                        external_account_id="acct-1")

A plugin's pages are declared where their views are, each with the levels it
serves, and refused to a session at any other (`Pages`, in `meridian.pages`).
The few figures it reports about its own work, which core draws on its Summary
under Manage, go on its heartbeat (`plugin.figures = [Figure(...)]`, in
`meridian.figures`). What its roles hear it receives with a handler per row,
seeded, followed and caught up from the store (`plugin.receive(...)`, each
change a `Heard`, in `meridian.receive`).
"""

from .asgi import CallerMiddleware
from .client import (
    _RETIRED_BY_026,
    DEFAULT_ADDRESS,
    SCHEMA_VERSION,
    AccessLevel,
    AccountScope,
    AppliesWhen,
    Caller,
    Choice,
    Grants,
    Identity,
    Interface,
    LinkedExternalAccount,
    Page,
    Plugin,
    Setting,
    Settings,
    connect,
)
from .errors import (
    CallFailed,
    MeridianError,
    NoSidecar,
    NotGranted,
    NotLinked,
    NotRegistered,
    Refused,
)
from .figures import Figure, FigureState

# An amount of currency as a typed operation takes one, the two readers of a
# number off the wire, and the nested messages a typed operation takes with
# numbers in them, generated with the operations (decisions/023).
from .operations import (
    Money,
    ReportedCollateral,
    ReportedLot,
    StatementFigures,
    as_decimal,
    as_money,
)
from .pages import Pages, Request, Response

# The plugin-facing mirrors a typed operation takes, generated with it.
from .plugin.v1.operations_pb2 import (
    AssetClass,
    CollateralDirection,
    ExternalAccount,
    HoldingSide,
    Identifier,
    MissReason,
    SyncState,
)
from .receive import Heard

__all__ = [
    "DEFAULT_ADDRESS",
    "SCHEMA_VERSION",
    "AccessLevel",
    "AccountScope",
    "AppliesWhen",
    "AssetClass",
    "CallFailed",
    "Caller",
    "CallerMiddleware",
    "Choice",
    "CollateralDirection",
    "ExternalAccount",
    "Figure",
    "FigureState",
    "Grants",
    "Heard",
    "HoldingSide",
    "Identifier",
    "Identity",
    "Interface",
    "LinkedExternalAccount",
    "MeridianError",
    "MissReason",
    "Money",
    "NoSidecar",
    "NotGranted",
    "NotLinked",
    "NotRegistered",
    "Page",
    "Pages",
    "Plugin",
    "Refused",
    "ReportedCollateral",
    "ReportedLot",
    "Request",
    "Response",
    "Setting",
    "Settings",
    "StatementFigures",
    "SyncState",
    "as_decimal",
    "as_money",
    "connect",
]


def __getattr__(name: str) -> object:
    """A name this package no longer has, said plainly rather than as a typo.

    An ImportError, because `from meridian import TagAccess` is how a plugin
    reaches for it, and an import replaces an AttributeError's words with its
    own generic ones."""
    if name == "TagAccess":
        raise ImportError(_RETIRED_BY_026, name=__name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
