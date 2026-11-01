"""A pool's money, by the contract's rules."""

from decimal import Decimal

import meridian
import meridian.helpers.debt as rules


def cash(face: Decimal, price: Decimal) -> Decimal:
    return rules.percent_of_par(face, price)


def itm(strike: Decimal, close: Decimal) -> Decimal:
    return meridian.helpers.lifecycle.in_the_money("put", strike, close)
