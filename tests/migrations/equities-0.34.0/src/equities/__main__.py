"""The plugin's process, wired by hand: its loops restarted by its own
`again`, its licences read by its own loop."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import meridian

from .declaration import DECLARATION
from .lake import Lake

log = logging.getLogger("equities")
LICENCES_SECONDS = 300
TICK_SECONDS = 5


async def licences(plugin: meridian.Plugin, lake: Lake) -> None:
    while True:
        try:
            await lake.read_licences()
        except meridian.MeridianError as failed:
            log.warning("the datasets' licences were not read this time: %s", failed)
        await asyncio.sleep(LICENCES_SECONDS)


async def timetable(lake: Lake) -> None:
    while True:
        await lake.tick()
        await asyncio.sleep(TICK_SECONDS)


async def again(work: Callable[[], Coroutine[Any, Any, None]], what: str) -> None:
    """Work that stops is said and started again, a little later each time."""
    wait = 1.0
    while True:
        try:
            await work()
            return
        except asyncio.CancelledError:
            raise
        except Exception as failed:  # noqa: BLE001 - said, and started again
            log.warning("%s stopped (%s); again in %.0fs", what, failed, wait)
        await asyncio.sleep(wait)
        wait = min(wait * 2, 30.0)


async def run() -> None:
    async with await meridian.connect(declaration=DECLARATION) as plugin:
        lake = Lake(None)
        await asyncio.gather(
            again(lambda: licences(plugin, lake), "the licences"),
            again(lambda: timetable(lake), "the timetable"),
        )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
