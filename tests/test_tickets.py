"""A plugin files a ticket for a person, and reads what it filed (W4.12,
contract v13).

What this client decides, and so what is worth asserting: that a filing goes
for the person whose request the plugin is serving, as the call's
`meridian-caller` metadata, and never for nobody; that what the sidecar would
refuse by its bounds is refused here first, naming the field, with nothing
sent; and that a refusal arrives in this package's terms. The fake sidecar
keeps what was filed and folds a repeat, as the dashboard does, so a filing
can be followed to what the plugin reads back.
"""

from __future__ import annotations

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import (
    Caller,
    CallFailed,
    NotGranted,
    NotRegistered,
    TicketKind,
    TicketReference,
    TicketResolution,
    TicketState,
    TicketSubject,
)
from meridian.testing import caller_header
from meridian.v1 import sidecar_pb2

BEN = Caller.from_header(caller_header("read", read={"ACC-GROWTH"}, subject="local|ben"))


def filing(**given: object) -> dict[str, object]:
    """A filing that passes, with `given` in place of its fields."""
    return {
        "title": "Break on the growth account still open after its cause was confirmed",
        "seen": "I confirmed the cause on 3 October; the page still lists it as open.",
        "kind": "defect",
        "idempotency_key": "break-still-open-BRK-1",
        "for_caller": BEN,
        **given,
    }


