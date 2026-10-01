"""Hearing what a plugin's roles hear (W4.3), from the plugin's side.

Against the fake sidecar, which streams what a test scripts and answers the
catch-up reads from a store the test holds: what these hold is the SDK's
half -- a seed read before anything heard, a change handed on once and in
order, a gap or a loss caught up from the store, a broken stream opened again,
and no number ever handed to a plugin. What the sidecar delivers, filters and
drops is meridian-core's to test, and the interop suite's.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import grpc
import pytest

import meridian
from conftest import FakeSidecar, Stream
from meridian import Heard, NotGranted
from meridian.plugin.v1 import operations_pb2 as ops

STREET = "street"


def journal(sequence: int, previous: int) -> ops.JournalRef:
    return ops.JournalRef(partition=STREET, sequence=sequence, previous_sequence=previous)


def watermark(sequence: int) -> ops.Watermark:
    return ops.Watermark(
        partitions=[ops.PartitionSequence(partition=STREET, sequence=sequence)]
    )


def position(
    account: str, instrument: str, sequence: int, previous: int = 0, **more
) -> ops.CustodialPosition:
    return ops.CustodialPosition(
        account_id=account,
        instrument_id=instrument,
        side=ops.HOLDING_SIDE_LONG,
        last_change=journal(sequence, previous),
        **more,
    )


def changed(held: ops.CustodialPosition, *, own: bool = False) -> ops.Delivery:
    """A position delivered as the sidecar delivers it."""
    return ops.Delivery(
        meta=ops.DeliveryMeta(
            message_id=f"msg-{held.last_change.sequence}",
            row="CustodialPositionUpdated",
            journal=held.last_change,
            cause=ops.ChangeCause(
                instance_id="operations-1" if own else "custody-snaptrade-1",
                causation_id="cmd-1",
            ),
            own=own,
        ),
        custodial_position_updated=ops.CustodialPositionUpdatedEvent(
            position=held, statement_id="STMT-1", journal=held.last_change
        ),
    )


def statement(account: str, sequence: int, previous: int = 0) -> ops.StatementRecordedEvent:
    return ops.StatementRecordedEvent(
        statement_id=f"STMT-{sequence}",
        account_id=account,
        journal=journal(sequence, previous),
        cause=ops.ChangeCause(instance_id="custody-snaptrade-1"),
    )


def lost(dropped: int = 0, *rows: str) -> ops.Delivery:
    return ops.Delivery(lost=ops.Lost(dropped=dropped, rows=list(rows)))


@dataclass
class Store:
    """The street as the catch-up reads see it: each record whole, its last
    change numbered, tombstones kept for a read since a watermark."""

    head: int = 0
    held: dict[tuple[str, str], ops.CustodialPosition] = field(default_factory=dict)
    completed: list[ops.StatementRecordedEvent] = field(default_factory=list)
    # Changes made after the first read: what the seed did not see.
    later: list[ops.CustodialPosition] = field(default_factory=list)
    read: int = 0

    def put(self, held: ops.CustodialPosition) -> ops.CustodialPosition:
        self.held[(held.account_id, held.instrument_id)] = held
        self.head = max(self.head, held.last_change.sequence)
        return held

    def positions(
        self, request: ops.ListCustodialPositionsParams
    ) -> ops.ListCustodialPositionsResult:
        since = request.since.partitions[0].sequence if request.HasField("since") else None
        answered = [
            held
            for held in self.held.values()
            if (not request.account_id or held.account_id == request.account_id)
            and (
                since is None
                and not held.removed
                or since is not None
                and held.last_change.sequence > since
            )
        ]
        result = ops.ListCustodialPositionsResult(
            positions=answered, as_of=watermark(self.head)
        )
        self.read += 1
        if self.read == 1:
            for each in self.later:
                self.put(each)
        return result

    def statements(self, request: ops.ListStatementsParams) -> ops.ListStatementsResult:
        since = request.since.partitions[0].sequence if request.HasField("since") else 0
        answered = [
            each
            for each in self.completed
            if (not request.account_id or each.account_id == request.account_id)
            and each.journal.sequence > since
        ]
        return ops.ListStatementsResult(statements=answered, as_of=watermark(self.head))


@dataclass
class Heard_:
    """What each handler was handed, in order."""

    positions: list[Heard[ops.CustodialPositionUpdatedEvent]] = field(default_factory=list)
    statements: list[Heard[ops.StatementRecordedEvent]] = field(default_factory=list)
    arrived: asyncio.Event = field(default_factory=asyncio.Event)
    wanted: int = 0

    async def position(self, heard: Heard[ops.CustodialPositionUpdatedEvent]) -> None:
        self.positions.append(heard)
        self._count()

    async def statement(self, heard: Heard[ops.StatementRecordedEvent]) -> None:
        self.statements.append(heard)
        self._count()

    def _count(self) -> None:
        if len(self.positions) + len(self.statements) >= self.wanted:
            self.arrived.set()


async def hearing(
    sidecar: tuple[FakeSidecar, str],
    store: Store,
    streams: list[Stream],
    wanted: int,
    *,
    statements: bool = False,
    seed: bool = True,
) -> tuple[Heard_, FakeSidecar]:
    """Receive until `wanted` changes were handed on, then stop."""
    service, address = sidecar
    service.instance_id = "operations-1"
    service.operations.store = store
    service.operations.streams = streams
    heard = Heard_(wanted=wanted)
    plugin = await meridian.connect(address, heartbeat=False)
    task = asyncio.create_task(
        plugin.receive(
            custodial_position_updated=heard.position,
            statement_recorded=heard.statement if statements else None,
            seed=seed,
        )
    )
    try:
        await asyncio.wait_for(heard.arrived.wait(), timeout=5)
        # Anything more than wanted would be a change handed on twice.
        await asyncio.sleep(0.1)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await plugin.leave()
    return heard, service


async def test_it_seeds_from_the_store_then_hands_on_each_change_heard(sidecar) -> None:
    store = Store()
    store.put(position("ACC-1", "INS-A", 30))
    store.put(position("ACC-1", "INS-B", 40, 30))
    later = position("ACC-1", "INS-A", 42, 40, quantity=ops.Decimal(low=5))
    heard, service = await hearing(sidecar, store, [Stream([changed(later)])], 3)

    assert [h.caught_up for h in heard.positions] == [True, True, False]
    assert [h.message.position.instrument_id for h in heard.positions] == [
        "INS-A",
        "INS-B",
        "INS-A",
    ]
    assert service.operations.received[0].rows == ["CustodialPositionUpdated"]
    live = heard.positions[2]
    assert live.message_id == "msg-42" and not live.own
    assert live.cause is not None and live.cause.instance_id == "custody-snaptrade-1"
    assert live.message.position.quantity.low == 5


async def test_a_handler_never_sees_a_number(sidecar) -> None:
    store = Store()
    store.put(position("ACC-1", "INS-A", 30))
    heard, _ = await hearing(
        sidecar, store, [Stream([changed(position("ACC-1", "INS-A", 31, 30))])], 2
    )
    for each in heard.positions:
        assert not each.message.HasField("journal")
        assert not each.message.position.HasField("last_change")


async def test_a_change_already_read_is_not_handed_on_again(sidecar) -> None:
    store = Store()
    seeded = store.put(position("ACC-1", "INS-A", 40, 30))
    heard, _ = await hearing(sidecar, store, [Stream([changed(seeded)])], 1)
    assert len(heard.positions) == 1 and heard.positions[0].caught_up


async def test_a_gap_in_an_accounts_changes_is_caught_up_from_the_store(sidecar) -> None:
    store = Store()
    store.put(position("ACC-1", "INS-A", 40))
    store.put(position("ACC-2", "INS-Z", 41))
    # Made after the seed's read; 45 never comes down the stream.
    after = position("ACC-1", "INS-A", 50, 45)
    store.later = [position("ACC-1", "INS-B", 45, 40), after]
    heard, service = await hearing(sidecar, store, [Stream([changed(after)])], 4)

    caught = [(h.message.position.instrument_id, h.caught_up) for h in heard.positions[2:]]
    # The read since 41 answers 45 and 50 whole; 50 heard is then had already.
    assert caught == [("INS-B", True), ("INS-A", True)]
    read = service.operations.reads[-1]
    assert read.account_id == "ACC-1"
    assert read.since.partitions[0].sequence == 41


async def test_a_loss_is_caught_up_across_the_scope(sidecar) -> None:
    store = Store()
    store.put(position("ACC-1", "INS-A", 40))
    store.later = [position("ACC-2", "INS-Z", 44)]
    heard, service = await hearing(sidecar, store, [Stream([lost(0)])], 2)

    assert heard.positions[-1].message.position.instrument_id == "INS-Z"
    assert heard.positions[-1].caught_up
    read = service.operations.reads[-1]
    assert read.account_id == ""
    assert read.since.partitions[0].sequence == 40


async def test_a_stream_that_breaks_is_opened_again_and_caught_up(sidecar) -> None:
    store = Store()
    store.put(position("ACC-1", "INS-A", 40))
    first = position("ACC-1", "INS-A", 41, 40)
    store.later = [first, position("ACC-1", "INS-B", 43, 41)]
    heard, service = await hearing(
        sidecar,
        store,
        [Stream([changed(first)], breaks=grpc.StatusCode.UNAVAILABLE), Stream([])],
        3,
    )
    assert len(service.operations.received) == 2
    assert [h.message.position.instrument_id for h in heard.positions] == [
        "INS-A",
        "INS-A",
        "INS-B",
    ]
    assert [h.caught_up for h in heard.positions] == [True, False, True]


async def test_an_accounts_first_change_needs_no_read(sidecar) -> None:
    store = Store()
    store.put(position("ACC-1", "INS-A", 40))
    first = position("ACC-9", "INS-N", 41, 0)
    heard, service = await hearing(sidecar, store, [Stream([changed(first)])], 2)
    assert [h.caught_up for h in heard.positions] == [True, False]
    assert len(service.operations.reads) == 1, "the seed alone"


async def test_its_own_act_is_marked(sidecar) -> None:
    store = Store()
    heard, _ = await hearing(
        sidecar, store, [Stream([changed(position("ACC-1", "INS-A", 1, 0), own=True)])], 1
    )
    assert heard.positions[0].own


async def test_statements_follow_their_own_chain(sidecar) -> None:
    store = Store()
    store.put(position("ACC-1", "INS-A", 40))
    store.completed.append(statement("ACC-1", 38))
    store.head = 40
    later = statement("ACC-1", 58, 38)
    delivery = ops.Delivery(
        meta=ops.DeliveryMeta(
            row="StatementRecorded", journal=later.journal, cause=later.cause
        ),
        statement_recorded=later,
    )
    heard, _ = await hearing(sidecar, store, [Stream([delivery])], 3, statements=True)
    assert [h.caught_up for h in heard.statements] == [True, False]
    assert heard.statements[0].cause is not None, "a statement read keeps its cause"


async def test_without_a_seed_it_is_read_and_not_handed_on(sidecar) -> None:
    store = Store()
    store.put(position("ACC-1", "INS-A", 40))
    heard, service = await hearing(
        sidecar, store, [Stream([changed(position("ACC-1", "INS-A", 41, 40))])], 1, seed=False
    )
    assert [h.caught_up for h in heard.positions] == [False]
    assert len(service.operations.reads) == 1


async def test_a_row_its_roles_do_not_hear_is_refused(sidecar) -> None:
    service, address = sidecar
    service.operations.receive_refused = (
        grpc.StatusCode.PERMISSION_DENIED,
        "StatementRecorded is not a row this plugin's roles hear",
    )
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(NotGranted, match="not a row this plugin's roles hear"):
            await asyncio.wait_for(
                plugin.receive(statement_recorded=Heard_().statement), timeout=5
            )
    finally:
        await plugin.leave()


async def test_receive_names_a_row(sidecar) -> None:
    _, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(ValueError, match="names no row"):
            await plugin.receive()
    finally:
        await plugin.leave()
