"""A data plugin for a venue of binary event contracts, generic over the venue
(0.30.0; sdk-contract/the-sdk-carries-each-roles-common-logic). Kalshi's and
the international Polymarket's plugins kept this byte for byte between them;
it is the SDK's now, each plugin keeping only its venue's client and its
conversion.

    feed = event_contracts.Feed(plugin, KalshiMarket(client, "live"),
                                event_contracts.ContractMap(path))
    await plugin.receive(observations_wanted=feed.on_want, want_withdrawn=feed.on_withdrawn)
    await feed.keep_current()

**What the plugin supplies.** A `Market`: its venue's answers read into the
values below -- every number a `Decimal` from the venue's own text, never a
float; a value that would not read kept as sent (`Unread`) -- each answer
kept as a raw record before anything is read from it. A contract is read by
its code, one at a time: the venue's whole listing is never read.

- `Cash`: the asset the venue's prices and payouts are in: a currency by its
  ISO 4217 code, or the venue's own token instrument, known by its code
  with the venue as source (a token, never its currency).
- `Contract`: one binary event contract, by the venue's own code, with the
  venue's words for what it pays on, what one contract pays if the event
  happens (`payout`, in the venue's cash) and when trading in it closes.
- `Tick`: the last trade's price, per contract; `Top`: the best bid and
  offer, each with its size in contracts, a side with no order None.
- `Resolution` (contract v23): the venue's determination of a contract,
  from the contract's own side, at the stage the venue states.

A price is money per contract, never a probability (plans/the-lake-prices-
the-book, "The event contract"): the implied probability is a reader's.

**Two datasets** (`live`, `outcomes`): each contract's last trade price and
best bid and offer as prices, and its best bid and offer with their sizes as
a quote, at most once a second per subject; and each contract's outcome as
the venue states it -- it pays its full payout, nothing, or part -- with what
one contract settles at and the venue's own word kept as reported. One row
key per contract (`<code>:outcome`); each change of stage (proposed,
determined, disputed, final) or of its determination is a new version, and
nothing is sent while the venue's statement is unchanged. Its valid time is
the determination's: the venue's own where it states one, else when the
answer first stating it arrived. It answers no want: it is recorded, unasked,
for each contract a subject the lake asked for is, and each minute for a
contract past its close until its final stage is recorded.

**A contract's identifiers** (0.31.0, ruling 312): its symbol at the venue
and its ticker -- the venue's own market ticker under the `ticker` scheme,
the venue's ISO 10383 MIC in source, or its VEN- ID where it has no MIC --
which the platform matches and mints on.

**Per subject wanted, never the whole venue** (W3.6, W3.1, W3.14): each
subject is the deployment's record, read and named as one of the venue's
contracts by its identifiers -- the venue's own code first, then another
source's symbol the venue answers as one of its contracts, never for a
record that is a security or of a type other than a binary event contract.
A contract the venue does not state as binary, or whose payout its record
states otherwise, is not served. Where the record lacks the venue's code,
its class or its type, the venue's code is reported beside the one it
matched (W3.1) with the class, the type and the venue's words offered; where
that resolve meets another record it is reported (W3.2). The cash and the
venue are resolved once; what does not resolve is reported, never guessed.

**Wants** (W10.7): the latest of the live dataset, or a day or range covering
now; declined `not_covered` where the record names none of the venue's
binary event contracts, `beyond_history` for a day or range already past,
`source_silent` where the venue states nothing. A standing want keeps its
subjects current until withdrawn, at most once a second. It records no
trades, so a restart leaves no gap to read back.

**Event groups** (contract v26; W3.29, W3.30; spec/the-contract-gaps-v26-
and-v27-close, A1 to A9). The venue's grouping of its contracts into an
event, as its conversion reads it (`Event`): the event's reference and
words, its members by the venue's codes, whether the venue states them
mutually exclusive and exhaustive -- each True, False or None where it
states nothing, which is reported not stated, never false (A2) -- its
series and when the grouping took effect. `Feed.report_event` resolves
every member (W3.1) and reports the group (ReportEventGroup) with the raw
record it was read from; the platform matches or mints it, and the
deployment keeps its own `LCL-` group meanwhile. A member that does not
resolve holds the report back: a group missing a member would misstate it.
A range market's bounds are the member's (A4): `Contract.floor` and
`Contract.cap`, each a `Bound` (a Decimal and whether it is inclusive --
Kalshi's `greater` false, `greater_or_equal` true), and `bound_unit`, kept
in the contract map with each value's exact text (0.31.1). From 0.32.0
(contract v27, ruling 464) `report_event` sends each range member's floor,
cap and unit with the group (`member_bounds`), which the instrument record
takes as values offered; a person's value wins. `keep_events` reports the
events of the contracts served -- read once first served and every ten
minutes, reported on a change -- for a `Market` answering `event(ref)`.

Every role reads groups through `EventGroups` (re-exported here and as
`meridian.EventGroups`): the versions read and heard, and the one in force
at a moment.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from ...errors import NotGranted
from ...figures import Figure
from ...operations import (
    EventContractBound,
    EventGroupMemberBound,
    Money,
    ObservationMeta,
    Outcome,
    Price,
    Quote,
    SourceTime,
    as_money,
)
from ...plugin.v1 import operations_pb2 as ops
from . import figures as role_figures
from ._groups import EventGroups, flag, stated
from ._pages import connection_fields, connection_figure, served, want_rows
from ._reading import NANOS_PER_SECOND, Session, Unread, iso_time, utc_day
from ._records import DatasetsRead as RoleDatasetsRead
from ._records import VenueConnection
from ._wants import Counts, Heard, Standing, Venue, Wants, asked, same, unconverted

__all__ = [
    "Bound",
    "Event",
    "EventGroups",
    "flag",
    "stated",
    "DETERMINED",
    "DISPUTED",
    "FINAL",
    "LIVE",
    "NOT_A_CONTRACT",
    "NOT_READ",
    "OUTCOMES",
    "PAYOUT_DIFFERS",
    "PROPOSED",
    "Cash",
    "ConnectionRead",
    "Contract",
    "ContractMap",
    "DatasetsRead",
    "Feed",
    "Mapped",
    "Market",
    "NotServed",
    "Recorded",
    "Resolution",
    "Tick",
    "Top",
    "connection_read",
    "datasets_read",
    "figures_read",
]

log = logging.getLogger("meridian.roles.data.event_contracts")

LIVE = "live"
#: The dataset of each contract's outcome (contract v23).
OUTCOMES = "outcomes"
PRICE, QUOTE = "meridian.v1.Price", "meridian.v1.Quote"
#: The live dataset's pace: each subject at most once a second.
LIVE_EVERY_SECONDS = 1.0
#: How soon an event first served is read, and how often each is read again
#: (`Feed.keep_events`, 0.32.0), in seconds.
EVENTS_FIRST_SECONDS, EVENTS_EVERY_SECONDS = 15.0, 600.0
#: How often a contract past its close, its final stage not yet recorded,
#: is read again for its determination.
OUTCOME_EVERY_SECONDS = 60.0
#: Each contract, and the venue, read again once a day.
REREAD_SECONDS = 86_400
#: The longest description offered from the venue's words.
MOST_DESCRIPTION = 500

#: A record's classes that may be an event contract's: none yet, or one.
_EVENT_CLASSES = {ops.ASSET_CLASS_UNSPECIFIED, ops.ASSET_CLASS_EVENT_CONTRACT}
#: A record's types that may be a binary event contract's: none yet, or one.
_BINARY_TYPES = {ops.INSTRUMENT_TYPE_UNSPECIFIED, ops.INSTRUMENT_TYPE_BINARY_EVENT_CONTRACT}
#: Identifiers only a security carries.
_SECURITY_SCHEMES = {"cusip", "isin", "sedol", "figi"}
_LIVE_KINDS = {ops.PRICE_KIND_LAST, ops.PRICE_KIND_BID, ops.PRICE_KIND_ASK}

#: Why a subject is not served, as the Datasets page counts them.
NOT_A_CONTRACT = "its record names none of the venue's binary event contracts"
PAYOUT_DIFFERS = "its record states another payout"
NOT_READ = "its record could not be read"


# ── What the venue's answers are read into ──────────────────────────────


@dataclass(frozen=True)
class Cash:
    """The asset a venue's prices and payouts are in."""

    #: The venue's own code for it (`USD`, `USDC`).
    code: str
    #: "currency" or "token".
    kind: str
    #: Its global identifier's scheme and value -- ("iso4217", "USD") -- or
    #: empty for the venue's own token instrument, known by its code alone.
    scheme: str = ""
    value: str = ""
    #: The venue's own name for it, offered as stated.
    name: str = ""

    @property
    def currency_code(self) -> str:
        """Its ISO 4217 code, for a currency; empty for a token."""
        return self.value if self.scheme == "iso4217" else ""


