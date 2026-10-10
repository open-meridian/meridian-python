"""A person's access to a plugin granted per role (contract v15; decisions/033;
plans/access-is-granted-per-role, the SDK's row), from the plugin's side.

A plugin launched holding `custody` and `operations` -- the two-role plugin
the plan's e2e drives -- written as an author writes one on 0.20.0: each page,
route, tool and setting names the roles it serves, and each page adapts per
role by the caller's entry for it. What this SDK decides: what it declares at
registration, the per-role view it reads from the claims, the 403 by role
before a view runs, the tab row by role, and the test client's sessions per
role and level. Which acts are admitted is the sidecar's alone, tested in
meridian-core: a page's roles decide what is shown, never what is admitted.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest

import meridian
from conftest import FakeSidecar
from meridian import Caller, Refused
from meridian.pages import Pages
from meridian.testing import PageClient, caller_header
from meridian.v1 import sidecar_pb2

ROLES = ("custody", "operations")
WRITE, READ, ADMIN = (
    sidecar_pb2.ACCESS_LEVEL_WRITE,
    sidecar_pb2.ACCESS_LEVEL_READ,
    sidecar_pb2.ACCESS_LEVEL_ADMIN,
)

#: What the plugin holds for each account, which no Manage session may show.
HELD = {"ACC-1": "125 AAPL", "ACC-2": "40 VIGIX"}


@dataclass(frozen=True)
class Statement:
    account: str


@dataclass(frozen=True)
class OpeningBalance:
    account: str
    quantity: Decimal


@dataclass(frozen=True)
class Done:
    account: str


SETTINGS = (
    # The brokerage key serves both roles, and only an admin of both sets it.
    meridian.Setting("api_key", secret=True, required=True, roles=ROLES),
    meridian.Setting("tolerance", int, default=0, roles="operations"),
)


def desk(templates: Path) -> Pages:
    """The two-role plugin's pages, each naming the roles it serves."""
    (templates / "rows.html").write_text(
        '{% extends "meridian/base.html" %}{% block content %}'
        "{% for role, rows in shown.items() %}<h2>{{ role }}</h2>"
        "{% for row in rows %}<p>{{ row }}</p>{% endfor %}{% endfor %}"
        "{% if may_record %}<button>Record</button>{% endif %}"
        "{% endblock %}"
    )
    (templates / "admin.html").write_text(
        '{% extends "meridian/base.html" %}{% block content %}<p>{{ said }}</p>{% endblock %}'
    )
    pages = Pages("Desk", templates=templates)

    def rows(request: meridian.Request, *roles: str) -> dict[str, list[str]]:
        # Each role's rows cut to what the caller reads through that role.
        return {
            role: [HELD[a] for a in sorted(request.caller.read_for(role))] for role in roles
        }

    @pages.page("/statements", "Statements", roles=["custody"], levels=["write", "read"])
    async def statements(request: meridian.Request) -> str:
        return pages.render(
            "rows.html",
            shown=rows(request, "custody"),
            may_record=bool(request.caller.write_for("custody")),
        )

    @pages.page("/balances", "Opening balances", roles="operations", levels=["write", "read"])
    async def balances(request: meridian.Request) -> str:
        return pages.render(
            "rows.html",
            shown=rows(request, "operations"),
            may_record=bool(request.caller.write_for("operations")),
        )

    @pages.page("/blotter", "Blotter", roles=ROLES, levels=["write", "read"])
    async def blotter(request: meridian.Request) -> str:
        return pages.render("rows.html", shown=rows(request, *ROLES), may_record=False)

    @pages.page("/links", "Account links", roles=["custody"], levels=["admin"])
    async def links(request: meridian.Request) -> str:
        return pages.render("admin.html", said="Link an account")

    @pages.page("/rules", "Rules", roles=["operations"], levels=["admin"])
    async def rules(request: meridian.Request) -> str:
        return pages.render("admin.html", said="Tolerances")

    @pages.route(
        "/statements/record",
        roles=["custody"],
        levels=["write"],
        methods=["POST"],
        params=Statement,
        name="record_statement",
    )
    async def record_statement(request: meridian.Request) -> meridian.Response:
        """Record the account's holdings statement."""
        return pages.answer("admin.html", Done(request.params.account), said="Recorded")

    @pages.route(
        "/balances/record",
        roles=["operations"],
        levels=["write"],
        methods=["POST"],
        params=OpeningBalance,
        name="open_balance",
    )
    async def open_balance(request: meridian.Request) -> meridian.Response:
        """Record the account's opening balance."""
        return pages.answer("admin.html", Done(request.params.account), said="Recorded")

    return pages


