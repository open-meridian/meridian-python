from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class JournalRef(_message.Message):
    __slots__ = ("partition", "sequence", "previous_sequence")
    PARTITION_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    partition: str
    sequence: int
    previous_sequence: int
    def __init__(self, partition: _Optional[str] = ..., sequence: _Optional[int] = ..., previous_sequence: _Optional[int] = ...) -> None: ...

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
