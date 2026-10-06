from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class NotCarriedReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NOT_CARRIED_REASON_UNSPECIFIED: _ClassVar[NotCarriedReason]
    NOT_CARRIED_REASON_NO_CONTRACT_MEANING: _ClassVar[NotCarriedReason]
    NOT_CARRIED_REASON_NOT_CONVERTED: _ClassVar[NotCarriedReason]

class AccessLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCESS_LEVEL_UNSPECIFIED: _ClassVar[AccessLevel]
    ACCESS_LEVEL_READ: _ClassVar[AccessLevel]
    ACCESS_LEVEL_WRITE: _ClassVar[AccessLevel]
    ACCESS_LEVEL_ADMIN: _ClassVar[AccessLevel]

class SettingColumnType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SETTING_COLUMN_TYPE_UNSPECIFIED: _ClassVar[SettingColumnType]
    SETTING_COLUMN_TYPE_TEXT: _ClassVar[SettingColumnType]
    SETTING_COLUMN_TYPE_INTEGER: _ClassVar[SettingColumnType]
    SETTING_COLUMN_TYPE_DECIMAL: _ClassVar[SettingColumnType]
    SETTING_COLUMN_TYPE_DATE: _ClassVar[SettingColumnType]
    SETTING_COLUMN_TYPE_CHOICE: _ClassVar[SettingColumnType]
    SETTING_COLUMN_TYPE_EXTERNAL_ACCOUNT: _ClassVar[SettingColumnType]
    SETTING_COLUMN_TYPE_INSTRUMENT: _ClassVar[SettingColumnType]

class SettingType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SETTING_TYPE_UNSPECIFIED: _ClassVar[SettingType]
    SETTING_TYPE_STRING: _ClassVar[SettingType]
    SETTING_TYPE_INTEGER: _ClassVar[SettingType]
    SETTING_TYPE_BOOLEAN: _ClassVar[SettingType]
    SETTING_TYPE_CHOICE: _ClassVar[SettingType]
    SETTING_TYPE_TABLE: _ClassVar[SettingType]

class FigureState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FIGURE_STATE_UNSPECIFIED: _ClassVar[FigureState]
    FIGURE_STATE_OK: _ClassVar[FigureState]
    FIGURE_STATE_WARN: _ClassVar[FigureState]
    FIGURE_STATE_ERROR: _ClassVar[FigureState]

class ProvenanceKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PROVENANCE_KIND_UNSPECIFIED: _ClassVar[ProvenanceKind]
    PROVENANCE_KIND_REPORTED: _ClassVar[ProvenanceKind]
    PROVENANCE_KIND_SECOND_SOURCE: _ClassVar[ProvenanceKind]
    PROVENANCE_KIND_SUPPLIED: _ClassVar[ProvenanceKind]
    PROVENANCE_KIND_DERIVED: _ClassVar[ProvenanceKind]

