"""The book of record's operations, from the plugin's side (contract v8).

Against the fake sidecar: the params each sends -- lots, lines and buckets,
a oneof's one arm, the idempotency key, the person -- and the book's refusal
raised by its code. What the book does with them is meridian-core's to test,
and its e2e-book suite's.
"""

from __future__ import annotations

import inspect
from decimal import Decimal

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import CallFailed, CommandRefused, Money
from meridian.plugin.v1 import operations_pb2
from meridian.v1 import sidecar_pb2


async def connected(sidecar: tuple[FakeSidecar, str]) -> meridian.Plugin:
    _, address = sidecar
    return await meridian.connect(address, heartbeat=False)


def opening_position() -> meridian.OpeningPosition:
    return meridian.OpeningPosition(
        instrument_id="INS-AAPL",
        side="long",
        trade_date_quantity=Decimal("12.5"),
        settled_quantity=None,
        lots=[
            meridian.OpeningLot(
                quantity=Decimal("12.5"),
                terms=meridian.LotTerms(
                    cost=Money(Decimal("2250.00"), "USD"),
                    acquired_date="2025-03-14",
                    source="opening_balance",
                ),
            )
        ],
    )


async def test_an_opening_balance_carries_its_lots_its_source_and_its_key(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        reply = await plugin.record_opening_balance(
            account_id="ACC-1",
            as_of_date="2026-09-08",
            sources=[
                meridian.OpeningSource(
                    kind="custodian",
                    name="Interactive Brokers",
                    as_of_date="2026-09-08",
                    basis="trade_date",
                    street_records=[meridian.StreetRecordRef(statement_id="STMT-1")],
                )
            ],
            positions=[opening_position()],
            reason="from the statement of 2026-09-08",
            idempotency_key="opening-balance:ACC-1:STMT-1",
        )
    finally:
        await plugin.leave()
    assert reply.entry.kind == "opening-balance"
    (sent,) = service.operations.sent
    assert isinstance(sent, operations_pb2.RecordOpeningBalanceParams)
    assert sent.idempotency_key == "opening-balance:ACC-1:STMT-1"
    assert sent.sources[0].kind == operations_pb2.OPENING_SOURCE_KIND_CUSTODIAN
    (position,) = sent.positions
    assert position.side == operations_pb2.HOLDING_SIDE_LONG
    # Not stated, unset: unknown, never zero.
    assert not position.HasField("settled_quantity")
    assert meridian.as_decimal(position.lots[0].quantity) == Decimal("12.5")
    assert position.lots[0].terms.source == operations_pb2.LOT_SOURCE_OPENING_BALANCE
    assert str(meridian.as_money(position.lots[0].terms.cost).amount) == "2250.00"
    # A lot's unit cost unset where the source gave none, never derived.
    assert not position.lots[0].terms.HasField("unit_cost")


async def test_a_number_inside_a_lot_is_refused_naming_its_path(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    position = opening_position()
    bad = meridian.OpeningPosition(
        instrument_id="INS-AAPL",
        side="long",
        trade_date_quantity=Decimal("12.5"),
        lots=[meridian.OpeningLot(quantity=Decimal("0.0000000000000000001"))],
    )
    try:
        with pytest.raises(ValueError, match=r"positions\[1\]\.lots\[0\]\.quantity"):
            await plugin.record_opening_balance(account_id="ACC-1", positions=[position, bad])
    finally:
        await plugin.leave()
    assert service.operations.sent == []


async def test_a_break_takes_one_subject_and_two_are_refused_naming_the_oneof(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.record_break(
            account_id="ACC-1",
            position=meridian.PositionKey(instrument_id="INS-AAPL", side="long"),
            category="trade_date_quantity",
            differences=[
                meridian.BreakDifference(
                    field="trade_date_quantity",
                    book=meridian.BreakValue(quantity=Decimal("12.5")),
                    street=meridian.BreakValue(quantity=Decimal("15")),
                )
            ],
            business_date="2026-09-09",
            candidate_causes=[
                meridian.BreakCause(category="unbooked_trade", none_found=True, note="")
            ],
            idempotency_key="break:ACC-1:STMT-2:AAPL",
        )
        with pytest.raises(ValueError, match="subject takes one of position, figure"):
            await plugin.record_break(
                account_id="ACC-1",
                position=meridian.PositionKey(instrument_id="INS-AAPL", side="long"),
                figure=meridian.FigureKey(figure="collateral.quantity"),
            )
        with pytest.raises(ValueError, match=r"differences\[0\]\.book\.value takes one of"):
            await plugin.record_break(
                account_id="ACC-1",
                differences=[
                    meridian.BreakDifference(
                        field="x",
                        book=meridian.BreakValue(quantity=Decimal("1"), text="one"),
                    )
                ],
            )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert sent.WhichOneof("subject") == "position"
    assert sent.differences[0].book.WhichOneof("value") == "quantity"
    assert meridian.as_decimal(sent.differences[0].street.quantity) == Decimal("15")
    assert sent.candidate_causes[0].WhichOneof("item") == "none_found"
    unbooked = operations_pb2.BREAK_CAUSE_CATEGORY_UNBOOKED_TRADE
    assert sent.candidate_causes[0].category == unbooked


async def test_a_resolution_is_one_of_its_kinds_for_a_person(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.resolve_break(
            account_id="ACC-1",
            break_ids=["BRK-1"],
            reason="books the buy",
            adjustment=meridian.Adjustment(
                effective_date="2026-09-09",
                lines=[
                    meridian.MovementLine(
                        instrument_id="INS-AAPL",
                        side="long",
                        bucket="settled",
                        quantity=Decimal("2.5"),
                        opens_lot=meridian.LotTerms(cost=Money(Decimal("567.50"), "USD")),
                    )
                ],
            ),
        )
        await plugin.resolve_break(
            account_id="ACC-1", break_ids=["BRK-3"], reason="r", explanation="custodian error"
        )
        with pytest.raises(ValueError, match="resolution takes one of"):
            await plugin.resolve_break(
                account_id="ACC-1",
                break_ids=["BRK-4"],
                explanation="one",
                reversal=meridian.Reversal(entry_id="ENT-1"),
            )
    finally:
        await plugin.leave()
    adjusted, explained = service.operations.sent
    assert adjusted.WhichOneof("resolution") == "adjustment"
    line = adjusted.adjustment.lines[0]
    assert line.bucket == operations_pb2.SETTLEMENT_BUCKET_SETTLED
    assert meridian.as_decimal(line.quantity) == Decimal("2.5")
    assert explained.WhichOneof("resolution") == "explanation"
    # An empty string is still an arm: only None is unset.
    assert "acting_for" in inspect.signature(meridian.Plugin.resolve_break).parameters


async def test_a_stated_cost_is_the_other_arm_of_a_basis_adjustment(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.resolve_break(
            account_id="ACC-1",
            break_ids=["BRK-5"],
            reason="the custodian's cost",
            adjustment=meridian.Adjustment(
                effective_date="2026-09-09",
                basis_adjustments=[
                    meridian.BasisAdjustment(
                        lot_id="LOT-1", stated_cost=Money(Decimal("2300.00"), "USD")
                    )
                ],
            ),
        )
        with pytest.raises(ValueError, match="cost takes one of"):
            await plugin.resolve_break(
                account_id="ACC-1",
                adjustment=meridian.Adjustment(
                    basis_adjustments=[
                        meridian.BasisAdjustment(
                            lot_id="LOT-1",
                            stated_cost=Money(Decimal("1"), "USD"),
                            cost_change=Money(Decimal("1"), "USD"),
                        )
                    ],
                ),
            )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    (basis,) = sent.adjustment.basis_adjustments
    assert basis.WhichOneof("cost") == "stated_cost"
    assert str(meridian.as_money(basis.stated_cost).amount) == "2300.00"


async def test_breaks_close_as_cleared_citing_the_statement_for_a_person(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.close_breaks_as_cleared(
            account_id="ACC-1",
            break_ids=["BRK-2", "BRK-3"],
            cleared_at=meridian.StreetRecordRef(statement_id="STMT-3", as_of_date="2026-09-10"),
            reason="gone at the next statement",
            idempotency_key="cleared:ACC-1:STMT-3",
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert isinstance(sent, operations_pb2.CloseBreaksAsClearedParams)
    assert list(sent.break_ids) == ["BRK-2", "BRK-3"]
    assert sent.cleared_at.statement_id == "STMT-3"
    assert sent.idempotency_key == "cleared:ACC-1:STMT-3"
    assert "acting_for" in inspect.signature(meridian.Plugin.close_breaks_as_cleared).parameters


async def test_encumbrances_are_recorded_from_a_statement_as_the_plugin_itself(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.record_encumbrances(
            account_id="ACC-1",
            business_date="2026-09-10",
            source=meridian.StreetRecordRef(statement_id="STMT-3", as_of_date="2026-09-10"),
            positions=[
                meridian.PositionEncumbrances(
                    instrument_id="INS-AAPL",
                    side="long",
                    encumbrances=[
                        meridian.Encumbrance(
                            kind="pledged", quantity=Decimal("4"), source_code="PLED"
                        ),
                        meridian.Encumbrance(kind="posted", quantity=Decimal("1")),
                    ],
                ),
                meridian.PositionEncumbrances(instrument_id="INS-MSFT", side="long"),
            ],
            idempotency_key="encumbrances:ACC-1:STMT-3",
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert isinstance(sent, operations_pb2.RecordEncumbrancesParams)
    aapl, msft = sent.positions
    assert [held.kind for held in aapl.encumbrances] == [
        operations_pb2.ENCUMBRANCE_KIND_PLEDGED,
        operations_pb2.ENCUMBRANCE_KIND_POSTED,
    ]
    assert meridian.as_decimal(aapl.encumbrances[0].quantity) == Decimal("4")
    # The whole set: empty is none now.
    assert list(msft.encumbrances) == []
    assert not sent.HasField("acting_for"), "a finding, sent as the plugin itself"


def test_findings_and_reads_carry_no_person_and_justified_acts_may() -> None:
    for sent_for in (
        "record_opening_balance",
        "handle_break",
        "resolve_break",
        "close_breaks_as_cleared",
    ):
        assert "acting_for" in inspect.signature(getattr(meridian.Plugin, sent_for)).parameters
    for read in (
        "list_positions",
        "list_breaks",
        "list_account_figures",
        "list_account_attributes",
        "resolve_instrument",
    ):
        assert "acting_for" not in inspect.signature(getattr(meridian.Plugin, read)).parameters


@pytest.mark.parametrize(
    "reason",
    [
        sidecar_pb2.REFUSAL_REASON_OPENING_BALANCE_RECORDED,
        sidecar_pb2.REFUSAL_REASON_ACTOR_REQUIRED,
        sidecar_pb2.REFUSAL_REASON_BREAK_STATE,
        sidecar_pb2.REFUSAL_REASON_LATER_ENTRIES_STAND,
        sidecar_pb2.REFUSAL_REASON_IDEMPOTENCY_CONFLICT,
    ],
)
async def test_the_books_refusal_is_raised_by_its_code(sidecar, reason: int) -> None:
    service, _ = sidecar
    service.operations.refuse = (grpc.StatusCode.ABORTED, "worded any way at all")
    service.operations.refuse_metadata = (
        ("meridian-refusal-bin", sidecar_pb2.Refusal(reason=reason).SerializeToString()),
    )
    plugin = await connected(sidecar)
    try:
        with pytest.raises(CommandRefused) as caught:
            await plugin.record_opening_balance(account_id="ACC-1", reason="r")
    finally:
        await plugin.leave()
    assert caught.value.reason == reason
    assert caught.value.reason_name == sidecar_pb2.RefusalReason.Name(reason)
    # Still what a plugin catching a refusal caught: a CallFailed, refused.
    assert isinstance(caught.value, CallFailed)
    assert caught.value.kind == "refused"
    assert caught.value.detail == "worded any way at all"


async def test_an_incomplete_entry_names_each_field_it_left_out(sidecar) -> None:
    """Contract v9: the book refuses an entry missing what downstream needs,
    and the refusal names each field by its path in the call, beside the
    code, so a plugin shows the person what to supply."""
    service, _ = sidecar
    service.operations.refuse = (grpc.StatusCode.ABORTED, "the opening balance is incomplete")
    missing = ("positions[0].settled_quantity", "positions[1].lots[0].terms.cost")
    service.operations.refuse_metadata = (
        (
            "meridian-refusal-bin",
            sidecar_pb2.Refusal(
                reason=sidecar_pb2.REFUSAL_REASON_INCOMPLETE, fields=missing
            ).SerializeToString(),
        ),
    )
    plugin = await connected(sidecar)
    try:
        with pytest.raises(CommandRefused) as caught:
            await plugin.record_opening_balance(account_id="ACC-1", reason="r")
    finally:
        await plugin.leave()
    assert caught.value.reason_name == "REFUSAL_REASON_INCOMPLETE"
    assert caught.value.fields == missing


async def test_a_refusal_naming_nothing_missing_has_no_fields(sidecar) -> None:
    service, _ = sidecar
    service.operations.refuse = (grpc.StatusCode.ABORTED, "standing")
    service.operations.refuse_metadata = (
        (
            "meridian-refusal-bin",
            sidecar_pb2.Refusal(
                reason=sidecar_pb2.REFUSAL_REASON_OPENING_BALANCE_RECORDED
            ).SerializeToString(),
        ),
    )
    plugin = await connected(sidecar)
    try:
        with pytest.raises(CommandRefused) as caught:
            await plugin.record_opening_balance(account_id="ACC-1", reason="r")
    finally:
        await plugin.leave()
    assert caught.value.fields == ()


async def test_an_abort_with_no_code_is_still_a_handler_error(sidecar) -> None:
    service, _ = sidecar
    service.operations.refuse = (grpc.StatusCode.ABORTED, "no break BRK-9 in ACC-1")
    plugin = await connected(sidecar)
    try:
        with pytest.raises(CallFailed) as caught:
            await plugin.handle_break(account_id="ACC-1", break_id="BRK-9", reason="r")
    finally:
        await plugin.leave()
    assert not isinstance(caught.value, CommandRefused)
    assert caught.value.kind == "handler error"


async def test_an_unusable_instrument_record_is_named_and_unavailability_retryable(
    sidecar,
) -> None:
    """Contract v10: the book names an instrument whose record lacks its asset
    class or currency, as any missing field; and a command it could not check
    because the instrument store did not answer is refused beside
    UNAVAILABLE, to be tried again."""
    service, _ = sidecar
    service.operations.refuse = (grpc.StatusCode.ABORTED, "the opening balance is incomplete")
    missing = ("positions[0].instrument.asset_class", "positions[0].instrument.currency")
    service.operations.refuse_metadata = (
        (
            "meridian-refusal-bin",
            sidecar_pb2.Refusal(
                reason=sidecar_pb2.REFUSAL_REASON_INCOMPLETE, fields=missing
            ).SerializeToString(),
        ),
    )
    plugin = await connected(sidecar)
    try:
        with pytest.raises(CommandRefused) as caught:
            await plugin.record_opening_balance(account_id="ACC-1", reason="r")
        assert caught.value.fields == missing
        assert not caught.value.retryable

        service.operations.refuse = (grpc.StatusCode.UNAVAILABLE, "try again")
        service.operations.refuse_metadata = (
            (
                "meridian-refusal-bin",
                sidecar_pb2.Refusal(
                    reason=sidecar_pb2.REFUSAL_REASON_REFERENCE_UNAVAILABLE
                ).SerializeToString(),
            ),
        )
        with pytest.raises(CommandRefused) as again:
            await plugin.record_opening_balance(account_id="ACC-1", reason="r")
    finally:
        await plugin.leave()
    assert again.value.reason_name == "REFUSAL_REASON_REFERENCE_UNAVAILABLE"
    assert again.value.retryable


def test_the_sdk_declares_contract_v18() -> None:
    assert meridian.SCHEMA_VERSION == "v19"


def test_every_row_of_the_book_is_heard_with_a_handler_of_its_own() -> None:
    from meridian.operations import DELIVERED

    names = {row.name: row for row in DELIVERED}
    for row, caught_up_by in (
        ("PositionChanged", "list_positions"),
        ("BreakChanged", "list_breaks"),
        ("AccountFiguresRecorded", "list_account_figures"),
        ("AccountAttributeChanged", "list_account_attributes"),
    ):
        assert names[row].caught_up_by == caught_up_by
        assert names[row].record_journal == "last_change"
    assert names["PositionChanged"].account == ("position", "account_id")
    assert names["BreakChanged"].within == "break_record"
    receive = inspect.signature(meridian.Plugin.receive).parameters
    for handler in (
        "position_changed",
        "break_changed",
        "account_figures_recorded",
        "account_attribute_changed",
    ):
        assert handler in receive
