"""Step 3d, from the plugin's side: a standby pod's plugin held until its
sidecar serves it, and stopped when the sidecar is lost (the resilience
spec's section 7).

A standby pod's sidecar holds no Lease, and serves its plugin only once it
takes the instance's; a holder's that loses it stops serving. What the SDK
holds of that is here: nothing of the plugin starts before the sidecar
answers, however long that takes, and two heartbeats in a row left
unanswered stop it.
"""

from __future__ import annotations

import asyncio
import logging
import socket

import grpc
import pytest

import meridian
import meridian._run as running
import meridian.client as client
from conftest import FakeSidecar
from meridian.plugin.v1 import operations_pb2_grpc
from meridian.roles import custody
from meridian.v1 import sidecar_pb2_grpc


class _Session(custody.Role):
    """A class with a session to hold: what a standby must not start."""

    def __init__(self) -> None:
        self.started = self.stopped = 0
        self.running = asyncio.Event()
        self.cancelled = False

    async def on_start(self) -> None:
        self.started += 1

    async def run(self) -> None:
        self.running.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def on_stop(self) -> None:
        self.stopped += 1


class _Sidecar(FakeSidecar):
    """A sidecar whose heartbeats a test leaves unanswered: `unanswered`
    holds, per beat in order, whether it is not there to answer it."""

    unanswered: tuple[bool, ...] = ()

    async def Heartbeat(self, request, context):  # noqa: N802
        beat = len(self.heartbeats)
        if beat < len(self.unanswered) and self.unanswered[beat]:
            self.heartbeats.append(request)
            await context.abort(grpc.StatusCode.UNAVAILABLE, "not serving")
        return await super().Heartbeat(request, context)


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


async def _serving(service: FakeSidecar, port: int) -> grpc.aio.Server:
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(service.operations, server)
    assert server.add_insecure_port(f"127.0.0.1:{port}") == port
    await server.start()
    return server


async def test_a_standby_s_classes_start_only_once_its_sidecar_serves_it(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """No sidecar answers for several waits, as a standby pod's does not
    until it takes the Lease: `run` gives up on none of them and starts
    nothing; the sidecar serving, the classes start."""
    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(running, "_ATTEMPT_SECONDS", 0.2)
    monkeypatch.setattr(running, "_ATTEMPT_PAUSE_SECONDS", 0.05)
    caplog.set_level(logging.INFO, logger="meridian.run")
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    server = None
    try:
        for _ in range(200):
            waits = [r for r in caplog.records if "waiting for the sidecar" in r.getMessage()]
            if len(waits) >= 3:
                break
            await asyncio.sleep(0.025)
        # Three waits over, each one `connect` alone would have ended on.
        assert len(waits) >= 3 and not task.done()
        assert "a standby pod waits here for its lease" in waits[0].getMessage()
        assert session.started == 0 and not session.running.is_set()

        service = FakeSidecar()
        service.roles = ("custody",)
        server = await _serving(service, port)
        await asyncio.wait_for(session.running.wait(), timeout=5)
        assert session.started == 1
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        if server is not None:
            await server.stop(grace=None)
    assert session.stopped == 1


async def test_a_wait_for_the_sidecar_ends_when_the_process_is_stopped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{_free_port()}")
    monkeypatch.setattr(running, "_ATTEMPT_SECONDS", 30.0)
    stopped = asyncio.Event()
    waiting = asyncio.create_task(running._connected(meridian.Declaration(), [], stopped))
    await asyncio.sleep(0.1)
    assert not waiting.done()
    stopped.set()
    assert await asyncio.wait_for(waiting, timeout=2) is None


async def test_a_refusal_is_not_waited_out(monkeypatch: pytest.MonkeyPatch, sidecar) -> None:
    """A sidecar that answers and refuses has said why: asking again changes
    nothing, and the wait for one not answering is not for it."""
    service, address = sidecar
    service.admitted, service.refusal_reason = False, "no grant for custody"
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    with pytest.raises(meridian.Refused, match="no grant for custody"):
        await asyncio.wait_for(meridian.run_async(meridian.Declaration(), []), timeout=5)


async def test_a_holder_whose_sidecar_stops_serving_stops_its_classes_and_leaves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sidecar gone (it lost the instance's Lease): after two heartbeats
    in a row unanswered the `run()` is cancelled, `on_stop()` called, and
    `run_async` raises, so the process leaves and its pod starts a standby."""
    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.05)
    service = FakeSidecar()
    service.roles = ("custody",)
    server = await _serving(service, port)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        async with service.beat:
            await asyncio.wait_for(service.beat.wait(), timeout=5)
        assert not task.done()
        await server.stop(grace=None)
        with pytest.raises(meridian.NoSidecar, match=f"127.0.0.1:{port}"):
            await asyncio.wait_for(task, timeout=5)
    finally:
        if not task.done():
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    assert session.cancelled and session.stopped == 1


async def test_a_sidecar_that_exits_ends_the_stream_and_the_watch_and_the_plugin_leaves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Core's sidecar exits when it loses the Lease, so the plugin's stream
    and its settings watch end with it. Each is opened again, as for any
    break, until the heartbeats say the sidecar is lost; then the plugin
    stops once and leaves, whatever the stream and the watch were doing."""
    from meridian.v1 import sidecar_pb2

    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.2)
    service = FakeSidecar()
    service.roles = ("custody",)
    service.settings = [sidecar_pb2.SettingsDelivery()]
    server = await _serving(service, port)
    applied: list[object] = []

    class Hearing(_Session):
        async def on_replace_merged_instrument(self, heard: object) -> None:
            return None

    session = Hearing()
    assert Hearing.heard_rows()
    task = asyncio.create_task(
        meridian.run_async(meridian.Declaration(), [session], on_settings=applied.append)
    )
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        for _ in range(200):
            if service.operations.received:
                break
            await asyncio.sleep(0.01)
        assert service.operations.received and applied
        await server.stop(grace=None)
        with pytest.raises(meridian.NoSidecar):
            await asyncio.wait_for(task, timeout=10)
    finally:
        if not task.done():
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    assert session.cancelled and session.started == 1 and session.stopped == 1


async def test_one_heartbeat_unanswered_is_not_a_sidecar_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Counted in a row: a beat unanswered, one answered, one unanswered is a
    sidecar still there; two in a row is one lost."""
    port = _free_port()
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.02)
    service = _Sidecar()
    service.unanswered = (True, False, True, False, False, False, False, False)
    server = await _serving(service, port)
    plugin = await meridian.connect(f"127.0.0.1:{port}", roles=[])
    try:
        for _ in range(500):
            if len(service.heartbeats) >= 8:
                break
            await asyncio.sleep(0.01)
        assert len(service.heartbeats) >= 8 and not plugin._sidecar_lost.is_set()
        service.unanswered = (True,) * 10_000
        await asyncio.wait_for(plugin._sidecar_lost.wait(), timeout=5)
    finally:
        await plugin.leave()
        await server.stop(grace=None)


def test_run_leaves_with_status_1_when_its_sidecar_is_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def lost(*_: object, **__: object) -> None:
        raise meridian.NoSidecar("127.0.0.1:50051", 10.0)

    monkeypatch.setattr(running, "run_async", lost)
    with pytest.raises(SystemExit) as left:
        meridian.run(meridian.Declaration(), [])
    assert left.value.code == 1
