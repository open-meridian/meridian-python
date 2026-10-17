"""A connectivity plugin's tests on the SDK's `Trader` (0.30.0): the book's
messages as a test builds them, and a rig running the plugin's own adapter
and fake broker against the suites' `Recorder`, which stands in for the
sidecar alone. A plugin subclasses `Rig`, building its venue in `connect`:

    class Rig(testing.Rig):
        instance, code, source = "tradier", ACCOUNT_NUMBER, "tradier"

        def connect(self, broker):
            self.brokerage = broker or SyntheticBroker(clock)
            return TradierVenue(Broker(..., send=self.brokerage))

FAKES ONLY: a rig's venue is the plugin's adapter over a simulated broker,
never a real one, and never with a token.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, tzinfo
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from ...client import AccountScope, VenueAccountMap, VenueAccountMapping
from ...plugin.v1 import operations_pb2 as ops
from ...suites import Recorder
from ._bookkeeping import Sent
from ._trader import Trader, Venue, Watched

__all__ = [
    "ACCOUNT",
    "CALENDAR",
    "INSTRUMENT",
    "NOW",
    "Rig",
    "asking",
    "clock",
    "decimal",
    "instrument",
    "money",
    "order_of",
    "placement",
    "scope",
    "settled",
]

Producer = Callable[[Recorder], Awaitable[None]]

ACCOUNT = "ACC-01JAE000000000000000000001"
INSTRUMENT = "INS-01J8XQ4M7K0000000000AAPL"
CALENDAR = "CAL-01JAE0000000000000000USSS"
NOW = datetime(2026, 9, 29, 14, 30, tzinfo=UTC)


def clock() -> datetime:
    return NOW


def decimal(text: str) -> ops.Decimal:
    """A decimal's text as the wire's Decimal."""
    exact = Decimal(text)
    scale = max(0, -int(exact.as_tuple().exponent))
    units = int(exact.scaleb(scale))
    return ops.Decimal(high=units >> 64, low=units & ((1 << 64) - 1), scale=scale)


def money(text: str, currency: str = "USD") -> ops.Money:
    return ops.Money(amount=decimal(text), currency_code=currency)


def placement(
    pid: str = "PLC-01JAE00000000000000000001",
    *,
    instance: str,
    code: str,
    quantity: str = "10",
    tif: ops.TimeInForce = ops.TIME_IN_FORCE_DAY,
    state: ops.PlacementState = ops.PLACEMENT_STATE_QUEUED,
    strategy: ops.StrategyInstruction | None = None,
    venue_order_id: str = "",
    limit: str = "230.00",
) -> ops.Placement:
    """A placement as the book delivers it to the connectivity plugin
    `instance`, in the account its `ems` mapped to `code`."""
    held = ops.Placement(
        placement_id=pid,
        order_id="ORD-" + pid[4:],
        account_id=ACCOUNT,
        ems_instance_id="desk",
        connectivity_instance_id=instance,
        venue_account_code=code,
        quantity=decimal(quantity),
        limit_price=money(limit),
        time_in_force=tif,
        status=ops.PlacementStatus(state=state),
        venue_order_id=venue_order_id,
    )
    if strategy is not None:
        held.strategy.CopyFrom(strategy)
    return held


def asking(
    held: ops.Placement,
    kind: ops.PlacementChangeKind,
    crq: str = "CRQ-01JAE00000000000000000001",
    **change: Any,
) -> ops.Placement:
    """The placement as the book delivers it with a change requested."""
    asked = ops.Placement()
    asked.CopyFrom(held)
    asked.change_requests.append(
        ops.ChangeRequest(
            change_request_id=crq,
            order_id=held.order_id,
            placement_id=held.placement_id,
            placement_change=ops.PlacementChange(kind=kind, **change),
            outcome=ops.CHANGE_REQUEST_OUTCOME_PENDING,
        )
    )
    return asked


def scope(*codes: str, instance: str) -> AccountScope:
    """The account scope with the `ems`'s map naming `codes` on `instance`."""
    return AccountScope(
        venue_account_map=VenueAccountMap(
            ems_instance_id="desk",
            mappings=tuple(VenueAccountMapping(instance, code, ACCOUNT) for code in codes),
        )
    )


def order_of(held: ops.Placement, **changes: Any) -> ops.Order:
    """The order a placement works, as ListOrders answers it."""
    order = ops.Order(
        order_id=held.order_id,
        account_id=ACCOUNT,
        instrument_id=changes.pop("instrument_id", INSTRUMENT),
        side=changes.pop("side", ops.SIDE_BUY),
        quantity=held.quantity,
        order_type=changes.pop("order_type", ops.ORDER_TYPE_LIMIT),
        limit_price=held.limit_price,
        time_in_force=changes.pop("time_in_force", held.time_in_force),
    )
    order.placements.append(held)
    return order


def instrument(symbol: str, source: str, currency: str = "USD") -> ops.InstrumentRecord:
    """The instrument's record, holding the symbol the venue names it by."""
    return ops.InstrumentRecord(
        instrument_id=INSTRUMENT,
        currency=currency,
        identifiers=[ops.Identifier(scheme="symbol", value=symbol, source=source)],
    )


