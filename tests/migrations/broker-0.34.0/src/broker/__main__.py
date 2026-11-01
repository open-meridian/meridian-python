"""The broker plugin's process, wired by hand on one connection."""

import asyncio
import signal
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import meridian
from meridian.roles import connectivity

from .book import Book
from .lake import Lake
from .page import pages
from .venue import Venue


async def run() -> None:
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for stop in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(stop, stopped.set)

    async with await meridian.connect(interface=meridian.Interface(port=8000, pages=pages)) as plugin:
        lake = Lake(plugin)
        book = Book(plugin)
        venue: Any = Venue()
        trader = connectivity.Trader(
            plugin,
            lambda: venue,
            now=lambda: datetime.now(UTC),
            market_zone=ZoneInfo("America/New_York"),
        )
        await lake.start()
        await book.sync()
        hearing = asyncio.create_task(
            plugin.receive(
                observations_wanted=lake.on_want,
                want_withdrawn=lake.on_withdrawn,
                placement_updated=trader.on_placement,
                trading_instruction_changed=trader.on_instruction,
                execution_recorded=trader.on_execution,
                seed=False,
            )
        )
        trading = asyncio.create_task(trader.run(poll_seconds=lambda: 5.0, hear=False))
        served = pages.serve(plugin, 8000)
        await plugin.report(healthy=True, detail="started")
        await stopped.wait()
        hearing.cancel()
        trading.cancel()
        served.shutdown()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
