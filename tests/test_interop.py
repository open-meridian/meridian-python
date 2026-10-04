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
import base64
import os
import uuid
from decimal import Decimal

import grpc
import pytest

import meridian
import meridian.edge
import meridian.testing
from meridian import CallFailed, Money, NotLinked
from meridian.plugin.v1 import operations_pb2, operations_pb2_grpc
from meridian.v1 import sidecar_pb2, sidecar_pb2_grpc

# A topic the custody role's grants hold. Named here rather than imported,
# because the point is that two implementations agree about these strings, and
# importing them from one side would be that side agreeing with itself.
RECORD_STATEMENT = "platform.street.command.record-statement"

NOW = 1_757_376_000_000_000_000

# The external account core's `make interop` links to an account this plugin
# may write, as a deployment admin would through the dashboard: the only way a
# row reaches the street store, and the store is where these values are
# checked after the suite (the target reads them back from Postgres).
LINKED = "ext-interop"


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
        "external_account_id": LINKED,
        "as_of_date": "2026-09-12",
        "read_at_ns": NOW,
        "expected_rows": 1,
    }
    first = await plugin.record_holdings_statement(**statement)
    second = await plugin.record_holdings_statement(**statement)
    assert second.already_recorded
    assert second.statement_id == first.statement_id


async def test_a_set_nothing_matches_is_answered_with_a_minted_record(plugin) -> None:
    """The instrument store answers, and nothing matching is still an answer.

    Nothing is loaded into the instrument store here, so it mints the
    deployment's own record for the set (W3.7, contract v10: its LCL- ID is its
    key for life, not a placeholder), saying so; asked again, the same record
    matches and nothing is minted. What the source states is offered, never in
    force, so a resolve stating it is answered the same way.
    """
    asked = {
        "identifiers": [meridian.Identifier(scheme="isin", value="US0000000000")],
        "as_of_ns": NOW,
        "stated_asset_class": "equity",
        "stated_currency": "USD",
    }
    reply = await plugin.resolve_identifier(**asked)
    assert reply.found
    assert reply.instrument_id.startswith("LCL-")
    again = await plugin.resolve_identifier(**asked)
    assert again.instrument_id == reply.instrument_id
    assert not again.minted


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
    """W4.10 and W4.11: exactly what core's `make interop` configured -- one
    account, written through this plugin by one user group -- answered by the
    conductor, which is what crossing the bus as this plugin shows."""
    stream = plugin.account_scope()
    async with asyncio.timeout(10):
        scope = await anext(stream)
    await stream.aclose()
    held = frozenset({"ACC-INTEROP"})
    # And the link beside the scope it grants, named as the conductor holds
    # the account (e2e/interop/a-linked-account.sql): what a plugin just
    # started reads, rather than guessing from what it last recorded.
    assert scope == meridian.AccountScope(
        read=held,
        write=held,
        links=(meridian.LinkedExternalAccount(LINKED, "ACC-INTEROP", "Interop"),),
    )
    table = await plugin.access()
    assert [group.user_group_id for group in table.user_groups] == ["ug-interop"]


