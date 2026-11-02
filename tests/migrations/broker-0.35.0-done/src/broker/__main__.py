"""The broker plugin's process: one class per role it holds, registered on
one connection (its findings done by hand: `connect-to-run`)."""

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import meridian
from meridian.roles import connectivity

from .book import BOOK
from .declaration import DECLARATION
from .lake import Lake
from .page import pages
from .venue import Venue

PORT = 8000


def main() -> None:
    venue: Any = Venue()
    trader = connectivity.Trader(
        lambda: venue,
        now=lambda: datetime.now(UTC),
        market_zone=ZoneInfo("America/New_York"),
    )
    meridian.run(declaration=DECLARATION, roles=[Lake(), BOOK, trader], pages=pages, port=PORT)


if __name__ == "__main__":
    main()
