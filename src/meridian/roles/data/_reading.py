"""What every data plugin reads a venue into before a row exists: its numbers
as the contract's `Decimal`, a value that would not read kept as sent, the
UTC day, and how the venue has answered (`Session`). Nothing here speaks to a
venue: the plugin's own client fills `Health` as it calls, and its
conversion reads the venue's words with `number` and `json_decimal`."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

NANOS_PER_SECOND = 1_000_000_000
SECONDS_PER_DAY = 86_400
NANOS_PER_DAY = SECONDS_PER_DAY * NANOS_PER_SECOND

#: The contract's Decimal: at most 18 places and 38 digits (meridian.Money).
MOST_PLACES = 18
MOST_DIGITS = 38


@dataclass(frozen=True)
class Unread:
    """A venue's value that did not read as the contract's number: its field
    in the venue's answer, and its text as sent."""

    field: str
    text: str


def json_decimal(body: str | bytes) -> Any:
    """A JSON body with every number that is not a whole one a `Decimal` from
    its own text: no float ever exists (one float() loses a satoshi)."""
    return json.loads(body, parse_float=Decimal)


def number(value: object) -> Decimal | None:
    """A venue's figure as the contract's number, from its text: a string or a
    JSON number read by `json_decimal`. None where it is not a finite number,
    or holds more places or digits than the contract's Decimal does; never
    rounded, and never from a float."""
    if isinstance(value, bool) or value is None or isinstance(value, float):
        return None
    try:
        amount = Decimal(value) if isinstance(value, int | Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite():
        return None
    _, digits, exponent = amount.as_tuple()
    places = -exponent if isinstance(exponent, int) and exponent < 0 else 0
    if places > MOST_PLACES or len(digits) > MOST_DIGITS:
        return None
    return amount


def utc_day(at_s: int) -> date:
    """The UTC date the second `at_s` falls on (a day starting at a UTC
    midnight is that day)."""
    return date.fromordinal(date(1970, 1, 1).toordinal() + at_s // SECONDS_PER_DAY)


def day_start(day: date) -> int:
    """The UTC midnight `day` starts at, in seconds."""
    return (day.toordinal() - date(1970, 1, 1).toordinal()) * SECONDS_PER_DAY


def iso_time(at_ns: int) -> str:
    """A time as the role's records carry it: ISO 8601, to the second, UTC;
    empty for none."""
    if not at_ns:
        return ""
    return datetime.fromtimestamp(at_ns / 1e9, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Health:
    """How the venue has answered since the plugin started, as its client
    counts it."""

    calls: int = 0
    rate_limited: int = 0
    failures: int = 0
    last_ok_ns: int = 0
    last_failed_ns: int = 0
    last_error: str = ""
    waited_seconds: float = 0.0

    @property
    def healthy(self) -> bool:
        """Whether the venue answered last, or has not been asked yet."""
        return self.last_ok_ns >= self.last_failed_ns and (
            self.last_ok_ns > 0 or self.calls == 0
        )


@dataclass(frozen=True)
class Limits:
    """What the venue allows, as its documentation says, and what the plugin
    spends of it; for a venue serving daily history, the most daily candles
    one request returns and how far back that history reaches in days (0:
    it states no bound)."""

    allowed: str
    spent: str
    most_candles: int = 0
    history_days: int = 0


@dataclass(frozen=True)
class Endpoint:
    """One way the plugin reaches the venue: its name, its address and what
    it is read for."""

    name: str
    address: str
    what: str


@dataclass
class Session:
    """What the plugin connects to, and how it is going: `mode` is `live` for
    the venue itself, anything else for sample data (the package's synthetic
    answers or a developer's recorded ones)."""

    mode: str
    endpoints: tuple[Endpoint, ...]
    limits: Limits
    health: Health = field(default_factory=Health)
