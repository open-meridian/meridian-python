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
  one recorded (`LifecycleEventRecorded`); from contract v29 (740) a read
  naming no account answers every account in the reader's scope.

**Fixed income** (contract v29, sdk-contract/fixed-income-contract; rulings
680 to 683, 988 and 991 to 993; W9.16 to W9.18). Seven more records on a
debt record, `quantity` its face, each reported as the custodian states it:
`coupon_received` (its cash, the period and record date; the book books it
as two cash lines, the purchased accrued returned and the income, 988),
`redemption` (maturity, a full or partial call, a put or a sinking-fund
draw at its price per 100), `paydown` (a pool's or a tranche's principal,
the factors it fell between), `accretion` (a Z class's face, an IO's
notional; no cash), `tba_allocation` (the TBA's lots closed and each pool
delivered opened in original face), `strip` and `reconstitution`.
`servicing` proposes the flows it can expect from the terms and the lake
(W9.17): each coupon on its payment date from the face held at the record
date (`expected_coupon`), each maturity (`expected_maturity`) and each
paydown or accretion from the agency's published factors
(`expected_paydown`) -- never a partial call, a put, a TBA allocation, a
strip or a reconstitution, which only a report states. The book's own
factor revision (992) is never reported or proposed; one still owed after
settlement (`LIFECYCLE_EVENT_STATE_CLAIM_OPEN`, `debt.open_claims`) is
marked settled by a person through `operations` (`settle_claim`).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time
from decimal import Decimal
from fractions import Fraction
from typing import Any

from ..operations import LifecycleDelivery, LifecycleEvent, Money
from ..plugin.v1 import operations_pb2 as ops
from . import debt

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


async def report(role: Any, event: LifecycleEvent, *, acting_for: str | None = None) -> Any:
    """Record an event as the broker stated it, applied once: its key is the
    plugin's instance and the broker's own ID for the event (the raw
    record's key where the broker gives none)."""
    own = event.external_event_id or (event.raw_record.key if event.raw_record else "")
    if not own:
        raise ValueError("a reported lifecycle event names the broker's ID or its raw record")
    key = f"{role.plugin.identity.instance_id}:{own}"
    return await role.record_lifecycle_event(
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
    role: Any, events: Sequence[LifecycleEvent], *, acting_for: str | None = None
) -> Any:
    """Propose the expected events, each in its account, recorded as
    proposed; nothing sent where there are none."""
    if not events:
        return None
    return await role.propose_lifecycle_events(events=list(events), acting_for=acting_for)


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


async def release(role: Any, event_id: str, note: str, *, acting_for: str | None = None) -> Any:
    """Release a proposal no report answered, with the note kept on its
    entry (decisions/031)."""
    if not note.strip():
        raise ValueError("a release carries a note")
    return await role.release_lifecycle_event(
        event_id=event_id, note=note, acting_for=acting_for
    )


# ── Reading ──────────────────────────────────────────────────────────────


async def read_events(
    role: Any,
    account_id: str,
    from_date: date | str,
    to_date: date | str,
    *,
    kinds: Sequence[str] = (),
) -> list[ops.LifecycleEvent]:
    """An account's lifecycle events dated in the range, every page read;
    from contract v29 (740) `account_id` empty reads every account in the
    reader's scope, each event naming its account."""
    rows: list[ops.LifecycleEvent] = []
    cursor = ""
    while True:
        page = await role.list_lifecycle_events(
            account_id=account_id, from_date=from_date, to_date=to_date, kinds=list(kinds),
            cursor=cursor,
        )  # fmt: skip
        rows.extend(page.events)
        cursor = page.next_cursor
        if not cursor:
            return rows


# ── Fixed income: what a custodian reports (contract v29) ───────────────


def coupon_received(
    account_id: str,
    instrument_id: str,
    face: Decimal | int,
    payment_date: date | str,
    cash: Money,
    *,
    period_start: date | str,
    period_end: date | str,
    record_date: date | str = "",
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """A coupon received on a debt record as the custodian states it: the
    face it was paid on, its cash (the whole coupon; the book books the
    purchased accrued returned apart from the income, 988 -- add back a
    custodian's purchased accrued line with `debt.coupon_split`), its
    period and record date."""
    if Decimal(cash.amount) <= 0:
        raise ValueError(f"a coupon received is cash received, not {cash.amount}")
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind="coupon_received",
        quantity=face, event_date=payment_date, cash=cash, period_start_date=period_start,
        period_end_date=period_end, record_date=record_date,
        external_event_id=external_event_id, raw_record=raw_record,
    )  # fmt: skip


