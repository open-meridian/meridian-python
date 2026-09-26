from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class MessageMeta(_message.Message):
    __slots__ = ("message_id", "correlation_id", "causation_id", "publisher_instance_id", "topic", "schema_version", "published_at_ns", "acting_for_subject", "account_scope")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    CAUSATION_ID_FIELD_NUMBER: _ClassVar[int]
    PUBLISHER_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_SUBJECT_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_SCOPE_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    correlation_id: str
    causation_id: str
    publisher_instance_id: str
    topic: str
    schema_version: str
    published_at_ns: int
    acting_for_subject: str
    account_scope: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, message_id: _Optional[str] = ..., correlation_id: _Optional[str] = ..., causation_id: _Optional[str] = ..., publisher_instance_id: _Optional[str] = ..., topic: _Optional[str] = ..., schema_version: _Optional[str] = ..., published_at_ns: _Optional[int] = ..., acting_for_subject: _Optional[str] = ..., account_scope: _Optional[_Iterable[str]] = ...) -> None: ...