@pytest.fixture
def pages(tmp_path: Path) -> Pages:
    return desk(tmp_path)


@pytest.fixture
def client(pages: Pages) -> PageClient:
    return PageClient(pages, read={"ACC-1", "ACC-2"}, write={"ACC-1"}, roles=ROLES)


# ── What registration declares ───────────────────────────────────────────


async def test_every_declaration_names_its_roles_and_registers_on_two_roles(
    sidecar: tuple[FakeSidecar, str], pages: Pages
) -> None:
    service, address = sidecar
    service.roles = ROLES
    async with await meridian.connect(
        address,
        heartbeat=False,
        interface=meridian.Interface(port=8000, title="Desk", pages=pages),
        settings=SETTINGS,
    ) as plugin:
        assert plugin.identity.roles == ROLES
    (sent,) = service.registered
    assert sent.schema_version == "v18"
    assert {p.path: list(p.roles) for p in sent.interface.pages} == {
        "/statements": ["custody"],
        "/balances": ["operations"],
        "/blotter": ["custody", "operations"],
        "/links": ["custody"],
        "/rules": ["operations"],
    }
    assert {t.name: list(t.roles) for t in sent.tools} == {
        "record_statement": ["custody"],
        "open_balance": ["operations"],
    }, "a derived tool takes its route's roles"
    assert {s.name: list(s.roles) for s in sent.settings} == {
        "api_key": ["custody", "operations"],
        "tolerance": ["operations"],
    }


async def test_a_declaration_naming_no_role_or_a_stranger_is_refused_on_two_roles(
    sidecar: tuple[FakeSidecar, str], tmp_path: Path
) -> None:
    """The sidecar's rule (W4.1), as the fake holds it: built at v15, a page
    naming no role on a plugin holding two is refused, and so is one naming
    a role the plugin was not launched with, each naming the plugin's roles."""
    service, address = sidecar
    service.roles = ROLES
    for page, says in (
        (
            meridian.Page("/", "Home", levels=["read"]),
            "names no role, and it holds custody and",
        ),
        (
            meridian.Page("/orders", "Orders", levels=["write"], roles=["oms"]),
            "serves oms, which this plugin was not launched with: it holds custody and "
            "operations",
        ),
    ):
        with pytest.raises(Refused, match=says):
            await meridian.connect(
                address,
                heartbeat=False,
                interface=meridian.Interface(port=8000, title="Desk", pages=[page]),
            )
    with pytest.raises(Refused, match="the setting poll serves ems"):
        await meridian.connect(
            address, heartbeat=False, settings=[meridian.Setting("poll", int, roles=["ems"])]
        )


