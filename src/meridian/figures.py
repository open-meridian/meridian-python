"""The few figures a plugin reports about its own work (W4.5).

Core draws them as tiles on the plugin's Summary under Manage, below its own
status (W6.9): Connections, Accounts reached, Last read. They go on the
heartbeat, the one report a plugin already sends its sidecar, and each
heartbeat carries the list as it stands, replacing the last.

    plugin.figures = [
        meridian.Figure("Connections", 3, state="warn",
                        why="1 connection needs attention: the brokerage asked to reconnect"),
        meridian.Figure("Accounts reached", 7),
        meridian.Figure("Last read", read_at),
    ]

About the plugin's own work, like the rest of its report: a figure names no
account and carries none of an account's data, since Manage shows none.

Bounded, and refused rather than cut, here at the call that sets them and in
the sidecar's words (meridian-design's fixtures/sidecar/heartbeat.yaml), so a
plugin learns of a bad figure where it made it rather than from its Summary:
at most 8; a label of 1 to 40 characters, given once; a text of at most 40; a
why of at most 200; a state of ok, warn or error; a value always given; a
decimal within decisions/023's range. Each bound is the data dictionary's
(meridian-schema's boundaries/fields.json), taken from the generated
meridian.bounds rather than written here.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from . import bounds
from .v1 import sidecar_pb2

# The entries' bounds: meridian.v1.HeartbeatRequest.figures' count and
# meridian.v1.PluginFigure's label, text and why lengths.
_FIGURES = bounds.HEARTBEAT_REQUEST_FIGURES_COUNT
_LABEL = bounds.PLUGIN_FIGURE_LABEL_LENGTH
_TEXT = bounds.PLUGIN_FIGURE_TEXT_LENGTH
_WHY = bounds.PLUGIN_FIGURE_WHY_LENGTH

#: What a figure's tile is marked with: ok, warn or error, or none, drawn plain.
FigureState = sidecar_pb2.FigureState

# What the wire carries of a Decimal (decisions/023), as the dictionary states
# it: a scale of 0 to DECIMAL_SCALE.most, and an integer whose magnitude is
# below 10 to the DECIMAL_DIGITS; and of a count or a time, 64 bits.
_TOO_MANY_DIGITS = 10**bounds.DECIMAL_DIGITS
_LOW_HALF = 2**64 - 1
_INT64 = range(-(2**63), 2**63)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

_STATES: dict[str, int] = {
    **dict(FigureState.items()),
    **{name.removeprefix("FIGURE_STATE_").lower(): v for name, v in FigureState.items()},
}

_KINDS = "a count (int), a decimal (Decimal), a text (str) or a time (datetime)"


@dataclass(frozen=True)
class Figure:
    """One figure, as core draws it on the plugin's Summary.

    `value` is what kind of figure it is: an `int` is a count, a `Decimal` a
    decimal, a `str` a text, and a timezone-aware `datetime` a time ("Last
    read"). `as_of` is when the value was true, where that is not the
    heartbeat's moment. `state` marks the tile -- "ok", "warn" or "error"
    (or a `meridian.FigureState`), none drawn plain -- and `why` is the note
    beside it.

    Checked when the list is set on the plugin, where each figure's place in
    it is known, so a refusal names the figure as the sidecar would.
    """

    label: str
    value: int | Decimal | str | datetime
    as_of: datetime | None = None
    state: str | int | None = None
    why: str | None = None


def listed(figures: Iterable[Figure]) -> tuple[Figure, ...]:
    """The figures given, as a tuple: a list of them, never one alone."""
    if isinstance(figures, Figure):
        raise TypeError("figures is a list of meridian.Figure, not one Figure")
    return tuple(figures)


def wire(figures: Iterable[Figure]) -> tuple[sidecar_pb2.PluginFigure, ...]:
    """The figures as the heartbeat carries them, or refused before anything
    is sent: ValueError for a bound, in the sidecar's words, and TypeError for
    a value that is not one of a figure's kinds."""
    given = listed(figures)
    if not _FIGURES.admits(len(given)):
        raise ValueError(f"{len(given)} figures; a plugin reports at most {_FIGURES.most}")
    labels: set[str] = set()
    sent = []
    for i, figure in enumerate(given):
        at = f"figures[{i}]"
        if not isinstance(figure, Figure):
            raise TypeError(f"{at} is a meridian.Figure, not {type(figure).__name__}")
        sent.append(_figure(at, figure, labels))
    return tuple(sent)


def _figure(at: str, figure: Figure, labels: set[str]) -> sidecar_pb2.PluginFigure:
    """One figure, its bounds checked in the order the sidecar checks them."""
    label = _text(at, "label", figure.label)
    if not label:
        raise ValueError(
            f"{at}.label is empty; a label is {_LABEL.least} to {_LABEL.most} characters"
        )
    _within(at, "label", "a label", label, _LABEL)
    if label in labels:
        raise ValueError(
            f"{at}.label {json.dumps(label, ensure_ascii=False)} is given twice; "
            "a label is given once"
        )
    labels.add(label)

    sent = sidecar_pb2.PluginFigure(label=label)
    value = figure.value
    if value is None:
        raise ValueError(f"{at} has no value; a figure is a count, a decimal, a text or a time")
    if isinstance(value, bool):
        raise TypeError(f"{at}'s value is a bool; a figure is {_KINDS}")
    if isinstance(value, int):
        if value not in _INT64:
            raise ValueError(f"{at}.count is {value}, more than a 64-bit integer holds")
        sent.count = value
    elif isinstance(value, Decimal):
        sent.decimal.CopyFrom(_decimal(at, value))
    elif isinstance(value, str):
        _within(at, "text", "a text", value, _TEXT)
        sent.text = value
    elif isinstance(value, datetime):
        sent.at_ns = _ns(f"{at}'s value", value)
    else:
        raise TypeError(f"{at}'s value is a {type(value).__name__}; a figure is {_KINDS}")

    if figure.as_of is not None:
        if not isinstance(figure.as_of, datetime):
            raise TypeError(f"{at}.as_of is a datetime, not {type(figure.as_of).__name__}")
        sent.as_of_ns = _ns(f"{at}.as_of", figure.as_of)
    sent.state = _state(at, figure.state)  # type: ignore[assignment]
    why = _text(at, "why", figure.why or "")
    _within(at, "why", "a why", why, _WHY)
    sent.why = why
    return sent


def _text(at: str, field: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{at}.{field} is a str, not {type(value).__name__}")
    return value


def _within(at: str, field: str, what: str, text: str, bound: bounds.Length) -> None:
    """No longer than its bound, counted in characters as a person reads them
    rather than in bytes."""
    if len(text) > bound.most:
        raise ValueError(
            f"{at}.{field} is {len(text)} characters; {what} is at most {bound.most}"
        )


def _decimal(at: str, value: Decimal) -> sidecar_pb2.Decimal:
    """Its integer, in two 64-bit halves, and the scale it was stated with:
    exact, or refused, never rounded and never normalised."""
    sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        raise ValueError(f"{at}.decimal is not a finite number")
    magnitude = int("".join(map(str, digits))) * 10 ** max(exponent, 0)
    integer, scale = -magnitude if sign else magnitude, max(-exponent, 0)
    if not bounds.DECIMAL_SCALE.admits(scale):
        raise ValueError(
            f"{at}.decimal has {scale} decimal places, and at most "
            f"{bounds.DECIMAL_SCALE.most} cross the wire; it is refused rather than rounded"
        )
    if abs(integer) >= _TOO_MANY_DIGITS:
        raise ValueError(
            f"{at}.decimal has more than {bounds.DECIMAL_DIGITS} digits; "
            "it is refused rather than rounded"
        )
    return sidecar_pb2.Decimal(high=integer >> 64, low=integer & _LOW_HALF, scale=scale)


def _ns(where: str, moment: datetime) -> int:
    """A moment in nanoseconds since the epoch. A datetime without a timezone
    names no moment, so it is refused rather than taken as this host's."""
    if moment.utcoffset() is None:
        raise TypeError(
            f"{where} is a datetime without a timezone; give it one, as "
            "datetime.now(timezone.utc) does"
        )
    ns = (moment - _EPOCH) // timedelta(microseconds=1) * 1000
    if ns not in _INT64:
        raise ValueError(f"{where} is {moment.isoformat()}, outside what a 64-bit time holds")
    return ns


def _state(at: str, state: str | int | None) -> int:
    """None is no state, drawn plain; otherwise one the contract defines,
    by name ("warn", "FIGURE_STATE_WARN") or as a FigureState."""
    if state is None or state == "":
        return FigureState.FIGURE_STATE_UNSPECIFIED
    if isinstance(state, str) and state in _STATES:
        return _STATES[state]
    if isinstance(state, int) and not isinstance(state, bool) and state in _STATES.values():
        return state
    raise ValueError(f"{at}.state is {state!r}, which the contract does not define")
