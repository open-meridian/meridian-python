"""What a data plugin has sent, and what it holds back to send at its pace
(SDK 0.35; spec/each-role-is-one-generated-class, section 4, 924's item 6;
the data-plugin fit review's sections 1.3 and 1.5).

`SentRows(capacity)` remembers each row's last sending by a digest of its
values -- never `repr`, which costs its text in memory and in time -- so a
row is sent again only when what it says changed:

    sent = data.SentRows(200_000)
    if sent.changed(SERIES, dataset, row.meta.row_key, terms):
        rows.append(row)

The listings feed, the chains feed and a polled tape keep one each; the
copies of `_changed` the fit review found in four plugins are this.

`Conflator(every_ns)` keeps the latest value per key and hands back what
is due once a period: a quote or a price stated many times a second is
recorded once a second, the latest. A trade, a fill or an outcome is never
conflated (ruling 375): each is recorded, so `put` refuses one.

    conflator = data.Conflator(1_000_000_000)
    conflator.put(product, top)
    for top in conflator.due(): ...
"""

from __future__ import annotations

import dataclasses
import hashlib
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from google.protobuf.message import Message

__all__ = ["Conflator", "SentRows", "digest"]

#: What `Conflator.put` refuses: each is recorded, never conflated (375).
NEVER_CONFLATED = ("Trade", "Fill", "Outcome", "ExecutionRecorded", "Execution")


def _feed(hash_: Any, value: Any) -> None:
    """A value's wire words into the digest, by kind, so two values differ
    in the digest exactly where they differ in what they say."""
    if value is None:
        hash_.update(b"N")
    elif isinstance(value, bool):
        hash_.update(b"T" if value else b"F")
    elif isinstance(value, int | float | Decimal):
        hash_.update(b"n" + str(value).encode() + b";")
    elif isinstance(value, str):
        hash_.update(b"s" + str(len(value)).encode() + b":" + value.encode())
    elif isinstance(value, bytes):
        hash_.update(b"b" + str(len(value)).encode() + b":" + value)
    elif isinstance(value, date | datetime):
        hash_.update(b"d" + value.isoformat().encode() + b";")
    elif isinstance(value, Enum):
        hash_.update(b"e" + str(value.value).encode() + b";")
    elif isinstance(value, Message):
        hash_.update(b"m" + value.SerializeToString(deterministic=True) + b";")
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        hash_.update(b"(" + type(value).__name__.encode())
        for each in dataclasses.fields(value):
            hash_.update(each.name.encode() + b"=")
            _feed(hash_, getattr(value, each.name))
        hash_.update(b")")
    elif isinstance(value, dict):
        hash_.update(b"{")
        for key in sorted(value, key=str):
            _feed(hash_, key)
            _feed(hash_, value[key])
        hash_.update(b"}")
    elif isinstance(value, list | tuple):
        hash_.update(b"[")
        for each in value:
            _feed(hash_, each)
        hash_.update(b"]")
    else:
        hash_.update(b"r" + repr(value).encode() + b";")


def digest(value: Any) -> bytes:
    """A stable 16-byte digest of a value's words: a row, a dataclass, a
    protobuf message, text or a number."""
    hash_ = hashlib.blake2b(digest_size=16)
    _feed(hash_, value)
    return hash_.digest()


class SentRows:
    """Each row's last sending, by (data type, dataset, row key), at most
    `capacity` of them, the least recently sent forgotten first."""

    def __init__(self, capacity: int = 200_000) -> None:
        if capacity < 1:
            raise ValueError(f"SentRows holds at least one row: {capacity}")
        self.capacity = capacity
        self._said: OrderedDict[tuple[str, str, str], bytes] = OrderedDict()

    def changed(self, data_type: str, dataset: str, row_key: str, said: Any) -> bool:
        """Whether the row says something other than its last sending: true
        for one never sent, or forgotten; and it is remembered as sent."""
        key = (data_type, dataset, row_key)
        now = digest(said)
        if self._said.get(key) == now:
            self._said.move_to_end(key)
            return False
        self._said[key] = now
        self._said.move_to_end(key)
        while len(self._said) > self.capacity:
            self._said.popitem(last=False)
        return True

    def forget(self, data_type: str, dataset: str, row_key: str) -> None:
        """Forget one row's sending: it is sent again whatever it says."""
        self._said.pop((data_type, dataset, row_key), None)

    def clear(self) -> None:
        """Forget every sending (a source switched)."""
        self._said.clear()

    def __len__(self) -> int:
        return len(self._said)


class Conflator:
    """The latest value per key, handed back once every `every_ns` (see the
    module). `clock_ns` is for a test."""

    def __init__(self, every_ns: int, *, clock_ns: Callable[[], int] = time.time_ns) -> None:
        if every_ns <= 0:
            raise ValueError(f"a conflator's every_ns is above 0: {every_ns}")
        self.every_ns = every_ns
        self._clock_ns = clock_ns
        self._held: dict[Hashable, Any] = {}
        self._due_at = 0

    def put(self, key: Hashable, value: Any) -> None:
        """Hold `value` as the latest for `key`, replacing one held. A trade,
        a fill or an outcome is refused: each is recorded."""
        if type(value).__name__ in NEVER_CONFLATED:
            raise ValueError(
                f"a {type(value).__name__} is never conflated (ruling 375): record each"
            )
        self._held.pop(key, None)
        self._held[key] = value

    def due(self, now_ns: int | None = None) -> list[Any]:
        """The values held, the latest per key in the order first put, once
        `every_ns` has passed since the last were handed back; else none."""
        now = self._clock_ns() if now_ns is None else now_ns
        if not self._held or now < self._due_at:
            return []
        return self.flush(now)

    def flush(self, now_ns: int | None = None) -> list[Any]:
        """Every value held, now, whatever is due."""
        now = self._clock_ns() if now_ns is None else now_ns
        held, self._held = list(self._held.values()), {}
        self._due_at = now + self.every_ns
        return held

    def __len__(self) -> int:
        return len(self._held)
