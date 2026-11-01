"""A pool's current face, through the roles package."""

from decimal import Decimal

from meridian import roles


def face(original: Decimal, factor: Decimal) -> Decimal:
    return roles.debt.current_face(original, factor)
