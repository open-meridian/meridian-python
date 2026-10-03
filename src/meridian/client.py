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

Since contract v2 (decisions/013) a plugin reaches the bus through its typed
operations and nothing else. What it learns from the deployment -- its
settings, its account scope, who may use it -- it learns here, and who is
asking for its page it reads from the one header its sidecar forwards.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import os
import warnings
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar, cast

import grpc

from meridian.plugin.v1 import operations_pb2_grpc
from meridian.v1 import sidecar_pb2, sidecar_pb2_grpc

from .errors import (
    CallFailed,
    CommandRefused,
    NoSidecar,
    NotGranted,
    NotLinked,
    NotRegistered,
    Refused,
)
from .figures import Figure, listed, wire
from .operations import Operations, _enum
from .statements import checked

if TYPE_CHECKING:
    from .pages import Pages

#: The contract version this SDK was built for, sent at registration (W4.1). A
#: sidecar older than this refuses the plugin at the door, naming both versions,
#: rather than admitting it to run without what the SDK reads -- its links on
#: the account-scope stream, the refusal code beside a refusal, the asset class
#: as an enum on a miss it reports, its pages each declared with the levels it
#: serves, the level a session was opened at, the figures on its heartbeat,
#: the stream of what its roles hear and the reads within its scope, and a
#: statement naming its external account with its figures per segment, and the
#: book of record's operations with their refusal codes, the fields an
#: incomplete entry left out, and the delegation a person acted through -- and
#: a newer sidecar still admits it. Raised with every contract revision that
#: adds something a plugin can depend on.
SCHEMA_VERSION = "v10"

#: Where a sidecar listens. Loopback, always: a sidecar reachable from another
#: host is a way around the boundary it exists to enforce.
DEFAULT_ADDRESS = "127.0.0.1:9191"

#: What a plugin written against an earlier SDK meets where it reached for a
#: person's access tag by tag: a plugin declares no tags, and a person's access
#: to it is read or write, the same for every plugin (decisions/026).
_RETIRED_BY_026 = (
    "access tag by tag was retired with tags (decisions/026): a person's access "
    "to a plugin is read or write, the same for every plugin. Read Caller.read "
    "and Caller.write, the accounts this person may read and write through the "
    "plugin, or ask Caller.may_read and Caller.may_write"
)

#: How often liveness is reported. The sidecar's own view of a plugin that has
#: stopped sending these is the more informative signal, so this is deliberately
#: frequent enough that silence means something within seconds.
HEARTBEAT_SECONDS = 5.0

#: How long `connect` waits for a sidecar that is not answering yet. A plugin
#: and its sidecar start together in one pod, in no promised order, so the
#: plugin's first attempt can meet nothing listening; failing there would have
#: the orchestrator restart it with a growing backoff, for no fault of either.
SIDECAR_WAIT_SECONDS = 60.0

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

#: The statuses a refusal with a code arrives beside: a component's refusal
#: of its own, or one it could not check, to be tried again (contract v10).
_CODED = (grpc.StatusCode.ABORTED, grpc.StatusCode.UNAVAILABLE)

