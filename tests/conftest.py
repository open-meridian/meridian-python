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
from meridian.v1 import envelope_pb2, sidecar_pb2, sidecar_pb2_grpc


@dataclass
class FakeSidecar(sidecar_pb2_grpc.SidecarServiceServicer):
    admitted: bool = True
    refusal_reason: str = ""
    instance_id: str = "custody-snaptrade-1"
    role: str = "custody"
    tags: tuple[str, ...] = ()
    publish_grants: tuple[str, ...] = ("platform.kernel.command.record-holding",)
    subscribe_grants: tuple[str, ...] = ("platform.reference.event.instrument-applied",)

    publish_accepted: bool = True
    publish_refusal: str = ""
    call_reply: sidecar_pb2.CallReply | None = None
    deliveries: list[envelope_pb2.Envelope] = field(default_factory=list)
    subscribe_status: grpc.StatusCode | None = None

    # What the client actually sent, so a test can assert the client did not
    # supply something it must not be able to supply.
    registered: list[sidecar_pb2.RegisterRequest] = field(default_factory=list)
    published: list[sidecar_pb2.PublishRequest] = field(default_factory=list)
    called: list[sidecar_pb2.CallRequest] = field(default_factory=list)
    heartbeats: list[sidecar_pb2.HeartbeatRequest] = field(default_factory=list)
    left: list[sidecar_pb2.LeaveRequest] = field(default_factory=list)

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
            role=self.role,
            tags=list(self.tags),
            publish_grants=list(self.publish_grants),
            subscribe_grants=list(self.subscribe_grants),
        )

    async def Publish(  # noqa: N802
        self, request: sidecar_pb2.PublishRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.PublishReply:
        self.published.append(request)
        if not self.publish_accepted:
            return sidecar_pb2.PublishReply(accepted=False, refusal_reason=self.publish_refusal)
        return sidecar_pb2.PublishReply(accepted=True, message_id="msg-1")

    async def Subscribe(  # noqa: N802
        self, request: sidecar_pb2.SubscribeRequest, context: grpc.aio.ServicerContext
    ) -> AsyncIterator[sidecar_pb2.Delivery]:
        if self.subscribe_status is not None:
            await context.abort(self.subscribe_status, "no grant covers that pattern")
        for envelope in self.deliveries:
            yield sidecar_pb2.Delivery(envelope=envelope)

    async def Call(  # noqa: N802
        self, request: sidecar_pb2.CallRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.CallReply:
        self.called.append(request)
        return self.call_reply or sidecar_pb2.CallReply(ok=True)

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
    """
    monkeypatch.delenv("MERIDIAN_SIDECAR_ADDRESS", raising=False)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


__all__ = ["FakeSidecar", "asyncio", "sidecar"]
