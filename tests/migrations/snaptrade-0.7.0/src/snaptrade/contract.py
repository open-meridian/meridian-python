"""What reaches the sidecar, through the SDK's typed operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import meridian

log = logging.getLogger("snaptrade")


def refused_unlinked(refused: meridian.MeridianError) -> bool:
    """Whether a row was refused because its external account is not linked
    (W4.8): the sidecar's refusal names it so, and no code says it."""
    return isinstance(refused, meridian.NotLinked)


@dataclass
class Outcome:
    """What recording one account's statement came to."""

    recorded: int = 0
    # Why it stopped before every row was recorded, when it did.
    stopped: str = ""
    # Stopped because the account is not linked to one of the deployment's.
    unlinked: bool = False


class Recorder:
    def __init__(self, plugin: meridian.Plugin) -> None:
        self._plugin = plugin

    async def record(
        self, statement_id: str, external_account_id: str, rows: list[dict[str, Any]]
    ) -> Outcome:
        """Each row, stopping at the first refusal, which is said and not retried."""
        outcome = Outcome()
        try:
            for row in rows:
                await self._plugin.record_holding(
                    statement_id=statement_id, external_account_id=external_account_id, **row
                )
                outcome.recorded += 1
        except meridian.MeridianError as refused:
            outcome.stopped = str(refused)
            outcome.unlinked = refused_unlinked(refused)
            log.warning("statement for %s stopped: %s", external_account_id, refused)
        return outcome
