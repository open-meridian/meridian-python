from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SettingType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SETTING_TYPE_UNSPECIFIED: _ClassVar[SettingType]
    SETTING_TYPE_STRING: _ClassVar[SettingType]
    SETTING_TYPE_INTEGER: _ClassVar[SettingType]
    SETTING_TYPE_BOOLEAN: _ClassVar[SettingType]
SETTING_TYPE_UNSPECIFIED: SettingType
SETTING_TYPE_STRING: SettingType
SETTING_TYPE_INTEGER: SettingType
SETTING_TYPE_BOOLEAN: SettingType

class RegisterRequest(_message.Message):
    __slots__ = ("schema_version", "interface", "settings", "reads_external_accounts")
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    READS_EXTERNAL_ACCOUNTS_FIELD_NUMBER: _ClassVar[int]
    schema_version: str
    interface: InterfaceDeclaration
    settings: _containers.RepeatedCompositeFieldContainer[SettingDeclaration]
    reads_external_accounts: bool
    def __init__(self, schema_version: _Optional[str] = ..., interface: _Optional[_Union[InterfaceDeclaration, _Mapping]] = ..., settings: _Optional[_Iterable[_Union[SettingDeclaration, _Mapping]]] = ..., reads_external_accounts: bool = ...) -> None: ...

class InterfaceDeclaration(_message.Message):
    __slots__ = ("loopback_port", "title")
    LOOPBACK_PORT_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    loopback_port: int
    title: str
    def __init__(self, loopback_port: _Optional[int] = ..., title: _Optional[str] = ...) -> None: ...

class SettingDeclaration(_message.Message):
    __slots__ = ("name", "type", "required", "secret", "description")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    SECRET_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: SettingType
    required: bool
    secret: bool
    description: str
    def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[SettingType, str]] = ..., required: bool = ..., secret: bool = ..., description: _Optional[str] = ...) -> None: ...

class RegisterReply(_message.Message):
    __slots__ = ("admitted", "deployment_id", "refusal_reason", "publish_grants", "subscribe_grants", "instance_id", "roles", "tags")
    ADMITTED_FIELD_NUMBER: _ClassVar[int]
    DEPLOYMENT_ID_FIELD_NUMBER: _ClassVar[int]
    REFUSAL_REASON_FIELD_NUMBER: _ClassVar[int]
    PUBLISH_GRANTS_FIELD_NUMBER: _ClassVar[int]
    SUBSCRIBE_GRANTS_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    admitted: bool
    deployment_id: str
    refusal_reason: str
    publish_grants: _containers.RepeatedScalarFieldContainer[str]
    subscribe_grants: _containers.RepeatedScalarFieldContainer[str]
    instance_id: str
    roles: _containers.RepeatedScalarFieldContainer[str]
    tags: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, admitted: bool = ..., deployment_id: _Optional[str] = ..., refusal_reason: _Optional[str] = ..., publish_grants: _Optional[_Iterable[str]] = ..., subscribe_grants: _Optional[_Iterable[str]] = ..., instance_id: _Optional[str] = ..., roles: _Optional[_Iterable[str]] = ..., tags: _Optional[_Iterable[str]] = ...) -> None: ...

class HeartbeatRequest(_message.Message):
    __slots__ = ("healthy", "detail")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    detail: str
    def __init__(self, healthy: bool = ..., detail: _Optional[str] = ...) -> None: ...

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
    __slots__ = ("subject", "display_name", "audience_instance_id", "access", "issued_at_ns", "expires_at_ns", "assertion_id")
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    ISSUED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ASSERTION_ID_FIELD_NUMBER: _ClassVar[int]
    subject: str
    display_name: str
    audience_instance_id: str
    access: _containers.RepeatedCompositeFieldContainer[TagAccess]
    issued_at_ns: int
    expires_at_ns: int
    assertion_id: str
    def __init__(self, subject: _Optional[str] = ..., display_name: _Optional[str] = ..., audience_instance_id: _Optional[str] = ..., access: _Optional[_Iterable[_Union[TagAccess, _Mapping]]] = ..., issued_at_ns: _Optional[int] = ..., expires_at_ns: _Optional[int] = ..., assertion_id: _Optional[str] = ...) -> None: ...

class TagAccess(_message.Message):
    __slots__ = ("tag", "read_account_ids", "write_account_ids")
    TAG_FIELD_NUMBER: _ClassVar[int]
    READ_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    WRITE_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    tag: str
    read_account_ids: _containers.RepeatedScalarFieldContainer[str]
    write_account_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, tag: _Optional[str] = ..., read_account_ids: _Optional[_Iterable[str]] = ..., write_account_ids: _Optional[_Iterable[str]] = ...) -> None: ...

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
    __slots__ = ("user_group_id", "name", "access")
    USER_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    user_group_id: str
    name: str
    access: _containers.RepeatedCompositeFieldContainer[TagAccess]
    def __init__(self, user_group_id: _Optional[str] = ..., name: _Optional[str] = ..., access: _Optional[_Iterable[_Union[TagAccess, _Mapping]]] = ...) -> None: ...

class PersonAccess(_message.Message):
    __slots__ = ("subject", "display_name", "user_group_ids", "last_signed_in_at_ns", "access")
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    LAST_SIGNED_IN_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    subject: str
    display_name: str
    user_group_ids: _containers.RepeatedScalarFieldContainer[str]
    last_signed_in_at_ns: int
    access: _containers.RepeatedCompositeFieldContainer[TagAccess]
    def __init__(self, subject: _Optional[str] = ..., display_name: _Optional[str] = ..., user_group_ids: _Optional[_Iterable[str]] = ..., last_signed_in_at_ns: _Optional[int] = ..., access: _Optional[_Iterable[_Union[TagAccess, _Mapping]]] = ...) -> None: ...

class WatchAccountScopeRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AccountScopeDelivery(_message.Message):
    __slots__ = ("read_account_ids", "write_account_ids")
    READ_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    WRITE_ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    read_account_ids: _containers.RepeatedScalarFieldContainer[str]
    write_account_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, read_account_ids: _Optional[_Iterable[str]] = ..., write_account_ids: _Optional[_Iterable[str]] = ...) -> None: ...
