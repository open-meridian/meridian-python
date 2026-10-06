"""A plugin's pages, declared and enforced in one place, each a view function
and a template on the kit's one base template (W4.8, W6.9).

    pages = meridian.Pages("Statements", templates=Path(__file__).parent / "templates")

    @pages.page("/", "Statements", levels=["write", "read"])
    async def statements(request: meridian.Request) -> str:
        rows = [...]  # cut to request.caller.read
        return pages.render("statements.html", rows=rows)

    @pages.route("/sync", levels=["write"], methods=["POST"])
    async def sync(request: meridian.Request) -> str: ...

    meridian.Interface(port=8000, title="Statements", pages=pages)

`page` declares a tab and `route` an endpoint that is not one. Each records
the declaration, which `Interface(pages=pages)` sends at registration, and
wraps the view, which then answers 403 to a session whose level the page does
not serve, before the view runs: the tab row shows a page and the plugin
refuses it by the same declaration. One path may serve several levels, and
adapts by `request.caller.level`. A session is opened at one level by the
home's buttons: Manage `admin`, Open `write`, View `read`.

From contract v15 a person holds a level on each role of a plugin, and a
plugin holding several roles names the roles each page, route and tool
serves (`roles=`): served when the person's level on one of them within the
session's button is one of its levels, and adapting per role by
`request.caller.level_for(role)`, `read_for(role)` and `write_for(role)`. A
plugin holding one role, or none, names none, and nothing changes:

    @pages.page("/statements", "Statements", roles=["custody"], levels=["write", "read"])
    async def statements(request: meridian.Request) -> str:
        rows = [...]  # cut to request.caller.read_for("custody")

`render` renders a Jinja2 template from `templates`, autoescaped, with
`caller` and `level` (admin, write or read) always in its context. A page's
template extends the kit's one base template, `meridian/base.html`, which
links the kit's stylesheet and script -- each person's theme, and the frame's
messages: the page's size, its header actions and its status -- and draws
the page's heading and the tab row of the pages at the session's level,
which the kit drops when the dashboard frames the page and draws its own. So
one page serves framed and standalone alike:

    {% extends "meridian/base.html" %}
    {% block status %}
      <om-status data-om-header state="ok" label="Synced"></om-status>
    {% endblock %}
    {% block head_actions %}
      {% if level == "write" %}
      <form class="inline" method="post" action="/sync">
        <button data-om-action="sync">Sync</button></form>
      {% endif %}
    {% endblock %}
    {% block content %}
      <om-grid row-key="id"><script type="application/json">{{ grid|tojson }}</script></om-grid>
    {% endblock %}

`status` is an `om-status` the host draws beside the plugin's name (kit
0.7.0), and `head_actions` holds buttons marked `data-om-action` the host
draws in its header (kit 0.4.0); on its own, the page shows both itself.
`tojson` writes a kit component's data safely inside its `<script>`.
`{% include %}` and macros compose a page from pieces.

A route that changes something cannot be asked for from another page. The
plugin's host keeps the person's session in a cookie, and every plugin's host
is the same site as the dashboard, so the cookie's SameSite=Lax does not stop
another plugin's page from posting here as the person; and the plugin cannot
check an `Origin` against its own, since the host it is reached at never
reaches it. So every request but GET and HEAD must carry a token only a page
of this plugin could have read: `{{ csrf_input }}` in a form, or the
`X-CSRF-Token` header from a script, `request.csrf_token` in a view. It is an
HMAC of the person and the session's level under a secret this process makes
at start, checked before the view runs and answered 403 when it is missing or
wrong. A restart makes a page open before it stale, which a reload mends.

The tab row marks the tab whose path the request is for. A request for a
path that is no tab -- a form's action that answers by rendering a page --
marks the tab it was sent from, its `Referer`'s path, when it carried this
plugin's token, so came from one of its pages.

HEAD is answered for every path that takes GET: the GET view runs, with
`request.method` HEAD, and the answer's headers are sent without its body.
A request whose body is larger than `max_body` bytes (`Pages(max_body=...)`,
1 MiB unless said, or `serve(..., max_body=...)`) is answered 413 before
anything reads it, so a view need not measure what it is sent.

The pages are an ASGI application (`pages.app(plugin)`), with the caller read
as `CallerMiddleware` reads it; `pages.serve(plugin, port)` runs it on the
standard library's server, so a plugin needs nothing its base image does not
have.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextvars
import dataclasses
import functools
import hashlib
import hmac
import http.server
import inspect
import json
import logging
import os
import re
import secrets
import threading
import urllib.parse
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn, cast

import jinja2
from markupsafe import Markup

from . import params as _params
from .asgi import ASGIApp, CallerMiddleware, Receive, Scope, Send
from .client import BUTTONS, Caller, Page, _levels, _roles, _serves
from .v1 import sidecar_pb2

if TYPE_CHECKING:
    from .client import Plugin

log = logging.getLogger("meridian.pages")

#: The kit the base template links, from the path the dashboard serves it at on
#: the plugin's own host. A dashboard answers any 0.x with the newest 0.x it
#: carries; this is the version the base template was built against.
KIT = "0.9.0"

#: The form field, and the header, a request that changes something carries its
#: token in.
CSRF_FIELD = "csrf"
CSRF_HEADER = "x-csrf-token"

#: The methods that change nothing, and so carry no token.
SAFE_METHODS = frozenset({"GET", "HEAD"})

#: How long the standard library's server waits for a view before answering 500.
REQUEST_SECONDS = 60.0

#: The largest body a request may carry unless `Pages` or `serve` says
#: otherwise: far over any form of a page's, and under what would weigh on a
#: plugin's memory.
MAX_BODY = 1024 * 1024

TOO_LARGE = "This request is larger than this plugin takes."

#: What the standard library's server reads and drops of a body it refused,
#: and for how long, so that closing the connection does not reset it before
#: the sender reads the answer. Past either, it is closed regardless.
DISCARD = 64 * 1024 * 1024
DISCARD_SECONDS = 10.0

#: A level's ruled spelling, as a template reads it in `level`.
SPELLING: dict[int, str] = {
    sidecar_pb2.ACCESS_LEVEL_ADMIN: "admin",
    sidecar_pb2.ACCESS_LEVEL_WRITE: "write",
    sidecar_pb2.ACCESS_LEVEL_READ: "read",
}


# Markup is markupsafe's, re-exported: text that is HTML already, which a
# template puts in as it is, where it escapes every other value.
__all__ = ["KIT", "MAX_BODY", "Field", "Markup", "Pages", "Refusal", "Request", "Response"]


@dataclass(frozen=True)
class Request:
    """A request for one of the plugin's pages, as its sidecar forwarded it.

    `caller` is who is asking, read from the `Meridian-Caller` header, with
    the level their session was opened at. `plugin` is the registered plugin
    the pages were served for, whose operations a view calls, with
    `acting_for=request.caller.header` to act for the person. `query` and
    `form` are the query string's and a form's fields, the last of each name;
    `headers` its headers, by lower-case name; `body` is the body as sent.
    `csrf_token` is the token a request that changes something must carry
    back, set before the view runs.
    """

    method: str
    path: str
    caller: Caller
    plugin: Plugin
    query: Mapping[str, str] = field(default_factory=dict)
    form: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)
    csrf_token: str = ""
    # The route's typed record of inputs (`params=`), read from the form by
    # its fields' paths or from a tool's JSON; None where the route declares
    # none, or a form left out a field the record requires. `param_errors`
    # names each field that did not read, by its path: a tool's call never
    # reaches the view with one, a browser's does, so the page can show the
    # person what they typed and what is wrong with it.
    params: Any = None
    param_errors: tuple[_params.Problem, ...] = ()

    @property
    def tool_name(self) -> str:
        """The tool this request is a call to, through the deployment's MCP
        surface (contract v12): set only by the dashboard's `/mcp`, and never
        for a browser's request."""
        return self.caller.tool_name


