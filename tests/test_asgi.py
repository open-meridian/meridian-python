"""The caller middleware, driven as an ASGI server would drive it."""

from __future__ import annotations

import base64
from typing import Any

from meridian.asgi import CallerMiddleware
from meridian.v1 import sidecar_pb2


def header_for(subject: str) -> bytes:
    claims = sidecar_pb2.CallerClaims(subject=subject, display_name="Ada Park")
    assertion = sidecar_pb2.CallerAssertion(claims=claims.SerializeToString(), key_id="k")
    return base64.urlsafe_b64encode(assertion.SerializeToString()).rstrip(b"=")


async def run(headers: list[tuple[bytes, bytes]]) -> tuple[list[dict[str, Any]], list[Any]]:
    seen: list[Any] = []

    async def app(scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        seen.append(scope["state"]["caller"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b""}

    scope = {"type": "http", "headers": headers}
    await CallerMiddleware(app)(scope, receive, send)
    return sent, seen


async def test_the_caller_is_on_the_request_for_the_handler() -> None:
    sent, seen = await run([(b"meridian-caller", header_for("local|ada"))])
    assert sent[0]["status"] == 200
    assert seen[0].subject == "local|ada" and seen[0].display_name == "Ada Park"


async def test_a_request_that_did_not_come_through_a_sidecar_is_refused() -> None:
    for headers in (
        [],
        [(b"meridian-caller", header_for("a")), (b"meridian-caller", header_for("b"))],
        [(b"meridian-caller", b"not base64 at all!")],
    ):
        sent, seen = await run(headers)
        assert sent[0]["status"] == 401, headers
        assert not seen, "the handler ran for nobody"
