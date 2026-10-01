"""A plugin's pages in its own tests, asked as its sidecar would forward them.

    from meridian.testing import PageClient

    client = PageClient(pages, plugin=sidecar, read={"ACC-1"}, write={"ACC-1"})
    assert client.get("/", "write").status == 200
    client.assert_no_account_data("AAPL", "125", "12,500.00")  # what ACC-1 holds

Each request carries a `Meridian-Caller` header for a session at one level,
its accounts cut to that level as the dashboard cuts them (W6.9): none under
`admin` (Manage), the read and write sets under `write` (Open), the read set
alone under `read` (View); `deployment_admin=True` makes the person a
deployment admin. `every_page` renders each declared page under each of the
three; `assert_no_account_data` fails when a page at `admin` shows any of the
account data the test names, since a Manage session sees no account's data.
What the plugin holds for an account -- a synced statement's holdings,
quantities, values and balances, say -- nothing technical keeps off a page,
so the plugin's tests do. An account's identity is not its data: a Manage
page may list every account of the deployment by name as a link target.

`heartbeat` is the heartbeat a plugin's sidecar receives, with the figures
it reports on its Summary (W4.5), checked as the SDK checks them before
sending: a test of the figures a plugin computes asserts on it, or on the
refusal it raises.

`post` carries the person's CSRF token back, as the page's form would;
`request` sends only what it is given, for a test that a request without
one, or with somebody else's, is refused. A view raising fails the test with
its traceback. Synchronous, for a plain
pytest test: not from inside a running event loop.
"""

from __future__ import annotations

import asyncio
import base64
import urllib.parse
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, cast

from markupsafe import escape

from .client import Caller, Page, _levels
from .figures import Figure, wire
from .pages import CSRF_FIELD, SPELLING, Pages, Request, Response
from .v1 import sidecar_pb2

#: The three levels, as the home's Manage, Open and View open a session.
LEVELS = ("admin", "write", "read")


def caller_header(
    level: str | int = "",
    *,
    read: Iterable[str] = (),
    write: Iterable[str] = (),
    subject: str = "local|ada",
    display_name: str = "Ada Park",
    deployment_admin: bool = False,
) -> str:
    """The `Meridian-Caller` header a sidecar forwards for a session at
    `level`, with the accounts cut to it: `read` and `write` are those the
    person may read and write through the plugin (write included in read).
    No level is a session that holds nothing. Unsigned: only a plugin's own
    tests read it, never a sidecar."""
    at = _levels(level, "the session")[0] if level else sidecar_pb2.ACCESS_LEVEL_UNSPECIFIED
    writes = sorted(set(write))
    reads = sorted(set(read) | set(writes))
    if at == sidecar_pb2.ACCESS_LEVEL_ADMIN:
        reads, writes = [], []
    elif at == sidecar_pb2.ACCESS_LEVEL_READ:
        writes = []
    claims = sidecar_pb2.CallerClaims(
        subject=subject,
        display_name=display_name,
        level=at,  # type: ignore[arg-type]
        read_account_ids=reads,
        write_account_ids=writes,
        deployment_admin=deployment_admin,
    )
    assertion = sidecar_pb2.CallerAssertion(claims=claims.SerializeToString())
    return base64.urlsafe_b64encode(assertion.SerializeToString()).decode().rstrip("=")


def heartbeat(
    *, healthy: bool = True, detail: str = "", figures: Iterable[Figure] = ()
) -> sidecar_pb2.HeartbeatRequest:
    """The heartbeat the sidecar receives from a plugin reporting these: its
    figures as the wire carries them, in the plugin's order. Raises as
    `plugin.figures = figures` does, before anything would be sent, for a
    figure past a bound (ValueError, in the sidecar's words) or of no kind
    a figure is (TypeError)."""
    return sidecar_pb2.HeartbeatRequest(healthy=healthy, detail=detail, figures=wire(figures))


@dataclass(frozen=True)
class Rendered:
    """One declared page, asked in a session at one level, and its answer."""

    page: Page
    level: str
    response: Response


