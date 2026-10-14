"""A plugin's side of every case contract v22 adds to the role suites:
the order path's (`connectivity`, `oms`, and its cases of `portfolio`,
`ems`, `compliance`, `operations` and `reporting`) and the settlement
calendars' reads every role holds; and contract v23's: venue-originated
fills (`connectivity`, `ems`, `operations`, `compliance`) and an event
contract's outcomes heard and read (`reporting`, `portfolio`, `compliance`,
`signal`, `operations`), and the OANDA batch's value-date roll
(`connectivity`).

Each producer is what a plugin holding the role does, through the SDK's
typed operations, for what the case's source presents: it runs against the
suite's `Recorder`, and the case is checked by what was sent and heard. A
case name means one thing in every suite holding it, so one producer
answers it in each. Imported by the tests that run a role's whole suite.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal

import meridian
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder
from meridian.testing import caller_header

Producer = Callable[[Recorder], Awaitable[None]]

ACCOUNT = "ACC-1"
ORDER = "ORD-01JAE00000000000000000001"
PLACEMENT = "PLC-01JAE00000000000000000001"
VENUE = "sim-venue-1"
CODE = "SIM-ACCT-7"
AAPL = "INS-01J8XQ4M7K0000000000AAPL"
EUR = "INS-01J8XQ4M7K00000000CASHEUR"
USD = "INS-01J8XQ4M7K00000000CASHUSD"
CALENDAR = "CAL-01JAE0000000000000000USSS"
AFTER = ops.Watermark(partitions=[ops.PartitionSequence(partition="book", sequence=41)])


def usd(amount: str) -> meridian.Money:
    return meridian.Money(Decimal(amount), "USD")


def hearing(*rows: tuple[str, str, object]) -> Producer:
    """A producer hearing each row's message on its handler, as delivered."""

    async def produce(recorder: Recorder) -> None:
        handlers = {}
        for row, arm, message in rows:
            recorder.answer(row, lambda _, message=message: message)

            async def heard(_: object) -> None:
                return None

            handlers[arm] = heard
        await recorder.receive(**handlers)

    return produce


def then(*steps: Producer) -> Producer:
    async def produce(recorder: Recorder) -> None:
        for step in steps:
            await step(recorder)

    return produce


ORDER_UPDATED = ("OrderUpdated", "order_updated", ops.OrderUpdatedEvent())
PLACEMENT_UPDATED = (
    "PlacementUpdated",
    "placement_updated",
    ops.PlacementUpdatedEvent(
        placement=ops.Placement(
            placement_id=PLACEMENT,
            order_id=ORDER,
            connectivity_instance_id=VENUE,
            venue_account_code=CODE,
        )
    ),
)
EXECUTION_RECORDED = ("ExecutionRecorded", "execution_recorded", ops.ExecutionRecordedEvent())
LOCATE_UPDATED = ("LocateUpdated", "locate_updated", ops.LocateUpdatedEvent())
INSTRUCTION_CHANGED = (
    "TradingInstructionChanged",
    "trading_instruction_changed",
    ops.TradingInstructionChangedEvent(
        instruction=ops.TradingInstruction(
            target=ops.TradingInstructionTarget(all_accounts=True),
            value=ops.TRADING_INSTRUCTION_VALUE_STOP,
        )
    ),
)
ATTRIBUTE_CHANGED = (
    "AccountAttributeChanged",
    "account_attribute_changed",
    ops.AccountAttributeChangedEvent(
        attributes=ops.AccountAttributes(account_id=ACCOUNT, waits_for_compliance=True)
    ),
)
CATALOGUE_HEARD = ("ReportVenueCatalogue", "report_venue_catalogue", ops.VenueCatalogueEvent())


# ── Reads every role holds ───────────────────────────────────────────────────


async def reads_a_calendar(recorder: Recorder) -> None:
    await recorder.read_calendar(
        calendar_id=CALENDAR, from_date=date(2026, 10, 1), to_date=date(2026, 10, 31)
    )


async def asks_for_a_settlement_date(recorder: Recorder) -> None:
    await recorder.compute_date(
        settlement=meridian.SettlementDateInputs(instrument_id=AAPL, trade_date="2026-10-09")
    )


