"""Views: a targeted read kept open, the copy kept by the SDK (W4.3; contract
v28, amended 2026-10-30; spec/one-data-access-model, step 2).

Against a fake sidecar that answers Subscribe, the snapshot's read, and a
stream the test pushes deliveries into: the SDK's half -- subscribe, a
snapshot at W, a delivery at W dropped, a gap or a loss marker caught up, one
view shared by two pages and dropped after its linger, entitlements changed
while a view is open, and the page channel's conflation. What the sidecar
matches and masks is meridian-core's to test.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.plugin.v1 import operations_pb2_grpc
from meridian.v1 import sidecar_pb2_grpc

DATASET = "oanda-1:quotes"
EURUSD = "INS-EURUSD"


def quote(sequence: int, bid: str, subject: str = EURUSD) -> ops.Quote:
    return ops.Quote(
        meta=ops.ObservationMeta(
            subjects=[ops.SubjectRef(entity_id=subject)],
            source=ops.Source(dataset=DATASET, venue_id="VEN-OANDA"),
            sequence=sequence,
            recorded_at_ns=1_791_417_600_000_000_000 + sequence,
        ),
        bid=ops.Money(currency_code="USD", instrument_id="INS-USD"),
        bid_quantity=ops.Decimal(scale=0, low=int(bid.replace(".", ""))),
    )


class Lake(operations_pb2_grpc.PluginOperationsServicer):
    """The sidecar's typed operations as views meet them."""

    def __init__(self) -> None:
        self.latest: dict[str, ops.Quote] = {EURUSD: quote(10, "1.1000")}
        self.head = 10
        self.reads = 0
        self.subscribed: list[ops.SubscribeRequest] = []
        self.unsubscribed: list[str] = []
        self.pushed: asyncio.Queue[ops.Delivery] = asyncio.Queue()

    async def Receive(self, request, context):  # noqa: N802
        await context.send_initial_metadata(())
        while True:
            yield await self.pushed.get()

    async def Subscribe(self, request, context):  # noqa: N802
        self.subscribed.append(request)
        return ops.SubscribeReply()

    async def Unsubscribe(self, request, context):  # noqa: N802
        self.unsubscribed.append(request.subscription_id)
        return ops.UnsubscribeReply()

    async def ListQuotes(self, request, context):  # noqa: N802
        self.reads += 1
        return ops.ListQuotesResult(
            quotes=list(self.latest.values()),
            watermark=ops.Watermark(
                partitions=[ops.PartitionSequence(partition=DATASET, sequence=self.head)]
            ),
        )

    def deliver(self, held: ops.Quote) -> None:
        ids = [s.subscription_id for s in self.subscribed]
        self.pushed.put_nowait(
            ops.Delivery(
                meta=ops.DeliveryMeta(row="QuotesRecorded", subscription_ids=ids[-1:]),
                quotes_recorded=ops.QuotesRecordedEvent(quote=held),
            )
        )

    def lose(self) -> None:
        self.pushed.put_nowait(
            ops.Delivery(meta=ops.DeliveryMeta(), lost=ops.Lost(rows=["QuotesRecorded"]))
        )


