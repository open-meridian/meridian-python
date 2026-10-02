"""The book of record, end to end, through this SDK and real sidecars (contracts v8 and v9).

Run by `make e2e-book` in meridian-core, which brings up the street store, the
book, the instrument store and the conductor across a broker, four sidecars in
one network namespace -- a custody plugin's, an operations plugin's holding the
public half of a key made for the run, a reporting plugin's whose read scope is
one account, and an operations plugin's whose scope is empty -- and this
container beside them. Its accounts and grants are e2e/book/accounts.sql's.

What it holds, in one narrative, since each step reads what the last wrote:

day 1, a custody plugin records an account's statement; an operations plugin
sends an opening balance missing what downstream needs, refused naming each
field (contract v9), then composes the complete one from the street and
records it for a person, who answers for it, acting through a client on a
delegation; a reporting plugin reads the positions, lots and
pending settlements, and the account's standing opening balance; a second
opening balance is refused by its code, a duplicate by its key is answered as
the first, and one sent for nobody is refused;

day 2, the custodian's change: the operations plugin records the difference
as a break, as itself, which the reporting plugin hears (own false) and the
operations plugin hears as its own; the book's positions do not move; the
figures are recorded per agreement and read as a series; a person confirms
the cause and resolves the break with an adjustment, and the book moves into
agreement with the custodian, heard and read at the new watermark; an
injected difference is closed with an explanation and another as cleared,
nothing moving;

and throughout: the reporting plugin reads nothing of the account outside its
scope, the operations plugin whose scope is empty reads nothing, and a stream
killed and opened again is caught up from the store.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import meridian
from meridian import CommandRefused, Money, NotGranted
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.v1 import sidecar_pb2

# The accounts e2e/book/accounts.sql makes, and the external accounts the
# custody plugin's statements name, linked to them.
BROKERAGE = "ACC-BOOK-A"
FUTURES = "ACC-BOOK-B"
LINKED = "ext-book-a"
INSTITUTION = "Book Securities"
PERSON = "https://directory.example.org|e2e-book"

_ADDRESSES = {
    name: os.environ.get(variable)
    for name, variable in (
        ("custody", "MERIDIAN_SIDECAR_ADDRESS"),
        ("operations", "MERIDIAN_OPERATIONS_SIDECAR_ADDRESS"),
        ("reporting", "MERIDIAN_REPORTING_SIDECAR_ADDRESS"),
        ("unscoped", "MERIDIAN_UNSCOPED_SIDECAR_ADDRESS"),
    )
}
_KEYS = os.environ.get("MERIDIAN_BOOK_KEYS")


def address(name: str) -> str:
    found = _ADDRESSES[name]
    if not found:
        raise RuntimeError(
            "this suite needs the book's sidecars; `make e2e-book` in meridian-core starts them"
        )
    return found


# ── A person, as the dashboard would vouch for them (W4.9) ───────────────────
#
# Ed25519 (RFC 8032), the dashboard's signature, in the reference algorithm:
# the suite holds the private half of the key made for the run, and only the
# operations sidecar the public half. Pure Python, for a handful of
# signatures, so the image needs nothing beyond the SDK's test tools.

_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _inverse(x: int) -> int:
    return pow(x, _P - 2, _P)


def _x_of(y: int, sign: int) -> int:
    x2 = (y * y - 1) * _inverse(_D * y * y + 1) % _P
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _I % _P
    if x & 1 != sign:
        x = _P - x
    return x


_GY = 4 * _inverse(5) % _P
_GX = _x_of(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)


def _add(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    e1 = (a[1] - a[0]) * (b[1] - b[0]) % _P
    e2 = (a[1] + a[0]) * (b[1] + b[0]) % _P
    c = 2 * a[3] * b[3] * _D % _P
    d = 2 * a[2] * b[2] % _P
    e, f, g, h = e2 - e1, d - c, d + c, e2 + e1
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _times(scalar: int, point: tuple[int, ...]) -> tuple[int, ...]:
    held = (0, 1, 1, 0)
    while scalar:
        if scalar & 1:
            held = _add(held, point)
        point = _add(point, point)
        scalar >>= 1
    return held


def _compressed(point: tuple[int, ...]) -> bytes:
    z = _inverse(point[2])
    x, y = point[0] * z % _P, point[1] * z % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _sign(seed: bytes, message: bytes) -> bytes:
    digest = hashlib.sha512(seed).digest()
    a = int.from_bytes(digest[:32], "little")
    a = (a & ((1 << 254) - 8)) | (1 << 254)
    public = _compressed(_times(a, _G))
    r = int.from_bytes(hashlib.sha512(digest[32:] + message).digest(), "little") % _L
    big_r = _compressed(_times(r, _G))
    h = int.from_bytes(hashlib.sha512(big_r + public + message).digest(), "little") % _L
    return big_r + int.to_bytes((r + h * a) % _L, 32, "little")


def person(
    write: list[str],
    *,
    instance: str = "operations-test-1",
    delegation_id: str = "",
    client_name: str = "",
) -> str:
    """The Meridian-Caller header for a person at write on `write`, signed
    with the run's key as the dashboard signs one: under a minute, once; with
    the delegation and client they came through, where they came through one
    (contract v9)."""
    if not _KEYS:
        raise RuntimeError("MERIDIAN_BOOK_KEYS names no key; `make e2e-book` mounts one")
    keys = Path(_KEYS)
    seed = (keys / "private-key.der").read_bytes()[-32:]
    now = time.time_ns()
    claims = sidecar_pb2.CallerClaims(
        subject=PERSON,
        display_name="E2E Book",
        audience_instance_id=instance,
        level=sidecar_pb2.ACCESS_LEVEL_WRITE,
        read_account_ids=write,
        write_account_ids=write,
        issued_at_ns=now - 1_000_000_000,
        expires_at_ns=now + 50_000_000_000,
        assertion_id=str(uuid.uuid4()),
        delegation_id=delegation_id,
        client_name=client_name,
    ).SerializeToString()
    assertion = sidecar_pb2.CallerAssertion(
        claims=claims,
        signature=_sign(seed, claims),
        key_id=(keys / "key-id").read_text().strip(),
    )
    return base64.urlsafe_b64encode(assertion.SerializeToString()).decode().rstrip("=")


# ── What the custody plugin records ──────────────────────────────────────────


async def resolved(custody: meridian.Plugin, scheme: str, value: str) -> str:
    """An instrument as custody resolves it: with no platform, the
    deployment's placeholder for the identifier (W3.1, W3.7)."""
    reply = await custody.resolve_identifier(
        identifiers=[meridian.Identifier(scheme=scheme, value=value, source="e2e-book")],
        as_of_ns=time.time_ns(),
    )
    assert reply.found, (scheme, value)
    return reply.instrument_id


