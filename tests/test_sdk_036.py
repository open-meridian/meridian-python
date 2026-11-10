"""SDK 0.36.0: contract 30 (sdk-contract/standing-analytics-and-resilience-
contract), and a stream held to its far end.

- A standing job (`analytics.Jobs.standing`): registered, subscribed by its
  job ID, its figures kept in a `LiveView` from `DerivedSeriesUpdated` in its
  sequence, read again whole after a gap, registered again when the
  component no longer holds it.
- A stream whose far end is killed abruptly (SIGKILL, no graceful close)
  under a live subscription -- shortly after it opened, and while it was
  opening again -- and one whose far end stays connected but goes silent:
  the view and the role's handler catch up each time. The dev deployment's
  lake was OOM-killed on 2026-11-09 and a plugin's view stayed frozen for six
  hours until it was relaunched; a graceful pod delete never froze it.
- The declaration's contract 30 fields, a dataset's trading sessions read
  from its calendar, and an event contract's terms and category stated.
"""

from __future__ import annotations

import asyncio
import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import AsyncIterator, Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import analytics
from meridian.helpers import sessions
from meridian.operations import _decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.plugin.v1 import operations_pb2_grpc
from meridian.receive import Heard, follow
from meridian.suites import Recorder
from meridian.v1 import sidecar_pb2, sidecar_pb2_grpc

HERE = Path(__file__).parent
JOB = "JOB-01JC30STANDING000000000001"
AGAIN = "JOB-01JC30STANDING000000000002"
ACCOUNT = "ACC-01JC30STANDING00000000001"
EURUSD = "INS-EURUSD"


async def until(done: Callable[[], bool], seconds: float = 10.0) -> None:
    """Until `done`, at most `seconds`, or the test fails."""
    deadline = time.monotonic() + seconds
    while not done():
        if time.monotonic() > deadline:
            raise AssertionError(f"not within {seconds} s")
        await asyncio.sleep(0.02)


def figure(value: str, account: str = ACCOUNT) -> ops.Figure:
    return ops.Figure(
        measure=ops.MeasureRef(definition="exposure", version=1),
        account_id=account,
        value=_decimal(Decimal(value), "value"),
    )


# ── A standing job ─────────────────────────────────────────────────────────


class Engine(operations_pb2_grpc.PluginOperationsServicer):
    """The sidecar's side of a standing job: RunJob, Subscribe, ReadJobAnswer
    and the stream its updates are pushed into."""

    def __init__(self) -> None:
        self.jobs: list[ops.RunJobParams] = []
        self.subscribed: list[ops.SubscribeRequest] = []
        self.unsubscribed: list[str] = []
        self.reads: list[str] = []
        self.answer: dict[str, list[ops.Figure]] = {JOB: [figure("100")]}
        self.held = {JOB}
        self.read_delay = 0.0
        self.pushed: asyncio.Queue[ops.Delivery] = asyncio.Queue()

    async def RunJob(self, request, context):  # noqa: N802
        self.jobs.append(request)
        job_id = JOB if len(self.jobs) == 1 else AGAIN
        self.held.add(job_id)
        self.answer.setdefault(job_id, [figure("300")])
        return ops.RunJobResult(answered_inline=False, job_id=job_id)

    async def ReadJobAnswer(self, request, context):  # noqa: N802
        self.reads.append(request.job_id)
        if request.job_id not in self.held:
            await context.abort(grpc.StatusCode.NOT_FOUND, f"{request.job_id} is not held")
        answered = list(self.answer[request.job_id])  # as of the read's start
        await asyncio.sleep(self.read_delay)
        return ops.ReadJobAnswerResult(job_id=request.job_id, figures=answered)

    async def Subscribe(self, request, context):  # noqa: N802
        self.subscribed.append(request)
        return ops.SubscribeReply()

    async def Unsubscribe(self, request, context):  # noqa: N802
        self.unsubscribed.append(request.subscription_id)
        return ops.UnsubscribeReply()

    async def Receive(self, request, context):  # noqa: N802
        await context.send_initial_metadata(())
        while True:
            yield await self.pushed.get()

    def update(self, sequence: int, value: str, job_id: str = JOB) -> None:
        ids = [s.subscription_id for s in self.subscribed if job_id in s.job_ids]
        self.pushed.put_nowait(
            ops.Delivery(
                meta=ops.DeliveryMeta(row="DerivedSeriesUpdated", subscription_ids=ids[-1:]),
                derived_series_updated=ops.DerivedSeriesUpdatedEvent(
                    job_id=job_id, figures=[figure(value)], sequence=sequence
                ),
            )
        )


