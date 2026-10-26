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

From contract v16 a plugin at the edge declares the kinds of raw record it
keeps (`Storage(kinds=[RecordKind(...)])`), each kept for its window and,
past it, archived, kept or deleted as its admin chose -- two settings per
kind the SDK declares, `<kind>_window_days` and `<kind>_past_window`. It
moves its records in units through `plugin.archive_unit`,
`plugin.restore_unit` and `plugin.delete_unit`, each reported through the
sidecar before anything is removed, and finds where a record's key stands
(`plugin.find_record`); the archive is `meridian.edge.archive_dir()` where it
is mounted. What each kind holds in storage goes on its heartbeat
(`plugin.stored`, `StoredSpan`s), and every edge plugin with pages offers
`POST /archive/restore`, derived as a tool.

From contract v18 the lake holds what sources say about prices. A data plugin
declares its catalogue in its declaration
(`Declaration(catalogue=[DatasetDeclaration(...)])`: each dataset's key,
vendor, data types, modes, cadence, the terms its vendor imposes
(`DatasetLicence`), the day its business dates are in -- `day_time_zone`,
`day_end_minute` -- and the venue it is, `venue_id`), and records prices and
bars in batches of 1 to 500 (`plugin.record_prices`, `plugin.record_bars`,
each a `Price` or `Bar` under an `ObservationMeta` naming its dataset, its
subjects, its business date and its raw record), every subject resolved
first (`resolve_identifier`, `report_missing_instrument`) and every venue
(`resolve_venue`, `report_missing_venue`). It hears what the lake wants of it
(`receive(observations_wanted=..., want_withdrawn=...)`), recording against
a want (`want_id=`) or declining it per subject (`plugin.decline_want`). A
reading role reads prices and bars by business date, as of a recorded time,
or side by side (`list_prices`, `list_bars`, with `business_date=`,
`as_of_ns=` and `sources=SourceChoice(...)`), learns the datasets it may read
(`list_datasets`), and hears what is recorded after for the subjects it names
(`receive(prices_recorded=..., subjects=[...])`), each row with its dataset
(`Heard.dataset`). A `Money` names the asset's cash instrument:
`Money("12.50", "USD")` still works, core resolving the ISO 4217 code, dated;
an asset with no ISO 4217 code, a stablecoin's say, is named by its
instrument alone (`Money(amount, instrument_id=...)`). A date is a
`datetime.date`, or its ISO 8601 text, and one that is no date is refused
naming the field before anything is sent.

From contract v19 the lake hears trades and quotes. A data plugin records them in
batches of 1 to 500 (`plugin.record_trades`, `plugin.record_quotes`, each a
`Trade` -- its price a `Money`, its quantity, its `TradeAttributes` with an
`Eligibility` for the consolidated bar and its venue's, and the `Aggressor`
where the source says it -- or a `Quote`, each side unset where it is
empty), keyed by UTC instants with no business date. `signal` and `ems`
read them (`list_trades` over a range, or after the watermark last seen;
`list_quotes` at the latest in force or over a range) and hear them
(`receive(trades_recorded=..., quotes_recorded=..., subjects=[...])`):
every trade, never conflated, and after a loss the trades recorded after the
watermark last seen; the latest quote per subject, dataset, venue and asset.

From contract v20 an act can be prepared rather than made: a route that
changes something names the read tool that checks it (`checked_by=`), the
paths in its record naming the accounts it touches (`accounts=`) and the
page a person makes it on (`made_on=`, filled by the SDK), and a page opened
from a prepared change reads it (`await request.prepared()`). A setting may
be each person's own (`Setting(per_person=True)`): the plugin saves a
person's values for them (`plugin.set_own_settings(...)`) and reads them
from each of their requests (`request.own_settings`). A data plugin reads
its own datasets' licences (`list_datasets`) and, on start, the last trade
it recorded of each subject (`list_trades(..., latest_recorded=True)`), to
backfill a restart's gap (`meridian.roles.data.backfill_restart`). The roles
`dgm`, `ccm` and `match` are `data`, `connectivity` and `confirmation`.

