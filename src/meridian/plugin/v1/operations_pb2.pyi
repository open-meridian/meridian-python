from meridian.v1 import sidecar_pb2 as _sidecar_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SyncState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SYNC_STATE_UNSPECIFIED: _ClassVar[SyncState]
    SYNC_STATE_CURRENT: _ClassVar[SyncState]
    SYNC_STATE_STALE: _ClassVar[SyncState]
    SYNC_STATE_NEEDS_SIGN_IN: _ClassVar[SyncState]
    SYNC_STATE_DISABLED: _ClassVar[SyncState]
    SYNC_STATE_DELAYED_BY_DESIGN: _ClassVar[SyncState]
    SYNC_STATE_HOLDINGS_UNAVAILABLE: _ClassVar[SyncState]

class CollateralDirection(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COLLATERAL_DIRECTION_UNSPECIFIED: _ClassVar[CollateralDirection]
    COLLATERAL_DIRECTION_POSTED: _ClassVar[CollateralDirection]
    COLLATERAL_DIRECTION_RECEIVED: _ClassVar[CollateralDirection]

class HoldingSide(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HOLDING_SIDE_UNSPECIFIED: _ClassVar[HoldingSide]
    HOLDING_SIDE_LONG: _ClassVar[HoldingSide]
    HOLDING_SIDE_SHORT: _ClassVar[HoldingSide]

class MissReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MISS_REASON_UNSPECIFIED: _ClassVar[MissReason]
    MISS_REASON_NOT_FOUND: _ClassVar[MissReason]
    MISS_REASON_AMBIGUOUS: _ClassVar[MissReason]

class AssetClass(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ASSET_CLASS_UNSPECIFIED: _ClassVar[AssetClass]
    ASSET_CLASS_EQUITY: _ClassVar[AssetClass]
    ASSET_CLASS_DEBT: _ClassVar[AssetClass]
    ASSET_CLASS_FUND: _ClassVar[AssetClass]
    ASSET_CLASS_DERIVATIVE: _ClassVar[AssetClass]
    ASSET_CLASS_CRYPTO_ASSET: _ClassVar[AssetClass]
    ASSET_CLASS_EVENT_CONTRACT: _ClassVar[AssetClass]
    ASSET_CLASS_CASH: _ClassVar[AssetClass]

class AccountState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCOUNT_STATE_UNSPECIFIED: _ClassVar[AccountState]
    ACCOUNT_STATE_OPEN: _ClassVar[AccountState]
    ACCOUNT_STATE_CLOSED: _ClassVar[AccountState]
SYNC_STATE_UNSPECIFIED: SyncState
SYNC_STATE_CURRENT: SyncState
SYNC_STATE_STALE: SyncState
SYNC_STATE_NEEDS_SIGN_IN: SyncState
SYNC_STATE_DISABLED: SyncState
SYNC_STATE_DELAYED_BY_DESIGN: SyncState
SYNC_STATE_HOLDINGS_UNAVAILABLE: SyncState
COLLATERAL_DIRECTION_UNSPECIFIED: CollateralDirection
COLLATERAL_DIRECTION_POSTED: CollateralDirection
COLLATERAL_DIRECTION_RECEIVED: CollateralDirection
HOLDING_SIDE_UNSPECIFIED: HoldingSide
HOLDING_SIDE_LONG: HoldingSide
HOLDING_SIDE_SHORT: HoldingSide
MISS_REASON_UNSPECIFIED: MissReason
MISS_REASON_NOT_FOUND: MissReason
MISS_REASON_AMBIGUOUS: MissReason
ASSET_CLASS_UNSPECIFIED: AssetClass
ASSET_CLASS_EQUITY: AssetClass
ASSET_CLASS_DEBT: AssetClass
ASSET_CLASS_FUND: AssetClass
ASSET_CLASS_DERIVATIVE: AssetClass
ASSET_CLASS_CRYPTO_ASSET: AssetClass
ASSET_CLASS_EVENT_CONTRACT: AssetClass
ASSET_CLASS_CASH: AssetClass
ACCOUNT_STATE_UNSPECIFIED: AccountState
ACCOUNT_STATE_OPEN: AccountState
ACCOUNT_STATE_CLOSED: AccountState

class Published(_message.Message):
    __slots__ = ("message_id",)
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    def __init__(self, message_id: _Optional[str] = ...) -> None: ...

class ReportExternalAccountsParams(_message.Message):
    __slots__ = ("accounts",)
    ACCOUNTS_FIELD_NUMBER: _ClassVar[int]
    accounts: _containers.RepeatedCompositeFieldContainer[ExternalAccount]
    def __init__(self, accounts: _Optional[_Iterable[_Union[ExternalAccount, _Mapping]]] = ...) -> None: ...

class ReportSyncStatusParams(_message.Message):
    __slots__ = ("source", "last_synced_at_ns", "connection_healthy", "status_detail", "observed_at_ns", "external_account_id", "state", "holdings_as_of_ns", "history_as_of_ns")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNCED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CONNECTION_HEALTHY_FIELD_NUMBER: _ClassVar[int]
    STATUS_DETAIL_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    HOLDINGS_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    HISTORY_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    source: str
    last_synced_at_ns: int
    connection_healthy: bool
    status_detail: str
    observed_at_ns: int
    external_account_id: str
    state: SyncState
    holdings_as_of_ns: int
    history_as_of_ns: int
    def __init__(self, source: _Optional[str] = ..., last_synced_at_ns: _Optional[int] = ..., connection_healthy: bool = ..., status_detail: _Optional[str] = ..., observed_at_ns: _Optional[int] = ..., external_account_id: _Optional[str] = ..., state: _Optional[_Union[SyncState, str]] = ..., holdings_as_of_ns: _Optional[int] = ..., history_as_of_ns: _Optional[int] = ...) -> None: ...

class RecordHoldingsStatementParams(_message.Message):
    __slots__ = ("source", "external_statement_id", "as_of_date", "read_at_ns", "expected_rows", "buying_power", "margin_requirement", "maintenance_excess", "currency_assumed", "external_account_id", "figures", "institution", "acting_for")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    READ_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_ROWS_FIELD_NUMBER: _ClassVar[int]
    BUYING_POWER_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    MAINTENANCE_EXCESS_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_ASSUMED_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    INSTITUTION_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    source: str
    external_statement_id: str
    as_of_date: str
    read_at_ns: int
    expected_rows: int
    buying_power: Money
    margin_requirement: Money
    maintenance_excess: Money
    currency_assumed: bool
    external_account_id: str
    figures: _containers.RepeatedCompositeFieldContainer[StatementFigures]
    institution: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, source: _Optional[str] = ..., external_statement_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., read_at_ns: _Optional[int] = ..., expected_rows: _Optional[int] = ..., buying_power: _Optional[_Union[Money, _Mapping]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ..., maintenance_excess: _Optional[_Union[Money, _Mapping]] = ..., currency_assumed: bool = ..., external_account_id: _Optional[str] = ..., figures: _Optional[_Iterable[_Union[StatementFigures, _Mapping]]] = ..., institution: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordHoldingsStatementResult(_message.Message):
    __slots__ = ("statement_id", "already_recorded")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ALREADY_RECORDED_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    already_recorded: bool
    def __init__(self, statement_id: _Optional[str] = ..., already_recorded: bool = ...) -> None: ...

class RecordHoldingParams(_message.Message):
    __slots__ = ("statement_id", "instrument_id", "unresolved_identifiers", "quantity", "market_value", "external_account_id", "side", "settle_date_quantity", "currency_assumed", "also_counted_in_cash", "cost_basis", "lots", "margin_requirement", "average_cost", "acting_for")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    SETTLE_DATE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_ASSUMED_FIELD_NUMBER: _ClassVar[int]
    ALSO_COUNTED_IN_CASH_FIELD_NUMBER: _ClassVar[int]
    COST_BASIS_FIELD_NUMBER: _ClassVar[int]
    LOTS_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_COST_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    instrument_id: str
    unresolved_identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    quantity: Decimal
    market_value: Money
    external_account_id: str
    side: HoldingSide
    settle_date_quantity: Decimal
    currency_assumed: bool
    also_counted_in_cash: bool
    cost_basis: Money
    lots: _containers.RepeatedCompositeFieldContainer[ReportedLot]
    margin_requirement: Money
    average_cost: Money
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, statement_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., unresolved_identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., market_value: _Optional[_Union[Money, _Mapping]] = ..., external_account_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., settle_date_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., currency_assumed: bool = ..., also_counted_in_cash: bool = ..., cost_basis: _Optional[_Union[Money, _Mapping]] = ..., lots: _Optional[_Iterable[_Union[ReportedLot, _Mapping]]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ..., average_cost: _Optional[_Union[Money, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordHoldingResult(_message.Message):
    __slots__ = ("holding_id", "resolved")
    HOLDING_ID_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_FIELD_NUMBER: _ClassVar[int]
    holding_id: str
    resolved: bool
    def __init__(self, holding_id: _Optional[str] = ..., resolved: bool = ...) -> None: ...

class ListCustodialPositionsParams(_message.Message):
    __slots__ = ("account_id", "include_unresolved", "page_size", "cursor", "since")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_UNRESOLVED_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    include_unresolved: bool
    page_size: int
    cursor: str
    since: Watermark
    def __init__(self, account_id: _Optional[str] = ..., include_unresolved: bool = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ListCustodialPositionsResult(_message.Message):
    __slots__ = ("positions", "unresolved", "next_cursor", "as_of")
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.RepeatedCompositeFieldContainer[CustodialPosition]
    unresolved: _containers.RepeatedCompositeFieldContainer[UnresolvedHolding]
    next_cursor: str
    as_of: Watermark
    def __init__(self, positions: _Optional[_Iterable[_Union[CustodialPosition, _Mapping]]] = ..., unresolved: _Optional[_Iterable[_Union[UnresolvedHolding, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ListStatementsParams(_message.Message):
    __slots__ = ("account_id", "as_of_date", "since", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    as_of_date: str
    since: Watermark
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListStatementsResult(_message.Message):
    __slots__ = ("statements", "next_cursor", "as_of")
    STATEMENTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    statements: _containers.RepeatedCompositeFieldContainer[StatementRecordedEvent]
    next_cursor: str
    as_of: Watermark
    def __init__(self, statements: _Optional[_Iterable[_Union[StatementRecordedEvent, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ResolveIdentifierParams(_message.Message):
    __slots__ = ("identifiers", "as_of_ns", "exchange_mic", "currency")
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    EXCHANGE_MIC_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    as_of_ns: int
    exchange_mic: str
    currency: str
    def __init__(self, identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., as_of_ns: _Optional[int] = ..., exchange_mic: _Optional[str] = ..., currency: _Optional[str] = ...) -> None: ...

class ResolveIdentifierResult(_message.Message):
    __slots__ = ("found", "instrument_id", "miss_reason", "placeholder")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    MISS_REASON_FIELD_NUMBER: _ClassVar[int]
    PLACEHOLDER_FIELD_NUMBER: _ClassVar[int]
    found: bool
    instrument_id: str
    miss_reason: MissReason
    placeholder: bool
    def __init__(self, found: bool = ..., instrument_id: _Optional[str] = ..., miss_reason: _Optional[_Union[MissReason, str]] = ..., placeholder: bool = ...) -> None: ...

class ReportMissingInstrumentParams(_message.Message):
    __slots__ = ("source", "asset_class", "identifiers", "as_of_ns", "reason", "observed_at_ns")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    ASSET_CLASS_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    source: str
    asset_class: AssetClass
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    as_of_ns: int
    reason: MissReason
    observed_at_ns: int
    def __init__(self, source: _Optional[str] = ..., asset_class: _Optional[_Union[AssetClass, str]] = ..., identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., as_of_ns: _Optional[int] = ..., reason: _Optional[_Union[MissReason, str]] = ..., observed_at_ns: _Optional[int] = ...) -> None: ...

class LinkExternalAccountParams(_message.Message):
    __slots__ = ("external_account_id", "account_id", "new_account_name", "new_account_custodian", "new_account_type", "new_account_owner", "new_account_note", "acting_for")
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_NAME_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_CUSTODIAN_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_OWNER_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_NOTE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    external_account_id: str
    account_id: str
    new_account_name: str
    new_account_custodian: str
    new_account_type: str
    new_account_owner: str
    new_account_note: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, external_account_id: _Optional[str] = ..., account_id: _Optional[str] = ..., new_account_name: _Optional[str] = ..., new_account_custodian: _Optional[str] = ..., new_account_type: _Optional[str] = ..., new_account_owner: _Optional[str] = ..., new_account_note: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class LinkExternalAccountResult(_message.Message):
    __slots__ = ("plugin_instance_id", "external_account_id", "account_id")
    PLUGIN_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    plugin_instance_id: str
    external_account_id: str
    account_id: str
    def __init__(self, plugin_instance_id: _Optional[str] = ..., external_account_id: _Optional[str] = ..., account_id: _Optional[str] = ...) -> None: ...

class ReadAccountsForLinkingParams(_message.Message):
    __slots__ = ("acting_for",)
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReadAccountsForLinkingResult(_message.Message):
    __slots__ = ("accounts",)
    ACCOUNTS_FIELD_NUMBER: _ClassVar[int]
    accounts: _containers.RepeatedCompositeFieldContainer[AccountRecord]
    def __init__(self, accounts: _Optional[_Iterable[_Union[AccountRecord, _Mapping]]] = ...) -> None: ...

class ReceiveRequest(_message.Message):
    __slots__ = ("rows",)
    ROWS_FIELD_NUMBER: _ClassVar[int]
    rows: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, rows: _Optional[_Iterable[str]] = ...) -> None: ...

class Delivery(_message.Message):
    __slots__ = ("meta", "lost", "statement_recorded", "custodial_position_updated")
    META_FIELD_NUMBER: _ClassVar[int]
    LOST_FIELD_NUMBER: _ClassVar[int]
    STATEMENT_RECORDED_FIELD_NUMBER: _ClassVar[int]
    CUSTODIAL_POSITION_UPDATED_FIELD_NUMBER: _ClassVar[int]
    meta: DeliveryMeta
    lost: Lost
    statement_recorded: StatementRecordedEvent
    custodial_position_updated: CustodialPositionUpdatedEvent
    def __init__(self, meta: _Optional[_Union[DeliveryMeta, _Mapping]] = ..., lost: _Optional[_Union[Lost, _Mapping]] = ..., statement_recorded: _Optional[_Union[StatementRecordedEvent, _Mapping]] = ..., custodial_position_updated: _Optional[_Union[CustodialPositionUpdatedEvent, _Mapping]] = ...) -> None: ...

class DeliveryMeta(_message.Message):
    __slots__ = ("message_id", "correlation_id", "causation_id", "published_at_ns", "row", "journal", "cause", "own")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    CAUSATION_ID_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ROW_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    OWN_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    correlation_id: str
    causation_id: str
    published_at_ns: int
    row: str
    journal: JournalRef
    cause: ChangeCause
    own: bool
    def __init__(self, message_id: _Optional[str] = ..., correlation_id: _Optional[str] = ..., causation_id: _Optional[str] = ..., published_at_ns: _Optional[int] = ..., row: _Optional[str] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ..., own: bool = ...) -> None: ...

class Lost(_message.Message):
    __slots__ = ("dropped", "rows")
    DROPPED_FIELD_NUMBER: _ClassVar[int]
    ROWS_FIELD_NUMBER: _ClassVar[int]
    dropped: int
    rows: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, dropped: _Optional[int] = ..., rows: _Optional[_Iterable[str]] = ...) -> None: ...

class ExternalAccount(_message.Message):
    __slots__ = ("external_account_id", "name", "venue_account_type")
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    external_account_id: str
    name: str
    venue_account_type: str
    def __init__(self, external_account_id: _Optional[str] = ..., name: _Optional[str] = ..., venue_account_type: _Optional[str] = ...) -> None: ...

class Money(_message.Message):
    __slots__ = ("amount", "currency_code")
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_CODE_FIELD_NUMBER: _ClassVar[int]
    amount: Decimal
    currency_code: str
    def __init__(self, amount: _Optional[_Union[Decimal, _Mapping]] = ..., currency_code: _Optional[str] = ...) -> None: ...

class Decimal(_message.Message):
    __slots__ = ("high", "low", "scale")
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    SCALE_FIELD_NUMBER: _ClassVar[int]
    high: int
    low: int
    scale: int
    def __init__(self, high: _Optional[int] = ..., low: _Optional[int] = ..., scale: _Optional[int] = ...) -> None: ...

class StatementFigures(_message.Message):
    __slots__ = ("segment", "buying_power", "margin_requirement", "maintenance_excess", "initial_margin", "variation_margin", "net_liquidation", "collateral")
    SEGMENT_FIELD_NUMBER: _ClassVar[int]
    BUYING_POWER_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    MAINTENANCE_EXCESS_FIELD_NUMBER: _ClassVar[int]
    INITIAL_MARGIN_FIELD_NUMBER: _ClassVar[int]
    VARIATION_MARGIN_FIELD_NUMBER: _ClassVar[int]
    NET_LIQUIDATION_FIELD_NUMBER: _ClassVar[int]
    COLLATERAL_FIELD_NUMBER: _ClassVar[int]
    segment: str
    buying_power: Money
    margin_requirement: Money
    maintenance_excess: Money
    initial_margin: Money
    variation_margin: Money
    net_liquidation: Money
    collateral: _containers.RepeatedCompositeFieldContainer[ReportedCollateral]
    def __init__(self, segment: _Optional[str] = ..., buying_power: _Optional[_Union[Money, _Mapping]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ..., maintenance_excess: _Optional[_Union[Money, _Mapping]] = ..., initial_margin: _Optional[_Union[Money, _Mapping]] = ..., variation_margin: _Optional[_Union[Money, _Mapping]] = ..., net_liquidation: _Optional[_Union[Money, _Mapping]] = ..., collateral: _Optional[_Iterable[_Union[ReportedCollateral, _Mapping]]] = ...) -> None: ...

class ReportedCollateral(_message.Message):
    __slots__ = ("direction", "instrument_id", "unresolved_identifiers", "quantity", "value", "haircut", "value_after_haircut", "held_at")
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    HAIRCUT_FIELD_NUMBER: _ClassVar[int]
    VALUE_AFTER_HAIRCUT_FIELD_NUMBER: _ClassVar[int]
    HELD_AT_FIELD_NUMBER: _ClassVar[int]
    direction: CollateralDirection
    instrument_id: str
    unresolved_identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    quantity: Decimal
    value: Money
    haircut: Decimal
    value_after_haircut: Money
    held_at: str
    def __init__(self, direction: _Optional[_Union[CollateralDirection, str]] = ..., instrument_id: _Optional[str] = ..., unresolved_identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., value: _Optional[_Union[Money, _Mapping]] = ..., haircut: _Optional[_Union[Decimal, _Mapping]] = ..., value_after_haircut: _Optional[_Union[Money, _Mapping]] = ..., held_at: _Optional[str] = ...) -> None: ...

class Identifier(_message.Message):
    __slots__ = ("scheme", "value", "source")
    SCHEME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    scheme: str
    value: str
    source: str
    def __init__(self, scheme: _Optional[str] = ..., value: _Optional[str] = ..., source: _Optional[str] = ...) -> None: ...

class ReportedLot(_message.Message):
    __slots__ = ("quantity", "cost", "acquired_date")
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    COST_FIELD_NUMBER: _ClassVar[int]
    ACQUIRED_DATE_FIELD_NUMBER: _ClassVar[int]
    quantity: Decimal
    cost: Money
    acquired_date: str
    def __init__(self, quantity: _Optional[_Union[Decimal, _Mapping]] = ..., cost: _Optional[_Union[Money, _Mapping]] = ..., acquired_date: _Optional[str] = ...) -> None: ...

class Watermark(_message.Message):
    __slots__ = ("partitions",)
    PARTITIONS_FIELD_NUMBER: _ClassVar[int]
    partitions: _containers.RepeatedCompositeFieldContainer[PartitionSequence]
    def __init__(self, partitions: _Optional[_Iterable[_Union[PartitionSequence, _Mapping]]] = ...) -> None: ...

class PartitionSequence(_message.Message):
    __slots__ = ("partition", "sequence")
    PARTITION_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    partition: str
    sequence: int
    def __init__(self, partition: _Optional[str] = ..., sequence: _Optional[int] = ...) -> None: ...

class CustodialPosition(_message.Message):
    __slots__ = ("account_id", "instrument_id", "quantity", "market_value", "last_statement_id", "as_of_date", "updated_at_ns", "side", "settle_date_quantity", "also_counted_in_cash", "cost_basis", "lots", "margin_requirement", "last_change", "removed", "average_cost")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    LAST_STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    SETTLE_DATE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ALSO_COUNTED_IN_CASH_FIELD_NUMBER: _ClassVar[int]
    COST_BASIS_FIELD_NUMBER: _ClassVar[int]
    LOTS_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    REMOVED_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_COST_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    instrument_id: str
    quantity: Decimal
    market_value: Money
    last_statement_id: str
    as_of_date: str
    updated_at_ns: int
    side: HoldingSide
    settle_date_quantity: Decimal
    also_counted_in_cash: bool
    cost_basis: Money
    lots: _containers.RepeatedCompositeFieldContainer[ReportedLot]
    margin_requirement: Money
    last_change: JournalRef
    removed: bool
    average_cost: Money
    def __init__(self, account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., market_value: _Optional[_Union[Money, _Mapping]] = ..., last_statement_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., updated_at_ns: _Optional[int] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., settle_date_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., also_counted_in_cash: bool = ..., cost_basis: _Optional[_Union[Money, _Mapping]] = ..., lots: _Optional[_Iterable[_Union[ReportedLot, _Mapping]]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., removed: bool = ..., average_cost: _Optional[_Union[Money, _Mapping]] = ...) -> None: ...

class JournalRef(_message.Message):
    __slots__ = ("partition", "sequence", "previous_sequence")
    PARTITION_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    partition: str
    sequence: int
    previous_sequence: int
    def __init__(self, partition: _Optional[str] = ..., sequence: _Optional[int] = ..., previous_sequence: _Optional[int] = ...) -> None: ...

class UnresolvedHolding(_message.Message):
    __slots__ = ("holding_id", "account_id", "identifiers", "quantity", "market_value", "source", "as_of_date", "escalated")
    HOLDING_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    ESCALATED_FIELD_NUMBER: _ClassVar[int]
    holding_id: str
    account_id: str
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    quantity: Decimal
    market_value: Money
    source: str
    as_of_date: str
    escalated: bool
    def __init__(self, holding_id: _Optional[str] = ..., account_id: _Optional[str] = ..., identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., market_value: _Optional[_Union[Money, _Mapping]] = ..., source: _Optional[str] = ..., as_of_date: _Optional[str] = ..., escalated: bool = ...) -> None: ...

class StatementRecordedEvent(_message.Message):
    __slots__ = ("statement_id", "source", "as_of_date", "rows_received", "rows_resolved", "rows_unresolved", "recorded_at_ns", "account_id", "figures", "currency_assumed", "journal", "cause", "external_account_id", "institution")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    ROWS_RECEIVED_FIELD_NUMBER: _ClassVar[int]
    ROWS_RESOLVED_FIELD_NUMBER: _ClassVar[int]
    ROWS_UNRESOLVED_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_ASSUMED_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTITUTION_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    source: str
    as_of_date: str
    rows_received: int
    rows_resolved: int
    rows_unresolved: int
    recorded_at_ns: int
    account_id: str
    figures: _containers.RepeatedCompositeFieldContainer[StatementFigures]
    currency_assumed: bool
    journal: JournalRef
    cause: ChangeCause
    external_account_id: str
    institution: str
    def __init__(self, statement_id: _Optional[str] = ..., source: _Optional[str] = ..., as_of_date: _Optional[str] = ..., rows_received: _Optional[int] = ..., rows_resolved: _Optional[int] = ..., rows_unresolved: _Optional[int] = ..., recorded_at_ns: _Optional[int] = ..., account_id: _Optional[str] = ..., figures: _Optional[_Iterable[_Union[StatementFigures, _Mapping]]] = ..., currency_assumed: bool = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ..., external_account_id: _Optional[str] = ..., institution: _Optional[str] = ...) -> None: ...

class ChangeCause(_message.Message):
    __slots__ = ("instance_id", "acting_for_subject", "correlation_id", "causation_id", "committed_at_ns")
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_SUBJECT_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    CAUSATION_ID_FIELD_NUMBER: _ClassVar[int]
    COMMITTED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    acting_for_subject: str
    correlation_id: str
    causation_id: str
    committed_at_ns: int
    def __init__(self, instance_id: _Optional[str] = ..., acting_for_subject: _Optional[str] = ..., correlation_id: _Optional[str] = ..., causation_id: _Optional[str] = ..., committed_at_ns: _Optional[int] = ...) -> None: ...

class AccountRecord(_message.Message):
    __slots__ = ("account_id", "name", "state", "created_at_ns", "custodian", "account_type", "owner", "note")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CUSTODIAN_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    name: str
    state: AccountState
    created_at_ns: int
    custodian: str
    account_type: str
    owner: str
    note: str
    def __init__(self, account_id: _Optional[str] = ..., name: _Optional[str] = ..., state: _Optional[_Union[AccountState, str]] = ..., created_at_ns: _Optional[int] = ..., custodian: _Optional[str] = ..., account_type: _Optional[str] = ..., owner: _Optional[str] = ..., note: _Optional[str] = ...) -> None: ...

class CustodialPositionUpdatedEvent(_message.Message):
    __slots__ = ("position", "statement_id", "previous_quantity", "journal", "cause")
    POSITION_FIELD_NUMBER: _ClassVar[int]
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    position: CustodialPosition
    statement_id: str
    previous_quantity: Decimal
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, position: _Optional[_Union[CustodialPosition, _Mapping]] = ..., statement_id: _Optional[str] = ..., previous_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...