class MoveOutcome(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MOVE_OUTCOME_UNSPECIFIED: _ClassVar[MoveOutcome]
    MOVE_OUTCOME_ARCHIVED: _ClassVar[MoveOutcome]
    MOVE_OUTCOME_RESTORED: _ClassVar[MoveOutcome]
    MOVE_OUTCOME_RETURNED: _ClassVar[MoveOutcome]
    MOVE_OUTCOME_DELETED: _ClassVar[MoveOutcome]

class TicketKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TICKET_KIND_UNSPECIFIED: _ClassVar[TicketKind]
    TICKET_KIND_DEFECT: _ClassVar[TicketKind]
    TICKET_KIND_DISCREPANCY: _ClassVar[TicketKind]
    TICKET_KIND_REQUEST: _ClassVar[TicketKind]
    TICKET_KIND_QUESTION: _ClassVar[TicketKind]

class TicketState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TICKET_STATE_UNSPECIFIED: _ClassVar[TicketState]
    TICKET_STATE_OPEN: _ClassVar[TicketState]
    TICKET_STATE_RESOLVED: _ClassVar[TicketState]
    TICKET_STATE_CLOSED: _ClassVar[TicketState]

class TicketResolution(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TICKET_RESOLUTION_UNSPECIFIED: _ClassVar[TicketResolution]
    TICKET_RESOLUTION_NOTE: _ClassVar[TicketResolution]
    TICKET_RESOLUTION_ANSWER: _ClassVar[TicketResolution]
    TICKET_RESOLUTION_VERSION: _ClassVar[TicketResolution]
    TICKET_RESOLUTION_WITHDRAWN: _ClassVar[TicketResolution]
    TICKET_RESOLUTION_DUPLICATE: _ClassVar[TicketResolution]
    TICKET_RESOLUTION_NOT_A_PROBLEM: _ClassVar[TicketResolution]

class TicketNoteKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TICKET_NOTE_KIND_UNSPECIFIED: _ClassVar[TicketNoteKind]
    TICKET_NOTE_KIND_NOTE: _ClassVar[TicketNoteKind]
    TICKET_NOTE_KIND_ADVICE: _ClassVar[TicketNoteKind]
    TICKET_NOTE_KIND_ANSWER: _ClassVar[TicketNoteKind]
    TICKET_NOTE_KIND_CHANGE: _ClassVar[TicketNoteKind]

class RefusalReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REFUSAL_REASON_UNSPECIFIED: _ClassVar[RefusalReason]
    REFUSAL_REASON_EXTERNAL_ACCOUNT_NOT_LINKED: _ClassVar[RefusalReason]
    REFUSAL_REASON_ACTOR_REQUIRED: _ClassVar[RefusalReason]
    REFUSAL_REASON_REASON_REQUIRED: _ClassVar[RefusalReason]
    REFUSAL_REASON_OPENING_BALANCE_RECORDED: _ClassVar[RefusalReason]
    REFUSAL_REASON_NO_OPENING_BALANCE: _ClassVar[RefusalReason]
    REFUSAL_REASON_BEFORE_OPENING_BALANCE: _ClassVar[RefusalReason]
    REFUSAL_REASON_LOTS_UNBALANCED: _ClassVar[RefusalReason]
    REFUSAL_REASON_BREAK_STATE: _ClassVar[RefusalReason]
    REFUSAL_REASON_LATER_ENTRIES_STAND: _ClassVar[RefusalReason]
    REFUSAL_REASON_IDEMPOTENCY_CONFLICT: _ClassVar[RefusalReason]
    REFUSAL_REASON_INCOMPLETE: _ClassVar[RefusalReason]
    REFUSAL_REASON_IDENTIFIER_HELD: _ClassVar[RefusalReason]
    REFUSAL_REASON_RECORD_CHANGED: _ClassVar[RefusalReason]
    REFUSAL_REASON_REFERENCE_UNAVAILABLE: _ClassVar[RefusalReason]
    REFUSAL_REASON_WITHIN_HOLD: _ClassVar[RefusalReason]
NOT_CARRIED_REASON_UNSPECIFIED: NotCarriedReason
NOT_CARRIED_REASON_NO_CONTRACT_MEANING: NotCarriedReason
NOT_CARRIED_REASON_NOT_CONVERTED: NotCarriedReason
ACCESS_LEVEL_UNSPECIFIED: AccessLevel
ACCESS_LEVEL_READ: AccessLevel
ACCESS_LEVEL_WRITE: AccessLevel
ACCESS_LEVEL_ADMIN: AccessLevel
SETTING_COLUMN_TYPE_UNSPECIFIED: SettingColumnType
SETTING_COLUMN_TYPE_TEXT: SettingColumnType
SETTING_COLUMN_TYPE_INTEGER: SettingColumnType
SETTING_COLUMN_TYPE_DECIMAL: SettingColumnType
SETTING_COLUMN_TYPE_DATE: SettingColumnType
SETTING_COLUMN_TYPE_CHOICE: SettingColumnType
SETTING_COLUMN_TYPE_EXTERNAL_ACCOUNT: SettingColumnType
SETTING_COLUMN_TYPE_INSTRUMENT: SettingColumnType
SETTING_TYPE_UNSPECIFIED: SettingType
SETTING_TYPE_STRING: SettingType
SETTING_TYPE_INTEGER: SettingType
SETTING_TYPE_BOOLEAN: SettingType
SETTING_TYPE_CHOICE: SettingType
SETTING_TYPE_TABLE: SettingType
FIGURE_STATE_UNSPECIFIED: FigureState
FIGURE_STATE_OK: FigureState
FIGURE_STATE_WARN: FigureState
FIGURE_STATE_ERROR: FigureState
PROVENANCE_KIND_UNSPECIFIED: ProvenanceKind
PROVENANCE_KIND_REPORTED: ProvenanceKind
PROVENANCE_KIND_SECOND_SOURCE: ProvenanceKind
PROVENANCE_KIND_SUPPLIED: ProvenanceKind
PROVENANCE_KIND_DERIVED: ProvenanceKind
MOVE_OUTCOME_UNSPECIFIED: MoveOutcome
MOVE_OUTCOME_ARCHIVED: MoveOutcome
MOVE_OUTCOME_RESTORED: MoveOutcome
MOVE_OUTCOME_RETURNED: MoveOutcome
MOVE_OUTCOME_DELETED: MoveOutcome
TICKET_KIND_UNSPECIFIED: TicketKind
TICKET_KIND_DEFECT: TicketKind
TICKET_KIND_DISCREPANCY: TicketKind
TICKET_KIND_REQUEST: TicketKind
TICKET_KIND_QUESTION: TicketKind
TICKET_STATE_UNSPECIFIED: TicketState
TICKET_STATE_OPEN: TicketState
TICKET_STATE_RESOLVED: TicketState
TICKET_STATE_CLOSED: TicketState
TICKET_RESOLUTION_UNSPECIFIED: TicketResolution
TICKET_RESOLUTION_NOTE: TicketResolution
TICKET_RESOLUTION_ANSWER: TicketResolution
TICKET_RESOLUTION_VERSION: TicketResolution
TICKET_RESOLUTION_WITHDRAWN: TicketResolution
TICKET_RESOLUTION_DUPLICATE: TicketResolution
TICKET_RESOLUTION_NOT_A_PROBLEM: TicketResolution
TICKET_NOTE_KIND_UNSPECIFIED: TicketNoteKind
TICKET_NOTE_KIND_NOTE: TicketNoteKind
TICKET_NOTE_KIND_ADVICE: TicketNoteKind
TICKET_NOTE_KIND_ANSWER: TicketNoteKind
TICKET_NOTE_KIND_CHANGE: TicketNoteKind
REFUSAL_REASON_UNSPECIFIED: RefusalReason
REFUSAL_REASON_EXTERNAL_ACCOUNT_NOT_LINKED: RefusalReason
REFUSAL_REASON_ACTOR_REQUIRED: RefusalReason
REFUSAL_REASON_REASON_REQUIRED: RefusalReason
REFUSAL_REASON_OPENING_BALANCE_RECORDED: RefusalReason
REFUSAL_REASON_NO_OPENING_BALANCE: RefusalReason
REFUSAL_REASON_BEFORE_OPENING_BALANCE: RefusalReason
REFUSAL_REASON_LOTS_UNBALANCED: RefusalReason
REFUSAL_REASON_BREAK_STATE: RefusalReason
REFUSAL_REASON_LATER_ENTRIES_STAND: RefusalReason
REFUSAL_REASON_IDEMPOTENCY_CONFLICT: RefusalReason
REFUSAL_REASON_INCOMPLETE: RefusalReason
REFUSAL_REASON_IDENTIFIER_HELD: RefusalReason
REFUSAL_REASON_RECORD_CHANGED: RefusalReason
REFUSAL_REASON_REFERENCE_UNAVAILABLE: RefusalReason
REFUSAL_REASON_WITHIN_HOLD: RefusalReason

class RegisterRequest(_message.Message):
    __slots__ = ("schema_version", "interface", "settings", "reads_external_accounts", "declaration", "tools")
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    READS_EXTERNAL_ACCOUNTS_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TOOLS_FIELD_NUMBER: _ClassVar[int]
    schema_version: str
    interface: InterfaceDeclaration
    settings: _containers.RepeatedCompositeFieldContainer[SettingDeclaration]
    reads_external_accounts: bool
    declaration: PluginDeclaration
    tools: _containers.RepeatedCompositeFieldContainer[ToolDeclaration]
    def __init__(self, schema_version: _Optional[str] = ..., interface: _Optional[_Union[InterfaceDeclaration, _Mapping]] = ..., settings: _Optional[_Iterable[_Union[SettingDeclaration, _Mapping]]] = ..., reads_external_accounts: bool = ..., declaration: _Optional[_Union[PluginDeclaration, _Mapping]] = ..., tools: _Optional[_Iterable[_Union[ToolDeclaration, _Mapping]]] = ...) -> None: ...

class ToolDeclaration(_message.Message):
    __slots__ = ("name", "title", "description", "method", "path", "levels", "reads", "input_schema", "output_schema", "roles")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    LEVELS_FIELD_NUMBER: _ClassVar[int]
    READS_FIELD_NUMBER: _ClassVar[int]
    INPUT_SCHEMA_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_SCHEMA_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    name: str
    title: str
    description: str
    method: str
    path: str
    levels: _containers.RepeatedScalarFieldContainer[AccessLevel]
    reads: bool
    input_schema: str
    output_schema: str
    roles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, name: _Optional[str] = ..., title: _Optional[str] = ..., description: _Optional[str] = ..., method: _Optional[str] = ..., path: _Optional[str] = ..., levels: _Optional[_Iterable[_Union[AccessLevel, str]]] = ..., reads: bool = ..., input_schema: _Optional[str] = ..., output_schema: _Optional[str] = ..., roles: _Optional[_Iterable[str]] = ...) -> None: ...

class PluginDeclaration(_message.Message):
    __slots__ = ("secret_settings", "not_carried", "storage")
    SECRET_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    NOT_CARRIED_FIELD_NUMBER: _ClassVar[int]
    STORAGE_FIELD_NUMBER: _ClassVar[int]
    secret_settings: _containers.RepeatedScalarFieldContainer[str]
    not_carried: _containers.RepeatedCompositeFieldContainer[NotCarried]
    storage: StorageDeclaration
    def __init__(self, secret_settings: _Optional[_Iterable[str]] = ..., not_carried: _Optional[_Iterable[_Union[NotCarried, _Mapping]]] = ..., storage: _Optional[_Union[StorageDeclaration, _Mapping]] = ...) -> None: ...

class NotCarried(_message.Message):
    __slots__ = ("role", "scheme", "name", "reason")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    SCHEME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    role: str
    scheme: str
    name: str
    reason: NotCarriedReason
    def __init__(self, role: _Optional[str] = ..., scheme: _Optional[str] = ..., name: _Optional[str] = ..., reason: _Optional[_Union[NotCarriedReason, str]] = ...) -> None: ...

class StorageDeclaration(_message.Message):
    __slots__ = ("retention_days", "record_kinds")
    RETENTION_DAYS_FIELD_NUMBER: _ClassVar[int]
    RECORD_KINDS_FIELD_NUMBER: _ClassVar[int]
    retention_days: int
    record_kinds: _containers.RepeatedCompositeFieldContainer[RawRecordKind]
    def __init__(self, retention_days: _Optional[int] = ..., record_kinds: _Optional[_Iterable[_Union[RawRecordKind, _Mapping]]] = ...) -> None: ...

class RawRecordKind(_message.Message):
    __slots__ = ("name", "label", "window_days", "archivable")
    NAME_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    WINDOW_DAYS_FIELD_NUMBER: _ClassVar[int]
    ARCHIVABLE_FIELD_NUMBER: _ClassVar[int]
    name: str
    label: str
    window_days: int
    archivable: bool
    def __init__(self, name: _Optional[str] = ..., label: _Optional[str] = ..., window_days: _Optional[int] = ..., archivable: bool = ...) -> None: ...

class InterfaceDeclaration(_message.Message):
    __slots__ = ("loopback_port", "title", "pages")
    LOOPBACK_PORT_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    PAGES_FIELD_NUMBER: _ClassVar[int]
    loopback_port: int
    title: str
    pages: _containers.RepeatedCompositeFieldContainer[PageDeclaration]
    def __init__(self, loopback_port: _Optional[int] = ..., title: _Optional[str] = ..., pages: _Optional[_Iterable[_Union[PageDeclaration, _Mapping]]] = ...) -> None: ...

class PageDeclaration(_message.Message):
    __slots__ = ("path", "title", "levels", "roles")
    PATH_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    LEVELS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    path: str
    title: str
    levels: _containers.RepeatedScalarFieldContainer[AccessLevel]
    roles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, path: _Optional[str] = ..., title: _Optional[str] = ..., levels: _Optional[_Iterable[_Union[AccessLevel, str]]] = ..., roles: _Optional[_Iterable[str]] = ...) -> None: ...

