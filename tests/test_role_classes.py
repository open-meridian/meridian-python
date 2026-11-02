"""Each role is one generated class (SDK 0.35; spec/each-role-is-one-generated-
class, rulings 1004, 1005 and 1009 to 1023), against the stand-in sidecar.

A role's base holds exactly its acts and events; a class missing a required
event is refused when it is made, naming it; the classes registered on one
connection hear one stream, the union of what each hears, each delivery
handed to every class hearing its row; an optional event no class overrides
is never asked of the sidecar; a class for a role the instance was not
launched with is not started; `run()` is restarted after its backoff; and
`hear_again()` opens the stream again with the subjects as they stand.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pytest

import meridian
import meridian._run as running
from conftest import FakeSidecar, Stream
from meridian import Heard
from meridian.helpers.sessions import Backoff
from meridian.operations import Operations
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import (
    compliance,
    confirmation,
    connectivity,
    custody,
    data,
    ems,
    oms,
    operations,
    portfolio,
    pricing,
    reference,
    reporting,
    servicing,
    settlement,
    signal,
)
from meridian.roles._generated import ROLES
from meridian.suites import Recorder
from test_receive import Store, changed, position

ALL = (
    compliance,
    confirmation,
    connectivity,
    custody,
    data,
    ems,
    oms,
    operations,
    portfolio,
    pricing,
    reference,
    reporting,
    servicing,
    settlement,
    signal,
)


# ── The bases ─────────────────────────────────────────────────────────────


def test_every_role_is_one_module_holding_its_generated_base() -> None:
    assert tuple(module.Role.role for module in ALL) == ROLES
    assert len(ROLES) == 15
    for module in ALL:
        assert module.Role.__module__ == f"meridian.roles._generated.{module.Role.role}"


def test_a_base_holds_exactly_its_roles_acts_bound_from_the_one_implementation() -> None:
    every = {name for name in vars(Operations) if not name.startswith("_")}
    for module in ALL:
        acts = set(module.Role.ACTS)
        assert acts <= every
        for act in acts:
            assert getattr(module.Role, act) is getattr(Operations, act)
        for other in every - acts:
            assert not hasattr(module.Role, other), (module.Role.role, other)
    # An act two roles hold is one call from either (requirement 11).
    assert data.Role.resolve_identifier is custody.Role.resolve_identifier


def test_the_required_events_are_the_suites_and_abstract() -> None:
    assert {"ObservationsWanted"} == data.Role.REQUIRED
    assert {"PlacementUpdated", "TradingInstructionChanged"} == connectivity.Role.REQUIRED
    assert {"PriceBatch"} == pricing.Role.REQUIRED
    assert frozenset() == reporting.Role.REQUIRED
    for module in ALL:
        abstract = getattr(module.Role, "__abstractmethods__", frozenset())
        assert abstract == {module.Role.EVENTS[row] for row in module.Role.REQUIRED}


def test_an_event_method_is_on_and_the_rows_name() -> None:
    assert data.Role.EVENTS["WantWithdrawn"] == "on_want_withdrawn"
    assert operations.Role.EVENTS["ActivityReResolved"] == "on_activity_re_resolved"
    assert ems.Role.EVENTS["ReportVenueCatalogue"] == "on_report_venue_catalogue"


def test_a_class_missing_a_required_event_is_refused_naming_the_role_and_event() -> None:
    class Lake(data.Role):
        pass

    with pytest.raises(TypeError, match="data role.*on_observations_wanted"):
        Lake()

    class Desk(connectivity.Role):
        async def on_placement_updated(self, heard: Any) -> None:
            return None

    with pytest.raises(TypeError, match="on_trading_instruction_changed"):
        Desk()


def test_a_class_hears_its_required_events_and_the_optional_ones_it_overrides() -> None:
    class Lake(data.Role):
        async def on_observations_wanted(self, heard: Any) -> None:
            return None

    class Withdrawing(Lake):
        async def on_want_withdrawn(self, heard: Any) -> None:
            return None

    assert Lake.heard_rows() == ("ObservationsWanted",)
    assert Withdrawing.heard_rows() == ("ObservationsWanted", "WantWithdrawn")
    assert reporting.Role.heard_rows() == ()


def test_a_role_class_makes_no_act_until_registered() -> None:
    with pytest.raises(meridian.NotRegistered, match="not registered"):
        _ = reporting.Role().plugin


def test_the_connection_holds_no_act_and_no_receive() -> None:
    assert not hasattr(meridian.Plugin, "record_prices")
    assert not hasattr(meridian.Plugin, "receive")
    assert not issubclass(meridian.Plugin, Operations)


# ── The suites' recorder ──────────────────────────────────────────────────


def test_the_recorder_binds_a_class_and_hands_it_what_it_hears() -> None:
    class Lake(data.Role):
        def __init__(self) -> None:
            self.wanted: list[str] = []

        async def on_observations_wanted(self, heard: Heard[Any]) -> None:
            self.wanted.append(heard.message.want_id)
            await self.decline_want(want_id=heard.message.want_id)

    recorder = Recorder("lake-1")
    lake = recorder.bind(Lake())
    recorder.answer(
        "ObservationsWanted", lambda _: [ops.ObservationsWantedEvent(want_id="WNT-1")]
    )
    asyncio.run(recorder.hear(lake))
    assert lake.wanted == ["WNT-1"]
    assert lake.plugin is recorder.plugin and lake.plugin.identity.instance_id == "lake-1"
    assert [sent.row for sent in recorder.sent] == ["ObservationsWanted", "DeclineWant"]


# ── One connection ────────────────────────────────────────────────────────


async def test_two_classes_for_one_role_are_refused_before_anything_is_sent(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    with pytest.raises(ValueError, match="two classes are registered for the reporting role"):
        await meridian.connect(
            address, heartbeat=False, roles=[reporting.Role(), reporting.Role()]
        )
    with pytest.raises(TypeError, match="no role class"):
        await meridian.connect(address, heartbeat=False, roles=[object()])  # type: ignore[list-item]
    with pytest.raises(TypeError, match="required"):
        await meridian.connect(address, heartbeat=False)  # type: ignore[call-arg]


async def test_a_class_for_a_role_not_held_is_not_registered_and_is_logged(
    sidecar: tuple[FakeSidecar, str], caplog: pytest.LogCaptureFixture
) -> None:
    service, address = sidecar
    service.roles = ("custody",)
    held, stranger = custody.Role(), reporting.Role()
    with caplog.at_level(logging.WARNING, "meridian.run"):
        plugin = await meridian.connect(address, heartbeat=False, roles=[held, stranger])
    try:
        assert plugin._roles == (held,)
        assert held.plugin is plugin
        with pytest.raises(meridian.NotRegistered):
            _ = stranger.plugin
        assert "Role is not started" in caplog.text and "reporting role" in caplog.text
    finally:
        await plugin.leave()


class _Book(operations.Role):
    """An operations class hearing custodial positions (optional) beside
    the activity its role requires."""

    def __init__(self, seed: bool = True) -> None:
        self.seed = seed
        self.positions: list[Heard[Any]] = []
        self.started = 0
        self.stopped = 0

    async def on_activity_recorded(self, heard: Heard[Any]) -> None:
        return None

    async def on_custodial_position_updated(self, heard: Heard[Any]) -> None:
        self.positions.append(heard)

    async def on_start(self) -> None:
        self.started += 1

    async def on_stop(self) -> None:
        self.stopped += 1


class _Watcher(custody.Role):
    """A second class on the same connection (a custody class): it hears
    nothing of the operations role's, so it is handed nothing."""

    def __init__(self) -> None:
        self.ran = asyncio.Event()

    async def run(self) -> None:
        self.ran.set()


