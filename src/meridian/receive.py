"""Hearing what the plugin's roles hear (W4.3): seed, follow, catch up.

The sidecar sends one stream per plugin of the rows its roles hear, within
its read scope: each item a row's message in plugin-facing form beside what
is known of it, or a `Lost` where the sidecar dropped deliveries it knows
of. Deliveries are at most once, so the stream alone cannot be trusted to be
whole, and a plugin catches up from the store, never from the bus
(spec/plugins-hear-and-read, Q1).

This is where that is done, once, for every plugin. Each delivery of a record
names its partition, its number there, and the number of the previous change
the same row made for the same account; this keeps, per row and account, the
point up to which it has what the store holds. A delivery continuing from
that point is handed on. One that does not, a `Lost`, a stream that broke, or
an account entering the read scope, is a read of the changes since, by the
row's own query (matrix/scoped.tsv's `caught_up_by`), handed on marked
`caught_up` before anything heard after it. A plugin's handler sees each
change once and in order, or is told it was caught up, and never sees a
number: the journal is taken off what it is handed.

A record carries its whole new state (Q2), so handing one on twice changes
nothing a handler keeps, and where reading a page at a time cannot say
exactly where the store was, a change may be handed on twice rather than
never.

From contract v18 the lake's rows (`CONFLATED`: a price or a bar recorded, a
want and its withdrawal) arrive on the same stream latest value first per
key: under load the sidecar drops a superseded value rather than queueing
it, so a gap between two of them is no loss, and no journal numbers them.
Each is handed on as heard, unless one recorded after it under the same key
was handed on already: a price's key its dataset, subjects, venue and kind,
a bar's its dataset, subjects, venue and interval start (W10.5), and a row's
place its sequence in its dataset, which the lake gives. A price or a
bar is heard for the subjects the plugin names, and on its start, after a
`Lost` naming it and after a broken stream it is read again, latest first,
by its query (`caught_up_by`, every dataset side by side, as the stream
delivers them), handed on marked `caught_up`. Each is handed on with the
dataset it came from (`Heard.dataset`), as the catalogue declares it, which
the lake's answer names once rather than on every row (spec/the-lake,
requirement 6): learned once from `list_datasets`, where the plugin may list
them.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import grpc

from meridian.plugin.v1 import operations_pb2 as ops

from . import bounds
from .errors import CallFailed, MeridianError, NotGranted
from .operations import CONFLATED, DELIVERED, ConflatedRow, DeliveredRow

if TYPE_CHECKING:
    from .client import Plugin

_log = logging.getLogger("meridian.receive")


def catch_up_page(row: DeliveredRow) -> int:
    """How many records one catch-up read asks for at a time: the most the
    store answers in one, its query's page_size bound in the data dictionary
    (W2.7, W9.10)."""
    bound: bounds.Range = getattr(bounds, f"{row.caught_up_by.upper()}_REQUEST_PAGE_SIZE_RANGE")
    return bound.most


Message = TypeVar("Message")


#: How long to wait before opening the stream again after it broke, doubling
#: to the most, so a sidecar restarting is not asked a thousand times.
RETRY_SECONDS = 0.5
RETRY_MOST_SECONDS = 15.0

#: How long a stream just opened is watched for a refusal arriving with its
#: headers, before the store is read.
REFUSAL_WAIT_SECONDS = 0.1
REFUSAL_WAIT_TICKS = 10

#: How many reads one delivery may prompt before it is handed on as it is: a
#: store changing faster than it can be read is caught up with by the next.
CATCH_UP_TRIES = 3

#: The stream's statuses that say it broke rather than that it was refused.
_BROKEN = (
    grpc.StatusCode.UNAVAILABLE,
    grpc.StatusCode.CANCELLED,
    grpc.StatusCode.UNKNOWN,
    grpc.StatusCode.INTERNAL,
    grpc.StatusCode.DEADLINE_EXCEEDED,
    grpc.StatusCode.ABORTED,
)


@dataclass(frozen=True)
class Heard(Generic[Message]):
    """One change a row's handler is handed.

    `message` is the row's message in plugin-facing form, its whole new
    state (a position, a statement), with the store's numbers taken off.
    `caught_up` says it was read from the store rather than heard: when the
    plugin started, after a gap or a loss, after the stream broke, or when an
    account entered its read scope. `own` says the plugin's own act caused it
    (Q6); `cause` is the store's record of who did, where it has one. The
    rest is the envelope's, empty for what was read.

    From contract v18, `dataset` is the dataset a price or a bar came from,
    as its instance's catalogue declares it -- its vendor, its aggregator and
    the instance serving it (spec/the-lake, requirement 6); None for any other
    row, and where the plugin may not list the datasets.
    """

    row: str
    message: Message
    caught_up: bool = False
    own: bool = False
    cause: ops.ChangeCause | None = None
    message_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    published_at_ns: int = 0
    dataset: ops.DatasetRef | None = None


Handler = Callable[[Heard[Any]], Awaitable[None]]


@dataclass
class _Point:
    """Where a row's changes for one account are had to: everything numbered
    at or below `floor` was read, and `last` is the last heard above it."""

    partition: str
    floor: int
    last: int

    @property
    def had(self) -> int:
        return max(self.floor, self.last)

    def continues(self, previous: int) -> bool:
        """Whether a change whose previous change for the account is
        `previous` follows on from what is had."""
        if self.last > self.floor:
            return previous == self.last
        return previous <= self.floor


def _at(message: Any, path: tuple[str, ...]) -> str:
    """The string at a dotted path in a message, empty where it is unset."""
    held = message
    for part in path:
        held = getattr(held, part)
    return str(held)


def _without_numbers(message: Any) -> None:
    """Take every JournalRef off a message, wherever it sits: a plugin's
    handler never sees a number (W4.3)."""
    for described, value in message.ListFields():
        if described.message_type is None:
            continue
        if described.message_type.full_name == ops.JournalRef.DESCRIPTOR.full_name:
            message.ClearField(described.name)
        elif hasattr(value, "ListFields"):
            _without_numbers(value)
        else:
            for each in value:
                _without_numbers(each)


def _sequence_of(watermark: ops.Watermark, partition: str) -> int:
    return next(
        (held.sequence for held in watermark.partitions if held.partition == partition), 0
    )


class _Follower:
    """The rows a plugin follows, and where it has each to."""

    def __init__(
        self, plugin: Plugin, rows: list[DeliveredRow], handlers: Mapping[str, Handler]
    ) -> None:
        self.plugin = plugin
        self.rows = rows
        self.handlers = handlers
        self.by_arm = {row.arm: row for row in rows}
        self.points: dict[tuple[str, str], _Point] = {}
        # Per row, where the last read of the whole scope was answered, by
        # partition: what an account never heard of is had to.
        self.read_to: dict[str, dict[str, int]] = {row.name: {} for row in rows}
        self.lock = asyncio.Lock()

    # ── Reading the store ─────────────────────────────────────────────────

    async def _read(
        self, row: DeliveredRow, account: str, since: dict[str, int] | None
    ) -> tuple[list[Any], dict[str, int]]:
        """Every record the row's query answers since `since` for `account`
        (every account in the scope when empty), and where its first page was
        answered: the point everything it returned is had to at least."""
        method = getattr(self.plugin, row.caught_up_by)
        watermark = (
            None
            if not since
            else ops.Watermark(
                partitions=[
                    ops.PartitionSequence(partition=partition, sequence=sequence)
                    for partition, sequence in sorted(since.items())
                ]
            )
        )
        records: list[Any] = []
        answered: dict[str, int] | None = None
        cursor = ""
        size = catch_up_page(row)
        while True:
            page = await method(
                **{row.account_param: account}, since=watermark, page_size=size, cursor=cursor
            )
            if answered is None:
                answered = {held.partition: held.sequence for held in page.as_of.partitions}
            records.extend(getattr(page, row.records))
            cursor = page.next_cursor
            if not cursor:
                break
        records.sort(key=lambda record: getattr(record, row.record_journal).sequence)
        return records, answered or {}

    def _as_message(self, row: DeliveredRow, record: Any) -> Any:
        """A record read from the store as the row's message."""
        if not row.within:
            message = row.message()
            message.CopyFrom(record)
            return message
        message = row.message()
        getattr(message, row.within).CopyFrom(record)
        if "journal" in row.message.DESCRIPTOR.fields_by_name:
            message.journal.CopyFrom(getattr(record, row.record_journal))
        return message

    async def _apply(
        self,
        row: DeliveredRow,
        records: list[Any],
        answered: dict[str, int],
        accounts: set[str] | None,
        handing: bool = True,
    ) -> None:
        """Records read, handed on and had: every account they name, and each
        of `accounts`, is had to where the read was answered."""
        named = {_at(record, row.record_account) for record in records}
        # What each account was had to before: a record at or below it was
        # handed on already, by a read or as heard.
        had = {
            account: point.had
            for (name, account), point in self.points.items()
            if name == row.name
        }
        for account in named | (accounts or set()):
            point = self.points.get((row.name, account))
            journals = [
                getattr(record, row.record_journal)
                for record in records
                if _at(record, row.record_account) == account
            ]
            partition = (
                journals[0].partition
                if journals
                else point.partition
                if point
                else next(iter(answered), "")
            )
            floor = answered.get(partition, 0)
            if point is None or floor > point.had:
                self.points[(row.name, account)] = _Point(partition, floor, floor)
        if not handing:
            return
        for record in records:
            account = _at(record, row.record_account)
            if getattr(record, row.record_journal).sequence <= had.get(account, -1):
                continue
            await self._hand(row, self._as_message(row, record), caught_up=True)

    async def seed(self, *, handing: bool) -> None:
        """Every row's records across the read scope, as the store holds them
        now: the plugin's start."""
        for row in self.rows:
            records, answered = await self._read(row, "", None)
            self.read_to[row.name] = answered
            await self._apply(row, records, answered, None, handing)

    async def catch_up(self, row: DeliveredRow, account: str) -> None:
        """One account's changes since the last it had, handed on."""
        point = self.points.get((row.name, account))
        since = None if point is None else {point.partition: point.had}
        records, answered = await self._read(row, account, since)
        await self._apply(row, records, answered, {account})

    async def catch_up_all(self, names: set[str] | None = None) -> None:
        """Every account's changes since the least any has, for the rows
        named or all: what a loss, or a broken stream, may have taken."""
        for row in self.rows:
            if names is not None and row.name not in names:
                continue
            since = dict(self.read_to[row.name])
            for (name, _), point in self.points.items():
                if name == row.name:
                    since[point.partition] = min(
                        since.get(point.partition, point.had), point.had
                    )
            records, answered = await self._read(row, "", since)
            self.read_to[row.name] = answered
            had = {account for (name, account) in self.points if name == row.name}
            await self._apply(row, records, answered, had)

    def forget(self, accounts: set[str]) -> None:
        """Accounts that left the read scope: nothing more is heard of them."""
        for key in [key for key in self.points if key[1] in accounts]:
            del self.points[key]

    # ── Following ─────────────────────────────────────────────────────────

    async def _hand(
        self, row: DeliveredRow, message: Any, *, caught_up: bool, meta: Any = None
    ) -> None:
        cause = message.cause if message.HasField("cause") else None
        if meta is not None and meta.HasField("cause"):
            cause = meta.cause
        given = type(message)()
        given.CopyFrom(message)
        _without_numbers(given)
        await self.handlers[row.name](
            Heard(
                row=row.name,
                message=given,
                caught_up=caught_up,
                own=bool(meta.own)
                if meta is not None
                else cause is not None
                and cause.instance_id == self.plugin.identity.instance_id,
                cause=cause,
                message_id=meta.message_id if meta is not None else "",
                correlation_id=meta.correlation_id if meta is not None else "",
                causation_id=meta.causation_id if meta is not None else "",
                published_at_ns=meta.published_at_ns if meta is not None else 0,
            )
        )

    async def delivered(self, delivery: ops.Delivery) -> None:
        which = delivery.WhichOneof("item")
        if which is None:
            return
        if which == "lost":
            lost = delivery.lost
            _log.warning(
                "the sidecar dropped %s deliveries of %s; catching up",
                lost.dropped or "some",
                ", ".join(lost.rows) or "every row",
            )
            await self.catch_up_all(set(lost.rows) if lost.rows else None)
            return
        row = self.by_arm.get(which)
        if row is None:
            return
        message = getattr(delivery, which)
        journal = delivery.meta.journal
        account = _at(message, row.account)
        key = (row.name, account)
        for _ in range(CATCH_UP_TRIES):
            point = self.points.get(key)
            if point is None and journal.previous_sequence == 0:
                # The first change this row ever made for the account.
                point = self.points[key] = _Point(journal.partition, 0, 0)
            if point is not None:
                if journal.sequence <= point.had:
                    return
                if point.continues(journal.previous_sequence):
                    break
            await self.catch_up(row, account)
        else:
            _log.warning(
                "%s for %s changed faster than it could be read; handing it on as heard",
                row.name,
                account or "no account",
            )
        point = self.points.setdefault(key, _Point(journal.partition, 0, 0))
        if journal.sequence <= point.had:
            return
        point.last = journal.sequence
        await self._hand(row, message, caught_up=False, meta=delivery.meta)


