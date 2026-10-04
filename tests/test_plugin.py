"""The client's half of the sidecar surface.

What is worth asserting here is not that a call reaches the server, which gRPC
already guarantees, but the three things this client decides: what it sends,
what it refuses to send, and how it translates a failure into something a plugin
author can act on.
"""

from __future__ import annotations

import asyncio
import base64

import pytest

import meridian
from conftest import FakeSidecar
from meridian import (
    AccountScope,
    AppliesWhen,
    Caller,
    Choice,
    Interface,
    LinkedExternalAccount,
    NotRegistered,
    Page,
    Refused,
    Setting,
    Settings,
)
from meridian.v1 import sidecar_pb2


async def test_registering_sends_no_identity(sidecar: tuple[FakeSidecar, str]) -> None:
    """The thing a plugin must not be able to do is the thing to assert.

    Instance and roles moved to the sidecar's launch configuration, so
    there is no field here to fill in. A client that grew one back would be
    letting a plugin choose its own privileges.
    """
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    await plugin.leave()

    (sent,) = service.registered
    assert sent.schema_version == meridian.SCHEMA_VERSION
    # From v11 the version's declaration rides beside it, which names no
    # instance and no role: here, no secret setting, nothing not carried and
    # no storage.
    assert [f.name for f, _ in sent.ListFields()] == ["schema_version", "declaration"]
    assert sent.declaration == sidecar_pb2.PluginDeclaration()