def settled() -> ops.ComputeDateResult:
    """The date read's answer for a fill: a settlement date and its basis."""
    return ops.ComputeDateResult(
        date="2026-09-30",
        outcome=ops.DATE_OUTCOME_COMPUTED,
        basis=ops.DateBasis(
            rule=ops.DateRuleRef(subject="XNAS", version=1),
            calendars=[ops.CalendarRef(calendar_id=CALENDAR, version=3)],
        ),
        business_day=True,
    )


class Rig:
    """A `Trader` over the recorder and the plugin's own venue on a fake
    broker (`connect`), trading enabled on its account; the book's answers
    (ListOrders, ResolveInstrument, ComputeDate, ReportExecution) as the
    recorder gives them. `after_poll` is where a venue streaming its trade
    updates delivers what a poll's steps made."""

    #: The plugin's instance, the venue account code its fake broker holds,
    #: and the source its symbols are named by.
    instance = "connectivity"
    code = "CODE-1"
    source = "venue"
    #: The listing market's zone (US equities).
    market_zone: tzinfo = ZoneInfo("America/New_York")

    def __init__(
        self,
        recorder: Recorder,
        symbol: str = "AAPL",
        sent: Sent | None = None,
        mapped: tuple[str, ...] | None = None,
        enabled: bool = True,
        broker: Any = None,
    ) -> None:
        self.recorder = recorder
        self.sent = sent
        self.scope = scope(
            *(mapped if mapped is not None else (self.code,)), instance=self.instance
        )
        self.venue = self.connect(broker)
        self.enabled = Sent(None)
        self.watched = Watched(None)
        if enabled:
            self.enabled.note(self.code)
        self.orders: list[ops.Order] = []
        self.executions: list[ops.Execution] = []
        self.minted = 0
        recorder.answer("ListOrders", self._listed)
        recorder.answer(
            "ResolveInstrument",
            lambda _: ops.ResolveInstrumentResult(
                found=True, instrument=instrument(symbol, self.source)
            ),
        )
        recorder.answer("ComputeDate", lambda _: settled())
        recorder.answer("ReportExecution", self._executed)
        self.trader = self.make()

    def connect(self, broker: Any) -> Venue:
        """The plugin's venue adapter over its fake broker (`broker`, where a
        test hands one in)."""
        raise NotImplementedError

    async def after_poll(self) -> None:
        """What a venue streaming its trade updates delivers after a poll."""
        return None

    def make(self) -> Trader:
        trader = Trader(
            self.recorder,
            lambda: self.venue,
            now=clock,
            sent=self.sent,
            enabled=self.enabled,
            scope=lambda: self.scope,
            watched=self.watched,
            market_zone=self.market_zone,
        )
        # As a running plugin's, past its start.
        trader.started.set()
        return trader

    def placement(self, pid: str = "PLC-01JAE00000000000000000001", **kw: Any) -> ops.Placement:
        """A placement to this rig's instance, in its account."""
        kw.setdefault("instance", self.instance)
        kw.setdefault("code", self.code)
        return placement(pid, **kw)

    def _listed(self, _: Any) -> ops.ListOrdersResult:
        return ops.ListOrdersResult(
            orders=self.orders,
            executions=self.executions,
            as_of=ops.Watermark(
                partitions=[ops.PartitionSequence(partition="book", sequence=7)]
            ),
        )

    def _executed(self, params: Any) -> ops.ReportExecutionResult:
        self.minted += 1
        held = ops.Execution(
            execution_id=f"EXE-{self.minted}",
            placement_id=params.placement_id,
            venue_order_id=params.venue_order_id,
            venue_execution_id=params.venue_execution_id,
            quantity=params.quantity,
            supersedes=params.supersedes,
        )
        self.executions.append(held)
        return ops.ReportExecutionResult(execution=held)

    def holds(self, *placements: ops.Placement, **changes: Any) -> None:
        """The book holds these placements' orders."""
        self.orders = [order_of(each, **changes) for each in placements]

    async def hear(self, *placements: ops.Placement) -> None:
        """The book delivers these placements, heard by the Trader."""
        self.recorder.answer(
            "PlacementUpdated",
            lambda _: [ops.PlacementUpdatedEvent(placement=each) for each in placements],
        )
        await self.recorder.receive(placement_updated=self.trader.on_placement)

    async def instruct(self, value: ops.TradingInstructionValue, *, instance: str = "") -> None:
        """A trading instruction on this instance (or `instance`), heard."""
        instruction = ops.TradingInstruction(
            target=ops.TradingInstructionTarget(instance_id=instance or self.instance),
            value=value,
            entry=ops.EntryMeta(entry_id="ENT-stop-1"),
        )
        self.recorder.answer(
            "TradingInstructionChanged",
            lambda _: ops.TradingInstructionChangedEvent(instruction=instruction),
        )
        await self.recorder.receive(trading_instruction_changed=self.trader.on_instruction)

    async def poll(self, times: int = 1) -> None:
        """The Trader's reads of the orders, each followed by `after_poll`."""
        for _ in range(times):
            await self.trader.poll()
            await self.after_poll()