class _Latest:
    """The rows heard latest value first (contract v18), and the latest of
    each key handed on."""

    def __init__(
        self,
        plugin: Plugin,
        rows: list[ConflatedRow],
        handlers: Mapping[str, Handler],
        subjects: tuple[str, ...],
    ) -> None:
        self.plugin = plugin
        self.rows = rows
        self.handlers = handlers
        self.subjects = subjects
        self.by_arm = {row.arm: row for row in rows}
        # A row's key (W10.5) -> the sequence in its dataset handed on.
        self.handed: dict[tuple[Any, ...], int] = {}
        # The datasets as their catalogue entries declare them, and those a
        # listing was asked for.
        self.datasets: dict[str, ops.DatasetRef] = {}
        self.asked: set[str] = set()

    @staticmethod
    def _meta(row: ConflatedRow, message: Any) -> Any:
        """The observation's envelope, where the row carries one."""
        if not row.within:
            return None
        return getattr(message, row.within).meta

    async def _dataset(self, name: str) -> ops.DatasetRef | None:
        """The dataset `name` as its catalogue entry declares it, listed once
        for each dataset not yet held: a dataset declared since is learned
        when first heard."""
        if not name:
            return None
        if name not in self.datasets and name not in self.asked:
            self.asked.add(name)
            try:
                answer = await self.plugin.list_datasets()
            except MeridianError as failed:
                _log.info("the datasets could not be listed (%s); heard without them", failed)
            else:
                for held in answer.datasets:
                    self.datasets[held.dataset] = held
        return self.datasets.get(name)

    @staticmethod
    def _key(row: ConflatedRow, record: Any) -> tuple[Any, ...]:
        """The key a row is delivered latest value first by (W10.5): its
        dataset, subjects and venue, and a price's kind or a bar's interval
        start."""
        meta = record.meta
        which = (
            record.kind if "kind" in record.DESCRIPTOR.fields_by_name else meta.valid_from_ns
        )
        return (
            row.name,
            meta.source.dataset,
            tuple(subject.entity_id for subject in meta.subjects),
            meta.source.venue_id,
            which,
        )

    async def hand(
        self, row: ConflatedRow, message: Any, *, caught_up: bool, meta: Any = None
    ) -> None:
        """One row handed on, unless one recorded after it under its key was."""
        observation = self._meta(row, message)
        dataset = None
        if observation is not None:
            key = self._key(row, getattr(message, row.within))
            if observation.sequence:
                if self.handed.get(key, 0) >= observation.sequence:
                    return
                self.handed[key] = observation.sequence
            dataset = await self._dataset(observation.source.dataset)
        own = (
            bool(meta.own)
            if meta is not None
            else observation is not None
            and observation.source.instance == self.plugin.identity.instance_id
        )
        given = type(message)()
        given.CopyFrom(message)
        await self.handlers[row.name](
            Heard(
                row=row.name,
                message=given,
                caught_up=caught_up,
                own=own,
                message_id=meta.message_id if meta is not None else "",
                correlation_id=meta.correlation_id if meta is not None else "",
                causation_id=meta.causation_id if meta is not None else "",
                published_at_ns=meta.published_at_ns if meta is not None else 0,
                dataset=dataset,
            )
        )

    async def delivered(self, delivery: ops.Delivery) -> None:
        which = delivery.WhichOneof("item")
        row = self.by_arm.get(which or "")
        if row is not None:
            await self.hand(
                row, getattr(delivery, row.arm), caught_up=False, meta=delivery.meta
            )

    async def read(self, names: set[str] | None = None) -> None:
        """Each row about subjects read again, latest first, for the subjects
        named, every dataset side by side: the plugin's start, a loss, a
        broken stream. A row no query reads again, a want, is not."""
        if not self.subjects:
            return
        for row in self.rows:
            if not row.caught_up_by or (names is not None and row.name not in names):
                continue
            method = getattr(self.plugin, row.caught_up_by)
            prefix = row.caught_up_by.upper()
            most: int = getattr(bounds, f"{prefix}_REQUEST_SUBJECTS_COUNT").most
            size: int = getattr(bounds, f"{prefix}_REQUEST_PAGE_SIZE_RANGE").most
            for start in range(0, len(self.subjects), most):
                subjects = [
                    ops.SubjectRef(entity_id=entity)
                    for entity in self.subjects[start : start + most]
                ]
                cursor = ""
                while True:
                    page = await method(
                        subjects=subjects,
                        sources=ops.SourceChoice(side_by_side=True),
                        page_size=size,
                        cursor=cursor,
                    )
                    for record in getattr(page, row.records):
                        message = row.message()
                        getattr(message, row.within).CopyFrom(record)
                        await self.hand(row, message, caught_up=True)
                    cursor = page.next_cursor
                    if not cursor:
                        break