async def test_a_ticket_is_filed_for_the_person_and_a_repeat_folds(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        made = await plugin.file_ticket(
            **filing(
                step="W9.7",
                operation="ResolveBreak",
                paths=["break_id"],
                references=[TicketReference("break", "BRK-1", account_id="ACC-GROWTH")],
            )
        )
        again = await plugin.file_ticket(**filing())
    finally:
        await plugin.leave()

    assert (made.ticket_id, made.outcome, made.seen_count) == ("TKT-1", "made", 1)
    assert (again.ticket_id, again.outcome, again.seen_count) == ("TKT-1", "unchanged", 2)
    assert len(service.tickets) == 1
    (sent, caller), _ = service.filings
    # For Ben, as the header his request carried, and never as the plugin.
    assert caller == BEN.header
    assert sent.title.startswith("Break on the growth account")
    assert sent.kind == sidecar_pb2.TICKET_KIND_DEFECT
    # This plugin, by default: the sidecar sets its instance and the
    # deployment its version, so the plugin names neither.
    assert sent.concerns == sidecar_pb2.TicketSubject(kind="plugin")
    assert (sent.step, sent.operation, list(sent.paths)) == (
        "W9.7",
        "ResolveBreak",
        ["break_id"],
    )
    assert list(sent.references) == [
        sidecar_pb2.TicketReference(kind="break", value="BRK-1", account_id="ACC-GROWTH")
    ]
    assert sent.idempotency_key == "break-still-open-BRK-1"


async def test_the_kind_and_what_it_concerns_are_taken_by_name_or_enum(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        await plugin.file_ticket(**filing(kind=TicketKind.Value("TICKET_KIND_REQUEST")))
        await plugin.file_ticket(
            **filing(
                kind="TICKET_KIND_QUESTION", concerns=TicketSubject.SDK, idempotency_key="b"
            )
        )
        await plugin.file_ticket(
            **filing(
                kind="discrepancy",
                concerns="platform",
                for_caller=BEN.header,
                idempotency_key="c",
            )
        )
    finally:
        await plugin.leave()
    assert [(f.kind, f.concerns.kind) for f, _ in service.filings] == [
        (sidecar_pb2.TICKET_KIND_REQUEST, "plugin"),
        (sidecar_pb2.TICKET_KIND_QUESTION, "sdk"),
        (sidecar_pb2.TICKET_KIND_DISCREPANCY, "platform"),
    ]
    assert [caller for _, caller in service.filings] == [BEN.header] * 3


def test_the_subjects_are_the_contracts_closed_list() -> None:
    assert [subject.value for subject in TicketSubject] == [
        "plugin",
        "dashboard",
        "bor",
        "street",
        "instrument",
        "conductor",
        "chart",
        "cli",
        "sdk",
        "platform",
    ]
    assert TicketState.Name(sidecar_pb2.TICKET_STATE_RESOLVED) == "TICKET_STATE_RESOLVED"
    assert TicketResolution.Value("TICKET_RESOLUTION_NOT_A_PROBLEM") == 6


@pytest.mark.parametrize(
    ("given", "named"),
    [
        ({"for_caller": ""}, "for_caller names nobody"),
        ({"title": ""}, "title is empty"),
        ({"title": "x" * 121}, "title is 121 characters; it holds at most 120"),
        ({"seen": "x" * 8001}, "seen is 8001 characters; it holds at most 8000"),
        ({"kind": ""}, "kind is ''"),
        ({"kind": "complaint"}, "kind is 'complaint', which TicketKind does not define"),
        ({"kind": "unspecified"}, "kind is 'unspecified'"),
        ({"concerns": "custody-1"}, "concerns is 'custody-1'; it is one of plugin, dashboard"),
        ({"idempotency_key": ""}, "idempotency_key is empty"),
        (
            {"references": [TicketReference("account", f"ACC-{n}") for n in range(51)]},
            "references names 51 records; a ticket names at most 50",
        ),
        ({"references": [TicketReference("note", "x")]}, "references[0].kind is 'note'"),
        ({"references": [TicketReference("instrument", "")]}, "references[0].value is empty"),
        (
            {"references": [TicketReference("tool_call", "x" * 201)]},
            "references[0].value is 201 characters",
        ),
        (
            {
                "references": [
                    TicketReference("account", "ACC-1"),
                    TicketReference("street_record", "SR-1"),
                ]
            },
            "references[1].account_id is empty; a street record names the account",
        ),
    ],
)
async def test_what_the_sidecar_would_refuse_by_its_bounds_is_refused_here_first(
    sidecar: tuple[FakeSidecar, str], given: dict[str, object], named: str
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(ValueError) as refused:
            await plugin.file_ticket(**filing(**given))
    finally:
        await plugin.leave()
    assert named in str(refused.value)
    assert service.filings == [], "a filing refused here was sent"


@pytest.mark.parametrize(
    ("status", "raised", "kind"),
    [
        # The plugin as itself, or an account the person may not read.
        (grpc.StatusCode.PERMISSION_DENIED, NotGranted, None),
        # An assertion that is not the dashboard's, or out of date.
        (grpc.StatusCode.UNAUTHENTICATED, CallFailed, "not vouched for"),
        # About another plugin, or a character the sidecar refuses.
        (grpc.StatusCode.INVALID_ARGUMENT, CallFailed, "invalid"),
        # The 21st filing in an hour.
        (grpc.StatusCode.RESOURCE_EXHAUSTED, CallFailed, "refused"),
    ],
)
async def test_a_refused_filing_is_raised_in_this_packages_terms(
    sidecar: tuple[FakeSidecar, str],
    status: grpc.StatusCode,
    raised: type[Exception],
    kind: str | None,
) -> None:
    service, address = sidecar
    service.ticket_refused = (status, "concerns.instance: custody-1 is another plugin")
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(raised) as refused:
            await plugin.file_ticket(**filing())
    finally:
        await plugin.leave()
    assert "FileTicket" in str(refused.value)
    assert "concerns.instance: custody-1 is another plugin" in str(refused.value)
    if kind is not None:
        assert isinstance(refused.value, CallFailed) and refused.value.kind == kind


async def test_what_it_filed_is_read_back_for_the_person(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        for key in ("a", "b", "c"):
            await plugin.file_ticket(**filing(idempotency_key=key))
        await plugin.file_ticket(**filing(idempotency_key="b"))
        service.tickets[0].state = sidecar_pb2.TICKET_STATE_RESOLVED
        service.tickets[0].resolution = sidecar_pb2.TICKET_RESOLUTION_NOTE

        by_key = await plugin.filed_tickets(for_caller=BEN, idempotency_keys=["b"])
        by_id = await plugin.filed_tickets(for_caller=BEN.header, ticket_ids=["TKT-1"])
        first = await plugin.filed_tickets(for_caller=BEN)
        rest = await plugin.filed_tickets(for_caller=BEN, cursor=first.next_cursor)
    finally:
        await plugin.leave()

    (b,) = by_key.tickets
    assert (b.ticket_id, b.state, b.seen_count) == ("TKT-2", sidecar_pb2.TICKET_STATE_OPEN, 2)
    (a,) = by_id.tickets
    assert (a.state, a.resolution) == (
        sidecar_pb2.TICKET_STATE_RESOLVED,
        sidecar_pb2.TICKET_RESOLUTION_NOTE,
    )
    assert list(a.answers) == []
    assert [t.ticket_id for t in first.tickets] == ["TKT-1", "TKT-2"]
    assert first.next_cursor == "TKT-2"
    assert [t.ticket_id for t in rest.tickets] == ["TKT-3"] and rest.next_cursor == ""
    assert {caller for _, caller in service.filed_reads} == {BEN.header}


async def test_reading_what_it_filed_names_one_way_and_a_person(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(
            ValueError, match="name one of ticket_ids, idempotency_keys or cursor"
        ):
            await plugin.filed_tickets(for_caller=BEN, ticket_ids=["TKT-1"], cursor="TKT-1")
        with pytest.raises(ValueError, match="name one of"):
            await plugin.filed_tickets(for_caller=BEN, idempotency_keys=["a"], cursor="x")
        with pytest.raises(ValueError, match="for_caller names nobody"):
            await plugin.filed_tickets(for_caller="")
    finally:
        await plugin.leave()
    assert service.filed_reads == []


async def test_nothing_is_filed_after_the_plugin_left(sidecar: tuple[FakeSidecar, str]) -> None:
    _, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    await plugin.leave()
    with pytest.raises(NotRegistered):
        await plugin.file_ticket(**filing())
    with pytest.raises(NotRegistered):
        await plugin.filed_tickets(for_caller=BEN)