async def reads_orders_and_catches_up(recorder: Recorder) -> None:
    await recorder.list_orders(account_id=ACCOUNT)
    await recorder.list_orders(account_id=ACCOUNT, since=AFTER)


async def reads_an_orders_history(recorder: Recorder) -> None:
    await recorder.read_order_history(account_id=ACCOUNT, order_id=ORDER)


async def reads_the_instructions(recorder: Recorder) -> None:
    await recorder.list_trading_instructions()


async def reads_the_attributes(recorder: Recorder) -> None:
    await recorder.list_account_attributes(account_id=ACCOUNT)


async def reads_the_catalogue(recorder: Recorder) -> None:
    await recorder.read_venue_catalogue(connectivity_instance_id=VENUE, venue_account_code=CODE)


async def reads_the_locates(recorder: Recorder) -> None:
    await recorder.list_locates(account_id=ACCOUNT)


# ── Proposing, releasing, deciding ───────────────────────────────────────────


async def proposes_an_order(recorder: Recorder) -> None:
    await recorder.propose_order(
        account_id=ACCOUNT,
        instrument_id=AAPL,
        side="buy",
        quantity=Decimal("10"),
        order_type="limit",
        limit_price=usd("227.50"),
        time_in_force="day",
        idempotency_key="propose:ACC-1:pm-ticket-4471",
    )


async def proposes_an_order_for_an_amount(recorder: Recorder) -> None:
    await recorder.propose_order(
        account_id=ACCOUNT,
        instrument_id=AAPL,
        side="buy",
        cash_quantity=usd("5000.00"),
        order_type="market",
        idempotency_key="propose:ACC-1:pm-ticket-4472",
    )


async def proposes_a_child_order(recorder: Recorder) -> None:
    await recorder.propose_order(
        account_id=ACCOUNT,
        instrument_id=AAPL,
        side="buy",
        quantity=Decimal("2"),
        link=meridian.OrderLink(kind="split", parent_order_id=ORDER),
        idempotency_key="twap:ORD-1:slice-3",
    )


async def withdraws(recorder: Recorder) -> None:
    await recorder.request_order_change(
        order_id=ORDER, change=meridian.OrderChange(kind="withdraw"), reason="No longer wanted."
    )


async def releases(recorder: Recorder) -> None:
    await recorder.release_order(order_id=ORDER, idempotency_key="release:ORD-1")


async def rejects(recorder: Recorder) -> None:
    await recorder.decide_approval(
        order_id=ORDER, decision="reject", reason="Outside the desk's mandate."
    )


async def requires_approval(recorder: Recorder) -> None:
    await recorder.decide_approval(order_id=ORDER, decision="require", reason="Over the limit.")


async def overrides_a_block(recorder: Recorder) -> None:
    await recorder.decide_approval(
        order_id=ORDER, decision="override", reason="Approved by the CIO on the call."
    )


async def holds(recorder: Recorder) -> None:
    await recorder.set_working_condition(
        order_id=ORDER, condition="held", set=True, reason="Waiting for the close."
    )


async def claims(recorder: Recorder) -> None:
    await recorder.set_working_condition(order_id=ORDER, condition="claimed", set=True)


async def amends_the_limit(recorder: Recorder) -> None:
    await recorder.request_order_change(
        order_id=ORDER, change=meridian.OrderChange(kind="amend", limit_price=usd("226.00"))
    )


async def cancels_the_order(recorder: Recorder) -> None:
    await recorder.request_order_change(
        order_id=ORDER, change=meridian.OrderChange(kind="cancel")
    )


async def cancels_a_placement(recorder: Recorder) -> None:
    await recorder.request_placement_change(
        placement_id=PLACEMENT, change=meridian.PlacementChange(kind="cancel")
    )


async def records_a_telephoned_order(recorder: Recorder) -> None:
    await recorder.record_order(
        account_id=ACCOUNT,
        instrument_id=AAPL,
        side="sell",
        quantity=Decimal("5"),
        origin="telephoned",
        idempotency_key="phone:ACC-1:0930",
    )


