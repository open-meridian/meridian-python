"""The option chains: the source as the SDK's chains feed asks it (its
findings done by hand: `helper-adopted` for `Chains` and `is_open`, and
`act-on-the-connection`). The feed records them, sends a row again only when
it changed, and dates them by the deployment's calendar."""

import datetime as dt

from meridian.roles.data import option_chains

#: The platform's US equity venues calendar the chains are dated by.
CALENDAR = "CAL-1"


class Source:
    """The vendor's chains, read in a thread: none in this stand-in."""

    def expirations(self, symbol: str) -> list[dt.date]:
        return []

    def chain(self, symbol: str, expiration: dt.date) -> list[option_chains.ChainOption]:
        return []
