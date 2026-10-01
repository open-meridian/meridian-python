"""A statement's figures, refused here as the sidecar refuses them (W2.2).

Since contract v7 a statement carries its figures as a set per margin
segment, each naming its segment as the venue does, with the collateral held
under it. Three things about them the sidecar refuses, and this refuses first,
in its words, before anything is sent: two sets naming one segment, a
collateral balance neither posted nor received, and the three figures a
plugin before v7 sent flat sent beside `figures`. A convenience, as every
check here is: the sidecar refuses the same whatever this client believes.
"""

from __future__ import annotations

from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops

#: The figures a plugin before v7 sent flat, read by the sidecar from one as
#: the set with no segment.
FLAT = ("buying_power", "margin_requirement", "maintenance_excess")


def checked(params: Any) -> None:
    """Raise ValueError, naming the field, for a statement the sidecar would
    refuse; nothing for anything else."""
    if not isinstance(params, ops.RecordHoldingsStatementParams):
        return
    if params.figures:
        for flat in FLAT:
            if params.HasField(flat):
                raise ValueError(f"{flat} is read from a plugin before v7; send it in figures")
    named: set[str] = set()
    for i, figures in enumerate(params.figures):
        if figures.segment in named:
            raise ValueError(
                f'figures[{i}].segment "{figures.segment}" is named twice; a statement has '
                "one set per segment"
            )
        named.add(figures.segment)
        for j, collateral in enumerate(figures.collateral):
            if collateral.direction == ops.COLLATERAL_DIRECTION_UNSPECIFIED:
                raise ValueError(
                    f"figures[{i}].collateral[{j}].direction is unspecified; collateral is "
                    "posted or received"
                )
