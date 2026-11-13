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
import contextlib
import json
import random
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from importlib import resources
from typing import Any, cast

from google.protobuf import json_format

__all__ = [
    "ADAPTERS",
    "HELD_MODULES",
    "NOT_HELD",
    "SUBJECTS",
    "Case",
    "Report",
    "cases",
    "run",
    "run_async",
]


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
    call: Callable[[Any, str, Mapping[str, Any]], Any],
) -> Adapter:
    """An adapter for steps cases: `made(given, clock)` builds the subject on
    the fake clock, and `call(subject, name, args)` makes one step's call,
    answering its values by name. Either may be a coroutine. A step
    expecting `refused` passes where its call raises naming that word."""

    async def adapter(case: Case) -> None:
        clock = Clock()
        subject = made(case.held.get("given") or {}, clock)
        if asyncio.iscoroutine(subject):
            subject = await subject
        try:
            for i, step in enumerate(case.held.get("steps") or []):
                if "clock" in step:
                    clock.now = float(step["clock"])
                expect = step.get("expect") or {}
                try:
                    answered = call(subject, step["call"], step.get("args") or {})
                    if asyncio.iscoroutine(answered) or isinstance(answered, Awaitable):
                        answered = await answered
                except (TypeError, ValueError) as refused:
                    word = expect.get("refused")
                    if word is None:
                        raise
                    if str(word).lower() not in str(refused).lower():
                        raise AssertionError(
                            f"steps[{i}] {step['call']}: refused, naming no {word}: {refused}"
                        ) from refused
                    continue
                if "refused" in expect:
                    raise AssertionError(
                        f"steps[{i}] {step['call']}: answered where {expect['refused']} is "
                        "refused"
                    )
                answered = answered or {}
                for name, wanted in expect.items():
                    got = answered.get(name)
                    if isinstance(wanted, dict) and (
                        "at_least" in wanted or "at_most" in wanted
                    ):
                        low = float(wanted.get("at_least", float("-inf")))
                        high = float(wanted.get("at_most", float("inf")))
                        if got is None or not low <= float(got) <= high:
                            raise AssertionError(
                                f"steps[{i}] {step['call']}: {name} is {got}, not within "
                                f"{low} to {high}"
                            )
                    elif plain(got) != wanted:
                        said = f"{name} is {plain(got)!r}, not {wanted!r}"
                        raise AssertionError(f"steps[{i}] {step['call']}: {said}")
        finally:
            closing = getattr(subject, "close", None)
            if callable(closing):
                done = closing()
                if asyncio.iscoroutine(done):
                    await done

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


# ── 0.35, part B: 924's helpers (rulings 924, 1009, 1016, 1017) ────────


def _iso_ns(text: str) -> int:
    from datetime import UTC, datetime

    moment = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return int(moment.timestamp()) * 1_000_000_000