#: The stages of a determination, in the contract's words: each venue's own
#: states are read into these by its conversion.
PROPOSED, DETERMINED, DISPUTED, FINAL = "proposed", "determined", "disputed", "final"


@dataclass(frozen=True)
class Resolution:
    """The venue's determination of one contract, at one stage, as the venue
    states it: nothing of the contract's yet."""

    #: The stage, one of PROPOSED, DETERMINED, DISPUTED and FINAL.
    stage: str
    #: What one contract settles at, in the venue's cash; None where the
    #: venue states no value at this stage, or its value did not read.
    value: Decimal | None
    #: The venue's own word for the determination, as reported: where it is
    #: in the venue's answer (`kalshi:result`), its code and its text. Empty
    #: where the venue states none at this stage.
    scheme: str = ""
    word: str = ""
    text: str = ""
    #: When the venue determined it, where the venue says; 0 where it does
    #: not, and the determination is valid from when its answer arrived.
    determined_at_ns: int = 0
    #: When the venue paid out, as it states it; 0 until then.
    settled_at_ns: int = 0
    unread: tuple[Unread, ...] = ()


@dataclass(frozen=True)
class Contract:
    """One binary event contract, as the venue states it."""

    #: The venue's own code for it: a market ticker, an outcome token's ID.
    code: str
    #: What it pays on, in the venue's words: offered as the record's
    #: description, marked as another's wherever it reaches an agent.
    title: str
    #: Whether the venue states it as binary: it pays `payout` if the event
    #: happens and nothing if it does not.
    binary: bool
    #: What one contract pays if the event happens, in the venue's cash;
    #: None where the venue's statement did not read.
    payout: Decimal | None
    #: When trading in it closes, in UTC nanoseconds; 0 where none is stated.
    closes_at_ns: int = 0
    #: Whether the venue trades it now, and its status in the venue's word.
    tradable: bool = True
    status: str = ""
    #: The venue's other code for the market it belongs to, where it gives
    #: one (Kalshi's event ticker, Polymarket's condition ID).
    market: str = ""
    raw_key: str = ""
    unread: tuple[Unread, ...] = ()
    #: Its determination as the venue states it in the same answer (contract
    #: v23); None while the venue states none.
    resolution: Resolution | None = None
    #: When the answer it was read from first arrived, in UTC nanoseconds.
    read_at_ns: int = 0
    #: A range market's bounds as the venue states them (contract v26, A4):
    #: an open tail has one only; neither for a contract that is no range.
    floor: Bound | None = None
    cap: Bound | None = None
    #: The unit both bounds are in: the venue's word (`degrees_f`,
    #: `index_points`, `percent`), or an instrument's ID where a bound is a
    #: price; empty where neither is set.
    bound_unit: str = ""


@dataclass(frozen=True)
class Bound:
    """One bound of a range market (contract v26, A4): its value and whether
    it is inclusive."""

    value: Decimal
    inclusive: bool

    def wire(self) -> ops.EventContractBound:
        from ...operations import _decimal

        return ops.EventContractBound(
            value=_decimal(self.value, "bound"), inclusive=self.inclusive
        )


@dataclass(frozen=True)
class Event:
    """A venue's event grouping its contracts (contract v26, W3.29), as the
    plugin's conversion read it: nothing of the deployment's yet."""

    #: The venue's reference for the event: Kalshi's event ticker,
    #: Polymarket's event slug.
    ref: str
    #: The venue's words for it.
    title: str
    #: Its members, by the venue's own codes, as `Market.contract` takes them.
    members: tuple[str, ...]
    #: Whether the venue states its members mutually exclusive, and
    #: exhaustive; None where it states nothing (reported not stated).
    mutually_exclusive: bool | None = None
    exhaustive: bool | None = None
    #: The venue's series, for a recurring event (A5); empty for none.
    series: str = ""
    #: When the grouping took effect, as the venue states it; 0 for when the
    #: answer it was read from arrived.
    valid_from_ns: int = 0
    #: The raw record the event was read from, as the plugin kept it.
    raw_key: str = ""


@dataclass(frozen=True)
class Tick:
    """The last trade's price, per contract."""

    code: str
    price: Decimal | None
    #: When it traded, as the venue stated it; else when the answer arrived,
    #: `stated` False.
    at_ns: int
    stated: bool
    #: The venue's own identity for it -- its trade ID -- where it gives one.
    ident: str = ""
    raw_key: str = ""
    unread: tuple[Unread, ...] = ()


@dataclass(frozen=True)
class Top:
    """The best bid and offer per contract, each with its size in contracts;
    a side with no order is None."""

    code: str
    bid: Decimal | None
    ask: Decimal | None
    bid_size: Decimal | None
    ask_size: Decimal | None
    at_ns: int
    stated: bool
    ident: str = ""
    raw_key: str = ""
    unread: tuple[Unread, ...] = ()


