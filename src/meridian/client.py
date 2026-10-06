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
import json
import os
import re
import warnings
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import TracebackType
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar, cast

import grpc

from meridian.plugin.v1 import operations_pb2_grpc
from meridian.v1 import sidecar_pb2, sidecar_pb2_grpc

from .bounds import (
    FILE_TICKET_REQUEST_REFERENCES_COUNT,
    FILE_TICKET_REQUEST_SEEN_LENGTH,
    FILE_TICKET_REQUEST_TITLE_LENGTH,
    PAGE_DECLARATION_ROLES_COUNT,
    TICKET_REFERENCE_VALUE_LENGTH,
    Length,
)
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
    from pathlib import Path

    from .declaration import Declaration, Storage
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
#: incomplete entry left out, and the delegation a person acted through, and
#: from v13 a ticket filed for a person and what became of those it filed, and
#: from v14 the custodian's activity recorded and read, and each sync status
#: the street keeps, and from v15 the roles each page, tool and setting
#: serves, the person's level and accounts on each role in the claims, and an
#: activity re-resolved, and from v16 the kinds of raw record in the
#: declaration, what each holds in storage on the heartbeat, and a move of
#: raw records reported and refused inside a hold -- and a newer sidecar
#: still admits it. Raised with every contract revision that adds something
#: a plugin can depend on.
SCHEMA_VERSION = "v16"

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
    # A ticket past its instance's 20 filings an hour (W4.12, contract v13).
    grpc.StatusCode.RESOURCE_EXHAUSTED: "refused",
}

#: The statuses a refusal with a code arrives beside: a component's refusal
#: of its own, or one it could not check, to be tried again (contract v10).
_CODED = (
    grpc.StatusCode.ABORTED,
    grpc.StatusCode.UNAVAILABLE,
    # A deletion inside the hold over the instance, REFUSAL_REASON_WITHIN_HOLD
    # (W4.13, contract v16): refused before it leaves the sidecar.
    grpc.StatusCode.FAILED_PRECONDITION,
)

#: Where the sidecar sends a refusal's code, beside its status: a `Refusal`,
#: encoded (spec/typed-sidecar-operations, section 7).
REFUSAL_METADATA = "meridian-refusal-bin"

#: Where a call made for a person carries the assertion the plugin was handed
#: for them, as the `Meridian-Caller` header it read (W4.12, contract v13).
CALLER_METADATA = "meridian-caller"

_SETTING_TYPES = {
    str: sidecar_pb2.SETTING_TYPE_STRING,
    int: sidecar_pb2.SETTING_TYPE_INTEGER,
    bool: sidecar_pb2.SETTING_TYPE_BOOLEAN,
    list: sidecar_pb2.SETTING_TYPE_TABLE,
}

#: A table setting's column kinds, as `Column` takes them (contract v14).
_COLUMN_KINDS = {
    "text": sidecar_pb2.SETTING_COLUMN_TYPE_TEXT,
    "integer": sidecar_pb2.SETTING_COLUMN_TYPE_INTEGER,
    "decimal": sidecar_pb2.SETTING_COLUMN_TYPE_DECIMAL,
    "date": sidecar_pb2.SETTING_COLUMN_TYPE_DATE,
    "choice": sidecar_pb2.SETTING_COLUMN_TYPE_CHOICE,
    "external_account": sidecar_pb2.SETTING_COLUMN_TYPE_EXTERNAL_ACCOUNT,
    "instrument": sidecar_pb2.SETTING_COLUMN_TYPE_INSTRUMENT,
}
#: What the conductor stamps on each row of a table setting.
_STAMPS = ("changed_by", "changed_at")
#: The most rows any table setting holds.
_MOST_ROWS = 500

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


#: A role's spelling in the deployment's fixed list (matrix/roles.tsv):
#: lower-case letters.
_ROLE = re.compile(r"[a-z]+")


def _roles(given: Sequence[str] | str, where: str) -> tuple[str, ...]:
    """Roles as a declaration names them (contract v15): one given alone is
    taken as one, each named once, in the order given. A role is one the
    plugin was launched with, which only its sidecar knows, so a role it
    does not hold is refused at registration, naming it; here only a name no
    role could have, and more than a declaration carries, is refused."""
    if isinstance(given, str):
        given = (given,)
    roles: list[str] = []
    for each in given:
        if not isinstance(each, str) or not _ROLE.fullmatch(each):
            raise ValueError(
                f"{where} names {each!r}, which is no role: a role is one the plugin was "
                "launched with, such as custody or operations"
            )
        if each not in roles:
            roles.append(each)
    if not PAGE_DECLARATION_ROLES_COUNT.admits(len(roles)):
        raise ValueError(
            f"{where} names {len(roles)} roles; at most {PAGE_DECLARATION_ROLES_COUNT.most}"
        )
    return tuple(roles)


