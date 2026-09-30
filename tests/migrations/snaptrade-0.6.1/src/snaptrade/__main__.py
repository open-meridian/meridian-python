"""Connects to the sidecar and records each account's statement."""

import asyncio
import logging

import meridian

log = logging.getLogger("snaptrade")


async def run() -> None:
    async with await meridian.connect() as plugin:
        log.info("registered as %s", plugin.identity.instance_id)
        await plugin.report(healthy=True, detail="started")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