async def test_a_plugin_holding_one_role_names_nothing_and_changes_nothing(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """Its declarations name no role, and the sidecar serves them its one."""
    service, address = sidecar
    page = meridian.Page("/", "Statements", levels=["write", "read"])
    async with await meridian.connect(
        address,
        heartbeat=False,
        interface=meridian.Interface(port=8000, title="Statements", pages=[page]),
        settings=[meridian.Setting("api_key", secret=True)],
    ):
        pass
    (sent,) = service.registered
    assert [list(p.roles) for p in sent.interface.pages] == [[]]
    assert [list(s.roles) for s in sent.settings] == [[]]
    (served,) = service.reported
    assert [list(p.roles) for p in served.interface.pages] == [["custody"]]
    assert [list(s.roles) for s in served.settings] == [["custody"]]


def test_a_name_no_role_could_have_is_refused_before_anything_is_sent() -> None:
    with pytest.raises(ValueError, match="'Custody', which is no role"):
        meridian.Setting("poll", int, roles=["Custody"])
    with pytest.raises(ValueError, match="names 14 roles; at most 13"):
        meridian.Page("/", "Home", levels="read", roles=[chr(97 + n) for n in range(14)])
    assert meridian.Page("/", "Home", levels="read", roles="custody").roles == ("custody",)
    assert meridian.Setting("poll", int, roles=["custody", "custody"]).roles == ("custody",)


# ── The caller's per-role view ───────────────────────────────────────────


def test_the_caller_reads_each_roles_level_and_accounts() -> None:
    """Ada under Open: write on operations, read on custody, her accounts per
    role as positions in the claims' read accounts."""
    ada = Caller.from_header(
        caller_header(
            "write",
            read={"ACC-1", "ACC-2"},
            write={"ACC-1"},
            roles={"operations": "write", "custody": "read"},
        )
    )
    assert ada.level == WRITE, "the session's button"
    assert ada.roles == {"operations": WRITE, "custody": READ}
    assert (ada.level_for("operations"), ada.level_for("custody")) == (WRITE, READ)
    assert ada.read_for("custody") == ada.read_for("operations") == {"ACC-1", "ACC-2"}
    assert ada.write_for("operations") == {"ACC-1"}
    assert ada.write_for("custody") == frozenset(), "read on custody writes nothing there"
    assert ada.level_for("oms") == sidecar_pb2.ACCESS_LEVEL_UNSPECIFIED
    assert ada.read_for("oms") == ada.write_for("oms") == frozenset()
    assert (ada.read, ada.write) == ({"ACC-1", "ACC-2"}, {"ACC-1"}), "the union"


def test_each_role_reaches_its_own_accounts_by_position() -> None:
    """The dashboard's claims as it mints them: custody reaching ACC-1 alone,
    operations ACC-2 alone, each by its position in the read accounts."""
    claims = sidecar_pb2.CallerClaims(
        subject="local|ben",
        level=WRITE,
        read_account_ids=["ACC-1", "ACC-2"],
        write_account_ids=["ACC-1"],
        roles=[
            sidecar_pb2.RoleAccess(
                role="custody", level=WRITE, read_positions=[0], write_positions=[0]
            ),
            sidecar_pb2.RoleAccess(role="operations", level=READ, read_positions=[1]),
        ],
    )
    ben = Caller.from_header(header(claims))
    assert (ben.read_for("custody"), ben.write_for("custody")) == ({"ACC-1"}, {"ACC-1"})
    assert (ben.read_for("operations"), ben.write_for("operations")) == ({"ACC-2"}, set())

    claims.roles[1].read_positions.append(2)
    with pytest.raises(ValueError, match="past the 2 the claims carry"):
        Caller.from_header(header(claims))


def test_under_manage_each_role_administered_reaches_no_account() -> None:
    cat = Caller.from_header(caller_header("admin", read={"ACC-1"}, roles=["custody"]))
    assert cat.roles == {"custody": ADMIN}
    assert cat.read_for("custody") == cat.write_for("custody") == frozenset()
    assert cat.level_for("operations") == sidecar_pb2.ACCESS_LEVEL_UNSPECIFIED


def test_claims_carrying_no_entry_read_every_role_as_the_session() -> None:
    """A plugin holding no role, or a dashboard before v15."""
    before = Caller.from_header(caller_header("write", read={"ACC-1"}, write={"ACC-1"}))
    assert before.roles == {}
    assert before.level_for("custody") == WRITE
    assert before.read_for("custody") == before.write_for("custody") == {"ACC-1"}


def test_a_session_carries_only_what_its_button_can() -> None:
    with pytest.raises(ValueError, match="a session at read carries no write on custody"):
        caller_header("read", roles={"custody": "write"})
    with pytest.raises(ValueError, match="a session at admin carries no read on custody"):
        caller_header("admin", roles={"custody": "read"})


# ── Pages served by role ─────────────────────────────────────────────────


def test_write_on_one_role_and_read_on_the_other(client: PageClient) -> None:
    """Ada (operations write, custody read) in Open: each page shows what her
    role allows; a custody act is refused before its view, naming custody and
    what she holds on it."""
    ada = {"operations": "write", "custody": "read"}
    balances = client.request("GET", "/balances", "write", roles=ada)
    statements = client.request("GET", "/statements", "write", roles=ada)
    assert balances.status == statements.status == 200
    assert "<button>Record</button>" in balances.text
    assert "<button>Record</button>" not in statements.text, "she reads custody"
    assert "125 AAPL" in statements.text and "40 VIGIX" in statements.text

    refused = client.post("/statements/record", "write", {"account": "ACC-1"}, roles=ada)
    assert refused.status == 403
    assert refused.text == (
        "/statements/record is for custody under Open; under Open this session holds "
        "read on custody."
    )
    recorded = client.post(
        "/balances/record", "write", {"account": "ACC-1", "quantity": "10"}, roles=ada
    )
    assert recorded.status == 200


def test_the_tab_row_shows_the_pages_of_the_sessions_roles(client: PageClient) -> None:
    on_custody = client.request("GET", "/blotter", "write", roles=["custody"])
    assert 'href="/statements"' in on_custody.text
    assert 'href="/balances"' not in on_custody.text
    assert "<h2>operations</h2>" in on_custody.text, "the blotter adapts per role"
    assert "40 VIGIX" in on_custody.text.split("<h2>custody</h2>")[1].split("<h2>")[0]


def test_every_page_under_each_level_for_each_role_alone_and_together(
    client: PageClient,
) -> None:
    served = {(r.page.path, r.level, r.roles): r.response.status for r in client.every_page()}
    assert len(served) == 5 * 3 * 3
    assert served[("/statements", "write", ("custody",))] == 200
    assert served[("/statements", "write", ("operations",))] == 403
    assert served[("/blotter", "read", ("operations",))] == 200
    assert served[("/blotter", "read", ROLES)] == 200
    assert served[("/links", "admin", ("custody",))] == 200
    assert served[("/links", "admin", ("operations",))] == 403
    assert served[("/rules", "admin", ROLES)] == 200
    assert served[("/statements", "admin", ROLES)] == 403
    client.assert_no_account_data(*HELD.values())


def test_a_manage_page_showing_account_data_is_named_with_its_role(tmp_path: Path) -> None:
    pages = desk(tmp_path)

    @pages.page("/leaky", "Leaky", roles=["operations"], levels=["admin"])
    async def leaky(request: meridian.Request) -> str:
        return pages.render("admin.html", said=HELD["ACC-1"])

    client = PageClient(pages, read={"ACC-1"}, roles=ROLES)
    with pytest.raises(AssertionError, match="/leaky shows account data under Manage on "):
        client.assert_no_account_data(*HELD.values())


def test_the_client_holds_only_the_plugins_roles(client: PageClient) -> None:
    with pytest.raises(ValueError, match="not oms"):
        client.caller("write", roles=["oms"])


# ── Tools by role ────────────────────────────────────────────────────────


def test_a_tool_is_called_on_its_roles(client: PageClient, pages: Pages) -> None:
    made = client.call_tool("record_statement", {"account": "ACC-1"})
    assert (made.status, made.outcome) == (200, "made")
    refused = client.call_tool(
        "record_statement", {"account": "ACC-1"}, roles={"custody": "read"}
    )
    assert refused.status == 403, "custody read in Open: the tool's role is not written"
    assert client.tool("open_balance").declared().roles == ["operations"]


def test_a_tool_replacing_a_route_serves_its_roles_unless_it_names_others(
    pages: Pages,
) -> None:
    @pages.tool(replaces="/balances/record", params=OpeningBalance, name="open_balance_v2")
    async def replaced(request: meridian.Request) -> meridian.Response:
        return pages.answer("admin.html", Done(request.params.account), said="Recorded")

    assert {t.name: t.roles for t in pages.tools}["open_balance_v2"] == ("operations",)


def header(claims: sidecar_pb2.CallerClaims) -> str:
    assertion = sidecar_pb2.CallerAssertion(claims=claims.SerializeToString())
    return base64.urlsafe_b64encode(assertion.SerializeToString()).decode().rstrip("=")
