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

    report = run("data", producers, not_presented={
        "a-trade-recorded": "daily closes and bars only; this source states no trades",
    })

From contract v20 the same holds for a case about one field a source may
never state (`about_field`, by its dictionary entry): a plugin whose source
never states a trade's aggressor, or its conditions, names the case in
`not_presented` with why:

    report = run("data", producers, not_presented={
        "the-takers-side-stated": "this source's trades name no side",
    })

Every other case is required, and a case with no producer fails. The suites
are meridian-schema's `boundaries/suites.json`, vendored with the bindings.

From contract v22 the suites hold the order path's roles -- `connectivity`,
`oms`, and the order path's cases of `portfolio`, `ems`, `compliance`,
`operations` and `reporting` -- and every role's settlement calendar reads
(`reads-a-calendar`, `asks-for-a-settlement-date`; `confirmation`,
`servicing` and `settlement` hold those two). A field a case names `<same>`
is one value present and the same on every message the plugin sends on its
row for the case, at least two sent: a connectivity plugin given the same
fill twice derives the same execution ID. A case's expect is never empty: a
case about what the plugin must not do says so on each row (`sends` false).

From contract v22 `about` names a kind of work as well as a kind of data:
every role's `reads-a-calendar` is about `calendars`, its
`asks-for-a-settlement-date` about `settlement dates`, connectivity's
`records-a-locate` about `locates`, and its two compliance-wait cases about
`compliance waits`. A plugin whose work never uses one names the case in
`not_presented`, with why, as a data plugin does a kind of data it never
publishes; and connectivity's two cases about a fill's place of execution
carry `about_field` (`meridian.v1.ReportExecutionRequest.venue_id`), not
presented by a plugin whose venue never states it:

    report = run("custody", producers, not_presented={
        "reads-a-calendar": "this plugin reports what its venue states; it reads no calendar",
    })

A case may name a row the plugin hears rather than sends (a want delivered to
a data plugin, contract v18; an activity recorded, to an operations plugin): the
plugin hears it through its own `receive`, called on the recorder, which
hands each row given a handler what `answer` gives for it -- the delivered
message, or a list of them -- and returns, where a sidecar's stream stays
open. What it handed on is kept on that row as what was sent, so the case
checks it beside what the plugin sent after:

    async def a_want_recorded_against(recorder):
        recorder.answer("ObservationsWanted", lambda _: synthetic_want())
        await recorder.receive(observations_wanted=MyDataPlugin(recorder).on_want)

    report = run("data", {"a-want-recorded-against": a_want_recorded_against, ...})

From contract v18 the suites hold the data plugin's (prices and bars recorded
exactly, a forming day restated, every subject and venue resolved, a token's
price on its own cash instrument, wants recorded against or declined), and
the reading roles' (`reporting`, `portfolio`, `compliance`, `signal`). From
v19 the data plugin's hold trades and quotes (the platform's trade attributes, the
side that took liquidity, a condition converted or kept as reported, a
withdrawal, a quote two-sided or one-sided, a standing want streamed);
`signal`'s and the new `ems` suite's, trades and quotes read, heard and
caught up after a watermark; and `reporting`'s, its reporting currency
resolved by its ISO 4217 code. From v20 the data suite holds a source's
stated aggressor (`the-takers-side-stated`), a restart's gap backfilled from
the venue's history after the last trade the lake holds of the plugin's own
(`a-restarts-gap-backfilled`, `meridian.roles.data.backfill_restart`), and
its datasets' licences read (`reads-its-datasets-licences`).

From contract v23 an expectation may name its fields `any_of`, in place of
`fields`, for a case whose situation the contract answers in more than one
way: a message on the row passes when it matches one of the ways in full.
Connectivity's `reports-a-fill-with-its-settlement-date` asks the date read
with a security's settlement inputs or a currency pair's spot inputs, from
its trade date or the fill's moment; a plugin sends whichever its market
needs, named in full, and passes on any one:

    async def fills_with_its_settlement_date(recorder):
        await recorder.compute_date(spot=SpotDateInputs(pair=[EUR, USD], at_ns=fill_ns))
        ...