async def test_the_sdk_declares_the_contract_it_was_built_for(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """v8 on v7: typed delivery, reads within the scope and a statement naming its
    external account with its figures per segment
    (sdk-contract/plugins-read-positions-and-prices), after v6's figures,
    v5's levels and one list of pages, v4's asset class as an enum and v3's
    links and refusal code.

    v8 is the book of record: its commands, reads and deliveries, a oneof
    taken by keyword, and the book's refusal codes (sdk-contract/the-book-holds-positions).

    v9 is the book's refusal of an incomplete entry with each field named,
    and the delegation a caller came through
    (sdk-contract/the-book-refuses-what-downstream-cannot-use,
    sdk-contract/delegations-at-the-deployment-contract).

    v10 is a deployment's own instrument identity: a resolve answering a
    record the deployment minted and stating what its source says, a
    record's sources and offers, and the book's refusal of an incomplete
    instrument record (decisions/030).

    v11 is the edge keeping its own: values as reported, raw records'
    references, provenance, the account kind, pending by value date, a
    backfill, the instrument type and the version's declaration
    (sdk-contract/the-edge-keeps-its-own). A sidecar from before it, still at
    v10, carries none of it, so it refuses the plugin at registration, naming
    both.

    v12 is the deployment's MCP surface: the tools derived from the
    plugin's typed routes, declared at registration, and the tool a call
    names in the claims (sdk-contract/a-deployment-serves-its-mcp-contract).

    v13 is a ticket filed for a person, and what became of those the plugin
    filed (sdk-contract/a-problem-reaches-someone-who-can-act-contract): a
    sidecar still at v12 answers neither call, so it refuses the plugin at
    registration, naming both versions.
    """
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    await plugin.leave()

    (sent,) = service.registered
    assert meridian.SCHEMA_VERSION == "v13"
    assert sent.schema_version == "v13"


async def test_identity_and_grants_come_back(sidecar: tuple[FakeSidecar, str]) -> None:
    """So a plugin can stop at startup when it is not what it expected to be."""
    service, address = sidecar
    service.roles = ("oms", "ems")
    service.publish_grants = ("platform.street.query.list-custodial-positions",)

    plugin = await meridian.connect(address, heartbeat=False)
    try:
        assert plugin.identity.roles == ("oms", "ems")
        assert plugin.identity.instance_id == "custody-snaptrade-1"
        assert plugin.identity.deployment_id == "dep-local-1"
        assert plugin.grants.publish == ("platform.street.query.list-custodial-positions",)
    finally:
        await plugin.leave()


async def test_a_refusal_stops_the_plugin_and_says_why(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """Not retried. A refusal is a statement about configuration."""
    service, address = sidecar
    service.admitted = False
    service.refusal_reason = "access control not loaded"

    with pytest.raises(Refused) as raised:
        await meridian.connect(address, heartbeat=False)
    assert raised.value.reason == "access control not loaded"
    assert len(service.registered) == 1, "a refusal was retried"


async def test_a_page_and_settings_are_declared_at_registration(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(
        address,
        heartbeat=False,
        interface=Interface(port=8000, title="Holdings"),
        settings=[
            Setting("api_key", required=True, secret=True, description="The rail's key"),
            Setting("page_size", kind=int),
        ],
        reads_external_accounts=True,
    )
    await plugin.leave()
    (sent,) = service.registered
    assert sent.schema_version == meridian.SCHEMA_VERSION
    assert sent.interface.loopback_port == 8000 and sent.interface.title == "Holdings"
    assert [(s.name, s.type, s.required, s.secret) for s in sent.settings] == [
        ("api_key", sidecar_pb2.SETTING_TYPE_STRING, True, True),
        ("page_size", sidecar_pb2.SETTING_TYPE_INTEGER, False, False),
    ]
    assert sent.reads_external_accounts


def test_a_setting_of_a_kind_the_contract_does_not_carry_is_refused() -> None:
    with pytest.raises(TypeError, match="str, int or bool"):
        Setting("ratio", kind=float)._declared()


ADMIN = sidecar_pb2.ACCESS_LEVEL_ADMIN
WRITE = sidecar_pb2.ACCESS_LEVEL_WRITE
READ = sidecar_pb2.ACCESS_LEVEL_READ


def test_pages_are_declared_in_order_each_with_the_levels_it_serves() -> None:
    declared = Interface(
        8000,
        "SnapTrade",
        pages=(
            Page("/", "Statements", levels=["write", "read"]),
            Page("/admin/connections", "Connections", levels="admin"),
            Page(
                "/both",
                "Both",
                levels=(meridian.AccessLevel.ACCESS_LEVEL_ADMIN, "ACCESS_LEVEL_READ"),
            ),
        ),
    )._declared()
    assert [(page.path, page.title, list(page.levels)) for page in declared.pages] == [
        ("/", "Statements", [WRITE, READ]),
        ("/admin/connections", "Connections", [ADMIN]),
        ("/both", "Both", [ADMIN, READ]),
    ]
    assert "admin_pages" not in sidecar_pb2.InterfaceDeclaration.DESCRIPTOR.fields_by_name


def test_a_page_naming_no_level_or_one_outside_the_three_is_refused() -> None:
    # W4.8: refused at registration by the sidecar; here, before it is sent.
    with pytest.raises(ValueError, match="names no level"):
        Interface(8000, "x", pages=(Page("/", "Home"),))._declared()
    with pytest.raises(ValueError, match="AccessLevel does not define"):
        Page("/", "Home", levels=["owner"])
    with pytest.raises(ValueError, match="which is no level"):
        Page("/", "Home", levels=["unspecified"])
    with pytest.raises(ValueError, match="begin it with /"):
        Interface(8000, "x", pages=(Page("admin", "Admin", levels="admin"),))._declared()


def test_the_retired_admin_pages_are_still_taken_as_pages_at_admin() -> None:
    """For one release: `meridian plugin migrate` rewrites them into pages."""
    with pytest.warns(DeprecationWarning, match="admin_pages"):
        interface = Interface(
            8000,
            "SnapTrade",
            admin_pages=(
                Page("/admin/connections", "Connections"),
                Page("/admin/accounts", "Accounts"),
            ),
            pages=(Page("/", "Statements", levels=["write", "read"]),),
        )
    declared = interface._declared()
    assert [(page.path, list(page.levels)) for page in declared.pages] == [
        ("/", [WRITE, READ]),
        ("/admin/connections", [ADMIN]),
        ("/admin/accounts", [ADMIN]),
    ]


def test_a_declaration_says_what_the_form_needs() -> None:
    key = Setting(
        "key_type",
        required=True,
        label="Key",
        default="personal",
        choices=(
            Choice("personal", "Personal key", "Belongs to one user."),
            Choice("commercial"),
        ),
    )._declared()
    assert key.type == sidecar_pb2.SETTING_TYPE_CHOICE and key.default_value == "personal"
    assert [choice.value for choice in key.choices] == ["personal", "commercial"]
    assert key.choices[0].label == "Personal key"
    secret = Setting(
        "user_secret",
        required=True,
        secret=True,
        applies_when=AppliesWhen("key_type", ("commercial",)),
    )._declared()
    assert secret.applies_when.setting == "key_type"
    assert list(secret.applies_when.one_of) == ["commercial"]
    poll = Setting("poll_seconds", kind=int, label="Read every", default=300, unit="seconds")
    declared = poll._declared()
    assert (declared.label, declared.default_value, declared.unit) == (
        "Read every",
        "300",
        "seconds",
    )
    assert not declared.HasField("applies_when")
    assert Setting("live", kind=bool, default=False)._declared().default_value == "false"
    synthetic = Setting("synthetic", kind=bool, default=False, developer=True)._declared()
    assert synthetic.developer and not poll.developer


def test_a_declaration_that_cannot_be_rendered_honestly_is_refused() -> None:
    with pytest.raises(ValueError, match="secret"):
        Setting("key", secret=True, default="x")._declared()
    with pytest.raises(TypeError, match="default is not a int"):
        Setting("n", kind=int, default="5")._declared()
    with pytest.raises(ValueError, match="not one of its choices"):
        Setting("k", choices=(Choice("a"),), default="b")._declared()
    with pytest.raises(TypeError, match="its kind is str"):
        Setting("k", kind=int, choices=(Choice("1"),))._declared()


async def test_settings_arrive_typed_by_what_was_declared(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.settings = [
        sidecar_pb2.SettingsDelivery(missing_required=["api_key"]),
        sidecar_pb2.SettingsDelivery(
            values=[
                sidecar_pb2.SettingValue(name="api_key", value="sk-123"),
                sidecar_pb2.SettingValue(name="page_size", value="50"),
                sidecar_pb2.SettingValue(name="live", value="true"),
            ]
        ),
    ]
    plugin = await meridian.connect(
        address,
        heartbeat=False,
        settings=[
            Setting("api_key", required=True),
            Setting("page_size", kind=int),
            Setting("live", kind=bool),
        ],
    )
    try:
        seen = [settings async for settings in plugin.settings()]
    finally:
        await plugin.leave()
    assert seen[0] == Settings(values={}, missing_required=("api_key",))
    assert seen[1].values == {"api_key": "sk-123", "page_size": 50, "live": True}


async def test_an_unset_setting_holds_its_default_and_a_choice_outside_its_options_is_raised(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.settings = [
        sidecar_pb2.SettingsDelivery(),
        sidecar_pb2.SettingsDelivery(
            values=[sidecar_pb2.SettingValue(name="poll_seconds", value="60")]
        ),
        sidecar_pb2.SettingsDelivery(
            values=[sidecar_pb2.SettingValue(name="key_type", value="trial")]
        ),
    ]
    plugin = await meridian.connect(
        address,
        heartbeat=False,
        settings=[
            Setting(
                "key_type",
                default="personal",
                choices=(Choice("personal"), Choice("commercial")),
            ),
            Setting("poll_seconds", kind=int, default=300, unit="seconds"),
        ],
    )
    seen: list[Settings] = []
    try:
        with pytest.raises(ValueError, match="not one of its choices"):
            async for settings in plugin.settings():
                seen.append(settings)
    finally:
        await plugin.leave()
    assert seen[0].values == {"key_type": "personal", "poll_seconds": 300}
    assert seen[1].values == {"key_type": "personal", "poll_seconds": 60}


async def test_a_setting_that_does_not_parse_is_raised_not_guessed(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.settings = [
        sidecar_pb2.SettingsDelivery(
            values=[sidecar_pb2.SettingValue(name="live", value="maybe")]
        )
    ]
    plugin = await meridian.connect(
        address, heartbeat=False, settings=[Setting("live", kind=bool)]
    )
    try:
        with pytest.raises(ValueError, match="not a boolean"):
            async for _ in plugin.settings():
                pass
    finally:
        await plugin.leave()


async def test_the_account_scope_and_the_access_table_arrive(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.scopes = [
        sidecar_pb2.AccountScopeDelivery(
            read_account_ids=["ACC-1", "ACC-2"], write_account_ids=["ACC-1"]
        )
    ]
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        scopes = [scope async for scope in plugin.account_scope()]
        table = await plugin.access()
    finally:
        await plugin.leave()
    assert scopes == [
        AccountScope(read=frozenset({"ACC-1", "ACC-2"}), write=frozenset({"ACC-1"}))
    ]
    assert table.user_groups[0].name == "Operations"


async def test_the_plugins_links_arrive_beside_its_scope_named_and_on_every_change(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    # W4.11: the first delivery at once, so a plugin just started names every
    # link and its account; then each change, a link made here.
    service, address = sidecar
    brokerage = sidecar_pb2.LinkedExternalAccount(
        external_account_id="st-acct-4471", account_id="ACC-1", account_name="Brokerage"
    )
    roth = sidecar_pb2.LinkedExternalAccount(
        external_account_id="st-acct-9902", account_id="ACC-3", account_name="Roth IRA"
    )
    service.scopes = [
        sidecar_pb2.AccountScopeDelivery(
            read_account_ids=["ACC-1"], write_account_ids=["ACC-1"], links=[brokerage]
        ),
        sidecar_pb2.AccountScopeDelivery(
            read_account_ids=["ACC-1", "ACC-3"],
            write_account_ids=["ACC-1", "ACC-3"],
            links=[brokerage, roth],
        ),
    ]
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        first, changed = [scope async for scope in plugin.account_scope()]
    finally:
        await plugin.leave()
    assert first.links == (LinkedExternalAccount("st-acct-4471", "ACC-1", "Brokerage"),)
    assert first.link_of("st-acct-9902") is None, "unlinked until a link names it"
    assert changed.link_of("st-acct-9902") == LinkedExternalAccount(
        "st-acct-9902", "ACC-3", "Roth IRA"
    )
    assert changed.write == frozenset({"ACC-1", "ACC-3"})


def test_a_caller_is_read_from_the_header_its_sidecar_forwarded() -> None:
    claims = sidecar_pb2.CallerClaims(
        subject="local|ada",
        display_name="Ada Park",
        read_account_ids=["ACC-1", "ACC-2"],
        write_account_ids=["ACC-1"],
    )
    assertion = sidecar_pb2.CallerAssertion(
        claims=claims.SerializeToString(), signature=b"sig", key_id="k"
    )
    header = base64.urlsafe_b64encode(assertion.SerializeToString()).decode().rstrip("=")
    caller = Caller.from_header(header)
    assert caller.subject == "local|ada" and caller.display_name == "Ada Park"
    assert caller.may_read("ACC-2") and not caller.may_write("ACC-2")
    assert caller.may_write("ACC-1")
    assert not caller.may_read("ACC-3")
    assert caller.read == {"ACC-1", "ACC-2"} and caller.write == {"ACC-1"}
    assert caller.header == header, "handed back unaltered as acting_for"
    assert not caller.deployment_admin, "absent means not"
    assert caller.level == sidecar_pb2.ACCESS_LEVEL_UNSPECIFIED, "absent means none"
    assert not caller.admin


def test_a_caller_says_the_level_their_session_was_opened_at() -> None:
    """W6.9: Manage opens a session at admin, Open at write, View at read."""
    for level, admin in ((ADMIN, True), (WRITE, False), (READ, False)):
        claims = sidecar_pb2.CallerClaims(subject="local|ada", level=level)
        assertion = sidecar_pb2.CallerAssertion(claims=claims.SerializeToString())
        header = base64.urlsafe_b64encode(assertion.SerializeToString()).decode().rstrip("=")
        caller = Caller.from_header(header)
        assert caller.level == level and caller.admin is admin
        assert Page("/", "Home", levels=[level]).serves(caller)
        assert not Page(
            "/", "Home", levels=[x for x in (ADMIN, WRITE, READ) if x != level]
        ).serves(caller)


def test_access_tag_by_tag_is_gone_and_says_why() -> None:
    """decisions/026: a plugin declares no tags, so a plugin written against
    the SDK that had them fails with the reason and what to read instead,
    rather than with a bare missing name."""
    with pytest.raises(ImportError, match="decisions/026"):
        from meridian import TagAccess  # noqa: F401
    with pytest.raises(ImportError, match=r"Caller\.read"):
        _ = meridian.TagAccess
    with pytest.raises(AttributeError, match="decisions/026"):
        _ = meridian.client.TagAccess
    caller = Caller(subject="s", display_name="d", header="h")
    with pytest.raises(AttributeError, match="read or write"):
        _ = caller.access
    assert not hasattr(caller, "access")
    assert not hasattr(sidecar_pb2, "TagAccess")
    assert "access" not in sidecar_pb2.CallerClaims.DESCRIPTOR.fields_by_name


def test_a_caller_says_whether_they_are_a_deployment_admin() -> None:
    claims = sidecar_pb2.CallerClaims(subject="local|ada", deployment_admin=True)
    assertion = sidecar_pb2.CallerAssertion(claims=claims.SerializeToString())
    header = base64.urlsafe_b64encode(assertion.SerializeToString()).decode().rstrip("=")
    assert Caller.from_header(header).deployment_admin


async def test_the_client_heartbeats_without_being_asked(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plugin author who has to remember this is one who will forget."""
    service, address = sidecar
    monkeypatch.setattr(meridian.client, "HEARTBEAT_SECONDS", 0.01)

    plugin = await meridian.connect(address)
    try:
        beats = await service.beats_from(0)
        assert all(beat.healthy for beat in beats)
    finally:
        await plugin.leave()


async def test_a_reported_health_stands_until_reported_again(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plugin that said it is unwell is not declared well by its own next
    automatic beat: the health it reported, with its detail, goes on every
    heartbeat after, as its figures do, until it reports healthy again."""
    service, address = sidecar
    monkeypatch.setattr(meridian.client, "HEARTBEAT_SECONDS", 0.01)
    plugin = await meridian.connect(address)
    try:
        await plugin.report(healthy=False, detail="brokerage credentials rejected")
        beats = await service.beats_from(service.mark())
        assert all(
            (beat.healthy, beat.detail) == (False, "brokerage credentials rejected")
            for beat in beats
        )

        await plugin.report(healthy=True)
        beats = await service.beats_from(service.mark())
        assert all((beat.healthy, beat.detail) == (True, "") for beat in beats)
    finally:
        await plugin.leave()


async def test_figures_refused_leave_the_health_as_it_was(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A report refused before sending sets nothing: neither its figures nor
    its health stand on the beats after it."""
    service, address = sidecar
    monkeypatch.setattr(meridian.client, "HEARTBEAT_SECONDS", 0.01)
    plugin = await meridian.connect(address)
    try:
        with pytest.raises(ValueError, match="at most 8"):
            await plugin.report(
                healthy=False,
                detail="never sent",
                figures=[meridian.Figure(f"F{i}", i) for i in range(9)],
            )
        beats = await service.beats_from(service.mark())
        assert all((beat.healthy, beat.detail) == (True, "") for beat in beats)
    finally:
        await plugin.leave()


async def test_leaving_says_why_and_closes_the_plugin(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """Saying so is what distinguishes a planned stop from a failure."""
    service, address = sidecar

    async with await meridian.connect(address, heartbeat=False) as plugin:
        pass

    (departure,) = service.left
    assert departure.reason == "stopping"
    with pytest.raises(NotRegistered):
        await plugin.record_holdings_statement(source="snaptrade", expected_rows=1)


async def test_an_exception_leaves_with_the_reason(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar

    with pytest.raises(RuntimeError):
        async with await meridian.connect(address, heartbeat=False):
            raise RuntimeError("the brokerage went away")

    (departure,) = service.left
    assert departure.reason == "RuntimeError"


async def test_a_sidecar_that_starts_after_the_plugin_is_waited_for() -> None:
    """A plugin and its sidecar start together, in no promised order."""
    import socket

    import grpc

    from conftest import FakeOperations
    from meridian.plugin.v1 import operations_pb2_grpc
    from meridian.v1 import sidecar_pb2_grpc

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    service = FakeSidecar()

    async def start_late() -> grpc.aio.Server:
        await asyncio.sleep(0.5)
        server = grpc.aio.server()
        sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
        operations_pb2_grpc.add_PluginOperationsServicer_to_server(FakeOperations(), server)
        server.add_insecure_port(f"127.0.0.1:{port}")
        await server.start()
        return server

    starting = asyncio.create_task(start_late())
    plugin = await meridian.connect(f"127.0.0.1:{port}", heartbeat=False, wait=10)
    server = await starting
    try:
        assert plugin.identity.instance_id == "custody-snaptrade-1"
    finally:
        await plugin.leave()
        await server.stop(grace=None)


async def test_no_sidecar_at_all_is_said_so_once_the_wait_is_over() -> None:
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with pytest.raises(meridian.NoSidecar) as raised:
        await meridian.connect(f"127.0.0.1:{port}", heartbeat=False, wait=0.5)
    assert f"127.0.0.1:{port}" in str(raised.value)


def test_a_caller_through_a_client_names_its_delegation_and_a_browser_none() -> None:
    """W6.18 (contract v9): the claims name the delegation and client a person
    came through; the person stays the subject."""
    from meridian.testing import caller_header

    through = meridian.Caller.from_header(
        caller_header(
            "write",
            write={"ACC-1"},
            delegation_id="DLG-1",
            client_name="meridian on ada-laptop",
        )
    )
    assert through.subject == "local|ada"
    assert through.delegation_id == "DLG-1"
    assert through.client_name == "meridian on ada-laptop"
    assert through.through_a_client
    browser = meridian.Caller.from_header(caller_header("write", write={"ACC-1"}))
    assert (browser.delegation_id, browser.client_name) == ("", "")
    assert not browser.through_a_client
