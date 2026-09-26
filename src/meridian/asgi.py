"""The caller on every request to a plugin's page, for ASGI applications.

A plugin's page is reached only through its sidecar, which verified who is
asking and forwarded exactly one `Meridian-Caller` header saying so (W6.9).
This reads it once per request and puts a `Caller` where an ASGI framework
keeps per-request state, so a handler writes `request.state.caller` and
nothing else:

    app = CallerMiddleware(app)

It verifies nothing: only the sidecar can reach the page, and it removed
every other claim the request arrived with. A request with no caller did not
come through a sidecar, and is refused rather than served to nobody.

Pure ASGI, so any framework built on it will do, and none is required.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from .client import Caller

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

HEADER = b"meridian-caller"


class CallerMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        presented = [
            value for name, value in scope.get("headers", []) if name.lower() == HEADER
        ]
        if len(presented) != 1:
            await _refuse(send, "open this page from the dashboard")
            return
        try:
            caller = Caller.from_header(presented[0].decode("ascii"))
        except Exception:  # anything that does not read is not a caller
            await _refuse(send, "the caller header does not read")
            return
        scope.setdefault("state", {})["caller"] = caller
        await self.app(scope, receive, send)


async def _refuse(send: Send, why: str) -> None:
    body = why.encode()
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
