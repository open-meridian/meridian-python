"""The client's half of the sidecar surface.

What is worth asserting here is not that a call reaches the server, which gRPC
already guarantees, but the three things this client decides: what it sends,
what it refuses to send, and how it translates a failure into something a plugin
author can act on.
"""

from __future__ import annotations

import asyncio

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import CallFailed, NotGranted, NotRegistered, Refused
from meridian.v1 import envelope_pb2, holdings_pb2, sidecar_pb2


def an_envelope(topic: str, payload: object = None) -> envelope_pb2.Envelope:
    body = payload or holdings_pb2.RecordHoldingRequest(account_id="ACC-1")
    return envelope_pb2.Envelope(
        meta=envelope_pb2.MessageMeta(
            message_id="msg-1",
            correlation_id="corr-1",
            publisher_instance_id="sidecar-custody-1",
            topic=topic,
            schema_version="v1",
            published_at_ns=1_757_376_000_000_000_000,
        ),
        payload_type=body.DESCRIPTOR.full_name,
        payload=body.SerializeToString(),
    )


async def test_registering_sends_no_identity(sidecar: tuple[FakeSidecar, str]) -> None:
    """The thing a plugin must not be able to do is the thing to assert.

    Instance, roles and tags moved to the sidecar's launch configuration, so
    there is no field here to fill in. A client that grew one back would be
    letting a plugin choose its own privileges.
    """
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    await plugin.leave()

    (sent,) = service.registered
    assert sent.schema_version == "v1"
    assert not sent.ListFields() or [f.name for f, _ in sent.ListFields()] == ["schema_version"]


async def test_identity_and_grants_come_back(sidecar: tuple[FakeSidecar, str]) -> None:
    """So a plugin can stop at startup when it is not what it expected to be."""
    service, address = sidecar
    service.roles = ("oms", "ems")
    service.tags = ("routing",)
    service.publish_grants = ("platform.street.query.list-custodial-positions",)

    plugin = await meridian.connect(address, heartbeat=False)
    try:
        assert plugin.identity.roles == ("oms", "ems")
        assert plugin.identity.instance_id == "custody-snaptrade-1"
        assert plugin.identity.tags == ("routing",)
        assert plugin.identity.deployment_id == "dep-local-1"
        assert plugin.grants.publish == ("platform.street.query.list-custodial-positions",)
    finally:
        await plugin.leave()


