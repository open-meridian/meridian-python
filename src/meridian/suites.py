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
never presents may be named in `not_presented`, with why; so, from contract
v19, may a case about one kind of data (`about`: closes, bars, trades,
quotes, prices on a venue) where the plugin declares it never publishes that
kind -- a source of daily closes no trades, a crypto venue no rate between
two currencies:

    report = run("dgm", producers, not_presented={
        "a-trade-recorded": "daily closes and bars only; this source states no trades",
    })

Every other case is required, and a case with no producer fails. The suites
are meridian-schema's `boundaries/suites.json`, vendored with the bindings.

A case may name a row the plugin hears rather than sends (a want delivered to
a `dgm`, contract v18; an activity recorded, to an operations plugin): the
plugin hears it through its own `receive`, called on the recorder, which
hands each row given a handler what `answer` gives for it -- the delivered
message, or a list of them -- and returns, where a sidecar's stream stays
open. What it handed on is kept on that row as what was sent, so the case
checks it beside what the plugin sent after:

    async def a_want_recorded_against(recorder):
        recorder.answer("ObservationsWanted", lambda _: synthetic_want())
        await recorder.receive(observations_wanted=MyDgm(recorder).on_want)

    report = run("dgm", {"a-want-recorded-against": a_want_recorded_against, ...})

From contract v18 the suites hold the `dgm`'s (prices and bars recorded
exactly, a forming day restated, every subject and venue resolved, a token's
price on its own cash instrument, wants recorded against or declined), and
the reading roles' (`reporting`, `portfolio`, `compliance`, `signal`). From
v19 the `dgm`'s hold trades and quotes (the platform's trade attributes, the
side that took liquidity, a condition converted or kept as reported, a
withdrawal, a quote two-sided or one-sided, a standing want streamed);
`signal`'s and the new `ems` suite's, trades and quotes read, heard and
caught up after a watermark; and `reporting`'s, its reporting currency
resolved by its ISO 4217 code.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from importlib import resources
from typing import Any, cast

from google.protobuf.message import Message

from .operations import CONFLATED, DELIVERED, UNCONFLATED, Operations, as_decimal
from .plugin.v1 import operations_pb2 as ops

#: The rows a plugin hears rather than sends, by name.
HEARD = frozenset(
    {
        *(row.name for row in DELIVERED),
        *(row.name for row in CONFLATED),
        *(row.name for row in UNCONFLATED),
    }
)

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
    #: The kind of data the case is about, in the contract's words (contract
    #: v19); empty for a case every plugin of the role answers.
    about: str = ""


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
                    about=case.get("about", ""),
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
    """One typed operation a plugin called: its row, and the params; or a row
    it heard, and the message handed to its handler."""

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
    accounts to link to; from contract v18 a batch of prices or bars (from v19
    of trades or quotes) recorded whole, a venue resolved to a record this
    recorder names, a want declined, a read answering nothing. `raw_record`
    and `note_not_carried` behave as a plugin's do. Use `answer` to answer a
    row otherwise, and to give a row the plugin hears what is delivered on
    it."""

    def __init__(self, instance_id: str = "suite-plugin") -> None:
        self.instance_id = instance_id
        self.sent: list[Sent] = []
        self.seen: dict[tuple[str, str], int] = {}
        self._answers: dict[str, Callable[[Message], Message | Sequence[Message]]] = {}

    @property
    def identity(self) -> Any:
        """The instance the recorder stands in for, as a plugin's identity."""
        from .client import Identity

        return Identity(instance_id=self.instance_id, roles=(), deployment_id="suite")

    def answer(self, row: str, reply: Callable[[Message], Message | Sequence[Message]]) -> None:
        """Answer `row` with what `reply` makes of its params; for a row the
        plugin hears, deliver on it what `reply` makes of the receive request:
        one message, or a list of them."""
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

    async def _receive(
        self,
        handlers: dict[str, Callable[[Any], Awaitable[None]] | None],
        *,
        seed: bool,
        subjects: Sequence[str] = (),
    ) -> None:
        """Each row given a handler handed what `answer` gives for it, in
        order, and kept as heard; then returns, where a sidecar's stream
        stays open."""
        from .receive import Heard

        for row, handler in handlers.items():
            reply = self._answers.get(row)
            if handler is None or reply is None:
                continue
            given = reply(ops.ReceiveRequest(rows=[row], subjects=list(subjects)))
            delivered = (
                list(given) if isinstance(given, list | tuple) else [cast(Message, given)]
            )
            for message in delivered:
                self.sent.append(Sent(row, message))
                await handler(Heard(row=row, message=message))

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
    if row == "RecordPrices":
        return ops.RecordPricesResult(recorded=len(params.prices))
    if row == "RecordBars":
        return ops.RecordBarsResult(recorded=len(params.bars))
    if row == "RecordTrades":
        return ops.RecordTradesResult(recorded=len(params.trades))
    if row == "RecordQuotes":
        return ops.RecordQuotesResult(recorded=len(params.quotes))
    if row == "ResolveVenue":
        return ops.ResolveVenueResult(
            found=True, venue=ops.VenueRecord(venue_id=f"VEN-suite-{n}")
        )
    # Any other read or command with an answer of its own: an empty one.
    answered = getattr(ops, f"{row}Result", None)
    if answered is not None:
        return cast(Message, answered())
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
            if not any(_element_is(descriptor, element, part) for element in value):
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


def _element_is(descriptor: Any, element: Any, wanted: Any) -> bool:
    """Whether one element of a repeated field is what a case names: a
    message matching its fields, an enum value by its name, a scalar by its
    text."""
    if descriptor.message_type is not None:
        return isinstance(wanted, Mapping) and _matches(element, wanted) is None
    if descriptor.enum_type is not None:
        held = descriptor.enum_type.values_by_number.get(element)
        return bool((held.name if held is not None else str(element)) == wanted)
    return str(element) == str(wanted)


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
        verb = "heard" if expected.row in HEARD else "sent"
        if not expected.sends:
            if on_row:
                sent = len(on_row)
                none = "hears" if verb == "heard" else "sends"
                return f"expect[{i}]: {verb} {sent} on {expected.row}, and the case {none} none"
            continue
        if not on_row:
            return f"expect[{i}]: nothing was {verb} on {expected.row}"
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
    cases its source never presents, each with why: a closed-list case, or
    from contract v19 a case about a kind of data (`about`) the plugin
    declares it never publishes."""
    held = suite(role)
    report = Report(role)
    skipped = dict(not_presented or {})
    unknown = sorted((set(producers) | set(skipped)) - {case.name for case in held.cases})
    for name in unknown:
        report.failures[name] = f"no case of the {role} suite is named {name!r}"
    for case in held.cases:
        if case.name in skipped:
            if not case.closed_list and not case.about:
                report.failures[case.name] = (
                    "only a closed-list case, or one about a kind of data the plugin "
                    "never publishes, may be not presented; this one is required"
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