async def statement(
    custody: meridian.Plugin,
    as_of: str,
    rows: list[dict[str, Any]],
    figures: list[meridian.StatementFigures],
) -> str:
    opened = await custody.record_holdings_statement(
        source="e2e-book",
        external_statement_id=f"e2e-book-{as_of}-{uuid.uuid4()}",
        as_of_date=as_of,
        read_at_ns=time.time_ns(),
        expected_rows=len(rows),
        external_account_id=LINKED,
        institution=INSTITUTION,
        figures=figures,
    )
    for row in rows:
        await custody.record_holding(
            statement_id=opened.statement_id, external_account_id=LINKED, **row
        )
    return opened.statement_id


async def until(what: str, check: Any, seconds: float = 20) -> Any:
    """`check()`'s first answer that is not None, every quarter second."""
    deadline = asyncio.get_running_loop().time() + seconds
    while True:
        found = await check()
        if found is not None:
            return found
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError(f"{what}, in {seconds} seconds")
        await asyncio.sleep(0.25)


# ── What the operations plugin composes (W9.1) ───────────────────────────────


def opening_from(street: list[Any]) -> list[meridian.OpeningPosition]:
    """An opening balance as the sample operations plugin composes one, once
    complete: each custodial position as reported, its settled quantity, its
    lots as the custodian lists them with their cost and acquisition date;
    cash, no lots. Nothing here makes up what the street lacks."""
    positions = []
    for held in street:
        quantity = meridian.as_decimal(held.quantity)
        lots = [
            meridian.OpeningLot(
                quantity=meridian.as_decimal(lot.quantity),
                terms=meridian.LotTerms(
                    cost=meridian.as_money(lot.cost) if lot.HasField("cost") else None,
                    acquired_date=lot.acquired_date,
                    source="opening_balance",
                ),
            )
            for lot in held.lots
        ]
        positions.append(
            meridian.OpeningPosition(
                instrument_id=held.instrument_id,
                side=held.side,
                trade_date_quantity=quantity,
                settled_quantity=meridian.as_decimal(held.settle_date_quantity)
                if held.HasField("settle_date_quantity")
                else None,
                lots=lots,
            )
        )
    return positions