async def test_a_ticket_reaches_the_v13_sidecar_only_for_a_person_it_vouches_for(
    plugin,
) -> None:
    """W4.12, contract v13: the sidecar answers both calls, which a v12 one
    could not, and refuses the plugin as itself before anything else.

    This runtime has no dashboard, so no assertion here is the dashboard's:
    a filing for a person the sidecar cannot vouch for is refused as such,
    and core's `make e2e-tickets` files for one through the whole harness.
    The plugin as itself, which the SDK never sends (`for_caller` names
    somebody), is refused by the sidecar in the words its fixture pins.
    """
    claims = sidecar_pb2.CallerClaims(
        subject="local|ben", display_name="Ben Ito", level=sidecar_pb2.ACCESS_LEVEL_READ
    )
    unsigned = (
        base64.urlsafe_b64encode(
            sidecar_pb2.CallerAssertion(
                claims=claims.SerializeToString(), signature=b"not-the-dashboards"
            ).SerializeToString()
        )
        .decode()
        .rstrip("=")
    )
    with pytest.raises(CallFailed) as filed:
        await plugin.file_ticket(
            title="A ticket for a person nobody vouched for",
            kind="defect",
            idempotency_key="interop-unvouched",
            for_caller=unsigned,
        )
    assert filed.value.kind == "not vouched for", filed.value
    with pytest.raises(CallFailed) as read:
        await plugin.filed_tickets(for_caller=unsigned, idempotency_keys=["interop-unvouched"])
    assert read.value.kind == "not vouched for", read.value

    stub = sidecar_pb2_grpc.SidecarServiceStub(plugin._channel)
    with pytest.raises(grpc.aio.AioRpcError) as itself:
        await stub.FileTicket(
            sidecar_pb2.FileTicketRequest(
                title="Filed as the plugin itself",
                kind=sidecar_pb2.TICKET_KIND_DEFECT,
                concerns=sidecar_pb2.TicketSubject(kind="plugin"),
                idempotency_key="interop-itself",
            )
        )
    assert itself.value.code() is grpc.StatusCode.PERMISSION_DENIED
    assert "a plugin files a ticket only for a person it acts for" in (
        itself.value.details() or ""
    )
    with pytest.raises(grpc.aio.AioRpcError) as reading:
        await stub.FiledTickets(sidecar_pb2.ReadFiledTicketsRequest())
    assert reading.value.code() is grpc.StatusCode.PERMISSION_DENIED


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
    assert page["writing without the token"] == 403

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

    # A session opened by Open, at write: the level the scaffold's accounts
    # page and its one action serve (W6.9).
    claims = sidecar_pb2.CallerClaims(
        subject="local|ada", display_name="Ada Park", level=sidecar_pb2.ACCESS_LEVEL_WRITE
    )
    assertion = sidecar_pb2.CallerAssertion(
        claims=claims.SerializeToString(), signature=b"not-the-dashboards", key_id="nobody"
    )
    header = base64.urlsafe_b64encode(assertion.SerializeToString()).decode().rstrip("=")

    def ask(method: str, path: str, caller: str | None, body: bytes = b"") -> tuple[int, str]:
        request = urllib.request.Request(
            f"http://127.0.0.1:8000{path}",
            method=method,
            data=body if method == "POST" else None,
        )
        if caller:
            request.add_header("Meridian-Caller", caller)
        try:
            with urllib.request.urlopen(request, timeout=20) as answer:
                return answer.status, answer.read().decode()
        except urllib.error.HTTPError as refused:
            return refused.code, refused.read().decode()

    import re

    page = ask("GET", "/", header)
    # The page's form carries its CSRF token; a post without it is refused
    # before anything reaches the sidecar.
    found = re.search(r'name="csrf" value="([0-9a-f]+)"', page[1])
    token = found.group(1) if found else ""
    return {
        "without a caller": ask("GET", "/", None)[0],
        "as Ada": page,
        "writing for Ada": ask("POST", "/statement", header, f"csrf={token}".encode())[1],
        "writing without the token": ask("POST", "/statement", header)[0],
    }


# ── The typed operations (spec/typed-sidecar-operations) ────────────────────


async def test_a_holding_for_an_unlinked_external_account_is_refused_as_such(plugin) -> None:
    """The sidecar asks the conductor for this plugin's links, as this plugin.

    Nobody has linked this external account, so the row is refused with
    that code -- which it can only say having reached the conductor as the
    right instance: asked as anything else, the answer would hold no links at
    all and the refusal would read the same, which is why the account is
    unique. Told by the code the sidecar sends beside the status, not by its
    words (spec/typed-sidecar-operations, section 7).
    """
    opened = await plugin.record_holdings_statement(
        source="interop",
        external_statement_id=f"typed-{uuid.uuid4()}",
        external_account_id=LINKED,
        as_of_date="2026-09-26",
        read_at_ns=NOW,
        expected_rows=1,
    )
    with pytest.raises(NotLinked) as refused:
        await plugin.record_holding(
            statement_id=opened.statement_id,
            instrument_id="INS-interop-1",
            quantity=Decimal("12.5"),
            market_value=Money(Decimal("2812.5"), "USD"),
            external_account_id=f"unlinked-{uuid.uuid4().hex[:8]}",
        )
    assert refused.value.kind == "refused"

    # And a statement naming one, from contract v7, the same way (W2.2).
    with pytest.raises(NotLinked):
        await plugin.record_holdings_statement(
            source="interop",
            external_statement_id=f"typed-{uuid.uuid4()}",
            external_account_id=f"unlinked-{uuid.uuid4().hex[:8]}",
            as_of_date="2026-09-26",
            read_at_ns=NOW,
            expected_rows=1,
        )


async def test_a_miss_is_reported_by_its_typed_operation(plugin) -> None:
    published = await plugin.report_missing_instrument(
        source="interop",
        asset_class="equity",
        identifiers=[meridian.Identifier(scheme="symbol", value="ZZZZ", source="interop")],
        as_of_ns=NOW,
        observed_at_ns=NOW,
    )
    assert published.message_id


# ── A quantity carries its own scale (spec/quantities-carry-their-own-scale) ──