class SettingDeclaration(_message.Message):
    __slots__ = ("name", "type", "required", "secret", "description", "label", "default_value", "unit", "choices", "applies_when", "developer", "columns", "most_rows", "roles")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    SECRET_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_VALUE_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    CHOICES_FIELD_NUMBER: _ClassVar[int]
    APPLIES_WHEN_FIELD_NUMBER: _ClassVar[int]
    DEVELOPER_FIELD_NUMBER: _ClassVar[int]
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    MOST_ROWS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: SettingType
    required: bool
    secret: bool
    description: str
    label: str
    default_value: str
    unit: str
    choices: _containers.RepeatedCompositeFieldContainer[SettingChoice]
    applies_when: SettingCondition
    developer: bool
    columns: _containers.RepeatedCompositeFieldContainer[SettingColumn]
    most_rows: int
    roles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[SettingType, str]] = ..., required: bool = ..., secret: bool = ..., description: _Optional[str] = ..., label: _Optional[str] = ..., default_value: _Optional[str] = ..., unit: _Optional[str] = ..., choices: _Optional[_Iterable[_Union[SettingChoice, _Mapping]]] = ..., applies_when: _Optional[_Union[SettingCondition, _Mapping]] = ..., developer: bool = ..., columns: _Optional[_Iterable[_Union[SettingColumn, _Mapping]]] = ..., most_rows: _Optional[int] = ..., roles: _Optional[_Iterable[str]] = ...) -> None: ...