def _serves(levels: Sequence[int], roles: Sequence[str], caller: Caller) -> bool:
    """Whether a declaration at `levels` serving `roles` is served in the
    caller's session (W6.9): naming no role, its level is one of them; naming
    roles, the caller's level on one of them within the session's button is
    (contract v15). A session at no level is served nothing."""
    if not roles:
        return caller.level in levels
    return any(caller.level_for(role) in levels for role in roles)


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

    `roles` are the roles it serves, from those the plugin was launched with
    (contract v15): its tab shows under a button when the person's level on
    one of them within that button is one of `levels`. A plugin holding one
    role, or none, names none, and its pages serve that role as before; a
    plugin holding several names them on every page, and the sidecar refuses
    its registration otherwise, or for a role it was not launched with.
    """

    path: str
    title: str
    levels: Sequence[str | int] = ()
    roles: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "levels", _levels(self.levels, f"page {self.title!r}"))
        object.__setattr__(self, "roles", _roles(self.roles, f"page {self.title!r}"))

    def serves(self, caller: Caller) -> bool:
        """Whether this page is served in the caller's session: its level is
        one the page declares, or, for a page naming its roles, the caller's
        level on one of them is (contract v15). A session at no level is
        served nothing."""
        return _serves(cast(tuple[int, ...], self.levels), self.roles, caller)

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
            roles=list(self.roles),
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

    def _tools(self) -> list[sidecar_pb2.ToolDeclaration]:
        """The tools derived from the pages' typed routes (contract v12)."""
        from .pages import Pages

        if not isinstance(self.pages, Pages):
            return []
        return [tool.declared() for tool in self.pages.tools]

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
class Column:
    """One column of a table setting (contract v14): its `name`, the key each
    row's cell is held under, and its `kind` -- "text", "integer",
    "decimal", "date", "choice" (one of `choices`), "external_account" (one
    this plugin reported) or "instrument" (a deployment instrument record's
    ID, picked by search, never a symbol). A `required` column is filled on
    every row."""

    name: str
    kind: str = "text"
    label: str = ""
    required: bool = False
    description: str = ""
    choices: tuple[Choice, ...] = ()

    def _declared(self, setting: str) -> sidecar_pb2.SettingColumn:
        if self.kind not in _COLUMN_KINDS:
            raise ValueError(
                f"setting {setting}'s column {self.name} is a {self.kind!r}; one of "
                f"{', '.join(_COLUMN_KINDS)}"
            )
        if self.name in _STAMPS:
            raise ValueError(
                f"setting {setting}'s column is named {self.name}, which the conductor stamps"
            )
        if self.kind == "choice" and not self.choices:
            raise ValueError(
                f"setting {setting}'s column {self.name} is a choice with no options"
            )
        return sidecar_pb2.SettingColumn(
            name=self.name,
            label=self.label,
            type=_COLUMN_KINDS[self.kind],
            required=self.required,
            description=self.description,
            choices=[
                sidecar_pb2.SettingChoice(
                    value=c.value, label=c.label, description=c.description
                )
                for c in self.choices
            ],
        )