# Requirement 7's three: Alpaca's ninth decimal, a hundred billion units, and
# those at eighteen decimals. Each on an instrument of its own, so each is a
# position the street store keeps; core's `make interop` reads them back from
# its Postgres after this suite and compares them with these, character for
# character.
ROUND_TRIPS = {
    "INS-interop-ninth-decimal": Decimal("0.000000001"),
    "INS-interop-hundred-billion": Decimal("100000000000"),
    "INS-interop-eighteen-decimals": Decimal("100000000000.000000000000000001"),
}


async def test_the_smallest_and_largest_holdings_reach_the_street_store(plugin) -> None:
    """Through the SDK, the sidecar and the street store, for an account linked
    and writable. The street store says each row resolved; what it kept is read
    back by the target that ran this suite."""
    opened = await plugin.record_holdings_statement(
        source="interop",
        external_statement_id=f"scale-{uuid.uuid4()}",
        external_account_id=LINKED,
        as_of_date="2026-09-28",
        read_at_ns=NOW,
        expected_rows=len(ROUND_TRIPS),
    )
    for instrument_id, quantity in ROUND_TRIPS.items():
        recorded = await plugin.record_holding(
            statement_id=opened.statement_id,
            instrument_id=instrument_id,
            side=meridian.HoldingSide.HOLDING_SIDE_LONG,
            quantity=quantity,
            market_value=Money(Decimal("41230.50"), "USD"),
            external_account_id=LINKED,
        )
        assert recorded.resolved, instrument_id


async def test_a_float_is_refused_by_the_sdk_naming_the_field(plugin) -> None:
    with pytest.raises(TypeError, match="quantity is a Decimal or an int, not float"):
        await plugin.record_holding(
            statement_id="unused",
            quantity=0.1,  # type: ignore[arg-type]
            market_value=Money(Decimal(0), "USD"),
            external_account_id=LINKED,
        )


@pytest.mark.parametrize(
    ("quantity", "says"),
    [
        (Decimal("0.0000000000000000001"), "quantity has 19 decimal places"),
        (Decimal("1" * 39), "quantity has more than 38 digits"),
    ],
)
async def test_a_number_past_the_wire_is_refused_by_the_sdk(
    plugin, quantity: Decimal, says: str
) -> None:
    with pytest.raises(ValueError, match=says):
        await plugin.record_holding(
            statement_id="unused",
            quantity=quantity,
            market_value=Money(Decimal(0), "USD"),
            external_account_id=LINKED,
        )


async def test_a_nineteenth_decimal_sent_raw_is_refused_by_the_sidecar(plugin) -> None:
    """Past the SDK, as a plugin in another language that skipped the check
    would send it: the sidecar refuses it naming the field, before it asks
    about the link or reaches the street store."""
    async with grpc.aio.insecure_channel(address()) as channel:
        raw = operations_pb2_grpc.PluginOperationsStub(channel)
        with pytest.raises(grpc.aio.AioRpcError) as refused:
            await raw.RecordHolding(
                operations_pb2.RecordHoldingParams(
                    statement_id="unused",
                    instrument_id="INS-interop-raw",
                    quantity=operations_pb2.Decimal(low=1, scale=19),
                    market_value=operations_pb2.Money(
                        amount=operations_pb2.Decimal(), currency_code="USD"
                    ),
                    external_account_id=LINKED,
                ),
                timeout=10,
            )
    assert refused.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert (refused.value.details() or "").startswith("quantity has 19 decimal places")


async def test_the_figures_go_on_the_heartbeat_and_past_a_bound_are_refused_alike(
    plugin,
) -> None:
    """W4.5: the sidecar takes the figures the SDK sends, and refuses, in the
    words the SDK refuses with, a heartbeat sent past the SDK that breaks a
    bound, as a plugin in another language that skipped the check would."""
    await plugin.report(
        healthy=True,
        figures=[
            meridian.Figure("Connections", 3, state="warn", why="1 needs attention"),
            meridian.Figure("Accounts reached", 7),
            meridian.Figure("Rows refused", Decimal("0.5")),
            meridian.Figure("Key", "Commercial"),
        ],
    )
    nine = [meridian.Figure(f"F{i}", i) for i in range(9)]
    with pytest.raises(ValueError) as by_the_sdk:
        meridian.testing.heartbeat(figures=nine)
    async with grpc.aio.insecure_channel(address()) as channel:
        raw = sidecar_pb2_grpc.SidecarServiceStub(channel)
        with pytest.raises(grpc.aio.AioRpcError) as refused:
            await raw.Heartbeat(
                sidecar_pb2.HeartbeatRequest(
                    healthy=True,
                    figures=[
                        sidecar_pb2.PluginFigure(label=f"F{i}", count=i) for i in range(9)
                    ],
                ),
                timeout=10,
            )
    assert refused.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert refused.value.details() == str(by_the_sdk.value)
    assert str(by_the_sdk.value) == "9 figures; a plugin reports at most 8"
    # And a heartbeat within the bounds is taken again.
    await plugin.report(healthy=True, figures=[])