@pytest.fixture
async def lake() -> AsyncIterator[tuple[Lake, str]]:
    service, lake = FakeSidecar(), Lake()
    service.instance_id = "signal-fx-1"
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(lake, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield lake, f"127.0.0.1:{port}"
    finally:
        await server.stop(grace=None)


def bid_of(view: meridian.LiveView) -> int:
    (only,) = view.rows().values()
    return only.bid_quantity.low


async def settled() -> None:
    await asyncio.sleep(0.1)


async def test_a_view_is_its_snapshot_then_the_deliveries_above_it(lake) -> None:
    fake, address = lake
    plugin = await meridian.connect(address, heartbeat=False)
    view = await plugin.subscribe(
        "QuotesRecorded", subjects=[EURUSD], fields=["meridian.v1.Quote.bid"]
    )
    asked = fake.subscribed[0]
    assert (asked.row, list(asked.subjects), list(asked.fields)) == (
        "QuotesRecorded",
        [EURUSD],
        ["meridian.v1.Quote.bid"],
    )
    assert bid_of(view) == 11000, "the snapshot, read at W = 10"

    fake.deliver(quote(10, "1.0999"))  # at W: in the snapshot already
    await settled()
    assert bid_of(view) == 11000, "a delivery at W dropped"
    fake.deliver(quote(11, "1.1001"))
    await settled()
    assert bid_of(view) == 11001, "a delivery above W applied"
    await view.close()
    await plugin.leave()


async def test_a_loss_marker_reads_the_view_again(lake) -> None:
    fake, address = lake
    plugin = await meridian.connect(address, heartbeat=False)
    view = await plugin.subscribe("QuotesRecorded", subjects=[EURUSD])
    assert fake.reads == 1
    # A change the stream dropped, the store holding it: an injected gap.
    fake.latest[EURUSD] = quote(15, "1.1005")
    fake.head = 15
    fake.lose()
    await settled()
    assert fake.reads == 2, "read again, for that selector"
    assert bid_of(view) == 11005
    fake.deliver(quote(14, "1.1004"))
    await settled()
    assert bid_of(view) == 11005, "below the new watermark: dropped"
    await view.close()
    await plugin.leave()


async def test_one_view_is_shared_by_two_pages_and_dropped_after_its_linger(lake) -> None:
    fake, address = lake
    plugin = await meridian.connect(address, heartbeat=False)
    first = await plugin.subscribe("QuotesRecorded", subjects=[EURUSD], linger=0.2)
    second = await plugin.subscribe("QuotesRecorded", subjects=[EURUSD], linger=0.2)
    assert len(fake.subscribed) == 1, "identical selectors are one subscription"
    assert first.subscription_id == second.subscription_id
    await first.close()
    await asyncio.sleep(0.3)
    assert fake.unsubscribed == [], "a reader is left"
    await second.close()
    await asyncio.sleep(0.1)
    assert fake.unsubscribed == [], "within its linger"
    # A page reloaded within the linger keeps the subscription.
    again = await plugin.subscribe("QuotesRecorded", subjects=[EURUSD], linger=0.2)
    assert len(fake.subscribed) == 1
    await again.close()
    await asyncio.sleep(0.35)
    assert fake.unsubscribed == [first.subscription_id]
    await plugin.leave()


async def test_entitlements_changed_while_a_view_is_open_reach_it_as_delivered(lake) -> None:
    """The sidecar decides the mask (meridian-core's test); the view keeps
    whatever whole state is delivered, a field withdrawn left unset."""
    fake, address = lake
    plugin = await meridian.connect(address, heartbeat=False)
    view = await plugin.subscribe("QuotesRecorded", subjects=[EURUSD])
    masked = quote(12, "1.1002")
    masked.ClearField("bid_quantity")
    fake.deliver(masked)
    await settled()
    (only,) = view.rows().values()
    assert not only.HasField("bid_quantity")
    await view.close()
    await plugin.leave()


async def test_the_page_channel_conflates_per_key_over_250_ms(lake) -> None:
    fake, address = lake
    plugin = await meridian.connect(address, heartbeat=False)
    view = await plugin.subscribe("QuotesRecorded", subjects=[EURUSD])
    snapshot = view.snapshot()
    assert snapshot["sequence"] == "0", "nothing changed since the snapshot"
    assert len(snapshot["rows"]) == 1
    events = view.events()
    assert await anext(events) == b"retry: 1000\n\n"
    for sequence in (11, 12, 13):
        fake.deliver(quote(sequence, f"1.10{sequence:02d}"))
    frame = await asyncio.wait_for(anext(events), timeout=1)
    head, data = frame.decode().strip().split("\n")
    assert head == "id: 1", "the next sequence after the snapshot's"
    rows = json.loads(data.removeprefix("data: "))["rows"]
    assert len(rows) == 1, "one change per key per 250 ms"
    assert rows[0]["bid_quantity"]["low"] == "11013", "the latest"
    await events.aclose()
    await view.close()
    await plugin.leave()


async def test_a_live_channel_is_served_as_om_live_reads_it(lake, tmp_path) -> None:
    """`pages.live`: the snapshot as JSON, and the event stream sent as it
    is made through the standard library's server."""
    import urllib.request

    from meridian import Pages
    from meridian.testing import caller_header

    fake, address = lake
    plugin = await meridian.connect(address, heartbeat=False)
    (tmp_path / "base.html").write_text("{% block content %}{% endblock %}")
    pages = Pages(templates=tmp_path)

    @pages.live("/rates/live", levels="read")
    async def rates(request):
        return await plugin.subscribe("QuotesRecorded", subjects=[EURUSD], linger=0.2)

    server = pages.serve(plugin=None, port=0)  # type: ignore[arg-type]
    base = f"http://127.0.0.1:{server.server_address[1]}"
    header = caller_header("read")

    def get(path: str, lines: int = 0) -> tuple[str, str]:
        request = urllib.request.Request(base + path)
        request.add_header("Meridian-Caller", header)
        with urllib.request.urlopen(request, timeout=10) as answer:
            kind = answer.headers["Content-Type"]
            if not lines:
                return kind, answer.read().decode()
            got = [answer.readline().decode() for _ in range(lines)]
            return kind, "".join(got)

    try:
        kind, body = await asyncio.to_thread(get, "/rates/live")
        assert kind == "application/json"
        said = json.loads(body)
        assert said["sequence"] == "0" and len(said["rows"]) == 1
        streaming = asyncio.create_task(asyncio.to_thread(get, "/rates/live/events", 4))
        await asyncio.sleep(0.3)
        fake.deliver(quote(11, "1.1001"))
        kind, frames = await asyncio.wait_for(streaming, timeout=5)
        assert kind == "text/event-stream"
        assert "retry: 1000" in frames and "id: 1" in frames
    finally:
        server.shutdown()
        server.server_close()
        await plugin.leave()