@dataclass(frozen=True)
class Response:
    """What a view answers; a view may answer a `str` instead, an HTML page."""

    body: str | bytes = ""
    status: int = 200
    content_type: str = "text/html; charset=utf-8"
    headers: tuple[tuple[str, str], ...] = ()

    @property
    def text(self) -> str:
        return self.body if isinstance(self.body, str) else self.body.decode()

    def _bytes(self) -> bytes:
        return self.body.encode() if isinstance(self.body, str) else self.body


@dataclass(frozen=True)
class Field:
    """One field a refusal names: its path in the route's record by the data
    dictionary's grammar (`positions[3].lots[0].cost`), or a path in the
    command it was sent in (`positions[2].instrument.asset_class`); the
    plugin's words; and, where it resolves, the dictionary's entry and what
    the entry says, so an agent reads why without parsing a sentence."""

    path: str
    message: str = ""
    entry: str = ""
    said: str = ""

    @classmethod
    def of(cls, path: str, message: str = "", *, operation: str = "", at: str = "") -> Field:
        """A field, resolved to its entry through `operation` (a matrix row's
        name, such as RecordOpeningBalance) at `at`, the path in its command
        (the field's own path unless given)."""
        found = None
        if operation:
            from .dictionary import entry

            found = entry(operation, at or path)
        if found is None:
            return cls(path, message)
        return cls(path, message, str(found["name"]), str(found.get("meaning", "")))

    def to_json(self) -> dict[str, str]:
        out = {"path": self.path}
        for name in ("message", "entry", "said"):
            if getattr(self, name):
                out[name] = getattr(self, name)
        return out


class Refusal(Exception):  # noqa: N818 - a refusal, not an error of the plugin's
    """A route refusing what it was asked, by path (`Pages.refuse`): a tool's
    call answers it as its error, outcome refused, each field by its path; a
    browser's request is answered 422 with it in words, unless the route
    says how its page shows it (`on_refused=`)."""

    def __init__(
        self, detail: str, fields: Sequence[Field] = (), reason: str = "refused"
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.fields = tuple(fields)
        self.reason = reason

    def to_json(self) -> dict[str, Any]:
        return {
            "outcome": "refused",
            "reason": self.reason,
            "fields": [each.to_json() for each in self.fields],
            "detail": self.detail,
        }


View = Callable[[Request], Response | str | Awaitable[Response | str]]
Guarded = Callable[[Request], Awaitable[Response]]


#: A tool's name: lower-case letters, digits, `_` and `-`, at most 61.
TOOL_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,60}")