# ── The account side fits every venue (spec/the-account-side-fits-every-venue) ─

# Each venue's shape, from reference/broker-apis.md, recorded through the SDK,
# the sidecar and the street store into the one linked account, each on an
# instrument of its own. Core's `make interop` reads the positions, the rows
# whose currency was assumed and each statement's figures back from Postgres
# after this suite, and holds them to e2e/interop/positions.expected character
# for character: that is where "without loss" is checked, since nothing a
# plugin can ask reads a statement's figures back.
LONG = meridian.HoldingSide.HOLDING_SIDE_LONG
SHORT = meridian.HoldingSide.HOLDING_SIDE_SHORT


async def statement(
    plugin, source: str, rows: int, *, currency_assumed: bool = False, **figures: Money
) -> str:
    """The connector's snapshot of the linked account: its identifier made
    from the account and the time it read, as no venue has one of its own;
    naming the account it read, and its figures as the account's as a whole,
    the set with no segment (contract v7)."""
    opened = await plugin.record_holdings_statement(
        source=source,
        external_statement_id=f"{LINKED}/{NOW}/{uuid.uuid4().hex[:8]}",
        external_account_id=LINKED,
        as_of_date="2026-09-28",
        read_at_ns=NOW,
        expected_rows=rows,
        currency_assumed=currency_assumed,
        figures=[meridian.StatementFigures(segment="", **figures)] if figures else [],
    )
    return opened.statement_id


async def test_a_snaptrade_shaped_account_records_holdings_with_no_value_and_cash(
    plugin,
) -> None:
    """SnapTrade reports no market value, and cash per currency with its
    settled part: cash is a holding of the currency's cash instrument, which
    the security master holds under {scheme: iso4217}; this suite has none
    loaded, so the rows name the instruments it would have resolved to. A
    money-market fund SnapTrade counts in cash is also a position, recorded as
    reported and marked, so the book counts it once."""
    opened = await statement(
        plugin, "interop-snaptrade", 4, buying_power=Money(Decimal("25000.00"), "USD")
    )
    for instrument_id, quantity, settled in [
        ("INS-interop-snaptrade-vti", Decimal("12.5"), Decimal("10")),
        ("INS-interop-cash-usd", Decimal("1520.35"), Decimal("1020.35")),
        ("INS-interop-cash-cad", Decimal("250.00"), None),
    ]:
        recorded = await plugin.record_holding(
            statement_id=opened,
            instrument_id=instrument_id,
            side=LONG,
            quantity=quantity,
            settle_date_quantity=settled,
            external_account_id=LINKED,
        )
        assert recorded.resolved, instrument_id
    fund = await plugin.record_holding(
        statement_id=opened,
        instrument_id="INS-interop-snaptrade-spaxx",
        side=LONG,
        quantity=Decimal("500"),
        market_value=Money(Decimal("500.00"), "USD"),
        also_counted_in_cash=True,
        external_account_id=LINKED,
    )
    assert fund.resolved


async def test_cash_is_named_by_its_currency_under_iso4217(plugin) -> None:
    """The scheme reaches the instrument store like any global one; with no
    record of it here, it answers one the deployment mints (contract v10)."""
    reply = await plugin.resolve_identifier(
        identifiers=[meridian.Identifier(scheme="iso4217", value="USD")], as_of_ns=NOW
    )
    assert reply.found
    assert reply.instrument_id.startswith(("INS-", "LCL-"))


async def test_an_etrade_shaped_account_records_a_signed_short_and_its_figures(plugin) -> None:
    """E*TRADE signs a short negative and states no currency, for a position
    or a balance: the connector assumes USD and says so, and its margin
    figures are carried as reported."""
    opened = await statement(
        plugin,
        "interop-etrade",
        1,
        buying_power=Money(Decimal("41250.00"), "USD"),
        margin_requirement=Money(Decimal("18250.00"), "USD"),
        maintenance_excess=Money(Decimal("23000.00"), "USD"),
        currency_assumed=True,
    )
    recorded = await plugin.record_holding(
        statement_id=opened,
        instrument_id="INS-interop-etrade-tsla",
        side=SHORT,
        quantity=Decimal("-100"),
        market_value=Money(Decimal("-18250.00"), "USD"),
        currency_assumed=True,
        external_account_id=LINKED,
    )
    assert recorded.resolved