@dataclass(frozen=True)
class Setting:
    """One setting the plugin needs, declared at registration (W4.7).

    `kind` is str, int or bool; a str with `choices` is a choice, one of them.
    `list` with `columns` is a table (contract v14): rows an admin of the
    plugin enters in the dashboard's Settings form, as an editable table, and
    which the plugin only reads -- in `Settings.values`, a list of rows, each
    a dict of its cells by column name, every cell text, with `changed_by`
    and `changed_at`, which the conductor stamps on a row added or changed.
    `most_rows` bounds it (0: 500).
    A secret is set through the dashboard and never read back, displayed,
    logged, reported or bundled; the plugin receives it in `Settings` and
    nowhere else.

    What the dashboard's form shows (W6.11): `label` as the field's name,
    `default` greyed in the empty field, `unit` beside a number. While a
    setting with a `default` is unset, `Settings.values` holds the default, so
    the plugin uses what the form showed. A `developer` setting is shown only
    on a development deployment.

    `roles` are the roles it serves, from those the plugin was launched with
    (contract v15): it is shown to an admin of any of them and set only by a
    person holding admin on every one. A plugin holding one role, or none,
    names none; one holding several names them on every setting. Not who may
    read the value: the plugin reads every setting it declared.
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
    columns: tuple[Column, ...] = ()
    most_rows: int = 0
    roles: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "roles", _roles(self.roles, f"setting {self.name}"))

    def _declared(self) -> sidecar_pb2.SettingDeclaration:
        if self.kind not in _SETTING_TYPES:
            raise TypeError(
                f"setting {self.name} is a {self.kind.__name__}; str, int, bool or list"
            )
        if (self.kind is list) != bool(self.columns):
            raise TypeError(
                f"setting {self.name}: a table's kind is list, and only a table has columns"
            )
        if self.kind is list:
            if self.secret or self.default is not None or self.choices:
                raise ValueError(f"setting {self.name} is a table: never secret, no default")
            if len({c.name for c in self.columns}) != len(self.columns):
                raise ValueError(f"setting {self.name} names a column twice")
            if not 0 <= self.most_rows <= _MOST_ROWS:
                raise ValueError(f"setting {self.name}'s most_rows is 0 to {_MOST_ROWS}")
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
            columns=[column._declared(self.name) for column in self.columns],
            most_rows=self.most_rows,
            roles=list(self.roles),
        )

    def _parsed(self, text: str) -> str | int | bool | list[dict[str, str]]:
        if self.kind is list:
            try:
                rows = json.loads(text)
            except ValueError:
                raise ValueError(f"setting {self.name} is not a table's JSON") from None
            if not isinstance(rows, list) or not all(
                isinstance(row, dict) and all(isinstance(v, str) for v in row.values())
                for row in rows
            ):
                raise ValueError(f"setting {self.name} is not a list of rows of text")
            return [dict(row) for row in rows]
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

    values: dict[str, str | int | bool | list[dict[str, str]]]
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

    From contract v15 a person holds a level on each role of a plugin
    (decisions/033), and the session carries one entry per role they hold
    something on within its button: `roles`, each role's level, which
    `level_for(role)` reads, and the accounts it reaches, `read_for(role)`
    and `write_for(role)` -- under Open a role held at write is at write and
    one held at read at read, under View each at read, under Manage each role
    administered at admin with no account. `level`, `read` and `write` stay
    the session's: its button, and the union over its roles. Claims carrying
    no entry -- a plugin holding no role, or a dashboard before v15 -- read
    every role as the session's level and accounts, as the sidecar reads them
    on a plugin holding one.
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
    # The tool a call through the deployment's MCP surface names (contract
    # v12): set only by the dashboard's `/mcp`, and the sidecar admits it at
    # that tool's route alone. Empty for every browser's request.
    tool_name: str = ""
    # Each role's level within the session's button (contract v15), and the
    # accounts it reaches, read and write; empty where the claims carry no
    # entry. `level_for`, `read_for` and `write_for` read them.
    roles: Mapping[str, int] = field(default_factory=dict, hash=False)
    _reach: Mapping[str, tuple[frozenset[str], frozenset[str]]] = field(
        default_factory=dict, hash=False, repr=False
    )

    @classmethod
    def from_header(cls, header: str) -> Caller:
        padded = header + "=" * (-len(header) % 4)
        assertion = sidecar_pb2.CallerAssertion.FromString(base64.urlsafe_b64decode(padded))
        claims = sidecar_pb2.CallerClaims.FromString(assertion.claims)
        reads = list(claims.read_account_ids)

        def accounts(positions: Sequence[int], role: str) -> frozenset[str]:
            # Positions in the claims' read accounts (contract v15, the plan's
            # Q2); one past them is a header that does not read.
            if any(at >= len(reads) for at in positions):
                raise ValueError(
                    f"the caller's entry for {role} names an account past the "
                    f"{len(reads)} the claims carry"
                )
            return frozenset(reads[at] for at in positions)

        roles: dict[str, int] = {}
        reach: dict[str, tuple[frozenset[str], frozenset[str]]] = {}
        for entry in claims.roles:
            roles[entry.role] = entry.level
            reach[entry.role] = (
                accounts(entry.read_positions, entry.role),
                accounts(entry.write_positions, entry.role),
            )
        return cls(
            subject=claims.subject,
            display_name=claims.display_name,
            header=header,
            read=frozenset(reads),
            write=frozenset(claims.write_account_ids),
            deployment_admin=claims.deployment_admin,
            level=claims.level,
            delegation_id=claims.delegation_id,
            client_name=claims.client_name,
            tool_name=claims.tool_name,
            roles=roles,
            _reach=reach,
        )

    def level_for(self, role: str) -> int:
        """The caller's level on `role` within the session's button
        (contract v15): an `AccessLevel`, unspecified for a role they hold
        nothing on here. Claims carrying no per-role entry read every role
        at the session's level."""
        if not self.roles:
            return self.level
        return self.roles.get(role, sidecar_pb2.ACCESS_LEVEL_UNSPECIFIED)

    def read_for(self, role: str) -> frozenset[str]:
        """The accounts the plugin may show the caller for `role`: within
        `read`, empty under Manage and for a role they hold nothing on.
        Claims carrying no per-role entry read every role as `read`."""
        if not self.roles:
            return self.read
        return self._reach.get(role, (frozenset(), frozenset()))[0]

    def write_for(self, role: str) -> frozenset[str]:
        """The accounts the plugin may act on for the caller in `role`: those
        the sidecar admits a command of that role for, on their behalf.
        Within `read_for(role)`; empty under View and Manage, and for a role
        held at read. Claims carrying no per-role entry read every role as
        `write`."""
        if not self.roles:
            return self.write
        return self._reach.get(role, (frozenset(), frozenset()))[1]

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


