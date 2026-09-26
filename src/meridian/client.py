"""A plugin's whole contract with the platform.

The sidecar implements the operations; this is a gRPC client that calls them
over loopback. Nothing here decides anything. Access control, provenance
stamping, correlation and the bus itself live on the other side of the socket,
which is the point: a plugin that could decide any of those is a plugin that
could get them wrong, and there would be one copy per plugin to fix.

So the rule for anything added here is that it must be a convenience, never a
decision. Running the heartbeat is a convenience. Deciding whether an operation
is allowed would not be, and is not offered even though the grants are right
there in `Plugin.grants`: those are for failing early with a good message, and
the sidecar refuses independently whatever this client believes.

Contract v2 (decisions/013): a plugin reaches the bus through its typed
operations and nothing else. What it learns from the deployment -- its
settings, its account scope, who may use it -- it learns here, and who is
asking for its page it reads from the one header its sidecar forwards.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, TypeVar

import grpc

from meridian.plugin.v1 import operations_pb2_grpc
from meridian.v1 import sidecar_pb2, sidecar_pb2_grpc

from .errors import CallFailed, NotGranted, NotRegistered, Refused
from .operations import Operations

#: The schema version this SDK was generated against. Sent at registration so a
#: mismatch is refused at the door rather than found later in a decode failure.
SCHEMA_VERSION = "v2"

#: Where a sidecar listens. Loopback, always: a sidecar reachable from another
#: host is a way around the boundary it exists to enforce.
DEFAULT_ADDRESS = "127.0.0.1:9191"

#: How often liveness is reported. The sidecar's own view of a plugin that has
#: stopped sending these is the more informative signal, so this is deliberately
#: frequent enough that silence means something within seconds.
HEARTBEAT_SECONDS = 5.0

# A typed operation's refusal, by the status the sidecar chose for it
# (spec/typed-sidecar-operations): each asks something different of the caller.
_OPERATION_FAILURES = {
    grpc.StatusCode.FAILED_PRECONDITION: "refused",
    grpc.StatusCode.UNAVAILABLE: "no handler",
    grpc.StatusCode.DEADLINE_EXCEEDED: "timeout",
    grpc.StatusCode.ABORTED: "handler error",
    grpc.StatusCode.INVALID_ARGUMENT: "invalid",
    grpc.StatusCode.UNAUTHENTICATED: "not vouched for",
}

_SETTING_TYPES = {
    str: sidecar_pb2.SETTING_TYPE_STRING,
    int: sidecar_pb2.SETTING_TYPE_INTEGER,
    bool: sidecar_pb2.SETTING_TYPE_BOOLEAN,
}

_Answer = TypeVar("_Answer")


@dataclass(frozen=True)
class Identity:
    """Who this plugin was launched to be.

    Read from the registration reply, never sent. The roles decide the
    plugin's topic access -- one or more from the deployment's fixed list, the
    union of their grants, or none, which is a plugin admitted with no topics
    -- so a plugin that could name them would be choosing its own privileges.
    The tags are its parts, for people, and grant nothing on the bus. A plugin
    that cares can compare these against what it expected and stop.
    """

    instance_id: str
    roles: tuple[str, ...] = ()
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
class Interface:
    """A page the plugin serves to people, on loopback (W6.9).

    Only the plugin's sidecar reaches it, forwarding requests the dashboard
    vouched for; who is asking is in the `Meridian-Caller` header, which
    `Caller.from_header` reads.
    """

    port: int
    title: str


@dataclass(frozen=True)
class Setting:
    """One setting the plugin needs, declared at registration (W4.7).

    `kind` is str, int or bool. A secret is set through the dashboard and never
    read back, displayed, logged, reported or bundled; the plugin receives it
    in `Settings` and nowhere else.
    """

    name: str
    kind: type = str
    required: bool = False
    secret: bool = False
    description: str = ""

    def _declared(self) -> sidecar_pb2.SettingDeclaration:
        if self.kind not in _SETTING_TYPES:
            raise TypeError(f"setting {self.name} is a {self.kind.__name__}; str, int or bool")
        return sidecar_pb2.SettingDeclaration(
            name=self.name,
            type=_SETTING_TYPES[self.kind],
            required=self.required,
            secret=self.secret,
            description=self.description,
        )

    def _parsed(self, text: str) -> str | int | bool:
        if self.kind is bool:
            if text.lower() in ("true", "yes", "1", "on"):
                return True
            if text.lower() in ("false", "no", "0", "off"):
                return False
            raise ValueError(f"setting {self.name} is not a boolean: {text!r}")
        if self.kind is int:
            return int(text)
        return text


@dataclass(frozen=True)
class Settings:
    """The plugin's settings as the deployment holds them, typed by what it
    declared, and the required ones it holds nothing for yet. While any is
    missing the sidecar reports the plugin unhealthy, naming it."""

    values: dict[str, str | int | bool]
    missing_required: tuple[str, ...] = ()


@dataclass(frozen=True)
class AccountScope:
    """Every account anybody may read, or write, through this plugin (W4.11).

    A plugin reads its whole read scope as itself and serves each person only
    what their access allows; a write outside `write` is refused by the
    sidecar whoever it is for.
    """

    read: frozenset[str] = frozenset()
    write: frozenset[str] = frozenset()


@dataclass(frozen=True)
class TagAccess:
    """What a person may do through one tag of this plugin."""

    tag: str
    read: frozenset[str] = frozenset()
    write: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Caller:
    """Who a request for the plugin's page came from, as the dashboard vouched
    and the sidecar verified before forwarding it (W6.9).

    Read, not verified: only the sidecar can reach the page, and it removed
    every other claim the request arrived with. Hand `header` back as
    `acting_for` on a command to send it for this person (W4.9).
    """

    subject: str
    display_name: str
    access: tuple[TagAccess, ...]
    header: str

    @classmethod
    def from_header(cls, header: str) -> Caller:
        padded = header + "=" * (-len(header) % 4)
        assertion = sidecar_pb2.CallerAssertion.FromString(base64.urlsafe_b64decode(padded))
        claims = sidecar_pb2.CallerClaims.FromString(assertion.claims)
        return cls(
            subject=claims.subject,
            display_name=claims.display_name,
            access=tuple(
                TagAccess(
                    tag=held.tag,
                    read=frozenset(held.read_account_ids),
                    write=frozenset(held.write_account_ids),
                )
                for held in claims.access
            ),
            header=header,
        )

    def may_read(self, account_id: str) -> bool:
        return any(account_id in held.read for held in self.access)

    def may_write(self, account_id: str) -> bool:
        return any(account_id in held.write for held in self.access)


@dataclass
class Plugin(Operations):
    """A registered plugin.

    Built by `connect`, which registers before returning, so an instance of this
    is always one that was admitted. Its typed operations -- `record_holding`,
    `resolve_identifier` and the rest -- are generated from the contract into
    `Operations`, one per workflow step its roles may take.
    """

    identity: Identity
    grants: Grants
    _channel: grpc.aio.Channel
    _stub: sidecar_pb2_grpc.SidecarServiceStub
    _operations_stub: operations_pb2_grpc.PluginOperationsStub
    _heartbeat: asyncio.Task[None] | None = field(default=None, repr=False)
    _left: bool = field(default=False, repr=False)

    _declared: tuple[Setting, ...] = field(default=(), repr=False)

    async def settings(self) -> AsyncIterator[Settings]:
        """The settings it declared, now and again on every change (W4.7).

        Each is typed by its declaration; a value that does not parse is
        raised rather than guessed at.
        """
        self._check_open()
        by_name = {setting.name: setting for setting in self._declared}
        async for delivered in self._stub.WatchSettings(sidecar_pb2.WatchSettingsRequest()):
            yield Settings(
                values={
                    held.name: by_name[held.name]._parsed(held.value)
                    for held in delivered.values
                    if held.name in by_name
                },
                missing_required=tuple(delivered.missing_required),
            )

    async def account_scope(self) -> AsyncIterator[AccountScope]:
        """Its account scope, now and again on every change (W4.11)."""
        self._check_open()
        async for delivered in self._stub.WatchAccountScope(
            sidecar_pb2.WatchAccountScopeRequest()
        ):
            yield AccountScope(
                read=frozenset(delivered.read_account_ids),
                write=frozenset(delivered.write_account_ids),
            )

    async def access(self) -> sidecar_pb2.PluginAccessReply:
        """Who may use this plugin: each user group naming it, and each person
        who has signed in, with their access (W4.10). For shaping an interface;
        nothing here is an access decision."""
        self._check_open()
        reply: sidecar_pb2.PluginAccessReply = await self._stub.PluginAccess(
            sidecar_pb2.PluginAccessRequest()
        )
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

    def _operations(self) -> Any:
        return self._operations_stub

    async def _operate(
        self, method: Callable[[Any], Awaitable[_Answer]], params: Any
    ) -> _Answer:
        """One typed operation, its refusal turned into this package's terms."""
        self._check_open()
        operation = type(params).__name__.removesuffix("Params")
        try:
            return await method(params)
        except grpc.aio.AioRpcError as failed:
            detail = failed.details() or ""
            if failed.code() is grpc.StatusCode.PERMISSION_DENIED:
                raise NotGranted(operation, detail) from failed
            kind = _OPERATION_FAILURES.get(failed.code())
            if kind is None:
                raise
            raise CallFailed(operation, kind, detail) from failed

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
    interface: Interface | None = None,
    settings: Sequence[Setting] = (),
    reads_external_accounts: bool = False,
) -> Plugin:
    """Register with the sidecar and return the admitted plugin.

    The address defaults to `MERIDIAN_SIDECAR_ADDRESS`, then to loopback. No
    other configuration is read, because there is no other configuration: the
    sidecar knows the deployment, the bus, the grants and who this plugin is.
    What the plugin declares is what it offers and needs: a page, its settings,
    and whether it reads accounts from an external source.

    Raises `Refused` when the sidecar declines, carrying its reason. Refusals
    are not retried; every one of them is a statement about configuration, and
    none resolves by asking again.
    """
    target = address or os.environ.get("MERIDIAN_SIDECAR_ADDRESS") or DEFAULT_ADDRESS
    channel = grpc.aio.insecure_channel(target)
    stub = sidecar_pb2_grpc.SidecarServiceStub(channel)

    try:
        reply = await stub.Register(
            sidecar_pb2.RegisterRequest(
                schema_version=SCHEMA_VERSION,
                interface=(
                    sidecar_pb2.InterfaceDeclaration(
                        loopback_port=interface.port, title=interface.title
                    )
                    if interface is not None
                    else None
                ),
                settings=[setting._declared() for setting in settings],
                reads_external_accounts=reads_external_accounts,
            )
        )
    except BaseException:
        await channel.close(None)
        raise

    if not reply.admitted:
        await channel.close(None)
        raise Refused(reply.refusal_reason)

    plugin = Plugin(
        identity=Identity(
            instance_id=reply.instance_id,
            roles=tuple(reply.roles),
            tags=tuple(reply.tags),
            deployment_id=reply.deployment_id,
        ),
        grants=Grants(
            publish=tuple(reply.publish_grants),
            subscribe=tuple(reply.subscribe_grants),
        ),
        _channel=channel,
        _stub=stub,
        _operations_stub=operations_pb2_grpc.PluginOperationsStub(channel),
        _declared=tuple(settings),
    )
    if heartbeat:
        plugin._heartbeat = asyncio.create_task(plugin._beat())
    return plugin
