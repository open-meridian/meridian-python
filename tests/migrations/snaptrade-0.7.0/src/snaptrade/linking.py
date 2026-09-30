"""Links an external account to one of the deployment's accounts."""

from __future__ import annotations

import meridian


def refusal(failed: meridian.MeridianError) -> str:
    """The sidecar's own words for a refusal, to show as they are."""
    if isinstance(failed, meridian.CallFailed) and failed.detail:
        return failed.detail
    return str(failed)