def by_instrument(positions: Any) -> dict[str, Any]:
    return {held.instrument_id: held for held in positions}


async def test_the_book_of_record_end_to_end() -> None:
    custody = await meridian.connect(address("custody"), heartbeat=False)
    operations = await meridian.connect(address("operations"), heartbeat=False)
    reporting = await meridian.connect(address("reporting"), heartbeat=False)
    unscoped = await meridian.connect(address("unscoped"), heartbeat=False)
    heard: dict[str, list[meridian.Heard[Any]]] = {"reporting": [], "operations": []}
    following: list[asyncio.Task[None]] = []

    def keeping(who: str) -> Any:
        async def kept(change: meridian.Heard[Any]) -> None:
            heard[who].append(change)

        return kept

    try:
        aapl = await resolved(custody, "symbol", "AAPL")
        usd = await resolved(custody, "iso4217", "USD")

        # ── Day 1 ────────────────────────────────────────────────────────
        day_one = await statement(
            custody,
            "2026-09-08",
            [
                {
                    "instrument_id": aapl,
                    "quantity": Decimal("12.5"),
                    "settle_date_quantity": Decimal("12.5"),
                    "side": "long",
                    "lots": [
                        meridian.ReportedLot(
                            quantity=Decimal("12.5"),
                            cost=Money(Decimal("2250.00"), "USD"),
                            acquired_date="2025-03-14",
                        )
                    ],
                },
                {
                    "instrument_id": usd,
                    "quantity": Decimal("1000.00"),
                    "settle_date_quantity": Decimal("1000.00"),
                    "side": "long",
                },
            ],
            [
                meridian.StatementFigures(
                    segment="", buying_power=Money(Decimal("25000.00"), "USD")
                )
            ],
        )

        async def completed(statement_id: str) -> Any:
            page = await operations.list_statements(account_id=BROKERAGE, page_size=100)
            done = [held for held in page.statements if held.statement_id == statement_id]
            return done[0] if done else None

        await until("the day 1 statement never completed", lambda: completed(day_one))
        street = await operations.list_custodial_positions(account_id=BROKERAGE, page_size=100)
        assert {held.instrument_id for held in street.positions} == {aapl, usd}

        # The account's first completed statement, composed and confirmed by
        # a person with write on it, with their reason (W9.1).
        source = meridian.OpeningSource(
            kind="custodian",
            name=INSTITUTION,
            as_of_date="2026-09-08",
            basis="trade_date",
            street_records=[
                meridian.StreetRecordRef(statement_id=day_one, as_of_date="2026-09-08")
            ],
        )
        key = f"opening-balance:{BROKERAGE}:{day_one}"

        # Incomplete: AAPL with no settled quantity and a lot of unknown
        # cost, which v8 admitted. Refused, nothing recorded, each missing
        # field named by its path (contract v9).
        with pytest.raises(CommandRefused) as incomplete:
            await operations.record_opening_balance(
                account_id=BROKERAGE,
                as_of_date="2026-09-08",
                sources=[source],
                positions=[
                    meridian.OpeningPosition(
                        instrument_id=aapl,
                        side="long",
                        trade_date_quantity=Decimal("12.5"),
                        lots=[
                            meridian.OpeningLot(
                                quantity=Decimal("12.5"),
                                terms=meridian.LotTerms(
                                    acquired_date="2025-03-14", source="opening_balance"
                                ),
                            )
                        ],
                    ),
                    meridian.OpeningPosition(
                        instrument_id=usd,
                        side="long",
                        trade_date_quantity=Decimal("1000.00"),
                        settled_quantity=Decimal("1000.00"),
                    ),
                ],
                reason="Opening balance from the statement of 2026-09-08, unfinished",
                idempotency_key=f"{key}:incomplete",
                acting_for=person([BROKERAGE, FUTURES]),
            )
        assert incomplete.value.reason == sidecar_pb2.REFUSAL_REASON_INCOMPLETE
        assert incomplete.value.fields == (
            "positions[0].settled_quantity",
            "positions[0].lots[0].terms.cost",
        )

        # Complete, confirmed by the person through a client on a
        # delegation: admitted, and the person stays the actor (W4.9).
        recorded = await operations.record_opening_balance(
            account_id=BROKERAGE,
            as_of_date="2026-09-08",
            sources=[source],
            positions=opening_from(list(street.positions)),
            reason="Opening balance from the statement of 2026-09-08, confirmed",
            idempotency_key=key,
            acting_for=person(
                [BROKERAGE, FUTURES],
                delegation_id="DLG-e2e-book",
                client_name="meridian on e2e",
            ),
        )
        assert recorded.entry.kind == "opening-balance"
        assert recorded.entry.actor.person.subject == PERSON
        assert recorded.attributes.opening_balance.as_of_date == "2026-09-08"

        # A duplicate by its key, after a lost reply: the first's answer.
        again = await operations.record_opening_balance(
            account_id=BROKERAGE,
            as_of_date="2026-09-08",
            sources=[source],
            positions=opening_from(list(street.positions)),
            reason="Opening balance from the statement of 2026-09-08, confirmed",
            idempotency_key=key,
            acting_for=person([BROKERAGE, FUTURES]),
        )
        assert again.entry.entry_id == recorded.entry.entry_id

        # A second opening balance: refused by its code.
        with pytest.raises(CommandRefused) as second:
            await operations.record_opening_balance(
                account_id=BROKERAGE,
                as_of_date="2026-09-08",
                sources=[source],
                reason="again",
                idempotency_key=f"{key}:again",
                acting_for=person([BROKERAGE, FUTURES]),
            )
        assert second.value.reason == sidecar_pb2.REFUSAL_REASON_OPENING_BALANCE_RECORDED

        # Sent for nobody: refused, a justified act being a person's.
        with pytest.raises(CommandRefused) as nobody:
            await operations.record_opening_balance(
                account_id=FUTURES,
                as_of_date="2026-09-08",
                sources=[source],
                reason="nobody answers for this",
            )
        assert nobody.value.reason == sidecar_pb2.REFUSAL_REASON_ACTOR_REQUIRED

        # What reporting reads of it: the positions, lots, and the standing
        # opening balance.
        read = await reporting.list_positions(account_id=BROKERAGE, page_size=100)
        held = by_instrument(read.positions)
        assert meridian.as_decimal(held[aapl].trade_date_quantity) == Decimal("12.5")
        assert meridian.as_decimal(held[aapl].settled_quantity) == Decimal("12.5")
        assert [meridian.as_decimal(lot.open_quantity) for lot in held[aapl].lots] == [
            Decimal("12.5")
        ]
        assert len(held[usd].lots) == 0, "cash has no lots"
        day_one_mark = read.as_of
        attributes = await reporting.list_account_attributes(account_id=BROKERAGE)
        (standing,) = attributes.attributes
        assert standing.opening_balance.entry_id == recorded.entry.entry_id

        # Following from here: reporting and operations each hear the book.
        following.append(
            asyncio.create_task(
                reporting.receive(
                    position_changed=keeping("reporting"),
                    break_changed=keeping("reporting"),
                    seed=False,
                )
            )
        )
        following.append(
            asyncio.create_task(
                operations.receive(break_changed=keeping("operations"), seed=False)
            )
        )
        await asyncio.sleep(1.5)

        # ── Day 2: the custodian's change ────────────────────────────────
        day_two = await statement(
            custody,
            "2026-09-09",
            [
                {
                    "instrument_id": aapl,
                    "quantity": Decimal("15"),
                    "settle_date_quantity": Decimal("15"),
                    "side": "long",
                    "lots": [
                        meridian.ReportedLot(
                            quantity=Decimal("12.5"),
                            cost=Money(Decimal("2250.00"), "USD"),
                            acquired_date="2025-03-14",
                        ),
                        meridian.ReportedLot(
                            quantity=Decimal("2.5"),
                            cost=Money(Decimal("567.50"), "USD"),
                            acquired_date="2026-09-09",
                        ),
                    ],
                },
                {
                    "instrument_id": usd,
                    "quantity": Decimal("432.50"),
                    "settle_date_quantity": Decimal("432.50"),
                    "side": "long",
                },
            ],
            [
                meridian.StatementFigures(
                    segment="", buying_power=Money(Decimal("24000.00"), "USD")
                ),
                meridian.StatementFigures(
                    segment="futures",
                    initial_margin=Money(Decimal("48000.00"), "USD"),
                    variation_margin=Money(Decimal("-1250.00"), "USD"),
                ),
            ],
        )
        await until("the day 2 statement never completed", lambda: completed(day_two))
        compared = meridian.StreetRecordRef(statement_id=day_two, as_of_date="2026-09-09")

        # The reconciliation finds AAPL short by 2.5: a break, as the plugin
        # itself (W9.4).
        found = await operations.record_break(
            account_id=BROKERAGE,
            position=meridian.PositionKey(instrument_id=aapl, side="long"),
            category="trade_date_quantity",
            differences=[
                meridian.BreakDifference(
                    field="trade_date_quantity",
                    book=meridian.BreakValue(quantity=Decimal("12.5")),
                    street=meridian.BreakValue(quantity=Decimal("15")),
                )
            ],
            book_watermark=day_one_mark,
            street=compared,
            business_date="2026-09-09",
            candidate_causes=[
                meridian.BreakCause(category="unbooked_trade", street_record=compared, note="")
            ],
            idempotency_key=f"break:{BROKERAGE}:{day_two}:{aapl}:trade_date_quantity",
        )
        (aapl_break,) = found.breaks
        assert found.entry.actor.system.instance_id == "operations-test-1"

        async def heard_break(who: str, own: bool) -> Any:
            for change in heard[who]:
                record = getattr(change.message, "break_record", None)
                if record is not None and record.break_id == aapl_break.break_id:
                    return change if change.own == own else None
            return None

        await until("reporting never heard the break", lambda: heard_break("reporting", False))
        await until(
            "operations never heard its own break", lambda: heard_break("operations", True)
        )

        # The book did not move: a read at the new watermark agrees with day 1's.
        unmoved = await reporting.list_positions(account_id=BROKERAGE, page_size=100)
        assert meridian.as_decimal(
            by_instrument(unmoved.positions)[aapl].trade_date_quantity
        ) == (Decimal("12.5"))

        # The figures per agreement, as reported (W9.5), and read as a series.
        agreement = meridian.MarginAgreementRef(
            statement_segment=meridian.StatementSegmentRef(
                external_account_id=LINKED, segment="futures", counterparty=INSTITUTION
            )
        )
        whole = meridian.MarginAgreementRef(
            statement_segment=meridian.StatementSegmentRef(
                external_account_id=LINKED, segment="", counterparty=INSTITUTION
            )
        )
        await operations.record_account_figures(
            account_id=BROKERAGE,
            business_date="2026-09-09",
            source=compared,
            agreements=[
                meridian.AgreementFigures(
                    agreement=whole,
                    figures=meridian.StatementFigures(
                        segment="", buying_power=Money(Decimal("24000.00"), "USD")
                    ),
                ),
                meridian.AgreementFigures(
                    agreement=agreement,
                    figures=meridian.StatementFigures(
                        segment="futures",
                        initial_margin=Money(Decimal("48000.00"), "USD"),
                        variation_margin=Money(Decimal("-1250.00"), "USD"),
                    ),
                ),
            ],
            idempotency_key=f"figures:{BROKERAGE}:{day_two}",
        )
        series = await reporting.list_account_figures(
            account_id=BROKERAGE,
            agreement=agreement,
            from_date="2026-09-01",
            to_date="2026-09-30",
        )
        (futures,) = series.figures
        assert meridian.as_money(futures.figures.variation_margin).amount == Decimal("-1250.00")
        # What cannot move, recorded from the statement as a finding: an
        # attribute, free derived from it, nothing moving (W9.15).
        await operations.record_encumbrances(
            account_id=BROKERAGE,
            business_date="2026-09-09",
            source=compared,
            positions=[
                meridian.PositionEncumbrances(
                    instrument_id=aapl,
                    side="long",
                    encumbrances=[
                        meridian.Encumbrance(
                            kind="pledged", quantity=Decimal("4"), source_code="PLED"
                        )
                    ],
                )
            ],
            idempotency_key=f"encumbrances:{BROKERAGE}:{day_two}",
        )
        encumbered = by_instrument(
            (await reporting.list_positions(account_id=BROKERAGE, page_size=100)).positions
        )[aapl]
        assert meridian.as_decimal(encumbered.trade_date_quantity) == Decimal("12.5")
        assert meridian.as_decimal(encumbered.free_quantity) == Decimal("8.5")
        assert encumbered.encumbrances[0].source_code == "PLED"

        # A person confirms the cause and resolves the break with the
        # adjustment that matches the custodian: +2.5, its lot as reported
        # (W9.6, W9.7).
        handled = await operations.handle_break(
            account_id=BROKERAGE,
            break_id=aapl_break.break_id,
            confirmed_cause=meridian.BreakCause(
                category="unbooked_trade", street_record=compared, note="a buy at the broker"
            ),
            handling=meridian.BreakHandling(owner_subject=PERSON, escalation_level=1),
            reason="Confirmed with the desk",
            acting_for=person([BROKERAGE]),
        )
        assert handled.breaks[0].state == ops.BREAK_STATE_OPEN
        resolved_by = await operations.resolve_break(
            account_id=BROKERAGE,
            break_ids=[aapl_break.break_id],
            reason="Books the buy of 2.5 placed at the broker",
            adjustment=meridian.Adjustment(
                effective_date="2026-09-09",
                lines=[
                    meridian.MovementLine(
                        instrument_id=aapl,
                        side="long",
                        bucket="settled",
                        quantity=Decimal("2.5"),
                        opens_lot=meridian.LotTerms(
                            cost=Money(Decimal("567.50"), "USD"), acquired_date="2026-09-09"
                        ),
                    ),
                    # Cash paid for it: no lot.
                    meridian.MovementLine(
                        instrument_id=usd,
                        side="long",
                        bucket="settled",
                        quantity=Decimal("-567.50"),
                    ),
                ],
            ),
            idempotency_key=f"resolve:{aapl_break.break_id}",
            acting_for=person([BROKERAGE]),
        )
        assert resolved_by.breaks[0].state == ops.BREAK_STATE_RESOLVED

        async def heard_position() -> Any:
            for change in heard["reporting"]:
                position = getattr(change.message, "position", None)
                if (
                    position is not None
                    and position.instrument_id == aapl
                    and meridian.as_decimal(position.trade_date_quantity) == Decimal("15.0")
                ):
                    return change
            return None

        await until("reporting never heard AAPL move", heard_position)
        agreed = await reporting.list_positions(account_id=BROKERAGE, page_size=100)
        agreed_held = by_instrument(agreed.positions)
        assert meridian.as_decimal(agreed_held[aapl].trade_date_quantity) == Decimal("15")
        assert meridian.as_decimal(agreed_held[usd].trade_date_quantity) == Decimal("432.50")
        assert len(agreed_held[aapl].lots) == 2

        # An injected difference closed with an explanation, and another as
        # cleared where it was gone: nothing moves.
        injected = []
        for category in ("cost_or_lots", "settled_quantity"):
            reply = await operations.record_break(
                account_id=BROKERAGE,
                position=meridian.PositionKey(instrument_id=usd, side="long"),
                category=category,
                differences=[meridian.BreakDifference(field="injected")],
                business_date="2026-09-09",
            )
            injected.append(reply.breaks[0].break_id)
        await operations.resolve_break(
            account_id=BROKERAGE,
            break_ids=[injected[0]],
            reason="custodian error",
            explanation="the custodian reported a cost it later corrected",
            acting_for=person([BROKERAGE]),
        )
        await operations.close_breaks_as_cleared(
            account_id=BROKERAGE,
            break_ids=[injected[1]],
            cleared_at=compared,
            reason="gone at the next statement",
            acting_for=person([BROKERAGE]),
        )
        closed = await reporting.list_breaks(account_id=BROKERAGE, states=["closed"])
        assert {held.break_id for held in closed.breaks} == set(injected)
        still = await reporting.list_positions(account_id=BROKERAGE, page_size=100)
        assert still.positions == agreed.positions

        # ── Scope (W4.11) ────────────────────────────────────────────────
        with pytest.raises(NotGranted):
            await reporting.list_positions(account_id=FUTURES)
        everything = await reporting.list_positions(page_size=500)
        assert {held.account_id for held in everything.positions} == {BROKERAGE}
        nothing = await unscoped.list_positions(page_size=500)
        assert list(nothing.positions) == []

        # ── A killed stream, caught up from the store ────────────────────
        for task in following:
            task.cancel()
        following.clear()
        late = await operations.record_break(
            account_id=BROKERAGE,
            position=meridian.PositionKey(instrument_id=aapl, side="long"),
            category="book_only",
            differences=[meridian.BreakDifference(field="late")],
            business_date="2026-09-10",
        )
        heard["reporting"].clear()
        following.append(
            asyncio.create_task(
                reporting.receive(break_changed=keeping("reporting"), seed=True)
            )
        )

        async def caught_up() -> Any:
            for change in heard["reporting"]:
                if change.message.break_record.break_id == late.breaks[0].break_id:
                    return change if change.caught_up else None
            return None

        await until("the reporting plugin never caught up the late break", caught_up)
    finally:
        for task in following:
            task.cancel()
        for plugin in (custody, operations, reporting, unscoped):
            await plugin.leave()