#: Where the sidecar sends a refusal's code, beside its status: a `Refusal`,
#: encoded (spec/typed-sidecar-operations, section 7).
REFUSAL_METADATA = "meridian-refusal-bin"

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
    A plugin has no tags: a person's access to it is read or write, the same
    for every plugin (decisions/026). A plugin that cares can compare these
    against what it expected and stop.
    """

    instance_id: str
    roles: tuple[str, ...] = ()
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


#: A person's level on a plugin, the same three for every plugin (W6.7): the
#: level a session was opened at -- Manage `admin`, Open `write`, View `read`
#: -- and the levels a page serves (W4.8).
AccessLevel = sidecar_pb2.AccessLevel

#: The home's button for each level (W6.9).
BUTTONS: dict[int, str] = {
    sidecar_pb2.ACCESS_LEVEL_ADMIN: "Manage",
    sidecar_pb2.ACCESS_LEVEL_WRITE: "Open",
    sidecar_pb2.ACCESS_LEVEL_READ: "View",
}


def _levels(given: Sequence[str | int] | str | int, where: str) -> tuple[int, ...]:
    """Levels as the wire carries them, each an `AccessLevel`, its name
    (ACCESS_LEVEL_ADMIN) or its ruled spelling (admin, write, read); one given
    alone is taken as one. Anything else is refused, naming where."""
    if isinstance(given, (str, int)):
        given = (given,)
    levels: list[int] = []
    for each in given:
        level = _enum(AccessLevel, each, where)
        if level is None or level == sidecar_pb2.ACCESS_LEVEL_UNSPECIFIED:
            raise ValueError(f"{where} names {each!r}, which is no level: admin, write or read")
        if level not in levels:
            levels.append(level)
    return tuple(levels)


@dataclass(frozen=True)
class Page:
    """One of the plugin's pages, at a path on its own host, and the levels it
    serves (W4.8): its tab shows under the home's button for each -- Manage
    `admin`, Open `write`, View `read` -- and one path may serve several,
    adapting by the session's level.

    `levels` takes `AccessLevel` values, their names or the ruled spelling:
    `Page("/statements", "Statements", levels=["write", "read"])`. A page in
    `Interface.pages` names at least one. `Pages` declares a page where its
    view is and refuses a session at a level it does not serve; a plugin on
    another framework asks `page.serves(caller)` itself.
    """

    path: str
    title: str
    levels: Sequence[str | int] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "levels", _levels(self.levels, f"page {self.title!r}"))

    def serves(self, caller: Caller) -> bool:
        """Whether this page is served in the caller's session: its level is
        one the page declares. A session at no level is served nothing."""
        return caller.level in self.levels

    def _declared(self) -> sidecar_pb2.PageDeclaration:
        if not self.path.startswith("/"):
            raise ValueError(f"page {self.title!r} has path {self.path!r}; begin it with /")
        if not self.levels:
            raise ValueError(
                f"page {self.title!r} names no level: give levels=, one or several of "
                "admin, write and read"
            )
        return sidecar_pb2.PageDeclaration(
            path=self.path,
            title=self.title,
            levels=cast(Any, list(self.levels)),
        )


@dataclass(frozen=True)
class Interface:
    """A page the plugin serves to people, on loopback (W6.9).

    Only the plugin's sidecar reaches it, forwarding requests the dashboard
    vouched for; who is asking is in the `Meridian-Caller` header, which
    `Caller.from_header` reads.

    `pages` are the plugin's pages, one list in the order shown (W4.8): a
    `Pages` registry, which declares each page where its view is and refuses
    a session at a level the page does not serve, or `Page`s, each with its
    levels. The plugin's area on the dashboard shows under each button the
    pages whose levels include its level, framing each at its path.

    `admin_pages`, the list contract v5 retired, is still taken for this
    release, as pages at `admin` after `pages`, with a DeprecationWarning;
    `meridian plugin migrate` rewrites it into `pages`.
    """

    port: int
    title: str
    admin_pages: Sequence[Page] = ()
    pages: Pages | Sequence[Page] = field(default=(), kw_only=True)

    def __post_init__(self) -> None:
        if self.admin_pages:
            warnings.warn(
                "Interface(admin_pages=...) is retired by contract v5: declare "
                'pages=, a page at admin with levels=["admin"]. `meridian plugin '
                "migrate` rewrites it",
                DeprecationWarning,
                stacklevel=3,
            )

    def _declared(self) -> sidecar_pb2.InterfaceDeclaration:
        from .pages import Pages

        pages = self.pages.declared if isinstance(self.pages, Pages) else tuple(self.pages)
        retired = tuple(
            Page(page.path, page.title, levels=(sidecar_pb2.ACCESS_LEVEL_ADMIN,))
            for page in self.admin_pages
        )
        return sidecar_pb2.InterfaceDeclaration(
            loopback_port=self.port,
            title=self.title,
            pages=[page._declared() for page in (*pages, *retired)],
        )


@dataclass(frozen=True)
class Choice:
    """One option of a setting that is a choice, shown as a radio button."""

    value: str
    label: str = ""
    description: str = ""


@dataclass(frozen=True)
class AppliesWhen:
    """A setting applies only while another, declared before it, holds one of
    these values: the form shows it, and asks for it when required, only then."""

    setting: str
    one_of: tuple[str, ...]


@dataclass(frozen=True)
class Setting:
    """One setting the plugin needs, declared at registration (W4.7).

    `kind` is str, int or bool; a str with `choices` is a choice, one of them.
    A secret is set through the dashboard and never read back, displayed,
    logged, reported or bundled; the plugin receives it in `Settings` and
    nowhere else.

    What the dashboard's form shows (W6.11): `label` as the field's name,
    `default` greyed in the empty field, `unit` beside a number. While a
    setting with a `default` is unset, `Settings.values` holds the default, so
    the plugin uses what the form showed. A `developer` setting is shown only
    on a development deployment.
    """

    name: str
    kind: type = str
    required: bool = False
    secret: bool = False
    description: str = ""
    label: str = ""
    default: str | int | bool | None = None
    unit: str = ""
    choices: tuple[Choice, ...] = ()
    applies_when: AppliesWhen | None = None
    developer: bool = False

    def _declared(self) -> sidecar_pb2.SettingDeclaration:
        if self.kind not in _SETTING_TYPES:
            raise TypeError(f"setting {self.name} is a {self.kind.__name__}; str, int or bool")
        if self.choices and self.kind is not str:
            raise TypeError(f"setting {self.name} has choices, so its kind is str")
        if self.secret and self.default is not None:
            raise ValueError(f"setting {self.name} is secret, so it declares no default")
        if self.default is not None and not isinstance(self.default, self.kind):
            raise TypeError(f"setting {self.name}'s default is not a {self.kind.__name__}")
        values = {choice.value for choice in self.choices}
        if self.choices and self.default is not None and self.default not in values:
            raise ValueError(f"setting {self.name}'s default is not one of its choices")
        return sidecar_pb2.SettingDeclaration(
            name=self.name,
            type=(
                sidecar_pb2.SETTING_TYPE_CHOICE if self.choices else _SETTING_TYPES[self.kind]
            ),
            required=self.required,
            secret=self.secret,
            description=self.description,
            label=self.label,
            default_value="" if self.default is None else _written(self.default),
            unit=self.unit,
            choices=[
                sidecar_pb2.SettingChoice(
                    value=choice.value, label=choice.label, description=choice.description
                )
                for choice in self.choices
            ],
            applies_when=(
                None
                if self.applies_when is None
                else sidecar_pb2.SettingCondition(
                    setting=self.applies_when.setting, one_of=list(self.applies_when.one_of)
                )
            ),
            developer=self.developer,
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
        if self.choices and text not in {choice.value for choice in self.choices}:
            raise ValueError(f"setting {self.name} is not one of its choices: {text!r}")
        return text


def _written(value: str | int | bool) -> str:
    """A value as the form would take it, and as `_parsed` reads it back."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