async def enters_a_done_away_execution(recorder: Recorder) -> None:
    await recorder.report_execution(
        order_id=ORDER,
        kind="done_away",
        quantity=Decimal("5"),
        price=usd("227.41"),
        settlement_date=date(2026, 10, 13),
    )


async def enters_a_manual_execution(recorder: Recorder) -> None:
    await recorder.report_execution(
        placement_id=PLACEMENT,
        kind="manual",
        quantity=Decimal("5"),
        price=usd("227.41"),
        settlement_date=date(2026, 10, 13),
    )


async def acknowledges_a_late_fact(recorder: Recorder) -> None:
    await recorder.acknowledge_flag(
        order_id=ORDER, condition="late_fact", reason="The fill after the cancel is ours."
    )


def uses_the_locate(kind: str) -> Producer:
    async def produce(recorder: Recorder) -> None:
        await recorder.list_locates(account_id=ACCOUNT)
        await recorder.record_locate_use(
            locate_record_id="LOC-01JAE00000000000000000001",
            use=meridian.LocateUse(kind=kind, quantity=Decimal("100"), order_id=ORDER),
        )

    return produce


async def checks_a_proposed_order(recorder: Recorder) -> None:
    await recorder.record_check(
        order_id=ORDER, order_version=1, rule="restricted-list", verdict="pass"
    )


async def checks_a_placement(recorder: Recorder) -> None:
    await recorder.record_check(placement_id=PLACEMENT, rule="fat-finger", verdict="pass")


async def checks_after_a_fill(recorder: Recorder) -> None:
    await recorder.record_check(order_id=ORDER, rule="concentration", verdict="warn")


async def maps_an_account(recorder: Recorder) -> None:
    # From the ems's page at admin, acting for the admin viewing it (W11.22).
    await recorder.map_venue_account(
        connectivity_instance_id=VENUE,
        venue_account_code=CODE,
        account_id=ACCOUNT,
        acting_for=caller_header("admin"),
    )


async def places(recorder: Recorder) -> None:
    await recorder.resolve_instrument(instrument_id=AAPL)
    await recorder.resolve_venue(
        identifiers=[meridian.Identifier(scheme="mic", value="XNAS")], as_of_ns=1
    )
    await recorder.create_placement(
        order_id=ORDER,
        connectivity_instance_id=VENUE,
        venue_account_code=CODE,
        quantity=Decimal("10"),
        destination="XNAS",
        idempotency_key="place:ORD-1:1",
    )


async def re_checks_a_value_date(recorder: Recorder) -> None:
    await recorder.compute_date(
        business_day=meridian.BusinessDayInputs(date="2026-11-26", calendars=[CALENDAR])
    )


# ── A connectivity plugin ────────────────────────────────────────────────────

RAW = ops.RawRecordRef(instance_id=VENUE, key="sim:exec-report:1")


def reports(**fields: object) -> Producer:
    async def produce(recorder: Recorder) -> None:
        await recorder.report_placement(placement_id=PLACEMENT, **fields)  # type: ignore[arg-type]

    return produce


async def acknowledges_its_placement(recorder: Recorder) -> None:
    await hearing(PLACEMENT_UPDATED)(recorder)
    (heard,) = recorder.on("PlacementUpdated")
    await recorder.report_placement(
        placement_id=heard.placement.placement_id,
        event="acknowledged",
        venue_order_id="SIM-ORD-1",
        raw_record=RAW,
    )


async def hears_nothing_of_another_instance(recorder: Recorder) -> None:
    # The sidecar delivers it no placement naming another instance, so
    # nothing reaches its handler and it sends nothing.
    async def heard(_: object) -> None:
        return None

    await recorder.receive(placement_updated=heard)


PAUSE_HEARD = (
    "TradingInstructionChanged",
    "trading_instruction_changed",
    ops.TradingInstructionChangedEvent(
        instruction=ops.TradingInstruction(
            target=ops.TradingInstructionTarget(instance_id=VENUE),
            value=ops.TRADING_INSTRUCTION_VALUE_PAUSE,
        )
    ),
)


