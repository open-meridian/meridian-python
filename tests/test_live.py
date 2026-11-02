"""A page's live values (`meridian.live`, `pages.live`; SDK 0.35.4, ruling
1070's 450 and 452): the step 3a samples' live cells made general.

A value worked out from rows carries its source, its confirmed time and when
it is stale, or why it has none; out of session it is closed, never stale;
with no ceiling declared it is never stale. The values of one key are worked
out from views, shared, and served as `om-live` reads them: a snapshot with
the deployment's clock, and an event per change at most every 250 ms.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.request
from collections.abc import AsyncIterator
from typing import Any

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import LiveValue, Pages
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.plugin.v1 import operations_pb2_grpc
from meridian.testing import caller_header
from meridian.v1 import sidecar_pb2_grpc

#: Thursday 2026-10-08 00:00 UTC.
NOW = 1_791_417_600_000_000_000
SECOND = 1_000_000_000
DATASET = "quotes"
EURUSD, USDJPY = "INS-EURUSD", "INS-USDJPY"
LISTED = [
    ops.DatasetRef(
        instance="oanda-1", dataset=DATASET, stale_after_ns=5 * SECOND, declared_delay_ns=0
    ),
    ops.DatasetRef(instance="ecb-1", dataset="ecb_fx"),
]
#: Weekdays, all day, in UTC: out of session on Saturday and Sunday.
WEEKDAYS = ops.TradingSessions(
    time_zone="UTC",
    sessions=[
        ops.TradingSession(
            weekdays=[
                ops.WEEKDAY_MONDAY,
                ops.WEEKDAY_TUESDAY,
                ops.WEEKDAY_WEDNESDAY,
                ops.WEEKDAY_THURSDAY,
                ops.WEEKDAY_FRIDAY,
            ],
            start_minute=0,
            end_minute=1440,
        )
    ],
)
SATURDAY = NOW + 2 * 86_400 * SECOND


def quote(
    subject: str,
    sequence: int,
    *,
    at_ns: int = NOW,
    dataset: str = DATASET,
    instance: str = "oanda-1",
    bid: int = 11000,
) -> ops.Quote:
    held = ops.Quote(
        meta=ops.ObservationMeta(
            subjects=[ops.SubjectRef(entity_id=subject)],
            source=ops.Source(instance=instance, dataset=dataset, venue_id="VEN-OANDA"),
            sequence=sequence,
            valid_from_ns=at_ns,
            recorded_at_ns=at_ns + 2_000_000,
        ),
        bid_quantity=ops.Decimal(scale=4, low=bid),
    )
    held.meta.source_times.add(kind=ops.SOURCE_TIME_KIND_EVENT, at_ns=at_ns)
    return held


def ms(ns: int) -> float:
    """A time on the page, in milliseconds to the microsecond."""
    return round(ns / 1e6, 3)


# ── A value ─────────────────────────────────────────────────────────────────


def test_a_value_carries_its_source_age_and_ceiling() -> None:
    eur = quote(EURUSD, 1, at_ns=NOW - 2 * SECOND)
    jpy = quote(USDJPY, 2, at_ns=NOW - 1 * SECOND)
    value = LiveValue.of("cell:EUR/JPY", {"mid": "162.10"}, [eur, jpy], datasets=LISTED)
    assert value.source == DATASET
    assert value.confirmed_ns == NOW - 2 * SECOND, "the oldest input's"
    assert value.stale_at_ns == NOW + 3 * SECOND, "its dataset's 5 s ceiling"
    assert value.recorded_ns == NOW - 1 * SECOND + 2_000_000, "the newest input's"
    assert not value.stale(NOW)
    assert value.stale(NOW + 4 * SECOND)
    row = value.to_json(NOW)
    assert row == {
        "key": "cell:EUR/JPY",
        "f": {"mid": "162.10"},
        "tone": {},
        "title": "",
        "source": DATASET,
        "at_ms": ms(NOW - 2 * SECOND),
        "stale_at_ms": ms(NOW + 3 * SECOND),
        "closed": False,
        "recorded_ms": ms(NOW - SECOND + 2_000_000),
        "why": "",
    }


def test_liveness_confirms_a_value_and_a_delay_is_added_to_its_ceiling() -> None:
    from meridian.roles import Liveness

    delayed = [
        ops.DatasetRef(
            instance="oanda-1",
            dataset=DATASET,
            stale_after_ns=5 * SECOND,
            declared_delay_ns=900 * SECOND,
        )
    ]
    liveness = Liveness()
    liveness.keep(ops.DatasetLiveness(dataset=DATASET, venue_id="VEN-OANDA", alive_at_ns=NOW))
    held = quote(EURUSD, 1, at_ns=NOW - 60 * SECOND)
    value = LiveValue.of("pair:EUR/USD", {}, [held], datasets=delayed, liveness=liveness)
    assert value.confirmed_ns == NOW, "its dataset's liveness after it"
    assert value.stale_at_ns == NOW + 905 * SECOND


def test_with_no_ceiling_declared_a_value_is_never_stale() -> None:
    held = quote(EURUSD, 1, at_ns=NOW - 3600 * SECOND, dataset="ecb_fx", instance="ecb-1")
    value = LiveValue.of("ref:EUR/USD", {"mid": "1.0842"}, [held], datasets=LISTED)
    assert value.stale_at_ns == 0, "no stale limit declared"
    assert not value.stale(NOW + 86_400 * SECOND)
    # An admin's own ceiling applies where the dataset declares none.
    tight = LiveValue.of("ref:EUR/USD", {}, [held], datasets=LISTED, stale_after_ns=60 * SECOND)
    assert tight.stale_at_ns == NOW - 3540 * SECOND and tight.stale(NOW)
    # And the tighter of the two where both do.
    both = LiveValue.of(
        "pair:EUR/USD", {}, [quote(EURUSD, 1)], datasets=LISTED, stale_after_ns=2 * SECOND
    )
    assert both.stale_at_ns == NOW + 2 * SECOND


def test_out_of_session_a_value_is_closed_with_its_age_and_never_stale() -> None:
    friday = quote(EURUSD, 1, at_ns=NOW + 86_400 * SECOND)
    value = LiveValue.of(
        "pair:EUR/USD", {"mid": "1.0842"}, [friday], datasets=LISTED, sessions=WEEKDAYS
    )
    assert value.closed(SATURDAY) and not value.stale(SATURDAY)
    row = value.to_json(SATURDAY)
    assert row["closed"] is True and row["at_ms"] == ms(NOW + 86_400 * SECOND)
    # Back in session (Monday), past its ceiling: stale.
    monday = NOW + 4 * 86_400 * SECOND
    assert not value.closed(monday) and value.stale(monday)


def test_a_value_with_nothing_to_show_says_why() -> None:
    value = LiveValue.of("pair:EUR/GBP", {"mid": "–"}, [None])
    assert value.why == "nothing heard yet"
    assert not value.stale(NOW)
    said = LiveValue.of("pair:EUR/GBP", {"mid": "–"}, [], why="no EUR/GBP quote is entitled")
    assert said.to_json(NOW)["why"] == "no EUR/GBP quote is entitled"


# ── The values of a page, worked out from views ─────────────────────────────


class Lake(operations_pb2_grpc.PluginOperationsServicer):
    def __init__(self) -> None:
        self.latest = {EURUSD: quote(EURUSD, 10)}
        self.head = 10
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


@pytest.fixture
async def plugin() -> AsyncIterator[tuple[Lake, Any]]:
    service, lake = FakeSidecar(), Lake()
    service.instance_id = "signal-fx-1"
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(lake, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    connected = await meridian.connect(f"127.0.0.1:{port}", heartbeat=False, roles=[])
    try:
        yield lake, connected
    finally:
        await connected.leave()
        await server.stop(grace=None)


def mids(views: Any) -> list[LiveValue]:
    """The page's values: each quote's bid, from the first view."""
    return [
        LiveValue.of(
            f"pair:{q.meta.subjects[0].entity_id}",
            {"bid": str(q.bid_quantity.low)},
            [q],
            datasets=LISTED,
        )
        for q in views[0].rows().values()
    ]


def opener(connected: Any) -> Any:
    async def views() -> list[Any]:
        return [await connected.subscribe("QuotesRecorded", subjects=[EURUSD], linger=0.1)]

    return views


async def test_one_key_is_one_set_of_values_and_its_views_close_after_its_linger(
    plugin, tmp_path
) -> None:
    lake, connected = plugin
    pages = Pages(templates=tmp_path)
    first = await pages.live_values("rates", mids, views=opener(connected), linger=0.1)
    second = await pages.live_values("rates", mids, views=opener(connected), linger=0.1)
    assert first is second, "one key, one set of values"
    assert len(lake.subscribed) == 1, "its views opened once"
    snapshot = await first.snapshot()
    assert snapshot["sequence"] == "1" and snapshot["now_ms"] > 0
    assert [r["f"]["bid"] for r in snapshot["rows"]] == ["11000"]
    await first.close()
    await asyncio.sleep(0.2)
    assert not first.dropped, "a reader is left"
    await second.close()
    await asyncio.sleep(0.4)
    assert first.dropped, "dropped after its linger"
    assert lake.unsubscribed, "the views it opened closed"
    third = await pages.live_values("rates", mids, views=opener(connected), linger=0.1)
    assert third is not first
    await third.close()


async def test_a_change_leaves_as_one_event_at_most_every_250_ms(
    plugin, tmp_path, caplog
) -> None:
    lake, connected = plugin
    pages = Pages(templates=tmp_path)
    clock = iter(range(NOW, NOW + 10**15, 10**6))
    values = await pages.live_values(
        "rates", mids, views=opener(connected), clock=lambda: next(clock)
    )
    said = await values.snapshot()
    events = values.events()
    assert await anext(events) == b"retry: 1000\n\n"
    with caplog.at_level(logging.INFO, logger="meridian.live"):
        for sequence, bid in ((11, 11001), (12, 11002), (13, 11003)):
            lake.deliver(quote(EURUSD, sequence, bid=bid, at_ns=NOW + sequence * SECOND))
        frame = await asyncio.wait_for(anext(events), timeout=3)
    head, data = frame.decode().strip().split("\n")
    assert head == f"id: {int(said['sequence']) + 1}", "the next after the snapshot's"
    body = json.loads(data.removeprefix("data: "))
    assert [r["f"]["bid"] for r in body["rows"]] == ["11003"], "the latest, once"
    assert body["sent_ms"] > 0 and body["removed"] == []
    assert any(r.getMessage() == "a page's live values sent" for r in caplog.records)
    # Two changes in quick succession: the second leaves no sooner than
    # 250 ms after the first.
    started = asyncio.get_running_loop().time()
    lake.deliver(quote(EURUSD, 14, bid=11004))
    await asyncio.wait_for(anext(events), timeout=3)
    lake.deliver(quote(EURUSD, 15, bid=11005))
    await asyncio.wait_for(anext(events), timeout=3)
    assert asyncio.get_running_loop().time() - started >= 0.25
    await events.aclose()
    await values.close()


async def test_a_value_out_of_session_changes_to_closed_with_no_new_input(
    plugin, tmp_path
) -> None:
    lake, connected = plugin
    pages = Pages(templates=tmp_path)
    now = [NOW]

    def compute(views: Any) -> dict[str, LiveValue]:
        (held,) = views[0].rows().values()
        return {"pair": LiveValue.of("pair", {}, [held], datasets=LISTED, sessions=WEEKDAYS)}

    values = await pages.live_values(
        "week", compute, views=opener(connected), clock=lambda: now[0]
    )
    assert (await values.snapshot())["rows"][0]["closed"] is False
    events = values.events()
    await anext(events)
    now[0] = SATURDAY  # the week closes; nothing new is heard
    frame = await asyncio.wait_for(anext(events), timeout=3)
    (row,) = json.loads(frame.decode().split("data: ")[1])["rows"]
    assert row["closed"] is True
    await events.aclose()
    await values.close()


async def test_a_failing_computation_is_said_and_tried_again(plugin, tmp_path, caplog) -> None:
    lake, connected = plugin
    pages = Pages(templates=tmp_path)
    failing = [True]

    def compute(views: Any) -> list[LiveValue]:
        if failing[0]:
            raise RuntimeError("the lake is restarting")
        return mids(views)

    values = await pages.live_values("rates", mids, views=opener(connected))
    await values.snapshot()
    events = values.events()
    await anext(events)
    with caplog.at_level(logging.WARNING, logger="meridian.live"):
        await pages.live_values("rates", compute, views=opener(connected))
        lake.deliver(quote(EURUSD, 11, bid=11001))
        await asyncio.sleep(0.5)
        failing[0] = False
        frame = await asyncio.wait_for(anext(events), timeout=3)
    assert b"11001" in frame
    said = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(said) == 1 and "the lake is restarting" in said[0], "said once"
    await events.aclose()
    await values.close()
    await values.close()


async def test_pages_live_serves_values_as_om_live_reads_them(plugin, tmp_path) -> None:
    lake, connected = plugin
    (tmp_path / "base.html").write_text("{% block content %}{% endblock %}")
    pages = Pages(templates=tmp_path)

    @pages.live("/rates/live", levels="read")
    async def rates(request):
        return await pages.live_values("rates", mids, views=opener(connected), linger=0.2)

    server = pages.serve(plugin=None, port=0)  # type: ignore[arg-type]
    base = f"http://127.0.0.1:{server.server_address[1]}"
    header = caller_header("read")

    def get(path: str, lines: int = 0) -> tuple[str, str, str]:
        request = urllib.request.Request(base + path)
        request.add_header("Meridian-Caller", header)
        with urllib.request.urlopen(request, timeout=10) as answer:
            kind = answer.headers["Content-Type"]
            cache = answer.headers["Cache-Control"]
            if not lines:
                return kind, cache, answer.read().decode()
            return kind, cache, "".join(answer.readline().decode() for _ in range(lines))

    try:
        kind, cache, body = await asyncio.to_thread(get, "/rates/live")
        assert kind == "application/json"
        said = json.loads(body)
        assert set(said) == {"sequence", "rows", "now_ms"}
        (row,) = said["rows"]
        assert row["key"] == f"pair:{EURUSD}" and row["source"] == DATASET
        streaming = asyncio.create_task(asyncio.to_thread(get, "/rates/live/events", 4))
        await asyncio.sleep(0.3)
        lake.deliver(quote(EURUSD, 11, bid=11001))
        kind, cache, frames = await asyncio.wait_for(streaming, timeout=5)
        assert (kind, cache) == ("text/event-stream", "no-cache")
        assert "retry: 1000" in frames and '"bid":"11001"' in frames
    finally:
        server.shutdown()
        server.server_close()
