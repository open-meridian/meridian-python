"""The figures a plugin reports on its heartbeat (W4.5), which core draws on
its Summary under Manage.

Each refusal here is the sidecar's, word for word (meridian-design's
fixtures/sidecar/heartbeat.yaml, and meridian-core's sidecar figures.rs): the
SDK refuses first, at the call that sets the figures, so a plugin meets the
same words whichever side caught it.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

import meridian
from conftest import FakeSidecar
from meridian import Figure, FigureState
from meridian.testing import heartbeat
from meridian.v1 import sidecar_pb2

READ_AT = datetime(2026, 9, 26, 22, 35, tzinfo=UTC)


def sent(*figures: Figure) -> list[sidecar_pb2.PluginFigure]:
    return list(heartbeat(figures=figures).figures)


def refused(*figures: Any) -> str:
    with pytest.raises((ValueError, TypeError)) as raised:
        heartbeat(figures=figures)
    return str(raised.value)


# ── Each kind of value ───────────────────────────────────────────────────


def test_an_int_is_a_count() -> None:
    (figure,) = sent(Figure("Connections", 3))
    assert figure.WhichOneof("value") == "count"
    assert figure.count == 3
    assert figure.label == "Connections"
    # Zero is a value, not none: the oneof says which.
    (zero,) = sent(Figure("Connections", 0))
    assert zero.WhichOneof("value") == "count"


def test_a_decimal_crosses_exactly_with_the_scale_it_was_stated_with() -> None:
    (figure,) = sent(Figure("Rows refused", Decimal("0.50")))
    assert figure.WhichOneof("value") == "decimal"
    assert (figure.decimal.high, figure.decimal.low, figure.decimal.scale) == (0, 50, 2)
    (negative,) = sent(Figure("Drift", Decimal("-1.5")))
    integer = (negative.decimal.high << 64) | negative.decimal.low
    assert (integer, negative.decimal.scale) == (-15, 1)
    assert meridian.as_decimal(negative.decimal) == Decimal("-1.5")


def test_a_str_is_a_text() -> None:
    (figure,) = sent(Figure("Key", "Commercial"))
    assert figure.WhichOneof("value") == "text"
    assert figure.text == "Commercial"


def test_a_datetime_is_a_time_in_nanoseconds_since_the_epoch() -> None:
    (figure,) = sent(Figure("Last read", READ_AT))
    assert figure.WhichOneof("value") == "at_ns"
    assert figure.at_ns == 1_790_462_100_000_000_000
    # The same moment in another zone is the same time; microseconds kept.
    eastern = READ_AT.astimezone(timezone(timedelta(hours=-4))) + timedelta(microseconds=7)
    (shifted,) = sent(Figure("Last read", eastern))
    assert shifted.at_ns == 1_790_462_100_000_007_000


def test_as_of_state_and_why_are_carried_and_optional() -> None:
    (plain,) = sent(Figure("Accounts reached", 7))
    assert (plain.as_of_ns, plain.state, plain.why) == (0, 0, "")
    (marked,) = sent(
        Figure("Connections", 3, as_of=READ_AT, state="warn", why="1 needs attention")
    )
    assert marked.as_of_ns == 1_790_462_100_000_000_000
    assert marked.state == FigureState.FIGURE_STATE_WARN
    assert marked.why == "1 needs attention"


@pytest.mark.parametrize(
    ("given", "state"),
    [
        ("ok", FigureState.FIGURE_STATE_OK),
        ("warn", FigureState.FIGURE_STATE_WARN),
        ("error", FigureState.FIGURE_STATE_ERROR),
        ("FIGURE_STATE_ERROR", FigureState.FIGURE_STATE_ERROR),
        (FigureState.FIGURE_STATE_OK, FigureState.FIGURE_STATE_OK),
        (None, FigureState.FIGURE_STATE_UNSPECIFIED),
    ],
)
def test_a_state_is_ok_warn_or_error_by_name_or_enum_or_none(given: Any, state: int) -> None:
    (figure,) = sent(Figure("Connections", 3, state=given))
    assert figure.state == state


def test_the_order_is_the_plugins() -> None:
    labels = [f.label for f in sent(Figure("B", 1), Figure("A", 2), Figure("C", 3))]
    assert labels == ["B", "A", "C"]


def test_eight_figures_and_none_are_accepted() -> None:
    assert len(sent(*(Figure(f"F{i}", i) for i in range(8)))) == 8
    assert sent() == []


# ── The bounds, refused in the sidecar's words ───────────────────────────


def test_more_than_eight_is_refused_never_cut() -> None:
    nine = [Figure(f"F{i}", i) for i in range(9)]
    assert refused(*nine) == "9 figures; a plugin reports at most 8"


def test_an_empty_label_is_refused_naming_the_figure() -> None:
    assert refused(Figure("", 1)) == "figures[0].label is empty; a label is 1 to 40 characters"


def test_a_label_over_forty_characters_is_refused() -> None:
    long = Figure("Connections that need the admin to reconnect", 1)
    assert refused(long) == "figures[0].label is 44 characters; a label is at most 40"
    # Characters, not bytes: forty accented letters are forty.
    assert len(sent(Figure("é" * 40, 1))) == 1


def test_a_repeated_label_is_refused_naming_the_figure() -> None:
    assert (
        refused(Figure("Connections", 1), Figure("Connections", 2))
        == 'figures[1].label "Connections" is given twice; a label is given once'
    )


def test_a_text_over_forty_characters_is_refused() -> None:
    assert (
        refused(Figure("Key", "x" * 41))
        == "figures[0].text is 41 characters; a text is at most 40"
    )
    assert len(sent(Figure("Key", "x" * 40))) == 1


def test_a_why_over_two_hundred_characters_is_refused() -> None:
    assert (
        refused(Figure("Accounts", 1), Figure("Connections", 3, why="x" * 201))
        == "figures[1].why is 201 characters; a why is at most 200"
    )
    assert len(sent(Figure("Connections", 3, why="x" * 200))) == 1


def test_a_decimal_outside_decisions_023_is_refused_never_rounded() -> None:
    assert refused(Figure("Rows refused", Decimal("0.0000000000000000001"))) == (
        "figures[0].decimal has 19 decimal places, and at most 18 cross the wire; "
        "it is refused rather than rounded"
    )
    assert refused(Figure("Rows refused", Decimal("1" * 39))) == (
        "figures[0].decimal has more than 38 digits; it is refused rather than rounded"
    )
    # Thirty-eight digits at eighteen places is the widest that crosses.
    assert len(sent(Figure("Rows refused", Decimal("9" * 20 + "." + "9" * 18)))) == 1
    assert refused(Figure("Rows refused", Decimal("NaN"))) == (
        "figures[0].decimal is not a finite number"
    )


@pytest.mark.parametrize(("state", "named"), [(7, "7"), ("bad", "'bad'"), ("WARN", "'WARN'")])
def test_a_state_the_contract_does_not_define_is_refused(state: Any, named: str) -> None:
    assert (
        refused(Figure("Connections", 3, state=state))
        == f"figures[0].state is {named}, which the contract does not define"
    )


def test_a_figure_with_no_value_is_refused() -> None:
    assert refused(Figure("Connections", None)) == (
        "figures[0] has no value; a figure is a count, a decimal, a text or a time"
    )


def test_a_value_of_no_kind_a_figure_is_refused_naming_the_figure() -> None:
    kinds = "a count (int), a decimal (Decimal), a text (str) or a time (datetime)"
    assert (
        refused(Figure("Ratio", 0.5)) == f"figures[0]'s value is a float; a figure is {kinds}"
    )
    assert refused(Figure("Live", True)) == f"figures[0]'s value is a bool; a figure is {kinds}"
    assert refused(Figure("Last read", datetime(2026, 9, 26))) == (
        "figures[0]'s value is a datetime without a timezone; give it one, as "
        "datetime.now(timezone.utc) does"
    )
    assert refused({"label": "Connections"}) == "figures[0] is a meridian.Figure, not dict"
    with pytest.raises(TypeError, match="not one Figure"):
        heartbeat(figures=Figure("Connections", 3))


# ── On the plugin's heartbeat ────────────────────────────────────────────


async def test_the_heartbeat_carries_the_figures_as_they_stand(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each heartbeat replaces the last list, so every one carries it."""
    service, address = sidecar
    monkeypatch.setattr(meridian.client, "HEARTBEAT_SECONDS", 0.01)
    plugin = await meridian.connect(address)
    try:
        figures = [Figure("Connections", 3, state="warn"), Figure("Last read", READ_AT)]
        plugin.figures = figures
        assert plugin.figures == tuple(figures)
        service.heartbeats.clear()
        await asyncio.sleep(0.1)
        assert len(service.heartbeats) > 1
        assert all(beat.figures == sent(*figures) for beat in service.heartbeats)

        plugin.figures = []  # none clears them
        service.heartbeats.clear()
        await asyncio.sleep(0.1)
        assert service.heartbeats
        assert all(not beat.figures for beat in service.heartbeats)
    finally:
        await plugin.leave()


