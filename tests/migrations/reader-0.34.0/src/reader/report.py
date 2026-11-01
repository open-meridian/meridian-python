"""The closes the reader shows, and the prices it hears."""

from __future__ import annotations

from typing import Any

import meridian


class Report:
    def __init__(self, plugin: Any) -> None:
        self.plugin = plugin
        self.heard = 0

    async def closes(self, subjects: list[str], day: str) -> int:
        answer = await self.plugin.list_prices(
            subjects=[meridian.SubjectRef(entity_id=each) for each in subjects],
            business_date=day,
        )
        return len(answer.prices)

    async def on_price(self, heard: Any) -> None:
        self.heard += 1
