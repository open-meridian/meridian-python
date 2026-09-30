"""The plugin's page, built on the kit the dashboard serves beside it."""

from __future__ import annotations

import asyncio
import html
import http.server
import threading
import time
import uuid
from typing import Any

import meridian

from .access import files_statements, granted_anything, may_act, readable

TITLE = "Desk"
KIT = "/.meridian/ui/0.1.0/"


def render(caller: meridian.Caller, notice: str = "") -> str:
    rows = "".join(
        f"<tr><td><code>{html.escape(account)}</code></td>"
        f"<td>{'read and write' if may_act(caller, account) else 'read'}</td></tr>"
        for account in sorted(readable(caller))
    )
    if not granted_anything(caller):
        rows = '<tr><td colspan="2">Nothing is granted to you here.</td></tr>'
    said = f'<div class="notice good" role="status">{html.escape(notice)}</div>' if notice else ""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{TITLE}</title>"
        f'<link rel="stylesheet" href="{KIT}meridian.css">'
        f'<script src="{KIT}meridian.js"></script>'
        '</head><body><main class="page">'
        f"<h1>{TITLE}</h1>"
        f"<p>Signed in as <strong>{html.escape(caller.display_name)}</strong>.</p>"
        f"{said}"
        '<section class="panel"><table>'
        "<thead><tr><th>Account</th><th>You may</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></section>"
        "</main></body></html>"
    )


def serve(plugin: meridian.Plugin, loop: asyncio.AbstractEventLoop, port: int) -> Any:
    """The page on 127.0.0.1:`port`, in a thread, for the sidecar to forward to."""

    class Page(http.server.BaseHTTPRequestHandler):
        def _caller(self) -> meridian.Caller | None:
            presented = self.headers.get_all("Meridian-Caller") or []
            if len(presented) != 1:
                self._send(401, "Open this page from the dashboard.")
                return None
            return meridian.Caller.from_header(presented[0])

        def _send(self, status: int, body: str) -> None:
            data = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            caller = self._caller()
            if caller is not None:
                self._send(200, render(caller))

        def do_POST(self) -> None:  # noqa: N802
            caller = self._caller()
            if caller is None:
                return
            if not files_statements(caller):
                self._send(403, render(caller, "Only the statements desk files statements."))
                return
            opening = plugin.record_holdings_statement(
                source="desk",
                external_statement_id=f"desk-{uuid.uuid4()}",
                as_of_date=time.strftime("%Y-%m-%d", time.gmtime()),
                read_at_ns=time.time_ns(),
                expected_rows=0,
                acting_for=caller.header,
            )
            opened = asyncio.run_coroutine_threadsafe(opening, loop).result(timeout=15)
            self._send(200, render(caller, f"Opened statement {opened.statement_id}."))

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Page)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