async def test_a_kalshi_shaped_no_position_is_a_short_row_of_its_one_contract(plugin) -> None:
    opened = await statement(plugin, "interop-kalshi", 1)
    recorded = await plugin.record_holding(
        statement_id=opened,
        instrument_id="INS-interop-kalshi-rain",
        side=SHORT,
        quantity=Decimal("-15.25"),
        external_account_id=LINKED,
    )
    assert recorded.resolved


async def test_a_schwab_shaped_long_and_short_of_one_instrument_are_two_rows(plugin) -> None:
    opened = await statement(plugin, "interop-schwab", 2)
    for side, quantity, value in [
        (LONG, Decimal("200"), Decimal("84000.00")),
        (SHORT, Decimal("-50"), Decimal("-21000.00")),
    ]:
        recorded = await plugin.record_holding(
            statement_id=opened,
            instrument_id="INS-interop-schwab-msft",
            side=side,
            quantity=quantity,
            settle_date_quantity=quantity,
            market_value=Money(value, "USD"),
            external_account_id=LINKED,
        )
        assert recorded.resolved


@pytest.mark.parametrize(
    ("side", "quantity", "says"),
    [
        (None, Decimal("1"), "neither long nor short"),
        (SHORT, Decimal("1"), "short side states a quantity of 1"),
        (LONG, Decimal("-1"), "long side states a quantity of -1"),
    ],
)
async def test_a_side_missing_or_contradicted_is_refused_by_the_street_store(
    plugin, side, quantity: Decimal, says: str
) -> None:
    opened = await statement(plugin, "interop", 1)
    with pytest.raises(CallFailed) as refused:
        await plugin.record_holding(
            statement_id=opened,
            instrument_id="INS-interop-refused",
            side=side,
            quantity=quantity,
            external_account_id=LINKED,
        )
    assert says in refused.value.detail


async def test_a_connector_reports_the_accounts_it_reaches_linked_or_not(plugin) -> None:
    """Published before anything is recorded, so an account nobody has linked
    is reported rather than refused."""
    published = await plugin.report_external_accounts(
        accounts=[
            meridian.ExternalAccount(
                external_account_id=LINKED, name="Interop", venue_account_type="Individual"
            ),
            meridian.ExternalAccount(
                external_account_id=f"unlinked-{uuid.uuid4().hex[:8]}",
                name="Roth IRA 5678",
                venue_account_type="Roth IRA",
            ),
        ]
    )
    assert published.message_id


async def test_an_unlinked_accounts_sync_status_is_published_and_its_holding_refused(
    plugin,
) -> None:
    """Ruled 2026-09-28: a sync status describes the connection, so it is not
    refused for want of a link; a holding from the same account still is."""
    unlinked = f"unlinked-{uuid.uuid4().hex[:8]}"
    published = await plugin.report_sync_status(
        source="interop",
        external_account_id=unlinked,
        state=meridian.SyncState.SYNC_STATE_HOLDINGS_UNAVAILABLE,
        observed_at_ns=NOW,
    )
    assert published.message_id
    opened = await statement(plugin, "interop", 1)
    with pytest.raises(NotLinked):
        await plugin.record_holding(
            statement_id=opened,
            instrument_id="INS-interop-unlinked",
            side=LONG,
            quantity=Decimal("1"),
            external_account_id=unlinked,
        )


@pytest.mark.parametrize("state", list(meridian.SyncState.values()))
async def test_every_sync_state_is_published_with_its_freshness(plugin, state) -> None:
    published = await plugin.report_sync_status(
        source="interop",
        external_account_id=LINKED,
        connection_healthy=state == meridian.SyncState.SYNC_STATE_CURRENT,
        state=state,
        holdings_as_of_ns=NOW,
        history_as_of_ns=NOW - 86_400_000_000_000,
        observed_at_ns=NOW,
    )
    assert published.message_id


# ── Contract v11: the edge keeps its own ─────────────────────────────────────
#
# A value as reported is checked for its shape alone; a raw record's
# reference is the sender's own; a row carries its raw record, pending
# quantities by value date and the provenance of what the plugin closed; and a
# backfill amends a row already recorded, journaled beside it, its cause the
# version and the field, the row as first recorded left as it was. The street
# lines core's `make interop` reads back hold the pending, closed and amended
# lines (e2e/interop/positions.expected).