async def follow(
    plugin: Plugin,
    handlers: Mapping[str, Handler | None],
    *,
    seed: bool,
    subjects: Sequence[str] = (),
) -> None:
    """Hear the rows given a handler until cancelled (Operations.receive)."""
    given = {name: handler for name, handler in handlers.items() if handler is not None}
    rows = [row for row in DELIVERED if row.name in given]
    latest_rows = [row for row in CONFLATED if row.name in given]
    if not rows and not latest_rows:
        raise ValueError("receive() names no row to hear: give a handler for at least one")
    if isinstance(subjects, str):
        raise TypeError("subjects is a sequence of entity IDs, not one string")
    wanted = tuple(dict.fromkeys(subjects))
    if not bounds.RECEIVE_REQUEST_SUBJECTS_COUNT.admits(len(wanted)):
        most = bounds.RECEIVE_REQUEST_SUBJECTS_COUNT.most
        raise ValueError(f"subjects names {len(wanted)}; at most {most}")
    follower = _Follower(plugin, rows, given)
    latest = _Latest(plugin, latest_rows, given, wanted)
    watching = asyncio.create_task(_watch_scope(plugin, follower)) if rows else None
    started = False
    wait = RETRY_SECONDS
    try:
        while True:
            call = plugin._operations().Receive(
                ops.ReceiveRequest(
                    rows=[*(row.name for row in rows), *(row.name for row in latest_rows)],
                    subjects=list(wanted),
                )
            )
            try:
                # Answered once the sidecar has subscribed, so nothing changed
                # after the read below is missed by the stream.
                await call.initial_metadata()
                # A refusal comes with the headers; its status may reach the
                # call a moment after them. Reading a refused call raises it.
                for _tick in range(REFUSAL_WAIT_TICKS):
                    if call.done():
                        async for _refused in call:
                            pass
                        break
                    await asyncio.sleep(REFUSAL_WAIT_SECONDS / REFUSAL_WAIT_TICKS)
                async with follower.lock:
                    if not started:
                        await follower.seed(handing=seed)
                        if seed:
                            await latest.read()
                        started = True
                    else:
                        await follower.catch_up_all()
                        await latest.read()
                wait = RETRY_SECONDS
                async for delivery in call:
                    async with follower.lock:
                        which = delivery.WhichOneof("item")
                        if which in latest.by_arm:
                            await latest.delivered(delivery)
                            continue
                        await follower.delivered(delivery)
                        if which == "lost":
                            named = set(delivery.lost.rows)
                            await latest.read(named or None)
                _log.warning("the delivery stream ended; opening it again")
            except grpc.aio.AioRpcError as failed:
                if failed.code() is grpc.StatusCode.PERMISSION_DENIED:
                    raise NotGranted("Receive", failed.details() or "") from failed
                if failed.code() not in _BROKEN:
                    raise
                _log.warning("the delivery stream broke (%s); opening it again", failed.code())
            except CallFailed as failed:
                if failed.kind not in ("no handler", "timeout", "handler error"):
                    raise
                _log.warning("a read to catch up failed (%s); trying again", failed)
            finally:
                call.cancel()
            await asyncio.sleep(wait)
            wait = min(wait * 2, RETRY_MOST_SECONDS)
    finally:
        if watching is not None:
            watching.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await watching


async def _watch_scope(plugin: Plugin, follower: _Follower) -> None:
    """Read an account afresh when it enters the read scope, and forget one
    that leaves it (W4.3, W4.11)."""
    held: frozenset[str] | None = None
    with contextlib.suppress(grpc.aio.AioRpcError):
        async for scope in plugin.account_scope():
            if held is not None:
                entered, left = scope.read - held, held - scope.read
                async with follower.lock:
                    follower.forget(set(left))
                    for account in sorted(entered):
                        for row in follower.rows:
                            await follower.catch_up(row, account)
            held = scope.read