class SettingColumn(_message.Message):
    __slots__ = ("name", "label", "type", "required", "description", "choices")
    NAME_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CHOICES_FIELD_NUMBER: _ClassVar[int]
    name: str
    label: str
    type: SettingColumnType
    required: bool
    description: str
    choices: _containers.RepeatedCompositeFieldContainer[SettingChoice]
    def __init__(self, name: _Optional[str] = ..., label: _Optional[str] = ..., type: _Optional[_Union[SettingColumnType, str]] = ..., required: bool = ..., description: _Optional[str] = ..., choices: _Optional[_Iterable[_Union[SettingChoice, _Mapping]]] = ...) -> None: ...

class SettingChoice(_message.Message):
    __slots__ = ("value", "label", "description")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    value: str
    label: str
    description: str
    def __init__(self, value: _Optional[str] = ..., label: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class SettingCondition(_message.Message):
    __slots__ = ("setting", "one_of")
    SETTING_FIELD_NUMBER: _ClassVar[int]
    ONE_OF_FIELD_NUMBER: _ClassVar[int]
    setting: str
    one_of: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, setting: _Optional[str] = ..., one_of: _Optional[_Iterable[str]] = ...) -> None: ...

class RegisterReply(_message.Message):
    __slots__ = ("admitted", "deployment_id", "refusal_reason", "publish_grants", "subscribe_grants", "instance_id", "roles")
    ADMITTED_FIELD_NUMBER: _ClassVar[int]
    DEPLOYMENT_ID_FIELD_NUMBER: _ClassVar[int]
    REFUSAL_REASON_FIELD_NUMBER: _ClassVar[int]
    PUBLISH_GRANTS_FIELD_NUMBER: _ClassVar[int]
    SUBSCRIBE_GRANTS_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    admitted: bool
    deployment_id: str
    refusal_reason: str
    publish_grants: _containers.RepeatedScalarFieldContainer[str]
    subscribe_grants: _containers.RepeatedScalarFieldContainer[str]
    instance_id: str
    roles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, admitted: bool = ..., deployment_id: _Optional[str] = ..., refusal_reason: _Optional[str] = ..., publish_grants: _Optional[_Iterable[str]] = ..., subscribe_grants: _Optional[_Iterable[str]] = ..., instance_id: _Optional[str] = ..., roles: _Optional[_Iterable[str]] = ...) -> None: ...

