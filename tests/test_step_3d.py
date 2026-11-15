"""Step 3d, from the plugin's side: a book of several partitions and an
account moved between them (W9.8), followed without a number of one
partition ever compared with another's.

The book numbers a record in its account's partition. From step 3d a book
has several, an account's own read is answered at its own partition's head
alone, and an account moved by `MoveAccount` is numbered afresh in the
partition it continues in: its next change names the new partition, a small
number there, and as its previous change the old partition's last.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

import meridian
from conftest import FakeSidecar, Stream, receive
from meridian import Heard
from meridian.operations import DELIVERED
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import _Follower, _Point

POSITION_CHANGED = next(row for row in DELIVERED if row.name == "PositionChanged")


def position(
    account: str, instrument: str, partition: str, sequence: int, previous: int = 0
) -> ops.BookPosition:
    return ops.BookPosition(
        account_id=account,
        instrument_id=instrument,
        side=ops.HOLDING_SIDE_LONG,
        last_change=ops.JournalRef(
            partition=partition, sequence=sequence, previous_sequence=previous
        ),
    )


def changed(held: ops.BookPosition) -> ops.Delivery:
    return ops.Delivery(
        meta=ops.DeliveryMeta(
            message_id=f"msg-{held.last_change.partition}-{held.last_change.sequence}",
            row="PositionChanged",
            journal=held.last_change,
        ),
        position_changed=ops.PositionChangedEvent(position=held, journal=held.last_change),
    )


@dataclass
class Book:
    """The book as its reads answer: a record above the watermark a read is
    since, a partition the watermark does not name read from its start; a
    read of no account answered at every partition's head, and an account's
    at its own partition's alone (core's `watermark_for`), or at every
    partition's where `whole` (core before it)."""

    heads: dict[str, int] = field(default_factory=dict)
    placed: dict[str, str] = field(default_factory=dict)
    held: dict[tuple[str, str], ops.BookPosition] = field(default_factory=dict)
    # Changes made after the first read: what the seed did not see.
    later: list[ops.BookPosition] = field(default_factory=list)
    whole: bool = False
    read: int = 0

    def put(self, held: ops.BookPosition) -> ops.BookPosition:
        change = held.last_change
        self.held[(held.account_id, held.instrument_id)] = held
        self.heads[change.partition] = max(self.heads.get(change.partition, 0), change.sequence)
        self.placed[held.account_id] = change.partition
        return held

    def book_positions(self, request: ops.ListPositionsParams) -> ops.ListPositionsResult:
        since = (
            {each.partition: each.sequence for each in request.since.partitions}
            if request.HasField("since")
            else None
        )
        answered = [
            held
            for held in self.held.values()
            if (not request.account_id or held.account_id == request.account_id)
            and (
                since is None
                or held.last_change.sequence > since.get(held.last_change.partition, 0)
            )
        ]
        heads = dict(self.heads)
        if request.account_id and not self.whole:
            own = self.placed.get(request.account_id)
            heads = {own: heads[own]} if own in heads else {}
        result = ops.ListPositionsResult(
            positions=answered,
            as_of=ops.Watermark(
                partitions=[
                    ops.PartitionSequence(partition=partition, sequence=head)
                    for partition, head in sorted(heads.items())
                ]
            ),
        )
        self.read += 1
        if self.read == 1:
            for each in self.later:
                self.put(each)
        return result


async def following(
    sidecar: tuple[FakeSidecar, str], book: Book, deliveries: list[ops.Delivery], wanted: int
) -> list[Heard[ops.PositionChangedEvent]]:
    """The positions handed on, in order, once `wanted` were."""
    service, address = sidecar
    service.operations.store = book
    service.operations.streams = [Stream(deliveries)]
    heard: list[Heard[ops.PositionChangedEvent]] = []
    arrived = asyncio.Event()

    async def handed(each: Heard[ops.PositionChangedEvent]) -> None:
        heard.append(each)
        if len(heard) >= wanted:
            arrived.set()

    plugin = await meridian.connect(address, heartbeat=False, roles=[])
    task = asyncio.create_task(receive(plugin, position_changed=handed))
    try:
        await asyncio.wait_for(arrived.wait(), timeout=5)
        # Anything more than wanted would be a change handed on twice.
        await asyncio.sleep(0.1)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await plugin.leave()
    return heard


def seen(heard: list[Heard[ops.PositionChangedEvent]]) -> list[tuple[str, str, str]]:
    return [
        (
            h.message.position.account_id,
            h.message.position.instrument_id,
            h.message.journal.partition,
        )
        for h in heard
    ]


