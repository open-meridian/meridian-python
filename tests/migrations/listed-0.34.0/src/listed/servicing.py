"""A pool's current face, through the roles package."""

from decimal import Decimal

import meridian


def face(original: Decimal, factor: Decimal) -> Decimal:
    return meridian.helpers.debt.current_face(original, factor)
