"""Contract v21 through the SDK: a plugin's autonomous work calls its own
acts as the service account its role runs as (`meridian.runs_as`, W4.15),
and a route reached for such a call reads a caller who is a service account
and acts as for a person (W4.9).

What this client decides, and so what is worth asserting: that the call is
sent as the plugin itself, never for a person; that its answer, made or
prepared, is handed back as the dashboard gave it; that a refusal keeps its
status and the fields it named, and an older sidecar says so plainly; and
that what the sidecar would refuse by its bounds is refused here first.
Whether the account may make the act is the dashboard's, tested in
meridian-core.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import Caller, CallFailed, NotGranted, NotRegistered, SubjectKind
from meridian.pages import Request
from meridian.testing import PageClient, caller_header
from meridian.v1 import sidecar_pb2

SERVICE_ACCOUNT = SubjectKind.SUBJECT_KIND_SERVICE_ACCOUNT

CLOSE = {
    "account_id": "ACC-1",
    "break_ids": ["BRK-01J8XQ7B000000000000000002"],
    "statement_id": "STMT-01J8XQ5N2P0000000000003",
    "as_of_date": "2026-09-10",
}
WHY = "The settlement landed: the difference was gone at the statement of 2026-09-10"


@pytest.fixture
async def operations_plugin(sidecar: tuple[FakeSidecar, str]):
    service, address = sidecar
    service.roles = ("operations",)
    service.instance_id = "operations-1"
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        yield service, plugin
    finally:
        await plugin.leave()


# ── The caller's kind and owner ──────────────────────────────────────────────


def test_a_caller_is_a_person_unless_the_claims_say_a_service_account() -> None:
    person = Caller.from_header(caller_header("write", read={"ACC-1"}, write={"ACC-1"}))
    assert person.subject_kind == SubjectKind.SUBJECT_KIND_UNSPECIFIED
    assert person.owner_subject == ""

    account = Caller.from_header(
        caller_header(
            "write",
            read={"ACC-1"},
            write={"ACC-1"},
            subject="SA-01JAD3R5N8M0000000000000A",
            display_name="Breaks sweep",
            tool_name="close_cleared_breaks",
            roles=["operations"],
            subject_kind=SERVICE_ACCOUNT,
            owner_subject="local|ada",
        )
    )
    assert account.subject_kind == SERVICE_ACCOUNT
    assert account.subject == "SA-01JAD3R5N8M0000000000000A"
    assert account.owner_subject == "local|ada"
    assert not account.through_a_client, "a service account acts on no delegation"
    assert account.write_for("operations") == {"ACC-1"}


# ── An act called as the role's service account ──────────────────────────────


async def test_an_act_called_as_the_service_account_is_sent_as_the_plugin_and_made(
    operations_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, plugin = operations_plugin
    service.service_account_answer = sidecar_pb2.CallAsServiceAccountReply(
        outcome="made",
        answer_json='{"outcome":"made","data":{"entry_id":"ENT-7","closed":1}}',
    )
    async with meridian.runs_as("operations") as act:
        reply = await act("close_cleared_breaks", CLOSE, reason=WHY)

    assert reply.outcome == "made"
    assert json.loads(reply.answer_json)["data"]["closed"] == 1
    assert reply.prepared_call_id == ""
    ((sent, carried),) = service.service_account_calls
    assert carried == "", "no person is behind the call: it carries no meridian-caller"
    assert sent.role == "operations"
    assert sent.tool_name == "close_cleared_breaks"
    assert json.loads(sent.arguments_json) == CLOSE
    assert sent.reason == WHY


async def test_an_act_held_to_preparing_answers_its_prepared_change(
    operations_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, plugin = operations_plugin
    service.service_account_answer = sidecar_pb2.CallAsServiceAccountReply(
        outcome="prepared", prepared_call_id="PC-01JAD3R5N8M00000000000001"
    )
    async with meridian.runs_as("operations", plugin=plugin) as act:
        reply = await act("close_cleared_breaks", CLOSE, reason=WHY)
    assert (reply.outcome, reply.prepared_call_id) == (
        "prepared",
        "PC-01JAD3R5N8M00000000000001",
    )
    assert reply.answer_json == ""


@dataclass(frozen=True)
class Close:
    account_id: str
    break_ids: list[str] = field(default_factory=list)
    difference: Decimal | None = None


async def test_the_acts_typed_record_is_sent_as_its_json(
    operations_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, _ = operations_plugin
    async with meridian.runs_as("operations") as act:
        await act(
            "close_cleared_breaks",
            Close("ACC-1", ["BRK-1"], Decimal("0.00")),
            reason=WHY,
        )
        await act("close_cleared_breaks", '{"account_id": "ACC-2"}', reason=WHY)
    first, second = (sent for sent, _ in service.service_account_calls)
    # A Decimal as its string, as a tool's call sends it.
    assert (
        first.arguments_json
        == '{"account_id":"ACC-1","break_ids":["BRK-1"],"difference":"0.00"}'
    )
    assert second.arguments_json == '{"account_id": "ACC-2"}'


@pytest.mark.parametrize(
    ("status", "fields", "raised", "kind"),
    [
        (grpc.StatusCode.FAILED_PRECONDITION, ("role",), CallFailed, "refused"),
        (grpc.StatusCode.PERMISSION_DENIED, ("role",), NotGranted, None),
        (grpc.StatusCode.PERMISSION_DENIED, ("tool_name",), NotGranted, None),
        (grpc.StatusCode.FAILED_PRECONDITION, ("tool_name",), CallFailed, "refused"),
        (grpc.StatusCode.INVALID_ARGUMENT, ("tool_name",), CallFailed, "invalid"),
        (grpc.StatusCode.INVALID_ARGUMENT, ("reason",), CallFailed, "invalid"),
    ],
)
async def test_a_refusal_keeps_its_status_and_names_its_field(
    operations_plugin: tuple[FakeSidecar, meridian.Plugin],
    status: grpc.StatusCode,
    fields: tuple[str, ...],
    raised: type[Exception],
    kind: str | None,
) -> None:
    service, _ = operations_plugin
    words = f"{fields[0]}: the dashboard's words"
    service.service_account_answer = (status, words, fields)
    async with meridian.runs_as("operations") as act:
        with pytest.raises(raised) as refused:
            await act("close_cleared_breaks", CLOSE, reason=WHY)
    assert refused.value.fields == fields  # type: ignore[attr-defined]
    assert words in str(refused.value)
    assert isinstance(refused.value.__cause__, grpc.aio.AioRpcError)
    assert refused.value.__cause__.code() is status
    if kind is not None:
        assert refused.value.kind == kind  # type: ignore[attr-defined]


async def test_no_service_account_chosen_for_the_role_is_refused_saying_so(
    operations_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, _ = operations_plugin
    service.service_account_answer = (
        grpc.StatusCode.FAILED_PRECONDITION,
        "role: operations runs as no service account; its admin chooses one on the "
        "plugin's Access tab",
        ("role",),
    )
    async with meridian.runs_as("operations") as act:
        with pytest.raises(CallFailed, match="runs as no service account") as refused:
            await act("close_cleared_breaks", CLOSE, reason=WHY)
    assert (refused.value.kind, refused.value.fields) == ("refused", ("role",))


async def test_an_older_sidecar_is_said_to_be_older_than_v21(
    operations_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, _ = operations_plugin
    service.older_than_v21 = True
    async with meridian.runs_as("operations") as act:
        with pytest.raises(CallFailed, match="older than contract v21") as refused:
            await act("close_cleared_breaks", CLOSE, reason=WHY)
    assert refused.value.kind == "unimplemented"


@pytest.mark.parametrize(
    ("tool_name", "arguments", "reason", "said"),
    [
        ("", CLOSE, WHY, "tool_name is empty"),
        ("x" * 62, CLOSE, WHY, "tool_name is 62 characters"),
        ("dashboard__make_prepared", CLOSE, WHY, "a core tool"),
        ("close_cleared_breaks", CLOSE, "", "reason is empty"),
        ("close_cleared_breaks", CLOSE, "x" * 4001, "reason is 4001 characters"),
        ("close_cleared_breaks", "[1, 2]", WHY, "not a JSON object"),
        ("close_cleared_breaks", "{not json", WHY, "not a JSON object"),
    ],
)
async def test_what_the_sidecar_would_refuse_by_its_bounds_is_refused_first(
    operations_plugin: tuple[FakeSidecar, meridian.Plugin],
    tool_name: str,
    arguments: object,
    reason: str,
    said: str,
) -> None:
    service, _ = operations_plugin
    async with meridian.runs_as("operations") as act:
        with pytest.raises(ValueError, match=said):
            await act(tool_name, arguments, reason=reason)
    assert service.service_account_calls == []


async def test_a_role_the_plugin_does_not_hold_is_refused_before_anything_is_sent(
    operations_plugin: tuple[FakeSidecar, meridian.Plugin],
) -> None:
    service, _ = operations_plugin
    with pytest.raises(
        ValueError, match="operations-1 was not launched with; it holds operations"
    ):
        async with meridian.runs_as("custody"):
            pass
    assert service.service_account_calls == []


async def test_it_calls_only_inside_its_block_and_beside_a_registered_plugin(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.roles = ("operations",)
    plugin = await meridian.connect(address, heartbeat=False)
    entered = meridian.runs_as("operations")
    async with entered as act:
        pass
    with pytest.raises(NotRegistered, match="only inside its block"):
        await act("close_cleared_breaks", CLOSE, reason=WHY)
    await plugin.leave()
    with pytest.raises(NotRegistered, match="connect first"):
        async with meridian.runs_as("operations"):
            pass
    with pytest.raises(NotRegistered, match="has left"):
        async with meridian.runs_as("operations", plugin=plugin):
            pass


# ── A route reached for a service account's call ─────────────────────────────


@dataclass(frozen=True)
class Clearing:
    account_id: str
    break_ids: list[str] = field(default_factory=list)
    reason: str = ""


def sweep_pages(sent: list[dict[str, object]]) -> meridian.Pages:
    pages = meridian.Pages("Operations")

    @pages.route(
        "/breaks/check",
        levels="write",
        methods=["POST"],
        params=Clearing,
        reads=True,
        name="check_close_cleared_breaks",
    )
    async def check(request: meridian.Request) -> meridian.Response:
        return pages.answer("x.html", request.params)

    @pages.route(
        "/breaks/close",
        levels="write",
        methods=["POST"],
        params=Clearing,
        name="close_cleared_breaks",
        checked_by="check_close_cleared_breaks",
        accounts=["account_id"],
        made_on="",
    )
    async def close(request: meridian.Request) -> meridian.Response:
        # As for a person: the request's assertion handed back as acting_for.
        await request.plugin.close_breaks_as_cleared(
            account_id=request.params.account_id,
            break_ids=request.params.break_ids,
            reason=request.params.reason,
            acting_for=request.caller.header,
        )
        sent.append(
            {
                "kind": request.caller.subject_kind,
                "owner": request.caller.owner_subject,
                "subject": request.caller.subject,
            }
        )
        return pages.answer("x.html", request.params)

    return pages


async def test_a_route_reached_for_a_service_account_acts_as_for_a_person(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.roles = ("operations",)
    seen: list[dict[str, object]] = []
    pages = sweep_pages(seen)
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        header = caller_header(
            "write",
            read={"ACC-1"},
            write={"ACC-1"},
            subject="SA-01JAD3R5N8M0000000000000A",
            display_name="Breaks sweep",
            tool_name="close_cleared_breaks",
            subject_kind=SERVICE_ACCOUNT,
            owner_subject="local|ada",
        )
        body = json.dumps({"account_id": "ACC-1", "break_ids": ["BRK-2"], "reason": WHY})
        answer = await pages.dispatch(
            Request(
                "POST",
                "/breaks/close",
                Caller.from_header(header),
                plugin,
                body=body.encode(),
                headers={"content-type": "application/json"},
            )
        )
    finally:
        await plugin.leave()

    assert answer.status == 200, answer.text
    assert seen == [
        {
            "kind": SERVICE_ACCOUNT,
            "owner": "local|ada",
            "subject": "SA-01JAD3R5N8M0000000000000A",
        }
    ]
    (closed,) = (
        s for s in service.operations.sent if type(s).__name__.startswith("CloseBreaks")
    )
    claims = sidecar_pb2.CallerClaims.FromString(closed.acting_for.claims)  # type: ignore[attr-defined]
    assert claims.subject_kind == SERVICE_ACCOUNT
    assert claims.owner_subject == "local|ada"
    assert claims.delegation_id == "" and claims.client_name == ""


def test_a_plugins_own_test_calls_an_act_as_a_service_account() -> None:
    seen: list[dict[str, object]] = []

    class Book:
        sent: list[dict[str, object]] = []

        async def close_breaks_as_cleared(self, **given: object) -> None:
            self.sent.append(given)

    book = Book()
    client = PageClient(sweep_pages(seen), plugin=book, read={"ACC-1"}, write={"ACC-1"})
    answer = client.call_tool(
        "close_cleared_breaks",
        {"account_id": "ACC-1", "break_ids": ["BRK-2"], "reason": WHY},
        subject="SA-01JAD3R5N8M0000000000000A",
        subject_kind=SERVICE_ACCOUNT,
        owner_subject="local|ada",
    )
    assert answer.outcome == "made", answer.json
    assert seen[0]["kind"] == SERVICE_ACCOUNT
    acting_for = Caller.from_header(str(book.sent[0]["acting_for"]))
    assert acting_for.subject == "SA-01JAD3R5N8M0000000000000A"
    assert acting_for.owner_subject == "local|ada"
    assert not acting_for.through_a_client and acting_for.client_name == ""
