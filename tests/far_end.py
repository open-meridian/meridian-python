"""A sidecar in a process of its own, for the tests that kill a stream's far
end abruptly (SIGKILL, no graceful close) under a live subscription
(tests/test_sdk_036.py; SDK 0.36.0, the dev deployment's lake OOM-killed on
2026-11-09).

    python tests/far_end.py <port> <first sequence>

It registers any plugin, answers its subscriptions, and on every stream
delivers one quote of EUR/USD every 20 ms, its sequence counting up from
the first given, each matched to every subscription open; the latest read
(`ListQuotes`) answers the last quote delivered. It prints `ready` once it
listens, and runs until it is killed.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import grpc

sys.path.insert(0, str(Path(__file__).parent))

from conftest import FakeSidecar  # noqa: E402
from meridian.plugin.v1 import operations_pb2 as ops  # noqa: E402
from meridian.plugin.v1 import operations_pb2_grpc  # noqa: E402
from meridian.v1 import sidecar_pb2_grpc  # noqa: E402

DATASET = "oanda-1:quotes"
EURUSD = "INS-EURUSD"
TICK_SECONDS = 0.02


def quote(sequence: int) -> ops.Quote:
    """A quote whose bid quantity is its sequence, so a test reads which it is."""
    return ops.Quote(
        meta=ops.ObservationMeta(
            subjects=[ops.SubjectRef(entity_id=EURUSD)],
            source=ops.Source(dataset=DATASET, venue_id="VEN-OANDA"),
            sequence=sequence,
            recorded_at_ns=1_791_417_600_000_000_000 + sequence,
        ),
        bid=ops.Money(currency_code="USD", instrument_id="INS-USD"),
        bid_quantity=ops.Decimal(scale=0, low=sequence),
    )


class Lake(operations_pb2_grpc.PluginOperationsServicer):
    def __init__(self, first: int) -> None:
        self.head = first
        self.subscriptions: set[str] = set()

    async def ticking(self) -> None:
        while True:
            await asyncio.sleep(TICK_SECONDS)
            self.head += 1

    async def Receive(self, request, context):  # noqa: N802
        await context.send_initial_metadata(())
        sent = self.head
        while True:
            await asyncio.sleep(TICK_SECONDS / 2)
            if self.head == sent:
                continue
            sent = self.head
            yield ops.Delivery(
                meta=ops.DeliveryMeta(
                    row="QuotesRecorded", subscription_ids=sorted(self.subscriptions)
                ),
                quotes_recorded=ops.QuotesRecordedEvent(quote=quote(sent)),
            )

    async def Subscribe(self, request, context):  # noqa: N802
        self.subscriptions.add(request.subscription_id)
        return ops.SubscribeReply()

    async def Unsubscribe(self, request, context):  # noqa: N802
        self.subscriptions.discard(request.subscription_id)
        return ops.UnsubscribeReply()

    async def ListQuotes(self, request, context):  # noqa: N802
        return ops.ListQuotesResult(
            quotes=[quote(self.head)],
            watermark=ops.Watermark(
                partitions=[ops.PartitionSequence(partition=DATASET, sequence=self.head)]
            ),
        )

    async def ListDatasets(self, request, context):  # noqa: N802
        return ops.ListDatasetsResult()


async def main(port: int, first: int) -> None:
    service, lake = FakeSidecar(), Lake(first)
    service.instance_id = "signal-fx-1"
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(lake, server)
    server.add_insecure_port(f"127.0.0.1:{port}")
    await server.start()
    ticking = asyncio.create_task(lake.ticking())
    print("ready", flush=True)
    try:
        await server.wait_for_termination()
    finally:
        ticking.cancel()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), int(sys.argv[2])))