async def sends_nothing_on_a_pause(recorder: Recorder) -> None:
    # It hears the pause on itself, then a placement naming it, and holds
    # the placement unsent: no report, no execution.
    await hearing(PAUSE_HEARD, PLACEMENT_UPDATED)(recorder)


async def fills_with_its_settlement_date(recorder: Recorder) -> None:
    await recorder.compute_date(
        settlement=meridian.SettlementDateInputs(instrument_id=AAPL, trade_date="2026-10-09")
    )
    await recorder.report_execution(
        placement_id=PLACEMENT,
        venue_execution_id="SIM-EXE-1",
        quantity=Decimal("10"),
        price=usd("227.41"),
        trade_date=date(2026, 10, 9),
        computed_settlement_date=date(2026, 10, 13),
        settlement_date_basis=meridian.DateBasis(
            rule=meridian.DateRuleRef(kind="settlement", subject="US/equity", version=3)
        ),
        raw_record=RAW,
    )


async def derives_one_id_twice(recorder: Recorder) -> None:
    for _ in range(2):
        await recorder.report_execution(
            placement_id=PLACEMENT,
            venue_execution_id="SIM-PLC-1:fill:227.41:10:1760360400",
            quantity=Decimal("10"),
            price=usd("227.41"),
        )


async def reports_a_bust(recorder: Recorder) -> None:
    await recorder.report_execution(
        placement_id=PLACEMENT,
        venue_execution_id="SIM-EXE-1-bust",
        quantity=Decimal("0"),
        price=usd("227.41"),
        supersedes="EXE-01JAE00000000000000000001",
    )


async def reports_a_charge(recorder: Recorder) -> None:
    await recorder.report_charge(
        placement_id=PLACEMENT, fee=meridian.Fee(kind="exchange", amount=usd("0.02"))
    )


async def reports_a_value_date_roll(recorder: Recorder) -> None:
    """Contract v23 (W11.25): at the venue's daily cut an open EUR/USD spot
    position rolls to the next value date; the plugin asks the date read for
    it, reports the financing charge, then the roll naming it."""
    rolled_at = 1791925200000000000
    computed = await recorder.compute_date(
        spot=meridian.SpotDateInputs(pair=[EUR, USD], at_ns=rolled_at)
    )
    charged = await recorder.report_charge(
        placement_id=PLACEMENT,
        fee=meridian.Fee(kind="financing", amount=usd("1.37")),
        trade_date=date(2026, 10, 14),
        settlement_date=date(2026, 10, 14),
        raw_record=ops.RawRecordRef(instance_id=VENUE, key="transactions/6311:trades/6290"),
    )
    await recorder.report_value_date_roll(
        venue_account_code=CODE,
        pair=[EUR, USD],
        from_value_date=date(2026, 10, 15),
        to_value_date=computed.date or date(2026, 10, 16),
        value_date_basis=meridian.DateBasis(
            rule=meridian.DateRuleRef(kind="spot", subject="EUR/USD", version=1)
        ),
        rolled_at_ns=rolled_at,
        charge_ids=[charged.charge.charge_id or "CHG-01JAF0R5N8M00000000000021"],
        raw_record=ops.RawRecordRef(instance_id=VENUE, key="transactions/6311"),
        idempotency_key=f"roll:{CODE}:6311",
    )


async def cancels_on_a_stop(recorder: Recorder) -> None:
    await hearing(INSTRUCTION_CHANGED)(recorder)
    await recorder.request_placement_change(
        placement_id=PLACEMENT,
        change=meridian.PlacementChange(kind="cancel"),
        cause=ops.EntryMeta(entry_id="ENT-01JAE00000000000000000077"),
    )


async def publishes_its_catalogue(recorder: Recorder) -> None:
    await recorder.report_venue_catalogue(
        catalogue=meridian.VenueCatalogue(
            connectivity_instance_id=VENUE, venue_account_code=CODE
        )
    )


async def records_a_locate(recorder: Recorder) -> None:
    await recorder.record_locate(
        venue_account_code=CODE,
        instrument_id=AAPL,
        quantity_requested=Decimal("100"),
        raw_record=RAW,
    )


