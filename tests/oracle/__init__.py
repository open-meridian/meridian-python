"""The QuantLib oracle harness (spec/the-analytics-engines-first-release, §4
and Q12; stood up in v26 so v28 does not build it under deadline).

QuantLib is the analytics engine's test oracle only, never part of the SDK
or any image (the product owner, 2026-10-12: our own engine, QuantLib as
the oracle). Here it is a test dependency pinned in pyproject.toml's
`oracle` extra, which nothing but `make oracle-live` and
`make oracle-regenerate` installs.

**Case sets** (`oracle case set`, approved 2026-10-14) are pinned canonical
JSON under `cases/`. Each holds:
- the inputs, by the engine's own terms;
- QuantLib's setup, written out (`setup`: the engine, the step count, the
  day count);
- QuantLib's committed answer (`expected`);
- a tolerance of a stated kind: `absolute`, `relative`, `vol_points` or
  `basis_points`.

A set marked `gating: false` stands the harness up and gates no model. v26
has no model QuantLib can check -- its models are arithmetic, checked
exactly against the SDK's reference computations -- so its one set aligns
the calendars. The first gating sets are v28's.

**Committed, not computed in CI** (Q12). The committed answers come from the
pinned QuantLib (`quantlib` in each set, equal to the pin). They are
regenerated only on a deliberate version bump, with the diff reviewed
(`make oracle-regenerate`). A scheduled live run (`make oracle-live`, the
`oracle-live` workflow) recomputes every case with the pinned QuantLib and
fails on drift. The ordinary gate reads only the committed files, so it
stays offline and deterministic.

**Calendars aligned** (§4). A set's `calendar` is core's settlement
calendar as a plugin reads it (`ReadCalendar`'s answer, protobuf JSON). The
harness builds QuantLib's calendar from that data (`quantlib_calendar`),
never from QuantLib's own holiday lists, so a difference is the model's and
never a holiday list's. The same data read directly (`Calendar`) must give
the committed answers too, which the offline gate checks.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
CASES = HERE / "cases"

#: The QuantLib release the committed answers come from. pyproject.toml's
#: `oracle` extra pins the same release; test_oracle.py holds them equal.
PINNED = "1.40"
TOLERANCE_KINDS = ("absolute", "relative", "vol_points", "basis_points")
WEEKDAYS = {
    "WEEKDAY_MONDAY": 0,
    "WEEKDAY_TUESDAY": 1,
    "WEEKDAY_WEDNESDAY": 2,
    "WEEKDAY_THURSDAY": 3,
    "WEEKDAY_FRIDAY": 4,
    "WEEKDAY_SATURDAY": 5,
    "WEEKDAY_SUNDAY": 6,
}


def canonical(value: Any) -> bytes:
    """A case set's canonical JSON (RFC 8785): it carries no float, every
    number a string, so Python's sorted, compact JSON is the canonical form
    for its ASCII keys."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def load(path: Path) -> dict[str, Any]:
    """A case set, refused unless it is exactly its own canonical form."""
    raw = path.read_bytes()
    held: dict[str, Any] = json.loads(raw)
    if canonical(held) != raw.rstrip(b"\n"):
        raise ValueError(f"{path.name} is not in canonical form; make oracle-regenerate")
    return held


def case_sets() -> list[Path]:
    return sorted(CASES.glob("*.json"))


# ── Core's settlement calendar, read directly ───────────────────────────────


@dataclass(frozen=True)
class Calendar:
    """Core's settlement calendar as ReadCalendar answers it: the weekend's
    days, the days closed, and its coverage."""

    weekend: frozenset[int]
    closed: frozenset[date]
    covers: tuple[date, date]

    @classmethod
    def of(cls, read: Mapping[str, Any]) -> Calendar:
        weekends = read.get("weekends") or []
        if len(weekends) != 1:
            # QuantLib's bespoke calendar holds one weekend for all time.
            raise ValueError("the harness aligns a calendar with one weekend rule")
        coverage = read["coverage"]
        return cls(
            weekend=frozenset(WEEKDAYS[day] for day in weekends[0]["weekdays"]),
            closed=frozenset(
                date.fromisoformat(day["date"])
                for day in read.get("days") or []
                if day.get("kind", "CALENDAR_DAY_KIND_CLOSED") == "CALENDAR_DAY_KIND_CLOSED"
            ),
            covers=(
                date.fromisoformat(coverage["fromDate"]),
                date.fromisoformat(coverage["toDate"]),
            ),
        )

    def business(self, day: date) -> bool:
        if not self.covers[0] <= day <= self.covers[1]:
            raise ValueError(f"{day} is outside the calendar's coverage")
        return day.weekday() not in self.weekend and day not in self.closed

    def advance(self, day: date, days: int) -> date:
        """`days` business days after `day` (before, for a negative count);
        0 adjusts a holiday forward, as QuantLib's `advance` does."""
        step = 1 if days >= 0 else -1
        at = day
        if days == 0:
            while not self.business(at):
                at += timedelta(days=1)
            return at
        left = abs(days)
        while left:
            at += timedelta(days=step)
            if self.business(at):
                left -= 1
        return at

    def between(self, start: date, end: date) -> int:
        """Business days from `start` (included) to `end` (excluded), as
        QuantLib's `businessDaysBetween` counts them by default."""
        count, at = 0, start
        while at < end:
            count += int(self.business(at))
            at += timedelta(days=1)
        return count