async def test_an_account_moved_to_another_partition_is_followed_there(sidecar) -> None:
    """An account had to 500 in P0 moves to P1: its changes there, numbered
    3 and 4, are handed on, each once, though both are below 500."""
    book = Book(heads={"P0": 500, "P1": 2})
    book.put(position("ACC-1", "INS-A", "P0", 490))
    book.put(position("ACC-1", "INS-B", "P0", 500, 490))
    third = position("ACC-1", "INS-C", "P1", 3, 500)
    fourth = position("ACC-1", "INS-D", "P1", 4, 3)
    fifth = position("ACC-1", "INS-E", "P1", 5, 4)
    # The store holds the first two when the third is heard; the fifth is
    # heard alone.
    book.later = [third, fourth]
    heard = await following(sidecar, book, [changed(third), changed(fourth), changed(fifth)], 5)

    assert [h.message.position.instrument_id for h in heard] == [
        "INS-A",
        "INS-B",
        "INS-C",
        "INS-D",
        "INS-E",
    ]
    # No number is handed on, the new partition's no more than the old's.
    assert all(not h.message.HasField("journal") for h in heard)
    assert [h.caught_up for h in heard] == [True, True, True, True, False]


async def test_a_moved_account_s_changes_are_heard_before_the_store_is_read_of_them(
    sidecar,
) -> None:
    """The read a move's first delivery prompts answers nothing new (a
    reader behind): the delivery is handed on as heard, and the next
    follows it by number in the new partition."""
    book = Book(heads={"P0": 500, "P1": 2})
    book.put(position("ACC-1", "INS-A", "P0", 500))
    book.placed["ACC-1"] = "P1"
    third = position("ACC-1", "INS-C", "P1", 3, 500)
    fourth = position("ACC-1", "INS-D", "P1", 4, 3)
    heard = await following(sidecar, book, [changed(third), changed(fourth)], 3)

    assert [(h.message.position.instrument_id, h.caught_up) for h in heard] == [
        ("INS-A", True),
        ("INS-C", False),
        ("INS-D", False),
    ]


async def test_an_account_with_nothing_read_is_had_in_the_partition_it_is_heard_in(
    sidecar,
) -> None:
    """An account's read answering no record under a watermark of every
    partition (core before `watermark_for`) says nothing of where the
    account is: its change in P1, numbered below P0's head, is handed on."""
    book = Book(heads={"P0": 900, "P1": 40}, whole=True)
    book.put(position("ACC-1", "INS-A", "P0", 900))
    first = position("ACC-2", "INS-B", "P1", 41, 30)
    second = position("ACC-2", "INS-B", "P1", 42, 41)
    heard = await following(sidecar, book, [changed(first), changed(second)], 3)

    assert seen(heard) == [
        ("ACC-1", "INS-A", ""),
        ("ACC-2", "INS-B", ""),
        ("ACC-2", "INS-B", ""),
    ]
    assert [h.caught_up for h in heard] == [True, False, False]


class _NoPlugin:
    """A follower's plugin where a test reads nothing through it."""


async def test_a_read_naming_several_partitions_places_no_account() -> None:
    """`_apply` takes the one partition a watermark names, or none: an
    account nothing was read of is not had to the first partition's head."""
    follower = _Follower(_NoPlugin(), [POSITION_CHANGED], {})  # type: ignore[arg-type]
    row = POSITION_CHANGED

    await follower._apply(row, [], {"P0": 900, "P1": 40}, {"ACC-2"})
    assert follower.points == {}

    # One partition named: the account's own read (core's `watermark_for`),
    # or a book of one.
    await follower._apply(row, [], {"P1": 40}, {"ACC-2"})
    assert follower.points == {("PositionChanged", "ACC-2"): _Point("P1", 40, 40)}

    # An account not placed yet is answered at no partition.
    await follower._apply(row, [], {}, {"ACC-3"})
    assert ("PositionChanged", "ACC-3") not in follower.points

    # Had in a partition, it stays there under a watermark of several, and
    # is had to that partition's head, never another's.
    await follower._apply(row, [], {"P0": 900, "P1": 45}, {"ACC-2"})
    assert follower.points[("PositionChanged", "ACC-2")] == _Point("P1", 45, 45)


async def test_a_record_read_in_another_partition_is_handed_on_whatever_its_number() -> None:
    """A read of the whole scope after a loss: an account had to 500 in P0
    whose record is now numbered 3 in P1 is handed it, and had there."""
    handed: list[Heard[ops.PositionChangedEvent]] = []

    async def hand(each: Heard[ops.PositionChangedEvent]) -> None:
        handed.append(each)

    class Identified:
        class identity:  # noqa: N801
            instance_id = "reporting-1"

    follower = _Follower(Identified(), [POSITION_CHANGED], {"PositionChanged": hand})  # type: ignore[arg-type]
    row = POSITION_CHANGED
    follower.points[(row.name, "ACC-1")] = _Point("P0", 500, 500)

    moved = position("ACC-1", "INS-A", "P1", 3, 500)
    await follower._apply(row, [moved], {"P0": 600, "P1": 3}, {"ACC-1"})

    assert [h.message.position.instrument_id for h in handed] == ["INS-A"]
    # Had in P1 now, and in P0 to where the read was answered there.
    assert follower.points[(row.name, "ACC-1")] == _Point("P1", 3, 3, {"P0": 600})
    # Read again, it is had.
    await follower._apply(row, [moved], {"P0": 600, "P1": 3}, {"ACC-1"})
    assert len(handed) == 1