class Market(Protocol):
    """A venue's public market data for event contracts, read into the values
    above by the plugin's own client and conversion."""

    #: The venue's code as a `symbol`'s source (`kalshi`, `polymarket`).
    venue: str
    #: The venue's name, as people know it.
    name: str
    #: The identifiers the venue is known by in a venue master, each
    #: (scheme, value, source).
    venue_identifiers: tuple[tuple[str, str, str], ...]
    #: The asset its prices and payouts are in.
    cash: Cash
    session: Session

    def contract(self, code: str, watching: bool = False) -> Contract | None:
        """The contract the venue knows by `code`, or None where it knows
        none by it. `watching`: read again for its determination."""
        ...

    def last(self, contract: Contract) -> Tick: ...

    def top(self, contract: Contract) -> Top: ...


# ── The contract map ────────────────────────────────────────────────────


@dataclass(frozen=True)
class Recorded:
    """A contract's outcome as last recorded in the lake (contract v23)."""

    stage: str
    #: What one contract settles at, in the venue's cash, as text.
    value: str
    scheme: str
    word: str
    text: str
    settled_at_ns: int
    #: Its valid time, the determination's, and whether the venue stated it.
    valid_from_ns: int
    stated: bool
    raw_key: str

    def says(self) -> tuple[str, Decimal, str, str, str, int]:
        """What the venue stated, which a new version changes."""
        return (self.stage, Decimal(self.value), self.scheme, self.word, self.text,
                self.settled_at_ns)  # fmt: skip


@dataclass(frozen=True)
class Mapped:
    """A contract serving a subject, the venue's cash resolved."""

    contract: Contract
    subject: str
    cash_id: str


def _resolution(held: dict[str, Any] | None) -> Resolution | None:
    if not held:
        return None
    value = held.get("value")
    return Resolution(
        stage=held["stage"],
        value=None if value is None else Decimal(value),
        scheme=held.get("scheme", ""),
        word=held.get("word", ""),
        text=held.get("text", ""),
        determined_at_ns=int(held.get("determined_at_ns", 0)),
        settled_at_ns=int(held.get("settled_at_ns", 0)),
        unread=tuple(Unread(**u) for u in held.get("unread", [])),
    )


def _contract(held: dict[str, Any]) -> Contract:
    payout = held.get("payout")
    return Contract(
        code=held["code"],
        title=held.get("title", ""),
        binary=bool(held.get("binary", False)),
        payout=None if payout is None else Decimal(payout),
        closes_at_ns=int(held.get("closes_at_ns", 0)),
        tradable=bool(held.get("tradable", True)),
        status=held.get("status", ""),
        market=held.get("market", ""),
        raw_key=held.get("raw_key", ""),
        unread=tuple(Unread(**u) for u in held.get("unread", [])),
        resolution=_resolution(held.get("resolution")),
        read_at_ns=int(held.get("read_at_ns", 0)),
        floor=_bound(held.get("floor")),
        cap=_bound(held.get("cap")),
        bound_unit=held.get("bound_unit", ""),
    )


def _bound(held: dict[str, Any] | None) -> Bound | None:
    """A range market's bound as the map keeps it (0.31.1): its value as
    its exact text, and whether it is inclusive."""
    if not held:
        return None
    return Bound(value=Decimal(held["value"]), inclusive=bool(held["inclusive"]))


def _bound_held(bound: Bound | None) -> dict[str, Any] | None:
    if bound is None:
        return None
    return {"value": str(bound.value), "inclusive": bound.inclusive}


def _held(contract: Contract) -> dict[str, Any]:
    body = asdict(contract)
    body["payout"] = None if contract.payout is None else str(contract.payout)
    if contract.resolution is not None:
        value = contract.resolution.value
        body["resolution"]["value"] = None if value is None else str(value)
    # Each bound's value as its exact text, as the payout's (0.31.1).
    body["floor"], body["cap"] = _bound_held(contract.floor), _bound_held(contract.cap)
    return body


