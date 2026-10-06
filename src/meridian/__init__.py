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
From contract v10 a deployment's instrument identity is its own: a resolve
that matches nothing answers a record the deployment minted
(`ResolveIdentifierResult.minted`), a resolve may state what the source says
of the security (`stated_asset_class`, `stated_currency`,
`stated_description`), kept as offers for the deployment admin to accept, and
the book requires each instrument's asset class and currency, naming
`positions[n].instrument.asset_class` when a record lacks it.
From contract v11 the edge keeps its own (`meridian.edge`): a value that did
not convert travels as reported beside the field's not-known value
(`as_reported`), every row references the raw record it was converted from
in the plugin's own storage (`plugin.raw_record(key)`), every value the
plugin closed rather than read carries its provenance (`derived`,
`supplied`, `second_source`, `reported`), an account carries its kind
(`AccountKind`) and a holding its pending quantities by value date
(`ReportedPending`), each asset is counted once, and a row sent again with a
field a revision added is a backfill (`backfill("v11", "raw_record")`). A
plugin registers with its version's declaration (`meridian.Declaration`:
its secret settings' names, what it does not carry, the storage it asks
for), and counts what it saw and does not carry
(`plugin.note_not_carried`). A resolve may state a security's instrument type
(`stated_instrument_type`, a money market fund first). The role suites a
plugin holds itself to are `meridian.suites`.

From contract v13 a plugin files a ticket for the person whose request it is
serving, never as itself (`plugin.file_ticket(...)`, keyed by its own
`idempotency_key`, `for_caller=` the person's `Caller`), about itself, a part
of core or the platform (`TicketSubject`), and reads what became of those it
filed (`plugin.filed_tickets(...)`).

From contract v14 a custody plugin reports each activity on an account as
the custodian states it (`plugin.record_activity(...)`, a `CustodialActivity`
of an `ActivityKind`), answered as already recorded when sent again; and
operations reads it (`plugin.list_activities(...)`, with the source's
`history_from`), hears it (`activity_recorded=`), links a break's cause to it
(`BreakCause(activity=ActivityRef(...))`, `BREAK_CAUSE_CATEGORY_INCOME_REINVESTED`),
and reads and hears each sync status the street keeps
(`plugin.list_sync_statuses(...)`, `sync_status_recorded=`).

From contract v15 a person's access to a plugin is granted per role: a page,
route, tool and setting names the roles it serves (`roles=`; none on a plugin
holding one role or none), and the session carries the person's level and
accounts on each role within its button (`caller.roles`,
`caller.level_for(role)`, `caller.read_for(role)`, `caller.write_for(role)`).
A custody plugin re-resolves an activity it recorded once its instrument
resolves (`plugin.re_resolve_activity(...)`), the activity kept as first
recorded and the re-resolution beside it, which operations reads
(`re_resolutions`) and hears (`activity_re_resolved=`).
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
    Column,
    Grants,
    Identity,
    Interface,
    LinkedExternalAccount,
    Page,
    Plugin,
    Setting,
    Settings,
    TicketKind,
    TicketReference,
    TicketResolution,
    TicketState,
    TicketSubject,
    connect,
)
from .declaration import Declaration, NotCarried, Storage
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
    CustodialActivity,
    Encumbrance,
    ExternalAccount,
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
    Provenance,
    ReportedCollateral,
    ReportedEncumbrance,
    ReportedLot,
    ReportedPending,
    ReportedPositionValue,
    StatementFigures,
    as_decimal,
    as_money,
)
from .pages import Pages, Request, Response

# The plugin-facing mirrors a typed operation takes, generated with it.
from .plugin.v1.operations_pb2 import (
    AccountKind,
    ActivityKind,
    ActivityRef,
    AsReported,
    AssetClass,
    Backfill,
    BreakCategory,
    BreakCauseCategory,
    BreakHandling,
    BreakState,
    CollateralDirection,
    FigureKey,
    HoldingSide,
    Identifier,
    InstrumentType,
    LotReliefMethod,
    LotSource,
    MarginAgreementRef,
    MissReason,
    OpeningSourceKind,
    PendingState,
    PositionBasis,
    ProvenanceKind,
    RawRecordRef,
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
    "AccountKind",
    "AccountScope",
    "ActivityKind",
    "ActivityRef",
    "AsReported",
    "Backfill",
    "Declaration",
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
    "Column",
    "CollateralDirection",
    "CommandRefused",
    "CustodialActivity",
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
    "InstrumentType",
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
    "NotCarried",
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
    "Provenance",
    "ProvenanceKind",
    "RawRecordRef",
    "Refused",
    "ReportedCollateral",
    "ReportedEncumbrance",
    "ReportedLot",
    "ReportedPending",
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
    "Storage",
    "StreetRecordRef",
    "SyncState",
    "TicketKind",
    "TicketReference",
    "TicketResolution",
    "TicketState",
    "TicketSubject",
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
