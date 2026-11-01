"""A data plugin's two common settings, in the data role's words (SDK 0.35;
spec/each-role-is-one-generated-class, section 4, 924's item 4; the
data-plugin fit review's section 1.12). Their names stay each plugin's
(rulings 908, 912 and 915); these are their shape, once:

    @meridian.settings
    class Declared:
        massive_api_key: str = data.api_key("API key", "From your account's dashboard.")
        stocks_timeliness: str = data.timeliness("Stocks plan")
        sample_data: bool = meridian.sample_data()

- `api_key(label, description)`: a required secret, the vendor's key, sent
  only to the vendor, said on Connection as set or not, never its value.
- `timeliness(label, choices, default)`: what the vendor's plan serves, a
  choice of the data terms' timeliness -- `real_time` ("Real time"),
  `delayed` ("Delayed") and `end_of_day` ("End of day"), the ones the vendor
  offers -- `delayed` by default, so nothing is recorded as real time until
  a person says so. One dataset per timeliness (ruling 382): a listings
  feed given it records into the dataset of the timeliness in force
  (`listings.Feed(timeliness=, datasets_by_timeliness=)`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ...client import Choice

__all__ = ["DELAYED", "END_OF_DAY", "REAL_TIME", "TIMELINESS", "api_key", "timeliness"]

REAL_TIME, DELAYED, END_OF_DAY = "real_time", "delayed", "end_of_day"
#: The data terms' timeliness, in its order, and each one's words.
TIMELINESS = (REAL_TIME, DELAYED, END_OF_DAY)
WORDS = {REAL_TIME: "Real time", DELAYED: "Delayed", END_OF_DAY: "End of day"}


def timeliness(
    label: str,
    choices: Sequence[str] = TIMELINESS,
    default: str = DELAYED,
    *,
    description: str = "",
) -> Any:
    """A timeliness setting (see the module): a field of a class decorated
    `@meridian.settings`, offering `choices` of `real_time`, `delayed` and
    `end_of_day` in that order."""
    from ..._settings import setting

    offered = tuple(dict.fromkeys(choices))
    if not offered:
        raise ValueError(
            "a timeliness setting offers at least one of real_time, delayed, end_of_day"
        )
    for value in offered:
        if value not in TIMELINESS:
            raise ValueError(f"a timeliness is one of {', '.join(TIMELINESS)}, not {value!r}")
    if default not in offered:
        raise ValueError(f"a timeliness setting's default is one it offers, not {default!r}")
    ordered = [value for value in TIMELINESS if value in offered]
    return setting(
        label,
        default=default,
        choices=[Choice(value, WORDS[value]) for value in ordered],
        description=description
        or "What your plan with the vendor serves; live data is recorded into the dataset of "
        "this timeliness.",
    )


def api_key(label: str = "API key", description: str = "") -> Any:
    """The vendor's key (see the module): a required secret, a field of a
    class decorated `@meridian.settings`."""
    from ..._settings import setting

    return setting(
        label,
        required=True,
        secret=True,
        description=description
        or "From your account with the vendor. Sent only to the vendor.",
    )