async def test_an_account_kind_and_a_type_as_reported_beside_not_known_are_published(
    plugin,
) -> None:
    published = await plugin.report_external_accounts(
        accounts=[
            meridian.ExternalAccount(
                external_account_id=LINKED, name="Interop", account_kind="margin"
            ),
            meridian.ExternalAccount(
                external_account_id=f"unlinked-{uuid.uuid4().hex[:8]}",
                name="Individual 1234",
                account_kind="ACCOUNT_KIND_UNSPECIFIED",
                account_kind_as_reported=meridian.edge.as_reported(
                    "interop:account-type", "INDIVIDUAL", "Individual"
                ),
            ),
        ]
    )
    assert published.message_id


async def test_the_venues_own_type_from_an_earlier_plugin_is_still_accepted(plugin) -> None:
    # Deprecated in v11, accepted for the notice its stability gives.
    published = await plugin.report_external_accounts(
        accounts=[
            meridian.ExternalAccount(
                external_account_id=LINKED, name="Interop", venue_account_type="Individual"
            )
        ]
    )
    assert published.message_id


@pytest.mark.parametrize(
    ("given", "named"),
    [
        (
            operations_pb2.AsReported(scheme="interop:account-type", code="INDIVIDUAL"),
            "text is empty",
        ),
        (
            operations_pb2.AsReported(scheme="interop:account-type", code="x" * 129, text="t"),
            "code is 129 characters; at most 128",
        ),
    ],
)
async def test_a_value_as_reported_with_a_part_missing_or_too_long_is_refused_naming_it(
    plugin, given, named
) -> None:
    # Built by hand, past the SDK's own check, as a plugin in another
    # language might: the sidecar checks the shape and length, and nothing
    # else.
    with pytest.raises(CallFailed) as refused:
        await plugin.report_external_accounts(
            accounts=[
                meridian.ExternalAccount(
                    external_account_id=LINKED,
                    account_kind_as_reported=given,
                )
            ]
        )
    assert refused.value.kind == "invalid"
    assert f"accounts[0].account_kind_as_reported.{named}" in refused.value.detail


async def test_a_raw_record_naming_another_plugin_is_refused(plugin) -> None:
    opened = await statement(plugin, "interop-edge-refused", 1)
    with pytest.raises(CallFailed) as refused:
        await plugin.record_holding(
            statement_id=opened,
            instrument_id="INS-interop-edge-refused",
            side=LONG,
            quantity=Decimal("1"),
            external_account_id=LINKED,
            raw_record=operations_pb2.RawRecordRef(instance_id="another-plugin", key="k"),
        )
    assert refused.value.kind == "invalid"
    assert "raw_record.instance_id names another-plugin" in refused.value.detail


async def test_a_row_carries_its_raw_record_pending_and_what_the_plugin_closed(plugin) -> None:
    opened = await statement(plugin, "interop-edge", 1)
    recorded = await plugin.record_holding(
        statement_id=opened,
        instrument_id="INS-interop-edge-vti",
        side=LONG,
        quantity=Decimal("12.5"),
        settle_date_quantity=Decimal("10"),
        pending=[meridian.ReportedPending(value_date="2026-09-29", quantity=Decimal("2.5"))],
        provenance=[
            meridian.edge.derived(
                "settle_date_quantity", "the quantity less the trades not settled"
            )
        ],
        raw_record=plugin.raw_record("positions/interop/edge"),
        external_account_id=LINKED,
    )
    assert recorded.resolved


async def test_a_backfill_amends_a_past_row_and_run_twice_adds_nothing(plugin) -> None:
    """W2.4: the statement sent again is answered with the one recorded, and
    the row sent under it marked as a backfill names the field v11 added and
    the raw record it was re-converted from. The street journals one
    amendment, however many times it is sent; the row as first recorded
    stands (positions.expected holds both)."""
    external = f"{LINKED}/backfill/{uuid.uuid4().hex[:8]}"

    async def opening() -> operations_pb2.RecordHoldingsStatementResult:
        return await plugin.record_holdings_statement(
            source="interop-backfill",
            external_statement_id=external,
            external_account_id=LINKED,
            as_of_date="2026-09-28",
            read_at_ns=NOW,
            expected_rows=1,
        )

    first = await opening()
    await plugin.record_holding(
        statement_id=first.statement_id,
        instrument_id="INS-interop-backfill",
        side=LONG,
        quantity=Decimal("3"),
        external_account_id=LINKED,
    )
    again = await opening()
    assert again.already_recorded and again.statement_id == first.statement_id
    for _ in range(2):
        amended = await plugin.record_holding(
            statement_id=again.statement_id,
            instrument_id="INS-interop-backfill",
            side=LONG,
            quantity=Decimal("3"),
            external_account_id=LINKED,
            raw_record=plugin.raw_record("positions/interop/backfill"),
            backfill=meridian.edge.backfill("v11", "raw_record"),
        )
        assert amended.holding_id == "", "no new row is recorded"
    with pytest.raises(meridian.CallFailed) as refused:
        await plugin.record_holding(
            statement_id=again.statement_id,
            instrument_id="INS-interop-never-recorded",
            side=LONG,
            quantity=Decimal("1"),
            external_account_id=LINKED,
            raw_record=plugin.raw_record("positions/interop/none"),
            backfill=meridian.edge.backfill("v11", "raw_record"),
        )
    assert "a backfill amends a row already recorded" in str(refused.value)