class ContractMap:
    """The contracts the lake's subjects are, and what the cash resolved to,
    kept in the plugin's own storage (`path`, `contracts-<mode>.json` beside
    its raw records), read at start, each contract read again once a day.
    Nothing else reads it (decisions/028)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        #: Each contract read, by the venue's code.
        self.contracts: dict[str, Contract] = {}
        #: Which contract each subject is, by the deployment's instrument ID.
        self.subjects: dict[str, str] = {}
        #: The deployment's instrument for the venue's cash, once resolved.
        self.cash_id = ""
        #: Each asset or contract reported as missing, by the venue's code,
        #: and why.
        self.missing: dict[str, str] = {}
        #: When the contracts were last read again, in UTC nanoseconds.
        self.read_at_ns = 0
        #: Each contract's outcome as last recorded, by the venue's code.
        self.outcomes: dict[str, Recorded] = {}

    def load(self) -> bool:
        """Read the map kept in storage; whether there was one."""
        if self.path is None or not self.path.is_file():
            return False
        held: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        self.contracts = {c["code"]: _contract(c) for c in held.get("contracts", [])}
        self.subjects = dict(held.get("subjects", {}))
        self.cash_id = str(held.get("cash_id", ""))
        self.missing = dict(held.get("missing", {}))
        self.read_at_ns = int(held.get("read_at_ns", 0))
        self.outcomes = {code: Recorded(**o) for code, o in held.get("outcomes", {}).items()}
        return True

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "contracts": [_held(c) for _, c in sorted(self.contracts.items())],
            "subjects": self.subjects,
            "cash_id": self.cash_id,
            "missing": self.missing,
            "read_at_ns": self.read_at_ns,
            "outcomes": {code: asdict(o) for code, o in sorted(self.outcomes.items())},
        }
        written = self.path.with_suffix(".tmp")
        written.write_text(json.dumps(body, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(written, self.path)

    def serving(self, subject: str) -> Mapped | None:
        """The contract a subject is, where the cash has resolved; None
        otherwise."""
        code = self.subjects.get(subject, "")
        contract = self.contracts.get(code)
        if contract is None or not self.cash_id:
            return None
        return Mapped(contract, subject, self.cash_id)

    def mapped(self) -> list[Mapped]:
        """Every contract serving a subject, each once, for the first subject
        it serves."""
        seen: dict[str, Mapped] = {}
        for subject in sorted(self.subjects):
            mapped = self.serving(subject)
            if mapped is not None:
                seen.setdefault(mapped.contract.code, mapped)
        return [seen[code] for code in sorted(seen)]

    def code_of(self, instrument_id: str) -> str:
        """The venue's code a subject is, or the cash resolved to; empty if
        none."""
        if instrument_id in self.subjects:
            return self.subjects[instrument_id]
        return "cash" if instrument_id and instrument_id == self.cash_id else ""


# ── The work ────────────────────────────────────────────────────────────


@dataclass
class Feed:
    """An event-contract venue's work: resolving, recording, answering wants,
    keeping them current and recording outcomes (see the module). `plugin`
    is a `meridian.Plugin`, or the suites' `Recorder`."""

    plugin: Any
    market: Market
    contracts: ContractMap
    clock_ns: Callable[[], int] = time.time_ns
    venue: Venue = field(default_factory=Venue)
    #: Whether the deployment answers this plugin's ResolveInstrument (W3.6).
    reads_instruments: bool = True
    #: Subjects not served, and why, until the contracts are read again.
    unnamed: dict[str, str] = field(default_factory=dict)
    #: Contracts whose stated determination did not read, counted once each.
    unreadable: set[str] = field(default_factory=set)
    wants: Wants = field(init=False)
    #: When each event was last read, and what was last reported of each
    #: (`keep_events`, 0.32.0).
    _events_read_at: dict[str, float] = field(default_factory=dict, init=False)
    _events_reported: dict[str, tuple[object, ...]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.wants = Wants(self.plugin, (LIVE, OUTCOMES), clock_ns=self.clock_ns)

    # ── What the Datasets page and the suites read ───────────────────────

    @property
    def standing(self) -> dict[str, Standing]:
        return self.wants.standing

    @property
    def counts(self) -> Counts:
        """What it sent the live dataset, and the wants and declines heard."""
        return self.wants.counts

    @property
    def outcome_counts(self) -> Counts:
        """What it sent the outcomes dataset, apart from the live one's."""
        return self.wants.sent_to(OUTCOMES)

    @property
    def heard(self) -> deque[Heard]:
        return self.wants.heard

    @property
    def by_dataset(self) -> dict[str, Counts]:
        return self.wants.by_dataset

    @property
    def reads_licences(self) -> bool:
        return self.wants.reads_licences

    @property
    def licensed(self) -> frozenset[str]:
        return self.wants.licensed

    @licensed.setter
    def licensed(self, value: frozenset[str]) -> None:
        self.wants.licensed = value

    def dataset(self, key: str) -> str:
        """A dataset as rows name it: the instance, a colon and the key."""
        return self.wants.dataset(key)

    def sent_to(self, key: str) -> Counts:
        return self.wants.sent_to(key)

    async def read_licences(self) -> frozenset[str]:
        """Its own declared datasets' licences (contract v20, W10.9)."""
        return await self.wants.read_licences()

    def use(self, market: Market, contracts: ContractMap) -> None:
        """Answer from another source (sample data switched): its own map, the
        venue asked again; standing wants carry over."""
        self.market, self.contracts, self.venue = market, contracts, Venue()
        self.unnamed.clear()

    # ── Event groups (contract v26) ──────────────────────────────────────

    async def member_id(self, code: str) -> str:
        """The deployment's record of one of the venue's contracts by its
        code (W3.1), resolved by the venue's identifiers for it; empty where
        none resolves or the venue knows no such contract."""
        contract = await self.contract(code)
        if contract is None:
            return ""
        found = await self.plugin.resolve_identifier(
            identifiers=await self.stated_identifiers(contract),
            as_of_ns=self.clock_ns(),
            stated_asset_class="event_contract",
            stated_instrument_type="binary_event_contract",
            stated_currency=self.market.cash.currency_code,
            stated_description=contract.title[:MOST_DESCRIPTION],
        )
        return str(found.instrument_id) if found.found and found.instrument_id else ""

    async def report_event(self, event: Event) -> ops.ReportEventGroupResult | None:
        """Report the venue's grouping of an event (ReportEventGroup, W3.29):
        each member resolved, the two flags as the venue states them (not
        stated where it says nothing), its series and when it took effect,
        with the raw record it was read from. None, and nothing sent, where
        a member does not resolve or the venue is not held: a group missing
        a member would misstate it."""
        members: list[str] = []
        bounds: list[EventGroupMemberBound] = []
        for code in event.members:
            member = await self.member_id(code)
            if not member:
                log.info("event %s held back: its member %s does not resolve", event.ref, code)
                return None
            members.append(member)
            contract = await self.contract(code)
            if contract is not None and (contract.floor or contract.cap):
                # Contract v27 (ruling 464): each range member's bounds as
                # the venue states them, offered for its record.
                bounds.append(
                    EventGroupMemberBound(
                        instrument_id=member,
                        floor=_offered(contract.floor),
                        cap=_offered(contract.cap),
                        bound_unit=contract.bound_unit,
                    )
                )
        venue = await self.venue_id()
        if not venue:
            return None
        answer: ops.ReportEventGroupResult = await self.plugin.report_event_group(
            venue_id=venue,
            venue_event_ref=event.ref,
            title=event.title[:MOST_DESCRIPTION],
            member_instrument_ids=members,
            mutually_exclusive=flag(event.mutually_exclusive),
            exhaustive=flag(event.exhaustive),
            series_id=event.series,
            valid_from_ns=event.valid_from_ns or self.clock_ns(),
            raw_record=self.plugin.raw_record(event.raw_key) if event.raw_key else None,
            member_bounds=bounds,
        )
        return answer

    async def keep_events(
        self,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        *,
        clock: Callable[[], float] = time.monotonic,
        once: bool = False,
    ) -> int:
        """Report the events of the contracts served, until cancelled (0.32.0;
        the loop Kalshi's and Polymarket's plugins each kept): each event --
        a served contract's `market` -- read once its contract is first
        served and again every `EVENTS_EVERY_SECONDS`, and reported
        (`report_event`) where it is new or the venue states it otherwise
        than as last reported; one held back, a member not resolving, read
        again on the next pass. A pass every `EVENTS_FIRST_SECONDS`; a
        failure said, never raised. The `Market` answers `event(ref)`, an
        `Event` or None; one that does not reports none. `once` makes one
        pass and answers how many events it reported."""
        reported = 0
        while True:
            try:
                reported += await self._events_pass(clock)
            except Exception as failed:  # noqa: BLE001 - said, and read again on the next pass
                log.warning("events not reported: %s", failed)
            if once:
                return reported
            await sleep(EVENTS_FIRST_SECONDS)

    async def _events_pass(self, clock: Callable[[], float]) -> int:
        read = getattr(self.market, "event", None)
        if not callable(read):
            return 0
        sent = 0
        refs = {m.contract.market for m in self.contracts.mapped() if m.contract.market}
        for ref in sorted(refs):
            at = self._events_read_at.get(ref)
            if at is not None and clock() - at < EVENTS_EVERY_SECONDS:
                continue
            self._events_read_at[ref] = clock()
            event = await asyncio.to_thread(read, ref)
            if event is None or self._events_reported.get(event.ref) == _event_said(event):
                continue
            if await self.report_event(event) is None:
                del self._events_read_at[ref]  # held back: read again on the next pass
                continue
            self._events_reported[event.ref] = _event_said(event)
            sent += 1
        return sent

    # ── Resolving ────────────────────────────────────────────────────────

    def venue_identifiers(self) -> list[ops.Identifier]:
        return [
            ops.Identifier(scheme=scheme, value=value, source=source)
            for scheme, value, source in self.market.venue_identifiers
        ]

    async def venue_id(self) -> str:
        """The venue master's ID for the venue, asked once per reading by its
        identifiers; a venue not held is reported once and left empty."""
        return await self.venue.resolve(
            self.plugin, self.market.venue_identifiers, self.market.venue, self.clock_ns()
        )

    def cash_identifiers(self) -> list[ops.Identifier]:
        """The identifiers the venue's own statements give its cash: a
        currency's ISO 4217 code, or the venue's own token by its code."""
        cash = self.market.cash
        if cash.scheme:
            return [ops.Identifier(scheme=cash.scheme, value=cash.value)]
        return [ops.Identifier(scheme="symbol", value=cash.code, source=self.market.venue)]

    async def cash_id(self) -> str:
        """The deployment's instrument for the venue's cash, resolved once
        (W3.1); what does not resolve is reported once per reason."""
        if self.contracts.cash_id:
            return self.contracts.cash_id
        cash = self.market.cash
        now = self.clock_ns()
        found = await self.plugin.resolve_identifier(
            identifiers=self.cash_identifiers(),
            as_of_ns=now,
            stated_asset_class="cash",
            stated_description=cash.name,
        )
        if found.found and found.instrument_id:
            self.contracts.cash_id = str(found.instrument_id)
            self.contracts.missing.pop(cash.code, None)
            self.contracts.save()
            return self.contracts.cash_id
        reason = ops.MissReason.Name(found.miss_reason or ops.MISS_REASON_NOT_FOUND)
        if self.contracts.missing.get(cash.code) != reason:
            await self.plugin.report_missing_instrument(
                source=self.market.venue,
                asset_class="cash",
                identifiers=self.cash_identifiers(),
                as_of_ns=now,
                reason=found.miss_reason or "not_found",
                observed_at_ns=now,
            )
        self.contracts.missing[cash.code] = reason
        return ""

    def identifiers(self, contract: Contract) -> list[ops.Identifier]:
        """The identifiers the venue's own statements give a contract: its
        code, as a `symbol` with the venue as source."""
        return [ops.Identifier(scheme="symbol", value=contract.code, source=self.market.venue)]

    async def _ticker(self, contract: Contract) -> ops.Identifier | None:
        """The contract's ticker (0.31.0, ruling 312): the venue's own market
        ticker under the contract's `ticker` scheme, its venue in source as
        an ISO 10383 MIC, or the venue master's VEN- ID where the venue has
        no MIC -- what the platform matches and mints on, beside the
        source-scoped symbol. None where the venue is not held."""
        venue = self._mic() or await self.venue_id()
        if not venue:
            return None
        return ops.Identifier(scheme="ticker", value=contract.code, source=venue)

    def _mic(self) -> str:
        """The venue's ISO 10383 MIC, where its statements give one."""
        return next(
            (
                value
                for scheme, value, _ in self.market.venue_identifiers
                if scheme == "iso10383"
            ),
            "",
        )

    async def stated_identifiers(self, contract: Contract) -> list[ops.Identifier]:
        """What the plugin sends for a contract (0.31.0, ruling 312): its
        symbol at the venue and, where the venue is known, its ticker
        (`ticker`), with the venue's MIC, or its VEN- ID, as source. A record
        holding all of them, as a binary event contract, is complete: the
        plugin resolves it no further (W3.1)."""
        held = self.identifiers(contract)
        ticker = await self._ticker(contract)
        return held + ([ticker] if ticker is not None else [])

    async def _stated_identifiers(self, contract: Contract) -> list[ops.Identifier]:
        """`stated_identifiers`, by its 0.31.0 name."""
        return await self.stated_identifiers(contract)

    async def _candidates(self, record: ops.InstrumentRecord) -> list[ops.Identifier]:
        """The record's identifiers that may name one of the venue's
        contracts, in order: the venue's own code -- its symbol at the venue,
        or (0.31.1) its ticker with the venue's MIC or VEN- ID as source, as
        `stated_identifiers` sends it (ruling 312), so a record the platform
        minted with the ticker alone is named -- then another source's
        symbol -- never for a record that is a security, or of another type."""
        held = list(record.identifiers)
        venue = self.market.venue
        own = [i for i in held if i.scheme == "symbol" and i.source == venue and i.value]
        if any(i.scheme == "ticker" and i.value for i in held):
            # The venue master's ID is asked only for a record holding a
            # ticker, and once per reading of the venue.
            sources = {self._mic(), await self.venue_id()} - {""}
            own += [i for i in held if i.scheme == "ticker" and i.source in sources and i.value]
        if (
            record.asset_class not in _EVENT_CLASSES
            or record.instrument_type not in _BINARY_TYPES
            or any(i.scheme in _SECURITY_SCHEMES for i in held)
        ):
            return own
        return own + [i for i in held if i.scheme == "symbol" and i.source != venue and i.value]

    async def contract(self, code: str) -> Contract | None:
        """The venue's contract by its code: as read already, else asked of
        the venue, one contract at a time."""
        held = self.contracts.contracts.get(code)
        if held is not None:
            return held
        read: Contract | None = await self._asked(self.market.contract, code)
        if read is not None:
            self.contracts.contracts[code] = read
        return read

    async def _payout_differs(self, record: ops.InstrumentRecord, contract: Contract) -> bool:
        """Whether the record states a payout the venue's does not match:
        another amount, or another asset than the venue's cash."""
        if not record.HasField("binary_event_contract") or contract.payout is None:
            return False
        stated = as_money(record.binary_event_contract.payout)
        if not stated.amount and not stated.currency_code and not stated.instrument_id:
            return False
        if Decimal(stated.amount) != contract.payout:
            return True
        cash = self.market.cash
        if stated.currency_code:
            return stated.currency_code != cash.currency_code
        return stated.instrument_id != await self.cash_id()

    async def _join(
        self, subject: str, contract: Contract, matched: ops.Identifier, record: Any
    ) -> None:
        """Report the venue's code beside the one the record matched (W3.1),
        with the class, the type and the venue's words offered, where the
        record lacks any of them; meeting another record is a miss (W3.2),
        reported once, and the subject is served all the same."""
        held = list(record.identifiers)
        own = await self.stated_identifiers(contract)
        if (
            all(any(same(o, h) for h in held) for o in own)
            and record.asset_class == ops.ASSET_CLASS_EVENT_CONTRACT
            and record.instrument_type == ops.INSTRUMENT_TYPE_BINARY_EVENT_CONTRACT
        ):
            return
        named = own + ([] if any(same(matched, o) for o in own) else [matched])
        now = self.clock_ns()
        found = await self.plugin.resolve_identifier(
            identifiers=named,
            as_of_ns=now,
            stated_asset_class="event_contract",
            stated_instrument_type="binary_event_contract",
            stated_currency=self.market.cash.currency_code,
            stated_description=contract.title[:MOST_DESCRIPTION],
        )
        if found.found and found.instrument_id == subject:
            return
        # Matched another record: two records for one contract, which a
        # person merges (W3.13).
        miss = ops.MISS_REASON_AMBIGUOUS if found.found else found.miss_reason
        reason = ops.MissReason.Name(miss or ops.MISS_REASON_AMBIGUOUS)
        if self.contracts.missing.get(contract.code) != reason:
            await self.plugin.report_missing_instrument(
                source=self.market.venue,
                asset_class="event_contract",
                identifiers=named,
                as_of_ns=now,
                reason=miss or ops.MISS_REASON_AMBIGUOUS,
                observed_at_ns=now,
            )
        self.contracts.missing[contract.code] = reason

    async def _named(self, subject: str) -> str:
        """The venue's code for the contract a subject is, read from its
        record; empty, with why, where it names none of the venue's binary
        event contracts or cannot be read."""
        if not self.reads_instruments:
            self.unnamed[subject] = NOT_READ
            return ""
        try:
            found = await self.plugin.resolve_instrument(
                instrument_id=subject, as_of_ns=self.clock_ns()
            )
        except NotGranted:
            # A runtime that grants a data plugin no read of what an
            # instrument is (W3.6): asked once, and said on Datasets.
            log.warning(
                "this data plugin may not read an instrument's record; nothing is named"
            )
            self.reads_instruments = False
            self.unnamed[subject] = NOT_READ
            return ""
        if not found.found:
            self.unnamed[subject] = NOT_READ
            return ""
        record = found.instrument
        for matched in await self._candidates(record):
            contract = await self.contract(matched.value)
            if contract is None or not contract.binary:
                continue
            if await self._payout_differs(record, contract):
                log.warning(
                    "%s's record states another payout than %s's", subject, contract.code
                )
                self.unnamed[subject] = PAYOUT_DIFFERS
                return ""
            await self._join(subject, contract, matched, record)
            return contract.code
        self.unnamed[subject] = NOT_A_CONTRACT
        return ""

    async def name(self, subjects: Iterable[str]) -> None:
        """Name each subject not named yet as one of the venue's contracts, and
        resolve the venue's cash once one is; the map kept in storage."""
        changed = False
        for subject in subjects:
            if subject in self.contracts.subjects or subject in self.unnamed:
                continue
            code = await self._named(subject)
            if code:
                self.contracts.subjects[subject] = code
                changed = True
        # The cash is asked once a subject is named, and again after a miss
        # only when a subject is newly named or the day's reading cleared it.
        cash = self.market.cash.code
        if (
            self.contracts.subjects
            and not self.contracts.cash_id
            and (changed or cash not in self.contracts.missing)
        ):
            await self.cash_id()
        if changed:
            self.contracts.save()

    async def reread(self) -> ContractMap:
        """Read each contract serving a subject again from the venue, and ask
        for the venue again; a subject not named is read again when next
        asked."""
        for code in sorted(set(self.contracts.subjects.values())):
            read = await self._asked(self.market.contract, code)
            if read is not None:
                self.contracts.contracts[code] = read
        self.contracts.read_at_ns = self.clock_ns()
        self.contracts.missing.pop(self.market.cash.code, None)
        self.unnamed.clear()
        self.contracts.save()
        self.venue.asked = False
        await self.venue_id()
        await self._outcomes_of(self.contracts.mapped())
        return self.contracts

    # ── Rows ─────────────────────────────────────────────────────────────

    def _money(self, amount: Any, mapped: Mapped) -> Money:
        """An amount in the venue's cash: a currency by its code, the venue's
        token by its own instrument, never a fiat code."""
        code = self.market.cash.currency_code
        if code:
            return Money(amount, code)
        return Money(amount, instrument_id=mapped.cash_id)

    @staticmethod
    def _within(amount: Decimal | None, contract: Contract) -> bool:
        """Whether a price per contract is one: nothing to the payout."""
        if amount is None or amount < 0:
            return False
        return contract.payout is None or amount <= contract.payout

    def _unconverted(self, unread: Iterable[Unread]) -> list[ops.AsReported]:
        return unconverted(self.market.venue, unread, self.venue, self.market.name)

    @staticmethod
    def _ident(seen: Tick | Top) -> str:
        """What a row read from `seen` is keyed by: the venue's identity for
        it, else the day and line of the raw record it was first read from,
        else when it arrived."""
        if seen.ident:
            return seen.ident
        path, _, line = seen.raw_key.partition("#")
        day = next((p for p in path.split("/") if len(p) == 10 and p[4] == "-"), "")
        return f"{day}#{line}" if day and line else str(seen.at_ns)

    def _meta(self, row_key: str, mapped: Mapped, seen: Tick | Top) -> ObservationMeta:
        times = [SourceTime(kind="event", at_ns=seen.at_ns)] if seen.stated else []
        return ObservationMeta(
            row_key=row_key[:128],
            subjects=[ops.SubjectRef(entity_id=mapped.subject)],
            source=ops.Source(dataset=self.dataset(LIVE), venue_id=self.venue.venue_id),
            valid_from_ns=seen.at_ns,
            source_times=times,
            raw=self.plugin.raw_record(seen.raw_key),
            unconverted=self._unconverted(seen.unread),
        )

    def price(self, mapped: Mapped, kind: str, amount: Any, seen: Tick | Top) -> Price:
        """A price per contract of one kind, in the venue's cash."""
        return Price(
            meta=self._meta(f"{mapped.contract.code}:{kind}:{self._ident(seen)}", mapped, seen),
            kind=kind,
            price=self._money(amount, mapped),
            basis="per_unit",
        )

    def quote(self, mapped: Mapped, top: Top) -> Quote | None:
        """The best bid and offer with their sizes; a side the venue states no
        order on, or whose price is no price per contract, left unset."""
        bid = top.bid if self._within(top.bid, mapped.contract) else None
        ask = top.ask if self._within(top.ask, mapped.contract) else None
        if bid is None and ask is None:
            return None
        return Quote(
            meta=self._meta(f"{mapped.contract.code}:quote:{self._ident(top)}", mapped, top),
            bid=None if bid is None else self._money(bid, mapped),
            ask=None if ask is None else self._money(ask, mapped),
            bid_quantity=None if bid is None else top.bid_size,
            ask_quantity=None if ask is None else top.ask_size,
        )

    # ── Recording ────────────────────────────────────────────────────────

    async def _send(self, prices: list[Price], quotes: list[Quote], want_id: str) -> None:
        await self.wants.record("prices", prices, LIVE, want_id)
        await self.wants.record("quotes", quotes, LIVE, want_id)

    async def _asked(self, call: Callable[..., Any], *args: Any) -> Any:
        return await asked(call, *args, of=self.market.name)

    async def record_live(
        self,
        subjects: Iterable[str],
        kinds: Iterable[int] = (),
        want_id: str = "",
        data_type: str = "",
    ) -> dict[str, str]:
        """Each subject's last trade price and best bid and offer now, as
        prices (`data_type` Price), as a quote (Quote), or both (empty); what
        was declined, by subject and reason."""
        await self.venue_id()
        subjects = list(subjects)
        await self.name(subjects)
        wanted = set(kinds) or set(_LIVE_KINDS)
        priced = data_type in ("", PRICE)
        quoted = data_type in ("", QUOTE)
        declined: dict[str, str] = {}
        prices: list[Price] = []
        quotes: list[Quote] = []
        for subject in subjects:
            mapped = self.contracts.serving(subject)
            if mapped is None:
                declined[subject] = "not_covered"
                continue
            before = len(prices) + len(quotes)
            contract = mapped.contract
            if priced and ops.PRICE_KIND_LAST in wanted:
                tick = await self._asked(self.market.last, contract)
                if tick and self._within(tick.price, contract):
                    prices.append(self.price(mapped, "last", tick.price, tick))
                elif tick and (tick.price is not None or tick.unread):
                    self.counts.unread += 1
            if quoted or (priced and wanted & {ops.PRICE_KIND_BID, ops.PRICE_KIND_ASK}):
                best = await self._asked(self.market.top, contract)
                if best is not None:
                    for kind, amount in (("bid", best.bid), ("ask", best.ask)):
                        chosen = priced and getattr(ops, f"PRICE_KIND_{kind.upper()}") in wanted
                        if chosen and self._within(amount, contract):
                            prices.append(self.price(mapped, kind, amount, best))
                        elif amount is not None and not self._within(amount, contract):
                            self.counts.unread += 1
                    self.counts.unread += len(best.unread)
                    if quoted and (row := self.quote(mapped, best)):
                        quotes.append(row)
            if len(prices) + len(quotes) == before:
                declined[subject] = "source_silent"
        await self._send(prices, quotes, want_id)
        await self._outcomes_of(self.contracts.serving(s) for s in subjects)
        return declined

    # ── Outcomes (contract v23) ──────────────────────────────────────────

    @staticmethod
    def _determination(value: Decimal, contract: Contract) -> str | None:
        """What a settlement value per contract says the contract pays: its
        full payout, nothing, or part of it; None for no value per contract."""
        if value < 0:
            return None
        if value == 0:
            return "pays_nothing"
        if contract.payout is None or value > contract.payout:
            return None
        return "pays" if value == contract.payout else "pays_part"

    def outcome(self, mapped: Mapped) -> tuple[Outcome, Recorded] | None:
        """The contract's outcome as the venue now states it, and what to keep
        of it once recorded; None where the venue states no determination,
        or states what was last recorded."""
        contract = mapped.contract
        said = contract.resolution
        if said is None:
            return None
        held = self.contracts.outcomes.get(contract.code)
        value, scheme, word, text = said.value, said.scheme, said.word, said.text
        if value is None or not word:
            # A stage stated with no determination of its own: the one held.
            if held is None:
                return None
            value, scheme, word, text = Decimal(held.value), held.scheme, held.word, held.text
        determination = self._determination(value, contract)
        if determination is None:
            if contract.code not in self.unreadable:
                log.warning("%s's settlement value %s is no value per contract", contract.code,
                            value)  # fmt: skip
                self.unreadable.add(contract.code)
                self.outcome_counts.unread += 1
            return None
        if held is not None and held.says() == (said.stage, value, scheme, word, text,
                                                said.settled_at_ns):  # fmt: skip
            return None
        if said.determined_at_ns:
            at, stated = said.determined_at_ns, True
        elif held is not None and (Decimal(held.value), held.word) == (value, word):
            at, stated = held.valid_from_ns, held.stated
        else:
            at, stated = contract.read_at_ns or self.clock_ns(), False
        kept = Recorded(said.stage, str(value), scheme, word, text, said.settled_at_ns, at,
                        stated, contract.raw_key)  # fmt: skip
        row = Outcome(
            meta=ObservationMeta(
                row_key=f"{contract.code}:outcome"[:128],
                subjects=[ops.SubjectRef(entity_id=mapped.subject)],
                source=ops.Source(dataset=self.dataset(OUTCOMES), venue_id=self.venue.venue_id),
                valid_from_ns=at,
                source_times=[SourceTime(kind="event", at_ns=at)] if stated else [],
                raw=self.plugin.raw_record(contract.raw_key),
                unconverted=self._unconverted(said.unread),
            ),
            determination=determination,
            stage=said.stage,
            settlement_value=self._money(value, mapped),
            settled_at_ns=said.settled_at_ns,
            determination_as_reported=ops.AsReported(
                scheme=scheme[:64], code=word[:128], text=(text or word)[:256]
            ),
        )
        return row, kept

    async def record_outcomes(self, mapped: Iterable[Mapped | None]) -> int:
        """Each contract's outcome where the venue's statement of it changed,
        in batches; how many versions were sent."""
        serving = [m for m in mapped if m is not None and m.contract.resolution is not None]
        if not serving:
            return 0
        await self.venue_id()
        rows: list[Outcome] = []
        kept: dict[str, Recorded] = {}
        for each in serving:
            if each.contract.code in kept:
                continue
            built = self.outcome(each)
            if built is not None:
                rows.append(built[0])
                kept[each.contract.code] = built[1]
        await self.wants.record("outcomes", rows, OUTCOMES, overall=False)
        if kept:
            self.contracts.outcomes.update(kept)
            self.contracts.save()
        return len(rows)

    async def _outcomes_of(self, mapped: Iterable[Mapped | None]) -> None:
        """Record outcomes beside other work, a refusal said and not raised:
        the work it is beside still answers."""
        try:
            await self.record_outcomes(mapped)
        except Exception as failed:  # noqa: BLE001 - said; the next pass tries again
            log.warning("outcomes not recorded: %s", failed)

    async def watch_outcomes(self) -> int:
        """Read again each contract past its close or no longer trading, its
        final stage not yet recorded, and record its outcome where the
        venue's statement changed."""
        now = self.clock_ns()
        due: list[Mapped] = []
        for mapped in self.contracts.mapped():
            contract = mapped.contract
            held = self.contracts.outcomes.get(contract.code)
            if held is not None and held.stage == FINAL:
                continue
            if contract.tradable and contract.closes_at_ns > now:
                continue
            read = await self._asked(self.market.contract, contract.code, True)
            if read is None:
                continue
            self.contracts.contracts[contract.code] = read
            due.append(Mapped(read, mapped.subject, mapped.cash_id))
        if due:
            self.contracts.save()
        return await self.record_outcomes(due)

    # ── Wants ────────────────────────────────────────────────────────────

    async def on_want(self, heard: Any) -> None:
        """Record what the lake wants, or decline it per subject."""
        await self.wants.hear(heard, self._answer)

    def _when(self, want: ops.ObservationsWantedEvent) -> str:
        """Whether a want's day or range is past, to come, or covers now: the
        venue's public reads answer now alone."""
        now = self.clock_ns()
        if want.business_date:
            day = date.fromisoformat(want.business_date)
            today = utc_day(now // NANOS_PER_SECOND)
            return "past" if day < today else "coming" if day > today else "now"
        if want.valid_from_ns:
            if want.valid_from_ns > now:
                return "coming"
            if want.valid_until_ns and want.valid_until_ns <= now - NANOS_PER_SECOND:
                return "past"
        return "now"

    async def _answer(
        self,
        want: ops.ObservationsWantedEvent,
        key: str,
        subjects: list[str],
        kinds: tuple[int, ...],
    ) -> dict[str, str]:
        if (
            key != LIVE
            or want.data_type not in ("", PRICE, QUOTE)
            or (want.data_type != QUOTE and kinds and not set(kinds) & _LIVE_KINDS)
        ):
            return {s: "not_covered" for s in subjects}
        when = self._when(want)
        if when != "now":
            return {
                s: "beyond_history" if when == "past" else "source_silent" for s in subjects
            }
        if want.standing:
            self.wants.stand(want, subjects, kinds)
        return await self.record_live(subjects, kinds, want.want_id, want.data_type)

    async def on_withdrawn(self, heard: Any) -> None:
        """A standing want withdrawn: its subjects are no longer kept current."""
        self.wants.withdraw(heard.message.want_id)

    # ── Keeping current ──────────────────────────────────────────────────

    async def current(self) -> None:
        """One pass keeping each standing want's subjects current."""
        for data_type, kinds, subjects in _grouped(self.standing.values()):
            await self.record_live(subjects, kinds, data_type=data_type)

    async def keep_current(
        self, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    ) -> None:
        """Keep each standing want's subjects current, until cancelled: at most
        once a second; each contract, and the venue, read again once a day;
        and each minute the contracts due for their outcome."""
        last_read = last_watched = time.monotonic()
        while True:
            now = time.monotonic()
            try:
                if now - last_read >= REREAD_SECONDS:
                    await self.reread()
                    last_read = now
                if now - last_watched >= OUTCOME_EVERY_SECONDS:
                    last_watched = now
                    await self.watch_outcomes()
                await self.current()
            except Exception as failed:  # noqa: BLE001 - said, and tried again next time
                log.warning("keeping current stopped this time: %s", failed)
            await sleep(LIVE_EVERY_SECONDS)


def _offered(bound: Bound | None) -> EventContractBound | None:
    return (
        None
        if bound is None
        else EventContractBound(value=bound.value, inclusive=bound.inclusive)
    )


def _event_said(event: Event) -> tuple[object, ...]:
    """What a venue states of an event that a new version would change."""
    return (
        event.members,
        event.mutually_exclusive,
        event.exhaustive,
        event.series,
        event.title,
    )


def _grouped(wants: Iterable[Standing]) -> list[tuple[str, tuple[int, ...], list[str]]]:
    """The standing wants' subjects, once each, by the data type and kinds
    asked."""
    by_ask: dict[tuple[str, tuple[int, ...]], set[str]] = {}
    for want in wants:
        by_ask.setdefault((want.data_type, tuple(sorted(want.kinds))), set()).update(
            want.subjects
        )
    return [(dt, kinds, sorted(subjects)) for (dt, kinds), subjects in sorted(by_ask.items())]


# ── The pages ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConnectionRead(VenueConnection):
    """The role's Connection for an event-contract venue: the venue's part
    (`VenueConnection`). It reads each contract when it is wanted and keeps
    no stream open, so "Stream" says "Does not stream"."""


@dataclass(frozen=True)
class NotServed:
    """Subjects not served, by why."""

    why: str
    subjects: int


@dataclass(frozen=True)
class DatasetsRead(RoleDatasetsRead):
    """The role's Datasets for an event-contract venue, and the venue's
    contract map, cash and payouts: wants kept current, contracts read and
    mapped, subjects named and not served by why, the cash and the record
    it resolved to, each contract's payout, how the venue's sides make a
    contract (`vendor_note`, the plugin's words), what did not resolve, when
    the contracts were read, and rows restated, unchanged and not read."""

    standing_wants: int = 0
    contracts_read: int = 0
    contracts_mapped: int = 0
    subjects_named: int = 0
    not_served: list[NotServed] = field(default_factory=list)
    payouts_differ: int = 0
    cash: str = ""
    cash_instrument: str = ""
    payouts: list[str] = field(default_factory=list)
    vendor_note: str = ""
    assets_not_resolved: list[str] = field(default_factory=list)
    contracts_read_at: str = ""
    restated: int = 0
    unchanged: int = 0
    not_read: int = 0


def connection_read(
    feed: Feed | None, venue_name: str, entitled_at_vendor: str
) -> ConnectionRead:
    """Connection's record (`read_connection`), drawn by the template
    `meridian/roles/data/event_contracts/connection.html`."""
    if feed is None:
        return ConnectionRead(
            mode="Live", entitled_at_vendor=entitled_at_vendor, venue=venue_name
        )
    return ConnectionRead(
        **connection_fields(
            feed.market.session, feed.market.name, feed.venue, entitled_at_vendor
        ),
        # It reads each contract when it is wanted and keeps no stream open.
        sessions=None,
    )


def datasets_read(
    feed: Feed | None,
    catalogue: Sequence[Any],
    instance: str,
    entitled_at_vendor: str,
    vendor_note: str = "",
) -> DatasetsRead:
    """Datasets' record (`read_datasets`), drawn by the template
    `meridian/roles/data/event_contracts/datasets.html`; `instance` names the
    datasets before the plugin has started, and `vendor_note` says in the
    venue's words how its sides make a contract."""
    if feed is None:
        return DatasetsRead(
            served=served(catalogue, instance, None, entitled_at_vendor),
            vendor_note=vendor_note,
        )
    reasons: dict[str, int] = {}
    for why in feed.unnamed.values():
        reasons[why] = reasons.get(why, 0) + 1
    mapped = feed.contracts.mapped()
    cash = feed.market.cash
    payouts = sorted(
        {f"{m.contract.payout} {cash.code}" for m in mapped if m.contract.payout is not None}
    )
    return DatasetsRead(
        served=served(
            catalogue, feed.plugin.identity.instance_id, feed.wants, entitled_at_vendor
        ),
        wants=list(want_rows(feed.wants)),
        reads_instruments=feed.reads_instruments,
        standing_wants=len(feed.standing),
        contracts_read=len(feed.contracts.contracts),
        contracts_mapped=len(mapped),
        subjects_named=len(feed.contracts.subjects),
        not_served=[NotServed(why, n) for why, n in sorted(reasons.items())],
        payouts_differ=reasons.get(PAYOUT_DIFFERS, 0),
        cash=cash.code,
        cash_instrument=feed.contracts.cash_id,
        payouts=payouts,
        vendor_note=vendor_note,
        assets_not_resolved=sorted(feed.contracts.missing),
        contracts_read_at=iso_time(feed.contracts.read_at_ns),
        restated=feed.counts.restated,
        unchanged=feed.counts.unchanged,
        not_read=feed.counts.unread,
    )


def figures_read(feed: Feed | None, catalogue: Sequence[Any]) -> list[Figure]:
    """The data role's figures on the Summary, in its order: Connection,
    Entitled at the vendor, Stream ("Does not stream") and Last recorded. A
    venue stating no running rate to measure against leaves Rate use out."""
    if feed is None:
        return role_figures(connection="Answering", stream="Does not stream")
    said = connection_read(feed, feed.market.name, "")
    last = max(feed.sent_to(LIVE).last_ns, feed.outcome_counts.last_ns)
    return role_figures(
        connection=connection_figure(said.mode, said.healthy, said.last_error),
        entitled_at_vendor=f"{len(catalogue)} of {len(catalogue)} datasets",
        stream="Does not stream",
        last_recorded=datetime.fromtimestamp(last / 1e9, tz=UTC) if last else None,
    )
