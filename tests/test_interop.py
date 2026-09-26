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
from decimal import Decimal

import pytest

import meridian
from meridian import CallFailed

# A topic the custody role's grants hold. Named here rather than imported,
# because the point is that two implementations agree about these strings, and
# importing them from one side would be that side agreeing with itself.
RECORD_STATEMENT = "platform.street.command.record-statement"

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
    connected = await meridian.connect(address(), heartbeat=False)
    try:
        yield connected
    finally:
        await connected.leave("interop finished")


async def test_the_runtime_says_who_this_plugin_is(plugin) -> None:
    """Identity comes back from the sidecar's launch configuration.

    The SDK sent nothing but a schema version, so everything asserted here was
    decided by the deployment.
    """
    assert plugin.identity.roles == ("custody",)
    assert plugin.identity.instance_id
    assert plugin.identity.deployment_id
    assert RECORD_STATEMENT in plugin.grants.publish


async def test_the_same_statement_twice_is_recognised_not_duplicated(plugin) -> None:
    """Redelivery is a no-op, and the street store says so rather than staying silent.

    A row for an account reaches the street store only for an account somebody
    linked and may write through the plugin, which takes an administrator this
    suite has none of; meridian-core's `e2e-plugin-page` records one through
    the whole stack.
    """
    statement = {
        "source": "interop",
        "external_statement_id": f"interop-{uuid.uuid4()}",
        "as_of_date": "2026-09-12",
        "read_at_ns": NOW,
        "expected_rows": 1,
    }
    first = await plugin.record_holdings_statement(**statement)
    second = await plugin.record_holdings_statement(**statement)
    assert second.already_recorded
    assert second.statement_id == first.statement_id


async def test_an_unresolved_identifier_is_a_miss_not_an_error(plugin) -> None:
    """The instrument store answers, and a miss is an answer.

    Nothing is loaded into the instrument store here, so the interesting part
    is that the reply decodes and reports a reason rather than the call
    failing.
    """
    reply = await plugin.resolve_identifier(
        identifiers=[meridian.Identifier(scheme="isin", value="US0000000000")],
        as_of_ns=NOW,
    )
    assert not reply.found
    assert reply.miss_reason != meridian.MissReason.Value("MISS_REASON_UNSPECIFIED")


async def test_there_is_no_path_onto_the_bus_but_a_typed_operation(plugin) -> None:
    """decisions/013: the generic operations are gone from contract v2."""
    for generic in ("publish", "subscribe", "call"):
        assert not hasattr(plugin, generic), generic


async def test_a_required_setting_the_deployment_holds_nothing_for_is_named() -> None:
    """W4.7, against the real conductor, which holds no values here."""
    async with await meridian.connect(
        address(),
        heartbeat=False,
        settings=[meridian.Setting("api_key", required=True, secret=True)],
    ) as plugin:
        stream = plugin.settings()
        async with asyncio.timeout(10):
            first = await anext(stream)
        await stream.aclose()
    assert first.missing_required == ("api_key",)
    assert first.values == {}


async def test_the_account_scope_and_access_table_come_from_the_conductor(plugin) -> None:
    """W4.10 and W4.11: nobody holds access to this plugin here, so both are
    empty -- and answered, which is what crossing the bus as this plugin shows."""
    stream = plugin.account_scope()
    async with asyncio.timeout(10):
        scope = await anext(stream)
    await stream.aclose()
    assert scope == meridian.AccountScope()
    table = await plugin.access()
    assert list(table.user_groups) == []


