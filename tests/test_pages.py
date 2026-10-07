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
    assert answered.status == 405 and ("allow", "GET, HEAD") in answered.headers
    head = client.request("HEAD", "/act", "write")
    assert head.status == 405 and ("allow", "POST") in head.headers and head.body == b""


def test_head_is_answered_for_every_get_page_with_its_headers_and_no_body(
    templates: Path,
) -> None:
    pages = build(templates)
    methods: list[str] = []

    @pages.route("/report.csv", levels="read")
    def report(request: Request) -> Response:
        methods.append(request.method)
        return Response("a,b\n1,2\n", content_type="text/csv", headers=(("x-rows", "1"),))

    client = PageClient(pages, read={"ACC-1"})
    got = client.get("/", "read")
    head = client.request("HEAD", "/", "read")
    assert head.status == 200 and head.body == b"" and head.content_type == got.content_type
    assert head.headers == (("content-length", str(len(got.text.encode()))),)
    # The GET view ran, told it was HEAD; a route's own headers are kept.
    head = client.request("HEAD", "/report.csv", "read")
    assert methods == ["HEAD"] and head.body == b""
    assert head.headers == (("x-rows", "1"), ("content-length", "8"))
    # Refused as GET is, at a level the page does not serve, and still bodiless.
    refused = client.request("HEAD", "/setup", "read")
    assert refused.status == 403 and refused.body == b""


# ── Rendered ─────────────────────────────────────────────────────────────


def test_a_page_is_wrapped_in_the_kits_base_template(templates: Path) -> None:
    text = PageClient(build(templates), read={"ACC-1"}).get("/", "read").text
    assert text.startswith("<!doctype html>")
    assert '<link rel="stylesheet" href="/.meridian/ui/0.9.0/meridian.css">' in text
    assert '<script src="/.meridian/ui/0.9.0/meridian.js"></script>' in text
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


def test_a_form_answered_with_a_page_marks_the_tab_it_was_sent_from(templates: Path) -> None:
    pages = build(templates)

    @pages.page("/history", "History", levels=["write", "read"])
    def history(request: Request) -> str:
        return pages.render("setup.html", note="")

    @pages.route("/refresh", levels=["write"], methods=["GET", "POST"])
    def refresh(request: Request) -> str:
        return pages.render("setup.html", note="refreshed")

    def row(text: str) -> str:
        return text.split('<nav class="tabs">')[1].split("</nav>")[0]

    client = PageClient(pages)
    on_history = '<a class="tab on" href="/history" aria-current="page">History</a>'
    # Re-rendered by the form's action: the tab it was posted from is current,
    # and the page is titled as it.
    sent = client.post("/refresh", "write", headers={"Referer": "http://p.test/history?x=1"})
    assert on_history in row(sent.text) and 'class="tab on" href="/"' not in sent.text
    assert "<title>History · Ledger</title>" in sent.text
    # Sent from no tab, or with no Referer: none is.
    for headers in ({"Referer": "http://p.test/elsewhere"}, {}):
        assert 'class="tab on"' not in client.post("/refresh", "write", headers=headers).text
    # A GET carries no token, so did not necessarily come from this plugin's page.
    asked = client.request("GET", "/refresh", "write", headers={"Referer": "http://p.test/"})
    assert 'class="tab on"' not in asked.text
    # A redirect's GET is for the tab's own path, which marks it.
    assert on_history in row(client.get("/history", "write", notice="done").text)


def test_a_page_under_a_tabs_path_marks_that_tab(templates: Path) -> None:
    """A route at "/history/archive" is a view of History: History is marked,
    and the page titled as it. "/" marks only itself, and "/historic" is not
    under "/history"."""
    pages = build(templates)

    @pages.page("/history", "History", levels="read")
    def history(request: Request) -> str:
        return pages.render("setup.html", note="")

    for path in ("/history/archive", "/historic"):

        @pages.route(path, levels="read", tool=False, why="a test's page")
        def under(request: Request) -> str:
            return pages.render("setup.html", note="")

    client = PageClient(pages)
    shown = client.get("/history/archive", "read").text
    assert '<a class="tab on" href="/history" aria-current="page">History</a>' in shown
    assert 'class="tab on" href="/"' not in shown
    assert "<title>History · Ledger</title>" in shown
    assert 'class="tab on"' not in client.get("/historic", "read").text


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