@dataclass(frozen=True)
class Settings:
    """The plugin's settings as the deployment holds them, typed by what it
    declared, and the required ones it holds nothing for yet. While any is
    missing the sidecar reports the plugin unhealthy, naming it."""

    values: dict[str, str | int | bool]
    missing_required: tuple[str, ...] = ()


@dataclass(frozen=True)
class LinkedExternalAccount:
    """One of this plugin's external accounts, linked to one of the
    deployment's accounts by an admin of the plugin (W6.4)."""

    external_account_id: str
    account_id: str
    # The account's name as the deployment holds it now (W6.3).
    account_name: str = ""


@dataclass(frozen=True)
class AccountScope:
    """Every account anybody may read, or write, through this plugin, and the
    plugin's own links beside them (W4.11).

    A plugin reads its whole read scope as itself and serves each person only
    what their access allows; a write outside `write` is refused by the
    sidecar whoever it is for.

    `links` are this plugin's, each external account it links with the account
    that is and that account's name; a link puts its account in both scopes
    while it stands, a closed one in `read` alone. An external account the
    plugin reported and no link names is unlinked, and a row for it raises
    `NotLinked`. Delivered on every start and every change, so a plugin holds
    them from here and never keeps them itself.
    """

    read: frozenset[str] = frozenset()
    write: frozenset[str] = frozenset()
    links: tuple[LinkedExternalAccount, ...] = ()

    def link_of(self, external_account_id: str) -> LinkedExternalAccount | None:
        """The link naming this external account, or None while it is unlinked."""
        return next(
            (link for link in self.links if link.external_account_id == external_account_id),
            None,
        )


