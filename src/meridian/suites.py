"""The role suites, and a runner a plugin holds itself to (contract v11).

spec/vendor-differences-have-a-place-in-the-contract, requirements 18, 20,
21 and 34: the canonical role is the requirement, and a plugin holding a role
is verified for it only by passing every case of the role's suite. Nothing is
declared about what a plugin supports. Each case says, in the contract's
words, what the plugin's source presents, and what the plugin sends; the
plugin maps each case to its own recorded or synthetic exchange with its
source, runs its own conversion against a `Recorder` -- the plugin's typed
operations, recorded rather than sent -- and the runner compares what it sent
with the case. The outcome is tested, never the route: a value the source did
not send is expected with its provenance stated, however the plugin closed it.

    from meridian.suites import run

    async def holdings_unavailable(recorder):
        await my_sync(recorder, synthetic("holdings_unavailable"))

    report = run("custody", {"sync-holdings-unavailable": holdings_unavailable, ...})
    assert report.passed, report.failures

A case asserting one value of a closed list (`closed_list`) a plugin's source
never presents may be named in `not_presented`, with why; every other case is
required, and a case with no producer fails. The suites are meridian-schema's
`boundaries/suites.json`, vendored with the bindings.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from importlib import resources
from typing import Any

from google.protobuf.message import Message

from .operations import Operations, as_decimal
from .plugin.v1 import operations_pb2 as ops

SET, UNSET = "<set>", "<unset>"


@dataclass(frozen=True)
class Expectation:
    row: str
    fields: Mapping[str, Any] | None = None
    sends: bool = True


@dataclass(frozen=True)
class Case:
    name: str
    given: str
    expect: tuple[Expectation, ...]
    closed_list: str = ""


@dataclass(frozen=True)
class Suite:
    role: str
    since: str
    says: str
    cases: tuple[Case, ...]

    def case(self, name: str) -> Case:
        for case in self.cases:
            if case.name == name:
                return case
        raise KeyError(f"the {self.role} suite has no case {name!r}")


def suites() -> dict[str, Suite]:
    """Every role's suite, by role."""
    text = resources.files("meridian").joinpath("suites.json").read_text(encoding="utf-8")
    out: dict[str, Suite] = {}
    for suite in json.loads(text).get("suites", []):
        out[suite["role"]] = Suite(
            role=suite["role"],
            since=suite["since"],
            says=suite["says"],
            cases=tuple(
                Case(
                    name=case["name"],
                    given=case["given"],
                    closed_list=case.get("closed_list", ""),
                    expect=tuple(
                        Expectation(
                            row=expected["row"],
                            fields=expected.get("fields"),
                            sends=expected.get("sends", True),
                        )
                        for expected in case.get("expect", [])
                    ),
                )
                for case in suite["cases"]
            ),
        )
    return out


def suite(role: str) -> Suite:
    found = suites().get(role)
    if found is None:
        raise KeyError(f"no suite for {role!r}; there are suites for {sorted(suites())}")
    return found


@dataclass(frozen=True)
class Sent:
    """One typed operation a plugin called: its row, and the params."""

    row: str
    params: Message


class _Recording:
    """What `Recorder._operations()` answers: any operation, by its name."""

    def __getattr__(self, row: str) -> str:
        return row