async def test_the_asgi_app_answers_head_without_a_body(templates: Path) -> None:
    header = caller_header("read", read={"ACC-1"}).encode()
    got = await asgi(build(templates), [(b"meridian-caller", header)])
    head = await asgi(build(templates), [(b"meridian-caller", header)], method="HEAD")
    length = dict(got[0]["headers"])[b"content-length"]
    assert head[0]["status"] == 200 and dict(head[0]["headers"])[b"content-length"] == length
    assert int(length) == len(got[1]["body"]) > 0 and head[1]["body"] == b""


async def test_a_body_over_the_limit_is_refused_before_it_is_read(templates: Path) -> None:
    assert meridian.pages.MAX_BODY == Pages().max_body == 1024 * 1024
    for wrong in (-1, 1.5, True, "8192"):
        with pytest.raises(ValueError, match="max_body is a number of bytes"):
            Pages(max_body=wrong)  # type: ignore[arg-type]
    pages = build(templates)
    pages.max_body = 200
    writer = caller_header("write")
    token = pages.csrf_token(meridian.Caller.from_header(writer))
    form = f"csrf={token}&account=".encode()
    headers = [
        (b"meridian-caller", writer.encode()),
        (b"content-type", b"application/x-www-form-urlencoded"),
    ]
    fits = form + b"A" * (200 - len(form))
    taken = await asgi(pages, headers, method="POST", path="/act", body=fits)
    assert taken[0]["status"] == 200
    over = fits + b"A"
    sent = await asgi(pages, headers, method="POST", path="/act", body=over)
    assert sent[0]["status"] == 413 and b"larger than this plugin takes" in sent[1]["body"]
    # Said by its length, it is refused without a byte of it received.
    received: list[Any] = []

    async def receive() -> dict[str, Any]:
        received.append(1)
        return {"type": "http.request", "body": over}

    answered: list[Any] = []

    async def send(message: Any) -> None:
        answered.append(message)

    length = (b"content-length", str(len(over)).encode())
    await pages.app()(
        {"type": "http", "method": "POST", "path": "/act", "headers": [*headers, length]},
        receive,
        send,
    )
    assert answered[0]["status"] == 413 and received == []


