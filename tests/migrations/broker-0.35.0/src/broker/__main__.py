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
        lake = Lake()
        book = Book(plugin)
        venue: Any = Venue()
        trader = connectivity.Trader(
            lambda: venue,
            now=lambda: datetime.now(UTC),
            market_zone=ZoneInfo("America/New_York"),
        )
        await lake.start()
        await book.sync()
        trading = asyncio.create_task(trader.run())
        served = pages.serve(plugin, 8000)
        await plugin.report(healthy=True, detail="started")
        await stopped.wait()
        trading.cancel()
        served.shutdown()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
