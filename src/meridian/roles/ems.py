"""An `ems` plugin's common part (contract v27): its pre-trade check of the
reference price's age (W11.7, W11.8; rulings 374 and 420), its RFQ
placement's quotes (W11.40, W11.41) and its reads of the costs TCA records
(W10.11).

**The reference price's age.** Before a placement, the `ems` reads its
reference price's confirmed time -- the later of the price's source time
and its dataset's last liveness (ruling 418) -- records its age at the
`ems_check` hop, and judges it against the tighter of the dataset's stale
ceiling (`DatasetRef.stale_after_ns`) and its admin's own
(`stale_reference_after`, per asset class), a delayed dataset against its
declared delay plus the ceiling, and only in session (`in_session`):

    check = ems.ReferenceCheck(action=config.stale_reference_action,
                               after_ns=ems.after_ns(config.stale_reference_after),
                               latency=latency, liveness=liveness)
    stale = check.stale(price, dataset=ref, asset_class="equity", sessions=sessions)
    if stale is not None and check.refuses:
        await check.hold(plugin, order_id, stale)      # the order held, its cause typed
    else:
        await plugin.create_placement(..., **check.placement(stale))

Past the ceiling the admin's choice applies: **refuse** -- no placement, the
order held with `HOLD_CAUSE_REFERENCE_PRICE_STALE` naming the dataset, age
and ceiling -- or **warn** -- the placement sent carrying its
`StaleReference`, which the book records as
`PLACEMENT_CONDITION_SENT_ON_STALE_REFERENCE`. The book refuses nothing:
this is the plugin's check.

**An RFQ placement's quotes** (`open_quotes`): the dealers' quotes standing
on it, best first for its side, from which a person picks
(`pick_placement_quote`).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from ..operations import as_decimal
from ..plugin.v1 import operations_pb2 as ops
from ._latency import Latency, Liveness, confirmed_ns, in_session

__all__ = ["REFUSE", "WARN", "ReferenceCheck", "after_ns", "open_quotes"]

#: `stale_reference_action`'s two values.
REFUSE, WARN = "refuse", "warn"
_SECOND = 1_000_000_000


def after_ns(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """The `ems` admin's `stale_reference_after` table, each row an asset
    class and its ceiling in seconds, as nanoseconds by asset class."""
    out: dict[str, int] = {}
    for row in rows:
        asset_class = str(row.get("asset_class") or "").strip()
        seconds = row.get("after_seconds")
        if asset_class and seconds not in (None, ""):
            out[asset_class] = int(Decimal(str(seconds)) * _SECOND)
    return out


@dataclass
class ReferenceCheck:
    """The `ems`'s pre-trade check of its reference price (see the module)."""

    action: str = REFUSE
    #: The admin's own ceilings by asset class (`after_ns`), tighter than the
    #: dataset's only.
    after_ns: Mapping[str, int] = field(default_factory=dict)
    latency: Latency | None = None
    liveness: Liveness | None = None
    clock_ns: Callable[[], int] = time.time_ns

    @property
    def refuses(self) -> bool:
        return self.action != WARN

    def stale(
        self,
        price: Any,
        *,
        dataset: ops.DatasetRef | None = None,
        asset_class: str = "",
        sessions: ops.TradingSessions | None = None,
    ) -> ops.StaleReference | None:
        """The reference price's age, recorded at the `ems_check` hop; its
        `StaleReference` where it is past the ceiling in force, in session,
        else None. With no ceiling set, nothing is stale."""
        now = self.clock_ns()
        name = str(price.meta.source.dataset) if getattr(price, "meta", None) else ""
        age = now - confirmed_ns(price, self.liveness)
        if self.latency is not None and name:
            self.latency.age(name, ops.AGE_HOP_EMS_CHECK, age)
        if sessions is not None and not in_session(sessions, now):
            return None
        ceilings = [c for c in (self.after_ns.get(asset_class, 0),) if c > 0]
        if dataset is not None and dataset.stale_after_ns > 0:
            ceilings.append(int(dataset.stale_after_ns))
        if not ceilings:
            return None
        ceiling = min(ceilings)
        delay = int(dataset.declared_delay_ns) if dataset is not None else 0
        if age <= ceiling + delay:
            return None
        return ops.StaleReference(dataset=name, age_ns=age, ceiling_ns=ceiling)

    async def hold(
        self, plugin: Any, order_id: str, stale: ops.StaleReference, reason: str = ""
    ) -> Any:
        """Refuse: the order held, its cause typed and what the check found
        named (W11.7); a person places again once the price is fresh."""
        return await plugin.set_working_condition(
            order_id=order_id,
            condition="held",
            set=True,
            reason=reason
            or f"reference price {stale.age_ns // _SECOND}s old, past its ceiling",
            hold_cause="reference_price_stale",
            stale_reference=stale,
            idempotency_key=f"stale:{order_id}:{stale.dataset}:{stale.age_ns // _SECOND}",
        )

    def placement(self, stale: ops.StaleReference | None) -> dict[str, Any]:
        """What a placement carries: under warn, the stale reference found
        (W11.8); nothing otherwise."""
        return {"stale_reference": stale} if stale is not None and not self.refuses else {}


def open_quotes(placement: ops.Placement) -> list[ops.PlacementQuote]:
    """An RFQ placement's open quotes, best first for the firm: a dealer's
    offer (its side a sell, to a buyer) lowest first, its bid (to a seller)
    highest first; ties by the time received."""
    standing = [q for q in placement.quotes if q.outcome == ops.PLACEMENT_QUOTE_OUTCOME_OPEN]

    def key(quote: ops.PlacementQuote) -> tuple[Decimal, int]:
        price = as_decimal(quote.price.amount) if quote.HasField("price") else Decimal(0)
        offered = quote.side not in (ops.SIDE_BUY,)
        return (price if offered else -price, int(quote.received_at_ns))

    return sorted(standing, key=key)
