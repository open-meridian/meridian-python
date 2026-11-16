"""Step 3d, from the plugin's side: a standby pod's plugin held until its
sidecar serves it, and stopped when the sidecar is lost (the resilience
spec's section 7).

A standby pod's sidecar holds no Lease, and serves its plugin only once it
takes the instance's; a holder's that loses it stops serving. What the SDK
holds of that is here: nothing of the plugin starts before the sidecar
answers, however long that takes; two heartbeats in a row left unanswered
stop the plugin's classes; and the process stays, waiting for the sidecar to
serve it again as a standby does (PO item 50), so its container is never
restarted under the kubelet's back-off.
"""

from __future__ import annotations

import asyncio
import contextlib
import http.server
import logging
import socket
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

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
    """A class with a session to hold: what a standby must not start. It
    keeps what happened to it in order, and how many of its `run()`s ran at
    once at most."""

    def __init__(self) -> None:
        self.started = self.stopped = self.cancelled = 0
        self.running = asyncio.Event()
        self.said: list[str] = []
        self.live = self.most = 0

    async def on_start(self) -> None:
        self.started += 1
        self.said.append("start")

    async def run(self) -> None:
        self.live += 1
        self.most = max(self.most, self.live)
        self.said.append("run")
        self.running.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        finally:
            self.live -= 1

    async def on_stop(self) -> None:
        self.stopped += 1
        self.said.append("stop")
        self.running.clear()


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


class _Serving(FakeSidecar):
    """One serving of the sidecar, a new one each time it takes the Lease:
    as core's, it answers a heartbeat before any Register with
    FAILED_PRECONDITION."""

    async def Heartbeat(self, request, context):  # noqa: N802
        if not self.registered:
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "not registered: call Register before any other operation",
            )
        return await super().Heartbeat(request, context)


def _custody() -> FakeSidecar:
    service = _Serving()
    service.roles = ("custody",)
    return service


async def _until(check: Callable[[], bool], timeout: float = 5.0) -> None:
    for _ in range(int(timeout / 0.01)):
        if check():
            return
        await asyncio.sleep(0.01)
    assert check(), "not reached in time"


def _tasks() -> list[str]:
    """The tasks on the loop, by what each runs, the caller's own aside."""
    me = asyncio.current_task()
    return sorted(
        getattr(task.get_coro(), "__qualname__", repr(task.get_coro()))
        for task in asyncio.all_tasks()
        if task is not me
    )


async def _ended(task: asyncio.Task[None], server: grpc.aio.Server | None) -> None:
    """`task` cancelled, and the sidecar's server stopped even where the
    task had ended on something else, which is raised."""
    try:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    finally:
        if server is not None:
            await server.stop(grace=None)


def _threads() -> int:
    """The threads running, the loop's own executor's aside (`_status`
    asks through it, and its workers stay for the next ask)."""
    return sum(not each.name.startswith("asyncio_") for each in threading.enumerate())


async def _status(port: int) -> int:
    """The HTTP status the pages on `port` answer `/` with."""

    def ask() -> int:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as answered:
                return int(answered.status)
        except urllib.error.HTTPError as answered:
            return int(answered.code)

    return await asyncio.to_thread(ask)


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
        await _ended(task, server)
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