async def _running(address: str, roles: list[Any], until: Any) -> None:
    """The plugin run with `roles` until `until()` is true, then stopped."""
    declaration = meridian.Declaration()
    task = asyncio.create_task(meridian.run_async(declaration, roles))
    try:
        for _ in range(200):
            if until():
                break
            await asyncio.sleep(0.025)
        await asyncio.sleep(0.05)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_the_lifecycle_runs_on_start_the_stream_run_and_on_stop(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    service.roles = ("operations", "custody")
    store = Store()
    store.put(position("ACC-1", "INS-A", 30))
    service.operations.store = store
    service.operations.streams = [Stream([changed(position("ACC-1", "INS-A", 31, 30))])]
    book, watcher = _Book(), _Watcher()
    await _running(address, [book, watcher], lambda: len(book.positions) >= 2)

    assert book.started == 1 and book.stopped == 1 and watcher.ran.is_set()
    assert [h.caught_up for h in book.positions] == [True, False]
    # One stream, for the rows the classes hear: the required event and the
    # optional one the class overrides; none of the role's other events.
    (asked,) = service.operations.received[:1]
    assert sorted(asked.rows) == ["ActivityRecorded", "CustodialPositionUpdated"]


@pytest.mark.parametrize("seeded", [True, False])
async def test_two_classes_hearing_one_row_each_hear_every_delivery(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch, seeded: bool
) -> None:
    service, address = sidecar
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    service.roles = ("custody", "reporting")
    first = ops.InstrumentReplacedEvent(
        replaced_instrument_id="LCL-1",
        instrument=ops.InstrumentRecord(instrument_id="INS-1"),
        cause=ops.REPLACEMENT_CAUSE_RESOLVED,
        sequence=1,
    )
    second = ops.InstrumentReplacedEvent(
        replaced_instrument_id="LCL-2",
        instrument=ops.InstrumentRecord(instrument_id="INS-2"),
        cause=ops.REPLACEMENT_CAUSE_RESOLVED,
        sequence=2,
    )
    service.operations.replacements = [first]
    service.operations.streams = [Stream([ops.Delivery(replace_merged_instrument=second)])]

    class Custody(custody.Role):
        def __init__(self) -> None:
            self.ids: list[tuple[str, bool]] = []

        async def on_replace_merged_instrument(self, heard: Heard[Any]) -> None:
            self.ids.append((heard.message.replaced_instrument_id, heard.caught_up))

    class Reporting(reporting.Role):
        def __init__(self, seed: bool = True) -> None:
            self.seed = seed
            self.ids: list[tuple[str, bool]] = []

        async def on_replace_merged_instrument(self, heard: Heard[Any]) -> None:
            self.ids.append((heard.message.replaced_instrument_id, heard.caught_up))

    held, shown = Custody(), Reporting(seed=seeded)
    wanted = 2 if seeded else 1
    await _running(
        address, [held, shown], lambda: len(shown.ids) >= wanted and len(held.ids) >= 2
    )
    assert held.ids == [("LCL-1", True), ("LCL-2", False)]
    # A class whose `seed` is False is not handed the start's read, though
    # another class hearing the row is (ruling 1013).
    assert shown.ids == ([("LCL-1", True)] if seeded else []) + [("LCL-2", False)]
    # One stream for both classes, naming the row once.
    assert list(service.operations.received[0].rows) == ["ReplaceMergedInstrument"]


async def test_a_failing_run_is_restarted_after_its_backoff_and_said_on_health(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    service.roles = ("custody",)
    monkeypatch.setattr(running, "Backoff", lambda: Backoff(0.01, 0.05, 0.0, 60.0))

    class Flaky(custody.Role):
        def __init__(self) -> None:
            self.tries = 0

        async def run(self) -> None:
            self.tries += 1
            if self.tries < 3:
                raise RuntimeError(f"lost the venue ({self.tries})")
            await asyncio.Event().wait()

    flaky = Flaky()
    await _running(address, [flaky], lambda: flaky.tries >= 3)
    assert flaky.tries == 3
    said = [(beat.healthy, beat.detail) for beat in service.heartbeats]
    assert (False, "Flaky (custody) failed (RuntimeError: lost the venue (2))") in said


async def test_hear_again_reopens_the_stream_with_the_subjects_as_they_stand(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    service.roles = ("signal",)

    class Watching(signal.Role):
        def __init__(self) -> None:
            self.held = ["INS-A"]

        def subjects(self) -> list[str]:
            return self.held

        async def on_prices_recorded(self, heard: Heard[Any]) -> None:
            return None

    watching = Watching()
    service.operations.streams = [Stream()]

    async def widen() -> None:
        for _ in range(200):
            if service.operations.received:
                break
            await asyncio.sleep(0.025)
        watching.held = ["INS-A", "INS-B"]
        watching.hear_again()

    widening = asyncio.create_task(widen())
    await _running(address, [watching], lambda: len(service.operations.received) >= 2)
    await widening
    first, second = service.operations.received[:2]
    assert list(first.subjects) == ["INS-A"]
    assert list(second.subjects) == ["INS-A", "INS-B"]
    assert list(first.rows) == list(second.rows) == ["PricesRecorded"]


# ── The backoff ───────────────────────────────────────────────────────────


def test_the_backoff_doubles_within_its_jitter_to_its_most_and_resets_when_steady() -> None:
    now = [0.0]
    backoff = Backoff(1, 4, 0.2, 60, clock=lambda: now[0])
    waits = [backoff.failed() for _ in range(4)]
    for wait, base in zip(waits, (1, 2, 4, 4), strict=True):
        assert base * 0.8 <= wait <= base * 1.2
    now[0] = 61
    backoff.steady()
    assert 0.8 <= backoff.failed() <= 1.2
    with pytest.raises(ValueError, match="jitter"):
        Backoff(1, 2, 1.5, 60)
