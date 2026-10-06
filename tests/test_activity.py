"""The custodian's activity and each sync status the street keeps (W2.10 to
W2.14, contract v14), from the plugin's side.

Against the fake sidecar, which keeps what is reported on it as the street
keeps it: what these hold is the SDK's half -- an activity put on the wire
with its numbers exact and its kind as the wire's enum, a repeat answered as
already recorded, the reads' paging and `history_from` handed back as sent,
the rows heard typed, and a break's cause linked to an activity. What the
sidecar stamps and refuses, and what the street derives nothing from, is
meridian-core's to test, and the interop suite's.

From contract v15 an activity recorded before its instrument resolved is
re-resolved (W2.15, W2.16): the SDK's send, answered as already recorded when
the latest resolution names it, read back beside the activity as first
recorded, and heard typed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

import pytest

import meridian
from conftest import FakeSidecar
from meridian import (
    ActivityKind,
    ActivityRef,
    CallFailed,
    CustodialActivity,
    Heard,
    Money,
    Provenance,
    RawRecordRef,
)
from meridian.operations import Operations
from meridian.plugin.v1 import operations_pb2 as ops

EXTERNAL = "SNAP-ACC-1"


def reinvestment(identifier: str = "a3f0c2d4", **more: Any) -> CustodialActivity:
    """Fidelity's SPAXX dividend for September, reinvested, as the record-activity
    fixture states it."""
    given: dict[str, Any] = {
        "external_activity_id": identifier,
        "kind": ActivityKind.ACTIVITY_KIND_REINVESTMENT,
        "instrument_id": "INS-SPAXX",
        "trade_date": "2026-09-30",
        "settlement_date": "2026-09-30",
        "units": Decimal("3.27"),
        "price": Money(Decimal("1.00"), "USD"),
        "amount": Money(Decimal("-3.27"), "USD"),
        "description": "REINVESTMENT FIDELITY GOVERNMENT MONEY MARKET (SPAXX) (Cash)",
        "raw_record": RawRecordRef(
            instance_id="custody-snaptrade-1", key=f"activities/{EXTERNAL}/{identifier}"
        ),
    }
    given.update(more)
    return CustodialActivity(**given)


async def connected(sidecar: tuple[FakeSidecar, str]) -> meridian.Plugin:
    _, address = sidecar
    return await meridian.connect(address, heartbeat=False)


async def test_an_activity_crosses_as_the_custodian_stated_it(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        first = await plugin.record_activity(
            external_account_id=EXTERNAL, source="snaptrade", activity=reinvestment()
        )
        again = await plugin.record_activity(
            external_account_id=EXTERNAL, source="snaptrade", activity=reinvestment()
        )
    finally:
        await plugin.leave()
    assert (first.activity_id, first.already_recorded) == ("ACT-1", False)
    assert (again.activity_id, again.already_recorded) == ("ACT-1", True)
    assert len(service.operations.activities) == 1, "a redelivery is recorded once"

    sent = service.operations.sent[0]
    assert isinstance(sent, ops.RecordActivityParams)
    assert sent.activity.kind == ops.ACTIVITY_KIND_REINVESTMENT
    assert (sent.activity.units.low, sent.activity.units.scale) == (327, 2)
    assert meridian.as_money(sent.activity.amount) == Money(Decimal("-3.27"), "USD")
    assert sent.activity.raw_record.key == f"activities/{EXTERNAL}/a3f0c2d4"


async def test_a_value_the_custodian_did_not_state_is_unset(sidecar) -> None:
    """A 2-for-1 split: units added, no cash moved, no price stated."""
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.record_activity(
            external_account_id=EXTERNAL,
            source="snaptrade",
            activity=reinvestment(
                kind="ACTIVITY_KIND_SPLIT",
                units=40,
                price=None,
                amount=None,
                settlement_date="",
            ),
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert sent.activity.kind == ops.ACTIVITY_KIND_SPLIT, "a kind may be given by its name"
    assert not sent.activity.HasField("price")
    assert not sent.activity.HasField("amount")


async def test_a_kind_that_does_not_convert_travels_as_reported(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    reported = meridian.AsReported(
        scheme="snaptrade:activity-type", code="OPTIONEXPIRATION", text="OPTIONEXPIRATION"
    )
    try:
        await plugin.record_activity(
            external_account_id=EXTERNAL,
            source="snaptrade",
            activity=reinvestment(kind=None, kind_as_reported=reported),
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert sent.activity.kind == ops.ACTIVITY_KIND_UNSPECIFIED
    assert sent.activity.kind_as_reported.code == "OPTIONEXPIRATION"


@pytest.mark.parametrize(
    ("given", "says"),
    [
        ({"kind": "ACTIVITY_KIND_BOUGHT"}, "activity.kind"),
        ({"units": 3.27}, "activity.units"),
        ({"amount": Money(Decimal("1e-19"), "USD")}, "activity.amount"),
    ],
)
async def test_an_activity_the_wire_cannot_carry_is_refused_naming_its_path(
    sidecar, given: dict[str, Any], says: str
) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        with pytest.raises((ValueError, TypeError), match=says):
            await plugin.record_activity(
                external_account_id=EXTERNAL, source="snaptrade", activity=reinvestment(**given)
            )
    finally:
        await plugin.leave()
    assert service.operations.sent == [], "nothing is sent"


async def test_activity_is_read_by_trade_date_with_the_sources_history_from(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.report_sync_status(
            source="snaptrade",
            external_account_id=EXTERNAL,
            state=meridian.SyncState.SYNC_STATE_CURRENT,
            history_from="2024-10-04",
        )
        for n, date in enumerate(("2026-09-30", "2026-09-08", "2026-09-15", "2026-10-01")):
            await plugin.record_activity(
                external_account_id=EXTERNAL,
                source="snaptrade",
                activity=reinvestment(f"A-{n}", trade_date=date),
            )
        first = await plugin.list_activities(
            account_id="ACC-1",
            trade_date_from="2026-09-08",
            trade_date_to="2026-09-30",
            page_size=2,
        )
        rest = await plugin.list_activities(
            account_id="ACC-1",
            trade_date_from="2026-09-08",
            trade_date_to="2026-09-30",
            page_size=2,
            cursor=first.next_cursor,
        )
        since = await plugin.list_activities(account_id="ACC-1", since=first.as_of)
    finally:
        await plugin.leave()
    dates = [a.activity.trade_date for a in [*first.activities, *rest.activities]]
    assert dates == ["2026-09-08", "2026-09-15", "2026-09-30"], "inclusive, by trade date"
    assert first.next_cursor and not rest.next_cursor
    assert first.history_from == "2024-10-04"
    assert {a.account_id for a in first.activities} == {"ACC-1"}
    assert since.activities == [], "nothing recorded after the watermark"


async def test_the_latest_sync_status_of_each_connection_is_read(sidecar) -> None:
    service, _ = sidecar
    service.operations.links["SNAP-ACC-2"] = "ACC-2"
    plugin = await connected(sidecar)
    try:
        for external, state in (
            (EXTERNAL, meridian.SyncState.SYNC_STATE_CURRENT),
            ("SNAP-ACC-2", meridian.SyncState.SYNC_STATE_STALE),
            (EXTERNAL, meridian.SyncState.SYNC_STATE_NEEDS_SIGN_IN),
            ("SNAP-ACC-9", meridian.SyncState.SYNC_STATE_CURRENT),
        ):
            await plugin.report_sync_status(
                source="snaptrade", external_account_id=external, state=state
            )
        latest = await plugin.list_sync_statuses()
        mine = await plugin.list_sync_statuses(account_id="ACC-1")
        every = await plugin.list_sync_statuses(
            since=ops.Watermark(partitions=[ops.PartitionSequence(partition="street")])
        )
    finally:
        await plugin.leave()
    assert [(s.status.account_id, s.status.state) for s in latest.statuses] == [
        ("", meridian.SyncState.SYNC_STATE_CURRENT),
        ("ACC-1", meridian.SyncState.SYNC_STATE_NEEDS_SIGN_IN),
        ("ACC-2", meridian.SyncState.SYNC_STATE_STALE),
    ], "an unlinked account's is kept with its account empty"
    assert [s.status.state for s in mine.statuses] == [
        meridian.SyncState.SYNC_STATE_NEEDS_SIGN_IN
    ]
    assert [s.journal.sequence for s in every.statuses] == [1, 2, 3, 4]


async def test_a_break_names_the_activity_that_explains_it(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    linked = ActivityRef(
        activity_id="ACT-1",
        change=ops.JournalRef(partition="street", sequence=7, previous_sequence=3),
        trade_date="2026-09-30",
    )
    try:
        await plugin.record_break(
            account_id="ACC-1",
            candidate_causes=[
                meridian.BreakCause(
                    category="BREAK_CAUSE_CATEGORY_INCOME_REINVESTED", activity=linked
                )
            ],
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    (cause,) = sent.candidate_causes
    assert cause.category == ops.BREAK_CAUSE_CATEGORY_INCOME_REINVESTED
    assert cause.WhichOneof("item") == "activity"
    assert cause.activity.activity_id == "ACT-1"


async def test_activity_and_sync_statuses_are_heard_typed(sidecar) -> None:
    """Seeded from what the street keeps, each record handed on once."""
    service, address = sidecar
    reporter = await meridian.connect(address, heartbeat=False)
    try:
        await reporter.record_activity(
            external_account_id=EXTERNAL, source="snaptrade", activity=reinvestment()
        )
        await reporter.report_sync_status(
            source="snaptrade",
            external_account_id=EXTERNAL,
            state=meridian.SyncState.SYNC_STATE_NEEDS_SIGN_IN,
        )
    finally:
        await reporter.leave()

    activities: list[Heard[ops.ActivityRecordedEvent]] = []
    statuses: list[Heard[ops.SyncStatusRecordedEvent]] = []
    both = asyncio.Event()

    async def activity(heard: Heard[ops.ActivityRecordedEvent]) -> None:
        activities.append(heard)
        if statuses:
            both.set()

    async def status(heard: Heard[ops.SyncStatusRecordedEvent]) -> None:
        statuses.append(heard)
        if activities:
            both.set()

    plugin = await meridian.connect(address, heartbeat=False)
    task = asyncio.create_task(
        plugin.receive(activity_recorded=activity, sync_status_recorded=status)
    )
    try:
        await asyncio.wait_for(both.wait(), timeout=5)
        await asyncio.sleep(0.1)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await plugin.leave()
    assert sorted(service.operations.received[0].rows) == [
        "ActivityRecorded",
        "SyncStatusRecorded",
    ]
    ((heard_activity,), (heard_status,)) = (activities, statuses)
    assert heard_activity.caught_up and heard_activity.message.activity_id == "ACT-1"
    assert heard_status.message.status.state == meridian.SyncState.SYNC_STATE_NEEDS_SIGN_IN


async def test_receive_hands_on_only_the_rows_given_a_handler() -> None:
    """A revision adding a row a plugin does not hear changes nothing it is
    handed: v14 added two, and a plugin's own stand-in for the hook, which
    compared what it was handed, broke on rows it never asked for."""
    handed: dict[str, Any] = {}

    class Hearing(Operations):
        async def _receive(
            self, handlers: dict[str, Callable[[Any], Awaitable[None]] | None], *, seed: bool
        ) -> None:
            handed.update(handlers, seed=seed)

    async def statement(heard: Heard[ops.StatementRecordedEvent]) -> None:
        return None

    await Hearing().receive(statement_recorded=statement, seed=False)
    assert handed == {"StatementRecorded": statement, "seed": False}


# ── An activity re-resolved (W2.15, W2.16, contract v15) ─────────────────

#: The plan-code link a person set, which resolved OQKR to VIGIX.
LINKED_BY = Provenance(
    field="instrument_id",
    kind="PROVENANCE_KIND_SUPPLIED",
    person="Ada Park, in SnapTrade's plan-code links",
)


def unresolved(identifier: str) -> CustodialActivity:
    """A 401(k) reinvestment under the plan's own code, which resolved to
    nothing when it was recorded."""
    return reinvestment(
        identifier,
        instrument_id="",
        instrument_as_reported=meridian.AsReported(
            scheme="snaptrade:symbol", code="OQKR", text="OQKR"
        ),
    )


async def re_resolve(
    plugin: meridian.Plugin, identifier: str, instrument_id: str = "INS-VIGIX"
) -> ops.ReResolveActivityResult:
    return await plugin.re_resolve_activity(
        external_account_id=EXTERNAL,
        source="snaptrade",
        external_activity_id=identifier,
        instrument_id=instrument_id,
        provenance=LINKED_BY,
        resolved_at_ns=1_791_158_400_000_000_000,
    )


async def test_an_activity_is_re_resolved_beside_its_first_record(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        first = await plugin.record_activity(
            external_account_id=EXTERNAL, source="snaptrade", activity=unresolved("401k-1")
        )
        done = await re_resolve(plugin, "401k-1")
        again = await re_resolve(plugin, "401k-1")
        moved = await re_resolve(plugin, "401k-1", "INS-VFIAX")
        read = await plugin.list_activities(account_id="ACC-1")
    finally:
        await plugin.leave()
    assert (done.activity_id, done.already_recorded) == (first.activity_id, False)
    assert again.already_recorded, "naming what the latest resolution names"
    assert not moved.already_recorded

    sent = service.operations.sent[1]
    assert isinstance(sent, ops.ReResolveActivityParams)
    assert sent.provenance.kind == ops.PROVENANCE_KIND_SUPPLIED, "an enum by its name"
    assert sent.provenance.person == LINKED_BY.person
    assert not sent.HasField("acting_for"), "the plugin sends it as itself"

    (kept,) = read.activities
    assert kept.activity.instrument_id == "", "the activity as first recorded"
    assert kept.activity.instrument_as_reported.code == "OQKR"
    assert [(r.activity_id, r.instrument_id) for r in read.re_resolutions] == [
        (first.activity_id, "INS-VIGIX"),
        (first.activity_id, "INS-VFIAX"),
    ], "each its own record; the activity's instrument is the latest's"
    assert read.re_resolutions[0].account_id == "ACC-1"


async def test_a_re_resolution_of_nothing_recorded_is_refused(sidecar) -> None:
    plugin = await connected(sidecar)
    try:
        with pytest.raises(CallFailed) as refused:
            await re_resolve(plugin, "never-sent")
    finally:
        await plugin.leave()
    assert refused.value.kind == "handler error"
    assert "no activity is recorded as never-sent" in str(refused.value)


async def test_a_re_resolution_is_heard_typed_and_caught_up_from_a_read(sidecar) -> None:
    _, address = sidecar
    reporter = await meridian.connect(address, heartbeat=False)
    try:
        first = await reporter.record_activity(
            external_account_id=EXTERNAL, source="snaptrade", activity=unresolved("401k-2")
        )
        await re_resolve(reporter, "401k-2")
    finally:
        await reporter.leave()

    heard: list[Heard[ops.ActivityReResolvedEvent]] = []
    one = asyncio.Event()

    async def re_resolved(each: Heard[ops.ActivityReResolvedEvent]) -> None:
        heard.append(each)
        one.set()

    plugin = await meridian.connect(address, heartbeat=False)
    task = asyncio.create_task(plugin.receive(activity_re_resolved=re_resolved))
    try:
        await asyncio.wait_for(one.wait(), timeout=5)
        await asyncio.sleep(0.1)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await plugin.leave()
    (caught,) = heard
    assert caught.caught_up and caught.row == "ActivityReResolved"
    assert caught.message.re_resolution.activity_id == first.activity_id
    assert caught.message.re_resolution.instrument_id == "INS-VIGIX"
    assert caught.message.re_resolution.account_id == "ACC-1"
