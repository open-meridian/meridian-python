"""A route's typed record, and the tool derived from it (contract v12;
spec/a-deployment-serves-its-mcp, requirements 6 to 16).

What this SDK decides: one record read alike from a form and from a tool's
JSON, by the same paths; a decimal never a JSON number; the form token
skipped only for a call whose claims name the tool; an answer that renders
for a browser and is data for a tool; a refusal by path; and the tools
registration declares. Which tools a person sees, and at which level a call
opens, are the dashboard's; that a tool's claim reaches no other route is
the sidecar's.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import meridian
from meridian import params
from meridian.dictionary import entry
from meridian.pages import Field, Pages, Refusal
from meridian.testing import PageClient
from meridian.v1 import sidecar_pb2


@dataclass(frozen=True)
class Lot:
    quantity: Decimal
    cost: Decimal | None = None
    acquired: date | None = None
    source: str = ""


@dataclass(frozen=True)
class Position:
    settled: Decimal | None = None
    lots: list[Lot] = field(default_factory=list)


@dataclass(frozen=True)
class Confirmation:
    account: str
    reason: str = ""
    positions: list[Position] = field(default_factory=list)


@dataclass(frozen=True)
class Recorded:
    account: str
    positions: int


@dataclass(frozen=True)
class Asked:
    account: str


@pytest.fixture
def pages(tmp_path: Path) -> Pages:
    (tmp_path / "done.html").write_text(
        '{% extends "meridian/base.html" %}{% block content %}'
        "<p>Recorded {{ data.positions }} for {{ data.account }}.</p>{% endblock %}"
    )
    built = Pages("Desk", templates=tmp_path)

    @built.page(
        "/opening",
        "Opening",
        levels=["write", "read"],
        answers=Recorded,
        params=Asked,
        name="read_opening",
    )
    async def opening(request: meridian.Request) -> meridian.Response:
        """Each account's opening balance."""
        return built.answer("done.html", Recorded(request.params.account, 0))

    @built.route("/confirm", levels="write", methods=["POST"], params=Confirmation)
    async def confirm(request: meridian.Request) -> meridian.Response:
        """Record the account's opening balance.

        More words the description leaves out."""
        record = request.params
        if record is None or request.param_errors:
            built.refuse(
                "not readable", *(Field(p.path, p.message) for p in request.param_errors)
            )
        if not record.reason:
            built.refuse("Give a reason.", ("reason", "required to confirm"))
        return built.answer("done.html", Recorded(record.account, len(record.positions)))

    @built.route(
        "/check",
        levels="write",
        methods=["POST"],
        params=Confirmation,
        reads=True,
        name="check_opening",
    )
    async def check(request: meridian.Request) -> meridian.Response:
        return built.answer("done.html", Recorded(request.params.account, -1))

    @built.route(
        "/legacy",
        levels="write",
        methods=["POST"],
        tool=False,
        why="posts a file a person chooses",
    )
    async def legacy(request: meridian.Request) -> str:
        return "ok"

    return built


ARGUMENTS = {
    "account": "ACC-1",
    "reason": "Checked.",
    "positions": [
        {
            "settled": "100",
            "lots": [{"quantity": "100", "cost": "1500.25", "acquired": "2026-01-02"}],
        }
    ],
}


def test_a_record_reads_alike_from_a_form_and_from_json() -> None:
    form = {
        "account": "ACC-1",
        "reason": "Checked.",
        "positions[0].settled": "100",
        "positions[0].lots[0].quantity": "100",
        "positions[0].lots[0].cost": "1500.25",
        "positions[0].lots[0].acquired": "2026-01-02",
        # A blank row, as a page's plain table posts it, is no row.
        "positions[0].lots[1].quantity": "",
        "csrf": "token",
        "do": "check",
    }
    from_form, problems = params.from_form(Confirmation, form)
    assert problems == ()
    assert from_form == params.from_json(Confirmation, ARGUMENTS)
    assert from_form.positions[0].lots[0].cost == Decimal("1500.25")
    assert from_form.positions[0].lots[0].acquired == date(2026, 1, 2)


def test_the_same_fault_has_the_same_path_in_a_form_and_in_json() -> None:
    _, problems = params.from_form(
        Confirmation,
        {
            "account": "A",
            "positions[3].lots[0].quantity": "1",
            "positions[3].lots[0].cost": "1,5",
        },
    )
    # Rows are numbered as read: the form's fourth position is the only one.
    assert [p.path for p in problems] == ["positions[0].lots[0].cost"]
    with pytest.raises(params.Unread) as unread:
        params.from_json(
            Confirmation,
            {"account": "A", "positions": [{"lots": [{"quantity": "1", "cost": "1,5"}]}]},
        )
    assert [p.path for p in unread.value.problems] == ["positions[0].lots[0].cost"]


def test_a_decimal_is_a_string_never_a_json_number_and_an_unknown_argument_is_named() -> None:
    with pytest.raises(params.Unread) as unread:
        params.from_json(
            Confirmation, {"account": "A", "colour": "red", "positions": [{"settled": 100.5}]}
        )
    said = {p.path: p.message for p in unread.value.problems}
    assert "never a JSON number" in said["positions[0].settled"]
    assert "colour" in said


def test_the_schema_says_decimals_are_strings_and_what_is_required() -> None:
    schema = params.schema(Confirmation)
    assert schema["required"] == ["account"]
    assert schema["additionalProperties"] is False
    lot = schema["properties"]["positions"]["items"]["properties"]["lots"]["items"]
    cost = lot["properties"]["cost"]["anyOf"][0]
    assert cost["type"] == "string" and cost["format"] == "decimal"