def redemption(
    account_id: str,
    instrument_id: str,
    face: Decimal | int,
    event_date: date | str,
    kind: ops.RedemptionEventKind | str,
    price_per100: Decimal | int,
    *,
    cash: Money | None = None,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """A redemption -- `maturity`, `full_call`, `partial_call`, `put` or
    `sinking_fund` -- of the face redeemed at its price per 100 of face, its
    cash as stated; where none is stated the book takes face times the price
    times 0.01 (W9.16)."""
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind="redemption",
        quantity=face, event_date=event_date, redemption_kind=kind,
        redemption_price=price_per100, cash=cash, external_event_id=external_event_id,
        raw_record=raw_record,
    )  # fmt: skip


def paydown(
    account_id: str,
    instrument_id: str,
    original_face: Decimal | int,
    event_date: date | str,
    prior_factor: Decimal | int | str,
    factor: Decimal | int | str,
    cash: Money,
    *,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """A pool's or a tranche's principal returned, as the custodian states
    it: the original face held (the lots keep it, 680), the factors it fell
    between and the cash, the factor's fall times original face."""
    prior, now = Decimal(prior_factor), Decimal(factor)
    if now >= prior:
        raise ValueError(f"a paydown's factor falls: {prior} to {now} is an accretion")
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind="paydown",
        quantity=original_face, event_date=event_date, prior_factor=prior, factor=now,
        cash=cash, external_event_id=external_event_id, raw_record=raw_record,
    )  # fmt: skip


def accretion(
    account_id: str,
    instrument_id: str,
    original_face: Decimal | int,
    event_date: date | str,
    prior_factor: Decimal | int | str,
    factor: Decimal | int | str,
    *,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """A Z class's face increase, or an IO's notional fall: the factors
    beside it and the face change, signed, original face times their
    difference; no cash, and no lot changes (the factor carries the face)."""
    prior, now = Decimal(prior_factor), Decimal(factor)
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind="accretion",
        quantity=original_face, event_date=event_date, prior_factor=prior, factor=now,
        face_change=(now - prior) * Decimal(original_face),
        external_event_id=external_event_id, raw_record=raw_record,
    )  # fmt: skip


def _exchanged(
    kind: str,
    account_id: str,
    instrument_id: str,
    face: Decimal | int,
    event_date: date | str,
    deliveries: Sequence[tuple[str, Decimal | int, Money | None]],
    external_event_id: str,
    raw_record: ops.RawRecordRef | None,
) -> LifecycleEvent:
    if not deliveries:
        raise ValueError(f"a {kind.replace('_', ' ')} names what it delivered")
    if len(deliveries) > 512:
        raise ValueError(f"a {kind.replace('_', ' ')} names at most 512 deliveries")
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind=kind, quantity=face,
        event_date=event_date,
        deliveries=[
            LifecycleDelivery(instrument_id=i, quantity=q, price=p) for i, q, p in deliveries
        ],
        external_event_id=external_event_id, raw_record=raw_record,
    )  # fmt: skip


