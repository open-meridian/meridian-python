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
change a `Heard`, in `meridian.receive`). The book of record (contract v8) is
written by an operations plugin and read by five roles through the typed
operations -- record_opening_balance, record_break, record_account_figures,
handle_break, resolve_break, list_positions, list_breaks,
list_account_figures, list_account_attributes -- and a refusal the book
gives is a `CommandRefused` carrying its code. From contract v9 the book
refuses an entry missing what downstream needs (REFUSAL_REASON_INCOMPLETE),
naming each field in `CommandRefused.fields`; and a `Caller` who came through
a client names its delegation and client (`delegation_id`, `client_name`).
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
    CommandRefused,
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
    Adjustment,
    AgreementFigures,
    BasisAdjustment,
    BreakCause,
    BreakDifference,
    BreakValue,
    Encumbrance,
    LotTerms,
    Money,
    MovementLine,
    OpeningLot,
    OpeningPosition,
    OpeningSource,
    PendingSettlement,
    PendingSettlementRef,
    PositionEncumbrances,
    PositionKey,
    ReportedCollateral,
    ReportedEncumbrance,
    ReportedLot,
    ReportedPositionValue,
    StatementFigures,
    as_decimal,
    as_money,
)
from .pages import Pages, Request, Response

# The plugin-facing mirrors a typed operation takes, generated with it.
from .plugin.v1.operations_pb2 import (
    AssetClass,
    BreakCategory,
    BreakCauseCategory,
    BreakHandling,
    BreakState,
    CollateralDirection,
    ExternalAccount,
    FigureKey,
    HoldingSide,
    Identifier,
    LotReliefMethod,
    LotSource,
    MarginAgreementRef,
    MissReason,
    OpeningSourceKind,
    PendingState,
    PositionBasis,
    ResolvedByEntries,
    Reversal,
    SettlementBucket,
    StatementSegmentRef,
    StreetRecordRef,
    SyncState,
)
from .receive import Heard

__all__ = [
    "DEFAULT_ADDRESS",
    "SCHEMA_VERSION",
    "AccessLevel",
    "AccountScope",
    "Adjustment",
    "AgreementFigures",
    "AppliesWhen",
    "AssetClass",
    "BasisAdjustment",
    "BreakCategory",
    "BreakCause",
    "BreakCauseCategory",
    "BreakDifference",
    "BreakHandling",
    "BreakState",
    "BreakValue",
    "CallFailed",
    "Caller",
    "CallerMiddleware",
    "Choice",
    "CollateralDirection",
    "CommandRefused",
    "Encumbrance",
    "ExternalAccount",
    "Figure",
    "FigureKey",
    "FigureState",
    "Grants",
    "Heard",
    "HoldingSide",
    "Identifier",
    "Identity",
    "Interface",
    "LinkedExternalAccount",
    "LotReliefMethod",
    "LotSource",
    "LotTerms",
    "MarginAgreementRef",
    "MeridianError",
    "MissReason",
    "Money",
    "MovementLine",
    "NoSidecar",
    "NotGranted",
    "NotLinked",
    "NotRegistered",
    "OpeningLot",
    "OpeningPosition",
    "OpeningSource",
    "OpeningSourceKind",
    "Page",
    "Pages",
    "PendingSettlement",
    "PendingSettlementRef",
    "PendingState",
    "Plugin",
    "PositionBasis",
    "PositionEncumbrances",
    "PositionKey",
    "Refused",
    "ReportedCollateral",
    "ReportedEncumbrance",
    "ReportedLot",
    "ReportedPositionValue",
    "Request",
    "ResolvedByEntries",
    "Response",
    "Reversal",
    "Setting",
    "Settings",
    "SettlementBucket",
    "StatementFigures",
    "StatementSegmentRef",
    "StreetRecordRef",
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
