"""A vertical spread's legs, and how far each strike is in the money."""

from decimal import Decimal

from meridian.roles import (
    data,
    lifecycle,
)
from meridian.roles.packages import legs as package_legs

KEPT = data


def vertical(long_leg: str, short_leg: str) -> list[object]:
    return list(package_legs((long_leg, "buy", 2, "open"), (short_leg, "sell", 2, "open")))


def moneyness(strikes: list[Decimal], close: Decimal) -> list[Decimal]:
    return [lifecycle.in_the_money("call", strike, close) for strike in strikes]


def lazily(symbol: str) -> str:
    from meridian.roles import chains, ems

    assert ems is not None
    return chains.osi_terms(symbol)[0]
