"""Contract v20 through the SDK: an act's check tool, its accounts and its
page; the prepared change a page was opened from; a person's own settings;
an account a plugin may not link to; typed settings, the kit's macros and
each role's common part (spec/plugin-pages-follow-their-role); and a data
plugin's restart backfilled from the venue's history.

What this client decides, and so what is worth asserting: what an act
declares of itself, refused here where the sidecar would refuse the
registration; that a prepared change and a person's own settings are read
and saved for the person and never for nobody; and that the common pages
draw the role's sections, labels and "not set up yet" states in their order.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import Caller, CommandRefused, Figure
from meridian.pages import Request
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import custody, data, operations, reporting
from meridian.suites import Recorder
from meridian.testing import PageClient, caller_header
from meridian.v1 import sidecar_pb2

# ── An act that can be prepared ──────────────────────────────────────────────


@dataclass(frozen=True)
class Lot:
    quantity: str
    account: str = ""


@dataclass(frozen=True)
class Confirmation:
    account: str
    lots: list[Lot] = field(default_factory=list)


@dataclass(frozen=True)
class Draft:
    account: str
    ok: bool = True


def opening(
    *,
    checked_by: str = "check_opening_draft",
    accounts: tuple[str, ...] = ("account",),
    made_on: str | None = None,
) -> meridian.Pages:
    pages = meridian.Pages("Operations")

    @pages.page(
        "/opening",
        "Opening balances",
        levels=["write", "read"],
        answers=Draft,
        name="read_opening_balances",
    )
    async def read_opening_balances(request: meridian.Request) -> meridian.Response:
        return pages.answer("x.html", Draft(account="ACC-1"))

    @pages.route(
        "/opening/check",
        levels="write",
        methods=["POST"],
        params=Confirmation,
        answers=Draft,
        reads=True,
        name="check_opening_draft",
    )
    async def check_opening_draft(request: meridian.Request) -> meridian.Response:
        return pages.answer("x.html", Draft(account=request.params.account))

    @pages.route(
        "/opening/confirm",
        levels="write",
        methods=["POST"],
        params=Confirmation,
        name="confirm_opening_balance",
        checked_by=checked_by,
        accounts=accounts,
        made_on=made_on,
    )
    async def confirm_opening_balance(request: meridian.Request) -> meridian.Response:
        return pages.answer("x.html", Draft(account=request.params.account))

    return pages


def tool(pages: meridian.Pages, name: str) -> sidecar_pb2.ToolDeclaration:
    return next(each.declared() for each in pages.tools if each.name == name)


def test_an_act_names_its_check_its_accounts_and_the_page_it_is_made_on() -> None:
    declared = tool(opening(accounts=("account", "lots[].account")), "confirm_opening_balance")
    assert declared.checked_by == "check_opening_draft"
    assert list(declared.accounts) == ["account", "lots[].account"]
    # The route posts under the page it is the form of: made there.
    assert declared.made_on == "/opening"
    read = tool(opening(), "check_opening_draft")
    assert (read.checked_by, list(read.accounts), read.made_on) == ("", [], "")


def test_an_act_made_in_the_inbox_names_no_page() -> None:
    assert tool(opening(made_on=""), "confirm_opening_balance").made_on == ""


@pytest.mark.parametrize(
    ("given", "said"),
    [
        ({"checked_by": "no_such_tool"}, "no read tool"),
        ({"checked_by": "confirm_opening_balance"}, "no read tool"),
        ({"accounts": ("lots[].custodian",)}, "its record does not have"),
        ({"made_on": "/elsewhere"}, "not one of its pages"),
    ],
)
def test_what_an_act_declares_is_held_to_the_pages_own(given: dict, said: str) -> None:
    with pytest.raises(ValueError, match=said):
        _ = opening(**given).tools


def test_a_read_names_no_check_and_a_record_names_no_prepare_field() -> None:
    pages = meridian.Pages("x")

    @pages.route("/r", levels="admin", answers=Draft, name="read_r", checked_by="read_r")
    async def read_r(request: meridian.Request) -> str:
        return ""

    with pytest.raises(ValueError, match="only an act names checked_by"):
        _ = pages.tools

    @dataclass(frozen=True)
    class Prepared:
        prepare: str

    with pytest.raises(ValueError, match="the kit's Prepare button's"):
        pages.route("/p", levels="write", methods=["POST"], params=Prepared)


async def test_registration_sends_what_each_act_declares(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    interface = meridian.Interface(port=8000, title="Operations", pages=opening())
    plugin = await meridian.connect(address, heartbeat=False, interface=interface)
    try:
        sent = {each.name: each for each in service.registered[-1].tools}
        assert sent["confirm_opening_balance"].checked_by == "check_opening_draft"
        assert sent["confirm_opening_balance"].made_on == "/opening"
    finally:
        await plugin.leave()


# ── The prepared change a page was opened from ───────────────────────────────

PREPARED = sidecar_pb2.PreparedCall(
    prepared_call_id="PC-01J9",
    tool_name="confirm_opening_balance",
    arguments_json=json.dumps({"account": "ACC-1", "lots": [{"quantity": "10"}]}),
    prepared_by_subject="local|ada",
    prepared_by_display_name="Ada Park",
    prepared_through_client="Claude",
    reason="The statement of 30 September agrees.",
    state=sidecar_pb2.PREPARED_CALL_STATE_PREPARED,
)


async def test_a_page_opened_from_a_prepared_change_reads_it_for_the_person(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.prepared["PC-01J9"] = PREPARED
    pages = meridian.Pages("Operations")
    seen: list[object] = []

    @pages.page("/opening", "Opening balances", levels="write")
    async def page(request: meridian.Request) -> str:
        seen.append(await request.prepared())
        return "ok"

    plugin = await meridian.connect(address, heartbeat=False)
    try:

        async def ask(prepared_call_id: str) -> object:
            header = caller_header(
                "write", read={"ACC-1"}, write={"ACC-1"}, prepared_call_id=prepared_call_id
            )
            await pages.dispatch(Request("GET", "/opening", Caller.from_header(header), plugin))
            return seen[-1]

        found = await ask("PC-01J9")
        assert isinstance(found, sidecar_pb2.PreparedCall)
        assert json.loads(found.arguments_json)["account"] == "ACC-1"
        assert found.prepared_through_client == "Claude"
        # Read for the person whose page it is, never as the plugin.
        assert service.prepared_reads[-1][0] == "PC-01J9"
        assert service.prepared_reads[-1][1]
        # One the dashboard does not answer, and a page reached from none.
        assert await ask("PC-NOT-SHOWN") is None
        reads = len(service.prepared_reads)
        assert await ask("") is None
        assert len(service.prepared_reads) == reads
    finally:
        await plugin.leave()


# ── A person's own settings ──────────────────────────────────────────────────

WATCHLIST = meridian.Setting(
    "watchlist",
    list,
    label="Watchlist",
    columns=(meridian.Column("instrument", "instrument", label="Instrument"),),
    per_person=True,
)
CHART = meridian.Setting("chart_days", int, label="Days shown", default=30, per_person=True)


def test_a_setting_of_a_persons_own_is_never_secret_nor_required() -> None:
    assert WATCHLIST._declared().per_person
    with pytest.raises(ValueError, match="never per person"):
        meridian.Setting("token", secret=True, per_person=True)._declared()
    with pytest.raises(ValueError, match="never required"):
        meridian.Setting("view", required=True, per_person=True)._declared()


async def test_a_persons_own_settings_are_saved_for_them_and_never_delivered_as_settings(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.roles = ("reporting",)
    service.settings = [
        sidecar_pb2.SettingsDelivery(
            values=[sidecar_pb2.SettingValue(name="currency", value="EUR")]
        )
    ]
    declared = [meridian.Setting("currency", default="USD"), WATCHLIST, CHART]
    plugin = await meridian.connect(address, heartbeat=False, settings=declared)
    try:
        sent = {each.name: each.per_person for each in service.registered[-1].settings}
        assert sent == {"currency": False, "watchlist": True, "chart_days": True}
        async for now in plugin.settings():
            assert now.values == {"currency": "EUR"}
            break
        ada = Caller.from_header(caller_header("write", read={"ACC-1"}, write={"ACC-1"}))
        held = await plugin.set_own_settings(
            {"watchlist": [{"instrument": "INS-QQQ"}], "chart_days": 90}, for_caller=ada
        )
        assert held == {"watchlist": [{"instrument": "INS-QQQ"}], "chart_days": 90}
        assert service.own["local|ada"]["chart_days"] == "90"
        with pytest.raises(ValueError, match="does not declare per_person"):
            await plugin.set_own_settings({"currency": "GBP"}, for_caller=ada)
        viewer = Caller.from_header(caller_header("read", read={"ACC-1"}))
        with pytest.raises(meridian.NotGranted):
            await plugin.set_own_settings({"chart_days": 7}, for_caller=viewer)
    finally:
        await plugin.leave()


def test_each_request_carries_the_persons_own_settings_typed() -> None:
    pages = meridian.Pages("Board")
    seen: list[dict] = []

    @pages.page("/", "Board", levels=["write", "read", "admin"])
    async def board(request: meridian.Request) -> str:
        seen.append(request.own_settings)
        return "ok"

    @dataclass
    class Stub:
        _declared: tuple = (WATCHLIST, CHART)

    client = PageClient(pages, Stub(), own_settings={"watchlist": '[{"instrument":"INS-1"}]'})
    client.get("/", "write")
    assert seen[-1] == {"watchlist": [{"instrument": "INS-1"}], "chart_days": 30}
    # Under Manage the claims carry none: the defaults alone.
    client.get("/", "admin")
    assert seen[-1] == {"chart_days": 30}


# ── An account the plugin may not link to ────────────────────────────────────


async def test_a_link_to_an_account_not_granted_is_refused_with_its_code(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.operations.refuse = (grpc.StatusCode.ABORTED, "ACC-9 is not granted to snaptrade-1")
    refusal = sidecar_pb2.Refusal(reason=sidecar_pb2.REFUSAL_REASON_ACCOUNT_NOT_LINKABLE)
    service.operations.refuse_metadata = (
        ("meridian-refusal-bin", refusal.SerializeToString()),
    )
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(CommandRefused) as refused:
            await plugin.link_external_account(external_account_id="SNAP-1", account_id="ACC-9")
        assert refused.value.reason == sidecar_pb2.REFUSAL_REASON_ACCOUNT_NOT_LINKABLE
    finally:
        await plugin.leave()


# ── Typed settings ───────────────────────────────────────────────────────────


@meridian.settings
class Config:
    environment: str = meridian.environment()
    api_key: str = meridian.setting("API key", required=True, secret=True)
    sandbox_key: str = meridian.setting(
        "Sandbox key", secret=True, applies_when=("environment", "sandbox")
    )
    poll_seconds: int = custody.poll_seconds()
    every: int = meridian.setting("Every", default=30, at_least=10, at_most=600)
    sample_data: bool = meridian.sample_data()


def test_a_class_declares_the_settings_in_its_order() -> None:
    names = [each.name for each in Config.declared()]
    assert names == [
        "environment",
        "api_key",
        "sandbox_key",
        "poll_seconds",
        "every",
        "sample_data",
    ]
    environment = Config.declared()[0]._declared()
    assert environment.required and environment.default_value == "live"
    assert [c.value for c in environment.choices] == ["live", "sandbox"]
    assert Config.declared()[2]._declared().applies_when.one_of == ["sandbox"]
    sample = Config.declared()[-1]._declared()
    assert (
        sample.developer and sample.label == "Sample data" and sample.default_value == "false"
    )
    assert Config.label("api_key") == "API key"


def test_an_instance_is_typed_defaulted_bounded_and_keeps_its_secrets_out_of_repr() -> None:
    held = Config._of({"api_key": "s3cret-value", "every": 5}, ["sandbox_key"])
    assert held.environment == "live" and held.poll_seconds == 900
    assert held.every == 10  # held to at_least
    assert held.missing == ("sandbox_key",)
    assert held.api_key == "s3cret-value"
    assert "s3cret" not in repr(held) and "s3cret" not in str(held)


def test_a_class_field_not_declared_as_a_setting_is_refused() -> None:
    with pytest.raises(TypeError, match="not declared with meridian.setting"):

        @meridian.settings
        class Bare:
            name: str = "x"

    with pytest.raises(TypeError, match="name the field sample_data"):

        @meridian.settings
        class Misnamed:
            demo: bool = meridian.sample_data()


async def test_a_plugin_connects_with_a_class_and_reads_instances_of_it(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.settings = [
        sidecar_pb2.SettingsDelivery(
            values=[sidecar_pb2.SettingValue(name="api_key", value="k")],
            missing_required=["environment"],
        )
    ]
    plugin = await meridian.connect(address, heartbeat=False, settings=Config)
    try:
        assert [s.name for s in service.registered[-1].settings][0] == "environment"
        first = await plugin.first_settings(Config)
        assert isinstance(first, Config)
        assert first.api_key == "k" and first.missing == ("environment",)
        applied: list[Config] = []
        await plugin.on_settings(Config, applied.append)
        assert applied[0].api_key == "k"
    finally:
        await plugin.leave()


# ── The kit's macros ─────────────────────────────────────────────────────────


def render(source: str, tmp_path: Path, **context: object) -> str:
    (tmp_path / "t.html").write_text(source)
    pages = meridian.Pages("Kit", templates=tmp_path)
    out: list[str] = []

    @pages.page("/", "Kit", levels=["write", "admin"])
    async def view(request: meridian.Request) -> str:
        out.append(pages.render("t.html", **context))
        return out[-1]

    PageClient(pages).get("/", "write")
    return out[-1]


def test_the_kit_macros_write_the_kits_patterns(tmp_path: Path) -> None:
    page = render(
        '{% import "meridian/kit.html" as kit %}'
        '{{ kit.badge("Linked", "good") }}|{{ kit.badge("Not linked") }}|'
        "{{ kit.notice(n) }}|{{ kit.when(at) }}|{{ kit.when(none) }}|"
        '{{ kit.empty("No statements yet", "An account appears once it is linked.") }}|'
        '{{ kit.action("/read", "Refresh", header="refresh", icon="refresh") }}|'
        '{{ kit.status(s) }}|{{ kit.nothing_here("This plugin reads brokerage accounts.") }}',
        tmp_path,
        n={"text": "The last read failed.", "tone": "bad", "items": ["503"]},
        at=datetime(2026, 10, 2, 13, 12, 40, tzinfo=UTC),
        s={
            "state": "ok",
            "label": "Read",
            "at": datetime(2026, 10, 2, 13, 12, tzinfo=UTC),
            "at_label": "Last read",
        },
    )
    parts = page.split("|")
    assert parts[0] == '<span class="badge good">Linked</span>'
    assert parts[1] == '<span class="badge">Not linked</span>'
    assert parts[2] == (
        '<div class="notice bad" role="alert">The last read failed.'
        '<ul class="plain"><li>503</li></ul></div>'
    )
    assert parts[3] == '<time datetime="2026-10-02T13:12:40+00:00">2026-10-02 13:12 UTC</time>'
    assert parts[4] == '<span class="faint">not reported</span>'
    assert parts[5] == (
        '<div class="empty-state"><strong>No statements yet</strong>'
        "<p>An account appears once it is linked.</p></div>"
    )
    assert (
        'data-om-action="refresh" data-om-icon="refresh" title="Refresh">Refresh</button>'
        in parts[6]
    )
    assert '<input type="hidden" name="csrf" value="' in parts[6]
    assert 'value=""' not in parts[6]
    assert parts[7].endswith("Read. Last read 2026-10-02 13:12 UTC.</om-status>")
    assert "you may read none of them" in parts[8]


def test_the_grid_macro_writes_its_json_and_its_table(tmp_path: Path) -> None:
    page = render(
        '{% import "meridian/kit.html" as kit %}'
        '{{ kit.grid("h", columns, rows, "key", empty="None.") }}',
        tmp_path,
        columns=[
            {"key": "instrument", "label": "Instrument", "type": "code"},
            {"key": "quantity", "label": "Quantity", "type": "decimal"},
        ],
        rows=[{"key": "A", "instrument": "<A&B>", "quantity": "1.5"}],
    )
    assert '<om-grid id="h" row-key="key" narrow="cards" empty="None.">' in page
    assert "\\u003cA\\u0026B\\u003e" in page
    assert '<td><code>&lt;A&amp;B&gt;</code></td><td class="num">1.5</td>' in page


# ── Each role's common part ──────────────────────────────────────────────────


def role_pages(role: str, page: str, record: object, tmp_path: Path, child: str = "") -> str:
    name = f"meridian/roles/{role}/{page}.html"
    if child:
        (tmp_path / "child.html").write_text('{% extends "' + name + '" %}' + child)
        name = "child.html"
    pages = meridian.Pages("Plugin", templates=tmp_path)

    @pages.page("/", "Page", levels=["admin", "write", "read"], answers=type(record))
    async def view(request: meridian.Request) -> meridian.Response:
        return pages.answer(name, record, action="/link")

    client = PageClient(pages, read={"ACC-1"}, write={"ACC-1"})
    return client.get("/", "admin" if role == "data" else "write").text


def in_order(page: str, *said: str) -> None:
    at = [page.find(each) for each in said]
    assert -1 not in at, [s for s, a in zip(said, at, strict=True) if a == -1]
    assert at == sorted(at), said


def test_a_data_plugins_connection_draws_its_sections_and_next_step(tmp_path: Path) -> None:
    record = data.ConnectionRead(
        mode="No key",
        credentials=[
            data.Credential("API key ID", False),
            data.Credential("API secret key", False),
        ],
        calls=3,
    )
    page = role_pages("data", "connection", record, tmp_path)
    in_order(
        page,
        "No key yet",
        'data-om-opens="settings"',
        "<h2>Key</h2>",
        "Mode",
        "API key ID: not set; API secret key: not set",
        "Entitled at the vendor",
        "<h2>Limits and use</h2>",
        "Limit",
        "Calls",
        "Last call",
        "Last error",
        "<h2>Stream</h2>",
        "Does not stream",
    )


def test_a_vendor_adds_rows_to_a_section_and_sections_after_the_common(tmp_path: Path) -> None:
    record = data.ConnectionRead(mode="Live", sessions=2)
    page = role_pages(
        "data",
        "connection",
        record,
        tmp_path,
        child='{% block vendor_rows %}{% if section == "Key" %}<tr><th>Feeds</th></tr>'
        "{% endif %}{% endblock %}{% block vendor_sections %}<h2>Release calendar</h2>"
        "{% endblock %}",
    )
    in_order(
        page,
        "<h2>Key</h2>",
        "Feeds",
        "<h2>Limits and use</h2>",
        "2 sessions",
        "Release calendar",
    )
    assert page.count("Feeds") == 1
    assert "No key yet" not in page


def test_a_data_plugins_datasets_say_whether_each_is_licensed(tmp_path: Path) -> None:
    record = data.DatasetsRead(
        served=[data.Served("alpaca-1:daily", licensed=True), data.Served("alpaca-1:live")]
    )
    page = role_pages(
        "data",
        "datasets",
        record,
        tmp_path,
        child="{% block vendor_columns %}{% if row is none %}<th>Feed</th>"
        "{% else %}<td>{{ row.dataset }}-feed</td>{% endif %}{% endblock %}",
    )
    in_order(
        page,
        "No wants yet",
        "<h2>Served</h2>",
        "Feed",
        "alpaca-1:daily",
        "Licensed",
        "alpaca-1:live",
        "Not licensed yet",
        "<h2>Wants</h2>",
        "<h2>Subjects</h2>",
    )
    assert "alpaca-1:daily-feed" in page and "alpaca-1:live-feed" in page


def test_a_custody_plugins_pages_say_their_next_steps(tmp_path: Path) -> None:
    links = role_pages(
        "custody",
        "account_links",
        custody.AccountLinksRead(
            external_accounts=[custody.ExternalAccountRead("SNAP-1", "Roth IRA")]
        ),
        tmp_path,
    )
    in_order(links, "No accounts granted yet", "<om-account-map", "Roth IRA", "Not linked")
    statements = role_pages("custody", "statements", custody.StatementsRead(), tmp_path)
    assert "No statements yet" in statements
    connections = role_pages(
        "custody",
        "connections",
        custody.ConnectionsRead(credentials=[data.Credential("Client ID", False)]),
        tmp_path,
    )
    in_order(connections, "No credentials yet", "<h2>Connections</h2>")


def test_an_operations_plugins_pages_say_their_next_steps(tmp_path: Path) -> None:
    breaks = role_pages("operations", "breaks", operations.BreaksRead(), tmp_path)
    assert "No breaks yet" in breaks and "Opening balances" in breaks
    opening_page = role_pages(
        "operations", "opening_balances", operations.OpeningBalancesRead(), tmp_path
    )
    assert "Nothing to confirm" in opening_page
    reconciled = role_pages(
        "operations", "reconciliations", operations.ReconciliationsRead(), tmp_path
    )
    in_order(reconciled, "<h2>Reconciliations</h2>", "Last reconciliation", "None yet")


def test_a_reporting_plugins_datasets_say_not_entitled_yet(tmp_path: Path) -> None:
    page = role_pages(
        "reporting",
        "datasets",
        reporting.DatasetsRead(datasets=[reporting.DatasetRead("tiingo-1:daily")]),
        tmp_path,
    )
    in_order(page, "Not entitled yet", "<h2>Datasets</h2>", "tiingo-1:daily", "Every field")


def test_each_roles_figures_come_in_its_order_with_its_labels() -> None:
    labels = [
        each.label
        for each in data.figures(
            connection="Not answering", rate_use="41 of 100 a minute", stream="Off"
        )
    ]
    assert labels == ["Connection", "Stream", "Rate use"]
    assert data.figures(connection="Not answering")[0].state == "error"
    assert [f.label for f in custody.figures(connections=3, accounts_reached=7)] == [
        "Connections",
        "Accounts reached",
    ]
    assert [
        f.label for f in operations.figures(open_breaks=2, last_reconciliation="never")
    ] == ["Open breaks", "Last reconciliation"]
    assert reporting.figures(last_valued="2026-10-11", not_priced=2)[1].state == "warn"
    kept = data.figures(connection=Figure("Connection", "Answering", why="since 09:00"))
    assert kept[0].why == "since 09:00"
    with pytest.raises(ValueError, match="keeps the role's label"):
        data.figures(connection=Figure("Vendor", "Answering"))


def test_each_roles_common_settings_keep_their_names_and_labels() -> None:
    made = [
        custody.poll_seconds(),
        custody.stale_after_hours(),
        operations.reconcile(),
        operations.due_business_days(),
        operations.street_fresh_within_hours(),
        reporting.reporting_currency(),
    ]
    assert [(s.name, s.label) for s in made] == [
        ("poll_seconds", "Read every"),
        ("stale_after_hours", "Stale after"),
        ("reconcile", "Reconcile"),
        ("due_business_days", "A break is due"),
        ("street_fresh_within_hours", "Reconcile against a statement no older than"),
        ("reporting_currency", "Reporting currency"),
    ]
    # Automation is off until an admin turns it on.
    assert operations.reconcile().default is False


# ── A restart's gap ──────────────────────────────────────────────────────────


async def test_a_restart_reads_its_last_trades_and_records_the_gap_in_batches() -> None:
    recorder = Recorder("coinbase-1")
    subjects = [f"INS-{n}" for n in range(501)]
    pages_of = {
        "": ops.ListTradesResult(
            trades=[
                ops.Trade(
                    meta=ops.ObservationMeta(
                        row_key="k", subjects=[ops.SubjectRef(entity_id="INS-0")]
                    )
                )
            ],
            next_cursor="c2",
        ),
        "c2": ops.ListTradesResult(),
    }
    recorder.answer(
        "ListTrades",
        lambda params: (
            pages_of[params.cursor] if len(params.subjects) == 500 else ops.ListTradesResult()
        ),
    )

    async def history(last: ops.Trade) -> list[meridian.Trade]:
        return [
            meridian.Trade(
                meta=meridian.ObservationMeta(
                    row_key=f"k{n}", subjects=list(last.meta.subjects)
                ),
                price=meridian.Money(1, "USD"),
                quantity=1,
            )
            for n in range(600)
        ]

    sent = await data.backfill_restart(recorder, subjects, history)
    assert sent == 600
    reads = recorder.on("ListTrades")
    assert all(read.latest_recorded for read in reads)
    assert [len(read.subjects) for read in reads] == [500, 500, 1]
    assert [len(batch.trades) for batch in recorder.on("RecordTrades")] == [500, 100]


def test_a_custody_plugins_history_and_raw_records(tmp_path: Path) -> None:
    history = role_pages(
        "custody",
        "history",
        custody.HistoryRead(
            activities=[
                custody.ActivityRead(
                    "Main", kind="dividend", trade_date="2026-10-01", amount="12.50"
                )
            ]
        ),
        tmp_path,
    )
    in_order(history, "<h2>History</h2>", "Main", "2026-10-01", "dividend", "12.50")
    assert "No activity yet" in role_pages(
        "custody", "history", custody.HistoryRead(), tmp_path
    )
    (tmp_path / "raw.html").write_text(
        '{% extends "meridian/roles/custody/raw_records.html" %}'
    )
    pages = meridian.Pages("Plugin", templates=tmp_path)

    @pages.page("/raw", "Raw records", levels=["write", "read"])
    async def raw(request: meridian.Request) -> str:
        return pages.render(
            "raw.html",
            kinds=[
                meridian.RecordKind("activity", "Reported activity", window_days=2555),
                meridian.RecordKind("state", "Connections", window_days=30, archivable=False),
            ],
            stored=[sidecar_pb2.StoredSpan(record_kind="activity", record_count=42)],
            past={"activity_past_window": "archived"},
            key="activity/2026-10-01.json",
            found=sidecar_pb2.RecordMoveRequest(outcome=sidecar_pb2.MOVE_OUTCOME_ARCHIVED),
        )

    page = PageClient(pages, read={"ACC-1"}).get("/raw", "read").text
    in_order(
        page,
        "activity/2026-10-01.json: archived, restorable",
        "<h2>Raw records</h2>",
        "Reported activity",
        "2555 days",
        ">archived<",
        "42",
        "Connections",
        "Updated in place",
    )