async def test_a_refusal_stops_the_plugin_and_says_why(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """Not retried. A refusal is a statement about configuration."""
    service, address = sidecar
    service.admitted = False
    service.refusal_reason = "access control not loaded"

    with pytest.raises(Refused) as raised:
        await meridian.connect(address, heartbeat=False)
    assert raised.value.reason == "access control not loaded"
    assert len(service.registered) == 1, "a refusal was retried"


async def test_publish_sends_the_payload_type_and_not_the_identity(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        row = holdings_pb2.RecordHoldingRequest(
            account_id="ACC-1", quantity_scaled_1e8=1_250_000_000
        )
        message_id = await plugin.publish(
            "platform.street.command.record-holding", row, correlation_id="corr-1"
        )
        assert message_id == "msg-1"
    finally:
        await plugin.leave()

    (sent,) = service.published
    assert sent.payload_type == "meridian.v1.RecordHoldingRequest"
    assert sent.correlation_id == "corr-1"
    # There is nowhere on this message to put a timestamp or a publisher, and
    # that is the design rather than an omission.
    assert "publisher" not in {f.name for f, _ in sent.ListFields()}


async def test_a_refused_publish_names_the_topic_and_the_missing_grant(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.publish_accepted = False
    service.publish_refusal = "no grant covers platform.street.command.record-holding"

    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(NotGranted) as raised:
            await plugin.publish(
                "platform.street.command.record-holding",
                holdings_pb2.RecordHoldingRequest(),
            )
    finally:
        await plugin.leave()

    assert raised.value.topic == "platform.street.command.record-holding"
    assert "no grant" in raised.value.reason


async def test_subscribe_yields_envelopes_with_the_sidecar_stamp(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.deliveries = [an_envelope("platform.reference.event.instrument-applied")]

    plugin = await meridian.connect(address, heartbeat=False)
    try:
        received = [d async for d in plugin.subscribe("platform.reference.event.*")]
    finally:
        await plugin.leave()

    (one,) = received
    assert one.topic == "platform.reference.event.instrument-applied"
    # Stamped by the sidecar, not by whoever published.
    assert one.meta.publisher_instance_id == "sidecar-custody-1"
    row = one.unpack(holdings_pb2.RecordHoldingRequest())
    assert row.account_id == "ACC-1"


async def test_unpacking_the_wrong_type_is_caught(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """Protobuf decodes mismatched bytes into an empty message rather than
    failing, so an unchecked unpack turns a bug into a plausible-looking blank.
    """
    service, address = sidecar
    service.deliveries = [an_envelope("platform.reference.event.instrument-applied")]

    plugin = await meridian.connect(address, heartbeat=False)
    try:
        (one,) = [d async for d in plugin.subscribe("platform.reference.event.*")]
        with pytest.raises(ValueError, match="RecordHoldingsStatementRequest"):
            one.unpack(holdings_pb2.RecordHoldingsStatementRequest())
    finally:
        await plugin.leave()


async def test_an_ungranted_subscription_is_refused_not_silently_empty(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.subscribe_status = grpc.StatusCode.PERMISSION_DENIED

    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(NotGranted):
            [d async for d in plugin.subscribe("platform.street.**")]
    finally:
        await plugin.leave()


async def test_call_returns_the_reply_parsed_into_the_caller_s_message(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    answer = holdings_pb2.RecordHoldingsStatementReply(statement_id="st-1")
    service.call_reply = sidecar_pb2.CallReply(
        ok=True,
        payload_type=answer.DESCRIPTOR.full_name,
        payload=answer.SerializeToString(),
    )

    plugin = await meridian.connect(address, heartbeat=False)
    try:
        reply = await plugin.call(
            "platform.street.command.record-statement",
            holdings_pb2.RecordHoldingsStatementRequest(expected_rows=1),
            holdings_pb2.RecordHoldingsStatementReply(),
            timeout_ms=1000,
        )
        assert reply.statement_id == "st-1"
    finally:
        await plugin.leave()

    (sent,) = service.called
    assert sent.timeout_ms == 1000


@pytest.mark.parametrize(
    ("failure", "kind"),
    [
        (sidecar_pb2.CALL_FAILURE_TIMEOUT, "timeout"),
        (sidecar_pb2.CALL_FAILURE_REFUSED, "refused"),
        (sidecar_pb2.CALL_FAILURE_NO_HANDLER, "no handler"),
        (sidecar_pb2.CALL_FAILURE_HANDLER_ERROR, "handler error"),
    ],
)
async def test_call_failures_stay_distinguishable(
    sidecar: tuple[FakeSidecar, str], failure: int, kind: str
) -> None:
    """The caller's next move differs for each: retry, stop, or report.

    Collapsing them is how a plugin ends up retrying something that will never
    succeed.
    """
    service, address = sidecar
    service.call_reply = sidecar_pb2.CallReply(
        ok=False, failure=failure, failure_detail="detail"
    )

    plugin = await meridian.connect(address, heartbeat=False)
    try:
        with pytest.raises(CallFailed) as raised:
            await plugin.call(
                "platform.street.query.list-custodial-positions",
                holdings_pb2.ListCustodialPositionsRequest(),
                holdings_pb2.ListCustodialPositionsReply(),
            )
    finally:
        await plugin.leave()

    assert raised.value.kind == kind
    assert raised.value.detail == "detail"


async def test_the_client_heartbeats_without_being_asked(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plugin author who has to remember this is one who will forget."""
    service, address = sidecar
    monkeypatch.setattr(meridian.plugin, "HEARTBEAT_SECONDS", 0.01)

    plugin = await meridian.connect(address)
    try:
        await asyncio.sleep(0.1)
        assert service.heartbeats, "no heartbeat was sent"
        assert all(beat.healthy for beat in service.heartbeats)
    finally:
        await plugin.leave()


async def test_leaving_says_why_and_closes_the_plugin(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """Saying so is what distinguishes a planned stop from a failure."""
    service, address = sidecar

    async with await meridian.connect(address, heartbeat=False) as plugin:
        pass

    (departure,) = service.left
    assert departure.reason == "stopping"
    with pytest.raises(NotRegistered):
        await plugin.publish(
            "platform.street.command.record-holding", holdings_pb2.RecordHoldingRequest()
        )


async def test_an_exception_leaves_with_the_reason(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar

    with pytest.raises(RuntimeError):
        async with await meridian.connect(address, heartbeat=False):
            raise RuntimeError("the brokerage went away")

    (departure,) = service.left
    assert departure.reason == "RuntimeError"
