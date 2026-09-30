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
import logging
import os
import secrets
import threading
import urllib.parse
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import jinja2
from markupsafe import Markup

from .asgi import ASGIApp, CallerMiddleware, Receive, Scope, Send
from .client import BUTTONS, Caller, Page, _levels
from .v1 import sidecar_pb2

if TYPE_CHECKING:
    from .client import Plugin

log = logging.getLogger("meridian.pages")

#: The kit the base template links, from the path the dashboard serves it at on
#: the plugin's own host. A dashboard answers any 0.x with the newest 0.x it
#: carries; this is the version the base template was built against.
KIT = "0.7.0"

#: The form field, and the header, a request that changes something carries its
#: token in.
CSRF_FIELD = "csrf"
CSRF_HEADER = "x-csrf-token"

#: The methods that change nothing, and so carry no token.
SAFE_METHODS = frozenset({"GET", "HEAD"})

#: How long the standard library's server waits for a view before answering 500.
REQUEST_SECONDS = 60.0

#: A level's ruled spelling, as a template reads it in `level`.
SPELLING: dict[int, str] = {
    sidecar_pb2.ACCESS_LEVEL_ADMIN: "admin",
    sidecar_pb2.ACCESS_LEVEL_WRITE: "write",
    sidecar_pb2.ACCESS_LEVEL_READ: "read",
}


# Markup is markupsafe's, re-exported: text that is HTML already, which a
# template puts in as it is, where it escapes every other value.
__all__ = ["KIT", "Markup", "Pages", "Request", "Response"]


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


View = Callable[[Request], Response | str | Awaitable[Response | str]]
Guarded = Callable[[Request], Awaitable[Response]]


@dataclass(frozen=True)
class _Route:
    path: str
    levels: tuple[int, ...]
    guarded: Guarded
    # The tab, for a page; none for a route.
    page: Page | None