async def resolves_a_symbol_by_the_facts_date(recorder: Recorder) -> None:
    found = await recorder.resolve_identifier(
        identifiers=[meridian.Identifier(scheme="ticker", value="AAPL")], as_of_ns=1760360400
    )
    await recorder.record_locate(
        venue_account_code=CODE,
        instrument_id=found.instrument_id,
        quantity_requested=Decimal("100"),
        raw_record=RAW,
    )


async def reports_a_symbol_it_cannot_resolve(recorder: Recorder) -> None:
    await recorder.report_missing_instrument(
        source="sim",
        identifiers=[meridian.Identifier(scheme="ticker", value="ZZZZ")],
        reason="not_found",
    )


async def resolves_an_executions_venue(recorder: Recorder) -> None:
    found = await recorder.resolve_venue(
        identifiers=[meridian.Identifier(scheme="mic", value="XNAS")], as_of_ns=1
    )
    await recorder.report_execution(
        placement_id=PLACEMENT,
        venue_execution_id="SIM-EXE-2",
        quantity=Decimal("1"),
        price=usd("227.41"),
        venue_id=found.venue.venue_id,
    )


async def reports_a_venue_not_held(recorder: Recorder) -> None:
    await recorder.report_missing_venue(
        source="sim",
        identifiers=[meridian.Identifier(scheme="mic", value="XXXX")],
        reason="not_found",
    )


#: Each case contract v22 adds, by name, as a plugin holding the role does it.
# ── Contract v23: venue-originated fills ────────────────────────────────────

EXECUTION = "EXE-01JAF0R5N8M00000000000011"
VENUE_ORDER = "SIM-ORD-9"
UNMATCHED_HEARD = (
    "ExecutionRecorded",
    "execution_recorded",
    ops.ExecutionRecordedEvent(
        execution=ops.Execution(
            execution_id=EXECUTION,
            account_id=ACCOUNT,
            instrument_id=AAPL,
            side=ops.SIDE_SELL,
            venue_order_id=VENUE_ORDER,
            state=ops.EXECUTION_STATE_UNMATCHED,
        )
    ),
)
ACCEPTED_PLACEMENT = (
    "PlacementUpdated",
    "placement_updated",
    ops.PlacementUpdatedEvent(
        placement=ops.Placement(
            placement_id=PLACEMENT,
            order_id=ORDER,
            connectivity_instance_id=VENUE,
            venue_account_code=CODE,
            venue_order_id=VENUE_ORDER,
        )
    ),
)
ACCEPTED_EXECUTION = (
    "ExecutionRecorded",
    "execution_recorded",
    ops.ExecutionRecordedEvent(
        execution=ops.Execution(
            execution_id=EXECUTION,
            placement_id=PLACEMENT,
            venue_order_id=VENUE_ORDER,
            state=ops.EXECUTION_STATE_MATCHED,
        )
    ),
)
ACCEPTED_ORDER = (
    "OrderUpdated",
    "order_updated",
    ops.OrderUpdatedEvent(
        order=ops.Order(order_id=ORDER, origin=ops.ORDER_ORIGIN_ACCEPTED_EXECUTION)
    ),
)


async def reports_a_fill_on_no_placement(recorder: Recorder) -> None:
    # The venue's fill of an order the platform never placed: no placement,
    # its instrument, side and venue order ID named, the account stamped
    # from the ems's map by the venue account code.
    await recorder.report_execution(
        venue_account_code=CODE,
        instrument_id=AAPL,
        side="sell",
        venue_order_id=VENUE_ORDER,
        venue_execution_id="SIM-EXE-9",
        quantity=Decimal("30"),
        price=usd("227.41"),
        trade_date=date(2026, 10, 9),
        settlement_date=date(2026, 10, 13),
        raw_record=RAW,
    )


async def reports_a_later_fill_on_the_accepted_placement(recorder: Recorder) -> None:
    await hearing(ACCEPTED_PLACEMENT, ACCEPTED_EXECUTION)(recorder)
    (heard,) = recorder.on("PlacementUpdated")
    await recorder.report_execution(
        placement_id=heard.placement.placement_id,
        venue_order_id=heard.placement.venue_order_id,
        venue_execution_id="SIM-EXE-10",
        quantity=Decimal("5"),
        price=usd("227.40"),
        settlement_date=date(2026, 10, 13),
        raw_record=RAW,
    )


