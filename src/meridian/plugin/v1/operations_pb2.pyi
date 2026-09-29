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
HOLDING_SIDE_UNSPECIFIED: HoldingSide
HOLDING_SIDE_LONG: HoldingSide
HOLDING_SIDE_SHORT: HoldingSide
MISS_REASON_UNSPECIFIED: MissReason
MISS_REASON_NOT_FOUND: MissReason
MISS_REASON_AMBIGUOUS: MissReason
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
    __slots__ = ("source", "external_statement_id", "as_of_date", "read_at_ns", "expected_rows", "buying_power", "margin_requirement", "maintenance_excess", "currency_assumed", "acting_for")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    READ_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_ROWS_FIELD_NUMBER: _ClassVar[int]
    BUYING_POWER_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    MAINTENANCE_EXCESS_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_ASSUMED_FIELD_NUMBER: _ClassVar[int]
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
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, source: _Optional[str] = ..., external_statement_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., read_at_ns: _Optional[int] = ..., expected_rows: _Optional[int] = ..., buying_power: _Optional[_Union[Money, _Mapping]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ..., maintenance_excess: _Optional[_Union[Money, _Mapping]] = ..., currency_assumed: bool = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordHoldingsStatementResult(_message.Message):
    __slots__ = ("statement_id", "already_recorded")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ALREADY_RECORDED_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    already_recorded: bool
    def __init__(self, statement_id: _Optional[str] = ..., already_recorded: bool = ...) -> None: ...

class RecordHoldingParams(_message.Message):
    __slots__ = ("statement_id", "instrument_id", "unresolved_identifiers", "quantity", "market_value", "external_account_id", "side", "settle_date_quantity", "currency_assumed", "also_counted_in_cash", "acting_for")
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
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, statement_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., unresolved_identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., market_value: _Optional[_Union[Money, _Mapping]] = ..., external_account_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., settle_date_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., currency_assumed: bool = ..., also_counted_in_cash: bool = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordHoldingResult(_message.Message):
    __slots__ = ("holding_id", "resolved")
    HOLDING_ID_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_FIELD_NUMBER: _ClassVar[int]
    holding_id: str
    resolved: bool
    def __init__(self, holding_id: _Optional[str] = ..., resolved: bool = ...) -> None: ...

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
    asset_class: str
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    as_of_ns: int
    reason: MissReason
    observed_at_ns: int
    def __init__(self, source: _Optional[str] = ..., asset_class: _Optional[str] = ..., identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., as_of_ns: _Optional[int] = ..., reason: _Optional[_Union[MissReason, str]] = ..., observed_at_ns: _Optional[int] = ...) -> None: ...

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

class Identifier(_message.Message):
    __slots__ = ("scheme", "value", "source")
    SCHEME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    scheme: str
    value: str
    source: str
    def __init__(self, scheme: _Optional[str] = ..., value: _Optional[str] = ..., source: _Optional[str] = ...) -> None: ...

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
