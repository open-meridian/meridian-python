"""The behaviour cases this SDK holds its helpers and common logic to (SDK
0.35; spec/each-role-is-one-generated-class, section 3, ruling 1009).

The suites hold a plugin to its role by what it sends; behaviour cases hold
an SDK to what its helpers and a role's common logic do, so every SDK --
this one, and TypeScript's and Rust's when they exist -- does the same.
They are meridian-schema's `boundaries/behaviours.json`, generated from
meridian-design's `matrix/boundaries/behaviours/`, vendored here beside the
suites. Each case names its subject by a path the same in every SDK
(`helpers.sessions.Backoff`, `roles.data.Wants`) and is one of three kinds:

- **value**: a call given arguments, and its answer, or its refusal naming
  the field refused;
- **steps**: calls on a fake clock, moved to a step's `clock` first, each
  answering a value or one within `at_least` and `at_most`;
- **acts**: deliveries heard by the subject over a fake source, and the
  rows it sends, matched as a suite case's `expect` is.

Each SDK maps every subject it carries to its own API with an adapter, and
runs every case in its own tests:

    report = meridian.behaviours.run(meridian.behaviours.ADAPTERS)
    assert report.passed, report.failures

A case whose subject has no adapter fails, as a suite case with no producer
does. Plugins never run these; they run the suites. Design's coverage gate
holds every case's subject to an adapter `SUBJECTS` names, and every
subject there to at least one case.
"""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from importlib import resources
from typing import Any

from google.protobuf import json_format

__all__ = ["ADAPTERS", "SUBJECTS", "Case", "Report", "cases", "run", "run_async"]


@dataclass(frozen=True)
class Case:
    """One behaviour case, as behaviours.json holds it."""

    module: str
    name: str
    subject: str
    kind: str
    held: Mapping[str, Any]


@dataclass
class Report:
    passed_cases: list[str] = field(default_factory=list)
    failures: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.failures


def cases() -> list[Case]:
    """Every behaviour case, in its module's order."""
    text = resources.files("meridian").joinpath("behaviours.json").read_text(encoding="utf-8")
    found = []
    for module in json.loads(text)["behaviours"]:
        for case in module["cases"]:
            found.append(
                Case(module["module"], case["name"], case["subject"], case["kind"], case)
            )
    return found


#: An adapter: given a case, it runs the SDK's own API for the case's
#: subject and raises AssertionError naming what differs.
Adapter = Callable[[Case], Awaitable[None] | None]


def run(adapters: Mapping[str, Adapter]) -> Report:
    """`run_async`, from a plain test: not from inside a running event loop."""
    return asyncio.run(run_async(adapters))


async def run_async(adapters: Mapping[str, Adapter]) -> Report:
    """Every case run by the adapter for its subject; a case with none fails."""
    report = Report()
    for case in cases():
        adapter = adapters.get(case.subject)
        if adapter is None:
            report.failures[case.name] = f"no adapter for {case.subject}"
            continue
        try:
            done = adapter(case)
            if done is not None:
                await done
        except Exception as failed:  # noqa: BLE001 - a case's failure, reported
            report.failures[case.name] = f"{type(failed).__name__}: {failed}"
            continue
        report.passed_cases.append(case.name)
    return report


# ── The kinds ──────────────────────────────────────────────────────────


def plain(value: Any) -> Any:
    """A value as a case writes it: a Decimal or a date as its text, a tuple
    as a list."""
    if isinstance(value, Decimal | date):
        # As the SDK writes it: a case compares the text, so an exponent
        # (1.5E+2 for 150) fails it.
        return str(value)
    if isinstance(value, tuple | list):
        return [plain(each) for each in value]
    if isinstance(value, dict):
        return {key: plain(each) for key, each in value.items()}
    return value


def value_case(call: Callable[[str, Mapping[str, Any]], Any]) -> Adapter:
    """An adapter for value cases: `call(name, args)` answers the case's
    value, in the case's terms, or raises refusing it."""

    def adapter(case: Case) -> None:
        expect = case.held["expect"]
        args = case.held.get("args") or {}
        if "refused" in expect:
            try:
                answered = call(case.held["call"], args)
            except (TypeError, ValueError) as refused:
                if expect["refused"] not in str(refused):
                    raise AssertionError(
                        f"refused, but naming no {expect['refused']}: {refused}"
                    ) from refused
                return
            raise AssertionError(f"answered {answered!r} where {expect['refused']} is refused")
        answered = plain(call(case.held["call"], args))
        if answered != expect["value"]:
            raise AssertionError(f"answered {answered!r}, not {expect['value']!r}")

    return adapter