From contract v24 the suites hold booking (the `oms`'s bookings, block,
error account, corrections and sleeve cross; `operations`' allocation
instruction, hand-off, correction and unsettled allocation; the alert for
`compliance`, the `oms`, `operations` and `reporting`; the give-up for
`connectivity` and `confirmation`), the escape hatch's setting read by each
role that proposes, places or checks an order, a custodian's thinly
described holding left unresolved, and the `reference` suite, in preview.
Every role's suite holds two cases the SDK answers itself, since what they
ask is the SDK's work rather than the plugin's: `hears-and-reads-a-replacement`
(a replacement heard and caught up, followed through the SDK's
`CurrentIdMap`) and `reads-the-template-catalogue` (the templates listed and
one read, through its `TemplateCatalogue`). A plugin mapping neither passes
both, each named in `Report.answered_by_sdk`; one with its own way of doing
either maps the case to its own producer, which is run instead.

From contract v26 every role's suite holds a third such case,
`hears-and-reads-an-event-group` (an event group's new version heard, and
the groups holding an instrument read, through the SDK's `EventGroups`),
answered alike; the data suite's event groups reported
(`reports-an-event-group`, `reports-a-flag-the-venue-does-not-state`, both
about `outcomes`); the reading roles' jobs run and caught up, the agents'
guard read, and the lake's bounded query; the `ems`'s five cases of the
agents' demo-only guard; the `pricing` suite; and custody's thin holding
about `securities`, not presented by a custodian holding only cash and
currencies.
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

from .operations import CONFLATED, DELIVERED, SEQUENCED, UNCONFLATED, Operations, as_decimal
from .plugin.v1 import operations_pb2 as ops

#: The rows a plugin hears rather than sends, by name.
HEARD = frozenset(
    {
        *(row.name for row in DELIVERED),
        *(row.name for row in CONFLATED),
        *(row.name for row in UNCONFLATED),
        *(row.name for row in SEQUENCED),
    }
)

SET, UNSET = "<set>", "<unset>"
#: The suite format's `<same>` (contract v22): one value present and the
#: same on every message the plugin sends on the row for the case, at least
#: two sent -- a connectivity plugin deriving the same execution ID from the
#: same fill reported twice.
_SAME = "<same>"


@dataclass(frozen=True)
class Expectation:
    row: str
    fields: Mapping[str, Any] | None = None
    sends: bool = True
    #: The suite format's alternatives (contract v23), in place of `fields`:
    #: each way's fields, a message matched by one of them in full. Empty
    #: where the expectation names `fields` alone.
    any_of: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class Case:
    name: str
    given: str
    expect: tuple[Expectation, ...]
    closed_list: str = ""
    #: The kind of data the case is about, in the contract's words (contract
    #: v19); empty for a case every plugin of the role answers.
    about: str = ""
    #: The field the case is about, by its dictionary entry (contract v20),
    #: one a source may never state; empty for none.
    about_field: str = ""


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
                    about_field=case.get("about_field", ""),
                    expect=tuple(
                        Expectation(
                            row=expected["row"],
                            fields=expected.get("fields"),
                            sends=expected.get("sends", True),
                            any_of=tuple(expected.get("any_of") or ()),
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
    identifier resolved to a record this recorder names (from contract v24
    the platform's `INS-suite-n`, or with `provisional=True` the deployment's
    provisional `LCL-suite-n`, minted only where the resolve states the
    minimum a record needs and otherwise not found), a link made, no
    accounts to link to; from contract v18 a batch of prices or bars (from v19
    of trades or quotes) recorded whole, a venue resolved to a record this
    recorder names, a want declined, a read answering nothing. `raw_record`
    and `note_not_carried` behave as a plugin's do. Use `answer` to answer a
    row otherwise, and to give a row the plugin hears what is delivered on
    it."""

    def __init__(self, instance_id: str = "suite-plugin", *, provisional: bool = False) -> None:
        self.instance_id = instance_id
        #: Whether an ordinary resolve answers the deployment's provisional
        #: record (contract v24): `LCL-suite-n`, minted and provisional,
        #: rather than the platform's `INS-suite-n`.
        self.provisional = provisional
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
        return _ordinary(row, params, len(self.sent), provisional=self.provisional)

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


def meets_minimum(params: Any) -> bool:
    """Whether a resolve states the minimum a record needs (contract v24,
    W3.7; the one-ID model's rule 3): an identifier, a description and a
    currency as the source stated them -- a currency's own code states both,
    and a crypto asset, its own unit, needs no currency. A resolve below it
    is answered not found, and the deployment mints nothing."""
    named = [each for each in params.identifiers if each.value.strip()]
    if not named:
        return False
    if any(each.scheme == "iso4217" for each in named):
        return True
    crypto = params.stated_asset_class == ops.ASSET_CLASS_CRYPTO_ASSET
    currency = bool(params.stated_currency.strip() or params.currency.strip())
    return bool(params.stated_description.strip()) and (crypto or currency)


def _ordinary(row: str, params: Any, n: int, *, provisional: bool = False) -> Message:
    if row == "RecordHoldingsStatement":
        return ops.RecordHoldingsStatementResult(statement_id=f"STMT-suite-{n}")
    if row == "RecordHolding":
        return ops.RecordHoldingResult(
            holding_id=f"HLD-suite-{n}", resolved=bool(params.instrument_id)
        )
    if row == "ResolveIdentifier":
        # From 0.28.0 (contract v24) the platform's record, keyed by its INS-
        # ID; the deployment's provisional record where the recorder says.
        if provisional:
            # Minted only where the source states the minimum a record needs
            # (contract v24, W3.7): below it, not found, nothing minted.
            if not meets_minimum(params):
                return ops.ResolveIdentifierResult(
                    found=False, miss_reason=ops.MISS_REASON_NOT_FOUND
                )
            return ops.ResolveIdentifierResult(
                found=True, instrument_id=f"LCL-suite-{n}", minted=True, provisional=True
            )
        return ops.ResolveIdentifierResult(found=True, instrument_id=f"INS-suite-{n}")
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
    if wanted in (SET, _SAME):
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
    #: The cases the plugin did not map that the SDK answered itself
    #: (contract v24), each passed through the SDK's own helper.
    answered_by_sdk: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


Producer = Callable[[Recorder], Awaitable[None]]


# ── The cases the SDK answers itself (contract v24) ─────────────────────────

#: What the runner's own replacement says: a provisional record resolved to
#: the platform's, heard, then merged on the platform, read after a loss.
_PROVISIONAL = "LCL-01JSUITE0000000000000000001"
_RESOLVED = "INS-01JSUITE0000000000000000001"
_MERGED_INTO = "INS-01JSUITE0000000000000000002"
_TEMPLATE = "TPL-01JSUITE0000000000000000001"


async def follows_a_replacement(recorder: Recorder) -> None:
    """`hears-and-reads-a-replacement`, as the SDK does it for every plugin:
    a provisional record's resolution heard, and the platform's later merge
    read after a loss (`list_replacements` after the sequence heard), both
    followed by a `CurrentIdMap` to the record the ID names now."""
    from .replacements import CurrentIdMap

    resolved = ops.InstrumentReplacedEvent(
        replaced_instrument_id=_PROVISIONAL,
        instrument=ops.InstrumentRecord(instrument_id=_RESOLVED),
        cause=ops.REPLACEMENT_CAUSE_RESOLVED,
        sequence=1,
    )
    merged = ops.InstrumentReplacedEvent(
        replaced_instrument_id=_RESOLVED,
        instrument=ops.InstrumentRecord(instrument_id=_MERGED_INTO),
        cause=ops.REPLACEMENT_CAUSE_PLATFORM_MERGED,
        sequence=2,
    )

    def replacements(params: Message) -> Message:
        after = cast(ops.ListReplacementsParams, params).after_sequence
        if after < merged.sequence:
            return ops.ListReplacementsResult(replacements=[merged], sequence=merged.sequence)
        return ops.ListReplacementsResult(sequence=after)

    recorder.answer("ReplaceMergedInstrument", lambda _: resolved)
    recorder.answer("ListReplacements", replacements)
    ids = CurrentIdMap()
    await recorder.receive(replace_merged_instrument=ids.heard)
    await ids.catch_up(recorder)
    if ids.current(_PROVISIONAL) != _MERGED_INTO:
        raise AssertionError(
            f"the current-ID map follows {_PROVISIONAL} to {ids.current(_PROVISIONAL)}, "
            f"not {_MERGED_INTO}"
        )


async def reads_the_template_catalogue(recorder: Recorder) -> None:
    """`reads-the-template-catalogue`, as the SDK does it for every plugin:
    the templates listed, and the one a record names read at its version,
    through a `TemplateCatalogue`."""
    from .replacements import TemplateCatalogue

    listed = ops.SecurityTemplate(
        template_id=_TEMPLATE,
        template_version="1",
        name="Common stock",
        asset_class=ops.ASSET_CLASS_EQUITY,
        fields=[ops.TemplateField(path="share_class_figi", type="string", required=True)],
        match_rule=["share_class_figi"],
    )
    recorder.answer("ListTemplates", lambda _: ops.ListTemplatesResult(templates=[listed]))
    recorder.answer("ReadTemplate", lambda _: ops.ReadTemplateResult(template=listed))
    catalogue = TemplateCatalogue()
    held = await catalogue.load(recorder)
    for template in held[:1]:
        await catalogue.template(recorder, template.template_id, template.template_version)


_GROUP = "EVG-01JSUITE0000000000000000001"
_MEMBERS = ("INS-01JSUITE0000000000000000011", "INS-01JSUITE0000000000000000012")


async def hears_and_reads_an_event_group(recorder: Recorder) -> None:
    """`hears-and-reads-an-event-group` (contract v26), as the SDK does it for
    every plugin: a group's new version heard, and the groups holding one of
    its members read in force now, through an `EventGroups`, whose version
    in force is the one heard."""
    from .roles.data._groups import EventGroups

    def version(n: int) -> ops.EventGroup:
        return ops.EventGroup(
            event_group_id=_GROUP,
            member_instrument_ids=list(_MEMBERS),
            mutually_exclusive=ops.EVENT_GROUP_FLAG_TRUE,
            exhaustive=ops.EVENT_GROUP_FLAG_NOT_STATED,
            version=n,
            valid_from_ns=n * 1_000,
            sequence=n,
        )

    recorder.answer("EventGroupChanged", lambda _: version(2))
    recorder.answer(
        "ListEventGroups",
        lambda _: ops.ListEventGroupsResult(event_groups=[version(1), version(2)], sequence=2),
    )
    groups = EventGroups()
    await recorder.receive(event_group_changed=groups.heard)
    await groups.read(recorder, instrument_ids=[_MEMBERS[0]])
    held = groups.holding(_MEMBERS[0])
    if not held or held[0].version != 2:
        raise AssertionError(
            f"the group in force holding {_MEMBERS[0]} is not version 2: {held}"
        )


#: The cases every role's suite holds that the SDK answers for a plugin that
#: maps none of them (contract v24; the event group's from v26).
ANSWERED_BY_SDK: Mapping[str, Producer] = {
    "hears-and-reads-a-replacement": follows_a_replacement,
    "reads-the-template-catalogue": reads_the_template_catalogue,
    "hears-and-reads-an-event-group": hears_and_reads_an_event_group,
}


def _one_value(row: str, on_row: Sequence[Message], wanted: Mapping[str, Any]) -> str | None:
    """Why the fields a case names `<same>` are not one value across every
    message on the row, at least two of them, or None."""
    for name, part in wanted.items():
        if part != _SAME:
            continue
        if len(on_row) < 2:
            return f"{name}: {len(on_row)} sent on {row}, and the case asks for one value twice"
        values = {str(getattr(params, name)) for params in on_row if _present(params, name)}
        if len(values) != 1 or not all(_present(params, name) for params in on_row):
            return f"{name} is not one value across what was sent: {sorted(values)}"
    return None


def _any_of(
    row: str, on_row: Sequence[Message], ways: Sequence[Mapping[str, Any]]
) -> str | None:
    """Why no message on the row matches one of an expectation's ways in
    full (contract v23), or None: each way held as `fields` are, its
    `<same>` across every message on the row."""
    whys: list[str] = []
    for k, way in enumerate(ways):
        why = _one_value(row, on_row, way)
        if why is None:
            each = [_matches(params, way) for params in on_row]
            if any(why is None for why in each):
                return None
            why = next(why for why in each if why is not None)
        whys.append(f"any_of[{k}]: {why}")
    return "matches none of its ways: " + "; ".join(whys)


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
        if expected.any_of:
            why = _any_of(expected.row, on_row, expected.any_of)
            if why is not None:
                return f"expect[{i}] on {expected.row}: {why}"
            continue
        wanted = expected.fields or {}
        why = _one_value(expected.row, on_row, wanted)
        if why is not None:
            return f"expect[{i}] on {expected.row}: {why}"
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
    provisional: bool = False,
) -> Report:
    """`run_async`, from a plain test: not from inside a running event loop."""
    return asyncio.run(
        run_async(
            role,
            producers,
            not_presented=not_presented,
            instance_id=instance_id,
            provisional=provisional,
        )
    )


async def run_async(
    role: str,
    producers: Mapping[str, Producer],
    *,
    not_presented: Mapping[str, str] | None = None,
    instance_id: str = "suite-plugin",
    provisional: bool = False,
) -> Report:
    """Run every case of `role`'s suite against the plugin's producers.

    `producers` maps each case's name to an async function that runs the
    plugin's own conversion, from its own exchange with its source for the
    case, against the `Recorder` it is given. `not_presented` names the
    cases its source never presents, each with why: a closed-list case, or
    from contract v19 a case about a kind of data (`about`) the plugin
    declares it never publishes, or from v22 a kind of work its work never
    uses (calendars, settlement dates, locates, compliance waits), or from
    v20 one about a
    field (`about_field`) its source never states.

    From contract v24 `provisional` runs every case with an ordinary resolve
    answering the deployment's provisional record (`LCL-suite-n`) rather than
    the platform's (`INS-suite-n`): the provisional cases beside the suite's,
    which a plugin's conversion passes alike. A case the plugin does not map
    that the SDK answers itself (`ANSWERED_BY_SDK`) is answered so, and named
    in `Report.answered_by_sdk`."""
    held = suite(role)
    report = Report(role)
    skipped = dict(not_presented or {})
    unknown = sorted((set(producers) | set(skipped)) - {case.name for case in held.cases})
    for name in unknown:
        report.failures[name] = f"no case of the {role} suite is named {name!r}"
    for case in held.cases:
        if case.name in skipped:
            if not case.closed_list and not case.about and not case.about_field:
                report.failures[case.name] = (
                    "only a closed-list case, or one about a kind of data the plugin "
                    "never publishes, a kind of work it never does or a field its "
                    "source never states, may be not presented; this one is required"
                )
            elif not skipped[case.name].strip():
                report.failures[case.name] = "a case not presented says why"
            else:
                report.not_presented[case.name] = skipped[case.name]
            continue
        producer = producers.get(case.name)
        by_sdk = producer is None and case.name in ANSWERED_BY_SDK
        if by_sdk:
            producer = ANSWERED_BY_SDK[case.name]
        if producer is None:
            report.failures[case.name] = "no producer: the plugin does not map this case"
            continue
        recorder = Recorder(instance_id, provisional=provisional)
        try:
            await producer(recorder)
        except Exception as failed:  # noqa: BLE001 - a case's failure, reported
            report.failures[case.name] = f"raised {type(failed).__name__}: {failed}"
            continue
        why = check(case, recorder)
        if why is None:
            report.passed_cases.append(case.name)
            if by_sdk:
                report.answered_by_sdk.append(case.name)
        else:
            report.failures[case.name] = why
    return report


def names(role: str) -> Iterable[str]:
    """The names of `role`'s cases, in order."""
    return [case.name for case in suite(role).cases]
