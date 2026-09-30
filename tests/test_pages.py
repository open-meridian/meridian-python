"""A plugin's pages, declared and enforced in one place (W4.8, W6.9).

What this SDK decides here is small and worth pinning: which declarations
registration sends, that a page's view never runs in a session at a level the
page does not serve, and that what a template shows is escaped. Who may open a
session at which level is the dashboard's, and what a session may do is the
sidecar's; neither is repeated here.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

import meridian
from meridian import Pages, Request, Response
from meridian.pages import Markup
from meridian.testing import LEVELS, PageClient, caller_header
from meridian.v1 import sidecar_pb2

ADMIN = sidecar_pb2.ACCESS_LEVEL_ADMIN
WRITE = sidecar_pb2.ACCESS_LEVEL_WRITE
READ = sidecar_pb2.ACCESS_LEVEL_READ


@pytest.fixture
def templates(tmp_path: Path) -> Path:
    (tmp_path / "accounts.html").write_text(
        '{% extends "meridian/base.html" %}\n'
        '{% block status %}<om-status data-om-header state="ok" label="Synced">'
        "</om-status>{% endblock %}\n"
        '{% block head_actions %}{% if level == "write" %}{% include "action.html" %}'
        "{% endif %}{% endblock %}\n"
        '{% block content %}<section class="panel"><p>{{ caller.display_name }}, at '
        '{{ level }}.</p><om-grid><script type="application/json">{{ grid | tojson }}'
        "</script></om-grid></section>{% endblock %}\n"
    )
    (tmp_path / "action.html").write_text(
        '<form method="post" action="/act"><button data-om-action="act">Act</button></form>'
    )
    (tmp_path / "setup.html").write_text(
        '{% extends "meridian/base.html" %}\n'
        "{% block content %}<p>Setup for {{ caller.subject }}: {{ note }}</p>{% endblock %}\n"
    )
    return tmp_path


def build(templates: Path) -> Pages:
    pages = Pages("Ledger", templates=templates)

    @pages.page("/", "Accounts", levels=["write", "read"])
    def accounts(request: Request) -> str:
        grid = {"rows": [{"account": a} for a in sorted(request.caller.read)]}
        return pages.render("accounts.html", grid=grid)

    @pages.page("/setup", "Setup", levels="admin")
    async def setup(request: Request) -> str:
        await asyncio.sleep(0)
        return pages.render("setup.html", note=request.query.get("note", "none"))

    @pages.route("/act", levels=["write"], methods=["POST"])
    def act(request: Request) -> Response:
        return Response(f"acted on {request.form.get('account', '')}", 200, "text/plain")

    return pages


# ── Declared ─────────────────────────────────────────────────────────────


def test_the_tabs_are_declared_in_order_and_routes_are_not(templates: Path) -> None:
    pages = build(templates)
    assert [(p.path, p.title, p.levels) for p in pages.declared] == [
        ("/", "Accounts", (WRITE, READ)),
        ("/setup", "Setup", (ADMIN,)),
    ]
    declared = meridian.Interface(8000, "Ledger", pages=pages)._declared()
    assert [(p.path, list(p.levels)) for p in declared.pages] == [
        ("/", [WRITE, READ]),
        ("/setup", [ADMIN]),
    ]


def test_a_declaration_the_contract_refuses_is_refused_where_it_is_written(
    templates: Path,
) -> None:
    pages = Pages(templates=templates)
    with pytest.raises(ValueError, match="names no level"):
        pages.page("/", "Home", levels=[])
    with pytest.raises(ValueError, match="begin it with /"):
        pages.page("home", "Home", levels="read")
    with pytest.raises(ValueError, match="names no level"):
        pages.route("/x", levels=())
    with pytest.raises(ValueError, match="AccessLevel does not define"):
        pages.route("/x", levels=["owner"])

    @pages.page("/", "Home", levels="read")
    def home(request: Request) -> str:
        return ""

    with pytest.raises(ValueError, match="GET / is declared twice"):
        pages.route("/", levels="admin")
    with pytest.raises(FileNotFoundError, match="templates"):
        Pages(templates=templates / "nowhere")


# ── Enforced ─────────────────────────────────────────────────────────────


def test_each_page_is_served_at_its_levels_and_refused_at_the_others(templates: Path) -> None:
    served = {
        (r.page.path, r.level): r.response.status
        for r in PageClient(build(templates)).every_page()
    }
    assert served == {
        ("/", "admin"): 403,
        ("/", "write"): 200,
        ("/", "read"): 200,
        ("/setup", "admin"): 200,
        ("/setup", "write"): 403,
        ("/setup", "read"): 403,
    }


def test_the_view_never_runs_for_a_level_it_does_not_serve(templates: Path) -> None:
    pages = Pages(templates=templates)
    ran: list[int] = []

    @pages.route("/act", levels="write", methods=["POST"])
    def act(request: Request) -> str:
        ran.append(request.caller.level)
        return "done"

    client = PageClient(pages)
    for level in ("admin", "read", ""):
        assert client.post("/act", level).status == 403
    assert ran == []
    refused = client.post("/act", "read")
    assert refused.text == "/act is not served under View; it is for Open."
    assert "holds nothing" in client.post("/act", "").text
    assert client.post("/act", "write").text == "done" and ran == [WRITE]


def test_the_wrapped_view_refuses_when_called_directly_too(templates: Path) -> None:
    pages = Pages(templates=templates)

    @pages.page("/", "Home", levels="admin")
    def home(request: Request) -> str:
        return "configuration"

    request = Request(
        "GET",
        "/",
        meridian.Caller.from_header(caller_header("read")),
        plugin=None,  # type: ignore[arg-type]
    )
    assert asyncio.run(home(request)).status == 403


def test_no_such_page_and_no_such_method_are_said(templates: Path) -> None:
    client = PageClient(build(templates))
    assert client.get("/nowhere", "write").status == 404
    answered = client.request("POST", "/", "write")
    assert answered.status == 405 and ("allow", "GET") in answered.headers


# ── Rendered ─────────────────────────────────────────────────────────────


def test_a_page_is_wrapped_in_the_kits_base_template(templates: Path) -> None:
    text = PageClient(build(templates), read={"ACC-1"}).get("/", "read").text
    assert text.startswith("<!doctype html>")
    assert '<link rel="stylesheet" href="/.meridian/ui/0.7.0/meridian.css">' in text
    assert '<script src="/.meridian/ui/0.7.0/meridian.js"></script>' in text
    assert "<title>Accounts · Ledger</title>" in text
    assert '<main class="page">' in text and "<h1>Ledger</h1>" in text
    assert "Ada Park, at read." in text


def test_the_tab_row_is_the_pages_at_the_sessions_level(templates: Path) -> None:
    pages = build(templates)

    @pages.page("/history", "History", levels="read")
    def history(request: Request) -> str:
        return pages.render("setup.html", note="")

    client = PageClient(pages)
    under_view = client.get("/", "read").text
    assert (
        '<nav class="tabs">\n<a class="tab on" href="/" aria-current="page">Accounts</a>\n'
        '<a class="tab" href="/history">History</a>\n</nav>'
    ) in under_view
    # One page at the level is no row to choose from; Setup is never shown.
    assert '<nav class="tabs">' not in client.get("/", "write").text
    assert "/setup" not in under_view


def test_what_a_template_shows_is_escaped_and_its_data_cannot_close_its_script(
    templates: Path,
) -> None:
    hostile = "</script><b>x"
    client = PageClient(build(templates), read={hostile}, display_name="Ada <Park>")
    text = client.get("/", "read").text
    assert "Ada &lt;Park&gt;" in text and "<b>x" not in text
    data = text.split('<script type="application/json">')[1].split("</script>")[0]
    assert json.loads(data) == {"rows": [{"account": hostile}]}
    # An include is a template too; this one only under Open.
    assert '<form method="post" action="/act">' in client.get("/", "write").text
    assert "<form" not in text


def test_the_head_hands_the_frame_its_status_and_actions(templates: Path) -> None:
    client = PageClient(build(templates))
    head = client.get("/", "write").text.split('<header class="page-head">')[1]
    head = head.split("</header>")[0]
    assert '<om-status data-om-header state="ok" label="Synced"></om-status>' in head
    assert (
        '<div class="actions"><form method="post" action="/act">'
        '<button data-om-action="act">Act</button></form></div>'
    ) in head
    # No actions, no .actions: a head with only its heading the kit drops, framed.
    assert '<div class="actions">' not in client.get("/", "read").text
    assert '<div class="actions">' not in client.get("/setup", "admin").text


def test_the_context_carries_the_caller_and_the_level_and_the_request(templates: Path) -> None:
    text = (
        PageClient(build(templates), subject="local|bo").get("/setup", "admin", note="<n>").text
    )
    assert "Setup for local|bo: &lt;n&gt;" in text


def test_render_outside_a_view_says_where_it_belongs(templates: Path) -> None:
    with pytest.raises(RuntimeError, match="called from a view"):
        build(templates).render("setup.html")


def test_markup_a_view_built_goes_in_as_it_is(templates: Path) -> None:
    pages = Pages(templates=templates)

    @pages.page("/", "Home", levels="read")
    def home(request: Request) -> str:
        return pages.render("setup.html", note=Markup("<b>ok</b>"))

    assert "Setup for local|ada: <b>ok</b>" in PageClient(pages).get("/", "read").text


def test_a_view_answering_something_else_is_said(templates: Path) -> None:
    pages = Pages(templates=templates)

    @pages.page("/", "Home", levels="read")
    def home(request: Request) -> Any:
        return None

    with pytest.raises(TypeError, match="answered a NoneType"):
        PageClient(pages).get("/", "read")


# ── Served ───────────────────────────────────────────────────────────────


async def asgi(pages: Pages, headers: list[tuple[bytes, bytes]], **scope: Any) -> list[Any]:
    sent: list[Any] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": scope.pop("body", b"")}

    async def send(message: Any) -> None:
        sent.append(message)

    await pages.app(plugin=None)(
        {"type": "http", "method": "GET", "path": "/", "headers": headers, **scope},
        receive,
        send,
    )
    return sent


async def test_the_asgi_app_reads_the_caller_and_refuses_without_one(templates: Path) -> None:
    pages = build(templates)
    assert (await asgi(pages, []))[0]["status"] == 401
    header = caller_header("read", read={"ACC-1"}).encode()
    sent = await asgi(pages, [(b"meridian-caller", header)])
    assert sent[0]["status"] == 200 and b"ACC-1" in sent[1]["body"]
    writer = caller_header("write")
    token = pages.csrf_token(meridian.Caller.from_header(writer))
    posted = await asgi(
        pages,
        [
            (b"meridian-caller", writer.encode()),
            (b"content-type", b"application/x-www-form-urlencoded"),
        ],
        method="POST",
        path="/act",
        body=f"account=ACC-9&csrf={token}".encode(),
    )
    assert posted[1]["body"] == b"acted on ACC-9"


async def test_a_view_that_fails_is_answered_500_and_logged(
    templates: Path, caplog: pytest.LogCaptureFixture
) -> None:
    pages = Pages(templates=templates)

    @pages.page("/", "Home", levels="read")
    def home(request: Request) -> str:
        raise KeyError("boom")

    sent = await asgi(pages, [(b"meridian-caller", caller_header("read").encode())])
    assert sent[0]["status"] == 500 and b"boom" not in sent[1]["body"]
    assert "GET / failed" in caplog.text


async def test_the_standard_librarys_server_serves_the_pages(templates: Path) -> None:
    pages = build(templates)
    server = pages.serve(plugin=None, port=0)  # type: ignore[arg-type]
    address = f"http://127.0.0.1:{server.server_address[1]}"

    def ask(path: str, header: str | None, data: bytes | None = None) -> tuple[int, str]:
        request = urllib.request.Request(address + path, data=data)
        if header is not None:
            request.add_header("Meridian-Caller", header)
        try:
            with urllib.request.urlopen(request, timeout=10) as answer:
                return answer.status, answer.read().decode()
        except urllib.error.HTTPError as answer:
            return answer.code, answer.read().decode()

    try:
        without = await asyncio.to_thread(ask, "/", None)
        viewing = await asyncio.to_thread(ask, "/", caller_header("read", read={"ACC-7"}))
        refused = await asyncio.to_thread(ask, "/setup", caller_header("read"))
        writer = caller_header("write")
        token = pages.csrf_token(meridian.Caller.from_header(writer))
        acted = await asyncio.to_thread(
            ask, "/act", writer, f"account=ACC-7&csrf={token}".encode()
        )
        forged = await asyncio.to_thread(ask, "/act", writer, b"account=ACC-7")
    finally:
        server.shutdown()
        server.server_close()
    assert without[0] == 401
    assert viewing[0] == 200 and "ACC-7" in viewing[1]
    assert refused[0] == 403
    assert acted == (200, "acted on ACC-7")
    assert forged[0] == 403


# ── The test client ──────────────────────────────────────────────────────


def test_a_session_carries_the_accounts_cut_to_its_level() -> None:
    def read(level: str) -> meridian.Caller:
        return meridian.Caller.from_header(caller_header(level, read={"A"}, write={"B"}))

    assert read("write").read == {"A", "B"} and read("write").write == {"B"}
    assert read("read").read == {"A", "B"} and read("read").write == frozenset()
    assert read("admin").read == frozenset() and read("admin").write == frozenset()
    assert read("admin").admin and read("admin").level == ADMIN
    assert LEVELS == ("admin", "write", "read")


def test_account_data_on_a_page_at_admin_fails_the_plugins_test(templates: Path) -> None:
    held = {"ACC-1": "Growth fund"}  # what the plugin holds for itself
    pages = build(templates)

    @pages.page("/leaky", "Leaky", levels="admin")
    def leaky(request: Request) -> str:
        return pages.render("setup.html", note=", ".join(held.values()))

    client = PageClient(pages, read={"ACC-1"}, write={"ACC-1"})
    with pytest.raises(
        AssertionError, match="/leaky shows account data under Manage: Growth fund"
    ):
        client.assert_no_account_data("Growth fund")
    # The same page, account agnostic, passes; Setup never showed any.
    held.clear()
    client.assert_no_account_data("Growth fund")


# ── Cross-site requests ──────────────────────────────────────────────────


def test_a_request_that_changes_something_carries_this_pages_token(templates: Path) -> None:
    pages = build(templates)
    client = PageClient(pages, subject="local|ada")
    ada = client.caller("write")
    token = pages.csrf_token(ada)
    # Refused before the view runs: none, a wrong one, another person's, the
    # same person's at another level, another process's.
    ben = PageClient(pages, subject="local|ben").caller("write")
    elsewhere = Pages(templates=templates).csrf_token(ada)
    for form in (
        {},
        {"csrf": ""},
        {"csrf": "not-a-token-é"},
        {"csrf": pages.csrf_token(ben)},
        {"csrf": pages.csrf_token(client.caller("read"))},
        {"csrf": elsewhere},
    ):
        refused = client.request("POST", "/act", "write", form={**form, "account": "A"})
        assert refused.status == 403 and "Reload the page" in refused.text, form
    # Taken in the form, or in the header a script sends; the same every time.
    assert client.request("POST", "/act", "write", form={"csrf": token}).status == 200
    assert (
        client.request("POST", "/act", "write", headers={"X-CSRF-Token": token}).status == 200
    )
    assert pages.csrf_token(client.caller("write")) == token
    assert client.post("/act", "write").status == 200


def test_every_template_and_view_has_the_token(templates: Path) -> None:
    (templates / "form.html").write_text(
        '<form method="post" action="/act">{{ csrf_input }}</form>{{ csrf_token }}'
    )
    pages = Pages(templates=templates)
    seen: list[str] = []

    @pages.page("/", "Home", levels="write")
    def home(request: Request) -> str:
        seen.append(request.csrf_token)
        return pages.render("form.html")

    client = PageClient(pages)
    token = pages.csrf_token(client.caller("write"))
    text = client.get("/", "write").text
    field = f'<input type="hidden" name="csrf" value="{token}">'
    assert text == f'<form method="post" action="/act">{field}</form>{token}'
    assert seen == [token]
