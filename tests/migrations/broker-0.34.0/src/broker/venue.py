"""The broker, as the Trader reaches it: a stand-in reaching no account."""

from __future__ import annotations


class Venue:
    def accounts(self) -> tuple[str, ...]:
        return ()