#: What kind of problem a ticket is (W4.12, contract v13): `defect`,
#: `discrepancy`, `request` or `question`. A ticket is routed by what it
#: concerns, never by its kind.
TicketKind = sidecar_pb2.TicketKind

#: Where a ticket a plugin filed stands: `open`, `resolved` or `closed`.
TicketState = sidecar_pb2.TicketState

#: What resolved a ticket -- a `note`, an `answer`, a `version` -- or why it
#: was closed with nothing fixed: `withdrawn`, `duplicate`, `not_a_problem`.
TicketResolution = sidecar_pb2.TicketResolution


class TicketSubject(StrEnum):
    """The one thing a ticket concerns (W4.12, contract v13): this plugin, a
    part of core, or the platform; never another plugin, which the sidecar
    refuses naming it. A plugin names no instance and no version: the sidecar
    sets this plugin's instance, and the deployment its version at filing."""

    PLUGIN = "plugin"
    DASHBOARD = "dashboard"
    BOR = "bor"
    STREET = "street"
    INSTRUMENT = "instrument"
    CONDUCTOR = "conductor"
    CHART = "chart"
    CLI = "cli"
    SDK = "sdk"
    PLATFORM = "platform"


#: What a ticket's reference may name, and those that carry the account they
#: are about, which the dashboard reads no store to find (W4.12).
_REFERENCE_KINDS = (
    "account",
    "instrument",
    "break",
    "entry",
    "street_record",
    "tool_call",
    "plugin",
)
_PLACED_BY_ACCOUNT = ("break", "entry", "street_record")


@dataclass(frozen=True)
class TicketReference:
    """One record a ticket is about, by value (W4.12): `kind` is `account`,
    `instrument`, `break`, `entry`, `street_record`, `tool_call` or `plugin`
    (the plugin's own opaque reference); `value` the record's identifier, 1 to
    200 characters; `account_id` the account it is about, required on a break,
    an entry and a street record, and the value itself on an account. An
    account named must be one the person may read through this plugin, and a
    ticket naming accounts is seen only by those who may read every one."""

    kind: str
    value: str
    account_id: str = ""

    def _wire(self, at: str) -> sidecar_pb2.TicketReference:
        if self.kind not in _REFERENCE_KINDS:
            raise ValueError(
                f"{at}.kind is {self.kind!r}; it is one of {', '.join(_REFERENCE_KINDS)}"
            )
        _bounded(f"{at}.value", self.value, TICKET_REFERENCE_VALUE_LENGTH)
        if self.kind in _PLACED_BY_ACCOUNT and not self.account_id:
            raise ValueError(
                f"{at}.account_id is empty; a {self.kind.replace('_', ' ')} names the "
                "account it is about"
            )
        return sidecar_pb2.TicketReference(
            kind=self.kind, value=self.value, account_id=self.account_id
        )


def _bounded(at: str, text: str, bound: Length) -> None:
    """A text held to its bound, counted in characters, refused naming it."""
    if not isinstance(text, str):
        raise TypeError(f"{at} is a str, not {type(text).__name__}")
    if not bound.admits(len(text)):
        if len(text) < bound.least:
            raise ValueError(
                f"{at} is empty; it holds {bound.least} to {bound.most} characters"
            )
        raise ValueError(f"{at} is {len(text)} characters; it holds at most {bound.most}")