async def test_the_standard_librarys_server_answers_head_and_refuses_a_large_body(
    templates: Path,
) -> None:
    pages = build(templates)
    acted: list[str] = []

    @pages.route("/big", levels="write", methods=["POST"])
    def big(request: Request) -> str:
        acted.append(request.form.get("pad", ""))
        return "taken"

    writer = caller_header("write")
    token = pages.csrf_token(meridian.Caller.from_header(writer))

    def ask(
        port: int, method: str, path: str, header: str | None, data: bytes | None = None
    ) -> tuple[int, Any, bytes]:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}", data=data, method=method
        )
        if header is not None:
            request.add_header("Meridian-Caller", header)
        try:
            with urllib.request.urlopen(request, timeout=10) as answer:
                return answer.status, answer.headers, answer.read()
        except urllib.error.HTTPError as answer:
            return answer.code, answer.headers, answer.read()

    form = f"csrf={token}&pad=".encode()
    server = pages.serve(plugin=None, port=0)  # type: ignore[arg-type]
    tight = pages.serve(plugin=None, port=0, max_body=len(form) + 10)  # type: ignore[arg-type]
    port, tight_port = server.server_address[1], tight.server_address[1]
    try:
        reader = caller_header("read", read={"ACC-7"})
        got = await asyncio.to_thread(ask, port, "GET", "/", reader)
        head = await asyncio.to_thread(ask, port, "HEAD", "/", reader)
        unsigned = await asyncio.to_thread(ask, port, "HEAD", "/", None)
        large = form + b"z" * (1024 * 1024)
        refused = await asyncio.to_thread(ask, port, "POST", "/big", writer, large)
        taken = await asyncio.to_thread(ask, port, "POST", "/big", writer, form + b"z" * 9000)
        tight_refused = await asyncio.to_thread(
            ask, tight_port, "POST", "/big", writer, form + b"z" * 11
        )
        tight_taken = await asyncio.to_thread(
            ask, tight_port, "POST", "/big", writer, form + b"z" * 10
        )
    finally:
        for each in (server, tight):
            each.shutdown()
            each.server_close()
    assert got[0] == 200 and b"ACC-7" in got[2]
    assert head[0] == 200 and head[2] == b""
    assert head[1]["Content-Length"] == str(len(got[2])) == got[1]["Content-Length"]
    assert unsigned[0] == 401 and unsigned[2] == b""
    assert refused[0] == 413 and refused[2] == b"This request is larger than this plugin takes."
    assert taken[:1] == (200,) and tight_taken[:1] == (200,) and tight_refused[0] == 413
    assert acted == ["z" * 9000, "z" * 10]


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
    held = {"ACC-1": "12,500.00"}  # what the plugin holds for an account
    pages = build(templates)

    @pages.page("/leaky", "Leaky", levels="admin")
    def leaky(request: Request) -> str:
        return pages.render("setup.html", note=", ".join(held.values()))

    client = PageClient(pages, read={"ACC-1"}, write={"ACC-1"})
    with pytest.raises(AssertionError, match="/leaky shows account data under Manage: 12,500"):
        client.assert_no_account_data("12,500.00", "AAPL")
    # The same page, showing none of it, passes; Setup never showed any.
    held.clear()
    client.assert_no_account_data("12,500.00", "AAPL")
    # Named as a template writes it, escaped, it is found all the same.
    held["ACC-1"] = "AT&T <common>"
    with pytest.raises(AssertionError, match="shows account data under Manage: AT&T <common>"):
        client.assert_no_account_data("AT&T <common>")
    # Naming nothing would check nothing.
    with pytest.raises(ValueError, match="names no account data"):
        client.assert_no_account_data()
    with pytest.raises(ValueError, match="names no account data"):
        client.assert_no_account_data("")


def test_account_identities_on_a_page_at_admin_are_not_account_data(templates: Path) -> None:
    # A Manage page lists every account of the deployment as a link target:
    # the accounts read answers each one's identity, and never its holdings.
    identities = {"ACC-1": "Growth fund, Fidelity, Roth IRA, Fund I, joint"}
    pages = build(templates)

    @pages.page("/links", "Account links", levels="admin")
    def links(request: Request) -> str:
        listed = "; ".join(f"{k} {v}" for k, v in sorted(identities.items()))
        return pages.render("setup.html", note=listed)

    client = PageClient(pages, read={"ACC-1"}, write={"ACC-1"})
    assert "ACC-1 Growth fund" in client.get("/links", "admin").text
    client.assert_no_account_data("AAPL", "125", "12,500.00")
    # Strict about what the test names, an identity included.
    with pytest.raises(AssertionError, match="/links shows account data under Manage: ACC-1"):
        client.assert_no_account_data("ACC-1")


def test_the_client_asks_as_a_deployment_admin_when_told(templates: Path) -> None:
    pages = build(templates)
    seen: list[bool] = []

    @pages.page("/accounts", "Account links", levels="admin")
    def accounts(request: Request) -> str:
        seen.append(request.caller.deployment_admin)
        offer = "Create a new account" if request.caller.deployment_admin else ""
        return pages.render("setup.html", note=offer)

    ada, root = PageClient(pages), PageClient(pages, deployment_admin=True)
    assert not ada.caller("admin").deployment_admin and root.caller("admin").deployment_admin
    assert ada.caller("read", deployment_admin=True).deployment_admin
    assert not root.caller("read", deployment_admin=False).deployment_admin
    assert "Create a new account" in root.get("/accounts", "admin").text
    assert "Create a new account" not in ada.get("/accounts", "admin").text
    assert root.post("/act", "write").status == 200  # the token is the person's either way
    root.assert_no_account_data("12,500.00")
    assert seen == [True, False, True]


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