async def test_the_scaffold_registers_with_a_real_sidecar() -> None:
    """What `meridian plugin new` writes, run the way its author runs it.

    The template in this repository is the scaffold the CLI copies, so the
    first plugin anybody makes is this one. It is installed from the SDK's
    wheel beside it, started as its console script, and must register, say the
    roles and grants the sidecar launched it with, and stop cleanly when told.
    """
    import asyncio
    import signal

    started = await asyncio.create_subprocess_exec(
        "reference-plugin",
        env={**os.environ, "MERIDIAN_SIDECAR_ADDRESS": address()},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    assert started.stdout is not None
    said: list[str] = []

    async def until(text: str) -> None:
        while not any(text in line for line in said):
            line = await started.stdout.readline()  # type: ignore[union-attr]
            if not line:
                raise AssertionError(f"the plugin exited before saying {text!r}: {said}")
            said.append(line.decode().rstrip())

    try:
        await asyncio.wait_for(until("serving its page"), timeout=20)
        page = await asyncio.to_thread(visit_the_scaffolds_page)
    finally:
        started.send_signal(signal.SIGTERM)
        await asyncio.wait_for(until("stopping"), timeout=10)
        code = await asyncio.wait_for(started.wait(), timeout=10)

    assert page["without a caller"] == 401
    assert page["as Ada"][0] == 200 and "Ada Park" in page["as Ada"][1]
    # The page's one write goes to the sidecar for her; the sidecar holds no
    # key that signed this assertion, so it refuses, and the page says so.
    assert "Refused" in page["writing for Ada"], page["writing for Ada"]

    registered = next(line for line in said if "registered as" in line)
    assert "roles custody" in registered, said
    assert RECORD_STATEMENT in next(line for line in said if "may publish" in line), said
    assert code == 0, said


def visit_the_scaffolds_page() -> dict[str, object]:
    """The scaffold's page, asked as its sidecar's front door would ask it --
    this suite shares the sidecar's network namespace -- with an assertion
    no dashboard signed."""
    import base64
    import urllib.error
    import urllib.request

    from meridian.v1 import sidecar_pb2

    claims = sidecar_pb2.CallerClaims(subject="local|ada", display_name="Ada Park")
    assertion = sidecar_pb2.CallerAssertion(
        claims=claims.SerializeToString(), signature=b"not-the-dashboards", key_id="nobody"
    )
    header = base64.urlsafe_b64encode(assertion.SerializeToString()).decode().rstrip("=")

    def ask(method: str, path: str, caller: str | None) -> tuple[int, str]:
        request = urllib.request.Request(
            f"http://127.0.0.1:8000{path}",
            method=method,
            data=b"" if method == "POST" else None,
        )
        if caller:
            request.add_header("Meridian-Caller", caller)
        try:
            with urllib.request.urlopen(request, timeout=20) as answer:
                return answer.status, answer.read().decode()
        except urllib.error.HTTPError as refused:
            return refused.code, refused.read().decode()

    return {
        "without a caller": ask("GET", "/", None)[0],
        "as Ada": ask("GET", "/", header),
        "writing for Ada": ask("POST", "/statement", header)[1],
    }


# ── The typed operations (spec/typed-sidecar-operations) ────────────────────


async def test_a_holding_for_an_unlinked_external_account_is_refused_as_such(plugin) -> None:
    """The sidecar asks the conductor for this plugin's links, as this plugin.

    Nobody has linked this external account, so the row is refused naming
    that -- which it can only say having reached the conductor as the right
    instance: asked as anything else, the answer would hold no links at all
    and the refusal would read the same, which is why the account is unique.
    """
    opened = await plugin.record_holdings_statement(
        source="interop",
        external_statement_id=f"typed-{uuid.uuid4()}",
        as_of_date="2026-09-26",
        read_at_ns=NOW,
        expected_rows=1,
    )
    with pytest.raises(CallFailed) as refused:
        await plugin.record_holding(
            statement_id=opened.statement_id,
            instrument_id="INS-interop-1",
            quantity=Decimal("12.5"),
            market_value=Decimal("2812.5"),
            currency="USD",
            external_account_id=f"unlinked-{uuid.uuid4().hex[:8]}",
        )
    assert refused.value.kind == "refused"
    assert "not linked" in refused.value.detail


async def test_a_miss_is_reported_by_its_typed_operation(plugin) -> None:
    published = await plugin.report_missing_instrument(
        source="interop",
        asset_class="equity",
        identifiers=[meridian.Identifier(scheme="symbol", value="ZZZZ", source="interop")],
        as_of_ns=NOW,
        observed_at_ns=NOW,
    )
    assert published.message_id