def _filing(
    *,
    title: str,
    seen: str,
    kind: str | int,
    concerns: TicketSubject | str,
    step: str,
    operation: str,
    reason: str,
    paths: Sequence[str],
    references: Sequence[TicketReference],
    idempotency_key: str,
) -> sidecar_pb2.FileTicketRequest:
    """A filing as the sidecar takes it, refused here, naming the field, where
    the sidecar would refuse it by its bounds: a convenience, since the
    sidecar refuses the same whatever this client believes."""
    _bounded("title", title, FILE_TICKET_REQUEST_TITLE_LENGTH)
    _bounded("seen", seen, FILE_TICKET_REQUEST_SEEN_LENGTH)
    wire_kind = _enum(TicketKind, kind, "kind")
    if wire_kind is None or wire_kind == sidecar_pb2.TICKET_KIND_UNSPECIFIED:
        raise ValueError(
            f"kind is {kind!r}; a ticket is a defect, a discrepancy, a request or a question"
        )
    try:
        subject = TicketSubject(concerns)
    except ValueError:
        raise ValueError(
            f"concerns is {concerns!r}; it is one of {', '.join(TicketSubject)}"
        ) from None
    if not idempotency_key:
        raise ValueError(
            "idempotency_key is empty; a plugin names each problem by its own key, so a "
            "restart files nothing twice"
        )
    if not FILE_TICKET_REQUEST_REFERENCES_COUNT.admits(len(references)):
        raise ValueError(
            f"references names {len(references)} records; a ticket names at most "
            f"{FILE_TICKET_REQUEST_REFERENCES_COUNT.most}"
        )
    return sidecar_pb2.FileTicketRequest(
        title=title,
        seen=seen,
        kind=wire_kind,
        concerns=sidecar_pb2.TicketSubject(kind=subject.value),
        step=step,
        operation=operation,
        reason=reason,
        paths=list(paths),
        references=[
            reference._wire(f"references[{n}]") for n, reference in enumerate(references)
        ],
        idempotency_key=idempotency_key,
    )


