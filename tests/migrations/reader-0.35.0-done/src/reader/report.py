"""The closes the reader shows, and the prices it hears: its reporting class
(its findings done by hand: `act-on-the-connection`, `receive-not-rewritten`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import meridian
from meridian.roles import reporting


class Report(reporting.Role):
    def __init__(self, held: Sequence[str] = ()) -> None:
        self.held = list(held)
        self.heard = 0

    def subjects(self) -> Sequence[str]:
        return self.held

    async def closes(self, subjects: list[str], day: str) -> int:
        answer = await self.list_prices(
            subjects=[meridian.SubjectRef(entity_id=each) for each in subjects],
            business_date=day,
        )
        return len(answer.prices)

    async def on_prices_recorded(self, heard: Any) -> None:
        self.heard += 1
