"""Contract v22 through the SDK: the order path's slice A and the
settlement calendars.

What this client decides, and so what is worth asserting: that a caller's
algorithm and the connectivity plugins it may route through read from the
claims; that a version's algorithms are declared and a service account's
call names one it declares, refused here first otherwise; that the order
path's refusals keep their status, code, fields and words; that a calendar
read and a date asked for reach the sidecar as typed; that the transition
table the SDK carries reads whole; and that a case naming one value twice is
matched as such. What the book, the sidecar and the dashboard do with any of
it is meridian-core's to test, and its e2e-orders suite's.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import (
    AlgorithmDeclaration,
    Caller,
    CallFailed,
    CommandRefused,
    Declaration,
    NotGranted,
    SubjectKind,
)
from meridian import _transitions as transitions
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.suites import Recorder, check, suite
from meridian.testing import caller_header
from meridian.v1 import sidecar_pb2

SERVICE_ACCOUNT = SubjectKind.SUBJECT_KIND_SERVICE_ACCOUNT
TWAP = AlgorithmDeclaration("twap-v1", "Time-weighted slices over the order's window.")
WHY = "TWAP slice 3 of 12 for ORD-1."


# ── The caller's algorithm and the connectivity plugins it may route through ──


def test_a_callers_algorithm_and_connectivity_plugins_read_from_the_claims() -> None:
    person = Caller.from_header(caller_header("write", read={"ACC-1"}, write={"ACC-1"}))
    assert person.algorithm_id == ""
    assert person.connectivity_instance_ids == frozenset()

    desk = Caller.from_header(
        caller_header(
            "write",
            read={"ACC-1"},
            write={"ACC-1"},
            connectivity_instance_ids=["snaptrade-1", "sim-venue-1"],
        )
    )
    assert desk.connectivity_instance_ids == {"snaptrade-1", "sim-venue-1"}

    account = Caller.from_header(
        caller_header(
            "write",
            read={"ACC-1"},
            write={"ACC-1"},
            subject="SA-01JAD3R5N8M0000000000000A",
            subject_kind=SERVICE_ACCOUNT,
            owner_subject="local|ada",
            algorithm_id="twap-v1",
        )
    )
    assert account.algorithm_id == "twap-v1"


# ── A version's algorithms, and the one a service account's call names ────────


def test_a_declarations_algorithms_go_on_the_wire_and_in_the_upload() -> None:
    declared = Declaration(algorithms=[TWAP])
    wire = declared.to_wire()
    assert [(held.algorithm_id, held.description) for held in wire.algorithms] == [
        ("twap-v1", "Time-weighted slices over the order's window.")
    ]
    assert declared.to_json()["algorithms"] == [
        {
            "algorithm_id": "twap-v1",
            "description": "Time-weighted slices over the order's window.",
        }
    ]
    # A version declaring none uploads what it did before v22.
    assert "algorithms" not in Declaration().to_json()
    assert list(Declaration().to_wire().algorithms) == []


def test_an_algorithm_is_declared_once_named_and_described() -> None:
    with pytest.raises(ValueError, match="declared twice"):
        Declaration(algorithms=[TWAP, AlgorithmDeclaration("twap-v1", "Again.")])
    with pytest.raises(ValueError, match="algorithm_id is empty"):
        AlgorithmDeclaration("", "No name.")
    with pytest.raises(ValueError, match="spaces around it"):
        AlgorithmDeclaration(" twap-v1", "Padded.")
    with pytest.raises(ValueError, match="description is 1 to 1024"):
        AlgorithmDeclaration("twap-v1", "")
    with pytest.raises(ValueError, match="description is 1 to 1024"):
        AlgorithmDeclaration("twap-v1", "x" * 1025)


@pytest.fixture
async def ems_plugin(sidecar: tuple[FakeSidecar, str]):
    service, address = sidecar
    service.roles = ("ems",)
    service.instance_id = "ems-desk-1"
    plugin = await meridian.connect(
        address, heartbeat=False, declaration=Declaration(algorithms=[TWAP])
    )
    try:
        yield service, plugin
    finally:
        await plugin.leave()


async def test_the_work_names_a_declared_algorithm_on_every_call(
    ems_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, plugin = ems_plugin
    (registered,) = service.registered
    assert [held.algorithm_id for held in registered.declaration.algorithms] == ["twap-v1"]
    async with meridian.runs_as("ems", algorithm_id="twap-v1") as act:
        await act("work_order", {"order_id": "ORD-1"}, reason=WHY)
        await act("work_order", {"order_id": "ORD-2"}, reason=WHY)
    async with meridian.runs_as("ems") as act:
        await act("work_order", {"order_id": "ORD-3"}, reason=WHY)
    named = [sent.algorithm_id for sent, _ in service.service_account_calls]
    assert named == ["twap-v1", "twap-v1", ""], "empty names none, as before v22"
    assert all(carried == "" for _, carried in service.service_account_calls)


async def test_an_algorithm_the_version_does_not_declare_is_refused_before_sending(
    ems_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, plugin = ems_plugin
    with pytest.raises(ValueError, match="algorithm_id is 'vwap-v1', which this version"):
        async with meridian.runs_as("ems", algorithm_id="vwap-v1") as act:
            await act("work_order", {"order_id": "ORD-1"}, reason=WHY)
    with pytest.raises(TypeError, match="algorithm_id is a int"):
        meridian.runs_as("ems", algorithm_id=7)  # type: ignore[arg-type]
    assert service.service_account_calls == []


async def test_the_sidecars_refusal_of_an_algorithm_names_it(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """A plugin whose declaration the sidecar holds differently -- an older
    image, say -- meets the sidecar's refusal, naming the field."""
    service, address = sidecar
    service.roles = ("ems",)
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        plugin._algorithms = ("twap-v1",)  # what this process thinks it declared
        with pytest.raises(CallFailed) as caught:
            async with meridian.runs_as("ems", algorithm_id="twap-v1") as act:
                await act("work_order", {"order_id": "ORD-1"}, reason=WHY)
    finally:
        await plugin.leave()
    assert (caught.value.kind, caught.value.fields) == ("invalid", ("algorithm_id",))


