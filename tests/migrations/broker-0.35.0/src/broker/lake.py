"""The broker's listings, answered for the lake."""

from __future__ import annotations

from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import data

KEY = "daily"


class Lake(data.Role):
    """What the lake wants of the broker's daily dataset: declined where the
    broker does not list the subject."""

    seed = False

    def __init__(self) -> None:
        self.wants = data.Wants(self, (KEY,))
        self.listed: dict[str, str] = {}

    async def start(self) -> None:
        await self.wants.read_licences()

    async def on_observations_wanted(self, heard: Any) -> None:
        await self.wants.hear(heard, self.answer)

    async def answer(
        self,
        want: ops.ObservationsWantedEvent,
        key: str,
        subjects: list[str],
        kinds: tuple[int, ...],
    ) -> dict[str, str]:
        found = await self.resolve_venue(
            identifiers=[ops.Identifier(scheme="iso10383", value="XNYS")], as_of_ns=1
        )
        del found
        return {subject: "not_covered" for subject in subjects if subject not in self.listed}

    async def on_want_withdrawn(self, heard: Any) -> None:
        self.wants.withdraw(heard.message.want_id)