async def re_reports_a_charge_on_the_accepted_placement(recorder: Recorder) -> None:
    await hearing(ACCEPTED_PLACEMENT)(recorder)
    (heard,) = recorder.on("PlacementUpdated")
    await recorder.report_charge(
        placement_id=heard.placement.placement_id,
        fee=meridian.Fee(kind="exchange", amount=usd("0.02")),
        raw_record=RAW,
    )


async def accepts_a_fill_to_an_order(recorder: Recorder) -> None:
    await hearing(UNMATCHED_HEARD)(recorder)
    (heard,) = recorder.on("ExecutionRecorded")
    await recorder.accept_execution(
        execution_ids=[heard.execution.execution_id],
        order_id=ORDER,
        note="Ours: the client's working order",
        acting_for=caller_header("write"),
    )


async def accepts_a_fill_to_a_new_order(recorder: Recorder) -> None:
    await hearing(UNMATCHED_HEARD)(recorder)
    (heard,) = recorder.on("ExecutionRecorded")
    await recorder.accept_execution(
        execution_ids=[heard.execution.execution_id],
        new_order=ops.NewOrderFromExecutions(
            sleeve="core", note="Sold in the broker's app on Monday"
        ),
        note="Confirmed with the client by phone",
        acting_for=caller_header("write"),
    )


async def answers_a_fill_dk(recorder: Recorder) -> None:
    await hearing(UNMATCHED_HEARD)(recorder)
    (heard,) = recorder.on("ExecutionRecorded")
    await recorder.dont_know_execution(
        execution_ids=[heard.execution.execution_id],
        reason="unknown_instrument",
        acting_for=caller_header("write"),
    )


async def accepts_past_ordered_to_a_new_order(recorder: Recorder) -> None:
    # The accept to the working order was refused for its quantity; the
    # trader accepts the fill to a new order instead.
    await recorder.accept_execution(
        execution_ids=[EXECUTION],
        new_order=ops.NewOrderFromExecutions(note="Past the working order's quantity"),
        acting_for=caller_header("write"),
    )


async def names_an_unmatched_fill_as_a_breaks_cause(recorder: Recorder) -> None:
    await recorder.list_orders(account_id=ACCOUNT, execution_state="unmatched")
    await recorder.record_break(
        account_id=ACCOUNT,
        position=meridian.PositionKey(instrument_id=AAPL, side="long"),
        category="trade_date_quantity",
        differences=[
            meridian.BreakDifference(
                field="trade_date_quantity",
                book=meridian.BreakValue(quantity=Decimal("100")),
                street=meridian.BreakValue(quantity=Decimal("70")),
            )
        ],
        business_date="2026-10-09",
        candidate_causes=[
            meridian.BreakCause(
                category="unbooked_trade",
                book_entry=ops.JournalRef(partition="P0", sequence=60),
            )
        ],
        idempotency_key="break:ACC-1:STMT-9:AAPL",
    )


async def hears_an_order_created_at_accept(recorder: Recorder) -> None:
    await hearing(ACCEPTED_ORDER, ACCEPTED_EXECUTION)(recorder)
    (heard,) = recorder.on("OrderUpdated")
    await recorder.record_check(
        order_id=heard.order.order_id, rule="restricted-list", verdict="warn"
    )


# ── Contract v23: an event contract's outcome, heard and read ───────────────

EVENT_CONTRACT = "INS-01JB00000000000000KXFED1"
OUTCOME_HEARD = (
    "OutcomesRecorded",
    "outcomes_recorded",
    ops.OutcomesRecordedEvent(
        outcome=ops.Outcome(
            meta=ops.ObservationMeta(
                row_key="KXFEDDECISION-26OCT-H0:outcome",
                subjects=[ops.SubjectRef(entity_id=EVENT_CONTRACT)],
            ),
            determination=ops.OUTCOME_DETERMINATION_PAYS,
            stage=ops.OUTCOME_STAGE_DETERMINED,
        )
    ),
)


