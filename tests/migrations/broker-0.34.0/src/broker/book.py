"""The broker's accounts, reported to the street."""

from __future__ import annotations

from typing import Any

import meridian


class Book:
    def __init__(self, plugin: Any) -> None:
        self.plugin = plugin

    async def sync(self) -> None:
        await self.plugin.report_external_accounts(
            accounts=[meridian.ExternalAccount(external_account_id="BRK-1", name="Margin")]
        )
