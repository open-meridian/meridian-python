"""The listings in the lake: the SDK's feed, its plan by the SDK's timeliness,
its chains the SDK's chains feed (its findings done by hand: `helper-adopted`
for `use_plan`, the chains and the loops)."""

import asyncio
from typing import Any

from meridian.helpers.calendars import MarketDays
from meridian.roles.data import listings, option_chains
from meridian.roles.data.listings import LIVE, TRADES
from meridian.roles.data.quality import EdgeChecks

from .chains import CALENDAR, Source

#: Each kind's dataset by the plan's timeliness.
DATASETS = {
    LIVE: {"real_time": "live", "delayed": "live_delayed"},
    TRADES: {"real_time": "trades", "delayed": "trades_delayed"},
}
TICK_SECONDS = 5


class Lake(listings.Feed):
    """The source's listings: the SDK's feed, its prints."""

    source_name = "equities"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, timeliness="delayed", datasets_by_timeliness=DATASETS, **kwargs)
        self.quality = EdgeChecks(clock_ns=self.clock_ns)
        self.chains = option_chains.Feed(
            Source(), role=self, market_days=MarketDays(self, CALENDAR), clock_ns=self.clock_ns
        )

    async def on_observations_wanted(self, heard: Any) -> None:
        if self.chains.serves(heard.message.dataset):
            return await self.chains.on_observations_wanted(heard)
        await super().on_observations_wanted(heard)

    async def on_want_withdrawn(self, heard: Any) -> None:
        await self.chains.on_want_withdrawn(heard)
        await super().on_want_withdrawn(heard)

    async def run(self) -> None:
        while True:
            await self.tick()
            await self.chains.refresh()
            await asyncio.sleep(TICK_SECONDS)