class PageClient:
    """The plugin's pages, asked in-process as its sidecar would ask them.

    `plugin` is what a view reaches as `request.plugin`: a stand-in for the
    sidecar whose operations answer here. `read` and `write` are the accounts
    the person asking may read and write, cut to each session's level;
    `deployment_admin`, whether they are a deployment admin, which every
    request this client sends says."""

    def __init__(
        self,
        pages: Pages,
        plugin: object = None,
        *,
        read: Iterable[str] = (),
        write: Iterable[str] = (),
        subject: str = "local|ada",
        display_name: str = "Ada Park",
        deployment_admin: bool = False,
    ) -> None:
        self.pages = pages
        self.plugin = plugin
        self.read = frozenset(read)
        self.write = frozenset(write)
        self.subject = subject
        self.display_name = display_name
        self.deployment_admin = deployment_admin

    def request(
        self,
        method: str,
        path: str,
        level: str | int,
        *,
        form: Mapping[str, str] | None = None,
        query: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        """The request as given: no token is added."""
        request = Request(
            method=method.upper(),
            path=path,
            caller=self.caller(level),
            plugin=cast(Any, self.plugin),
            query=dict(query or {}),
            form=dict(form or {}),
            body=urllib.parse.urlencode(form or {}).encode(),
            headers={name.lower(): value for name, value in (headers or {}).items()},
        )
        return asyncio.run(self.pages.dispatch(request))

    def caller(self, level: str | int, *, deployment_admin: bool | None = None) -> Caller:
        """This client's person, in a session at `level`: a deployment admin
        as the client was made, unless `deployment_admin` says."""
        return Caller.from_header(
            caller_header(
                level,
                read=self.read,
                write=self.write,
                subject=self.subject,
                display_name=self.display_name,
                deployment_admin=(
                    self.deployment_admin if deployment_admin is None else deployment_admin
                ),
            )
        )

    def get(self, path: str, level: str | int, **query: str) -> Response:
        return self.request("GET", path, level, query=query)

    def post(
        self,
        path: str,
        level: str | int,
        form: Mapping[str, str] | None = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        """A form posted from the plugin's page: its CSRF token carried back,
        unless `form` gives one of its own."""
        token = self.pages.csrf_token(self.caller(level))
        return self.request(
            "POST", path, level, form={CSRF_FIELD: token, **(form or {})}, headers=headers
        )

    def every_page(self) -> list[Rendered]:
        """Each declared page, in order, under Manage, Open and View: 200
        where its levels include the session's, 403 where they do not."""
        return [
            Rendered(page, level, self.get(page.path, level))
            for page in self.pages.declared
            for level in LEVELS
        ]

    def assert_no_account_data(self, *held: str) -> None:
        """Under Manage, every page at `admin` answers 200 and every other
        page 403, and no page at `admin` shows any of `held`: each string,
        as given or as a template escapes it, anywhere in the page's text.
        Raises AssertionError naming the page and what it showed.

        `held` is the account data the test put where the plugin reads it:
        holdings, quantities, values, balances, a statement's rows. Name at
        least one. An account's identity -- its ID, name, custodian, type,
        owner and note -- is not looked for: a Manage page may list every
        account of the deployment as a link target, as the accounts read
        answers them, identities and never holdings. Each string named is
        looked for all the same, an identity too."""
        named = {text for text in held if text}
        if not named:
            raise ValueError(
                "assert_no_account_data names no account data to look for: pass the "
                "holdings, figures and rows the test gave the plugin"
            )
        shown = {text: (text, str(escape(text))) for text in named}
        for rendered in self.every_page():
            if rendered.level != SPELLING[sidecar_pb2.ACCESS_LEVEL_ADMIN]:
                continue
            if sidecar_pb2.ACCESS_LEVEL_ADMIN not in rendered.page.levels:
                if rendered.response.status != 403:
                    raise AssertionError(
                        f"{rendered.page.path} answered {rendered.response.status} "
                        "under Manage, which it does not serve"
                    )
                continue
            if rendered.response.status != 200:
                raise AssertionError(
                    f"{rendered.page.path} answered {rendered.response.status} under Manage"
                )
            page = rendered.response.text
            found = sorted(t for t, forms in shown.items() if any(f in page for f in forms))
            if found:
                raise AssertionError(
                    f"{rendered.page.path} shows account data under Manage: {', '.join(found)}"
                )
