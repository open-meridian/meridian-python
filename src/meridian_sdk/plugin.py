"""A plugin's whole contract with the platform.

The sidecar implements the operations; this is a gRPC client that calls them
over loopback. Nothing here decides anything. Access control, provenance
stamping, correlation and the bus itself live on the other side of the socket,
which is the point: a plugin that could decide any of those is a plugin that
could get them wrong, and there would be one copy per plugin to fix.

So the rule for anything added here is that it must be a convenience, never a
decision. Running the heartbeat is a convenience. Deciding whether a publish is
allowed would not be, and is not offered even though the grants are right there
in `Plugin.grants`: those are for failing early with a good message, and the
sidecar refuses independently whatever this client believes.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from types import TracebackType

import grpc
from google.protobuf.message import Message
from meridian.v1 import envelope_pb2, sidecar_pb2, sidecar_pb2_grpc

from .errors import CallFailed, NotGranted, NotRegistered, Refused

#: The schema version this SDK was generated against. Sent at registration so a
#: mismatch is refused at the door rather than found later in a decode failure.
SCHEMA_VERSION = "v1"

#: Where a sidecar listens. Loopback, always: a sidecar reachable from another
#: host is a way around the boundary it exists to enforce.
DEFAULT_ADDRESS = "127.0.0.1:9191"

#: How often liveness is reported. The sidecar's own view of a plugin that has
#: stopped sending these is the more informative signal, so this is deliberately
#: frequent enough that silence means something within seconds.
HEARTBEAT_SECONDS = 5.0

_CALL_FAILURES = {
    sidecar_pb2.CALL_FAILURE_TIMEOUT: "timeout",
    sidecar_pb2.CALL_FAILURE_REFUSED: "refused",
    sidecar_pb2.CALL_FAILURE_NO_HANDLER: "no handler",
    sidecar_pb2.CALL_FAILURE_HANDLER_ERROR: "handler error",
}


@dataclass(frozen=True)
class Identity:
    """Who this plugin was launched to be.

    Read from the registration reply, never sent. These decide the plugin's
    topic access, so a plugin that could name them would be choosing its own
    privileges. A plugin that cares can compare them against what it expected
    and stop.
    """

    instance_id: str
    role: str
    tags: tuple[str, ...] = ()
    deployment_id: str = ""


@dataclass(frozen=True)
class Grants:
    """What the deployment allowed, as the patterns it allowed them as.

    Returned at registration so a plugin can fail at startup rather than at its
    first refused publish, which puts the failure where an operator is already
    looking.
    """

    publish: tuple[str, ...] = ()
    subscribe: tuple[str, ...] = ()


@dataclass(frozen=True)
class Delivery:
    """One message off a subscription.

    The envelope is handed over whole. Its metadata was stamped by the sidecar,
    so `meta.publisher_instance_id` is who really published rather than who
    claimed to.
    """

    envelope: envelope_pb2.Envelope

    @property
    def meta(self) -> envelope_pb2.MessageMeta:
        return self.envelope.meta

    @property
    def topic(self) -> str:
        return str(self.envelope.meta.topic)

    def unpack(self, message: Message) -> Message:
        """Parse the payload into `message`, checking it is what it says it is.

        The type name travels beside the bytes, so a payload parsed as the wrong
        type is catchable here rather than surfacing as absent fields later.
        Protobuf will happily decode mismatched bytes into a message with
        everything unset, which looks like an empty statement rather than a bug.
        """
        expected = message.DESCRIPTOR.full_name
        actual = self.envelope.payload_type
        if actual != expected:
            raise ValueError(f"{self.topic} carried {actual}, not {expected}")
        message.ParseFromString(self.envelope.payload)
        return message


@dataclass
class Plugin:
    """A registered plugin.

    Built by `connect`, which registers before returning, so an instance of this
    is always one that was admitted.
    """

    identity: Identity
    grants: Grants
    _channel: grpc.aio.Channel
    _stub: sidecar_pb2_grpc.SidecarServiceStub
    _heartbeat: asyncio.Task[None] | None = field(default=None, repr=False)
    _left: bool = field(default=False, repr=False)

    async def publish(
        self,
        topic: str,
        payload: Message,
        *,
        correlation_id: str = "",
        causation_id: str = "",
    ) -> str:
        """Send one message. Returns the identifier the sidecar stamped on it.

        Identity and publish time are not parameters and cannot be: a component
        that can forge its provenance makes the audit trail decorative.
        """
        self._check_open()
        reply = await self._stub.Publish(
            sidecar_pb2.PublishRequest(
                topic=topic,
                payload_type=payload.DESCRIPTOR.full_name,
                payload=payload.SerializeToString(),
                correlation_id=correlation_id,
                causation_id=causation_id,
            )
        )
        if not reply.accepted:
            raise NotGranted(topic, reply.refusal_reason)
        return str(reply.message_id)

    async def subscribe(self, pattern: str) -> AsyncIterator[Delivery]:
        """Receive messages matching `pattern` until the stream closes.

        Delivery is at-most-once. A message dropped because this consumer was
        slow is gone, and the sidecar counts it rather than blocking the
        publisher, so a plugin that falls behind loses data quietly by design.
        Do the slow thing elsewhere.
        """
        self._check_open()
        stream = self._stub.Subscribe(sidecar_pb2.SubscribeRequest(pattern=pattern))
        try:
            async for delivery in stream:
                yield Delivery(envelope=delivery.envelope)
        except grpc.aio.AioRpcError as failed:
            if failed.code() is grpc.StatusCode.PERMISSION_DENIED:
                raise NotGranted(pattern, failed.details() or "") from failed
            raise

    async def call(
        self,
        topic: str,
        request: Message,
        reply: Message,
        *,
        timeout_ms: int = 0,
        correlation_id: str = "",
    ) -> Message:
        """Ask a question and wait for the answer, bounded in time.

        `reply` is the message the answer is parsed into, supplied by the caller
        because the topic alone does not say what comes back.
        """
        self._check_open()
        answer = await self._stub.Call(
            sidecar_pb2.CallRequest(
                topic=topic,
                payload_type=request.DESCRIPTOR.full_name,
                payload=request.SerializeToString(),
                correlation_id=correlation_id,
                timeout_ms=timeout_ms,
            )
        )
        if not answer.ok:
            raise CallFailed(
                topic,
                _CALL_FAILURES.get(answer.failure, "unspecified"),
                answer.failure_detail,
            )
        expected = reply.DESCRIPTOR.full_name
        if answer.payload_type != expected:
            raise ValueError(f"{topic} answered with {answer.payload_type}, not {expected}")
        reply.ParseFromString(answer.payload)
        return reply

    async def report(self, *, healthy: bool, detail: str = "") -> None:
        """Report liveness once, out of band of the automatic heartbeat.

        For a plugin that knows it is unwell and should say so before the next
        tick, rather than for ordinary liveness, which is already handled.
        """
        self._check_open()
        await self._stub.Heartbeat(sidecar_pb2.HeartbeatRequest(healthy=healthy, detail=detail))

    async def leave(self, reason: str = "") -> None:
        """Say this plugin is stopping, and stop.

        Optional by nature, because a crash skips it. Saying so is what
        distinguishes a planned stop from a failure, which the timeout path
        cannot do.
        """
        if self._left:
            return
        self._left = True
        if self._heartbeat is not None:
            self._heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat
        # Best effort. A sidecar already gone is the ordinary case during a
        # shutdown, and failing here would turn a clean stop into a traceback.
        with contextlib.suppress(grpc.aio.AioRpcError):
            await self._stub.Leave(sidecar_pb2.LeaveRequest(reason=reason))
        # No grace period: Leave has already been sent and answered, so there is
        # nothing in flight worth waiting for.
        await self._channel.close(None)

    async def __aenter__(self) -> Plugin:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.leave("stopping" if exc is None else f"{type(exc).__name__}")

    def _check_open(self) -> None:
        if self._left:
            raise NotRegistered("this plugin has left; nothing more may be done on it")

    async def _beat(self) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            # A sidecar that has gone away is not this loop's problem to solve.
            # The next real operation surfaces it with context; failing here
            # would raise from a background task nobody awaited.
            with contextlib.suppress(grpc.aio.AioRpcError):
                await self._stub.Heartbeat(sidecar_pb2.HeartbeatRequest(healthy=True))


async def connect(
    address: str | None = None,
    *,
    heartbeat: bool = True,
) -> Plugin:
    """Register with the sidecar and return the admitted plugin.

    The address defaults to `MERIDIAN_SIDECAR_ADDRESS`, then to loopback. No
    other configuration is read, because there is no other configuration: the
    sidecar knows the deployment, the bus, the grants and who this plugin is.

    Raises `Refused` when the sidecar declines, carrying its reason. Refusals
    are not retried; every one of them is a statement about configuration, and
    none resolves by asking again.
    """
    target = address or os.environ.get("MERIDIAN_SIDECAR_ADDRESS") or DEFAULT_ADDRESS
    channel = grpc.aio.insecure_channel(target)
    stub = sidecar_pb2_grpc.SidecarServiceStub(channel)

    try:
        reply = await stub.Register(sidecar_pb2.RegisterRequest(schema_version=SCHEMA_VERSION))
    except BaseException:
        await channel.close(None)
        raise

    if not reply.admitted:
        await channel.close(None)
        raise Refused(reply.refusal_reason)

    plugin = Plugin(
        identity=Identity(
            instance_id=reply.instance_id,
            role=reply.role,
            tags=tuple(reply.tags),
            deployment_id=reply.deployment_id,
        ),
        grants=Grants(
            publish=tuple(reply.publish_grants),
            subscribe=tuple(reply.subscribe_grants),
        ),
        _channel=channel,
        _stub=stub,
    )
    if heartbeat:
        plugin._heartbeat = asyncio.create_task(plugin._beat())
    return plugin