class HeartbeatRequest(_message.Message):
    __slots__ = ("healthy", "detail", "figures", "not_carried_seen", "stored")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    NOT_CARRIED_SEEN_FIELD_NUMBER: _ClassVar[int]
    STORED_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    detail: str
    figures: _containers.RepeatedCompositeFieldContainer[PluginFigure]
    not_carried_seen: _containers.RepeatedCompositeFieldContainer[NotCarriedSeen]
    stored: _containers.RepeatedCompositeFieldContainer[StoredSpan]
    def __init__(self, healthy: bool = ..., detail: _Optional[str] = ..., figures: _Optional[_Iterable[_Union[PluginFigure, _Mapping]]] = ..., not_carried_seen: _Optional[_Iterable[_Union[NotCarriedSeen, _Mapping]]] = ..., stored: _Optional[_Iterable[_Union[StoredSpan, _Mapping]]] = ...) -> None: ...

class StoredSpan(_message.Message):
    __slots__ = ("record_kind", "record_count", "first_received_ns", "last_received_ns")
    RECORD_KIND_FIELD_NUMBER: _ClassVar[int]
    RECORD_COUNT_FIELD_NUMBER: _ClassVar[int]
    FIRST_RECEIVED_NS_FIELD_NUMBER: _ClassVar[int]
    LAST_RECEIVED_NS_FIELD_NUMBER: _ClassVar[int]
    record_kind: str
    record_count: int
    first_received_ns: int
    last_received_ns: int
    def __init__(self, record_kind: _Optional[str] = ..., record_count: _Optional[int] = ..., first_received_ns: _Optional[int] = ..., last_received_ns: _Optional[int] = ...) -> None: ...

class NotCarriedSeen(_message.Message):
    __slots__ = ("scheme", "name", "count")
    SCHEME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    scheme: str
    name: str
    count: int
    def __init__(self, scheme: _Optional[str] = ..., name: _Optional[str] = ..., count: _Optional[int] = ...) -> None: ...

class PluginFigure(_message.Message):
    __slots__ = ("label", "count", "decimal", "text", "at_ns", "as_of_ns", "state", "why")
    LABEL_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    DECIMAL_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    AT_NS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    WHY_FIELD_NUMBER: _ClassVar[int]
    label: str
    count: int
    decimal: Decimal
    text: str
    at_ns: int
    as_of_ns: int
    state: FigureState
    why: str
    def __init__(self, label: _Optional[str] = ..., count: _Optional[int] = ..., decimal: _Optional[_Union[Decimal, _Mapping]] = ..., text: _Optional[str] = ..., at_ns: _Optional[int] = ..., as_of_ns: _Optional[int] = ..., state: _Optional[_Union[FigureState, str]] = ..., why: _Optional[str] = ...) -> None: ...