def test_registration_declares_a_tool_for_each_typed_route(pages: Pages) -> None:
    tools = {tool.name: tool for tool in pages.tools}
    assert set(tools) == {"read_opening", "confirm", "check_opening"}
    confirm = tools["confirm"].declared()
    assert (confirm.method, confirm.path, confirm.reads) == ("POST", "/confirm", False)
    assert confirm.description == "Record the account's opening balance."
    assert list(confirm.levels) == [sidecar_pb2.ACCESS_LEVEL_WRITE]
    assert json.loads(confirm.input_schema)["required"] == ["account"]
    assert confirm.output_schema == ""
    assert tools["check_opening"].reads and tools["read_opening"].reads
    assert json.loads(tools["read_opening"].declared().output_schema)["required"] == [
        "account",
        "positions",
    ]
    assert [(n.method, n.path) for n in pages.not_offered] == [("POST", "/legacy")]


def test_a_route_not_offered_says_why() -> None:
    built = Pages("Desk")
    with pytest.raises(ValueError, match="why"):
        built.route("/x", levels="write", methods=["POST"], tool=False)


def test_a_tool_call_needs_no_form_token_and_answers_data(pages: Pages) -> None:
    client = PageClient(pages, read={"ACC-1"}, write={"ACC-1"})
    answered = client.call_tool("confirm", ARGUMENTS)
    assert answered.status == 200
    assert answered.outcome == "made"
    assert answered.data == {"account": "ACC-1", "positions": 1}
    assert answered.level == "write"
    read = client.call_tool("read_opening", {"account": "ACC-1"})
    assert (read.outcome, read.level) == ("unchanged", "write")


def test_a_browser_still_needs_its_form_token_and_gets_the_page(pages: Pages) -> None:
    client = PageClient(pages, read={"ACC-1"}, write={"ACC-1"})
    form = {"account": "ACC-1", "reason": "Checked."}
    assert client.request("POST", "/confirm", "write", form=form).status == 403
    page = client.post("/confirm", "write", form)
    assert page.status == 200
    assert "Recorded 0 for ACC-1." in page.text


def test_a_tool_call_refused_by_path_never_reaches_the_view(pages: Pages) -> None:
    client = PageClient(pages, read={"ACC-1"}, write={"ACC-1"})
    answered = client.call_tool("confirm", {"account": "ACC-1", "positions": [{"settled": 1}]})
    assert answered.status == 422
    assert answered.outcome == "refused"
    assert answered.paths == ["positions[0].settled"]
    bad = client.call_tool("confirm", body=b"not json")
    assert bad.status == 422 and bad.json["reason"] == "invalid_arguments"


def test_a_views_refusal_names_its_field_for_a_tool_and_in_words_for_a_browser(
    pages: Pages,
) -> None:
    client = PageClient(pages, read={"ACC-1"}, write={"ACC-1"})
    answered = client.call_tool("confirm", {"account": "ACC-1"})
    assert answered.status == 422
    assert answered.json["fields"] == [{"path": "reason", "message": "required to confirm"}]
    page = client.post("/confirm", "write", {"account": "ACC-1"})
    assert page.status == 422 and "reason: required to confirm" in page.text


def test_a_tool_claim_at_another_route_is_refused(pages: Pages) -> None:
    from meridian.pages import Request
    from meridian.testing import caller_header

    client = PageClient(pages, write={"ACC-1"})
    header = caller_header("write", write={"ACC-1"}, tool_name="confirm")
    request = Request(
        method="POST",
        path="/check",
        caller=meridian.Caller.from_header(header),
        plugin=None,
        body=json.dumps(ARGUMENTS).encode(),
        headers={"content-type": "application/json"},
    )
    import asyncio

    answer = asyncio.run(client.pages.dispatch(request))
    assert answer.status == 403
    assert json.loads(answer.text)["reason"] == "not_this_tool"


def test_a_tool_answering_a_page_is_refused_as_untyped(tmp_path: Path) -> None:
    built = Pages("Desk")

    @built.route("/act", levels="write", methods=["POST"], params=Asked)
    async def act(request: meridian.Request) -> str:
        return "<p>done</p>"

    answered = PageClient(built, write={"A"}).call_tool("act", {"account": "A"})
    assert answered.status == 500 and answered.json["reason"] == "untyped_answer"


def test_a_tool_may_replace_a_derived_one_at_its_route(pages: Pages) -> None:
    @pages.tool(replaces="/confirm", params=Asked, name="confirm_simply")
    async def simply(request: meridian.Request) -> meridian.Response:
        return pages.answer("done.html", Recorded(request.params.account, 99))

    names = [tool.name for tool in pages.tools]
    assert "confirm" not in names and "confirm_simply" in names
    client = PageClient(pages, write={"ACC-1"})
    assert client.call_tool("confirm_simply", {"account": "ACC-1"}).data["positions"] == 99
    # The browser's form still reaches the route's own view.
    assert client.post("/confirm", "write", {"account": "ACC-1", "reason": "r"}).status == 200


def test_a_book_refusals_path_resolves_to_its_dictionary_entry() -> None:
    found = entry("RecordOpeningBalance", "positions[2].instrument.asset_class")
    assert found is not None
    assert found["name"] == "meridian.v1.InstrumentRecord.asset_class"
    said = Field.of("positions[2].instrument.asset_class", operation="RecordOpeningBalance")
    assert said.entry == "meridian.v1.InstrumentRecord.asset_class" and said.said
    assert entry("RecordOpeningBalance", "positions[0].nothing_here") is None
    assert Refusal("x", [said]).to_json()["fields"][0]["entry"] == said.entry