@dataclass(frozen=True)
class _Serving:
    request: Request
    route: _Route


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
    ) -> None:
        self.title = title
        self.templates = None if templates is None else Path(templates)
        if self.templates is not None and not self.templates.is_dir():
            raise FileNotFoundError(f"the pages' templates are not at {self.templates}")
        self.kit = f"/.meridian/ui/{kit}/"
        self._routes: dict[tuple[str, str], _Route] = {}
        self._pages: list[Page] = []
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
        methods: Iterable[str] = ("GET",),
    ) -> Callable[[View], Guarded]:
        """A tab: shown under the home's button for each of `levels`, in the
        order declared, and served only in a session at one of them."""
        levelled = _levels(levels, f"page {title!r}")
        page = Page(path, title, levels=levelled)
        page._declared()  # a path without its slash, or no level, refused now
        return self._add(path, levelled, methods, page)

    def route(
        self,
        path: str,
        *,
        levels: Sequence[str | int] | str | int,
        methods: Iterable[str] = ("GET",),
    ) -> Callable[[View], Guarded]:
        """An endpoint that is not a tab -- a form's action, a page's data --
        served only in a session at one of `levels`."""
        levelled = _levels(levels, f"route {path!r}")
        if not path.startswith("/"):
            raise ValueError(f"route {path!r} does not begin with /")
        if not levelled:
            raise ValueError(f"route {path!r} names no level: admin, write or read")
        return self._add(path, levelled, methods, None)

    def _add(
        self, path: str, levels: tuple[int, ...], methods: Iterable[str], page: Page | None
    ) -> Callable[[View], Guarded]:
        verbs = tuple(dict.fromkeys(method.upper() for method in methods))
        for verb in verbs:
            if (path, verb) in self._routes:
                raise ValueError(f"{verb} {path} is declared twice")

        def decorate(view: View) -> Guarded:
            @functools.wraps(view)
            async def guarded(request: Request) -> Response:
                if request.caller.level not in levels:
                    return _refusal(path, levels, request.caller.level)
                request = dataclasses.replace(
                    request, csrf_token=self.csrf_token(request.caller)
                )
                if request.method.upper() not in SAFE_METHODS and not _presented(request):
                    return Response(
                        "This form has expired or did not come from this plugin's page. "
                        "Reload the page and try again.",
                        403,
                        "text/plain; charset=utf-8",
                    )
                serving = _serving.set(_Serving(request, route))
                try:
                    answer = view(request)
                    if inspect.isawaitable(answer):
                        answer = await answer
                finally:
                    _serving.reset(serving)
                if isinstance(answer, str):
                    return Response(answer)
                if not isinstance(answer, Response):
                    raise TypeError(
                        f"the view at {path} answered a {type(answer).__name__}; "
                        "a view answers a str, the page, or a Response"
                    )
                return answer

            route = _Route(path, levels, guarded, page)
            for verb in verbs:
                self._routes[(path, verb)] = route
            if page is not None:
                self._pages.append(page)
            return guarded

        return decorate

    def csrf_token(self, caller: Caller) -> str:
        """The token a request from this person, in a session at this level,
        carries back when it changes something."""
        said = f"{caller.subject}\0{caller.level}".encode()
        return hmac.new(self._secret, said, hashlib.sha256).hexdigest()

    @property
    def declared(self) -> tuple[Page, ...]:
        """The tabs, in the order declared: what registration sends."""
        return tuple(self._pages)

    # ── Serving ──────────────────────────────────────────────────────────

    async def dispatch(self, request: Request) -> Response:
        """The view declared at the request's path and method, if the
        session's level is one it serves: 404 for no such path, 405 for a
        method it does not take, 403 for a level it does not serve."""
        route = self._routes.get((request.path, request.method.upper()))
        if route is not None:
            return await route.guarded(request)
        taken = sorted(verb for path, verb in self._routes if path == request.path)
        if taken:
            return Response(
                f"{request.path} takes {', '.join(taken)}.",
                405,
                "text/plain; charset=utf-8",
                (("allow", ", ".join(taken)),),
            )
        return Response("No such page.", 404, "text/plain; charset=utf-8")

    def app(self, plugin: Plugin | None = None) -> ASGIApp:
        """The pages as an ASGI application, serving `plugin`: the caller read
        from the header its sidecar forwarded (401 without one), then
        dispatched. A view that raises is logged and answered 500."""

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
            body = b""
            while True:
                message = await receive()
                body += message.get("body", b"")
                if not message.get("more_body"):
                    break
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
        self, plugin: Plugin, port: int, *, loop: asyncio.AbstractEventLoop | None = None
    ) -> http.server.ThreadingHTTPServer:
        """Serve the pages on 127.0.0.1:`port`, with the standard library's
        server, in a thread of its own; each view runs on `loop`, the running
        one by default, where the plugin's operations are. The returned
        server's `shutdown()` stops it."""
        return _serve(self.app(plugin), port, loop or asyncio.get_running_loop())

    # ── Rendering ────────────────────────────────────────────────────────

    def render(self, template: str, /, **context: Any) -> str:
        """`template`, from `templates`, rendered with `context`, `caller` and
        `level` (admin, write or read); a page's template extends
        `meridian/base.html`. Called from a view, while it serves a request."""
        serving = _current()
        page, at = serving.route.page, serving.request.path
        caller = serving.request.caller
        named = page.title if page is not None else ""
        base = {
            "kit": self.kit,
            "heading": self.title or named,
            "title": " · ".join(part for part in (named, self.title) if part),
            "tabs": [
                {"path": each.path, "title": each.title, "current": each.path == at}
                for each in self._pages
                if caller.level in each.levels
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


def _presented(request: Request) -> bool:
    """Whether the request carries its token back, in its form or a header."""
    presented = request.form.get(CSRF_FIELD) or request.headers.get(CSRF_HEADER, "")
    return bool(presented) and hmac.compare_digest(
        presented.encode(), request.csrf_token.encode()
    )


def _current() -> _Serving:
    try:
        return _serving.get()
    except LookupError:
        raise RuntimeError("render is called from a view, while it serves a request") from None


def _refusal(path: str, levels: tuple[int, ...], level: int) -> Response:
    served = " and ".join(BUTTONS[each] for each in levels)
    if level == sidecar_pb2.ACCESS_LEVEL_UNSPECIFIED:
        said = "This session was opened at no level, and holds nothing here."
    elif level in BUTTONS:
        said = f"{path} is not served under {BUTTONS[level]}; it is for {served}."
    else:
        said = f"{path} is not served at level {level}; it is for {served}."
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
    await send(
        {
            "type": "http.response.start",
            "status": response.status,
            "headers": [
                (b"content-type", response.content_type.encode("latin-1")),
                (b"content-length", str(len(body)).encode()),
                *(
                    (name.encode("latin-1"), value.encode("latin-1"))
                    for name, value in response.headers
                ),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _serve(
    app: ASGIApp, port: int, loop: asyncio.AbstractEventLoop
) -> http.server.ThreadingHTTPServer:
    """An ASGI application on the standard library's threaded server: each
    request handed to `app` on `loop`, and its answer written back."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def _handle(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
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
            for message in sent:
                if message["type"] == "http.response.body":
                    self.wfile.write(message.get("body", b""))

        do_GET = _handle  # noqa: N815 - the server's names
        do_POST = _handle  # noqa: N815

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
