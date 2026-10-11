"""The role's figures in its order, its labels fixed (spec/plugin-pages-follow-
their-role, "The common Summary")."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Any

from ..figures import Figure

Value = int | Decimal | str | datetime | Figure | None
#: The state a plain value is marked with, by the role's rule; None, plain.
Rule = Callable[[Any], str | None]


def ordered(given: Sequence[tuple[str, Value, Rule | None]]) -> list[Figure]:
    """Each `(label, value, rule)` as a figure, in order: a plain value under
    the role's label, marked by its rule; a `Figure` kept with its state and
    why, under the role's label, refused where it names another; None left
    out, for a figure shown only when it has something to say."""
    out: list[Figure] = []
    for label, value, rule in given:
        if value is None:
            continue
        if isinstance(value, Figure):
            if value.label and value.label != label:
                raise ValueError(
                    f"the figure {value.label!r} is given as the role's {label!r}; a common "
                    "figure keeps the role's label"
                )
            out.append(replace(value, label=label))
            continue
        out.append(Figure(label, value, state=rule(value) if rule else None))
    return out
