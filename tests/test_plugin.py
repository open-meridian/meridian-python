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
from meridian import AccountScope, Caller, Interface, NotRegistered, Refused, Setting, Settings
from meridian.v1 import sidecar_pb2


async def test_registering_sends_no_identity(sidecar: tuple[FakeSidecar, str]) -> None:
    """The thing a plugin must not be able to do is the thing to assert.

    Instance, roles and tags moved to the sidecar's launch configuration, so
    there is no field here to fill in. A client that grew one back would be
    letting a plugin choose its own privileges.
    """
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    await plugin.leave()

    (sent,) = service.registered
    assert sent.schema_version == "v2"
    assert not sent.ListFields() or [f.name for f, _ in sent.ListFields()] == ["schema_version"]


async def test_identity_and_grants_come_back(sidecar: tuple[FakeSidecar, str]) -> None:
    """So a plugin can stop at startup when it is not what it expected to be."""
    service, address = sidecar
    service.roles = ("oms", "ems")
    service.tags = ("routing",)
    service.publish_grants = ("platform.street.query.list-custodial-positions",)

    plugin = await meridian.connect(address, heartbeat=False)
    try:
        assert plugin.identity.roles == ("oms", "ems")
        assert plugin.identity.instance_id == "custody-snaptrade-1"
        assert plugin.identity.tags == ("routing",)
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
    assert sent.schema_version == "v2"
    assert sent.interface.loopback_port == 8000 and sent.interface.title == "Holdings"
    assert [(s.name, s.type, s.required, s.secret) for s in sent.settings] == [
        ("api_key", sidecar_pb2.SETTING_TYPE_STRING, True, True),
        ("page_size", sidecar_pb2.SETTING_TYPE_INTEGER, False, False),
    ]
    assert sent.reads_external_accounts


def test_a_setting_of_a_kind_the_contract_does_not_carry_is_refused() -> None:
    with pytest.raises(TypeError, match="str, int or bool"):
        Setting("ratio", kind=float)._declared()


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


def test_a_caller_is_read_from_the_header_its_sidecar_forwarded() -> None:
    claims = sidecar_pb2.CallerClaims(
        subject="local|ada",
        display_name="Ada Park",
        access=[
            sidecar_pb2.TagAccess(
                tag="custody", read_account_ids=["ACC-1", "ACC-2"], write_account_ids=["ACC-1"]
            )
        ],
    )
    assertion = sidecar_pb2.CallerAssertion(
        claims=claims.SerializeToString(), signature=b"sig", key_id="k"
    )
    header = base64.urlsafe_b64encode(assertion.SerializeToString()).decode().rstrip("=")
    caller = Caller.from_header(header)
    assert caller.subject == "local|ada" and caller.display_name == "Ada Park"
    assert caller.may_read("ACC-2") and not caller.may_write("ACC-2")
    assert caller.may_write("ACC-1")
    assert caller.header == header, "handed back unaltered as acting_for"


async def test_the_client_heartbeats_without_being_asked(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plugin author who has to remember this is one who will forget."""
    service, address = sidecar
    monkeypatch.setattr(meridian.client, "HEARTBEAT_SECONDS", 0.01)

    plugin = await meridian.connect(address)
    try:
        await asyncio.sleep(0.1)
        assert service.heartbeats, "no heartbeat was sent"
        assert all(beat.healthy for beat in service.heartbeats)
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