# ── Contract v7: an operations plugin reads and hears the street ────────────
#
# Two more sidecars run beside this suite's custody one, as `operations`
# plugins: the first with the interop account in its read scope, the second
# with nothing in its scope. What the custody plugin records, the first reads
# and hears with its cause; the second reads and hears nothing (W2.5 to W2.7,
# W2.9, W4.3, W4.11).

_OPERATIONS = os.environ.get("MERIDIAN_OPERATIONS_SIDECAR_ADDRESS")
_UNSCOPED = os.environ.get("MERIDIAN_UNSCOPED_SIDECAR_ADDRESS")

#: The account a_linked_account.sql links LINKED to.
ACCOUNT = "ACC-INTEROP"
HEARD = "interop-operations"


@pytest.fixture
async def operations():
    if not _OPERATIONS:
        raise RuntimeError(
            "MERIDIAN_OPERATIONS_SIDECAR_ADDRESS is not set; `make interop` sets it"
        )
    connected = await meridian.connect(_OPERATIONS, heartbeat=False)
    try:
        yield connected
    finally:
        await connected.leave("interop finished")


@pytest.fixture
async def unscoped():
    if not _UNSCOPED:
        raise RuntimeError(
            "MERIDIAN_UNSCOPED_SIDECAR_ADDRESS is not set; `make interop` sets it"
        )
    connected = await meridian.connect(_UNSCOPED, heartbeat=False)
    try:
        yield connected
    finally:
        await connected.leave("interop finished")


async def recorded(plugin, instrument_id: str, quantity: str) -> str:
    """One statement of one row for the linked account, as the custody plugin
    sends it, with the account's figures as a whole."""
    opened = await statement(
        plugin, HEARD, 1, net_liquidation=Money(Decimal("93550.00"), "USD")
    )
    row = await plugin.record_holding(
        statement_id=opened,
        instrument_id=instrument_id,
        side=LONG,
        quantity=Decimal(quantity),
        average_cost=Money(Decimal("150.00"), "USD"),
        lots=[
            meridian.ReportedLot(
                quantity=Decimal(quantity),
                cost=Money(Decimal("1500.00"), "USD"),
                acquired_date="2024-03-11",
            )
        ],
        external_account_id=LINKED,
    )
    assert row.resolved
    return opened


class Hearing:
    """What an operations plugin's handlers were handed."""

    def __init__(self) -> None:
        self.positions: list[meridian.Heard] = []
        self.statements: list[meridian.Heard] = []
        self.arrived = asyncio.Event()

    async def position(self, heard: meridian.Heard) -> None:
        self.positions.append(heard)
        self.arrived.set()

    async def statement(self, heard: meridian.Heard) -> None:
        self.statements.append(heard)
        self.arrived.set()

    async def until(self, found, seconds: float = 10.0):
        """The first thing heard that `found` says is it."""

        async def waiting():
            while True:
                for heard in (*self.positions, *self.statements):
                    if found(heard):
                        return heard
                self.arrived.clear()
                await self.arrived.wait()

        return await asyncio.wait_for(waiting(), timeout=seconds)


def listening(plugin, hearing: Hearing, *, seed: bool) -> asyncio.Task[None]:
    return asyncio.create_task(
        plugin.receive(
            statement_recorded=hearing.statement,
            custodial_position_updated=hearing.position,
            seed=seed,
        )
    )


async def stopped(task: asyncio.Task[None]) -> None:
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_an_operations_plugin_is_launched_to_read_and_hear_the_street(operations) -> None:
    assert operations.identity.roles == ("operations",)
    assert "platform.street.query.list-statements" in operations.grants.publish
    assert "platform.street.event.custodial-position-updated" in operations.grants.subscribe