async def test_a_holder_whose_sidecar_is_lost_stops_its_classes_and_waits_to_register_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sidecar gone (it lost the instance's Lease): after two heartbeats
    in a row unanswered the `run()` is cancelled and `on_stop()` called, and
    `run_async` neither raises nor ends. It waits for the sidecar as a
    standby does, starting nothing, and once the sidecar serves it again it
    registers again and its classes start again."""
    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.05)
    monkeypatch.setattr(running, "_ATTEMPT_SECONDS", 0.2)
    monkeypatch.setattr(running, "_ATTEMPT_PAUSE_SECONDS", 0.05)
    first = _custody()
    server = await _serving(first, port)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        async with first.beat:
            await asyncio.wait_for(first.beat.wait(), timeout=5)
        await server.stop(grace=None)
        await _until(lambda: session.stopped == 1 or task.done())
        assert not task.done(), task.exception()
        assert session.cancelled == 1
        # Several heartbeats' and attempts' time without a sidecar: still
        # waiting, nothing started again.
        await asyncio.sleep(0.5)
        assert not task.done(), task.exception()
        assert session.said == ["start", "run", "stop"]

        second = _custody()
        server = await _serving(second, port)
        await asyncio.wait_for(session.running.wait(), timeout=5)
        assert len(first.registered) == 1 and len(second.registered) == 1
        assert session.said == ["start", "run", "stop", "start", "run"]
        assert session.plugin.identity.instance_id == second.instance_id
    finally:
        await _ended(task, server)
    assert session.said == ["start", "run", "stop", "start", "run", "stop"]
    assert session.most == 1


async def test_a_sidecar_that_exits_ends_the_stream_and_the_watch_and_the_plugin_waits_for_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sidecar that exits ends the plugin's stream and its settings watch
    with it. Each is opened again, as for any break, until the heartbeats
    say the sidecar is lost; then the plugin's classes stop once, whatever
    the stream and the watch were doing, and the plugin waits for the
    sidecar. Served again, the settings are applied again before any class
    starts, and the stream is opened again."""
    from meridian.v1 import sidecar_pb2

    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.2)
    monkeypatch.setattr(running, "_ATTEMPT_SECONDS", 0.2)
    monkeypatch.setattr(running, "_ATTEMPT_PAUSE_SECONDS", 0.05)
    first = _custody()
    first.settings = [sidecar_pb2.SettingsDelivery()]
    server = await _serving(first, port)
    applied: list[object] = []

    starts: list[int] = []

    class Hearing(_Session):
        async def on_start(self) -> None:
            starts.append(len(applied))
            await super().on_start()

        async def on_replace_merged_instrument(self, heard: object) -> None:
            return None

    session = Hearing()
    assert Hearing.heard_rows()
    task = asyncio.create_task(
        meridian.run_async(meridian.Declaration(), [session], on_settings=applied.append)
    )
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        await _until(lambda: bool(first.operations.received))
        await server.stop(grace=None)
        await _until(lambda: session.stopped == 1 or task.done(), timeout=10)
        assert not task.done(), task.exception()
        assert session.cancelled == 1 and session.started == 1
        had = len(applied)

        second = _custody()
        second.settings = [sidecar_pb2.SettingsDelivery()]
        server = await _serving(second, port)
        await asyncio.wait_for(session.running.wait(), timeout=10)
        await _until(lambda: bool(second.operations.received))
        assert session.said == ["start", "run", "stop", "start", "run"]
        assert starts[0] >= 1 and starts[1] > had
    finally:
        await _ended(task, server)
    assert session.started == 2 and session.stopped == 2 and session.most == 1


async def test_a_sidecar_lost_before_the_first_settings_starts_nothing_and_is_waited_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first settings are applied before any class starts. A sidecar
    lost before it delivers them ends that wait too: no class has started,
    so none is stopped, and the plugin waits for the sidecar again."""
    from meridian.v1 import sidecar_pb2

    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.05)
    monkeypatch.setattr(running, "_ATTEMPT_SECONDS", 0.2)
    monkeypatch.setattr(running, "_ATTEMPT_PAUSE_SECONDS", 0.05)
    first = _custody()  # delivers no settings: the watch ends at once, each time
    server = await _serving(first, port)
    applied: list[object] = []
    session = _Session()
    task = asyncio.create_task(
        meridian.run_async(meridian.Declaration(), [session], on_settings=applied.append)
    )
    try:
        await _until(lambda: len(first.heartbeats) >= 1)
        lost = session.plugin._sidecar_lost
        await server.stop(grace=None)
        await asyncio.wait_for(lost.wait(), timeout=5)
        second = _custody()
        second.settings = [sidecar_pb2.SettingsDelivery()]
        server = await _serving(second, port)
        await asyncio.wait_for(session.running.wait(), timeout=10)
        assert len(second.registered) == 1 and len(applied) == 1
        assert session.said == ["start", "run"]
    finally:
        await _ended(task, server)
    assert session.said == ["start", "run", "stop"]


async def test_a_sidecar_serving_again_within_two_heartbeats_is_registered_with_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sidecar that lost the Lease and took one again before two
    heartbeats went unanswered serves anew: it holds no registration of
    this plugin's, and says so on the next heartbeat. That registration is
    gone, so the classes stop and the plugin registers again at once."""
    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.2)
    monkeypatch.setattr(running, "_ATTEMPT_SECONDS", 0.5)
    monkeypatch.setattr(running, "_ATTEMPT_PAUSE_SECONDS", 0.05)
    first = _custody()
    server = await _serving(first, port)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        await server.stop(grace=None)
        second = _custody()
        server = await _serving(second, port)
        await _until(lambda: (session.started == 2 and session.running.is_set()) or task.done())
        assert not task.done(), task.exception()
        assert len(second.registered) == 1
        assert session.said == ["start", "run", "stop", "start", "run"]
    finally:
        await _ended(task, server)


