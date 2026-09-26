from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MissReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MISS_REASON_UNSPECIFIED: _ClassVar[MissReason]
    MISS_REASON_NOT_FOUND: _ClassVar[MissReason]
    MISS_REASON_AMBIGUOUS: _ClassVar[MissReason]
MISS_REASON_UNSPECIFIED: MissReason
MISS_REASON_NOT_FOUND: MissReason
MISS_REASON_AMBIGUOUS: MissReason

class Published(_message.Message):
    __slots__ = ("message_id",)
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    def __init__(self, message_id: _Optional[str] = ...) -> None: ...

class ReportSyncStatusParams(_message.Message):
    __slots__ = ("source", "last_synced_at_ns", "connection_healthy", "status_detail", "observed_at_ns", "external_account_id")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNCED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CONNECTION_HEALTHY_FIELD_NUMBER: _ClassVar[int]
    STATUS_DETAIL_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    source: str
    last_synced_at_ns: int
    connection_healthy: bool
    status_detail: str
    observed_at_ns: int
    external_account_id: str
    def __init__(self, source: _Optional[str] = ..., last_synced_at_ns: _Optional[int] = ..., connection_healthy: bool = ..., status_detail: _Optional[str] = ..., observed_at_ns: _Optional[int] = ..., external_account_id: _Optional[str] = ...) -> None: ...

class RecordHoldingsStatementParams(_message.Message):
    __slots__ = ("source", "external_statement_id", "as_of_date", "read_at_ns", "expected_rows")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    READ_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_ROWS_FIELD_NUMBER: _ClassVar[int]
    source: str
    external_statement_id: str
    as_of_date: str
    read_at_ns: int
    expected_rows: int
    def __init__(self, source: _Optional[str] = ..., external_statement_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., read_at_ns: _Optional[int] = ..., expected_rows: _Optional[int] = ...) -> None: ...

class RecordHoldingsStatementResult(_message.Message):
    __slots__ = ("statement_id", "already_recorded")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ALREADY_RECORDED_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    already_recorded: bool
    def __init__(self, statement_id: _Optional[str] = ..., already_recorded: bool = ...) -> None: ...

class RecordHoldingParams(_message.Message):
    __slots__ = ("statement_id", "instrument_id", "unresolved_identifiers", "quantity_scaled_1e8", "market_value_scaled_1e8", "currency", "external_account_id")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_SCALED_1E8_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_SCALED_1E8_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    instrument_id: str
    unresolved_identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    quantity_scaled_1e8: int
    market_value_scaled_1e8: int
    currency: str
    external_account_id: str
    def __init__(self, statement_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., unresolved_identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., quantity_scaled_1e8: _Optional[int] = ..., market_value_scaled_1e8: _Optional[int] = ..., currency: _Optional[str] = ..., external_account_id: _Optional[str] = ...) -> None: ...

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
    __slots__ = ("found", "instrument_id", "miss_reason")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    MISS_REASON_FIELD_NUMBER: _ClassVar[int]
    found: bool
    instrument_id: str
    miss_reason: MissReason
    def __init__(self, found: bool = ..., instrument_id: _Optional[str] = ..., miss_reason: _Optional[_Union[MissReason, str]] = ...) -> None: ...

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

class Identifier(_message.Message):
    __slots__ = ("scheme", "value", "source")
    SCHEME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    scheme: str
    value: str
    source: str
    def __init__(self, scheme: _Optional[str] = ..., value: _Optional[str] = ..., source: _Optional[str] = ...) -> None: ...