Each role's common part is `meridian.roles` (`data`, `custody`,
`operations`, `reporting`): its pages' records, figures, settings and
templates. Settings may be one typed class (`@meridian.settings`, its fields
`meridian.setting(...)`, `meridian.environment()` and
`meridian.sample_data()`), and every page's loader holds the kit's macros,
`meridian/kit.html`. From contract v23 a plugin whose source states no
currency declares `meridian.account_currency()`, a linked account's
currency its admin sets with a plugin-wide default, and gives it with its
provenance (`meridian.edge.supplied_currency`, its entry ready for
ResolveIdentifier's `provenance`), reporting nothing that needs it until it
is set.

From contract v21 a plugin's autonomous work -- a scheduled sweep, a
strategy, an agent inside the plugin -- calls the plugin's own acts as the
service account its role runs as (`async with meridian.runs_as(role) as act:
await act(tool_name, arguments, reason=...)`), answered made, with the act's
own answer, or prepared, with the prepared change's ID, by every level the
admins set and the account's own setting; a refusal names the field
(`.fields`). A route reached for such a call is a `Caller` whose
`subject_kind` is `SubjectKind.SUBJECT_KIND_SERVICE_ACCOUNT`, naming its
`owner_subject`, and acts as for a person (`acting_for=request.caller.header`).

From contract v22 an order reaches a venue through the book. Its operations
are typed as every other's, one per row a role may send: `portfolio` and the
`oms` propose (`propose_order`, an order of a unit `quantity` or a
`cash_quantity`, never both), the `oms` releases (`release_order`) and
records a telephoned or outside order for a person (`record_order`),
`compliance` checks and decides (`record_check`, `decide_approval`), the
`ems` claims (`set_working_condition`), places at a connectivity plugin
linked to it, setting the venue's account code its admin mapped on its page
at admin, acting for that admin (`create_placement`; `map_venue_account`
with `acting_for=request.caller.header`), and proposes child orders under a
released parent (`propose_order(link=OrderLink(...))`); a connectivity
plugin reports what the venue said of the `ems`'s placements
(`report_placement`, `report_execution`, `report_charge`), records a locate
(`record_locate`) and publishes its venue's catalogue
(`report_venue_catalogue`). Portfolio and the `oms` own orders, the `ems`
placements and a connectivity plugin fills: a connectivity plugin records no
order and creates no placement, and a venue-originated fill is not supported
in contract v22. They hear the order path's records
(`receive(order_updated=..., placement_updated=..., execution_recorded=...,
unplaced_fact_recorded=..., locate_updated=..., trading_instruction_changed=...)`),
a placement reaching only the connectivity plugin it names, carrying its own
change requests (`Placement.change_requests`, each with its
`PlacementChange`: a cancel or a replace and its new terms), and the trading
instructions in force reaching every subscriber with no account scope,
caught up by a read naming no account (`list_trading_instructions`). A
refusal by the order's state, a claim or a link is a `CommandRefused` with
its code; the order's transitions are the table the SDK carries,
`meridian/transitions.json`. A plugin works out a date in core, one way
for the deployment: a calendar's days (`read_calendar`) and a settlement,
spot, tenor or rolled date, or whether a date is a business day
(`compute_date`, with `SettlementDateInputs`, `SpotDateInputs`,
`TenorDateInputs`, `RollInputs` or `BusinessDayInputs`), answered with the
basis it was worked out on. A version declares the algorithms its
autonomous work may name (`Declaration(algorithms=[AlgorithmDeclaration(...)])`)
and `runs_as(role, algorithm_id=...)` names one; a `Caller` carries the
algorithm a service account's call named (`algorithm_id`) and, for an `ems`,
the connectivity plugins the user may route through
(`connectivity_instance_ids`). Beside its account scope a
connectivity plugin is told its link to its one `ems` and the codes that
`ems` mapped on it, and an `ems` the connectivity plugins linked to it and
its map (`AccountScope.connectivity_link`, `connectivity_links`,
`venue_account_map`).

From contract v23 a connectivity plugin may report a fill on no order and no
placement (`report_execution` naming its `instrument_id`, `side` and
`venue_order_id`), which waits in the book unmatched; the `ems` accepts it to
an order (`accept_execution`, to an `order_id` or a new order) or answers it
DK (`dont_know_execution`, with a reason), and the connectivity plugin hears
what became of the fills it reported (`receive(execution_recorded=...)`). A
data plugin records an event contract's outcomes in batches of 1 to 500
(`record_outcomes`, each an `Outcome`: its `OutcomeDetermination`, its
`OutcomeStage`, its settlement value as a `Money` and the venue's word as
reported), and prices' readers and `operations` hear every version
(`receive(outcomes_recorded=...)`) and read them (`list_outcomes`, as of a
recorded time or after the watermark last seen).

From contract v24 an execution is booked to its accounts, and every
instrument is named by the platform master's ID. The `oms` books an
explicit list of executions on one order (`book_order`, each an
`Allocation`: its account, quantity, average price, gross and net amounts,
fees and intended settlement date, a block's at one average price, an
overfill to the error account with its `ErrorCause`), hands a booking off
to `operations` (`hand_off_booking`), cancels or replaces it before then
(`correct_booking`, a `BookingCorrectionKind`) and records a cross between
two sleeves (`record_sleeve_cross`, a `SleeveCross`); `operations` and
`portfolio` amend an order's allocation instruction
(`set_allocation_instruction`) and `operations` corrects a booking handed
off; `connectivity` and `confirmation` report a prime's answer to a give-up
(`report_give_up`, a `GiveUpAnswer`). The readers hear and read bookings
(`receive(booking_updated=...)`, `list_bookings`, each in its
`BookingState`, whose transitions the table carries beside the order's) and
alerts (`receive(alert_changed=...)`, `list_alerts`; `compliance` raises its
own, `raise_alert`, and acknowledges one for a person,
`acknowledge_alert`). Cash follows option (c): the account's base currency
is a balance, every other currency opens lots with base-currency cost, and
every currency does until a base currency is set.

An instrument's record may be the deployment's provisional `LCL-` record
(`InstrumentRecord.provisional`, `ResolveIdentifierResult.provisional`),
held to the platform's template it names (`template_id`,
`template_version`) and resolved later to the platform's `INS-` record:
read the mark, never the ID's prefix. Every role hears a replacement
(`receive(replace_merged_instrument=...)`, its `ReplacementCause` and
`sequence`) and catches up by sequence (`list_replacements`); the SDK
follows each ID to the record it became (`CurrentIdMap`) and reads the
template catalogue (`list_templates`, `read_template`,
`TemplateCatalogue`). A `reference` plugin offers a record's template fields
(`offer_template_fields`, each a `TemplateFieldValue` with its provenance).
Whether orders may name a provisional record is the deployment admin's
setting, read by the roles that propose, place or check them
(`read_local_record_orders`; not `connectivity`, from contract v25).

From contract v25 a version's declaration is the whole of what it says
about itself: its settings, its interface and tools, whether it reads
external accounts, and the vendor's documentation by digest
(`Declaration(interface=..., reads_external_accounts=...,
documentation="docs")`); a plugin registers exactly the declaration its
version was uploaded with. An operations plugin declares its affirmation
deadline (`Declaration(affirmation_deadline=...)`).

`meridian.environment()` defaults to the vendor's sandbox: Live is a
plugin's only when its code says so (`environment(default="live")`), and
otherwise a person's choice.

From 0.31.0 (contract v26) a `reporting`, `portfolio`, `compliance` or
`signal` plugin asks the analytics component through `meridian.analytics`:
typed builders for a job (`analytics.job`, `analytics.measure`,
`analytics.what_if`), its answer read (`analytics.Answer`) and one answered
later waited for (`analytics.Jobs`); the reference computations v26's engine
equals exactly are `meridian.analytics.reference`. A `pricing` plugin
answers the component's batches with `meridian.roles.pricing.Pricer`.
Every role reads event groups and hears each new version through
`meridian.EventGroups`; a venue's data plugin reports them with
`meridian.roles.data.event_contracts.Feed.report_event`. `meridian.environment()`
offers `paper` beside `live` and `sandbox`, and a connectivity plugin reports
the environment its session reached on its venue catalogue
(`meridian.reached_environment`), the second key of the agents' demo-only
guard. A plugin calling a model counts its tokens on its heartbeat
(`plugin.count_model_tokens`), and asks the lake one bounded query
(`plugin.query_lake`).
"""

# Each role's common part (contract v20, spec/plugin-pages-follow-their-role).
# The analytics component's API (contract v26).
from . import (
    analytics,  # noqa: E402
    roles,  # noqa: E402  (after what it imports)
)
from ._settings import (
    account_currency,
    ceilings_from,
    connection_badge,
    dataset_thresholds,
    environment,
    is_demo,
    quality_thresholds,
    reached_environment,
    sample_data,
    session_ceilings,
    setting,
    settings,
    stale_reference_action,
    stale_reference_after,
)
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
    ConnectivityLink,
    ConnectivityUser,
    Grants,
    Identity,
    Interface,
    LinkedExternalAccount,
    Page,
    Plugin,
    RefusedSetting,
    Setting,
    Settings,
    SubjectKind,
    TicketKind,
    TicketReference,
    TicketResolution,
    TicketState,
    TicketSubject,
    VenueAccountMap,
    VenueAccountMapping,
    connect,
    runs_as,
)
from .declaration import (
    AlgorithmDeclaration,
    DataEligibility,
    DatasetDeclaration,
    DatasetLicence,
    Declaration,
    NotCarried,
    RecordKind,
    Storage,
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
# The analytics component's job and a pricing plugin's answer (contract v26).
from .operations import (
    Adjustment,
    AgreementFigures,
    AlertSubject,
    Allocation,
    AllocationInstruction,
    AllocationLine,
    Bar,
    BasisAdjustment,
    BreakCause,
    BreakDifference,
    BreakValue,
    CorporateActionAnnounced,
    CustodialActivity,
    DateBasis,
    DateCheck,
    DateRuleRef,
    DerivedSeries,
    Eligibility,
    Encumbrance,
    ExternalAccount,
    Fee,
    Filing,
    Finality,
    GiveUpRecord,
    Holding,
    HoldingsReport,
    Job,
    Leg,
    LifecycleDelivery,
    LifecycleEvent,
    ListedSeries,
    LocateAnswer,
    LocateUse,
    LotTerms,
    Money,
    MovementLine,
    ObservationMeta,
    OpeningLot,
    OpeningPosition,
    OpeningSource,
    OrderChange,
    OrderLink,
    Outcome,
    Party,
    PendingSettlement,
    PendingSettlementRef,
    PlacementChange,
    PositionEncumbrances,
    PositionKey,
    Price,
    PricedUnit,
    Provenance,
    QualityAssessment,
    Quote,
    QuoteAtTrade,
    RatingAction,
    ReceiptQuote,
    ReportedCollateral,
    ReportedEncumbrance,
    ReportedFact,
    ReportedLot,
    ReportedPending,
    ReportedPositionValue,
    RollInputs,
    SavedScenario,
    Scenario,
    ScenarioAxis,
    ScenarioKey,
    ScenarioSet,
    Sensitivity,
    SeriesWant,
    Shock,
    ShockBucket,
    SleeveCross,
    SourceTime,
    StatementFigures,
    Statistic,
    StrategyInstruction,
    StrategyParameter,
    SubjectRef,
    TemplateFieldValue,
    Tenor,
    TenorDateInputs,
    Trade,
    TradeAttributes,
    UnitValue,
    VenueCatalogue,
    VenueEligibility,
    VenueOrderType,
    VenueStrategy,
    WhatIf,
    WhatIfTrade,
    as_decimal,
    as_money,
)
from .pages import Pages, Request, Response

# The plugin-facing mirrors a typed operation takes, generated with it.
from .plugin.v1.operations_pb2 import (
    AccountKind,
    ActivityKind,
    ActivityRef,
    Actor,
    Aggressor,
    AlertKind,
    AlertState,
    AsReported,
    AssetClass,
    Backfill,
    BookingCorrectionKind,
    BookingState,
    BreakCategory,
    BreakCauseCategory,
    BreakHandling,
    BreakState,
    BusinessDayInputs,
    CollateralDirection,
    ComputedAs,
    DatasetRef,
    Eligible,
    ErrorCause,
    EventGroup,
    EventGroupFlag,
    FigureKey,
    GiveUpAnswer,
    HoldingSide,
    Identifier,
    InstrumentType,
    LotReliefMethod,
    LotSource,
    MarginAgreementRef,
    MissReason,
    NotEvaluatedReason,
    OpeningSourceKind,
    OutcomeDetermination,
    OutcomeStage,
    PendingState,
    PositionBasis,
    PriceBasis,
    PriceKind,
    ProvenanceKind,
    QuoteCharacteristic,
    RawRecordRef,
    ReplacementCause,
    ResolvedByEntries,
    Reversal,
    ScenarioKind,
    SecurityTemplate,
    SettlementBucket,
    SettlementDateInputs,
    Source,
    SourceChoice,
    SourceTimeKind,
    SpotDateInputs,
    StatementSegmentRef,
    StreetRecordRef,
    SyncState,
    TemplateField,
    TradeCharacteristic,
    Unanswered,
    UnansweredReason,
    VenueKind,
    VenueRecord,
)
from .receive import Heard
from .replacements import CurrentIdMap, TemplateCatalogue
from .roles.data._groups import EventGroups

# What a plugin at the edge says its storage holds of each kind (contract v16),
# and how a dataset's rows can arrive (contract v18).
from .v1.sidecar_pb2 import MoveOutcome, ObservationMode, StoredSpan

__all__ = [
    "AccessLevel",
    "AccountKind",
    "AccountScope",
    "ActivityKind",
    "ActivityRef",
    "Actor",
    "Adjustment",
    "Aggressor",
    "AgreementFigures",
    "AlertKind",
    "AlertState",
    "AlertSubject",
    "AlgorithmDeclaration",
    "Allocation",
    "AllocationInstruction",
    "AllocationLine",
    "AppliesWhen",
    "AsReported",
    "AssetClass",
    "Backfill",
    "Bar",
    "BasisAdjustment",
    "BookingCorrectionKind",
    "BookingState",
    "BreakCategory",
    "BreakCause",
    "BreakCauseCategory",
    "BreakDifference",
    "BreakHandling",
    "BreakState",
    "BreakValue",
    "BusinessDayInputs",
    "CallFailed",
    "Caller",
    "CallerMiddleware",
    "Choice",
    "CollateralDirection",
    "Column",
    "CommandRefused",
    "ComputedAs",
    "ConnectivityLink",
    "ConnectivityUser",
    "CorporateActionAnnounced",
    "CurrentIdMap",
    "CustodialActivity",
    "DEFAULT_ADDRESS",
    "DataEligibility",
    "DatasetDeclaration",
    "DatasetLicence",
    "DatasetRef",
    "DateBasis",
    "DateCheck",
    "DateRuleRef",
    "Declaration",
    "DerivedSeries",
    "Eligibility",
    "Eligible",
    "Encumbrance",
    "ErrorCause",
    "EventGroup",
    "EventGroupFlag",
    "EventGroups",
    "ExternalAccount",
    "Fee",
    "Figure",
    "FigureKey",
    "FigureState",
    "Filing",
    "Finality",
    "GiveUpAnswer",
    "GiveUpRecord",
    "Grants",
    "Heard",
    "Holding",
    "HoldingSide",
    "HoldingsReport",
    "Identifier",
    "Identity",
    "InstrumentType",
    "Interface",
    "Job",
    "Leg",
    "LifecycleDelivery",
    "LifecycleEvent",
    "LinkedExternalAccount",
    "ListedSeries",
    "LocateAnswer",
    "LocateUse",
    "LotReliefMethod",
    "LotSource",
    "LotTerms",
    "MarginAgreementRef",
    "MeridianError",
    "MissReason",
    "Money",
    "MoveOutcome",
    "MovementLine",
    "NoSidecar",
    "NotCarried",
    "NotEvaluatedReason",
    "NotGranted",
    "NotLinked",
    "NotRegistered",
    "ObservationMeta",
    "ObservationMode",
    "OpeningLot",
    "OpeningPosition",
    "OpeningSource",
    "OpeningSourceKind",
    "OrderChange",
    "OrderLink",
    "Outcome",
    "OutcomeDetermination",
    "OutcomeStage",
    "Page",
    "Pages",
    "Party",
    "PendingSettlement",
    "PendingSettlementRef",
    "PendingState",
    "PlacementChange",
    "Plugin",
    "PositionBasis",
    "PositionEncumbrances",
    "PositionKey",
    "Price",
    "PriceBasis",
    "PriceKind",
    "PricedUnit",
    "Provenance",
    "ProvenanceKind",
    "QualityAssessment",
    "Quote",
    "QuoteAtTrade",
    "QuoteCharacteristic",
    "RatingAction",
    "RawRecordRef",
    "ReceiptQuote",
    "RecordKind",
    "Refused",
    "RefusedSetting",
    "ReplacementCause",
    "ReportedCollateral",
    "ReportedEncumbrance",
    "ReportedFact",
    "ReportedLot",
    "ReportedPending",
    "ReportedPositionValue",
    "Request",
    "ResolvedByEntries",
    "Response",
    "Reversal",
    "RollInputs",
    "SCHEMA_VERSION",
    "SavedScenario",
    "Scenario",
    "ScenarioAxis",
    "ScenarioKey",
    "ScenarioKind",
    "ScenarioSet",
    "SecurityTemplate",
    "Sensitivity",
    "SeriesWant",
    "Setting",
    "Settings",
    "SettlementBucket",
    "SettlementDateInputs",
    "Shock",
    "ShockBucket",
    "SleeveCross",
    "Source",
    "SourceChoice",
    "SourceTime",
    "SourceTimeKind",
    "SpotDateInputs",
    "StatementFigures",
    "StatementSegmentRef",
    "Statistic",
    "Storage",
    "StoredSpan",
    "StrategyInstruction",
    "StrategyParameter",
    "StreetRecordRef",
    "SubjectKind",
    "SubjectRef",
    "SyncState",
    "TemplateCatalogue",
    "TemplateField",
    "TemplateFieldValue",
    "Tenor",
    "TenorDateInputs",
    "TicketKind",
    "TicketReference",
    "TicketResolution",
    "TicketState",
    "TicketSubject",
    "Trade",
    "TradeAttributes",
    "TradeCharacteristic",
    "Unanswered",
    "UnansweredReason",
    "UnitValue",
    "VenueAccountMap",
    "VenueAccountMapping",
    "VenueCatalogue",
    "VenueEligibility",
    "VenueKind",
    "VenueOrderType",
    "VenueRecord",
    "VenueStrategy",
    "WhatIf",
    "WhatIfTrade",
    "account_currency",
    "analytics",
    "as_decimal",
    "as_money",
    "ceilings_from",
    "connect",
    "connection_badge",
    "dataset_thresholds",
    "environment",
    "is_demo",
    "reached_environment",
    "roles",
    "runs_as",
    "sample_data",
    "quality_thresholds",
    "session_ceilings",
    "setting",
    "settings",
    "stale_reference_action",
    "stale_reference_after",
]


def __getattr__(name: str) -> object:
    """A name this package no longer has, said plainly rather than as a typo.

    An ImportError, because `from meridian import TagAccess` is how a plugin
    reaches for it, and an import replaces an AttributeError's words with its
    own generic ones."""
    if name == "TagAccess":
        raise ImportError(_RETIRED_BY_026, name=__name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