def _caller_metadata(for_caller: Caller | str) -> tuple[tuple[str, str], ...]:
    """The person a ticket is filed or read for, as the call's
    `meridian-caller` metadata: the header the plugin was handed (W6.9)."""
    header = for_caller.header if isinstance(for_caller, Caller) else for_caller
    if not isinstance(header, str) or not header:
        raise ValueError(
            "for_caller names nobody; a plugin files a ticket, and reads what it filed, "
            "only for a person it acts for: pass the Caller of the request it is serving"
        )
    return ((CALLER_METADATA, header),)


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
    _not_carried_seen: dict[tuple[str, str], int] = field(default_factory=dict, repr=False)
    # The storage it declared, with its kinds of raw record (contract v16);
    # the settings as last delivered, which a window's move names; what it
    # says each kind holds in storage; and its moves.
    _storage: Storage | None = field(default=None, repr=False)
    _settings_now: dict[str, Any] | None = field(default=None, repr=False)
    _stored: tuple[sidecar_pb2.StoredSpan, ...] = field(default=(), repr=False)
    _mover: Any = field(default=None, repr=False)

    def raw_record(self, key: str) -> Any:
        """A reference to a raw record in this plugin's own storage, by its
        own key (contract v11): what a row, a statement or a provenance names
        it by. Carried, never followed, past this plugin; a person follows it
        on this plugin's page."""
        from .edge import raw_record

        return raw_record(key, self.identity.instance_id)

    def note_not_carried(self, scheme: str, name: str) -> None:
        """Count one sighting of a vendor field or code this plugin's
        declaration lists as received and not carried (W4.5, contract v11):
        each heartbeat carries how often each was seen since it started, a
        name and a count, never a value."""
        key = (scheme, name)
        self._not_carried_seen[key] = self._not_carried_seen.get(key, 0) + 1

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
        defaults: dict[str, str | int | bool | list[dict[str, str]]] = {
            setting.name: setting.default
            for setting in self._declared
            if setting.default is not None
        }
        async for delivered in self._stub.WatchSettings(sidecar_pb2.WatchSettingsRequest()):
            now = Settings(
                values=defaults
                | {
                    held.name: by_name[held.name]._parsed(held.value)
                    for held in delivered.values
                    if held.name in by_name
                },
                missing_required=tuple(delivered.missing_required),
            )
            self._settings_now = dict(now.values)
            yield now

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

    async def file_ticket(
        self,
        *,
        title: str,
        kind: str | int,
        idempotency_key: str,
        for_caller: Caller | str,
        seen: str = "",
        concerns: TicketSubject | str = TicketSubject.PLUGIN,
        step: str = "",
        operation: str = "",
        reason: str = "",
        paths: Sequence[str] = (),
        references: Sequence[TicketReference] = (),
    ) -> sidecar_pb2.FileTicketReply:
        """File a ticket for the person whose request this plugin is serving
        (W4.12, contract v13): a problem they met that the plugin cannot
        handle, for someone who can act. Never as itself: `for_caller` is
        that person, their `Caller` or the header it was read from, at
        whatever level their session holds. What the plugin notices on its
        own is its health, figures on its Summary (`plugin.figures`), from
        which a person may choose to file.

        `title` says in a line what is wrong (1 to 120 characters) and
        `seen` what was seen, in the person's words (at most 8,000), both
        plain text; `kind` a `TicketKind`, its name or `defect`,
        `discrepancy`, `request` or `question`; `concerns` a `TicketSubject`,
        this plugin unless it is a part of core or the platform, never
        another plugin. `step`, `operation`, `reason` and `paths` name the
        workflow step, the operation, the refusal and the fields by their
        paths, where known; `references` the records it is about, at most 50
        `TicketReference`s.

        `idempotency_key` is the plugin's own key for the problem, so a
        restart files nothing twice: filed again while its ticket is open,
        the ticket is brought up to date and answered `unchanged`, its
        `seen_count` counting the filing; after it was resolved or closed, a
        new ticket. The reply's `ticket_id`, `outcome` (`made` or
        `unchanged`) and `seen_count` say which.

        Every text filed is data to whoever reads it, never instructions.
        Refused here, naming the field, past a bound; by the sidecar as
        itself (`NotGranted`), for a person it cannot vouch for, about
        another plugin, naming an account the person may not read, or past
        20 filings an hour from this instance, a repeat not counted.
        """
        self._check_open()
        filing = _filing(
            title=title,
            seen=seen,
            kind=kind,
            concerns=concerns,
            step=step,
            operation=operation,
            reason=reason,
            paths=paths,
            references=references,
            idempotency_key=idempotency_key,
        )
        metadata = _caller_metadata(for_caller)
        reply: sidecar_pb2.FileTicketReply = await self._for_person(
            "FileTicket", self._stub.FileTicket(filing, metadata=metadata)
        )
        return reply

    async def filed_tickets(
        self,
        *,
        for_caller: Caller | str,
        ticket_ids: Sequence[str] = (),
        idempotency_keys: Sequence[str] = (),
        cursor: str = "",
    ) -> sidecar_pb2.ReadFiledTicketsReply:
        """What became of the tickets this plugin filed (W4.12, contract
        v13), read for a person it acts for, as filing is: the tickets named
        by `ticket_ids`, those filed under `idempotency_keys`, or, naming
        neither, every one it filed after `cursor` (from the first when it
        is empty), the reply's `next_cursor` empty when nothing follows.

        Each `FiledTicket` carries its state (`TicketState`), its
        `TicketResolution` once resolved or closed, how often it was seen and
        when first and last, and its `answers`, empty until answers arrive
        from outside the deployment; never people's notes, nor who holds or
        works it. A ticket another instance filed is not in the answer.
        """
        self._check_open()
        if ticket_ids and (idempotency_keys or cursor) or idempotency_keys and cursor:
            raise ValueError(
                "name one of ticket_ids, idempotency_keys or cursor: the tickets named, "
                "those filed under the keys, or every one after the cursor"
            )
        metadata = _caller_metadata(for_caller)
        asked = sidecar_pb2.ReadFiledTicketsRequest(
            ticket_ids=list(ticket_ids), idempotency_keys=list(idempotency_keys), cursor=cursor
        )
        reply: sidecar_pb2.ReadFiledTicketsReply = await self._for_person(
            "FiledTickets", self._stub.FiledTickets(asked, metadata=metadata)
        )
        return reply

    # ── The archive (contract v16) ───────────────────────────────────────

    @property
    def stored(self) -> Sequence[sidecar_pb2.StoredSpan]:
        """What this plugin's storage holds of each kind of raw record it
        declared (W4.5, contract v16), as last set: one `StoredSpan` per kind,
        its count and the span from the first received to the last, on every
        heartbeat from the next on. Only the plugin knows its storage; what
        the archive holds the deployment sums from the moves. Refused here,
        as the sidecar would refuse it, for a kind not declared, a kind
        twice or more than 16; nothing is set then."""
        return self._stored

    @stored.setter
    def stored(self, spans: Sequence[sidecar_pb2.StoredSpan]) -> None:
        from .edge import _stored

        self._stored = _stored(spans, self._storage)

    def _moves(self) -> Any:
        from .edge import _Mover

        if self._mover is None:
            self._mover = _Mover(self)
        return self._mover

    async def archive_unit(
        self,
        record_kind: str,
        unit: str,
        *,
        record_count: int,
        first_received_ns: int,
        last_received_ns: int,
    ) -> None:
        """Move one unit of a kind of raw record past its window to the
        archive (W4.13, contract v16): written there, each file checked to
        have landed (size and digest), the move reported through the sidecar
        with its rule -- the kind's window setting and its value -- and only
        then removed from storage, the index keeping it as archived and
        restorable. `unit` is its path in the plugin's storage, a file or a
        directory; `record_count` and the span are the records it holds.

        Refused before anything moves for a kind not declared or declared
        not archivable, an instance given no archive, a unit not in storage
        or archived already, the settings not yet delivered, or the kind's
        `<kind>_past_window` not `archived`; and by the sidecar, which
        records nothing, the unit kept (`CallFailed`). An archive past its
        bound refuses the write, and the unit is kept."""
        self._check_open()
        await self._moves().archive(
            record_kind, unit, record_count, first_received_ns, last_received_ns
        )

    async def restore_unit(
        self, record_kind: str, unit: str, *, for_caller: Caller | str
    ) -> Path:
        """Restore an archived unit for the person who asked (W4.13, W6.9):
        copied back from the archive, each file checked against what was
        archived, to the restore area in storage, the restore reported for
        `for_caller` -- their `Caller` or the header it was read from, at
        write on one of the plugin's edge roles. Answers where the unit is
        readable, until the restore period (seven days) passes and it is
        removed, its return reported; asked again meanwhile, the same path
        and nothing reported. Refused for a unit not archived; by the
        sidecar for a person without write (`NotGranted`), the copy
        removed."""
        self._check_open()
        restored: Path = await self._moves().restore(record_kind, unit, for_caller)
        return restored

    async def delete_unit(
        self,
        record_kind: str,
        unit: str,
        *,
        record_count: int = 0,
        first_received_ns: int = 0,
        last_received_ns: int = 0,
        for_caller: Caller | str | None = None,
    ) -> None:
        """Delete one unit (W4.13, contract v16), the deletion reported
        before anything is removed, so a refusal keeps it. A unit in storage
        past its window, as the plugin itself, where the kind's
        `<kind>_past_window` is `deleted`, its count and span given; or an
        archived unit, which is an admin's act, `for_caller` the person at
        admin on one of the plugin's edge roles, its count and span the
        index's. Inside the deployment's hold the sidecar refuses it:
        `CommandRefused` with REFUSAL_REASON_WITHIN_HOLD, nothing recorded
        and nothing deleted."""
        self._check_open()
        await self._moves().delete(
            record_kind, unit, record_count, first_received_ns, last_received_ns, for_caller
        )

    def find_record(self, key: str) -> sidecar_pb2.RecordMoveRequest | None:
        """Where a raw record's key stands, by the index of what moved: the
        last move of the unit holding it -- the unit itself or a path in it
        -- whose `outcome` says archived and restorable (ARCHIVED),
        readable in the restore area (RESTORED) or deleted (DELETED); None
        for a record never moved, in storage where the plugin put it, or
        unknown. What a row's `record_key` resolves to on the plugin's own
        page (W4.13, requirement 6)."""
        found: sidecar_pb2.RecordMoveRequest | None = self._moves().find(key)
        return found

    async def _for_person(self, operation: str, call: Awaitable[_Answer]) -> _Answer:
        """A call sent for a person, its refusal in this package's terms as a
        typed operation's is."""
        try:
            return await call
        except grpc.aio.AioRpcError as failed:
            _translated(operation, failed)

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
        """What `receive` hears, seeded, followed and caught up (W4.3): the
        rows given a handler, and no others."""
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
            _translated(operation, failed)

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
            if self._storage is not None and self._storage.kinds:
                # Restored units past the restore period, returned (W4.13);
                # tried again on the next beat where it fails.
                with contextlib.suppress(Exception):
                    async with self._moves().lock:
                        await self._moves().return_due()

    def _heartbeat_request(self) -> sidecar_pb2.HeartbeatRequest:
        """The health and figures as they stand: healthy, with no detail and
        no figures, until the plugin reports otherwise."""
        return sidecar_pb2.HeartbeatRequest(
            healthy=self._healthy,
            detail=self._detail,
            figures=self._figures_sent,
            not_carried_seen=[
                sidecar_pb2.NotCarriedSeen(scheme=scheme, name=name, count=count)
                for (scheme, name), count in sorted(self._not_carried_seen.items())
            ],
            stored=self._stored,
        )