class Recorder(Operations):
    """A plugin's typed operations, recorded rather than sent.

    Each call is kept as a `Sent` and answered as a sidecar would answer it
    in the ordinary case: a statement opened, a row recorded and resolved, an
    identifier resolved to a record this recorder names, a link made, no
    accounts to link to. `raw_record` and `note_not_carried` behave as a
    plugin's do. Use `answer` to answer a row otherwise."""

    def __init__(self, instance_id: str = "suite-plugin") -> None:
        self.instance_id = instance_id
        self.sent: list[Sent] = []
        self.seen: dict[tuple[str, str], int] = {}
        self._answers: dict[str, Callable[[Message], Message]] = {}

    def answer(self, row: str, reply: Callable[[Message], Message]) -> None:
        self._answers[row] = reply

    def raw_record(self, key: str) -> ops.RawRecordRef:
        from .edge import raw_record

        return raw_record(key, self.instance_id)

    def note_not_carried(self, scheme: str, name: str) -> None:
        self.seen[(scheme, name)] = self.seen.get((scheme, name), 0) + 1

    def _operations(self) -> Any:
        return _Recording()

    async def _operate(self, method: Any, params: Any) -> Any:
        from .statements import checked

        checked(params)
        row = str(method)
        self.sent.append(Sent(row, params))
        if row in self._answers:
            return self._answers[row](params)
        return _ordinary(row, params, len(self.sent))

    def on(self, row: str) -> list[Message]:
        return [sent.params for sent in self.sent if sent.row == row]


def _ordinary(row: str, params: Any, n: int) -> Message:
    if row == "RecordHoldingsStatement":
        return ops.RecordHoldingsStatementResult(statement_id=f"STMT-suite-{n}")
    if row == "RecordHolding":
        return ops.RecordHoldingResult(
            holding_id=f"HLD-suite-{n}", resolved=bool(params.instrument_id)
        )
    if row == "ResolveIdentifier":
        return ops.ResolveIdentifierResult(
            found=True, instrument_id=f"LCL-suite-{n}", minted=True
        )
    if row == "ReadAccountsForLinking":
        return ops.ReadAccountsForLinkingResult()
    if row == "LinkExternalAccount":
        return ops.LinkExternalAccountResult(
            external_account_id=params.external_account_id, account_id=f"ACC-suite-{n}"
        )
    return ops.Published(message_id=f"suite-{n}")


# ── Matching ────────────────────────────────────────────────────────────────


def _repeated(descriptor: Any) -> bool:
    """Whether a field is repeated, without protobuf's deprecated `label`
    where the runtime offers `is_repeated`."""
    if hasattr(type(descriptor), "is_repeated"):
        return bool(descriptor.is_repeated)
    return bool(descriptor.label == descriptor.LABEL_REPEATED)


def _present(message: Message, name: str) -> bool:
    descriptor = message.DESCRIPTOR.fields_by_name[name]
    if _repeated(descriptor):
        return len(getattr(message, name)) > 0
    if descriptor.message_type is not None or descriptor.has_presence:
        return message.HasField(name)
    return bool(getattr(message, name))


def _same(message: Message, name: str, wanted: Any) -> str | None:
    """Why the field `name` of `message` is not `wanted`, or None."""
    descriptor = message.DESCRIPTOR.fields_by_name.get(name)
    if descriptor is None:
        return f"{message.DESCRIPTOR.name} has no field {name}"
    if wanted == SET:
        return None if _present(message, name) else f"{name} is unset"
    if wanted == UNSET:
        return None if not _present(message, name) else f"{name} is set"
    value = getattr(message, name)
    if _repeated(descriptor):
        if not isinstance(wanted, list):
            return f"{name} is repeated and the case names {wanted!r}"
        for i, part in enumerate(wanted):
            if not any(_matches(element, part) is None for element in value):
                return f"{name}[{i}] matches no element of {name}: {part!r}"
        return None
    if descriptor.enum_type is not None:
        held = descriptor.enum_type.values_by_number.get(value)
        named = held.name if held is not None else str(value)
        return None if named == wanted else f"{name} is {named}, not {wanted}"
    if descriptor.message_type is not None:
        if not message.HasField(name):
            return f"{name} is unset"
        if descriptor.message_type.name == "Decimal":
            return _decimal_same(name, as_decimal(value), wanted)
        if isinstance(wanted, Mapping):
            why = _matches(value, wanted)
            return None if why is None else f"{name}.{why}"
        return f"{name} is a message and the case names {wanted!r}"
    if isinstance(value, bool):
        return None if value == bool(wanted) else f"{name} is {value}, not {wanted}"
    if isinstance(value, int):
        return None if value == int(wanted) else f"{name} is {value}, not {wanted}"
    return None if str(value) == str(wanted) else f"{name} is {value!r}, not {wanted!r}"