@dataclass(frozen=True)
class Tool:
    """A tool the plugin offers on the deployment's MCP surface, derived from
    a route that declares its inputs (contract v12; W4.1, W6.20)."""

    name: str
    title: str
    description: str
    method: str
    path: str
    levels: tuple[int, ...]
    reads: bool
    params: Any = None
    answers: Any = None
    # The roles it serves (contract v15): a derived tool takes its route's.
    roles: tuple[str, ...] = ()

    def declared(self) -> sidecar_pb2.ToolDeclaration:
        inputs = (
            _params.schema(self.params)
            if self.params is not None
            else {"type": "object", "properties": {}, "additionalProperties": False}
        )
        output = ""
        if self.reads:
            output = json.dumps(
                _params.schema(self.answers)
                if self.answers is not None
                else {"type": "object"},
                separators=(",", ":"),
            )
        return sidecar_pb2.ToolDeclaration(
            name=self.name,
            title=self.title,
            description=self.description,
            method=self.method,
            path=self.path,
            levels=cast(Any, list(self.levels)),
            reads=self.reads,
            input_schema=json.dumps(inputs, separators=(",", ":")),
            output_schema=output,
            roles=list(self.roles),
        )


@dataclass(frozen=True)
class NotOffered:
    """A route a plugin declares it does not offer to agents, and why: what
    `meridian plugin check` reports, and verification refuses on a changing
    route."""

    method: str
    path: str
    why: str


@dataclass(frozen=True)
class _Route:
    path: str
    levels: tuple[int, ...]
    guarded: Guarded
    # The tab, for a page; none for a route.
    page: Page | None
    params: Any = None
    tool: Tool | None = None
    # The roles it serves (contract v15); none on a plugin holding one or none.
    roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Serving:
    request: Request
    route: _Route

    @property
    def for_a_tool(self) -> bool:
        return bool(self.request.tool_name)


_serving: contextvars.ContextVar[_Serving] = contextvars.ContextVar("meridian.pages")