async def test_report_sends_the_figures_now_and_they_stand_after(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        await plugin.report(healthy=True, figures=[Figure("Accounts reached", 7)])
        await plugin.report(healthy=False, detail="brokerage credentials rejected")
    finally:
        await plugin.leave()

    first, second = service.heartbeats
    assert first.healthy and first.figures == sent(Figure("Accounts reached", 7))
    # A report naming no figures carries those that stand; it does not clear them.
    assert (second.healthy, second.detail) == (False, "brokerage credentials rejected")
    assert second.figures == first.figures


async def test_figures_past_a_bound_are_refused_before_anything_is_sent(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """Nothing is set and nothing sent: the last list stands."""
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        plugin.figures = [Figure("Connections", 3)]
        with pytest.raises(ValueError, match="9 figures; a plugin reports at most 8"):
            await plugin.report(healthy=True, figures=[Figure(f"F{i}", i) for i in range(9)])
        with pytest.raises(ValueError, match="a label is at most 40"):
            plugin.figures = [Figure("x" * 41, 1)]
        assert not service.heartbeats
        assert plugin.figures == (Figure("Connections", 3),)
        # A generator is a list as well as any other.
        plugin.figures = (Figure(f"F{i}", i) for i in range(2))
        assert [f.label for f in plugin.figures] == ["F0", "F1"]
    finally:
        await plugin.leave()
