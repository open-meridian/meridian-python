"""SDK 0.35.4: what the step 3a samples found in the views (the 3a plugin
report, decided under A after ruling 1070).

- A book record's view keys it by its entity (`views.ENTITY_KEYS`), not by
  every `*_id` it carries: an order whose venue ID is set later was held
  twice.
- A quote stating no source time is confirmed at the moment it is in force
  from (`valid_from_ns`), so the pre-trade check stops judging it stale.
- The views' stream survives a re-read that fails with something other than
  a gRPC error -- the lake down after a loss -- says so, and reads again.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian.operations import DELIVERED
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.plugin.v1 import operations_pb2_grpc
from meridian.v1 import sidecar_pb2_grpc
from meridian.views import ENTITY_KEYS, _record_key

ACCOUNT = "ACC-1"
PARTITION = "account:ACC-1"


def order(order_id: str, sequence: int, **more: str) -> ops.Order:
    return ops.Order(
        order_id=order_id,
        account_id=ACCOUNT,
        instrument_id="INS-AAPL",
        last_change=ops.JournalRef(partition=PARTITION, sequence=sequence),
        **more,
    )


class Book(operations_pb2_grpc.PluginOperationsServicer):
    """The sidecar's typed operations as a view of the book's orders meets
    them, its stream pushed by the test."""

    def __init__(self) -> None:
        self.orders = [order("ORD-1", 5)]
        self.head = 5
        self.subscribed: list[ops.SubscribeRequest] = []
        self.pushed: asyncio.Queue[ops.Delivery] = asyncio.Queue()

    async def Receive(self, request, context):  # noqa: N802
        await context.send_initial_metadata(())
        while True:
            yield await self.pushed.get()

    async def Subscribe(self, request, context):  # noqa: N802
        self.subscribed.append(request)
        return ops.SubscribeReply()

    async def Unsubscribe(self, request, context):  # noqa: N802
        return ops.UnsubscribeReply()

    async def ListOrders(self, request, context):  # noqa: N802
        return ops.ListOrdersResult(
            orders=list(self.orders),
            as_of=ops.Watermark(
                partitions=[ops.PartitionSequence(partition=PARTITION, sequence=self.head)]
            ),
        )

    def deliver(self, changed: ops.Order) -> None:
        ids = [s.subscription_id for s in self.subscribed]
        self.pushed.put_nowait(
            ops.Delivery(
                meta=ops.DeliveryMeta(
                    row="OrderUpdated",
                    subscription_ids=ids[-1:],
                    journal=changed.last_change,
                ),
                order_updated=ops.OrderUpdatedEvent(order=changed),
            )
        )


async def _serve(servicer: object) -> tuple[grpc.aio.Server, str]:
    service = FakeSidecar()
    service.instance_id = "portfolio-1"
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    return server, f"127.0.0.1:{port}"


@pytest.fixture
async def book() -> AsyncIterator[tuple[Book, str]]:
    fake = Book()
    server, address = await _serve(fake)
    try:
        yield fake, address
    finally:
        await server.stop(grace=None)


async def settled() -> None:
    await asyncio.sleep(0.1)


# ── 1. A book record keyed by its entity ─────────────────────────────────────


async def test_an_order_that_gains_a_venue_id_is_held_once(book) -> None:
    fake, address = book
    plugin = await meridian.connect(address, heartbeat=False, roles=[])
    view = await plugin.subscribe("OrderUpdated", subjects=[ACCOUNT])
    assert list(view.rows()) == ["order_id=ORD-1"]

    # The venue acknowledged it: the same order, its venue's ID set.
    fake.deliver(order("ORD-1", 6, venue_order_id="V-77", locate_id="LOC-9"))
    await settled()
    rows = view.rows()
    assert list(rows) == ["order_id=ORD-1"], "one order, held once"
    assert rows["order_id=ORD-1"].venue_order_id == "V-77", "its latest state"
    assert view.get("order_id=ORD-1").locate_id == "LOC-9"

    # Another order is another row.
    fake.deliver(order("ORD-2", 7))
    await settled()
    assert sorted(view.rows()) == ["order_id=ORD-1", "order_id=ORD-2"]
    await view.close()
    await plugin.leave()


def test_a_placement_is_keyed_by_its_own_id_whatever_is_set_later() -> None:
    first = ops.Placement(placement_id="PLC-1", order_id="ORD-1", account_id=ACCOUNT)
    later = ops.Placement(
        placement_id="PLC-1",
        order_id="ORD-1",
        account_id=ACCOUNT,
        venue_order_id="V-1",
        picked_quote_id="Q-3",
    )
    assert _record_key(first) == _record_key(later) == "placement_id=PLC-1"


def test_a_position_is_keyed_per_account_and_instrument() -> None:
    held = ops.CustodialPosition(account_id=ACCOUNT, instrument_id="INS-AAPL")
    restated = ops.CustodialPosition(
        account_id=ACCOUNT, instrument_id="INS-AAPL", last_statement_id="STM-2"
    )
    other = ops.CustodialPosition(account_id=ACCOUNT, instrument_id="INS-MSFT")
    assert _record_key(held) == _record_key(restated)
    assert _record_key(held) != _record_key(other)


def test_instructions_on_two_targets_are_two_rows() -> None:
    one = ops.TradingInstruction(target=ops.TradingInstructionTarget(account_id=ACCOUNT))
    every = ops.TradingInstruction(target=ops.TradingInstructionTarget(all_accounts=True))
    assert _record_key(one) != _record_key(every)


def test_every_book_row_a_view_keeps_names_its_entity() -> None:
    """A row added to the matrix lands here first: its record's entity named,
    never keyed by whatever identifiers it happens to carry."""
    for row in DELIVERED:
        message = row.message.DESCRIPTOR
        record = message.fields_by_name[row.within].message_type if row.within else message
        assert record.name in ENTITY_KEYS, f"{row.name}: name {record.name}'s entity"
        for path in ENTITY_KEYS[record.name]:
            held = record
            for name in path.split("."):
                assert name in held.fields_by_name, f"{record.name} has no {path}"
                found = held.fields_by_name[name]
                held = found.message_type or held
