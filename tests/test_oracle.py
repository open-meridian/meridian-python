"""The QuantLib oracle's case sets, held offline (spec/the-analytics-engines-
first-release, §4 and Q12): each pinned in canonical form, answered by the
pinned QuantLib release, with tolerances of a stated kind, and its calendar
cases equal to what core's settlement calendar data gives read directly --
so the committed QuantLib answers align with core's calendars. The live run
against QuantLib itself is `make oracle-live`, scheduled; nothing here
imports QuantLib, which is never a dependency of the SDK."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

import oracle

ROOT = Path(__file__).resolve().parents[1]


def test_quantlib_is_pinned_once_and_test_only() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["optional-dependencies"]["oracle"] == [f"QuantLib=={oracle.PINNED}"]
    assert not [d for d in project["dependencies"] if d.lower().startswith("quantlib")]
    assert not [d for d in project["optional-dependencies"]["dev"] if "quantlib" in d.lower()]


def test_there_is_a_case_set() -> None:
    assert [path.stem for path in oracle.case_sets()] == ["calendar-alignment"]


@pytest.mark.parametrize("path", oracle.case_sets(), ids=lambda path: path.stem)
def test_each_case_set_is_pinned_from_the_pinned_quantlib(path: Path) -> None:
    held = oracle.load(path)  # refused unless canonical
    assert held["quantlib"] == oracle.PINNED, "regenerated only on a deliberate version bump"
    assert isinstance(held["gating"], bool)
    names = [case["name"] for case in held["cases"]]
    assert len(names) == len(set(names))
    for case in held["cases"]:
        assert case["tolerance"]["kind"] in oracle.TOLERANCE_KINDS, case["name"]
        assert set(case["setup"]) == {"engine", "steps", "day_count"}, case["name"]
        assert case["expected"], case["name"]


@pytest.mark.parametrize("path", oracle.case_sets(), ids=lambda path: path.stem)
def test_quantlibs_calendar_answers_are_core_calendars(path: Path) -> None:
    held = oracle.load(path)
    checked = 0
    for case in held["cases"]:
        direct = oracle.direct(held, case)
        if direct is not None:
            assert direct == case["expected"], case["name"]
            checked += 1
    assert checked or "calendar" not in held


def test_the_calendar_is_read_as_core_answers_it() -> None:
    held = oracle.load(oracle.CASES / "calendar-alignment.json")
    calendar = oracle.Calendar.of(held["calendar"])
    assert calendar.weekend == frozenset({5, 6})
    assert len(calendar.closed) == 10
    two = dict(held["calendar"], weekends=held["calendar"]["weekends"] * 2)
    with pytest.raises(ValueError, match="one weekend rule"):
        oracle.Calendar.of(two)


def test_a_tolerance_is_held_by_its_kind() -> None:
    assert oracle.within("0.5", "0.5000000000000001", {"kind": "absolute", "value": "1E-15"})
    assert not oracle.within("0.5", "0.501", {"kind": "absolute", "value": "1E-15"})
    assert oracle.within("100", "100.5", {"kind": "relative", "value": "0.01"})
    assert oracle.within("0.20", "0.2049", {"kind": "vol_points", "value": "0.5"})
    assert oracle.within("0.0400", "0.04009", {"kind": "basis_points", "value": "1"})
    with pytest.raises(ValueError, match="no tolerance"):
        oracle.within("1", "1", {"kind": "percent", "value": "1"})
