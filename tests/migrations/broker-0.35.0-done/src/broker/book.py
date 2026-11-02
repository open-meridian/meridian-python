"""The broker's accounts, reported to the street: its custody class (its
findings done by hand: `act-on-the-connection`)."""

from __future__ import annotations

import meridian
from meridian.roles import custody


class Book(custody.Role):
    async def on_start(self) -> None:
        await self.report_external_accounts(
            accounts=[meridian.ExternalAccount(external_account_id="BRK-1", name="Margin")]
        )


#: The custody role object the pages act through, which __main__.py registers.
BOOK = Book()