def direct(case_set: Mapping[str, Any], case: Mapping[str, Any]) -> str | None:
    """A calendar case's answer from core's calendar data alone, or None for
    a case that is not the calendar's."""
    calendar = Calendar.of(case_set["calendar"])
    inputs = case["inputs"]
    if case["kind"] == "advance":
        return calendar.advance(
            date.fromisoformat(inputs["date"]), int(inputs["days"])
        ).isoformat()
    if case["kind"] == "business_days_between":
        return str(
            calendar.between(
                date.fromisoformat(inputs["from"]), date.fromisoformat(inputs["to"])
            )
        )
    return None


# ── QuantLib ────────────────────────────────────────────────────────────────


def quantlib_calendar(ql: Any, read: Mapping[str, Any]) -> Any:
    """QuantLib's calendar built from core's settlement calendar data: a
    bespoke calendar with its weekend and every closed day, never a holiday
    list of QuantLib's own."""
    calendar = Calendar.of(read)
    built = ql.BespokeCalendar(read.get("calendarId", "core"))
    for weekday in sorted(calendar.weekend):
        # QuantLib numbers Sunday 1 to Saturday 7.
        built.addWeekend((weekday + 1) % 7 + 1)
    for day in sorted(calendar.closed):
        built.addHoliday(ql.Date(day.day, day.month, day.year))
    return built


def _day(ql: Any, text: str) -> Any:
    held = date.fromisoformat(text)
    return ql.Date(held.day, held.month, held.year)


def _iso(ql_date: Any) -> str:
    return date(ql_date.year(), ql_date.month(), ql_date.dayOfMonth()).isoformat()


DAY_COUNTS = {
    "actual_360": lambda ql: ql.Actual360(),
    "actual_365_fixed": lambda ql: ql.Actual365Fixed(),
    "thirty_360_bond_basis": lambda ql: ql.Thirty360(ql.Thirty360.BondBasis),
}


def computed(ql: Any, case_set: Mapping[str, Any], case: Mapping[str, Any]) -> str:
    """One case's answer as the installed QuantLib computes it, as text: a
    date in ISO 8601, a count, or a number by its repr."""
    inputs, kind = case["inputs"], case["kind"]
    if kind in ("advance", "business_days_between"):
        calendar = quantlib_calendar(ql, case_set["calendar"])
        if kind == "advance":
            moved = calendar.advance(_day(ql, inputs["date"]), int(inputs["days"]), ql.Days)
            return _iso(moved)
        return str(
            calendar.businessDaysBetween(_day(ql, inputs["from"]), _day(ql, inputs["to"]))
        )
    if kind == "year_fraction":
        counted = DAY_COUNTS[case["setup"]["day_count"]](ql)
        return repr(
            float(counted.yearFraction(_day(ql, inputs["from"]), _day(ql, inputs["to"])))
        )
    raise ValueError(f"no case of kind {kind!r}")


def within(expected: str, got: str, tolerance: Mapping[str, str]) -> bool:
    """Whether `got` is `expected` within the case's tolerance: a date or a
    count exactly; a number by the tolerance's kind."""
    kind, bound = tolerance["kind"], Decimal(tolerance["value"])
    if kind not in TOLERANCE_KINDS:
        raise ValueError(f"no tolerance of kind {kind!r}")
    try:
        want, have = Decimal(expected), Decimal(got)
    except ArithmeticError:
        return expected == got
    gap = abs(have - want)
    if kind == "relative":
        return gap <= bound * abs(want)
    if kind == "vol_points":
        return gap * 100 <= bound
    if kind == "basis_points":
        return gap * 10_000 <= bound
    return gap <= bound


def drift(ql: Any, case_set: Mapping[str, Any]) -> list[str]:
    """Each case the installed QuantLib answers outside its tolerance."""
    out = []
    for case in case_set["cases"]:
        got = computed(ql, case_set, case)
        if not _same(case["expected"], got, case["tolerance"]):
            out.append(f"{case_set['case_set']}/{case['name']}: {case['expected']} != {got}")
    return out


def _same(expected: str, got: str, tolerance: Mapping[str, str]) -> bool:
    try:
        date.fromisoformat(expected)
    except ValueError:
        return within(expected, got, tolerance)
    return expected == got


def regenerate(ql: Any, case_set: dict[str, Any]) -> dict[str, Any]:
    """The case set with every answer recomputed by the installed QuantLib:
    only on a deliberate version bump (Q12), its diff reviewed."""
    version = str(ql.__version__)
    if version != PINNED:
        raise SystemExit(f"QuantLib {version} is installed; the pin is {PINNED}")
    out = dict(case_set, quantlib=version)
    out["cases"] = [
        dict(case, expected=computed(ql, case_set, case)) for case in case_set["cases"]
    ]
    return out


def main(argv: Sequence[str]) -> int:
    """`python -m oracle --live` checks every set against the installed
    QuantLib; `python -m oracle --write <set>` prints a set regenerated, for
    the caller to write (never written from inside a container)."""
    import QuantLib as ql  # noqa: N813 - its own name

    if argv[:1] == ["--write"] and len(argv) == 2:
        sys.stdout.write(canonical(regenerate(ql, load(Path(argv[1])))).decode() + "\n")
        return 0
    if argv[:1] == ["--live"]:
        if str(ql.__version__) != PINNED:
            print(
                f"QuantLib {ql.__version__} is installed; the pin is {PINNED}", file=sys.stderr
            )
            return 1
        found = [line for path in case_sets() for line in drift(ql, load(path))]
        for line in found:
            print(line, file=sys.stderr)
        print(
            f"oracle: {len(case_sets())} case sets, {len(found)} drifted from QuantLib {PINNED}"
        )
        return 1 if found else 0
    print("python -m oracle --live | --write <case set>", file=sys.stderr)
    return 2
