"""The listings in the lake: the SDK's feed, this source's plan and the
edge glue every listings plugin kept until the feed did it."""

from typing import Any

from meridian.roles.data import listings
from meridian.roles.data.listings import LIVE, TRADES
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
