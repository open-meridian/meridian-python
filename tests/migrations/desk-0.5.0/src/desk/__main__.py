"""Connects to the sidecar, serves the page, and runs until stopped."""

import asyncio
import logging
import os
import signal

import meridian

from .page import TITLE, serve

log = logging.getLogger("desk")


async def run() -> None:
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for stop in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(stop, stopped.set)

    port = int(os.environ.get("DESK_PAGE_PORT", "8000"))
    async with await meridian.connect(
        interface=meridian.Interface(port=port, title=TITLE)
    ) as plugin:
        log.info(
            "registered as %s, tags %s",
            plugin.identity.instance_id,
            ", ".join(plugin.identity.tags) or "none",
        )
        page = serve(plugin, loop, port)
        await plugin.report(healthy=True, detail="started")
        await stopped.wait()
        page.shutdown()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