def _translated(operation: str, failed: grpc.aio.AioRpcError) -> NoReturn:
    """A sidecar's refusal of `operation` in this package's terms, raised."""
    detail = failed.details() or ""
    if failed.code() is grpc.StatusCode.PERMISSION_DENIED:
        raise NotGranted(operation, detail) from failed
    refusal = _refusal(failed)
    reason = refusal.reason
    if reason == sidecar_pb2.REFUSAL_REASON_EXTERNAL_ACCOUNT_NOT_LINKED:
        raise NotLinked(operation, detail) from failed
    coded = reason != sidecar_pb2.REFUSAL_REASON_UNSPECIFIED
    # ABORTED, a component's refusal of its own; or UNAVAILABLE with a code, a
    # command the component could not check, nothing recorded, to be tried
    # again (contract v10).
    if coded and failed.code() in _CODED:
        raise CommandRefused(
            operation, detail, reason, fields=tuple(refusal.fields)
        ) from failed
    kind = _OPERATION_FAILURES.get(failed.code())
    if kind is None:
        raise failed
    raise CallFailed(operation, kind, detail) from failed


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
    declaration: Declaration | None = None,
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

    From contract v11 a plugin registers with its version's declaration
    (`meridian.declaration.Declaration`): the same one `meridian plugin upload`
    read from its image. Without one, its declaration is its secret settings'
    names alone. A declaration's own settings are the ones registered where
    `settings` names none; naming both, they must be the same.
    """
    from .declaration import Declaration as _Declaration

    if declaration is None:
        declaration = _Declaration(settings=tuple(settings))
    elif not settings:
        settings = tuple(declaration.settings)
    elif declaration.settings and tuple(declaration.settings) != tuple(settings):
        raise ValueError("connect's settings and its declaration's settings differ")
    else:
        declaration = _Declaration(
            settings=tuple(settings),
            not_carried=declaration.not_carried,
            storage=declaration.storage,
        )
    # From contract v16, the two settings per kind of raw record, which the
    # SDK declares for every edge plugin alike (W4.1, W6.11), and the restore
    # route on its host (the names' choice b).
    storage = declaration.storage
    if storage is not None and storage.kinds:
        from .edge import _archive, _restore_route

        edge = _edge_roles(settings, interface)
        settings = (
            *settings,
            *declaration._window_settings(archive=_archive() is not None, roles=edge),
        )
        from .pages import Pages as _Pages

        if interface is not None and isinstance(interface.pages, _Pages):
            _restore_route(interface.pages, edge)
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
                declaration=declaration.to_wire(),
                tools=interface._tools() if interface is not None else [],
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
        _storage=storage,
    )
    if heartbeat:
        plugin._heartbeat = asyncio.create_task(plugin._beat())
    # Under `meridian-dev run`, on a development deployment: this revision
    # is running, which is what `ready` means (spec/live-plugin-development).
    from .dev import report_ready

    report_ready()
    return plugin


def _edge_roles(settings: Sequence[Setting], interface: Interface | None) -> tuple[str, ...]:
    """The edge roles the window settings and the restore route serve, on a
    plugin naming roles (contract v15): those its own settings and pages
    name; none on a plugin naming none, which serves its one role."""
    from .declaration import EDGE_ROLES
    from .pages import Pages as _Pages

    named: list[str] = [role for setting in settings for role in setting.roles]
    if interface is not None:
        pages = (
            interface.pages.declared if isinstance(interface.pages, _Pages) else interface.pages
        )
        named.extend(role for page in pages for role in page.roles)
    return tuple(sorted({role for role in named if role in EDGE_ROLES}))


def __getattr__(name: str) -> Any:
    """A name this module no longer has, said plainly rather than as a typo."""
    if name == "TagAccess":
        raise AttributeError(_RETIRED_BY_026)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