async def test_an_operations_plugin_hears_the_streets_changes_with_their_cause(
    plugin, operations
) -> None:
    """The custody plugin records; the operations plugin hears the position
    and the statement, typed, each with who caused it and not its own act,
    and with no number in what its handler sees (W2.5, W2.6, W4.3)."""
    hearing = Hearing()
    task = listening(operations, hearing, seed=False)
    try:
        await asyncio.sleep(1)  # the stream is open and the sidecar subscribed
        opened = await recorded(plugin, "INS-interop-heard", "12.5")
        position = await hearing.until(
            lambda h: (
                h.row == "CustodialPositionUpdated"
                and h.message.position.instrument_id == "INS-interop-heard"
            )
        )
        completed = await hearing.until(
            lambda h: h.row == "StatementRecorded" and h.message.statement_id == opened
        )
    finally:
        await stopped(task)

    assert not position.caught_up and not position.own
    assert position.cause is not None
    assert position.cause.instance_id == plugin.identity.instance_id
    held = position.message.position
    assert held.account_id == ACCOUNT
    assert meridian.as_decimal(held.quantity) == Decimal("12.5")
    assert str(meridian.as_money(held.average_cost).amount) == "150.00"
    assert [meridian.as_decimal(lot.quantity) for lot in held.lots] == [Decimal("12.5")]
    assert not position.message.HasField("journal") and not held.HasField("last_change")

    statement_heard = completed.message
    assert statement_heard.account_id == ACCOUNT
    assert statement_heard.external_account_id == LINKED
    assert str(meridian.as_money(statement_heard.figures[0].net_liquidation).amount) == (
        "93550.00"
    )
    assert completed.cause is not None and not completed.own


async def test_an_operations_plugin_reads_its_scope_and_is_refused_outside_it(
    plugin, operations
) -> None:
    """W2.7, W2.9, W4.4: the whole scope when it names no account, the
    account when it names one in its scope, and a refusal before the read
    leaves when it names one outside."""
    opened = await recorded(plugin, "INS-interop-read", "3")
    whole = await operations.list_custodial_positions(page_size=500)
    assert {held.account_id for held in whole.positions} == {ACCOUNT}
    assert whole.as_of.partitions[0].partition == "street"
    named = await operations.list_custodial_positions(account_id=ACCOUNT, page_size=500)
    assert "INS-interop-read" in {held.instrument_id for held in named.positions}

    statements = await operations.list_statements(account_id=ACCOUNT, page_size=500)
    read = [each for each in statements.statements if each.statement_id == opened]
    assert len(read) == 1 and read[0].rows_received == 1
    since = await operations.list_statements(
        account_id=ACCOUNT, since=statements.as_of, page_size=500
    )
    assert len(since.statements) == 0, "nothing completed since"

    with pytest.raises(
        meridian.NotGranted, match="ACC-ELSEWHERE is not in this plugin's read scope"
    ):
        await operations.list_custodial_positions(account_id="ACC-ELSEWHERE")


async def test_a_plugin_whose_scope_is_empty_reads_and_hears_nothing(plugin, unscoped) -> None:
    """W4.11: an empty scope is nothing, never everything."""
    hearing = Hearing()
    task = listening(unscoped, hearing, seed=True)
    try:
        await asyncio.sleep(1)
        await recorded(plugin, "INS-interop-unheard", "1")
        await asyncio.sleep(2)
    finally:
        await stopped(task)
    assert hearing.positions == [] and hearing.statements == []
    assert len((await unscoped.list_custodial_positions()).positions) == 0
    assert len((await unscoped.list_statements()).statements) == 0
    with pytest.raises(meridian.NotGranted):
        await unscoped.list_statements(account_id=ACCOUNT)


async def test_a_plugin_started_again_reads_what_changed_while_it_was_away(
    plugin, operations
) -> None:
    """W4.3: a plugin holds nothing; started again, it reads the store afresh
    and is handed what changed while it was not listening, marked caught up,
    before anything it hears after."""
    await recorded(plugin, "INS-interop-away", "1")
    first = Hearing()
    task = listening(operations, first, seed=True)
    try:
        await first.until(
            lambda h: (
                h.row == "CustodialPositionUpdated"
                and h.message.position.instrument_id == "INS-interop-away"
            )
        )
    finally:
        await stopped(task)

    # Changed while nothing listens.
    await recorded(plugin, "INS-interop-away", "2")

    again = Hearing()
    task = listening(operations, again, seed=True)
    try:
        caught = await again.until(
            lambda h: (
                h.row == "CustodialPositionUpdated"
                and h.message.position.instrument_id == "INS-interop-away"
            )
        )
    finally:
        await stopped(task)
    assert caught.caught_up
    assert meridian.as_decimal(caught.message.position.quantity) == Decimal("2")
