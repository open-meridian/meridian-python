"""The listings in the lake: the SDK's feed, this source's plan and the
edge glue every listings plugin kept until the feed did it."""

from typing import Any

from meridian.roles.data import listings
from meridian.roles.data.listings import LIVE, PRICE, QUOTE, TRADE, TRADES
from meridian.roles.data.quality import EdgeChecks

DELAYED = {LIVE: "live_delayed", TRADES: "trades_delayed"}


class Lake(listings.Feed):
    """The source's listings: the SDK's feed, its prints."""

    source_name = "equities"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.plan = "delayed"
        self.latency: Any = None
        self.quality = EdgeChecks(clock_ns=self.clock_ns)

    def use_plan(self, plan: str) -> None:
        """The plan as the settings stand: standing wants let go on a change."""
        if plan != self.plan:
            self.plan = plan
            self.standing.clear()
            self.restream()

    def in_force(self, key: str) -> str:
        return DELAYED.get(key, key) if self.plan != "real_time" else key

    # ── The edge (contract v28) ──────────────────────────────────────────

    def at_the_edge(self, key: str, rows: list[Any], want_id: str) -> list[Any]:
        """Rows recorded unasked or for a standing want, aged and judged."""
        standing = {w.want_id for w in self.standing.values()}
        if want_id and want_id not in standing:
            return rows
        dataset = self.dataset(key)
        if self.latency is not None:
            for row in rows:
                self.latency.aged(dataset, "AGE_HOP_EDGE", row)
        return self.quality.judged(key, rows)

    async def _record(self, key: str, data_type: str, rows: Any, want_id: str) -> None:
        if key in (LIVE, TRADES) and data_type in (PRICE, QUOTE, TRADE):
            rows = self.at_the_edge(self.in_force(key), list(rows), want_id)
        await super()._record(key, data_type, rows, want_id)