class Decimal(_message.Message):
    __slots__ = ("high", "low", "scale")
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    SCALE_FIELD_NUMBER: _ClassVar[int]
    high: int
    low: int
    scale: int
    def __init__(self, high: _Optional[int] = ..., low: _Optional[int] = ..., scale: _Optional[int] = ...) -> None: ...

class AsReported(_message.Message):
    __slots__ = ("scheme", "code", "text")
    SCHEME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    scheme: str
    code: str
    text: str
    def __init__(self, scheme: _Optional[str] = ..., code: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...

class RawRecordRef(_message.Message):
    __slots__ = ("instance_id", "key")
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    key: str
    def __init__(self, instance_id: _Optional[str] = ..., key: _Optional[str] = ...) -> None: ...

class Provenance(_message.Message):
    __slots__ = ("field", "kind", "raw_record", "source", "person", "rule")
    FIELD_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    PERSON_FIELD_NUMBER: _ClassVar[int]
    RULE_FIELD_NUMBER: _ClassVar[int]
    field: str
    kind: ProvenanceKind
    raw_record: RawRecordRef
    source: str
    person: str
    rule: str
    def __init__(self, field: _Optional[str] = ..., kind: _Optional[_Union[ProvenanceKind, str]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., source: _Optional[str] = ..., person: _Optional[str] = ..., rule: _Optional[str] = ...) -> None: ...

class Backfill(_message.Message):
    __slots__ = ("contract_version", "field")
    CONTRACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    FIELD_FIELD_NUMBER: _ClassVar[int]
    contract_version: str
    field: str
    def __init__(self, contract_version: _Optional[str] = ..., field: _Optional[str] = ...) -> None: ...

class HeartbeatReply(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class LeaveRequest(_message.Message):
    __slots__ = ("reason",)
    REASON_FIELD_NUMBER: _ClassVar[int]
    reason: str
    def __init__(self, reason: _Optional[str] = ...) -> None: ...

class LeaveReply(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class WatchSettingsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SettingsDelivery(_message.Message):
    __slots__ = ("values", "missing_required")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    MISSING_REQUIRED_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[SettingValue]
    missing_required: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[_Union[SettingValue, _Mapping]]] = ..., missing_required: _Optional[_Iterable[str]] = ...) -> None: ...

class SettingValue(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: str
    def __init__(self, name: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class CallerAssertion(_message.Message):
    __slots__ = ("claims", "signature", "key_id")
    CLAIMS_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    claims: bytes
    signature: bytes
    key_id: str
    def __init__(self, claims: _Optional[bytes] = ..., signature: _Optional[bytes] = ..., key_id: _Optional[str] = ...) -> None: ...

class CallerClaims(_message.Message):
    __slots__ = ("subject", "display_name", "audience_instance_id", "level", "read_account_ids", "write_account_ids", "issued_at_ns", "expires_at_ns", "assertion_id", "deployment_admin", "delegation_id", "client_name", "tool_name", "roles")
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    READ_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    WRITE_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    ISSUED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ASSERTION_ID_FIELD_NUMBER: _ClassVar[int]
    DEPLOYMENT_ADMIN_FIELD_NUMBER: _ClassVar[int]
    DELEGATION_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_NAME_FIELD_NUMBER: _ClassVar[int]
    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    subject: str
    display_name: str
    audience_instance_id: str
    level: AccessLevel
    read_account_ids: _containers.RepeatedScalarFieldContainer[str]
    write_account_ids: _containers.RepeatedScalarFieldContainer[str]
    issued_at_ns: int
    expires_at_ns: int
    assertion_id: str
    deployment_admin: bool
    delegation_id: str
    client_name: str
    tool_name: str
    roles: _containers.RepeatedCompositeFieldContainer[RoleAccess]
    def __init__(self, subject: _Optional[str] = ..., display_name: _Optional[str] = ..., audience_instance_id: _Optional[str] = ..., level: _Optional[_Union[AccessLevel, str]] = ..., read_account_ids: _Optional[_Iterable[str]] = ..., write_account_ids: _Optional[_Iterable[str]] = ..., issued_at_ns: _Optional[int] = ..., expires_at_ns: _Optional[int] = ..., assertion_id: _Optional[str] = ..., deployment_admin: bool = ..., delegation_id: _Optional[str] = ..., client_name: _Optional[str] = ..., tool_name: _Optional[str] = ..., roles: _Optional[_Iterable[_Union[RoleAccess, _Mapping]]] = ...) -> None: ...

class RoleAccess(_message.Message):
    __slots__ = ("role", "level", "read_positions", "write_positions")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    READ_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    WRITE_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    role: str
    level: AccessLevel
    read_positions: _containers.RepeatedScalarFieldContainer[int]
    write_positions: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, role: _Optional[str] = ..., level: _Optional[_Union[AccessLevel, str]] = ..., read_positions: _Optional[_Iterable[int]] = ..., write_positions: _Optional[_Iterable[int]] = ...) -> None: ...

class PluginAccessRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PluginAccessReply(_message.Message):
    __slots__ = ("user_groups", "people")
    USER_GROUPS_FIELD_NUMBER: _ClassVar[int]
    PEOPLE_FIELD_NUMBER: _ClassVar[int]
    user_groups: _containers.RepeatedCompositeFieldContainer[UserGroupAccess]
    people: _containers.RepeatedCompositeFieldContainer[PersonAccess]
    def __init__(self, user_groups: _Optional[_Iterable[_Union[UserGroupAccess, _Mapping]]] = ..., people: _Optional[_Iterable[_Union[PersonAccess, _Mapping]]] = ...) -> None: ...

class UserGroupAccess(_message.Message):
    __slots__ = ("user_group_id", "name", "read_account_ids", "write_account_ids", "roles")
    USER_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    READ_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    WRITE_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    user_group_id: str
    name: str
    read_account_ids: _containers.RepeatedScalarFieldContainer[str]
    write_account_ids: _containers.RepeatedScalarFieldContainer[str]
    roles: _containers.RepeatedCompositeFieldContainer[RoleAccess]
    def __init__(self, user_group_id: _Optional[str] = ..., name: _Optional[str] = ..., read_account_ids: _Optional[_Iterable[str]] = ..., write_account_ids: _Optional[_Iterable[str]] = ..., roles: _Optional[_Iterable[_Union[RoleAccess, _Mapping]]] = ...) -> None: ...

class PersonAccess(_message.Message):
    __slots__ = ("subject", "display_name", "user_group_ids", "last_signed_in_at_ns", "read_account_ids", "write_account_ids", "roles")
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    LAST_SIGNED_IN_AT_NS_FIELD_NUMBER: _ClassVar[int]
    READ_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    WRITE_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    subject: str
    display_name: str
    user_group_ids: _containers.RepeatedScalarFieldContainer[str]
    last_signed_in_at_ns: int
    read_account_ids: _containers.RepeatedScalarFieldContainer[str]
    write_account_ids: _containers.RepeatedScalarFieldContainer[str]
    roles: _containers.RepeatedCompositeFieldContainer[RoleAccess]
    def __init__(self, subject: _Optional[str] = ..., display_name: _Optional[str] = ..., user_group_ids: _Optional[_Iterable[str]] = ..., last_signed_in_at_ns: _Optional[int] = ..., read_account_ids: _Optional[_Iterable[str]] = ..., write_account_ids: _Optional[_Iterable[str]] = ..., roles: _Optional[_Iterable[_Union[RoleAccess, _Mapping]]] = ...) -> None: ...

class WatchAccountScopeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AccountScopeDelivery(_message.Message):
    __slots__ = ("read_account_ids", "write_account_ids", "links")
    READ_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    WRITE_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    LINKS_FIELD_NUMBER: _ClassVar[int]
    read_account_ids: _containers.RepeatedScalarFieldContainer[str]
    write_account_ids: _containers.RepeatedScalarFieldContainer[str]
    links: _containers.RepeatedCompositeFieldContainer[LinkedExternalAccount]
    def __init__(self, read_account_ids: _Optional[_Iterable[str]] = ..., write_account_ids: _Optional[_Iterable[str]] = ..., links: _Optional[_Iterable[_Union[LinkedExternalAccount, _Mapping]]] = ...) -> None: ...

class LinkedExternalAccount(_message.Message):
    __slots__ = ("external_account_id", "account_id", "account_name")
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_NAME_FIELD_NUMBER: _ClassVar[int]
    external_account_id: str
    account_id: str
    account_name: str
    def __init__(self, external_account_id: _Optional[str] = ..., account_id: _Optional[str] = ..., account_name: _Optional[str] = ...) -> None: ...

class RecordMoveRequest(_message.Message):
    __slots__ = ("record_kind", "unit", "record_count", "first_received_ns", "last_received_ns", "outcome", "rule")
    RECORD_KIND_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    RECORD_COUNT_FIELD_NUMBER: _ClassVar[int]
    FIRST_RECEIVED_NS_FIELD_NUMBER: _ClassVar[int]
    LAST_RECEIVED_NS_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    RULE_FIELD_NUMBER: _ClassVar[int]
    record_kind: str
    unit: str
    record_count: int
    first_received_ns: int
    last_received_ns: int
    outcome: MoveOutcome
    rule: str
    def __init__(self, record_kind: _Optional[str] = ..., unit: _Optional[str] = ..., record_count: _Optional[int] = ..., first_received_ns: _Optional[int] = ..., last_received_ns: _Optional[int] = ..., outcome: _Optional[_Union[MoveOutcome, str]] = ..., rule: _Optional[str] = ...) -> None: ...

class RecordMoveReply(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class FileTicketRequest(_message.Message):
    __slots__ = ("title", "seen", "kind", "concerns", "step", "operation", "reason", "paths", "references", "idempotency_key")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    SEEN_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    CONCERNS_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    OPERATION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    PATHS_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    title: str
    seen: str
    kind: TicketKind
    concerns: TicketSubject
    step: str
    operation: str
    reason: str
    paths: _containers.RepeatedScalarFieldContainer[str]
    references: _containers.RepeatedCompositeFieldContainer[TicketReference]
    idempotency_key: str
    def __init__(self, title: _Optional[str] = ..., seen: _Optional[str] = ..., kind: _Optional[_Union[TicketKind, str]] = ..., concerns: _Optional[_Union[TicketSubject, _Mapping]] = ..., step: _Optional[str] = ..., operation: _Optional[str] = ..., reason: _Optional[str] = ..., paths: _Optional[_Iterable[str]] = ..., references: _Optional[_Iterable[_Union[TicketReference, _Mapping]]] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class TicketSubject(_message.Message):
    __slots__ = ("kind", "instance", "version")
    KIND_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    kind: str
    instance: str
    version: str
    def __init__(self, kind: _Optional[str] = ..., instance: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class TicketReference(_message.Message):
    __slots__ = ("kind", "value", "account_id")
    KIND_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    kind: str
    value: str
    account_id: str
    def __init__(self, kind: _Optional[str] = ..., value: _Optional[str] = ..., account_id: _Optional[str] = ...) -> None: ...

class FileTicketReply(_message.Message):
    __slots__ = ("ticket_id", "outcome", "seen_count")
    TICKET_ID_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    SEEN_COUNT_FIELD_NUMBER: _ClassVar[int]
    ticket_id: str
    outcome: str
    seen_count: int
    def __init__(self, ticket_id: _Optional[str] = ..., outcome: _Optional[str] = ..., seen_count: _Optional[int] = ...) -> None: ...

class ReadFiledTicketsRequest(_message.Message):
    __slots__ = ("ticket_ids", "idempotency_keys", "cursor")
    TICKET_IDS_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEYS_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    ticket_ids: _containers.RepeatedScalarFieldContainer[str]
    idempotency_keys: _containers.RepeatedScalarFieldContainer[str]
    cursor: str
    def __init__(self, ticket_ids: _Optional[_Iterable[str]] = ..., idempotency_keys: _Optional[_Iterable[str]] = ..., cursor: _Optional[str] = ...) -> None: ...

class ReadFiledTicketsReply(_message.Message):
    __slots__ = ("tickets", "next_cursor")
    TICKETS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    tickets: _containers.RepeatedCompositeFieldContainer[FiledTicket]
    next_cursor: str
    def __init__(self, tickets: _Optional[_Iterable[_Union[FiledTicket, _Mapping]]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class FiledTicket(_message.Message):
    __slots__ = ("ticket_id", "idempotency_key", "state", "resolution", "seen_count", "first_seen_ns", "last_seen_ns", "answers")
    TICKET_ID_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    SEEN_COUNT_FIELD_NUMBER: _ClassVar[int]
    FIRST_SEEN_NS_FIELD_NUMBER: _ClassVar[int]
    LAST_SEEN_NS_FIELD_NUMBER: _ClassVar[int]
    ANSWERS_FIELD_NUMBER: _ClassVar[int]
    ticket_id: str
    idempotency_key: str
    state: TicketState
    resolution: TicketResolution
    seen_count: int
    first_seen_ns: int
    last_seen_ns: int
    answers: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, ticket_id: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., state: _Optional[_Union[TicketState, str]] = ..., resolution: _Optional[_Union[TicketResolution, str]] = ..., seen_count: _Optional[int] = ..., first_seen_ns: _Optional[int] = ..., last_seen_ns: _Optional[int] = ..., answers: _Optional[_Iterable[str]] = ...) -> None: ...

class Refusal(_message.Message):
    __slots__ = ("reason", "fields")
    REASON_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    reason: RefusalReason
    fields: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, reason: _Optional[_Union[RefusalReason, str]] = ..., fields: _Optional[_Iterable[str]] = ...) -> None: ...