async def hears_and_reads_an_outcome(recorder: Recorder) -> None:
    await hearing(OUTCOME_HEARD)(recorder)
    await recorder.list_outcomes(subjects=[ops.SubjectRef(entity_id=EVENT_CONTRACT)])


PRODUCERS: dict[str, Producer] = {
    # Every role's settlement calendar reads.
    "reads-a-calendar": reads_a_calendar,
    "asks-for-a-settlement-date": asks_for_a_settlement_date,
    # Reading and hearing the order path.
    "reads-orders-and-catches-up": reads_orders_and_catches_up,
    "reads-its-orders-and-catches-up": reads_orders_and_catches_up,
    "reads-an-orders-history": reads_an_orders_history,
    "reads-an-orders-history-for-the-person-roles": reads_an_orders_history,
    "reads-the-orders-and-an-orders-history": then(
        reads_orders_and_catches_up, reads_an_orders_history
    ),
    "reads-orders-and-an-orders-history": then(
        reads_orders_and_catches_up, reads_an_orders_history
    ),
    "hears-an-order-and-an-execution": hearing(ORDER_UPDATED, EXECUTION_RECORDED),
    "hears-its-order-and-its-fills": hearing(ORDER_UPDATED, EXECUTION_RECORDED),
    "hears-a-placement-and-an-execution": hearing(PLACEMENT_UPDATED, EXECUTION_RECORDED),
    "hears-an-unplaced-fact": hearing(
        ("UnplacedFactRecorded", "unplaced_fact_recorded", ops.UnplacedFactRecordedEvent())
    ),
    "hears-a-locate-answered": hearing(LOCATE_UPDATED),
    "reads-and-hears-the-locates": then(reads_the_locates, hearing(LOCATE_UPDATED)),
    "reads-and-hears-the-trading-instructions": then(
        reads_the_instructions, hearing(INSTRUCTION_CHANGED)
    ),
    "reads-and-hears-whether-releases-wait-for-compliance": then(
        reads_the_attributes, hearing(ATTRIBUTE_CHANGED)
    ),
    "hears-and-reads-a-venues-catalogue": then(hearing(CATALOGUE_HEARD), reads_the_catalogue),
    # portfolio and the oms.
    "proposes-an-order": proposes_an_order,
    "proposes-an-order-for-an-amount": proposes_an_order_for_an_amount,
    "withdraws-a-proposed-order": withdraws,
    "releases-a-proposed-order": then(hearing(ORDER_UPDATED), releases),
    "rejects-an-order-asked-to-work": rejects,
    "holds-an-order": holds,
    "asks-to-amend-an-orders-limit": amends_the_limit,
    "asks-to-cancel-a-placement": cancels_a_placement,
    "records-a-telephoned-order-for-a-person": records_a_telephoned_order,
    "enters-a-done-away-execution-for-a-person": enters_a_done_away_execution,
    "acknowledges-a-late-fact-for-a-person": acknowledges_a_late_fact,
    "gives-back-a-locate-on-a-cancel": uses_the_locate("give_back"),
    # compliance.
    "checks-a-proposed-order": then(hearing(ORDER_UPDATED), checks_a_proposed_order),
    "checks-a-placement-before-it-is-sent": then(
        hearing(PLACEMENT_UPDATED), checks_a_placement
    ),
    "checks-after-a-fill": then(hearing(EXECUTION_RECORDED), checks_after_a_fill),
    "requires-approval-by-policy": requires_approval,
    "overrides-a-block-for-a-person-with-a-reason": overrides_a_block,
    "checks-and-reserves-the-locate-a-short-names": uses_the_locate("reserve"),
    # the ems.
    "maps-an-account-to-a-venue-account-code": maps_an_account,
    "claims-a-released-order": then(hearing(ORDER_UPDATED), claims),
    "places-at-a-linked-connectivity-plugin": places,
    "proposes-a-child-order": proposes_a_child_order,
    "cancels-a-placement": cancels_a_placement,
    "asks-to-cancel-an-order": cancels_the_order,
    "enters-a-manual-execution-for-a-person": enters_a_manual_execution,
    # operations.
    "re-checks-a-pending-value-date": re_checks_a_value_date,
    # a connectivity plugin.
    "acknowledges-a-placement-naming-it": acknowledges_its_placement,
    "hears-no-placement-of-another-instance": hears_nothing_of_another_instance,
    "sends-the-venue-account-code-its-ems-set": reports(event="acknowledged"),
    "rejects-what-the-venue-does-not-offer": reports(
        event="rejected", rejection_reason="unsupported", raw_record=RAW
    ),
    "rejects-a-strategy-its-broker-lacks": reports(
        event="rejected", rejection_reason="unsupported", raw_record=RAW
    ),
    "venue-rejected-with-its-reason-as-reported": reports(
        event="rejected",
        rejection_reason="venue_rejected",
        rejection_as_reported=ops.AsReported(
            scheme="sim", code="ACCOUNT_RESTRICTED", text="Account restricted"
        ),
        raw_record=RAW,
    ),
    "unmapped-status-is-outcome-unknown": reports(
        event="outcome_unknown",
        unknown_reason="venue_status_not_mapped",
        status_as_reported=ops.AsReported(scheme="sim", code="PENDING_REVIEW"),
        raw_record=RAW,
    ),
    "resolves-an-unanswered-send-by-asking": reports(event="acknowledged", raw_record=RAW),
    "reports-a-fill-with-its-settlement-date": fills_with_its_settlement_date,
    "derives-the-same-execution-id-twice": derives_one_id_twice,
    "reports-a-bust": reports_a_bust,
    "reports-a-charge": reports_a_charge,
    "sends-nothing-new-on-a-pause": sends_nothing_on_a_pause,
    "cancels-at-the-venue-on-a-stop": cancels_on_a_stop,
    "publishes-its-catalogue": publishes_its_catalogue,
    "reads-the-instrument-it-places": lambda recorder: recorder.resolve_instrument(
        instrument_id=AAPL
    ),
    "reads-its-placements-orders-on-start": lambda recorder: recorder.list_orders(),
    "catches-up-placements-after-a-loss": lambda recorder: recorder.list_orders(since=AFTER),
    "reads-the-instructions-in-force-on-start": reads_the_instructions,
    "reads-whether-releases-wait-for-compliance": reads_the_attributes,
    "hears-an-accounts-attributes-change": hearing(ATTRIBUTE_CHANGED),
    "records-a-locate": records_a_locate,
    "resolves-a-venue-symbol-by-the-facts-date": resolves_a_symbol_by_the_facts_date,
    "reports-a-symbol-it-cannot-resolve": reports_a_symbol_it_cannot_resolve,
    "resolves-an-executions-venue": resolves_an_executions_venue,
    "reports-a-venue-not-held": reports_a_venue_not_held,
    # Contract v23: venue-originated fills.
    "reports-a-fill-on-no-placement": reports_a_fill_on_no_placement,
    "reports-a-later-fill-on-the-accepted-placement": (
        reports_a_later_fill_on_the_accepted_placement
    ),
    "re-reports-a-charge-on-the-accepted-placement": (
        re_reports_a_charge_on_the_accepted_placement
    ),
    "accepts-a-fill-to-an-order": accepts_a_fill_to_an_order,
    "accepts-a-fill-to-a-new-order": accepts_a_fill_to_a_new_order,
    "answers-a-fill-dk-with-a-reason": answers_a_fill_dk,
    "accept-past-ordered-refused": accepts_past_ordered_to_a_new_order,
    "names-an-unmatched-fill-as-a-breaks-cause": names_an_unmatched_fill_as_a_breaks_cause,
    "hears-an-order-created-at-accept": hears_an_order_created_at_accept,
    # Contract v23: a venue's value-date roll (the OANDA batch's item 1).
    "reports-a-value-date-roll": reports_a_value_date_roll,
    # Contract v23: an event contract's outcome, for every reader of it.
    "hears-and-reads-an-outcome": hears_and_reads_an_outcome,
}