async def test_many_losses_in_a_row_leak_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lost and served again five times, with pages, settings, figures and
    a stream: each wait for the sidecar holds what the first wait held --
    no task and no thread of an earlier serving left running, the pages'
    socket closed -- and each serving starts the classes once, stops them
    once, and serves the pages on the same port again."""
    from meridian.v1 import sidecar_pb2

    port = _free_port()
    pages_port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.05)
    monkeypatch.setattr(running, "FIGURES_SECONDS", 0.05)
    # One attempt outlasts each wait, so every wait is in the same state.
    monkeypatch.setattr(running, "_ATTEMPT_SECONDS", 60.0)

    class Hearing(_Session):
        async def on_replace_merged_instrument(self, heard: object) -> None:
            return None

    pages: list[http.server.ThreadingHTTPServer] = []
    serve = meridian.Pages.serve

    def serving_pages(*given: Any, **named: Any) -> http.server.ThreadingHTTPServer:
        pages.append(serve(*given, **named))
        return pages[-1]

    monkeypatch.setattr(meridian.Pages, "serve", serving_pages)
    session = Hearing()
    applied: list[object] = []
    task = asyncio.create_task(
        meridian.run_async(
            meridian.Declaration(),
            [session],
            pages=meridian.Pages(),
            port=pages_port,
            on_settings=applied.append,
            figures=lambda: (),
        )
    )
    plugins: list[object] = []
    servings: list[FakeSidecar] = []
    server = None
    try:
        await asyncio.sleep(0.2)
        waiting, threads = _tasks(), _threads()
        assert session.started == 0
        for serving in range(1, 6):
            service = _custody()
            service.settings = [sidecar_pb2.SettingsDelivery()]
            servings.append(service)
            server = await _serving(service, port)
            await asyncio.wait_for(session.running.wait(), timeout=10)
            await _until(lambda s=service: bool(s.operations.received))  # type: ignore[misc]
            assert session.started == serving and session.stopped == serving - 1
            assert await _status(pages_port) in (200, 401, 403, 404)
            plugins.append(session.plugin)
            await server.stop(grace=None)
            server = None
            await _until(lambda n=serving: session.stopped == n or task.done(), timeout=10)  # type: ignore[misc]
            assert not task.done(), task.exception()
            with contextlib.suppress(AssertionError):
                await _until(lambda: (_tasks(), _threads()) == (waiting, threads))
            assert (_tasks(), _threads()) == (waiting, threads)
            assert len(pages) == serving and pages[-1].socket.fileno() == -1
        assert session.said == ["start", "run", "stop"] * 5 and session.most == 1
        assert [len(each.registered) for each in servings] == [1] * 5
        for each in plugins:
            assert each._left and each._heartbeat.done()  # type: ignore[attr-defined]
    finally:
        await _ended(task, server)


async def test_the_started_report_unanswered_is_carried_by_the_next_heartbeat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The report that says the plugin started is one heartbeat: a sidecar
    not there to answer it is one heartbeat unanswered, not a fault of the
    plugin's. The health stands, and the next heartbeat carries it."""
    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.3)
    service = _Sidecar()
    service.roles = ("custody",)
    service.unanswered = (True,)
    server = await _serving(service, port)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await _until(lambda: len(service.heartbeats) >= 2 or task.done())
        assert not task.done(), task.exception()
        assert service.heartbeats[1].healthy and service.heartbeats[1].detail == "started"
        assert session.started == 1 and session.stopped == 0
    finally:
        await _ended(task, server)


async def test_the_started_report_refused_is_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only a sidecar not there to answer is waited out: a sidecar that
    answers the report and refuses it has said something about the plugin,
    and that is raised as before."""
    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 5.0)

    class Refusing(FakeSidecar):
        async def Heartbeat(self, request, context):  # noqa: N802
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "no")

    service = Refusing()
    service.roles = ("custody",)
    server = await _serving(service, port)
    session = _Session()
    try:
        with pytest.raises(grpc.aio.AioRpcError) as raised:
            await asyncio.wait_for(
                meridian.run_async(meridian.Declaration(), [session]), timeout=5
            )
        assert raised.value.code() == grpc.StatusCode.PERMISSION_DENIED
    finally:
        await server.stop(grace=None)
    assert session.started == 1 and session.stopped == 1


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