@pytest.fixture
async def engine() -> AsyncIterator[tuple[Engine, str]]:
    service, held = FakeSidecar(), Engine()
    service.instance_id = "signal-fx-1"
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(held, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield held, f"127.0.0.1:{port}"
    finally:
        await server.stop(grace=None)


def value_of(view: Any) -> Decimal:
    (only,) = [row for key, row in view.rows().items() if key.startswith("figure")]
    return meridian.as_decimal(only.value)


class _Acting:
    """A role object's acts over a connection, as `Jobs.standing` is given."""

    def __init__(self, plugin: meridian.Plugin) -> None:
        self.plugin = plugin

    async def run_job(self, *, job: Any) -> Any:
        from meridian.operations import _job

        return await self.plugin._operate(
            self.plugin._operations().RunJob, ops.RunJobParams(job=_job(job, "job"))
        )

    async def read_job_answer(self, *, job_id: str, cursor: str = "") -> Any:
        return await self.plugin._operate(
            self.plugin._operations().ReadJobAnswer,
            ops.ReadJobAnswerParams(job_id=job_id, cursor=cursor),
        )


def standing_job() -> Any:
    return analytics.job(
        analytics.measure("exposure", refresh="per_change"), accounts=[ACCOUNT], standing=True
    )


async def test_a_standing_job_is_a_view_of_its_figures_kept_in_its_sequence(engine) -> None:
    held, address = engine
    plugin = await meridian.connect(address, heartbeat=False, roles=[])
    try:
        view = await analytics.Jobs().standing(_Acting(plugin), standing_job())
        (ran,) = held.jobs
        assert ran.job.standing and ran.job.measures[0].refresh == ops.REFRESH_PER_CHANGE
        assert [list(s.job_ids) for s in held.subscribed] == [[JOB]]
        assert value_of(view) == 100  # the snapshot, read by its job ID
        held.update(1, "110")
        await until(lambda: value_of(view) == 110)
        held.update(1, "999")  # at or below the last applied: dropped
        held.update(2, "120")
        await until(lambda: value_of(view) == 120)
        # A gap in the job's sequence: the whole answer read again.
        reads = len(held.reads)
        held.answer[JOB] = [figure("140")]
        held.update(4, "130")
        await until(lambda: value_of(view) == 140)
        assert len(held.reads) == reads + 1
        # The gap's sequence is kept past the read: one held at or below it
        # is dropped, the next applied, and a second gap read again too.
        held.update(4, "999")
        await asyncio.sleep(0.2)
        assert value_of(view) == 140
        held.update(5, "150")
        await until(lambda: value_of(view) == 150)
        held.answer[JOB] = [figure("180")]
        held.update(7, "170")
        await until(lambda: value_of(view) == 180)
        assert len(held.reads) == reads + 2
        await view.close()
    finally:
        await plugin.leave()


async def test_a_gap_among_updates_held_while_it_reads_is_read_again(engine) -> None:
    """Updates arriving while the view reads are held, then applied above
    the read; one of them showing a gap reads the answer again."""
    held, address = engine
    held.read_delay = 0.5
    plugin = await meridian.connect(address, heartbeat=False, roles=[])
    try:
        opening = asyncio.create_task(
            analytics.Jobs().standing(_Acting(plugin), standing_job())
        )
        await until(lambda: bool(held.reads))  # the first read under way
        held.answer[JOB] = [figure("200")]  # what a read made now answers
        held.update(2, "120")  # held: the count's start
        held.update(4, "140")  # held, and a gap once applied
        view = await opening
        await until(lambda: value_of(view) == 200)
        assert len(held.reads) == 2
        await view.close()
    finally:
        await plugin.leave()


async def test_a_standing_job_not_held_is_registered_again_with_the_job(engine) -> None:
    held, address = engine
    plugin = await meridian.connect(address, heartbeat=False, roles=[])
    try:
        view = await analytics.Jobs().standing(_Acting(plugin), standing_job())
        held.update(1, "110")
        await until(lambda: value_of(view) == 110)
        held.held.discard(JOB)  # its coordinator lost: the job is not held
        held.update(3, "130")  # a gap: read again, answered not found
        await until(lambda: value_of(view) == 300)
        assert len(held.jobs) == 2 and held.jobs[1].job.standing
        assert [list(s.job_ids) for s in held.subscribed][-1] == [AGAIN]
        held.update(1, "310", job_id=AGAIN)
        await until(lambda: value_of(view) == 310)
        await view.close()
    finally:
        await plugin.leave()


def test_a_standing_job_names_no_fixed_input_and_each_measure_its_refresh() -> None:
    measure = analytics.measure("exposure", refresh="per_change")
    with pytest.raises(ValueError, match="standing names no lake_as_of_ns"):
        analytics.job(measure, accounts=[ACCOUNT], lake_as_of_ns=1, standing=True)
    with pytest.raises(ValueError, match="names no cadence_ns"):
        analytics.measure("historical_var", refresh="cadence")
    with pytest.raises(ValueError, match="only a refresh on a cadence"):
        analytics.measure("exposure", refresh="per_change", cadence_ns=1)
    fit = analytics.measure(
        "historical_var", refresh="cadence", cadence_ns=60 * 10**9, material_move_bp=25
    )
    built = analytics.job(fit, accounts=[ACCOUNT], standing=True)
    assert isinstance(built.measures[0], meridian.MeasureRef)
    assert (built.measures[0].cadence_ns, built.measures[0].material_move_bp) == (
        60 * 10**9,
        25,
    )
    with pytest.raises(ValueError, match="analytics.job"):
        asyncio.run(
            analytics.Jobs().standing(Recorder(), analytics.job(fit, accounts=[ACCOUNT]))
        )


# ── A stream held to its far end ───────────────────────────────────────────


def free_port() -> int:
    with socket.socket() as held:
        held.bind(("127.0.0.1", 0))
        return int(held.getsockname()[1])


class FarEnd:
    """tests/far_end.py in a process of its own, killed with SIGKILL."""

    def __init__(self, port: int) -> None:
        self.port = port
        self.process: subprocess.Popen[str] | None = None

    def start(self, first: int) -> None:
        self.process = subprocess.Popen(
            [sys.executable, str(HERE / "far_end.py"), str(self.port), str(first)],
            stdout=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        assert self.process.stdout is not None
        assert self.process.stdout.readline().strip() == "ready"

    def kill(self) -> None:
        assert self.process is not None
        self.process.send_signal(signal.SIGKILL)
        self.process.wait()

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.kill()


@pytest.fixture
def far_end() -> Any:
    held = FarEnd(free_port())
    held.start(100)
    try:
        yield held
    finally:
        held.stop()


def bid(row: Any) -> int:
    return int(row.bid_quantity.low)


async def test_a_view_catches_up_after_its_far_end_is_killed_just_after_it_opened(
    far_end: FarEnd,
) -> None:
    plugin = await meridian.connect(f"127.0.0.1:{far_end.port}", heartbeat=False, roles=[])
    try:
        view = await plugin.subscribe("QuotesRecorded", subjects=[EURUSD])
        far_end.kill()  # SIGKILL, just after the stream opened: no close sent
        far_end.start(1_000)  # back, its store moved on
        await until(lambda: any(bid(r) >= 1_000 for r in view.rows().values()), 20)
        first = max(bid(r) for r in view.rows().values())
        await until(lambda: max(bid(r) for r in view.rows().values()) > first)  # and ticking
        await view.close()
    finally:
        await plugin.leave()


async def hearing(plugin: meridian.Plugin, heard: list[int], reopen: asyncio.Event) -> Any:
    async def quotes(change: Heard[Any]) -> None:
        heard.append(bid(change.message.quote))

    return asyncio.create_task(
        follow(plugin, {"QuotesRecorded": quotes}, seed=False, subjects=[EURUSD], reopen=reopen)
    )


async def test_a_role_hears_again_after_its_far_end_is_killed_while_it_reopens(
    far_end: FarEnd,
) -> None:
    plugin = await meridian.connect(f"127.0.0.1:{far_end.port}", heartbeat=False, roles=[])
    heard: list[int] = []
    reopen = asyncio.Event()
    task = await hearing(plugin, heard, reopen)
    try:
        view = await plugin.subscribe("QuotesRecorded", subjects=[EURUSD])
        await until(lambda: bool(heard))
        reopen.set()  # its subjects changed: the stream opened again ...
        far_end.kill()  # ... and its far end killed while it reopens
        far_end.start(5_000)
        await until(lambda: heard[-1] >= 5_000, 20)
        await until(lambda: any(bid(r) >= 5_000 for r in view.rows().values()), 20)
        assert not task.done()
        await view.close()
    finally:
        task.cancel()
        await plugin.leave()


class Silent(operations_pb2_grpc.PluginOperationsServicer):
    """A far end that stays connected and goes silent: the stream open, and
    nothing delivered on it once `mute` -- its upstream subscription gone
    with a lake killed behind it -- while the store moves on. A stream
    opened again is heard again."""

    def __init__(self) -> None:
        self.head = 10
        self.mute = False
        self.muted_at = 0
        self.opened = 0
        self.subscriptions: set[str] = set()

    async def Receive(self, request, context):  # noqa: N802
        await context.send_initial_metadata(())
        self.opened += 1
        mine = self.opened
        sent = 0
        while True:
            await asyncio.sleep(0.01)
            if self.mute and mine <= self.muted_at:
                continue
            if self.head != sent:
                sent = self.head
                yield ops.Delivery(
                    meta=ops.DeliveryMeta(
                        row="QuotesRecorded", subscription_ids=sorted(self.subscriptions)
                    ),
                    quotes_recorded=ops.QuotesRecordedEvent(quote=_quote(sent)),
                )

    def silence(self) -> None:
        self.mute, self.muted_at = True, self.opened

    async def Subscribe(self, request, context):  # noqa: N802
        self.subscriptions.add(request.subscription_id)
        return ops.SubscribeReply()

    async def Unsubscribe(self, request, context):  # noqa: N802
        self.subscriptions.discard(request.subscription_id)
        return ops.UnsubscribeReply()

    async def ListQuotes(self, request, context):  # noqa: N802
        return ops.ListQuotesResult(
            quotes=[_quote(self.head)],
            watermark=ops.Watermark(
                partitions=[
                    ops.PartitionSequence(partition="oanda-1:quotes", sequence=self.head)
                ]
            ),
        )

    async def ListDatasets(self, request, context):  # noqa: N802
        return ops.ListDatasetsResult()


def _quote(sequence: int) -> ops.Quote:
    sys.path.insert(0, str(HERE))
    from far_end import quote

    return quote(sequence)


async def test_a_stream_silent_past_its_quiet_window_is_opened_again_and_caught_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import meridian.receive

    monkeypatch.setattr(meridian.receive, "QUIET_SECONDS", 0.5)
    service, far = FakeSidecar(), Silent()
    service.instance_id = "signal-fx-1"
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(far, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    plugin = await meridian.connect(f"127.0.0.1:{port}", heartbeat=False, roles=[])
    heard: list[int] = []
    task = await hearing(plugin, heard, asyncio.Event())
    try:
        view = await plugin.subscribe("QuotesRecorded", subjects=[EURUSD])
        far.head = 11
        await until(lambda: 11 in heard)
        far.silence()  # connected, and silent: nothing broke the stream
        far.head = 50
        await until(lambda: 50 in heard)  # opened again past the quiet window
        await until(lambda: any(bid(r) == 50 for r in view.rows().values()))
        assert far.opened >= 2
        await view.close()
    finally:
        task.cancel()
        await plugin.leave()
        await server.stop(grace=None)


# ── The declaration, the sessions and an event contract's terms ────────────


def test_a_version_declares_its_most_shards_and_a_dataset_its_sessions_and_gaps() -> None:
    fx = meridian.DatasetDeclaration(
        key="live",
        vendor="TrueFX",
        data_types=["meridian.v1.Quote"],
        modes=["stream"],
        sessions_calendar_id="CAL-FXWEEK",
        gap_recovery="GAP_RECOVERY_STREAM_ONLY",
        terms_and_pricing="Free with a registered account; not for redistribution.",
    )
    wire = fx._wire()
    assert wire.sessions_calendar_id == "CAL-FXWEEK"
    assert wire.gap_recovery == sidecar_pb2.GAP_RECOVERY_STREAM_ONLY
    said = fx._to_json()
    assert (said["gap_recovery"], said["sessions_calendar_id"]) == ("stream_only", "CAL-FXWEEK")
    declared = meridian.Declaration(catalogue=[fx], most_shards=4)
    assert declared.to_wire().most_shards == 4 and declared.to_json()["most_shards"] == 4
    assert "most_shards" not in meridian.Declaration().to_json()
    with pytest.raises(ValueError, match="most_shards"):
        meridian.Declaration(most_shards=65)


async def test_a_datasets_trading_sessions_are_read_from_its_calendar() -> None:
    recorder = Recorder("signal-fx-1")
    week = ops.TradingSessions(time_zone="America/New_York", sessions=sessions.FX_WEEK.sessions)
    recorder.answer(
        "ListDatasets",
        lambda _: ops.ListDatasetsResult(
            datasets=[
                ops.DatasetRef(
                    dataset="truefx-1:live",
                    declaration=ops.DatasetDeclaration(sessions_calendar_id="CAL-FXWEEK"),
                ),
                ops.DatasetRef(dataset="coinbase-1:live"),
            ]
        ),
    )
    recorder.answer(
        "ReadCalendar",
        lambda asked: ops.ReadCalendarResult(
            found=asked.calendar_id == "CAL-FXWEEK",
            calendar_id=asked.calendar_id,
            trading_sessions=week,
        ),
    )
    assert await sessions.read_sessions(recorder, "truefx-1:live") == week
    assert await sessions.read_sessions(recorder, "coinbase-1:live") is None  # names none
    assert await sessions.read_sessions(recorder, "elsewhere-1:live") is None  # not listed
    read = [sent.params for sent in recorder.sent if sent.row == "ReadCalendar"]
    assert [each.calendar_id for each in read] == ["CAL-FXWEEK"]


def test_an_event_contracts_terms_and_category_are_stated_at_its_resolve() -> None:
    from fake_venues import NOW_NS, BarsMarket
    from meridian.roles.data import event_contracts

    feed = event_contracts.Feed(
        BarsMarket(), event_contracts.ContractMap(), clock_ns=lambda: NOW_NS
    )
    contract = event_contracts.Contract(
        code="KXCPI-26NOV-T3.0",
        title="CPI above 3.0%",
        binary=True,
        payout=Decimal("1"),
        closes_at_ns=NOW_NS,
        floor=event_contracts.Bound(Decimal("3.0"), inclusive=False),
        bound_unit="percent",
        category="economics",
    )
    terms = feed.stated_terms(contract)
    assert terms is not None
    assert (terms.category, terms.bound_unit, terms.closes_at_ns) == (
        "economics", "percent", NOW_NS,
    )  # fmt: skip
    assert terms.payout == meridian.Money(Decimal("1"), feed.market.cash.currency_code)
    assert (
        feed.stated_terms(
            event_contracts.Contract(code="x", title="x", binary=True, payout=None)
        )
        is None
    )


# ── Refused for load, and told when to ask again (W4.4; section 10a) ───────


def refusal(reason: int, after: int = 0) -> sidecar_pb2.Refusal:
    return sidecar_pb2.Refusal(reason=reason, retry_after_seconds=after)


def test_a_refusal_for_load_is_waited_out_at_least_what_core_said() -> None:
    import random

    from meridian.client import load_wait

    rng = random.Random(7)
    exhausted = grpc.StatusCode.RESOURCE_EXHAUSTED
    overloaded = refusal(sidecar_pb2.REFUSAL_REASON_OVERLOADED, 2)
    waited = load_wait(overloaded, exhausted, 60, rng=rng)
    assert waited is not None and 2 <= waited <= 2.4
    limited = refusal(sidecar_pb2.REFUSAL_REASON_RATE_LIMITED, 5)
    waited = load_wait(limited, exhausted, 60, rng=rng)
    assert waited is not None and 5 <= waited <= 6
    # None named: at least a second.
    waited = load_wait(refusal(sidecar_pb2.REFUSAL_REASON_OVERLOADED), exhausted, 60, rng=rng)
    assert waited is not None and 1 <= waited <= 1.2
    # A bare RESOURCE_EXHAUSTED is a count cap that waiting does not clear.
    assert load_wait(refusal(0), exhausted, 60) is None
    # The reason beside another status, or a wait past the deadline: raised.
    assert load_wait(overloaded, grpc.StatusCode.UNAVAILABLE, 60) is None
    assert load_wait(overloaded, exhausted, 1.5) is None


class Loaded(operations_pb2_grpc.PluginOperationsServicer):
    """A sidecar refusing reads for load as it is told to, then answering."""

    def __init__(self, refusals: list[sidecar_pb2.Refusal]) -> None:
        self.refusals = refusals
        self.asked: list[float] = []

    async def ListDatasets(self, request, context):  # noqa: N802
        self.asked.append(time.monotonic())
        if self.refusals:
            said = self.refusals.pop(0)
            await context.abort(
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                "refused for load",
                trailing_metadata=(("meridian-refusal-bin", said.SerializeToString()),),
            )
        return ops.ListDatasetsResult(datasets=[ops.DatasetRef(dataset="oanda-1:quotes")])


@pytest.fixture
async def loaded() -> AsyncIterator[tuple[Loaded, meridian.Plugin]]:
    service, held = FakeSidecar(), Loaded([])
    service.instance_id = "signal-fx-1"
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(held, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    plugin = await meridian.connect(f"127.0.0.1:{port}", heartbeat=False, roles=[])
    try:
        yield held, plugin
    finally:
        await plugin.leave()
        await server.stop(grace=None)


async def list_datasets(plugin: meridian.Plugin) -> Any:
    return await plugin._operate(plugin._operations().ListDatasets, ops.ListDatasetsParams())


async def test_a_read_refused_for_load_is_asked_again_after_its_retry_after(loaded) -> None:
    held, plugin = loaded
    held.refusals = [refusal(sidecar_pb2.REFUSAL_REASON_RATE_LIMITED, 1)]
    answer = await list_datasets(plugin)
    assert [d.dataset for d in answer.datasets] == ["oanda-1:quotes"]
    assert len(held.asked) == 2 and held.asked[1] - held.asked[0] >= 1.0


async def test_a_count_cap_or_a_wait_past_the_deadline_is_raised_at_once(loaded) -> None:
    from meridian.client import READ_DEADLINE

    held, plugin = loaded
    held.refusals = [refusal(0)]  # a bare RESOURCE_EXHAUSTED: a count cap
    with pytest.raises(meridian.CallFailed):
        await list_datasets(plugin)
    assert len(held.asked) == 1
    held.refusals = [refusal(sidecar_pb2.REFUSAL_REASON_OVERLOADED, 5)]
    token = READ_DEADLINE.set(2.0)  # a read given 2 s cannot wait 5
    try:
        with pytest.raises(meridian.CallFailed):
            await list_datasets(plugin)
    finally:
        READ_DEADLINE.reset(token)
    assert len(held.asked) == 2
