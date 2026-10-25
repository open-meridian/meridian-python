"""Listed options' and futures' lifecycle in the book (contract v28,
sdk-contract/listed-options-and-futures-contract; ruling 563; W9.16 to
W9.18).

An exercise, an assignment, an expiry and a future's day of variation are
each their own record (decisions/031), as the broker states them:

- **`custody` or `connectivity` reports** what its broker states
  (`RecordLifecycleEvent`; `report`), once per report -- its idempotency key
  is the instance and the broker's own ID for it -- each built by its kind:
  `expiry` (the option's lots closed at nothing), `assignment` and
  `exercise` (the deliverable moved at the strike, with the cash, or cash
  alone on cash settlement), `variation` (a day's cash against the
  settlement price; the lot keeps its trade price, ruling 562);
- **`servicing` proposes** what it expects at expiration
  (`ProposeLifecycleEvents`): `exercise_by_exception` answers whether a long
  option expires in the money by more than the OCC's threshold ($0.01 by
  default) against the underlying's close, and builds the proposed
  exercise with its `proposal_basis`; a broker's report later answers the
  proposal, and a difference is a break;
- **`operations` releases** a proposed event no report answered
  (`ReleaseLifecycleEvent`, with a note), only once the morning after has
  passed and the statement no longer shows the position (`due_for_release`);
- **a reader** (`operations`, `servicing`, `portfolio`, `reporting`) reads
  an account's events for a range of dates (`read_events`) and hears each
  one recorded (`LifecycleEventRecorded`).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from ..operations import LifecycleDelivery, LifecycleEvent, Money
from ..plugin.v1 import operations_pb2 as ops

#: The OCC's exercise-by-exception threshold: in the money by this or more.
EXERCISE_THRESHOLD = Decimal("0.01")


def expiry(
    account_id: str,
    instrument_id: str,
    quantity: Decimal | int,
    event_date: date | str,
    *,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """An option expired worthless: its lots closed at nothing."""
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind="expiry",
        quantity=quantity, event_date=event_date, external_event_id=external_event_id,
        raw_record=raw_record,
    )  # fmt: skip


def _delivered(
    kind: str,
    account_id: str,
    instrument_id: str,
    quantity: Decimal | int,
    event_date: date | str,
    deliveries: Sequence[tuple[str, Decimal | int, Money | None]],
    cash: Money | None,
    settlement_price: Money | None,
    external_event_id: str,
    raw_record: ops.RawRecordRef | None,
) -> LifecycleEvent:
    return LifecycleEvent(
        account_id=account_id,
        instrument_id=instrument_id,
        kind=kind,
        quantity=quantity,
        event_date=event_date,
        deliveries=[
            LifecycleDelivery(instrument_id=i, quantity=q, price=p) for i, q, p in deliveries
        ],
        cash=cash,
        settlement_price=settlement_price,
        external_event_id=external_event_id,
        raw_record=raw_record,
    )


def assignment(
    account_id: str,
    instrument_id: str,
    quantity: Decimal | int,
    event_date: date | str,
    *,
    deliveries: Sequence[tuple[str, Decimal | int, Money | None]] = (),
    cash: Money | None = None,
    settlement_price: Money | None = None,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """A short option assigned: each delivery an instrument, its signed
    quantity (shares delivered negative) and the price it moved at (the
    strike), with the cash received, positive; or, cash-settled, the cash
    and the settlement value alone."""
    return _delivered(
        "assignment", account_id, instrument_id, quantity, event_date, deliveries, cash,
        settlement_price, external_event_id, raw_record,
    )  # fmt: skip


def exercise(
    account_id: str,
    instrument_id: str,
    quantity: Decimal | int,
    event_date: date | str,
    *,
    deliveries: Sequence[tuple[str, Decimal | int, Money | None]] = (),
    cash: Money | None = None,
    settlement_price: Money | None = None,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """A long option exercised, as `assignment` is built: shares received
    positive, the cash paid negative."""
    return _delivered(
        "exercise", account_id, instrument_id, quantity, event_date, deliveries, cash,
        settlement_price, external_event_id, raw_record,
    )  # fmt: skip


def variation(
    account_id: str,
    instrument_id: str,
    contracts: Decimal | int,
    trading_date: date | str,
    cash: Money,
    settlement_price: Money,
    *,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """A future's day of variation: the contracts held at the settlement,
    the cash signed (positive received) and the exchange's settlement
    price."""
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind="settlement_variation",
        quantity=contracts, event_date=trading_date, cash=cash,
        settlement_price=settlement_price, external_event_id=external_event_id,
        raw_record=raw_record,
    )  # fmt: skip


async def report(plugin: Any, event: LifecycleEvent, *, acting_for: str | None = None) -> Any:
    """Record an event as the broker stated it, applied once: its key is the
    plugin's instance and the broker's own ID for the event (the raw
    record's key where the broker gives none)."""
    own = event.external_event_id or (event.raw_record.key if event.raw_record else "")
    if not own:
        raise ValueError("a reported lifecycle event names the broker's ID or its raw record")
    key = f"{plugin.identity.instance_id}:{own}"
    return await plugin.record_lifecycle_event(
        event=event, idempotency_key=key[:128], acting_for=acting_for
    )


# ── servicing: what to expect ────────────────────────────────────────────


def in_the_money(put_or_call: str, strike: Decimal, close: Decimal) -> Decimal:
    """How far an option is in the money against the underlying's close:
    a call's close less its strike, a put's strike less the close; negative
    out of the money."""
    right = put_or_call.lower()
    if right in ("call", "c", "put_or_call_call"):
        return close - strike
    if right in ("put", "p", "put_or_call_put"):
        return strike - close
    raise ValueError(f"put_or_call is {put_or_call!r}: call or put")


def exercise_by_exception(
    account_id: str,
    instrument_id: str,
    contracts: Decimal | int,
    expiration: date | str,
    *,
    put_or_call: str,
    strike: Money,
    close: Money,
    underlying_id: str,
    multiplier: Decimal | int = 100,
    threshold: Decimal = EXERCISE_THRESHOLD,
) -> LifecycleEvent | None:
    """The exercise a long option's holder can expect at expiration where it
    is in the money by `threshold` or more against the underlying's close
    (OCC's exercise by exception), its proposal basis that close; None
    otherwise. Physically settled: shares received at the strike for a
    call (delivered for a put), the cash paid (received)."""
    held = Decimal(contracts)
    if held <= 0:
        return None
    strike_amount, close_amount = Decimal(strike.amount), Decimal(close.amount)
    if in_the_money(put_or_call, strike_amount, close_amount) < threshold:
        return None
    shares = held * Decimal(multiplier)
    call = put_or_call.lower() in ("call", "c", "put_or_call_call")
    signed = shares if call else -shares
    cash = -signed * strike_amount
    return LifecycleEvent(
        account_id=account_id,
        instrument_id=instrument_id,
        kind="exercise",
        quantity=held,
        event_date=expiration,
        deliveries=[
            LifecycleDelivery(instrument_id=underlying_id, quantity=signed, price=strike)
        ],
        cash=Money(cash, strike.currency_code) if strike.currency_code else None,
        proposal_basis=close,
    )


async def propose(
    plugin: Any, events: Sequence[LifecycleEvent], *, acting_for: str | None = None
) -> Any:
    """Propose the expected events, each in its account, recorded as
    proposed; nothing sent where there are none."""
    if not events:
        return None
    return await plugin.propose_lifecycle_events(events=list(events), acting_for=acting_for)


# ── operations: a proposal no report answered ────────────────────────────


def due_for_release(
    event: Any, *, now: datetime, reported: bool, still_held: bool, zone: Any = None
) -> bool:
    """Whether `operations` may release a proposed event: unanswered by any
    report by the morning after its date (09:00 in `zone`, the account's
    market's) and its position gone from the statement."""
    if reported or still_held:
        return False
    if int(getattr(event, "state", 0) or 0) not in (0, ops.LIFECYCLE_EVENT_STATE_PROPOSED):
        return False
    day = event.event_date
    held = date.fromisoformat(day) if isinstance(day, str) else day
    morning = datetime.combine(date.fromordinal(held.toordinal() + 1), time(9), tzinfo=zone)
    return now >= morning if morning.tzinfo else now.replace(tzinfo=None) >= morning


async def release(
    plugin: Any, event_id: str, note: str, *, acting_for: str | None = None
) -> Any:
    """Release a proposal no report answered, with the note kept on its
    entry (decisions/031)."""
    if not note.strip():
        raise ValueError("a release carries a note")
    return await plugin.release_lifecycle_event(
        event_id=event_id, note=note, acting_for=acting_for
    )


# ── Reading ──────────────────────────────────────────────────────────────


async def read_events(
    plugin: Any,
    account_id: str,
    from_date: date | str,
    to_date: date | str,
    *,
    kinds: Sequence[str] = (),
) -> list[ops.LifecycleEvent]:
    """An account's lifecycle events dated in the range, every page read."""
    rows: list[ops.LifecycleEvent] = []
    cursor = ""
    while True:
        page = await plugin.list_lifecycle_events(
            account_id=account_id, from_date=from_date, to_date=to_date, kinds=list(kinds),
            cursor=cursor,
        )  # fmt: skip
        rows.extend(page.events)
        cursor = page.next_cursor
        if not cursor:
            return rows
