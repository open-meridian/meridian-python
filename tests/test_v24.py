"""Contract v24, through the SDK: an execution booked to its accounts, and
every instrument named by the platform master's ID.

That the SDK declares v24; that a replacement is heard by every role,
caught up by sequence on start and after a loss, and handed on once; that
the current-ID map follows an ID through each replacement to the record it
names now, and the template catalogue keeps each version it reads; that the
suite runner answers the two every-role cases for a plugin that maps
neither, runs a plugin's own producer where it has one, and runs a suite on
provisional records too; that a booking's rows are read apart in the
transition table; that the booking operations reach the sidecar as typed;
and that `meridian.environment()` defaults to the sandbox, Live only where
code says so.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

import meridian
from conftest import Stream
from meridian import _transitions as transitions
from meridian.operations import SEQUENCED
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import ANSWERED_BY_SDK, HEARD, Recorder, names, run, suites

LCL = "LCL-01JB2000000000000000000001"
INS = "INS-01JB2000000000000000000001"
MERGED = "INS-01JB2000000000000000000002"
OTHER = "LCL-01JB2000000000000000000009"


def replaced(old: str, new: str, sequence: int, cause: int = ops.REPLACEMENT_CAUSE_RESOLVED):
    return ops.InstrumentReplacedEvent(
        replaced_instrument_id=old,
        instrument=ops.InstrumentRecord(instrument_id=new, description=f"{new} record"),
        cause=cause,
        sequence=sequence,
    )


def test_the_sdk_declares_contract_v24_or_later() -> None:
    assert int(meridian.SCHEMA_VERSION.removeprefix("v")) >= 24
    for name in ("CurrentIdMap", "TemplateCatalogue", "Allocation", "BookingState"):
        assert name in meridian.__all__ and getattr(meridian, name) is not None


# ── The replacement, heard by every role and caught up by sequence ──────────


def test_a_replacement_is_a_sequenced_row_every_role_hears() -> None:
    assert [(row.name, row.caught_up_by, row.records) for row in SEQUENCED] == [
        ("ReplaceMergedInstrument", "list_replacements", "replacements"),
        # Contract v26's three: a pricing plugin's batches, a client's
        # finished jobs, and event groups.
        ("PriceBatch", "list_price_batches", "batches"),
        ("JobFinished", "list_finished_jobs", "finished"),
        ("EventGroupChanged", "list_event_groups", "event_groups"),
    ]
    assert "ReplaceMergedInstrument" in HEARD
    for role, held in suites().items():
        if role == "pricing":
            # Contract v26: a pricing plugin reads nothing a batch did not carry.
            continue
        names = {case.name for case in held.cases}
        assert {"hears-and-reads-a-replacement", "reads-the-template-catalogue"} <= names, role


async def test_replacements_are_read_on_start_and_after_a_loss_each_handed_on_once(
    sidecar,
) -> None:
    service, address = sidecar
    first, second, third, fourth = (
        replaced(LCL, INS, 1),
        replaced(OTHER, "INS-01JB2000000000000000000003", 2),
        replaced(INS, MERGED, 3, ops.REPLACEMENT_CAUSE_PLATFORM_MERGED),
        replaced("LCL-01JB2000000000000000000004", "INS-01JB2000000000000000000004", 4),
    )
    # On start the store holds two, read a page at a time.
    service.operations.replacements = [first, second]
    service.operations.replacements_page = 1
    service.operations.streams = [
        Stream(
            deliveries=[
                # Heard again after the start's read had it: not handed on twice.
                ops.Delivery(replace_merged_instrument=second),
                ops.Delivery(lost=ops.Lost(rows=["ReplaceMergedInstrument"], dropped=1)),
                # Delivered after the catch-up read had it.
                ops.Delivery(replace_merged_instrument=fourth),
            ]
        )
    ]
    heard: list[meridian.Heard[ops.InstrumentReplacedEvent]] = []
    ids = meridian.CurrentIdMap()

    async def on_replaced(row: meridian.Heard[ops.InstrumentReplacedEvent]) -> None:
        heard.append(row)
        await ids.heard(row)

    plugin = await meridian.connect(address, heartbeat=False)
    task = asyncio.create_task(plugin.receive(replace_merged_instrument=on_replaced))
    try:
        # What the loss took is in the store by the time it is read.
        service.operations.replacements = [first, second, third, fourth]
        for _ in range(200):
            if len(heard) >= 4:
                break
            await asyncio.sleep(0.02)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await plugin.leave()
    (asked,) = service.operations.received
    assert list(asked.rows) == ["ReplaceMergedInstrument"]
    assert [(h.message.sequence, h.caught_up) for h in heard] == [
        (1, True),
        (2, True),
        (3, True),
        (4, True),
    ]
    reads = [r for r in service.operations.reads if isinstance(r, ops.ListReplacementsParams)]
    assert reads[0].after_sequence == 0
    assert any(read.after_sequence == 2 for read in reads), "after a loss, after the last seen"
    assert ids.current(LCL) == MERGED and ids.sequence == 4


async def test_a_start_without_seeding_hands_on_nothing_read_but_what_comes_after(
    sidecar,
) -> None:
    service, address = sidecar
    service.operations.replacements = [replaced(LCL, INS, 1), replaced(OTHER, MERGED, 2)]
    later = replaced(INS, "INS-01JB2000000000000000000005", 3)
    service.operations.streams = [
        Stream(
            deliveries=[
                ops.Delivery(replace_merged_instrument=service.operations.replacements[1]),
                ops.Delivery(replace_merged_instrument=later),
            ]
        )
    ]
    heard: list[int] = []

    async def on_replaced(row: meridian.Heard[ops.InstrumentReplacedEvent]) -> None:
        heard.append(row.message.sequence)

    plugin = await meridian.connect(address, heartbeat=False)
    task = asyncio.create_task(
        plugin.receive(replace_merged_instrument=on_replaced, seed=False)
    )
    try:
        for _ in range(200):
            if heard:
                break
            await asyncio.sleep(0.02)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await plugin.leave()
    assert heard == [3]


# ── The current-ID map ───────────────────────────────────────────────────────


async def test_the_map_follows_an_id_through_each_replacement_to_the_record_now() -> None:
    ids = meridian.CurrentIdMap()
    assert ids.current(LCL) == LCL and ids.record(LCL) is None
    assert ids.apply(replaced(LCL, INS, 1))
    assert ids.apply(replaced(INS, MERGED, 2, ops.REPLACEMENT_CAUSE_PLATFORM_MERGED))
    assert ids.current(LCL) == MERGED and ids.current(INS) == MERGED
    assert ids.same(LCL, MERGED) and ids.same(LCL, INS)
    assert not ids.same(LCL, OTHER)
    held = ids.record(LCL)
    assert held is not None and held.instrument_id == MERGED
    # One at or below the sequence applied changes nothing.
    assert not ids.apply(replaced(OTHER, LCL, 2))
    assert ids.replaced == {LCL: MERGED, INS: MERGED}
    # A replacement naming the way back would loop; the later one stands.
    assert ids.apply(replaced(MERGED, LCL, 3, ops.REPLACEMENT_CAUSE_MERGED))
    assert ids.current(MERGED) == LCL and ids.current(LCL) == LCL


async def test_the_map_catches_up_page_by_page_after_the_sequence_it_holds() -> None:
    held = [replaced(LCL, INS, 1), replaced(OTHER, MERGED, 2), replaced(INS, MERGED, 3)]
    asked: list[int] = []

    class Store:
        async def list_replacements(self, *, after_sequence: int) -> ops.ListReplacementsResult:
            asked.append(after_sequence)
            page = [event for event in held if event.sequence > after_sequence][:2]
            return ops.ListReplacementsResult(
                replacements=page, sequence=page[-1].sequence if page else after_sequence
            )

    ids = meridian.CurrentIdMap()
    assert await ids.catch_up(Store()) == 3
    assert asked == [0, 2, 3]
    assert ids.current(LCL) == MERGED and ids.sequence == 3
    assert await ids.catch_up(Store()) == 0
    assert asked[-1] == 3


async def test_the_catalogue_lists_and_reads_a_version_once() -> None:
    template = ops.SecurityTemplate(
        template_id="TPL-1",
        template_version="2",
        asset_class=ops.ASSET_CLASS_EQUITY,
        fields=[ops.TemplateField(path="share_class_figi", type="string", required=True)],
        match_rule=["share_class_figi"],
    )
    recorder = Recorder()
    recorder.answer("ListTemplates", lambda _: ops.ListTemplatesResult(templates=[template]))
    recorder.answer("ReadTemplate", lambda _: ops.ReadTemplateResult(template=template))
    catalogue = meridian.TemplateCatalogue()
    (listed,) = await catalogue.load(recorder, asset_class="equity")
    assert recorder.on("ListTemplates")[0].asset_class == ops.ASSET_CLASS_EQUITY
    assert catalogue.latest("TPL-1") == listed
    read = await catalogue.template(recorder, "TPL-1", "2")
    again = await catalogue.template(recorder, "TPL-1", "2")
    assert read == again and len(recorder.on("ReadTemplate")) == 1
    assert [field.path for field in read.fields if field.required] == ["share_class_figi"]
    recorder.answer("ReadTemplate", lambda _: ops.ReadTemplateResult())
    assert await catalogue.template(recorder, "TPL-9") is None


# ── The suite runner ─────────────────────────────────────────────────────────


def test_the_runner_answers_the_every_role_cases_for_a_plugin_mapping_neither() -> None:
    # Contract v26 adds a third, an event group heard and read.
    assert set(ANSWERED_BY_SDK) == {
        "hears-and-reads-a-replacement",
        "reads-the-template-catalogue",
        "hears-and-reads-an-event-group",
    }
    for role in suites():
        report = run(role, {})
        holds = [name for name in names(role) if name in ANSWERED_BY_SDK]
        if role == "pricing":
            assert holds == [], "a pricing plugin reads nothing a batch did not carry"
            continue
        assert set(holds) == set(ANSWERED_BY_SDK), role
        for name in holds:
            assert name in report.passed_cases, (role, name)
            assert name not in report.failures, (role, report.failures.get(name))
        assert report.answered_by_sdk == holds, role


def test_a_plugins_own_producer_is_run_instead_and_held_to_the_case() -> None:
    async def nothing(recorder: Recorder) -> None:
        await recorder.list_replacements(after_sequence=0)

    report = run("custody", {"hears-and-reads-a-replacement": nothing})
    assert (
        "nothing was heard on ReplaceMergedInstrument"
        in (report.failures["hears-and-reads-a-replacement"])
    )
    assert report.answered_by_sdk == [
        "reads-the-template-catalogue",
        "hears-and-reads-an-event-group",
    ]


async def test_an_ordinary_resolve_answers_the_platforms_record_or_a_provisional_one() -> None:
    platform = Recorder()
    found = await platform.resolve_identifier(
        identifiers=[ops.Identifier(scheme="isin", value="US0378331005")]
    )
    assert found.instrument_id == "INS-suite-1" and not found.provisional and not found.minted
    local = Recorder(provisional=True)
    symbol = ops.Identifier(scheme="symbol", value="ZZTOP", source="custodian")
    found = await local.resolve_identifier(
        identifiers=[symbol], stated_description="ZZ Top Corp.", stated_currency="USD"
    )
    assert found.instrument_id == "LCL-suite-1" and found.provisional and found.minted
    # Below the minimum a record needs (W3.7): not found, nothing minted.
    for thin in ({}, {"stated_description": "ZZ Top Corp."}):
        missed = await local.resolve_identifier(identifiers=[symbol], **thin)
        assert not missed.found and not missed.minted and not missed.instrument_id, thin
        assert missed.miss_reason == ops.MISS_REASON_NOT_FOUND
    coded = await local.resolve_identifier(
        identifiers=[ops.Identifier(scheme="iso4217", value="CHF")]
    )
    assert coded.found and coded.provisional, "a currency's code states both"


def test_the_reference_suite_is_carried_in_preview_with_its_cases() -> None:
    held = suites()["reference"]
    assert held.since == "v24"
    assert {case.name for case in held.cases} >= {
        "fills-a-template",
        "licensed-vendor-value-stays",
        "offers-never-overwrite-a-person",
        "reads-the-record-it-fills",
        "resolves-a-security-it-reconciles",
    }
    # Every OfferTemplateFields row the suite names is the reference role's.
    rows = {expected.row for case in held.cases for expected in case.expect}
    assert "OfferTemplateFields" in rows and "RecordHolding" not in rows


# ── Booking ──────────────────────────────────────────────────────────────────


def test_a_bookings_rows_are_read_apart_in_booking_states() -> None:
    rows = transitions.booking_table()
    assert [row.row for row in rows] == [f"b{n}" for n in range(1, 10)]
    states = set(transitions.booking_states())
    assert states == set(ops.BookingState.keys()) - {"BOOKING_STATE_UNSPECIFIED"}
    for row in rows:
        assert set(row.from_states) <= states | {transitions.NONE, transitions.ANY}, row.row
        assert set(row.to_states) <= states | {transitions.UNCHANGED}, row.row
    assert not {row.row for row in transitions.table()} & {row.row for row in rows}
    assert "oms" in rows[0].caused_by


async def test_a_booking_and_an_alert_reach_the_sidecar_typed() -> None:
    recorder = Recorder("oms-1")
    usd = meridian.Money(Decimal("2275.00"), "USD")
    await recorder.book_order(
        order_id="ORD-1",
        execution_ids=["EXE-1"],
        allocations=[
            meridian.Allocation(
                account_id="ACC-ERRORS",
                quantity=Decimal("10"),
                average_price=meridian.Money(Decimal("227.50"), "USD"),
                gross_amount=usd,
                net_amount=usd,
                intended_settlement_date="2026-10-16",
                reason="Overfill",
                error_cause="overfill",
            )
        ],
    )
    (sent,) = recorder.on("BookOrder")
    (part,) = sent.allocations
    assert part.error_cause == ops.ERROR_CAUSE_OVERFILL
    assert meridian.as_decimal(part.quantity) == Decimal("10")
    assert part.intended_settlement_date == "2026-10-16"
    await recorder.correct_booking(booking_id="BKG-1", kind="cancel", reason="wrong fund")
    assert recorder.on("CorrectBooking")[0].kind == ops.BOOKING_CORRECTION_KIND_CANCEL
    await recorder.report_give_up(execution_id="EXE-1", answer="rejected", reason="not set up")
    assert recorder.on("ReportGiveUp")[0].answer == ops.GIVE_UP_ANSWER_REJECTED
    await recorder.list_alerts(state="raised", kind="booking_held")
    (alerts,) = recorder.on("ListAlerts")
    assert alerts.state == ops.ALERT_STATE_RAISED and alerts.kind == ops.ALERT_KIND_BOOKING_HELD
    with pytest.raises(ValueError, match="error_cause"):
        await recorder.book_order(
            order_id="ORD-1",
            allocations=[
                meridian.Allocation(
                    quantity=1,
                    average_price=usd,
                    gross_amount=usd,
                    net_amount=usd,
                    error_cause="not-a-cause",
                )
            ],
        )


# ── The environment's safe default ───────────────────────────────────────────


def test_the_environment_defaults_to_the_sandbox_and_live_only_in_code() -> None:
    held = meridian.environment()._declared()
    assert held.name == "environment" and held.required
    assert held.default_value == "sandbox"
    assert [c.value for c in held.choices] == ["live", "sandbox"]
    assert "Sandbox until a person chooses Live" in held.description
    live = meridian.environment(default="live")._declared()
    assert live.default_value == "live" and "Live unless" in live.description
    own = meridian.environment(description="Paper or live trading.")._declared()
    assert own.description == "Paper or live trading."
    with pytest.raises(ValueError, match="one of live, sandbox"):
        meridian.environment(default="practice")


def test_a_typed_class_is_on_the_sandbox_until_a_value_is_set() -> None:
    @meridian.settings
    class Config:
        environment: str = meridian.environment()

    assert Config._of({}).environment == "sandbox"  # type: ignore[attr-defined]
    assert Config._of({"environment": "live"}).environment == "live"  # type: ignore[attr-defined]


# ── The templates' pre-push hook: CI-first ───────────────────────────────────


def test_the_templates_hook_runs_nothing_for_a_branch_push(tmp_path) -> None:
    import os
    import subprocess
    from pathlib import Path

    root = Path(__file__).parents[1]
    hook = root / "template" / "hooks" / "pre-push"
    assert os.access(hook, os.X_OK), "the hook is executable"
    for role in ("data", "reporting", "custody", "operations"):
        assert (root / "templates" / role / "hooks" / "pre-push").read_bytes() == (
            hook.read_bytes()
        ), role
    sha = "0" * 40
    branch = subprocess.run(
        [str(hook)],
        input=f"refs/heads/v24 {sha} refs/heads/v24 {sha}\n",
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert branch.returncode == 0 and "CI on its pull request is the gate" in branch.stdout


# ── A dataset's calendar (contract v22's field, carried from 0.28.0) ─────────


def test_a_dataset_names_its_calendar_on_the_wire_and_in_the_upload() -> None:
    from meridian.declaration import Declaration

    daily = meridian.DatasetDeclaration(
        key="daily",
        vendor="Tiingo",
        data_types=["meridian.v1.Price"],
        modes=["pull"],
        day_time_zone="America/New_York",
        day_end_minute=960,
        calendar_id="CAL-01M4VF0F4XGP3RATCCSKDPZSBP",
    )
    assert daily._wire().calendar_id == "CAL-01M4VF0F4XGP3RATCCSKDPZSBP"
    assert daily._to_json()["calendar_id"] == "CAL-01M4VF0F4XGP3RATCCSKDPZSBP"
    assert Declaration(catalogue=[daily]) is not None
    with pytest.raises(ValueError, match="no calendar's ID"):
        meridian.DatasetDeclaration(
            key="daily",
            vendor="Tiingo",
            data_types=["meridian.v1.Price"],
            modes=["pull"],
            calendar_id="XNYS",
        )