# ── The order path's refusals ─────────────────────────────────────────────────


@pytest.fixture
async def portfolio_plugin(sidecar: tuple[FakeSidecar, str]):
    service, address = sidecar
    service.roles = ("portfolio",)
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        yield service, plugin
    finally:
        await plugin.leave()


def refuse(
    service: FakeSidecar,
    status: grpc.StatusCode,
    words: str,
    reason: int = sidecar_pb2.REFUSAL_REASON_UNSPECIFIED,
    fields: tuple[str, ...] = (),
) -> None:
    service.operations.refuse = (status, words)
    service.operations.refuse_metadata = (
        (
            "meridian-refusal-bin",
            sidecar_pb2.Refusal(reason=reason, fields=list(fields)).SerializeToString(),
        ),
    )


async def test_an_invalid_order_is_read_by_its_fields_and_its_words(
    portfolio_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    """An order stating both a unit and a cash quantity is refused invalid,
    no code, naming both (W11.1): the fields to act on, the words to log."""
    service, plugin = portfolio_plugin
    refuse(
        service,
        grpc.StatusCode.INVALID_ARGUMENT,
        "quantity, cash_quantity: an order states exactly one",
        fields=("quantity", "cash_quantity"),
    )
    with pytest.raises(CallFailed) as caught:
        await plugin.propose_order(
            account_id="ACC-1",
            instrument_id="INS-AAPL",
            side="buy",
            quantity=Decimal("10"),
            cash_quantity=meridian.Money(Decimal("2275.00"), "USD"),
            idempotency_key="propose:ACC-1:1",
        )
    assert not isinstance(caught.value, CommandRefused)
    assert caught.value.kind == "invalid"
    assert caught.value.fields == ("quantity", "cash_quantity")
    assert caught.value.detail == "quantity, cash_quantity: an order states exactly one"


async def test_a_command_outside_the_write_scope_is_not_granted_with_its_words(
    portfolio_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    """A command naming an order by its ID alone, its account outside the
    instance's write scope: permission denied, no code, nothing changed."""
    service, plugin = portfolio_plugin
    service.operations.refuse = (
        grpc.StatusCode.PERMISSION_DENIED,
        "the order's account is outside this instance's write scope",
    )
    with pytest.raises(NotGranted) as caught:
        await plugin.release_order(order_id="ORD-9")
    assert caught.value.topic == "ReleaseOrder"
    assert caught.value.reason == "the order's account is outside this instance's write scope"
    assert caught.value.fields == ()


@pytest.mark.parametrize(
    "reason",
    [
        sidecar_pb2.REFUSAL_REASON_ALLOCATION_UNBALANCED,
        sidecar_pb2.REFUSAL_REASON_APPROVAL_REQUIRED,
        sidecar_pb2.REFUSAL_REASON_CHECK_BLOCKS,
        sidecar_pb2.REFUSAL_REASON_CLAIMED,
        sidecar_pb2.REFUSAL_REASON_ORDER_STATE,
        sidecar_pb2.REFUSAL_REASON_IDENTIFIER_IN_USE,
        sidecar_pb2.REFUSAL_REASON_CONNECTIVITY_NOT_ALLOWED,
        sidecar_pb2.REFUSAL_REASON_CONNECTIVITY_LINKED,
    ],
)
async def test_the_order_paths_refusals_are_raised_by_their_codes(
    portfolio_plugin: tuple[FakeSidecar, meridian.Plugin], reason: int
) -> None:
    service, plugin = portfolio_plugin
    refuse(service, grpc.StatusCode.ABORTED, "worded any way at all", reason)
    with pytest.raises(CommandRefused) as caught:
        await plugin.create_placement(
            order_id="ORD-1", connectivity_instance_id="sim-1", quantity=Decimal("10")
        )
    assert caught.value.reason == reason
    assert caught.value.reason_name == sidecar_pb2.RefusalReason.Name(reason)
    assert caught.value.kind == "refused"
    assert not caught.value.retryable


async def test_a_mapping_naming_an_account_not_granted_is_refused_by_its_code(
    portfolio_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, plugin = portfolio_plugin
    refuse(
        service,
        grpc.StatusCode.FAILED_PRECONDITION,
        "ACC-9 is not granted to this instance",
        sidecar_pb2.REFUSAL_REASON_ACCOUNT_NOT_LINKABLE,
    )
    with pytest.raises(CommandRefused) as caught:
        await plugin.create_placement(order_id="ORD-1", quantity=Decimal("10"))
    assert caught.value.reason_name == "REFUSAL_REASON_ACCOUNT_NOT_LINKABLE"


# ── The calendars ─────────────────────────────────────────────────────────────


async def test_a_calendar_read_and_a_date_asked_for_reach_the_sidecar_typed(
    portfolio_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, plugin = portfolio_plugin
    await plugin.read_calendar(
        calendar_id="CAL-01JAE0000000000000000USSS",
        from_date=date(2026, 10, 1),
        to_date="2026-10-31",
    )
    await plugin.compute_date(
        settlement=meridian.SettlementDateInputs(
            instrument_id="INS-AAPL", trade_date="2026-10-09"
        )
    )
    await plugin.compute_date(
        tenor=meridian.TenorDateInputs(
            pair=["INS-EUR", "INS-USD"],
            tenor=meridian.Tenor(count=1, unit="month"),
            trade_date=date(2026, 10, 9),
        )
    )
    await plugin.compute_date(
        roll=meridian.RollInputs(
            date=date(2026, 10, 10), convention="modified_following", calendars=["CAL-1"]
        )
    )
    read, settled, tenor, rolled = service.operations.sent
    assert (read.calendar_id, read.from_date, read.to_date) == (
        "CAL-01JAE0000000000000000USSS",
        "2026-10-01",
        "2026-10-31",
    )
    assert settled.WhichOneof("inputs") == "settlement"
    assert settled.settlement.trade_date == "2026-10-09"
    assert tenor.tenor.tenor.unit == ops.TENOR_UNIT_MONTH
    assert tenor.tenor.trade_date == "2026-10-09"
    assert rolled.roll.convention == ops.BUSINESS_DAY_CONVENTION_MODIFIED_FOLLOWING
    assert rolled.roll.date == "2026-10-10"


async def test_a_date_is_asked_for_one_way_at_a_time(
    portfolio_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, plugin = portfolio_plugin
    with pytest.raises(ValueError, match="inputs takes one of"):
        await plugin.compute_date(
            settlement=meridian.SettlementDateInputs(instrument_id="INS-AAPL"),
            business_day=meridian.BusinessDayInputs(date="2026-10-09"),
        )
    with pytest.raises(TypeError, match="a date, not a moment"):
        from datetime import datetime

        await plugin.read_calendar(calendar_id="CAL-1", from_date=datetime(2026, 10, 1))
    assert service.operations.sent == []


# ── The order's transitions, as data ─────────────────────────────────────────


def test_the_transition_table_reads_whole_and_names_only_the_contracts_words() -> None:
    rows = transitions.table()
    assert len(rows) == len({row.row for row in rows}) > 30
    held = set(transitions.states())
    assert held == set(ops.OrderState.keys()) - {"ORDER_STATE_UNSPECIFIED"}
    reasons = set(sidecar_pb2.RefusalReason.keys())
    for row in rows:
        assert set(row.from_states) <= held | {transitions.NONE, transitions.ANY}, row.row
        assert set(row.to_states) <= held | {transitions.UNCHANGED}, row.row
        assert set(row.refusal) <= reasons, row.row
    # Contract v23: an execution's rows, read apart, in ExecutionState's words.
    executions = transitions.execution_table()
    assert [row.row for row in executions] == [f"e{n}" for n in range(1, 9)]
    states = set(transitions.execution_states())
    assert states == set(ops.ExecutionState.keys()) - {"EXECUTION_STATE_UNSPECIFIED"}
    for row in executions:
        assert set(row.from_states) <= states | {transitions.NONE}, row.row
        assert set(row.to_states) <= states | {transitions.UNCHANGED}, row.row
        assert set(row.refusal) <= reasons, row.row


def test_what_a_role_may_cause_from_a_state_is_read_from_the_table() -> None:
    released = {row.row for row in transitions.caused_from("ORDER_STATE_PROPOSED", "oms")}
    assert "1" in released, "the oms releases a proposed order"
    assert "6" not in released, "a placement needs a released order"
    placed = transitions.caused_from("ORDER_STATE_RELEASED", "ems")
    assert any("REFUSAL_REASON_CLAIMED" in row.refusal for row in placed)
    created = {row.row for row in transitions.caused_from(transitions.NONE, "portfolio")}
    assert created == {"23b"}, "a row for every state is not a row creating an order"
    with pytest.raises(ValueError, match="no state of the order's table"):
        transitions.caused_from("PROPOSED", "oms")


def test_the_transition_table_is_carried_as_published() -> None:
    from importlib import resources

    text = resources.files("meridian").joinpath("transitions.json").read_text(encoding="utf-8")
    published = json.loads(text)
    assert published["_generated"].startswith("Generated by meridian-design")
    assert len(published["transitions"]) == len(transitions.table()) + len(
        transitions.execution_table()
    ) + len(transitions.booking_table())


# ── A placement's change requests, and no venue-originated path ─────────────


async def test_a_placement_heard_carries_its_change_requests_told_apart_by_kind() -> None:
    """Approved 2026-10-13: a placement carries its own change requests
    (`change_requests`), each with its PlacementChange and outcome, so a
    connectivity plugin hearing PlacementUpdated tells a cancel from a
    replace by the kind, never by a condition's reason."""
    replace = ops.PlacementChange(
        kind=ops.PLACEMENT_CHANGE_KIND_REPLACE,
        limit_price=ops.Money(amount=ops.Decimal(low=22780, scale=2), currency_code="USD"),
    )
    placement = ops.Placement(
        placement_id="PLC-1",
        order_id="ORD-1",
        connectivity_instance_id="sim-venue-1",
        status=ops.PlacementStatus(
            conditions=[
                ops.StandingPlacementCondition(
                    condition=ops.PLACEMENT_CONDITION_CHANGE_REQUESTED, reason="any words"
                )
            ]
        ),
        change_requests=[
            ops.ChangeRequest(
                change_request_id="CRQ-1",
                placement_id="PLC-1",
                placement_change=replace,
                outcome=ops.CHANGE_REQUEST_OUTCOME_PENDING,
            ),
            ops.ChangeRequest(
                change_request_id="CRQ-2",
                placement_id="PLC-1",
                placement_change=ops.PlacementChange(kind=ops.PLACEMENT_CHANGE_KIND_CANCEL),
                outcome=ops.CHANGE_REQUEST_OUTCOME_PENDING,
            ),
        ],
    )
    recorder = Recorder("sim-venue-1")
    recorder.answer(
        "PlacementUpdated", lambda _: ops.PlacementUpdatedEvent(placement=placement)
    )
    asked: list[ops.ChangeRequest] = []

    async def on_placement(heard: Heard[ops.PlacementUpdatedEvent]) -> None:
        asked.extend(heard.message.placement.change_requests)

    await recorder.receive(placement_updated=on_placement)
    assert [(each.change_request_id, each.placement_change.kind) for each in asked] == [
        ("CRQ-1", ops.PLACEMENT_CHANGE_KIND_REPLACE),
        ("CRQ-2", ops.PLACEMENT_CHANGE_KIND_CANCEL),
    ]
    assert meridian.as_money(asked[0].placement_change.limit_price) == meridian.Money(
        Decimal("227.80"), "USD"
    )
    wire = ops.Placement.FromString(placement.SerializeToString())
    assert ops.Placement.DESCRIPTOR.fields_by_name["change_requests"].number == 26
    assert wire.change_requests[0].placement_change == replace


def test_no_venue_originated_order_or_placement_is_offered() -> None:
    """Ruled 2026-10-13: v22 has no venue-originated path. A recorded order
    is the oms's telephoned or outside order, so the names that served a
    connectivity plugin's are gone, and connectivity's suite holds neither
    of its cases."""
    import inspect

    origins = ops.OrderOrigin.DESCRIPTOR.values_by_name
    reasons = ops.UnplacedReason.DESCRIPTOR.values_by_name
    assert "ORDER_ORIGIN_VENUE" not in origins and "ORDER_ORIGIN_TELEPHONED" in origins
    assert "UNPLACED_REASON_INSTRUMENT_INCOMPLETE" not in reasons
    assert "order" not in ops.UnplacedFact.DESCRIPTOR.fields_by_name
    assert not hasattr(ops, "RecordOrderRequest")
    recorded = inspect.signature(meridian.Plugin.record_order).parameters
    assert "venue_account_code" not in recorded and "raw_record" not in recorded
    names = {case.name for case in suite("connectivity").cases}
    assert not names & {"records-a-venue-originated-order", "places-a-direct-order"}
    resolves = suite("connectivity").case("resolves-a-venue-symbol-by-the-facts-date")
    assert resolves.about == "locates"
    assert [each.row for each in resolves.expect] == ["ResolveIdentifier", "RecordLocate"]
    assert transitions.caused_from(transitions.NONE, "connectivity") == ()


# ── A case naming one value twice ─────────────────────────────────────────────


async def test_a_case_naming_one_value_twice_is_matched_across_what_was_sent() -> None:
    case = suite("connectivity").case("derives-the-same-execution-id-twice")

    async def reported(*ids: str) -> Recorder:
        recorder = Recorder("sim-venue-1")
        for each in ids:
            await recorder.report_execution(
                placement_id="PLC-1",
                venue_execution_id=each,
                quantity=Decimal("10"),
                price=meridian.Money(Decimal("227.41"), "USD"),
            )
        return recorder

    assert check(case, await reported("SIM-a1", "SIM-a1")) is None
    assert "not one value" in (check(case, await reported("SIM-a1", "SIM-b2")) or "")
    assert "one value twice" in (check(case, await reported("SIM-a1")) or "")
    assert "not one value" in (check(case, await reported("SIM-a1", "")) or "")


# ── What the package exports for v22 ─────────────────────────────────────────


def test_the_order_paths_and_calendars_shapes_are_the_packages() -> None:
    for name in (
        "AlgorithmDeclaration",
        "AllocationInstruction",
        "OrderLink",
        "OrderChange",
        "PlacementChange",
        "StrategyInstruction",
        "VenueCatalogue",
        "SettlementDateInputs",
        "SpotDateInputs",
        "TenorDateInputs",
        "RollInputs",
        "BusinessDayInputs",
        "Actor",
    ):
        assert name in meridian.__all__ and getattr(meridian, name) is not None


# ── Every case contract v22 adds to the suites, as a plugin does it ──────────


def _v22_cases() -> list[tuple[str, str]]:
    from meridian.suites import suites

    return [
        (role, case.name)
        for role, held in sorted(suites().items())
        for case in held.cases
        if held.since == "v22" or case.name in _V22_NAMES
    ]


def _v22_names() -> set[str]:
    from order_path_cases import PRODUCERS

    return set(PRODUCERS)


_V22_NAMES = _v22_names()


@pytest.mark.parametrize(("role", "name"), _v22_cases(), ids=lambda each: str(each))
async def test_every_case_v22_adds_passes_as_a_plugin_holding_the_role_does_it(
    role: str, name: str
) -> None:
    from order_path_cases import PRODUCERS

    case = suite(role).case(name)
    recorder = Recorder(f"{role}-1")
    await PRODUCERS[name](recorder)
    assert check(case, recorder) is None


def test_the_suites_carry_the_rows_v22_adds() -> None:
    from meridian.suites import suites

    held = suites()
    assert {role for role, each in held.items() if each.since == "v22"} == {
        "connectivity",
        "oms",
        "confirmation",
        "servicing",
        "settlement",
    }
    # Contract v23 adds connectivity's three venue-originated fills, and the
    # OANDA batch's value-date roll; v24 the two every-role cases, the
    # give-up and the escape hatch's read, and the oms's booking; v25 drops
    # connectivity's escape-hatch read (decision 12, item 118).
    assert len(held["connectivity"].cases) == 34
    assert len(held["oms"].cases) == 32
    every = {case.name for each in held.values() for case in each.cases}
    assert set(_V22_NAMES) <= every, "each producer answers a published case"
    for role, each in held.items():
        names = {case.name for case in each.cases}
        assert "reads-a-calendar" in names, role
        if role not in ("connectivity", "operations"):
            assert "asks-for-a-settlement-date" in names, role
    order_rows = {
        expected.row
        for each in held.values()
        for case in each.cases
        for expected in case.expect
    }
    for row in (
        "ProposeOrder",
        "CreatePlacement",
        "ReportPlacement",
        "ReportExecution",
        "ListTradingInstructions",
        "TradingInstructionChanged",
        "ReadCalendar",
        "ComputeDate",
        "MapVenueAccount",
        "ReportVenueCatalogue",
    ):
        assert row in order_rows, row


async def test_a_connectivity_plugin_sending_on_a_pause_or_for_another_instance_fails() -> None:
    """The format's cases about what a plugin must not do (contract v22):
    each row it must stay silent on is `sends` false, so a plugin reporting
    a placement it holds under a pause, or one naming another instance,
    fails the case."""
    from order_path_cases import PRODUCERS

    for name in ("sends-nothing-new-on-a-pause", "hears-no-placement-of-another-instance"):
        case = suite("connectivity").case(name)
        assert case.expect, f"{name}: a case's expect is never empty"
        recorder = Recorder("sim-venue-1")
        await PRODUCERS[name](recorder)
        assert check(case, recorder) is None
        await recorder.report_placement(placement_id="PLC-1", event="acknowledged")
        assert "and the case sends none" in (check(case, recorder) or ""), name


def test_no_case_of_any_suite_expects_nothing() -> None:
    from meridian.suites import suites

    empty = [
        (role, case.name)
        for role, held in suites().items()
        for case in held.cases
        if not case.expect
    ]
    assert empty == []


def test_a_calendar_case_may_be_not_presented_and_an_unmarked_case_may_not() -> None:
    """Ruled 2026-10-13: the calendar cases and connectivity's
    records-a-locate carry `about`, so a plugin whose work never uses one
    marks it not presented, with why; a case with no marker stays required."""
    from meridian.suites import run, suites

    held = suites()
    for role, each in held.items():
        for case in each.cases:
            if case.name == "reads-a-calendar":
                assert case.about == "calendars", role
            if case.name == "asks-for-a-settlement-date":
                assert case.about == "settlement dates", role
    connectivity = held["connectivity"]
    for name in ("records-a-locate", "resolves-a-venue-symbol-by-the-facts-date"):
        assert connectivity.case(name).about == "locates", name
    for name in (
        "reads-whether-releases-wait-for-compliance",
        "hears-an-accounts-attributes-change",
    ):
        assert connectivity.case(name).about == "compliance waits", name
    for name in ("resolves-an-executions-venue", "reports-a-venue-not-held"):
        assert (
            connectivity.case(name).about_field == "meridian.v1.ReportExecutionRequest.venue_id"
        ), name
    assert not connectivity.case("acknowledges-a-placement-naming-it").about

    why = "this plugin reports what its venue states; it reads no calendar"
    report = run(
        "custody",
        {},
        not_presented={
            "reads-a-calendar": why,
            "asks-for-a-settlement-date": why,
            "a-security-holding": "never presented",
        },
    )
    assert report.not_presented == {
        "reads-a-calendar": why,
        "asks-for-a-settlement-date": why,
    }
    assert "required" in report.failures["a-security-holding"]
    assert "reads-a-calendar" not in report.failures