# What every page extends. The heading and the tab row are the page's when it
# is opened on its own; framed, the dashboard draws both, and the kit drops
# these, and hands the host the head's status and actions
# (spec/plugin-pages-share-one-kit.md, Q3).
BASE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}{{ meridian.title }}{% endblock %}</title>
<link rel="stylesheet" href="{{ meridian.kit }}meridian.css">
<script src="{{ meridian.kit }}meridian.js"></script>
</head>
<body>
<main class="page">
<header class="page-head">
<div><h1>{{ meridian.heading }}</h1></div>
{% block status %}{% endblock %}
{% if self.head_actions()|trim %}
<div class="actions">{% block head_actions %}{% endblock %}</div>
{% endif %}
</header>
{% if meridian.tabs|length > 1 %}
<nav class="tabs">
{% for tab in meridian.tabs %}
<a class="tab{% if tab.current %} on{% endif %}" href="{{ tab.path }}"
{%- if tab.current %} aria-current="page"{% endif %}>{{ tab.title }}</a>
{% endfor %}
</nav>
{% endif %}
{% block content %}{% endblock %}
</main>
</body>
</html>
"""


class Pages:
    """The plugin's pages: each declared where its view is, and served only in
    a session at a level it declares. See the module's documentation."""

    def __init__(
        self,
        title: str = "",
        *,
        templates: str | os.PathLike[str] | None = None,
        kit: str = KIT,
        max_body: int = MAX_BODY,
    ) -> None:
        self.title = title
        self.max_body = _limit(max_body)
        self.templates = None if templates is None else Path(templates)
        if self.templates is not None and not self.templates.is_dir():
            raise FileNotFoundError(f"the pages' templates are not at {self.templates}")
        self.kit = f"/.meridian/ui/{kit}/"
        self._routes: dict[tuple[str, str], _Route] = {}
        self._pages: list[Page] = []
        self._tools: dict[str, Tool] = {}
        # A tool replacing a derived one, by its route: its view serves the
        # calls naming it there.
        self._replacing: dict[tuple[str, str], tuple[Tool, Guarded]] = {}
        self.not_offered: list[NotOffered] = []
        # Held by this process alone, and new at every start.
        self._secret = secrets.token_bytes(32)
        loaders: list[jinja2.BaseLoader] = [jinja2.DictLoader({"meridian/base.html": BASE})]
        if self.templates is not None:
            loaders.append(jinja2.FileSystemLoader(self.templates))
        self.environment = jinja2.Environment(
            loader=jinja2.ChoiceLoader(loaders),
            autoescape=jinja2.select_autoescape(["html", "htm", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # ── Declaring ────────────────────────────────────────────────────────

    def page(
        self,
        path: str,
        title: str,
        *,
        levels: Sequence[str | int] | str | int,
        roles: Sequence[str] | str = (),
        methods: Iterable[str] = ("GET",),
        params: Any = None,
        answers: Any = None,
        name: str | None = None,
        description: str | None = None,
        tool: bool = True,
        why: str = "",
    ) -> Callable[[View], Guarded]:
        """A tab: shown under the home's button for each of `levels`, in the
        order declared, and served only in a session at one of them.

        From contract v12 a page that declares the typed data it renders
        (`answers=`, and `params=` for its inputs) is also a read tool on the
        deployment's MCP surface, answering that data (`answer`).

        From contract v15 `roles=` names the roles it serves, from those the
        plugin was launched with: served when the person's level on one of
        them within the session's button is one of `levels`. A plugin holding
        one role, or none, names none."""
        levelled = _levels(levels, f"page {title!r}")
        page = Page(path, title, levels=levelled, roles=_roles(roles, f"page {title!r}"))
        page._declared()  # a path without its slash, or no level, refused now
        return self._add(
            path,
            levelled,
            methods,
            page,
            _Declared(params, answers, name, description, None, tool, why, title),
            cast(tuple[str, ...], page.roles),
        )

    def route(
        self,
        path: str,
        *,
        levels: Sequence[str | int] | str | int,
        roles: Sequence[str] | str = (),
        methods: Iterable[str] = ("GET",),
        params: Any = None,
        answers: Any = None,
        name: str | None = None,
        description: str | None = None,
        reads: bool | None = None,
        tool: bool = True,
        why: str = "",
        title: str = "",
    ) -> Callable[[View], Guarded]:
        """An endpoint that is not a tab -- a form's action, a page's data --
        served only in a session at one of `levels`.

        From contract v12 a route declaring its inputs as one typed record
        (`params=`) is derived as a tool: an act for a method that changes
        something, unless `reads=True` says it changes nothing; a read for
        GET, answering `answers=`. `name=` names the tool (else the view's
        name), `description=` says what it does (else the view's docstring's
        first paragraph). `tool=False` with `why=` declares a route not
        offered to agents, which `meridian plugin check` reports and
        verification refuses on a changing route.

        From contract v15 `roles=` names the roles it serves, as a page's do,
        and its tool serves the same."""
        levelled = _levels(levels, f"route {path!r}")
        if not path.startswith("/"):
            raise ValueError(f"route {path!r} does not begin with /")
        if not levelled:
            raise ValueError(f"route {path!r} names no level: admin, write or read")
        return self._add(
            path,
            levelled,
            methods,
            None,
            _Declared(params, answers, name, description, reads, tool, why, title),
            _roles(roles, f"route {path!r}"),
        )

    def tool(
        self,
        *,
        replaces: str,
        method: str = "POST",
        params: Any = None,
        answers: Any = None,
        name: str | None = None,
        description: str | None = None,
        reads: bool | None = None,
        title: str = "",
        roles: Sequence[str] | str | None = None,
    ) -> Callable[[View], Guarded]:
        """A tool replacing the one derived from the route at `replaces` and
        `method` (or standing in for one the route could not derive): its view
        serves the calls naming it there, at the route's levels; a browser's
        request still reaches the route's own view. It serves the route's
        roles, or those `roles=` names (contract v15)."""
        verb = method.upper()
        route = self._routes.get((replaces, verb))
        if route is None:
            raise ValueError(f"no route {verb} {replaces} for a tool to replace")
        served = (
            route.roles if roles is None else _roles(roles, f"the tool at {verb} {replaces}")
        )

        def decorate(view: View) -> Guarded:
            made = self._tool_of(
                view,
                replaces,
                verb,
                route.levels,
                _Declared(params, answers, name, description, reads, True, "", title),
                served,
            )
            if made is None:
                raise ValueError(f"the tool replacing {verb} {replaces} declares no params=")
            if route.tool is not None:
                self._tools.pop(route.tool.name, None)
            if made.name in self._tools:
                raise ValueError(f"the tool {made.name} is declared twice")
            self._tools[made.name] = made
            replacing = dataclasses.replace(route, tool=made, params=made.params, roles=served)
            guarded = self._guard(view, replacing)
            self._replacing[(replaces, verb)] = (made, guarded)
            self.not_offered = [
                each
                for each in self.not_offered
                if (each.method, each.path) != (verb, replaces)
            ]
            return guarded

        return decorate

    def _tool_of(
        self,
        view: View,
        path: str,
        verb: str,
        levels: tuple[int, ...],
        declared: _Declared,
        roles: tuple[str, ...] = (),
    ) -> Tool | None:
        """The tool a route declares, or None where it is not derivable."""
        if not declared.tool:
            return None
        reads = declared.reads if declared.reads is not None else verb in SAFE_METHODS
        if declared.params is None and not (declared.answers is not None and reads):
            return None
        for record in (declared.params, declared.answers):
            if record is not None:
                _params.check(record)
        name: str = declared.name or str(getattr(view, "__name__", ""))
        if not TOOL_NAME.fullmatch(name):
            raise ValueError(
                f"the tool at {verb} {path} is named {name!r}: lower-case letters, digits, _ "
                "and -, at most 61, beginning with a letter or digit; give name="
            )
        docstring = inspect.getdoc(view) or ""
        description = (
            declared.description
            or docstring.split("\n\n")[0].replace("\n", " ")
            or declared.title
            or name.replace("_", " ")
        ).strip()[:1024]
        title = (declared.title or name.replace("_", " ").replace("-", " ").capitalize())[:120]
        return Tool(
            name=name,
            title=title,
            description=description,
            method=verb,
            path=path,
            levels=levels,
            reads=reads,
            params=declared.params,
            answers=declared.answers,
            roles=roles,
        )

    def _add(
        self,
        path: str,
        levels: tuple[int, ...],
        methods: Iterable[str],
        page: Page | None,
        declared: _Declared,
        roles: tuple[str, ...] = (),
    ) -> Callable[[View], Guarded]:
        verbs = tuple(dict.fromkeys(method.upper() for method in methods))
        for verb in verbs:
            if (path, verb) in self._routes:
                raise ValueError(f"{verb} {path} is declared twice")
        if not declared.tool and not declared.why.strip():
            raise ValueError(
                f"{path} is declared tool=False without why=: say why it is not offered"
            )
        if declared.params is not None:
            _params.check(declared.params)

        def decorate(view: View) -> Guarded:
            guarded: Guarded | None = None
            for verb in verbs:
                made = self._tool_of(view, path, verb, levels, declared, roles)
                if made is not None:
                    if made.name in self._tools:
                        # One view serving two methods: one tool, at the first.
                        made = None
                    else:
                        self._tools[made.name] = made
                if not declared.tool:
                    self.not_offered.append(NotOffered(verb, path, declared.why.strip()))
                route = _Route(path, levels, None, page, declared.params, made, roles)  # type: ignore[arg-type]
                serving = self._guard(view, route)
                route = dataclasses.replace(route, guarded=serving)
                self._routes[(path, verb)] = route
                guarded = guarded or serving
            if page is not None:
                self._pages.append(page)
            assert guarded is not None
            return guarded

        return decorate

    def _guard(self, view: View, route: _Route) -> Guarded:
        """The view, served only in a session at one of the route's levels,
        on one of its roles where it names them, its form token checked for a
        browser, its record read."""
        path, levels = route.path, route.levels

        @functools.wraps(view)
        async def guarded(request: Request) -> Response:
            if not _serves(levels, route.roles, request.caller):
                return _refusal(path, levels, request.caller, route.roles)
            request = dataclasses.replace(request, csrf_token=self.csrf_token(request.caller))
            if request.tool_name:
                # Only `/mcp` sets a tool's name, and the sidecar admits it at
                # this tool's route alone (W4.9): no browser's cookie came
                # with it, so no form token guards it.
                if route.tool is None or route.tool.name != request.tool_name:
                    return _tool_refused(
                        Refusal(
                            f"{request.method} {path} is not the tool {request.tool_name}",
                            reason="not_this_tool",
                        ),
                        403,
                    )
            elif request.method.upper() not in SAFE_METHODS and not _presented(request):
                return Response(
                    "This form has expired or did not come from this plugin's page. "
                    "Reload the page and try again.",
                    403,
                    "text/plain; charset=utf-8",
                )
            if route.params is not None:
                read = _read_params(route.params, request)
                if isinstance(read, Refusal):
                    return _tool_refused(read, 422)
                record, problems = read
                request = dataclasses.replace(request, params=record, param_errors=problems)
            serving = _serving.set(_Serving(request, route))
            try:
                try:
                    answer = view(request)
                    if inspect.isawaitable(answer):
                        answer = await answer
                except Refusal as refused:
                    if request.tool_name:
                        return _tool_refused(refused, 422)
                    return Response(_refusal_words(refused), 422, "text/plain; charset=utf-8")
            finally:
                _serving.reset(serving)
            if isinstance(answer, str):
                answer = Response(answer)
            if not isinstance(answer, Response):
                raise TypeError(
                    f"the view at {path} answered a {type(answer).__name__}; "
                    "a view answers a str, the page, or a Response"
                )
            if request.tool_name and not answer.content_type.startswith("application/json"):
                # A tool answers typed data (`answer`) or a refusal (`refuse`):
                # a page's HTML could say anything, a refusal included.
                log.error(
                    "the tool %s at %s answered a page, not typed data", request.tool_name, path
                )
                return _tool_refused(
                    Refusal(
                        f"the tool {request.tool_name} answered a page, not typed data: "
                        "its view answers with pages.answer or pages.refuse",
                        reason="untyped_answer",
                    ),
                    500,
                )
            return answer

        return guarded

    def csrf_token(self, caller: Caller) -> str:
        """The token a request from this person, in a session at this level,
        carries back when it changes something."""
        said = f"{caller.subject}\0{caller.level}".encode()
        return hmac.new(self._secret, said, hashlib.sha256).hexdigest()

    @property
    def declared(self) -> tuple[Page, ...]:
        """The tabs, in the order declared: what registration sends."""
        return tuple(self._pages)

    @property
    def tools(self) -> tuple[Tool, ...]:
        """The tools derived from the routes, and those replacing them, in
        the order declared: what registration sends (contract v12)."""
        return tuple(self._tools.values())

    # ── Answering ────────────────────────────────────────────────────────

    def answer(
        self,
        template: str,
        data: Any,
        /,
        *,
        outcome: str | None = None,
        status: int = 200,
        **context: Any,
    ) -> Response:
        """`data` as the route's answer: rendered into `template` for a
        browser, with `data` in its context beside `context`; for a tool's
        call, `data` itself as JSON with its outcome -- `made` for an act,
        `unchanged` for a read or for a repeat the plugin recognised
        (`outcome=`). Called from a view, while it serves a request."""
        serving = _current()
        if serving.for_a_tool:
            reads = serving.route.tool is not None and serving.route.tool.reads
            said = outcome or ("unchanged" if reads else "made")
            if said not in ("made", "unchanged"):
                raise ValueError(f"an answer's outcome is made or unchanged, not {said!r}")
            body = {"outcome": said, "data": _params.to_json(data)}
            return Response(json.dumps(body, separators=(",", ":")), status, "application/json")
        return Response(self.render(template, data=data, **context), status)

    def refuse(
        self, detail: str, *fields: Field | str | tuple[str, str], reason: str = "refused"
    ) -> NoReturn:
        """Refuse what the route was asked, naming each field by its path:
        a tool's call gets it as its error; a browser's page shows it."""
        named = [
            each
            if isinstance(each, Field)
            else Field(each)
            if isinstance(each, str)
            else Field(each[0], each[1])
            for each in fields
        ]
        raise Refusal(detail, named, reason)

    # ── Serving ──────────────────────────────────────────────────────────

    async def dispatch(self, request: Request) -> Response:
        """The view declared at the request's path and method, if the
        session's level is one it serves: 404 for no such path, 405 for a
        method it does not take, 403 for a level it does not serve. HEAD
        runs the GET view where none is declared for HEAD, and answers its
        headers, with the length of the body it does not send."""
        answer = await self._dispatch(request)
        if request.method.upper() != "HEAD":
            return answer
        length = (("content-length", str(len(answer._bytes()))),)
        unsent = tuple((n, v) for n, v in answer.headers if n.lower() != "content-length")
        return dataclasses.replace(answer, body=b"", headers=unsent + length)

    async def _dispatch(self, request: Request) -> Response:
        method = request.method.upper()
        route = self._routes.get((request.path, method))
        if route is None and method == "HEAD":
            route = self._routes.get((request.path, "GET"))
        if route is not None:
            replaced = self._replacing.get((route.path, method))
            if replaced is not None and request.tool_name == replaced[0].name:
                return await replaced[1](request)
            return await route.guarded(request)
        taken = {verb for path, verb in self._routes if path == request.path}
        if "GET" in taken:
            taken.add("HEAD")
        if taken:
            return Response(
                f"{request.path} takes {', '.join(sorted(taken))}.",
                405,
                "text/plain; charset=utf-8",
                (("allow", ", ".join(sorted(taken))),),
            )
        return Response("No such page.", 404, "text/plain; charset=utf-8")

    def app(self, plugin: Plugin | None = None) -> ASGIApp:
        """The pages as an ASGI application, serving `plugin`: the caller read
        from the header its sidecar forwarded (401 without one), then
        dispatched. A body over `max_body` is answered 413 without being
        read; a view that raises is logged and answered 500."""
        return self._app(plugin, self.max_body)

    def _app(self, plugin: Plugin | None, max_body: int) -> ASGIApp:
        async def serve(scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] == "lifespan":
                while True:
                    message = await receive()
                    if message["type"] == "lifespan.startup":
                        await send({"type": "lifespan.startup.complete"})
                    elif message["type"] == "lifespan.shutdown":
                        await send({"type": "lifespan.shutdown.complete"})
                        return
            if scope["type"] != "http":
                return
            body = await _body(scope, receive, max_body)
            if body is None:
                await _answer(send, Response(TOO_LARGE, 413, "text/plain; charset=utf-8"))
                return
            request = _request(scope, body, plugin)
            try:
                response = await self.dispatch(request)
            except Exception:
                log.exception("%s %s failed", request.method, request.path)
                response = Response(
                    "The page failed; the plugin's log says why.",
                    500,
                    "text/plain; charset=utf-8",
                )
            await _answer(send, response)

        return CallerMiddleware(serve)

    def serve(
        self,
        plugin: Plugin,
        port: int,
        *,
        loop: asyncio.AbstractEventLoop | None = None,
        max_body: int | None = None,
    ) -> http.server.ThreadingHTTPServer:
        """Serve the pages on 127.0.0.1:`port`, with the standard library's
        server, in a thread of its own; each view runs on `loop`, the running
        one by default, where the plugin's operations are. A request whose
        Content-Length is over `max_body`, the pages' own unless said, is
        answered 413 without its body being read. The returned server's
        `shutdown()` stops it."""
        most = self.max_body if max_body is None else _limit(max_body)
        return _serve(self._app(plugin, most), port, loop or asyncio.get_running_loop(), most)

    # ── Rendering ────────────────────────────────────────────────────────

    def render(self, template: str, /, **context: Any) -> str:
        """`template`, from `templates`, rendered with `context`, `caller` and
        `level` (admin, write or read); a page's template extends
        `meridian/base.html`. Called from a view, while it serves a request."""
        serving = _current()
        caller = serving.request.caller
        tabs = [each for each in self._pages if each.serves(caller)]
        at = _shown(serving.request, {each.path for each in tabs})
        # A route answering with a page is titled as the tab it marks.
        page = serving.route.page or next((each for each in tabs if each.path == at), None)
        named = page.title if page is not None else ""
        base = {
            "kit": self.kit,
            "heading": self.title or named,
            "title": " · ".join(part for part in (named, self.title) if part),
            "tabs": [
                {"path": each.path, "title": each.title, "current": each.path == at}
                for each in tabs
            ],
        }
        return self.environment.get_template(template).render(
            {
                **context,
                "caller": caller,
                "level": SPELLING.get(caller.level, ""),
                "csrf_token": serving.request.csrf_token,
                "csrf_input": Markup('<input type="hidden" name="{}" value="{}">').format(
                    CSRF_FIELD, serving.request.csrf_token
                ),
                "meridian": base,
            }
        )


@dataclass(frozen=True)
class _Declared:
    """What a route declares of itself as a tool."""

    params: Any
    answers: Any
    name: str | None
    description: str | None
    reads: bool | None
    tool: bool
    why: str
    title: str


def _read_params(
    record: Any, request: Request
) -> Refusal | tuple[Any, tuple[_params.Problem, ...]]:
    """The route's record from the request: a tool's JSON body, refused by
    path where it does not read; a script's JSON alike; or a form's fields
    (a GET's query), each field that does not read named beside it."""
    kind = request.headers.get("content-type", "").split(";")[0].strip()
    if request.tool_name or kind == "application/json":
        try:
            arguments = json.loads(request.body or b"{}")
        except ValueError:
            return Refusal("the arguments are not JSON", reason="invalid_arguments")
        try:
            return _params.from_json(record, arguments), ()
        except _params.Unread as unread:
            if request.tool_name:
                return Refusal(
                    "; ".join(
                        f"{p.path or 'the arguments'}: {p.message}" for p in unread.problems
                    ),
                    [Field(p.path, p.message) for p in unread.problems],
                    "invalid_arguments",
                )
            return None, unread.problems
    given = request.query if request.method.upper() in SAFE_METHODS else request.form
    return _params.from_form(record, given)


def _tool_refused(refusal: Refusal, status: int) -> Response:
    return Response(
        json.dumps(refusal.to_json(), separators=(",", ":")), status, "application/json"
    )


def _refusal_words(refusal: Refusal) -> str:
    lines = [refusal.detail] + [
        f"{each.path}: {each.message or each.said}".rstrip(": ") for each in refusal.fields
    ]
    return "\n".join(line for line in lines if line)


def _presented(request: Request) -> bool:
    """Whether the request carries its token back, in its form or a header."""
    presented = request.form.get(CSRF_FIELD) or request.headers.get(CSRF_HEADER, "")
    return bool(presented) and hmac.compare_digest(
        presented.encode(), request.csrf_token.encode()
    )


def _shown(request: Request, tabs: set[str]) -> str:
    """The tab a page rendered for `request` marks: the one at its path, or,
    for a request that carried this plugin's token and so was sent from one
    of its pages, the one it was sent from. Otherwise none."""
    if request.path in tabs:
        return request.path
    if request.method.upper() in SAFE_METHODS:
        return ""
    sent_from = urllib.parse.urlsplit(request.headers.get("referer", "")).path
    return sent_from if sent_from in tabs else ""


def _limit(most: int) -> int:
    if isinstance(most, bool) or not isinstance(most, int) or most < 0:
        raise ValueError(f"max_body is a number of bytes, not {most!r}")
    return most


async def _body(scope: Scope, receive: Receive, most: int) -> bytes | None:
    """The request's body, or None when it is over `most` bytes: refused by
    its Content-Length before any of it is read, or as soon as it passes."""
    for name, value in scope.get("headers", []):
        if name.lower() == b"content-length" and value.strip().isdigit() and int(value) > most:
            return None
    body = b""
    while True:
        message = await receive()
        body += cast(bytes, message.get("body", b""))
        if len(body) > most:
            return None
        if not message.get("more_body"):
            return body


def _current() -> _Serving:
    try:
        return _serving.get()
    except LookupError:
        raise RuntimeError("render is called from a view, while it serves a request") from None


def _refusal(
    path: str, levels: tuple[int, ...], caller: Caller, roles: tuple[str, ...] = ()
) -> Response:
    served = " and ".join(BUTTONS[each] for each in levels)
    level = caller.level
    if level == sidecar_pb2.ACCESS_LEVEL_UNSPECIFIED:
        said = "This session was opened at no level, and holds nothing here."
    elif level not in BUTTONS:
        said = f"{path} is not served at level {level}; it is for {served}."
    elif roles:
        # Served by role (contract v15): say which, and what the session
        # holds on each, as the sidecar's refusal does.
        held = ", ".join(
            f"{SPELLING.get(caller.level_for(role), 'nothing')} on {role}" for role in roles
        )
        said = (
            f"{path} is for {' and '.join(roles)} under {served}; under "
            f"{BUTTONS[level]} this session holds {held}."
        )
    else:
        said = f"{path} is not served under {BUTTONS[level]}; it is for {served}."
    return Response(said, 403, "text/plain; charset=utf-8")


def _request(scope: Scope, body: bytes, plugin: Any) -> Request:
    headers = {name.lower(): value for name, value in scope.get("headers", [])}
    query = dict(urllib.parse.parse_qsl(scope.get("query_string", b"").decode("latin-1")))
    kind = headers.get(b"content-type", b"").split(b";")[0].strip()
    form = (
        dict(urllib.parse.parse_qsl(body.decode(), keep_blank_values=True))
        if kind == b"application/x-www-form-urlencoded"
        else {}
    )
    return Request(
        method=scope["method"],
        path=scope["path"],
        caller=scope["state"]["caller"],
        plugin=plugin,
        query=query,
        form=form,
        body=body,
        headers={
            name.decode("latin-1"): value.decode("latin-1") for name, value in headers.items()
        },
    )


async def _answer(send: Send, response: Response) -> None:
    body = response._bytes()
    others = [(n, v) for n, v in response.headers if n.lower() != "content-length"]
    given = [v for n, v in response.headers if n.lower() == "content-length"]
    # A HEAD's answer carries the length of the body it does not send
    # (dispatch); any other body is measured.
    length = given[0] if given and not body else str(len(body))
    await send(
        {
            "type": "http.response.start",
            "status": response.status,
            "headers": [
                (b"content-type", response.content_type.encode("latin-1")),
                (b"content-length", length.encode("latin-1")),
                *((name.encode("latin-1"), value.encode("latin-1")) for name, value in others),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _serve(
    app: ASGIApp, port: int, loop: asyncio.AbstractEventLoop, max_body: int = MAX_BODY
) -> http.server.ThreadingHTTPServer:
    """An ASGI application on the standard library's threaded server: each
    request handed to `app` on `loop`, and its answer written back. A body
    over `max_body` bytes, by its Content-Length, is refused unread."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def _refuse(self, status: int, said: str, unread: int = 0) -> None:
            # The body is not taken, so the connection carries no other
            # request after this answer; what is still arriving of it is
            # dropped, unkept, so the sender reads the answer.
            self.close_connection = True
            text = said.encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(text)))
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(text)
            self.wfile.flush()
            unread = min(unread, DISCARD)
            try:
                self.connection.settimeout(DISCARD_SECONDS)
                while unread > 0 and (dropped := self.rfile.read(min(unread, 65536))):
                    unread -= len(dropped)
            except OSError:
                pass

        def _handle(self) -> None:
            said = (self.headers.get("Content-Length") or "0").strip()
            if not said.isdigit():
                self._refuse(400, "This request's Content-Length is not a number of bytes.")
                return
            length = int(said)
            if length > max_body:
                self._refuse(413, TOO_LARGE, unread=length)
                return
            body = self.rfile.read(length) if length else b""
            path, _, query = self.path.partition("?")
            scope: Scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": self.command,
                "scheme": "http",
                "path": urllib.parse.unquote(path),
                "raw_path": path.encode("latin-1"),
                "query_string": query.encode("latin-1"),
                "root_path": "",
                "headers": [
                    (name.lower().encode("latin-1"), value.encode("latin-1"))
                    for name, value in self.headers.items()
                ],
                "client": self.client_address[:2],
                "server": cast(Any, self.server.server_address)[:2],
            }
            sent: list[Mapping[str, Any]] = []

            async def receive() -> dict[str, Any]:
                return {"type": "http.request", "body": body, "more_body": False}

            async def send(message: Any) -> None:
                sent.append(message)

            async def answer() -> None:
                await app(scope, receive, send)

            running = asyncio.run_coroutine_threadsafe(answer(), loop)
            try:
                running.result(timeout=REQUEST_SECONDS)
            except concurrent.futures.TimeoutError:
                running.cancel()
                log.error("%s %s took longer than %ss", self.command, path, REQUEST_SECONDS)
                sent = []
            except Exception:
                log.exception("%s %s failed", self.command, path)
                sent = []
            start = next((m for m in sent if m["type"] == "http.response.start"), None)
            if start is None:
                self.send_error(500, "The page failed; the plugin's log says why.")
                return
            self.send_response(start["status"])
            for name, value in start.get("headers", []):
                self.send_header(name.decode("latin-1"), value.decode("latin-1"))
            self.end_headers()
            if self.command == "HEAD":  # whatever answered it, the headers alone
                return
            for message in sent:
                if message["type"] == "http.response.body":
                    self.wfile.write(message.get("body", b""))

        do_GET = _handle  # noqa: N815 - the server's names
        do_HEAD = _handle  # noqa: N815
        do_POST = _handle  # noqa: N815

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
