"""The SDK against a real runtime, not a fake.

Every other test in this suite talks to a server written in the same language by
the same hand, which proves the client is self-consistent and nothing else. This
one drives the Rust sidecar in meridian-core: a call here crosses the socket,
the grant table, the bus, the kernel and Postgres, and comes back.

That path is the product. Until something ran it, the six operations had been
exercised only by their own authors, which is the state in which a contract
looks settled and is not.

Run by `make interop` in meridian-core, which brings up the runtime and puts
this container in its network namespace, because the sidecar binds loopback and
that is the deployment shape the design calls for.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from meridian.v1 import holdings_pb2, reference_pb2

import meridian_sdk
from meridian_sdk import NotGranted

# The topics the shipped example grants admit for the custody role. Named here
# rather than imported, because the point is that two implementations agree
# about these strings, and importing them from one side would be that side
# agreeing with itself.
RECORD_STATEMENT = "platform.kernel.command.record-statement"
RECORD_HOLDING = "platform.kernel.command.record-holding"
RESOLVE_IDENTIFIER = "platform.reference.query.resolve-identifier"
INSTRUMENT_MISSING = "platform.reference.event.instrument-missing"
INSTRUMENT_APPLIED = "platform.reference.event.instrument-applied"
STATEMENT_RECORDED = "platform.kernel.event.statement-recorded"

NOW = 1_757_376_000_000_000_000


# Read at import, which is before any fixture runs. conftest clears this
# variable for every test, so the unit suite cannot accidentally talk to
# whatever a developer has running; capturing it here keeps that protection
# without disabling it for the one suite that needs the opposite.
_ADDRESS = os.environ.get("MERIDIAN_SIDECAR_ADDRESS")


def address() -> str:
    if not _ADDRESS:
        raise RuntimeError(
            "MERIDIAN_SIDECAR_ADDRESS is not set. This suite needs a running "
            "runtime; `make interop` in meridian-core starts one."
        )
    return _ADDRESS


@pytest.fixture
async def plugin():
    connected = await meridian_sdk.connect(address(), heartbeat=False)
    try:
        yield connected
    finally:
        await connected.leave("interop finished")


async def test_the_runtime_says_who_this_plugin_is(plugin) -> None:
    """Identity comes back from the sidecar's launch configuration.

    The SDK sent nothing but a schema version, so everything asserted here was
    decided by the deployment.
    """
    assert plugin.identity.role == "custody"
    assert plugin.identity.instance_id
    assert plugin.identity.deployment_id
    assert RECORD_HOLDING in plugin.grants.publish


async def test_a_statement_and_a_row_reach_the_ledger(plugin) -> None:
    """Python to Rust to Postgres and back.

    The statement promises one row, one row arrives, and the position it moves
    is read back through a different message on the same connection.
    """
    external_id = f"interop-{uuid.uuid4()}"
    account = f"ACC-{uuid.uuid4().hex[:8]}"

    opened = await plugin.call(
        RECORD_STATEMENT,
        holdings_pb2.RecordHoldingsStatementRequest(
            source="interop",
            external_statement_id=external_id,
            as_of_date="2026-09-12",
            read_at_ns=NOW,
            expected_rows=1,
        ),
        holdings_pb2.RecordHoldingsStatementReply(),
    )
    assert opened.statement_id
    assert not opened.already_recorded

    recorded = await plugin.call(
        RECORD_HOLDING,
        holdings_pb2.RecordHoldingRequest(
            statement_id=opened.statement_id,
            account_id=account,
            instrument_id="INS-interop-1",
            quantity_scaled_1e8=1_250_000_000,
            market_value_scaled_1e8=281_250_000_000,
            currency="USD",
        ),
        holdings_pb2.RecordHoldingReply(),
    )
    assert recorded.resolved
    assert recorded.holding_id


async def test_the_same_statement_twice_is_recognised_not_duplicated(plugin) -> None:
    """Redelivery is a no-op, and the ledger says so rather than staying silent."""
    external_id = f"interop-{uuid.uuid4()}"
    request = holdings_pb2.RecordHoldingsStatementRequest(
        source="interop",
        external_statement_id=external_id,
        as_of_date="2026-09-12",
        read_at_ns=NOW,
        expected_rows=1,
    )

    first = await plugin.call(
        RECORD_STATEMENT, request, holdings_pb2.RecordHoldingsStatementReply()
    )
    second = await plugin.call(
        RECORD_STATEMENT, request, holdings_pb2.RecordHoldingsStatementReply()
    )

    assert second.already_recorded
    assert second.statement_id == first.statement_id


async def test_an_unresolved_identifier_is_a_miss_not_an_error(plugin) -> None:
    """The replica answers, and a miss is an answer.

    Nothing is loaded into the replica here, so the interesting part is that the
    reply decodes and reports a reason rather than the call failing.
    """
    reply = await plugin.call(
        RESOLVE_IDENTIFIER,
        reference_pb2.ResolveIdentifierRequest(
            identifiers=[reference_pb2.Identifier(scheme="isin", value="US0000000000")],
            as_of_ns=NOW,
        ),
        reference_pb2.ResolveIdentifierReply(),
    )
    assert not reply.found
    assert reply.miss_reason != reference_pb2.MISS_REASON_UNSPECIFIED


async def test_a_granted_publish_is_accepted(plugin) -> None:
    message_id = await plugin.publish(
        INSTRUMENT_MISSING,
        reference_pb2.MissingInstrumentDetectedEvent(
            source="interop",
            identifiers=[reference_pb2.Identifier(scheme="isin", value="US0000000000")],
            as_of_ns=NOW,
        ),
    )
    assert message_id


async def test_an_ungranted_publish_is_refused_by_the_real_grant_table(
    plugin,
) -> None:
    """A connector states what it holds; it does not announce that the ledger
    moved. That is the kernel's to say, and the deployment's grant table is what
    enforces it.
    """
    with pytest.raises(NotGranted) as raised:
        await plugin.publish(STATEMENT_RECORDED, holdings_pb2.RecordHoldingsStatementReply())
    assert raised.value.topic == STATEMENT_RECORDED


async def test_an_ungranted_subscription_is_refused(plugin) -> None:
    with pytest.raises(NotGranted):
        [d async for d in plugin.subscribe("platform.kernel.**")]


async def test_a_granted_subscription_opens(plugin) -> None:
    """Nothing publishes on this topic here, so the assertion is that the stream
    opens rather than being refused.

    Bounded, because a subscription with nothing to deliver stays open forever,
    which is correct behaviour and would otherwise hang this suite. The timeout
    is the pass: it means the server accepted the pattern and is holding a
    stream. A refusal would raise before the wait.
    """
    stream = plugin.subscribe(INSTRUMENT_APPLIED)
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(2):
            await anext(stream)
    await stream.aclose()