class Clock:
    """The fake clock a steps case moves, in seconds."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def steps_case(
    made: Callable[[Mapping[str, Any], Clock], Any],
    call: Callable[[Any, str, Mapping[str, Any]], Mapping[str, Any] | None],
) -> Adapter:
    """An adapter for steps cases: `made(given, clock)` builds the subject on
    the fake clock, and `call(subject, name, args)` makes one step's call,
    answering its values by name."""

    def adapter(case: Case) -> None:
        clock = Clock()
        subject = made(case.held.get("given") or {}, clock)
        for i, step in enumerate(case.held.get("steps") or []):
            if "clock" in step:
                clock.now = float(step["clock"])
            answered = call(subject, step["call"], step.get("args") or {}) or {}
            for name, wanted in (step.get("expect") or {}).items():
                got = answered.get(name)
                if isinstance(wanted, dict) and ("at_least" in wanted or "at_most" in wanted):
                    low = float(wanted.get("at_least", float("-inf")))
                    high = float(wanted.get("at_most", float("inf")))
                    if got is None or not low <= float(got) <= high:
                        raise AssertionError(
                            f"steps[{i}] {step['call']}: {name} is {got}, not within "
                            f"{low} to {high}"
                        )
                elif plain(got) != wanted:
                    raise AssertionError(f"steps[{i}] {step['call']}: {name} is {got!r}")

    return adapter


def acts_case(
    drive: Callable[[Mapping[str, Any], Any, list[tuple[str, Any]]], Awaitable[None]],
) -> Adapter:
    """An adapter for acts cases: `drive(given, recorder, heard)` makes the
    subject over the suites' recorder and hands it each delivery; the rows
    it sent are matched as a suite case's are."""
    from .operations import CONFLATED, DELIVERED, SEQUENCED, UNCONFLATED
    from .suites import Case as SuiteCase
    from .suites import Expectation, Recorder, check

    rows: list[Any] = [*DELIVERED, *CONFLATED, *UNCONFLATED, *SEQUENCED]
    messages = {row.name: row.message for row in rows}

    async def adapter(case: Case) -> None:
        given = case.held.get("given") or {}
        recorder = Recorder(str(given.get("instance", "behaviour-1")))
        heard = []
        for each in case.held.get("heard") or []:
            message = json_format.ParseDict(each["message"], messages[each["row"]]())
            heard.append((each["row"], message))
        await drive(given, recorder, heard)
        expected = tuple(
            Expectation(
                row=each["row"],
                fields=each.get("fields"),
                sends=bool(each.get("sends", True)),
                any_of=tuple(each.get("any_of") or ()),
            )
            for each in case.held.get("sends") or []
        )
        why = check(SuiteCase(case.name, "", expected), recorder)
        if why is not None:
            raise AssertionError(why)

    return adapter


# ── This SDK's adapters ────────────────────────────────────────────────


def _backoff(given: Mapping[str, Any], clock: Clock) -> Any:
    from .helpers.sessions import Backoff

    return Backoff(
        given["first_s"],
        given["most_s"],
        given["jitter"],
        given["steady_s"],
        clock=clock,
        rng=random.Random(given.get("seed")),
    )


def _backoff_step(backoff: Any, name: str, args: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if name == "failed":
        return {"wait_s": backoff.failed()}
    if name == "steady":
        backoff.steady()
        return None
    raise AssertionError(f"Backoff has no step {name!r}")


def _backoff_made(name: str, args: Mapping[str, Any]) -> Any:
    from .helpers.sessions import Backoff

    if name != "make":
        raise AssertionError(f"Backoff has no call {name!r}")
    Backoff(args["first_s"], args["most_s"], args["jitter"], args["steady_s"])
    return None


def _backoff_adapter(case: Case) -> Awaitable[None] | None:
    if case.kind == "steps":
        return steps_case(_backoff, _backoff_step)(case)
    return value_case(_backoff_made)(case)


def _debt(name: str, args: Mapping[str, Any]) -> Any:
    from .helpers import debt

    if name == "capped":
        amount, capped = debt.capped(args["size"])
        return {"amount": str(amount), "capped": capped}
    return getattr(debt, name)(**args)


def _chains(name: str, args: Mapping[str, Any]) -> Any:
    from .helpers import chains

    if name == "osi_terms":
        root, expiration, right, strike = chains.osi_terms(args["symbol"])
        return {"root": root, "expiration": expiration, "right": right, "strike": strike}
    return getattr(chains, name)(**args)


async def _wants(given: Mapping[str, Any], recorder: Any, heard: list[tuple[str, Any]]) -> None:
    from .receive import Heard
    from .roles.data import Wants

    wants = Wants(recorder, tuple(given.get("keys") or ()))
    declines = dict(given.get("declines") or {})

    async def answer(
        want: Any, key: str, subjects: list[str], kinds: tuple[int, ...]
    ) -> dict[str, str]:
        if given.get("fails"):
            raise RuntimeError("the source failed")
        return {subject: declines[subject] for subject in subjects if subject in declines}

    for row, message in heard:
        await wants.hear(Heard(row=row, message=message), answer)


#: This SDK's adapter for each subject it carries.
ADAPTERS: Mapping[str, Adapter] = {
    "helpers.sessions.Backoff": _backoff_adapter,
    "helpers.debt.to_cent": value_case(_debt),
    "helpers.debt.percent_of_par": value_case(_debt),
    "helpers.debt.current_face": value_case(_debt),
    "helpers.debt.paydown_cash": value_case(_debt),
    "helpers.debt.capped": value_case(_debt),
    "helpers.chains.osi_symbol": value_case(_chains),
    "helpers.chains.osi_terms": value_case(_chains),
    "roles.data.Wants": acts_case(_wants),
}

#: The subjects this SDK carries, which design's coverage gate reads: a
#: literal, so the gate need not import the SDK.
SUBJECTS: Sequence[str] = (
    "helpers.sessions.Backoff",
    "helpers.debt.to_cent",
    "helpers.debt.percent_of_par",
    "helpers.debt.current_face",
    "helpers.debt.paydown_cash",
    "helpers.debt.capped",
    "helpers.chains.osi_symbol",
    "helpers.chains.osi_terms",
    "roles.data.Wants",
)
