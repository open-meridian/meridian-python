"""A holding recorded for one of the plugin's external accounts."""

from __future__ import annotations

import logging
from typing import Any

import meridian

log = logging.getLogger("desk")


async def record(
    plugin: meridian.Plugin, statement_id: str, external_account_id: str, **row: Any
) -> str:
    """Records one row. "unlinked" when nobody has linked the external
    account to one of the deployment's, which a deployment admin does on the
    plugin's admin page; any other refusal is raised."""
    try:
        await plugin.record_holding(
            statement_id=statement_id, external_account_id=external_account_id, **row
        )
    except meridian.CallFailed as refused:
        # The sidecar says so in its refusal.
        if "is not linked" in str(refused):
            log.info("%s is not linked yet", external_account_id)
            return "unlinked"
        raise
    return "recorded"