def _decimal_same(name: str, value: Decimal, wanted: Any) -> str | None:
    try:
        return None if value == Decimal(str(wanted)) else f"{name} is {value}, not {wanted}"
    except InvalidOperation:
        return f"{name}: {wanted!r} is not a number"


def _matches(message: Message, wanted: Mapping[str, Any]) -> str | None:
    for name, part in wanted.items():
        why = _same(message, name, part)
        if why is not None:
            return why
    return None


@dataclass
class Report:
    """What a run found: each case's failure, by name, and those its plugin
    said its source never presents."""

    role: str
    failures: dict[str, str] = field(default_factory=dict)
    not_presented: dict[str, str] = field(default_factory=dict)
    passed_cases: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


Producer = Callable[[Recorder], Awaitable[None]]


def check(case: Case, recorder: Recorder) -> str | None:
    """Why what `recorder` holds does not pass `case`, or None."""
    for i, expected in enumerate(case.expect):
        on_row = recorder.on(expected.row)
        if not expected.sends:
            if on_row:
                sent = len(on_row)
                return f"expect[{i}]: sent {sent} on {expected.row}, and the case sends none"
            continue
        if not on_row:
            return f"expect[{i}]: nothing was sent on {expected.row}"
        wanted = expected.fields or {}
        whys = [_matches(params, wanted) for params in on_row]
        if all(why is not None for why in whys):
            return f"expect[{i}] on {expected.row}: {whys[0]}"
    return None


def run(
    role: str,
    producers: Mapping[str, Producer],
    *,
    not_presented: Mapping[str, str] | None = None,
    instance_id: str = "suite-plugin",
) -> Report:
    """`run_async`, from a plain test: not from inside a running event loop."""
    return asyncio.run(
        run_async(role, producers, not_presented=not_presented, instance_id=instance_id)
    )


async def run_async(
    role: str,
    producers: Mapping[str, Producer],
    *,
    not_presented: Mapping[str, str] | None = None,
    instance_id: str = "suite-plugin",
) -> Report:
    """Run every case of `role`'s suite against the plugin's producers.

    `producers` maps each case's name to an async function that runs the
    plugin's own conversion, from its own exchange with its source for the
    case, against the `Recorder` it is given. `not_presented` names the
    closed-list cases its source never presents, each with why."""
    held = suite(role)
    report = Report(role)
    skipped = dict(not_presented or {})
    unknown = sorted((set(producers) | set(skipped)) - {case.name for case in held.cases})
    for name in unknown:
        report.failures[name] = f"no case of the {role} suite is named {name!r}"
    for case in held.cases:
        if case.name in skipped:
            if not case.closed_list:
                report.failures[case.name] = (
                    "only a closed-list case may be not presented; this one is required"
                )
            elif not skipped[case.name].strip():
                report.failures[case.name] = "a case not presented says why"
            else:
                report.not_presented[case.name] = skipped[case.name]
            continue
        producer = producers.get(case.name)
        if producer is None:
            report.failures[case.name] = "no producer: the plugin does not map this case"
            continue
        recorder = Recorder(instance_id)
        try:
            await producer(recorder)
        except Exception as failed:  # noqa: BLE001 - a case's failure, reported
            report.failures[case.name] = f"raised {type(failed).__name__}: {failed}"
            continue
        why = check(case, recorder)
        if why is None:
            report.passed_cases.append(case.name)
        else:
            report.failures[case.name] = why
    return report


def names(role: str) -> Iterable[str]:
    """The names of `role`'s cases, in order."""
    return [case.name for case in suite(role).cases]