@dataclass(frozen=True)
class Caller:
    """Who a request for the plugin's page came from, as the dashboard vouched
    and the sidecar verified before forwarding it (W6.9).

    Read, not verified: only the sidecar can reach the page, and it removed
    every other claim the request arrived with. Hand `header` back as
    `acting_for` on a command to send it for this person (W4.9).

    `level` is the level the session was opened at, one the person holds on
    this plugin: `AccessLevel.ACCESS_LEVEL_ADMIN` by the home's Manage,
    `ACCESS_LEVEL_WRITE` by Open, `ACCESS_LEVEL_READ` by View (W6.9); unset,
    the session holds nothing. The accounts are cut to it: `read`, the
    accounts the plugin may show them, and `write`, the accounts it may act on
    for them, which are also in `read` -- both under Open, `read` alone under
    View, and neither under Manage, which sees no account's data. The levels
    are the same for every plugin, and a plugin names no parts of itself
    (decisions/026, 027).
    """

    subject: str
    display_name: str
    header: str
    read: frozenset[str] = frozenset()
    write: frozenset[str] = frozenset()
    # Whether the person is a deployment admin. It opens no page and reaches
    # no account: it says only that, linking an external account under
    # Manage, they may name a new account rather than an existing one (W6.4).
    deployment_admin: bool = False
    level: int = sidecar_pb2.ACCESS_LEVEL_UNSPECIFIED
    # The delegation the person acted through and its client's registered
    # name, when they came through a client -- the CLI, their own agent, an
    # MCP client -- rather than a browser; both empty for a browser (W6.18,
    # decisions/029, contract v9). The person stays the actor: these say
    # through what, for the plugin to show and record as it chooses. The
    # sidecar stamps the delegation on every command sent for them.
    delegation_id: str = ""
    client_name: str = ""

    @classmethod
    def from_header(cls, header: str) -> Caller:
        padded = header + "=" * (-len(header) % 4)
        assertion = sidecar_pb2.CallerAssertion.FromString(base64.urlsafe_b64decode(padded))
        claims = sidecar_pb2.CallerClaims.FromString(assertion.claims)
        return cls(
            subject=claims.subject,
            display_name=claims.display_name,
            header=header,
            read=frozenset(claims.read_account_ids),
            write=frozenset(claims.write_account_ids),
            deployment_admin=claims.deployment_admin,
            level=claims.level,
            delegation_id=claims.delegation_id,
            client_name=claims.client_name,
        )

    @property
    def through_a_client(self) -> bool:
        """Whether the person came through a client on a delegation, rather
        than a browser (W6.18)."""
        return bool(self.delegation_id)

    @property
    def admin(self) -> bool:
        """Whether the session was opened by Manage: the plugin's pages at
        `admin`, configuration only, and no account's data (W6.9)."""
        return self.level == sidecar_pb2.ACCESS_LEVEL_ADMIN

    def may_read(self, account_id: str) -> bool:
        return account_id in self.read

    def may_write(self, account_id: str) -> bool:
        return account_id in self.write

    @property
    def access(self) -> NoReturn:
        raise AttributeError(_RETIRED_BY_026)


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
    _figures: tuple[Figure, ...] = field(default=(), repr=False)
    _figures_sent: tuple[sidecar_pb2.PluginFigure, ...] = field(default=(), repr=False)
    _healthy: bool = field(default=True, repr=False)
    _detail: str = field(default="", repr=False)

    @property
    def figures(self) -> Sequence[Figure]:
        """The figures this plugin reports on its heartbeat (W4.5), as last set.

        Set a list of `meridian.Figure` to report it on every heartbeat from
        the next on, each replacing the last; an empty one clears them. Core
        draws them on the plugin's Summary under Manage. Refused here, as the
        sidecar would refuse it, when it breaks a bound: more than 8, a label
        empty, over 40 characters or given twice, a text over 40, a why over
        200, a state other than ok, warn or error, no value, or a decimal out
        of range. Nothing is set then, and the last list stands.
        """
        return self._figures

    @figures.setter
    def figures(self, figures: Sequence[Figure]) -> None:
        given = listed(figures)
        self._figures_sent = wire(given)
        self._figures = given

    async def settings(self) -> AsyncIterator[Settings]:
        """The settings it declared, now and again on every change (W4.7).

        Each is typed by its declaration; a value that does not parse is
        raised rather than guessed at.
        """
        self._check_open()
        by_name = {setting.name: setting for setting in self._declared}
        defaults = {
            setting.name: setting.default
            for setting in self._declared
            if setting.default is not None
        }
        async for delivered in self._stub.WatchSettings(sidecar_pb2.WatchSettingsRequest()):
            yield Settings(
                values=defaults
                | {
                    held.name: by_name[held.name]._parsed(held.value)
                    for held in delivered.values
                    if held.name in by_name
                },
                missing_required=tuple(delivered.missing_required),
            )

    async def account_scope(self) -> AsyncIterator[AccountScope]:
        """Its account scope and its links, now and again on every change
        (W4.11): the first at once, so a plugin just started has its links."""
        self._check_open()
        async for delivered in self._stub.WatchAccountScope(
            sidecar_pb2.WatchAccountScopeRequest()
        ):
            yield AccountScope(
                read=frozenset(delivered.read_account_ids),
                write=frozenset(delivered.write_account_ids),
                links=tuple(
                    LinkedExternalAccount(
                        external_account_id=link.external_account_id,
                        account_id=link.account_id,
                        account_name=link.account_name,
                    )
                    for link in delivered.links
                ),
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

    async def report(
        self, *, healthy: bool, detail: str = "", figures: Sequence[Figure] | None = None
    ) -> None:
        """Report its health now, out of band of the automatic heartbeat.

        For a plugin that knows it is unwell and should say so, rather than
        for ordinary liveness, which is already handled. The health reported
        stands, with its `detail`, on every heartbeat after, as the figures
        do, until the plugin reports again: a plugin reported not healthy
        stays so until `report(healthy=True)`. It carries the plugin's
        figures as they stand; `figures` sets them first, as setting
        `plugin.figures` does, and sends them now. Figures refused leave the
        health as it was, and nothing is sent.
        """
        self._check_open()
        if figures is not None:
            self.figures = figures
        self._healthy, self._detail = healthy, detail
        await self._stub.Heartbeat(self._heartbeat_request())

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

    async def _receive(
        self, handlers: dict[str, Callable[[Any], Awaitable[None]] | None], *, seed: bool
    ) -> None:
        """What `receive` hears, seeded, followed and caught up (W4.3)."""
        self._check_open()
        from .receive import follow

        await follow(self, handlers, seed=seed)

    async def _operate(
        self, method: Callable[[Any], Awaitable[_Answer]], params: Any
    ) -> _Answer:
        """One typed operation, its refusal turned into this package's terms."""
        self._check_open()
        operation = type(params).__name__.removesuffix("Params")
        checked(params)
        try:
            return await method(params)
        except grpc.aio.AioRpcError as failed:
            detail = failed.details() or ""
            if failed.code() is grpc.StatusCode.PERMISSION_DENIED:
                raise NotGranted(operation, detail) from failed
            refusal = _refusal(failed)
            reason = refusal.reason
            if reason == sidecar_pb2.REFUSAL_REASON_EXTERNAL_ACCOUNT_NOT_LINKED:
                raise NotLinked(operation, detail) from failed
            coded = reason != sidecar_pb2.REFUSAL_REASON_UNSPECIFIED
            # ABORTED, a component's refusal of its own; or UNAVAILABLE with a
            # code, a command the component could not check, nothing recorded,
            # to be tried again (contract v10).
            if coded and failed.code() in _CODED:
                raise CommandRefused(
                    operation, detail, reason, fields=tuple(refusal.fields)
                ) from failed
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
                await self._stub.Heartbeat(self._heartbeat_request())

    def _heartbeat_request(self) -> sidecar_pb2.HeartbeatRequest:
        """The health and figures as they stand: healthy, with no detail and
        no figures, until the plugin reports otherwise."""
        return sidecar_pb2.HeartbeatRequest(
            healthy=self._healthy, detail=self._detail, figures=self._figures_sent
        )


def _refusal(failed: grpc.aio.AioRpcError) -> sidecar_pb2.Refusal:
    """What a refusal carries beside its status: its code, unspecified when
    it carries none, and the fields an incomplete command left out (contract
    v9). By these, and never by the words, is a refusal told apart."""
    for key, value in (*(failed.trailing_metadata() or ()), *(failed.initial_metadata() or ())):
        if key == REFUSAL_METADATA and isinstance(value, bytes):
            return sidecar_pb2.Refusal.FromString(value)
    return sidecar_pb2.Refusal(reason=sidecar_pb2.REFUSAL_REASON_UNSPECIFIED)


async def connect(
    address: str | None = None,
    *,
    heartbeat: bool = True,
    wait: float = SIDECAR_WAIT_SECONDS,
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

    A sidecar not answering yet is waited for, up to `wait` seconds, since it
    starts beside the plugin; `NoSidecar` when none answers by then.

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
                interface=interface._declared() if interface is not None else None,
                settings=[setting._declared() for setting in settings],
                reads_external_accounts=reads_external_accounts,
            ),
            # Held until the channel is ready rather than failed at once,
            # within the deadline; an answer, refusal included, ends the wait.
            wait_for_ready=True,
            timeout=wait,
        )
    except grpc.aio.AioRpcError as failed:
        await channel.close(None)
        if failed.code() in (grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.UNAVAILABLE):
            raise NoSidecar(target, wait) from failed
        raise
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
    # Under `meridian-dev run`, on a development deployment: this revision
    # is running, which is what `ready` means (spec/live-plugin-development).
    from .dev import report_ready

    report_ready()
    return plugin


def __getattr__(name: str) -> Any:
    """A name this module no longer has, said plainly rather than as a typo."""
    if name == "TagAccess":
        raise AttributeError(_RETIRED_BY_026)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
