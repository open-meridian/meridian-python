"""A sidecar that answers, so the client can be tested without a runtime.

Deliberately not a mock. It is a real gRPC server on a real socket speaking the
real generated stubs, because the things worth catching here are wire-level:
a field set on the wrong message, a stream that does not terminate, a status
code the client does not translate. A mock would agree with whatever the client
did and prove nothing.

What it does not do is enforce anything. It refuses what a test tells it to
refuse. Access control is the sidecar's job and is tested in meridian-core
against the real grant table; repeating a weaker version of it here would make
this suite look like it covers something it does not.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import grpc
import pytest
import pytest_asyncio

from meridian.plugin.v1 import operations_pb2, operations_pb2_grpc
from meridian.v1 import sidecar_pb2, sidecar_pb2_grpc


@dataclass
class FakeOperations(operations_pb2_grpc.PluginOperationsServicer):
    """The typed operations, answering fixed results and keeping what was sent."""

    refuse: tuple[grpc.StatusCode, str] | None = None
    sent: list[object] = field(default_factory=list)

    async def _answer(
        self, params: object, answer: object, context: grpc.aio.ServicerContext
    ) -> object:
        self.sent.append(params)
        if self.refuse is not None:
            await context.abort(*self.refuse)
        return answer

    async def ReportSyncStatus(self, request, context):  # noqa: N802
        return await self._answer(
            request, operations_pb2.Published(message_id="msg-1"), context
        )

    async def RecordHoldingsStatement(self, request, context):  # noqa: N802
        answer = operations_pb2.RecordHoldingsStatementResult(statement_id="S-1")
        return await self._answer(request, answer, context)

    async def RecordHolding(self, request, context):  # noqa: N802
        answer = operations_pb2.RecordHoldingResult(holding_id="H-1", resolved=True)
        return await self._answer(request, answer, context)

    async def ResolveIdentifier(self, request, context):  # noqa: N802
        answer = operations_pb2.ResolveIdentifierResult(found=True, instrument_id="INS-1")
        return await self._answer(request, answer, context)

    async def ReportMissingInstrument(self, request, context):  # noqa: N802
        return await self._answer(
            request, operations_pb2.Published(message_id="msg-2"), context
        )


@dataclass
class FakeSidecar(sidecar_pb2_grpc.SidecarServiceServicer):
    admitted: bool = True
    refusal_reason: str = ""
    instance_id: str = "custody-snaptrade-1"
    roles: tuple[str, ...] = ("custody",)
    tags: tuple[str, ...] = ()
    publish_grants: tuple[str, ...] = ("platform.street.command.record-holding",)
    subscribe_grants: tuple[str, ...] = ("platform.reference.event.instrument-applied",)

    # What the streams send, each item once and then the stream ends.
    settings: list[sidecar_pb2.SettingsDelivery] = field(default_factory=list)
    scopes: list[sidecar_pb2.AccountScopeDelivery] = field(default_factory=list)

    # What the client actually sent, so a test can assert the client did not
    # supply something it must not be able to supply.
    registered: list[sidecar_pb2.RegisterRequest] = field(default_factory=list)
    heartbeats: list[sidecar_pb2.HeartbeatRequest] = field(default_factory=list)
    left: list[sidecar_pb2.LeaveRequest] = field(default_factory=list)
    operations: FakeOperations = field(default_factory=FakeOperations)

    async def Register(  # noqa: N802 - the generated name
        self, request: sidecar_pb2.RegisterRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.RegisterReply:
        self.registered.append(request)
        if not self.admitted:
            return sidecar_pb2.RegisterReply(admitted=False, refusal_reason=self.refusal_reason)
        return sidecar_pb2.RegisterReply(
            admitted=True,
            deployment_id="dep-local-1",
            instance_id=self.instance_id,
            roles=list(self.roles),
            tags=list(self.tags),
            publish_grants=list(self.publish_grants),
            subscribe_grants=list(self.subscribe_grants),
        )

    async def WatchSettings(  # noqa: N802
        self, request: sidecar_pb2.WatchSettingsRequest, context: grpc.aio.ServicerContext
    ) -> AsyncIterator[sidecar_pb2.SettingsDelivery]:
        for delivered in self.settings:
            yield delivered

    async def WatchAccountScope(  # noqa: N802
        self, request: sidecar_pb2.WatchAccountScopeRequest, context: grpc.aio.ServicerContext
    ) -> AsyncIterator[sidecar_pb2.AccountScopeDelivery]:
        for delivered in self.scopes:
            yield delivered

    async def PluginAccess(  # noqa: N802
        self, request: sidecar_pb2.PluginAccessRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.PluginAccessReply:
        return sidecar_pb2.PluginAccessReply(
            user_groups=[sidecar_pb2.UserGroupAccess(user_group_id="UG-1", name="Operations")]
        )

    async def Heartbeat(  # noqa: N802
        self, request: sidecar_pb2.HeartbeatRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.HeartbeatReply:
        self.heartbeats.append(request)
        return sidecar_pb2.HeartbeatReply()

    async def Leave(  # noqa: N802
        self, request: sidecar_pb2.LeaveRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.LeaveReply:
        self.left.append(request)
        return sidecar_pb2.LeaveReply()


@pytest_asyncio.fixture
async def sidecar() -> AsyncIterator[tuple[FakeSidecar, str]]:
    """A running fake on an ephemeral loopback port."""
    service = FakeSidecar()
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(service.operations, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield service, f"127.0.0.1:{port}"
    finally:
        await server.stop(grace=None)


@pytest.fixture(autouse=True)
def no_ambient_address(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests name their address.

    Without this a developer with the variable set in their shell would run a
    different suite from CI, and the one that passes is the one nobody trusts.

    test_interop.py wants the opposite and reads the variable at import, before
    this runs. Do not "fix" that by narrowing this fixture: the protection is
    worth more than the tidiness, and the interop suite is the exception rather
    than the rule.
    """
    monkeypatch.delenv("MERIDIAN_SIDECAR_ADDRESS", raising=False)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


__all__ = ["FakeOperations", "FakeSidecar", "asyncio", "sidecar"]
