"""Package orders (contract v28, sdk-contract/listed-options-and-futures-contract;
ruling 564, OPT Q8; W11.1).

A package -- a vertical spread, a straddle, a covered call -- is one order
with legs and no top-level instrument: each leg an instrument, the side it
trades, its ratio (FIX's LegRatioQty) and, for an option, its position
effect (open or close); the ratios in lowest terms, the order's quantity
the number of package units, and its limit one net price per unit (2 to 16
legs, ruling 592; one stock leg allowed). One placement carries the legs
(FIX 35=AB), and the venue's fill is reported once for the package and once
per leg, each leg linked to the package's fill (FIX MultiLegReportingType,
442), so each leg books its own lots and TCA reads the net price.

- `portfolio` or the `oms` proposes one: `legs` puts its legs in lowest
  terms, `propose` sends it;
- a `connectivity` plugin reports its venue's fill of one: `report_fill`
  sends the package's execution and then each leg's, linked by the
  package fill's venue execution ID.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from ..operations import Finality, Leg, Money
from ..plugin.v1 import operations_pb2 as ops

#: How many legs a package may have (ruling 592).
MOST_LEGS = 16


def legs(*given: tuple[str, str, Decimal | int, str]) -> list[Leg]:
    """A package's legs, each (instrument, side, ratio, position effect),
    with the ratios divided by their greatest common divisor so they are in
    lowest terms; refused with fewer than 2 or more than 16, or a ratio that
    is not a whole number above zero."""
    if not 2 <= len(given) <= MOST_LEGS:
        raise ValueError(f"a package has 2 to {MOST_LEGS} legs, not {len(given)}")
    ratios = []
    for instrument_id, _, ratio, _ in given:
        held = Decimal(ratio)
        if held <= 0 or held != held.to_integral_value():
            raise ValueError(f"{instrument_id}'s ratio is {ratio}: a whole number above zero")
        ratios.append(int(held))
    common = math.gcd(*ratios)
    return [
        Leg(instrument_id=instrument_id, side=side, ratio=r // common, position_effect=effect)
        for (instrument_id, side, _, effect), r in zip(given, ratios, strict=True)
    ]


async def propose(
    plugin: Any,
    account_id: str,
    package: Sequence[Leg],
    quantity: Decimal | int,
    limit_price: Money,
    *,
    acting_for: str | None = None,
    **more: Any,
) -> Any:
    """Propose a package: its legs, the number of package units and the net
    limit per unit (positive a debit paid, negative a credit received);
    a limit order with no top-level instrument."""
    return await plugin.propose_order(
        account_id=account_id,
        legs=list(package),
        quantity=quantity,
        order_type="limit",
        limit_price=limit_price,
        acting_for=acting_for,
        **more,
    )


@dataclass(frozen=True)
class LegFill:
    """One leg of a package's fill as the venue stated it: the instrument,
    the side, the quantity, its price and the venue's ID for the leg's fill."""

    instrument_id: str
    side: str
    quantity: Decimal
    price: Money
    venue_execution_id: str


async def report_fill(
    plugin: Any,
    *,
    placement_id: str,
    venue_account_code: str,
    venue_execution_id: str,
    quantity: Decimal | int,
    net_price: Money,
    leg_fills: Sequence[LegFill],
    trade_time_ns: int,
    trade_date: date | str,
    raw_record: ops.RawRecordRef | None = None,
    **more: Any,
) -> list[Any]:
    """A venue's fill of a package: the package's execution (its units at
    the net price), then each leg's, linked to it by the package fill's
    venue execution ID; each sent once on its own idempotency key. The
    answers, the package's first."""
    common: dict[str, Any] = {
        "placement_id": placement_id,
        "venue_account_code": venue_account_code,
        "kind": "venue_reported",
        "source": "primary",
        "trade_time_ns": trade_time_ns,
        "trade_date": trade_date,
        "finality": Finality(level="final", at_ns=trade_time_ns),
        "raw_record": raw_record,
        **more,
    }
    answers = [
        await plugin.report_execution(
            venue_execution_id=venue_execution_id,
            quantity=quantity,
            price=net_price,
            multi_leg_reporting_type="package",
            idempotency_key=f"fill:{venue_execution_id}",
            **common,
        )
    ]
    for leg in leg_fills:
        answers.append(
            await plugin.report_execution(
                venue_execution_id=leg.venue_execution_id,
                instrument_id=leg.instrument_id,
                side=leg.side,
                quantity=leg.quantity,
                price=leg.price,
                multi_leg_reporting_type="leg",
                package_execution_id=venue_execution_id,
                idempotency_key=f"fill:{leg.venue_execution_id}",
                **common,
            )
        )
    return answers
