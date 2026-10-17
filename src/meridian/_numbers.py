"""A venue's figure read as the contract's number, defined once and
re-exported by each role that reads one (`meridian.roles.data.number`,
`meridian.roles.connectivity.number`): one function, one meaning.

The contract's Decimal holds at most 18 places and 38 digits
(`meridian.bounds`); a figure past either, not finite, or a float is no
number here, never rounded to one.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .bounds import DECIMAL_DIGITS, DECIMAL_SCALE

#: The contract's Decimal: at most 18 places and 38 digits (meridian.Money).
MOST_PLACES = DECIMAL_SCALE.most
MOST_DIGITS = DECIMAL_DIGITS


def number(value: object) -> Decimal | None:
    """A venue's figure as the contract's number, from its text: a string, an
    int, a Decimal, or a JSON number read by `json_decimal`. None where it is
    not a finite number, or holds more places or digits than the contract's
    Decimal does; never rounded, and never from a float."""
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