def tba_allocation(
    account_id: str,
    tba_id: str,
    face: Decimal | int,
    event_date: date | str,
    pools: Sequence[tuple[str, Decimal | int, Money | None]],
    *,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """A TBA's allocation at the 48-hour pool notice (681): its lots closed
    and each pool delivered -- its record, its original face and its price
    -- opened, the TBA's cost carried to them by face. A delivery outside
    SIFMA's variance is recorded as reported, a break, never refused."""
    return _exchanged(
        "tba_allocation", account_id, tba_id, face, event_date, pools, external_event_id,
        raw_record,
    )  # fmt: skip


def strip(
    account_id: str,
    bond_id: str,
    face: Decimal | int,
    event_date: date | str,
    components: Sequence[tuple[str, Decimal | int, Money | None]],
    *,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """A whole bond exchanged for its STRIPS components (each `TINT` or
    `TPRN` record `stripped_from` it, its face and price), the basis
    allocated by relative value."""
    return _exchanged(
        "strip", account_id, bond_id, face, event_date, components, external_event_id,
        raw_record,
    )  # fmt: skip


def reconstitution(
    account_id: str,
    bond_id: str,
    face: Decimal | int,
    event_date: date | str,
    components: Sequence[tuple[str, Decimal | int, Money | None]],
    *,
    external_event_id: str = "",
    raw_record: ops.RawRecordRef | None = None,
) -> LifecycleEvent:
    """STRIPS components exchanged back for their whole bond, as `strip`."""
    return _exchanged(
        "reconstitution", account_id, bond_id, face, event_date, components,
        external_event_id, raw_record,
    )  # fmt: skip


# ── Fixed income: servicing, what to expect (W9.17) ─────────────────────


def expected_coupon(
    account_id: str,
    instrument_id: str,
    face: Decimal | int,
    *,
    coupon_rate: Decimal | int | str,
    day_count: Any,
    period_start: date | str,
    period_end: date | str,
    payment_date: date | str,
    currency: str,
    record_date: date | str = "",
    frequency: int = 2,
) -> LifecycleEvent:
    """The coupon a debt record held at its record date pays: the face held
    times the rate (percent a year) times the period's fraction by the
    record's day count, rounded to the cent half-even, with its period. A
    floater's rate is the index the lake holds plus its spread, named in
    the proposal's note by the caller."""
    fraction = debt.year_fraction(
        day_count, period_start, period_end, period=(period_start, period_end),
        frequency=frequency,
    )  # fmt: skip
    cash = debt.to_cent(
        Fraction(Decimal(face)) * Fraction(Decimal(coupon_rate)) / 100 * fraction
    )
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind="coupon_received",
        quantity=face, event_date=payment_date, cash=Money(cash, currency),
        period_start_date=period_start, period_end_date=period_end, record_date=record_date,
    )  # fmt: skip


def expected_maturity(
    account_id: str,
    instrument_id: str,
    face: Decimal | int,
    maturity_date: date | str,
    *,
    currency: str,
    price_per100: Decimal | int = 100,
) -> LifecycleEvent:
    """A debt record's maturity: the face held redeemed at par (or the
    terms' price per 100), its cash face times the price times 0.01."""
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind="redemption",
        quantity=face, event_date=maturity_date, redemption_kind="maturity",
        redemption_price=price_per100,
        cash=Money(debt.percent_of_par(face, price_per100), currency),
    )  # fmt: skip


def expected_paydown(
    account_id: str,
    instrument_id: str,
    original_face: Decimal | int,
    prior: Any,
    current: Any,
    *,
    currency: str,
    interest_only: bool = False,
) -> LifecycleEvent | None:
    """What a pool's or a tranche's month brings, from the agency's two
    published `Factor` rows (W9.17), on the latter's payment date: a
    paydown where the factor fell (its cash the fall times original face,
    rounded to the cent half-even), an accretion where it rose (a Z class)
    or where an IO's notional fell (`interest_only`, no cash); None where
    it did not move. The proposal carries the factors it was made from."""
    from ..operations import as_decimal

    was, now = as_decimal(prior.factor), as_decimal(current.factor)
    if current.factor_month <= prior.factor_month:
        raise ValueError(
            f"the current factor's month {current.factor_month} is not after"
            f" {prior.factor_month}"
        )
    if was == now:
        return None
    on = current.payment_date
    if not on:
        raise ValueError(f"the factor for {current.factor_month} states no payment date")
    if now > was or interest_only:
        return accretion(account_id, instrument_id, original_face, on, was, now)
    return LifecycleEvent(
        account_id=account_id, instrument_id=instrument_id, kind="paydown",
        quantity=original_face, event_date=on, prior_factor=was, factor=now,
        cash=Money(debt.paydown_cash(original_face, was, now), currency),
    )  # fmt: skip


async def settle_claim(
    role: Any, event: Any, note: str, *, acting_for: str | None = None
) -> Any:
    """A person marks a factor revision's open claim settled (992): the
    difference received or paid, said in the note, through
    `ReleaseLifecycleEvent`; refused here for any event that is no open
    claim, as the book refuses one already booked."""
    if not debt.open_claims([event]):
        raise ValueError(f"{event.event_id} is no open factor revision claim")
    return await release(role, event.event_id, note, acting_for=acting_for)
