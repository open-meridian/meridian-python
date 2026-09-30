"""The recorder against a plugin whose sidecar refuses as told."""

from __future__ import annotations

import asyncio
from typing import Any

import meridian

from snaptrade.contract import Recorder
from snaptrade.linking import refusal

ALPACA = "ALPACA:INST-1"


class Refusing:
    def __init__(self, refuse: Exception) -> None:
        self.refuse = refuse

    async def record_holding(self, **params: Any) -> None:
        raise self.refuse


def record(refused: Exception) -> Any:
    recorder = Recorder(Refusing(refused))  # type: ignore[arg-type]
    return asyncio.run(recorder.record("st-1", ALPACA, [{"quantity": 1}]))


def test_a_refused_row_stops_the_statement_and_is_not_retried() -> None:
    outcome = record(meridian.CallFailed("RecordHolding", "refused", "no link for ALPACA:INST-1"))
    assert outcome.recorded == 0 and "no link" in outcome.stopped
    # Refused for something other than a missing link.
    assert not outcome.unlinked


def test_a_row_refused_for_want_of_a_link_says_so() -> None:
    outcome = record(
        meridian.NotLinked(
            "RecordHolding",
            "external account ALPACA:INST-1 is not linked to an account; a deployment "
            "admin links it on the plugin's admin page (W6.4)",
        )
    )
    assert outcome.unlinked and outcome.recorded == 0


def unlinked(name: str, params: Any) -> Exception | None:
    """The sidecar's refusal of a row for the Alpaca account, which nothing links."""
    if name == "RecordHolding":
        return meridian.NotLinked(
            "RecordHolding", f"external account {ALPACA} is not linked to an account"
        )
    return None


def test_the_refusal_from_the_page_s_stand_in_is_unlinked_too() -> None:
    refused = unlinked("RecordHolding", None)
    assert refused is not None and record(refused).unlinked


def test_the_sidecars_refusal_is_shown_plainly() -> None:
    said = "LinkExternalAccount is admitted only acting for a deployment admin"
    assert refusal(meridian.CallFailed("LinkExternalAccount", "refused", said)) == said