def _iso_of(at_ns: int) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(at_ns / 1e9, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day(text: Any) -> date:
    return text if isinstance(text, date) else date.fromisoformat(str(text))


def _backoff_of(given: Mapping[str, Any], clock: Clock) -> Any:
    from .helpers.sessions import Backoff

    return Backoff(
        given["first_s"],
        given["most_s"],
        given["jitter"],
        given["steady_s"],
        clock=clock,
        rng=random.Random(given.get("seed", 0)),
    )


class _Refused(Exception):
    """The fake source refused the key."""


class _Statement:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol


class _SupervisorHarness:
    """A `Supervisor` running over a scripted link on the fake clock: each
    open answered as the next step says, each statement heard put to its
    `receive`, each wait recorded and held until the next open."""

    def __init__(self, given: Mapping[str, Any], clock: Clock) -> None:
        from .helpers.sessions import Supervisor

        self.clock = clock
        self.opens: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        self.received: asyncio.Queue[list[Any]] = asyncio.Queue()
        self.waits: list[float] = []
        self.caught: dict[str, int] | None = None
        self.release = asyncio.Event()
        self.sleeping = False
        harness = self

        class Link:
            name = "behaviour"

            async def open(self) -> None:
                said, asked = await harness.opens.get()
                failed: Exception | None = None
                if said == "fail":
                    failed = ConnectionError("the source did not answer")
                elif said == "refuse":
                    failed = _Refused("the key was refused")
                if failed is not None:
                    if asked is not None:
                        # A source's Retry-After, as the failure carries it
                        # (0.35.3): a value that is no number is ignored.
                        failed.retry_after = asked  # type: ignore[attr-defined]
                    raise failed

            async def subscribe(self, wanted: Sequence[str]) -> None:
                return None

            async def receive(self) -> list[Any]:
                return await harness.received.get()

            async def close(self) -> None:
                return None

        async def heard(stated: list[Any]) -> None:
            return None

        async def caught_up(since: dict[str, int]) -> int:
            harness.caught = {k: v // 1_000_000_000 for k, v in since.items()}
            return 0

        async def sleep(seconds: float) -> None:
            harness.waits.append(seconds)
            harness.sleeping = True
            try:
                await harness.release.wait()
            finally:
                harness.release.clear()
                harness.sleeping = False

        self.supervisor = Supervisor(
            (lambda: None) if given.get("no_key") else Link,
            heard=heard,
            caught_up=caught_up,
            silent_seconds=float(given["silent_s"]),
            refused=(_Refused,),
            refused_seconds=float(given["refused_s"]),
            flush_seconds=0.001,
            backoff=_backoff_of(given, clock),
            reopen_on_want=bool(given.get("reopen_on_want")),
            clock_ns=lambda: int(clock.now * 1_000_000_000),
            sleep=sleep,
            clock=clock,
        )
        self.supervisor.want(given.get("wanted") or [])
        self.task = asyncio.ensure_future(self.supervisor.run())

    async def settle(self, done: Callable[[], bool]) -> None:
        """Until the step's effect is seen (at most two seconds), and a few
        turns of the session's loop after."""
        for _ in range(1000):
            if done():
                break
            await asyncio.sleep(0.002)
        for _ in range(5):
            await asyncio.sleep(0.002)

    async def step(self, name: str, args: Mapping[str, Any]) -> Mapping[str, Any]:
        waited = len(self.waits)
        state = self.supervisor.state
        heard, opened = state.messages, state.opened
        self.caught = None
        done: Callable[[], bool]
        if name in ("open_fails", "opens", "open_refused"):
            if self.sleeping:
                self.release.set()
            said = {"open_fails": "fail", "opens": "ok"}.get(name, "refuse")
            await self.opens.put((said, args.get("retry_after_s")))
            if name == "opens":
                done = lambda: state.opened > opened and state.state == "open"  # noqa: E731
            else:
                done = lambda: len(self.waits) > waited  # noqa: E731
        elif name == "hears":
            await self.received.put([_Statement(str(args["subject"]))])
            done = lambda: state.messages > heard  # noqa: E731
        elif name == "hears_nothing":
            # A receive stating nothing (a heartbeat): a sign of life (0.35.3).
            await self.received.put([])
            done = lambda: state.messages > heard  # noqa: E731
        elif name == "want":
            wanted = tuple(args.get("wanted") or [])
            self.supervisor.want(wanted)
            done = lambda: (  # noqa: E731
                state.subscribed == wanted or state.state in ("off", "no key", "connecting")
            )
        elif name == "goes_silent":
            done = lambda: len(self.waits) > waited  # noqa: E731
        elif name == "idles":
            done = lambda: state.state in ("off", "no key")  # noqa: E731
        else:
            raise AssertionError(f"Supervisor has no step {name!r}")
        await self.settle(done)
        return {
            "state": state.state,
            "opened": state.opened,
            "dropped": state.dropped,
            "messages": state.messages,
            "subscribed": list(state.subscribed),
            "wait_s": self.waits[-1] if len(self.waits) > waited else None,
            "caught_up": self.caught,
        }

    async def close(self) -> None:
        self.task.cancel()
        with contextlib.suppress(BaseException):
            await self.task


def _supervisor_step(harness: Any, name: str, args: Mapping[str, Any]) -> Any:
    return harness.step(name, args)


def _day_clock(name: str, args: Mapping[str, Any]) -> Any:
    from .helpers.calendars import DayClock

    clock = DayClock(str(args["time_zone"]), int(args.get("end_minute", 0)))
    if name == "make":
        return None
    if name == "business_date_of":
        return clock.business_date_of(_iso_ns(args["at"]))
    if name == "close_of":
        return _iso_of(clock.close_of(_day(args["day"])))
    if name == "opened_at":
        return _iso_of(clock.opened_at(_day(args["day"])))
    raise AssertionError(f"DayClock has no call {name!r}")


class _Calendar:
    """The deployment's calendar as the fake answers it, through a role
    object's `read_calendar`, failing its first `fails` reads."""

    def __init__(self, given: Mapping[str, Any]) -> None:
        self.given = given
        self.reads = 0

    async def read_calendar(self, **_: Any) -> Any:
        from .plugin.v1 import operations_pb2 as ops

        self.reads += 1
        if self.reads <= int(self.given.get("fails", 0)):
            raise ConnectionError("the calendar did not answer")
        return ops.ReadCalendarResult(
            found=True,
            calendar_id=str(self.given.get("calendar_id", "CAL-1")),
            weekends=[
                ops.CalendarWeekend(
                    weekdays=[
                        cast(Any, ops.Weekday.Value(w))
                        for w in self.given.get("weekends") or []
                    ]
                )
            ],
            days=[
                ops.CalendarDay(date=str(d), kind=ops.CALENDAR_DAY_KIND_CLOSED)
                for d in self.given.get("closed") or []
            ],
        )


def _market_days(given: Mapping[str, Any], clock: Clock) -> Any:
    from .helpers.calendars import DayClock, MarketDays

    calendar = _Calendar(given)
    days = MarketDays(
        calendar,
        str(given.get("calendar_id", "CAL-1")),
        day_clock=DayClock(str(given["time_zone"]), int(given.get("end_minute", 0))),
        backoff=_backoff_of(given["backoff"], clock),
        clock=clock,
    )
    days.calendar = calendar  # type: ignore[attr-defined]
    return days


async def _market_days_step(days: Any, name: str, args: Mapping[str, Any]) -> Mapping[str, Any]:
    if name == "is_open":
        return {"open": await days.is_open(_day(args["day"])), "reads": days.calendar.reads}
    if name in ("previous_open", "next_open"):
        return {"day": await getattr(days, name)(_day(args["day"]))}
    if name == "business_date_of":
        return {"day": await days.business_date_of(_iso_ns(args["at"]))}
    raise AssertionError(f"MarketDays has no step {name!r}")


def _sent_rows(given: Mapping[str, Any], clock: Clock) -> Any:
    from .roles.data import SentRows

    return SentRows(int(given["capacity"]))


def _sent_rows_step(rows: Any, name: str, args: Mapping[str, Any]) -> Mapping[str, Any]:
    from .roles.data import SentRows

    if name == "make":
        SentRows(int(args["capacity"]))
        return {}
    if name == "changed":
        said = rows.changed(args["data_type"], args["dataset"], args["row_key"], args["said"])
        return {"changed": said}
    raise AssertionError(f"SentRows has no step {name!r}")


def _conflator(given: Mapping[str, Any], clock: Clock) -> Any:
    from .roles.data import Conflator

    return Conflator(
        int(float(given["every_s"]) * 1_000_000_000),
        clock_ns=lambda: int(clock.now * 1_000_000_000),
    )


def _conflator_step(held: Any, name: str, args: Mapping[str, Any]) -> Mapping[str, Any]:
    from .operations import Money, Outcome, Trade

    if name == "put":
        held.put(args["key"], args["value"])
        return {}
    if name == "due":
        return {"values": held.due()}
    if name == "put_trade":
        held.put(args["key"], Trade(price=Money(Decimal(1), "USD"), quantity=Decimal(1)))
        return {}
    if name == "put_outcome":
        held.put(args["key"], Outcome(settlement_value=Money(Decimal(1), "USD")))
        return {}
    raise AssertionError(f"Conflator has no step {name!r}")


class _Allowance:
    """A vendor's quota as a plugin keeps it: its limit and what is used."""

    def __init__(self, limit: int, used: int) -> None:
        self.limit, self.used = limit, used

    def allows(self, calls: int = 1, *, reserve: int = 0) -> bool:
        return self.limit - self.used - calls >= reserve

    def spend(self, calls: int = 1) -> None:
        self.used += calls


def _timetable(given: Mapping[str, Any], clock: Clock) -> Any:
    from .roles.data import Timetable

    quota = given.get("allowance")
    allowance = _Allowance(int(quota["limit"]), int(quota["used"])) if quota else None
    table = Timetable(
        allowance=allowance,
        reserve=int(given.get("reserve", 0)),
        clock_ns=lambda: int(clock.now * 1_000_000_000),
    )
    for dataset, every in (given.get("every_s") or {}).items():
        table.every(str(dataset), float(every))
    return table


async def _timetable_step(table: Any, name: str, args: Mapping[str, Any]) -> Mapping[str, Any]:
    if name == "want":
        table.want(args["dataset"], args["subjects"])
        return {}
    if name == "withdraw":
        table.withdraw(args["dataset"], args.get("subjects"))
        return {}
    if name == "every":
        table.every(str(args["dataset"]), float(args["every_s"]))
        return {}
    if name == "due":
        due = await table.due()
        used = table.allowance.used if table.allowance is not None else None
        return {"due": [[dataset, list(subjects)] for dataset, subjects in due], "used": used}
    raise AssertionError(f"Timetable has no step {name!r}")


def _timeliness(name: str, args: Mapping[str, Any]) -> Any:
    from .roles.data import TIMELINESS, timeliness

    given = {k: v for k, v in args.items() if k in ("choices", "default")}
    made = timeliness(str(args["label"]), given.pop("choices", TIMELINESS), **given)
    return {"choices": [c.value for c in made.choices], "default": made.default}


def _api_key(name: str, args: Mapping[str, Any]) -> Any:
    from .roles.data import api_key

    made = api_key(str(args["label"]))
    return {"required": made.required, "secret": made.secret}


def _stated(fields: Mapping[str, Any]) -> Any:
    """A statement as a source states it: numbers as Decimals."""
    from types import SimpleNamespace

    held: dict[str, Any] = {
        "raw_key": "behaviour/1",
        "unconverted": (),
        "venue_code": "",
        "cancelled": False,
        "participant_ns": None,
    }
    for key, value in fields.items():
        numeric = key in ("price", "quantity", "bid", "ask", "bid_size", "ask_size", "amount")
        held[key] = Decimal(str(value)) if numeric else value
    return SimpleNamespace(**held)


async def _listings(
    given: Mapping[str, Any], recorder: Any, heard: list[tuple[str, Any]]
) -> None:
    from .receive import Heard
    from .roles.data import listings
    from .roles.data.quality import EdgeChecks

    now = 3_000_000_000

    class Source:
        def daily(self, symbols: Sequence[str], first: date, last: date) -> list[Any]:
            return []

        def live(self, symbols: Sequence[str]) -> list[Any]:
            return [_stated(each) for each in given.get("live") or []]

        def quotes(self, symbols: Sequence[str]) -> list[Any]:
            return []

    class Lake(listings.Feed):
        source_name = str(given.get("source_name", "behaviour"))

    mics = dict(given.get("mic_of") or {})
    feed = recorder.bind(
        Lake(
            Source(),
            listings.Listings(None),
            clock_ns=lambda: now,
            timeliness=str(given.get("timeliness", "")),
            datasets_by_timeliness=given.get("datasets_by_timeliness"),
            mic_of=mics.get if mics else None,
        )
    )
    for subject, symbol in (given.get("symbols") or {}).items():
        feed.products.put(subject, symbol)
    if given.get("edge"):
        feed.quality = EdgeChecks(clock_ns=lambda: now)
    for row, message in heard:
        await feed.on_observations_wanted(Heard(row=row, message=message))
    for each in given.get("stream") or []:
        for _kind, fields in each.items():
            await feed.heard([_stated(fields)])
    await feed.flush(force=True)


_CHAIN_NUMBERS = ("bid", "ask", "bid_size", "ask_size", "open_interest", "volume")


_CHAIN_NUMBERS = ("bid", "ask", "bid_size", "ask_size", "open_interest", "volume")


async def _option_chains(
    given: Mapping[str, Any], recorder: Any, heard: list[tuple[str, Any]]
) -> None:
    from .helpers.calendars import DayClock, MarketDays
    from .plugin.v1 import operations_pb2 as ops
    from .receive import Heard
    from .roles.data import option_chains

    now = _iso_ns(given["now"])
    chains = given.get("chain") or {}

    class Source:
        def expirations(self, symbol: str) -> list[date]:
            return sorted(_day(d) for d in chains.get(symbol, {}))

        def chain(self, symbol: str, expiration: date) -> list[Any]:
            out = []
            for d, options in chains.get(symbol, {}).items():
                if _day(d) != expiration:
                    continue
                for o in options:
                    number = {k: Decimal(str(o[k])) if k in o else None for k in _CHAIN_NUMBERS}
                    out.append(
                        option_chains.ChainOption(
                            osi=o["osi"],
                            expiration=expiration,
                            quoted_at_ns=now,
                            bid=number["bid"],
                            ask=number["ask"],
                            bid_size=number["bid_size"],
                            ask_size=number["ask_size"],
                            open_interest=number["open_interest"],
                            volume=number["volume"],
                        )
                    )
            return out

    recorder.answer(
        "ReadCalendar",
        lambda _: ops.ReadCalendarResult(
            found=True,
            calendar_id="CAL-1",
            weekends=[
                ops.CalendarWeekend(
                    weekdays=[
                        cast(Any, ops.Weekday.Value(w)) for w in given.get("weekends") or []
                    ]
                )
            ],
        ),
    )
    days = MarketDays(recorder, "CAL-1", day_clock=DayClock("America/New_York", 960))
    symbols = dict(given.get("symbols") or {})

    async def symbol_of(subject: str) -> str | None:
        return symbols.get(subject)

    feed = recorder.bind(
        option_chains.Feed(
            Source(),
            market_days=days,
            timeliness=str(given.get("timeliness", "")),
            datasets_by_timeliness=given.get("datasets_by_timeliness"),
            symbol_of=symbol_of,
            clock_ns=lambda: now,
        )
    )
    for row, message in heard:
        await feed.on_observations_wanted(Heard(row=row, message=message))


def _load(given: Mapping[str, Any], clock: Clock) -> Any:
    """`client.load_wait` as its cases give it: its jitter, and a seeded
    random source for the jitter."""
    import random

    return {"jitter": float(given.get("jitter", 0.2)), "rng": random.Random(given.get("seed"))}


def _load_step(held: Any, name: str, args: Mapping[str, Any]) -> Mapping[str, Any]:
    """A refusal heard (`refused`): whether it is asked again, and after how
    long (contract v30, the resilience spec's section 10a; W4.4)."""
    import grpc

    from .client import load_wait
    from .v1 import sidecar_pb2

    if name != "refused":
        raise AssertionError(f"client.load_wait has no step {name!r}")
    refusal = sidecar_pb2.Refusal(
        reason=str(args["reason"]),
        retry_after_seconds=int(args.get("retry_after_s", 0)),
    )
    wait = load_wait(
        refusal,
        getattr(grpc.StatusCode, str(args["status"])),
        float(args["left_s"]),
        jitter=held["jitter"],
        rng=held["rng"],
    )
    return {"asks_again": wait is not None, "wait_s": wait}


def _views(name: str, args: Mapping[str, Any]) -> Any:
    """`views.latest_key`'s `same_key`: whether two lake rows share the key a
    view keeps the latest by (SDK 0.35.3, the cases contract 30 holds)."""
    from .operations import CONFLATED
    from .views import _latest_key

    if name != "same_key":
        raise AssertionError(f"views.latest_key has no call {name!r}")
    keys = []
    for given in (args["one"], args["other"]):
        row = next(each for each in CONFLATED if each.name == given["row"])
        event = json_format.ParseDict(
            {k: v for k, v in given.items() if k != "row"}, row.message()
        )
        keys.append(_latest_key(getattr(event, row.within)))
    return keys[0] == keys[1]


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
    "helpers.sessions.Supervisor": steps_case(_SupervisorHarness, _supervisor_step),
    "helpers.calendars.DayClock": value_case(_day_clock),
    "helpers.calendars.MarketDays": steps_case(_market_days, _market_days_step),
    "roles.data.SentRows": steps_case(_sent_rows, _sent_rows_step),
    "roles.data.Conflator": steps_case(_conflator, _conflator_step),
    "roles.data.Timetable": steps_case(_timetable, _timetable_step),
    "roles.data.timeliness": value_case(_timeliness),
    "roles.data.api_key": value_case(_api_key),
    "roles.data.listings.Feed": acts_case(_listings),
    "roles.data.option_chains.Feed": acts_case(_option_chains),
    "views.latest_key": value_case(_views),
    "client.load_wait": steps_case(_load, _load_step),
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
    "helpers.sessions.Supervisor",
    "helpers.calendars.DayClock",
    "helpers.calendars.MarketDays",
    "roles.data.SentRows",
    "roles.data.Conflator",
    "roles.data.Timetable",
    "roles.data.timeliness",
    "roles.data.api_key",
    "roles.data.listings.Feed",
    "roles.data.option_chains.Feed",
    "views.latest_key",
    "client.load_wait",
)

#: The modules beside `meridian.helpers` whose helpers and common logic are
#: held to behaviour cases (rulings 1028 and 924's items), each with the
#: subject path its public names take. Design's coverage gate reads every
#: public class and function of every `meridian/helpers/*.py` module and of
#: each of these: each is a subject in SUBJECTS with a case, or is named in
#: NOT_HELD with why -- so a helper added with no case fails the gate.
HELD_MODULES: Mapping[str, str] = {
    "src/meridian/roles/data/_rows.py": "roles.data",
    "src/meridian/roles/data/_timetable.py": "roles.data",
    "src/meridian/roles/data/_settings.py": "roles.data",
    "src/meridian/roles/data/option_chains.py": "roles.data.option_chains",
}

#: What the gate's scan finds that no case holds, and why: a type a helper
#: names (no behaviour of its own), or a helper from before 0.35 whose cases
#: are owed -- the list each SDK release shortens.
NOT_HELD: Mapping[str, str] = {
    "helpers.sessions.Link": "a type: the plugin's session, scripted by Supervisor's cases",
    "helpers.sessions.SessionState": "a type: Supervisor's state, which its cases read",
    "helpers.sessions.Silent": "a type: a session gone silent, as Supervisor's cases see it",
    "helpers.sessions.read_sessions": "a read the sidecar answers (contract 30, ruling 455), "
    "held by tests/test_sdk_036.py",
    "helpers.debt.CouponSplit": "a type: a coupon's split, which coupon_split answers",
    "helpers.packages.LegFill": "a type: a leg's fill, which report_fill takes",
    "roles.data.option_chains.ChainOption": "a type: a series as the source states it",
    "roles.data.option_chains.SourceTrade": "a type: an option trade, as the source says",
    "roles.data.option_chains.ChainSource": "a type: the source, faked by its cases",
    "roles.data.option_chains.Counts": "a type: the Datasets page's counts",
    "roles.data.option_chains.SeriesTimes": "0.36.3, the Feed's own holder made public: "
    "held by tests/test_sdk_0363.py and the Feed's cases",
    "helpers.chains.osi_key": "before 0.35: its cases are owed",
    "helpers.chains.series_meta": "before 0.35: its cases are owed",
    "helpers.chains.option_series": "before 0.35: its cases are owed",
    "helpers.chains.statistic": "before 0.35: its cases are owed",
    "helpers.chains.read_expirations": "before 0.35: its cases are owed",
    "helpers.chains.read_chain": "before 0.35: its cases are owed",
    "helpers.chains.read_open_interest": "before 0.35: its cases are owed",
    "helpers.chains.want_series": "before 0.35: its cases are owed",
    "helpers.debt.fill_cash": "before 0.35: its cases are owed",
    "helpers.debt.relief": "before 0.35: its cases are owed",
    "helpers.debt.coupon_split": "before 0.35: its cases are owed",
    "helpers.debt.year_fraction": "before 0.35: its cases are owed",
    "helpers.debt.coupon_dates": "before 0.35: its cases are owed",
    "helpers.debt.coupon_period": "before 0.35: its cases are owed",
    "helpers.debt.accrued_per100": "before 0.35: its cases are owed",
    "helpers.debt.factor_month": "before 0.35: its cases are owed",
    "helpers.debt.settlement_month": "before 0.35: its cases are owed",
    "helpers.debt.factor": "before 0.35: its cases are owed",
    "helpers.debt.quoted_yield": "before 0.35: its cases are owed",
    "helpers.debt.characteristics": "before 0.35: its cases are owed",
    "helpers.debt.read_factors": "before 0.35: its cases are owed",
    "helpers.debt.latest": "before 0.35: its cases are owed",
    "helpers.debt.taken": "before 0.35: its cases are owed",
    "helpers.debt.awaited": "before 0.35: its cases are owed",
    "helpers.debt.open_claims": "before 0.35: its cases are owed",
    "helpers.lifecycle.expiry": "before 0.35: its cases are owed",
    "helpers.lifecycle.assignment": "before 0.35: its cases are owed",
    "helpers.lifecycle.exercise": "before 0.35: its cases are owed",
    "helpers.lifecycle.variation": "before 0.35: its cases are owed",
    "helpers.lifecycle.report": "before 0.35: its cases are owed",
    "helpers.lifecycle.in_the_money": "before 0.35: its cases are owed",
    "helpers.lifecycle.exercise_by_exception": "before 0.35: its cases are owed",
    "helpers.lifecycle.propose": "before 0.35: its cases are owed",
    "helpers.lifecycle.due_for_release": "before 0.35: its cases are owed",
    "helpers.lifecycle.release": "before 0.35: its cases are owed",
    "helpers.lifecycle.read_events": "before 0.35: its cases are owed",
    "helpers.lifecycle.coupon_received": "before 0.35: its cases are owed",
    "helpers.lifecycle.redemption": "before 0.35: its cases are owed",
    "helpers.lifecycle.paydown": "before 0.35: its cases are owed",
    "helpers.lifecycle.accretion": "before 0.35: its cases are owed",
    "helpers.lifecycle.tba_allocation": "before 0.35: its cases are owed",
    "helpers.lifecycle.strip": "before 0.35: its cases are owed",
    "helpers.lifecycle.reconstitution": "before 0.35: its cases are owed",
    "helpers.lifecycle.expected_coupon": "before 0.35: its cases are owed",
    "helpers.lifecycle.expected_maturity": "before 0.35: its cases are owed",
    "helpers.lifecycle.expected_paydown": "before 0.35: its cases are owed",
    "helpers.lifecycle.settle_claim": "before 0.35: its cases are owed",
    "helpers.packages.legs": "before 0.35: its cases are owed",
    "helpers.packages.propose": "before 0.35: its cases are owed",
    "helpers.packages.report_fill": "before 0.35: its cases are owed",
}
