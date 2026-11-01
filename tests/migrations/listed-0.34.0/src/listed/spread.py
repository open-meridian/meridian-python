"""A vertical spread's legs, and how far each strike is in the money."""

from decimal import Decimal

from meridian.helpers import lifecycle
from meridian.roles import (
    data,
)
from meridian.helpers.packages import legs as package_legs

KEPT = data


def vertical(long_leg: str, short_leg: str) -> list[object]:
    return list(package_legs((long_leg, "buy", 2, "open"), (short_leg, "sell", 2, "open")))


def moneyness(strikes: list[Decimal], close: Decimal) -> list[Decimal]:
    return [lifecycle.in_the_money("call", strike, close) for strike in strikes]


def lazily(symbol: str) -> str:
    from meridian.helpers import chains
    from meridian.roles import ems

    assert ems is not None
    return chains.osi_terms(symbol)[0]
