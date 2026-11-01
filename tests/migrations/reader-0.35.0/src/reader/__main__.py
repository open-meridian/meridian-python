"""The reader's process, wired by hand."""

import asyncio

import meridian

from .report import Report


async def run() -> None:
    async with await meridian.connect() as plugin:
        report = Report(plugin)
        held = ["INS-1", "INS-2"]
        await plugin.receive(prices_recorded=report.on_price, subjects=held)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
