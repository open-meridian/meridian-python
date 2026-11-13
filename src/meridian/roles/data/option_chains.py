"""A data plugin's listed option chains, generic over the source (SDK 0.35;
spec/each-role-is-one-generated-class, section 4, 924's item 7, ruling
1016; the data-plugin fit review's section 1.11). Tradier's, Massive's and
Databento's plugins each kept the same 500-750 line machine, and Unusual
Whales part of it; it is the SDK's now, each plugin keeping its source's
client and conversion -- a `ChainSource`:

    class Source:                                   # the plugin's, blocking calls
        def expirations(self, symbol) -> list[date]: ...
        def chain(self, symbol, expiration) -> list[option_chains.ChainOption]: ...
        def trades(self, osi, since_ns) -> list[option_chains.SourceTrade]: ...   # optional

    chains = option_chains.Feed(Source(), market_days=days)      # a data role class
    meridian.run(declaration=DECLARATION, roles=[chains])

or, where one class also serves listings (a plugin registers one class per
role), held by it and given it as `role`, the listings class handing it the
wants of its dataset (`serves`):

    class Lake(listings.Feed):
        def __init__(self, ...):
            super().__init__(...)
            self.chains = option_chains.Feed(Source(), role=self, market_days=days)

        async def on_observations_wanted(self, heard):
            if self.chains.serves(heard.message.dataset):
                return await self.chains.on_observations_wanted(heard)
            await super().on_observations_wanted(heard)

**One dataset, `options`** (or one per timeliness, as a listings feed's:
`timeliness=` and `datasets_by_timeliness=`): each series' terms
(`meridian.v1.ListedSeries`, the platform's listed-option template), its
open interest and volume (`Statistic`), its best bid and offer (`Quote`)
and its trades (`Trade`), every row under the underlying's record with the
series' OCC OSI symbol as its series key (ruling 561: never minted, never
resolved; `helpers.chains`).

**Bounded by what readers ask** (rulings 152 and 821): a want names its
underlyings and the expirations (`expiration_from`, `expiration_to`) or
series it shows; only those are read and recorded, at most
`reads_per_minute` chain reads a minute, a reader waiting before a standing
want kept current. A standing want is read again every `cadence_seconds`
by `run()`. Only what changed is sent again (`SentRows`): a series' terms,
a quote's prices and sizes, a statistic's value. Each pass that read
quotes records the dataset's liveness.

**A row key fixes its valid time** (spec/the-lake rule 5; SDK 0.36.2): a
series' terms are sent again under their key's first valid time, kept with
a digest of the terms in the plugin's storage where the feed is given
`series_path` (a JSON file, `series.json` beside its raw records), in memory
otherwise; terms changed since are an adjustment, a new key
(`<OSI>:<date>:ADJ`) valid from the start of today. A re-send the lake
refuses naming its valid time, the terms unchanged (the storage lost), is
taken as recorded, said once per series.

**Dated by the market's days** (`helpers.calendars.MarketDays`): open
interest is the market day before today's, volume today's once it is a
market day; where the calendar does not answer, none is recorded rather
than misdated. Each is valid from the start of the day it describes, in the
calendar's `day_clock` (New York's where it has none), never when it was
read (SDK 0.36.2, the-lake rule 5).

**Timeliness**: on a plan not real time, quotes and trades are declined,
not covered; a range of trades is read only where the source states its
trade history (`ChainSource.trades`), else declined.

**Trades streamed** for the series a standing want of trades names, at most
`stream_limit`: `streamed` is what the plugin's `helpers.sessions.
Supervisor` is to want (`restream` hands it on where `streamer` is set),
`heard` takes its statements and `flush` records them every half second,
none twice. Rows recorded unasked or for a standing want are aged and
judged at the edge (`latency`, `quality`), each series on its own.

A rule of the role's is kept here, never a vendor's: how a source is
reached, its pacing and its conversion are the plugin's.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import os
import re
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from ...errors import CallFailed, MeridianError
from ...operations import Money, ObservationMeta, Quote, SourceTime, SubjectRef, Trade
from ...plugin.v1 import operations_pb2 as ops
from ...receive import Heard
from .._generated.data import Role
from ._rows import SentRows, _digest
from ._settings import REAL_TIME

__all__ = [
    "OPTIONS",
    "QUOTE",
    "SERIES",
    "STATISTIC",
    "TRADE",
    "ChainOption",
    "ChainSource",
    "Feed",
    "SourceTrade",
]

log = logging.getLogger("meridian.roles.data.option_chains")

OPTIONS = "options"
SERIES = "meridian.v1.ListedSeries"
STATISTIC = "meridian.v1.Statistic"
QUOTE = "meridian.v1.Quote"
TRADE = "meridian.v1.Trade"
DATA_TYPES = (SERIES, STATISTIC, QUOTE, TRADE)
#: What a plan not real time serves of a chain.
NOT_LIVE = (SERIES, STATISTIC)
#: The platform's listed-option template (ruling 617) and its version.
TEMPLATE_ID = "TPL-listed-option"
TEMPLATE_VERSION = "1"
NS = 1_000_000_000
MINUTE_NS = 60 * NS
BATCH = 500
#: Streamed trades wait at most this long before they are recorded.
TRADE_EVERY_NS = NS // 2
#: How many trades recorded are remembered, so none is sent twice.
RECENT_TRADES = 50_000
#: A refusal's path to the row it is about, in a batch of series.
_ROW = re.compile(r"(?:^|\.)series\[(\d+)\]")


@dataclass(frozen=True)
class ChainOption:
    """One series of a chain as the source states it: its OCC OSI symbol,
    its terms (style and settlement by the template's values, its
    multiplier, and whether it is standard -- 100 shares of the underlying,
    delivered), and what it states now, each None where it states none: its
    best bid and offer with their sizes in contracts and their time, its
    open interest and its volume. Every number a `Decimal` from the source's
    own text."""

    osi: str
    expiration: dt.date
    exercise_style: str = "EXERCISE_STYLE_AMERICAN"
    settlement_method: str = "SETTLEMENT_METHOD_PHYSICAL"
    multiplier: Decimal = Decimal(100)
    standard: bool = True
    bid: Decimal | None = None
    ask: Decimal | None = None
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None
    quoted_at_ns: int = 0
    open_interest: Decimal | None = None
    volume: Decimal | None = None
    raw_key: str = ""
    unconverted: tuple[ops.AsReported, ...] = ()


@dataclass(frozen=True)
class SourceTrade:
    """One option trade as the source states it: its series, when, its
    price and size (None where they did not convert), where it printed (the
    source's code, kept as reported), the side that took liquidity where
    the source says it, and its raw record and row key."""

    osi: str
    at_ns: int
    price: Decimal | None
    quantity: Decimal | None
    row_key: str
    raw_key: str = ""
    venue_code: str = ""
    aggressor: str = ""
    unconverted: tuple[ops.AsReported, ...] = ()


class ChainSource(Protocol):
    """The source, as the feed asks it: blocking calls, run in a thread. It
    may also read a series' trades since a moment, `trades(osi, since_ns)`;
    the feed asks only where the source has it."""

    def expirations(self, symbol: str) -> list[dt.date]: ...

    def chain(self, symbol: str, expiration: dt.date) -> list[ChainOption]: ...


@dataclass
class _Underlying:
    """One underlying whose chain is wanted: its symbol, its expirations,
    what each standing want keeps current (data type and expirations), and
    the series each standing want of trades streams."""

    subject: str
    symbol: str
    expirations: list[dt.date] = field(default_factory=list)
    listed_on: dt.date | None = None
    standing: dict[str, tuple[str, frozenset[dt.date], frozenset[str]]] = field(
        default_factory=dict
    )
    trades: dict[str, list[str]] = field(default_factory=dict)
    read_at_ns: int = 0
    stats_on: dt.date | None = None


@dataclass
class Counts:
    """What the chain dataset did since the plugin started."""

    wants: int = 0
    recorded: int = 0
    restated: int = 0
    unchanged: int = 0
    declined: int = 0
    unconverted: int = 0
    reads: int = 0
    last_recorded_at_ns: int = 0
    last_declined: str = ""


class _FirstTimes:
    """Each series' terms as last sent, by dataset and OSI symbol: the
    valid time of their key's first record, a digest of the terms, and the
    date they were adjusted from ("" for the series' own key). A row key
    fixes its valid time (spec/the-lake rule 5), so terms are sent again
    under that time, never a later read's; kept in the plugin's storage
    where the feed is given `series_path`, so a restart keeps them too, as
    JSON: `{"series": {"<dataset>": {"<OSI>": {"adjusted_on": "",
    "terms": "<hex>", "valid_from_ns": <ns>}}}}`. A change is staged until
    the lake has the batch holding it (`commit`), and a series past its
    expiration is let go when the map is saved."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.held: dict[str, dict[str, dict[str, Any]]] = {}
        self.staged: dict[tuple[str, str], dict[str, Any]] = {}
        if path is not None and path.is_file():
            body = json.loads(path.read_text(encoding="utf-8"))
            self.held = {d: dict(by) for d, by in body.get("series", {}).items()}

    def get(self, dataset: str, osi: str) -> dict[str, Any] | None:
        return self.staged.get((dataset, osi)) or self.held.get(dataset, {}).get(osi)

    def stage(
        self, dataset: str, osi: str, valid_from_ns: int, terms: str, adjusted_on: str
    ) -> None:
        self.staged[(dataset, osi)] = {
            "adjusted_on": adjusted_on, "terms": terms, "valid_from_ns": valid_from_ns,
        }  # fmt: skip

    def discard(self) -> None:
        self.staged.clear()

    def commit(self, rows: Sequence[Any], today: dt.date) -> None:
        """What was staged for `rows`, a batch the lake has, kept; every
        series expired let go, and the map written where it has a path."""
        done = [
            (row.meta.source.dataset, row.meta.series_key[0].value)
            for row in rows
            if row.meta is not None and row.meta.series_key
        ]
        kept = {each: self.staged.pop(each) for each in done if each in self.staged}
        if not kept:
            return
        for (dataset, osi), held in kept.items():
            self.held.setdefault(dataset, {})[osi] = held
        for by in self.held.values():
            for osi in [o for o in by if _expiration(o) < today]:
                del by[osi]
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        written = self.path.with_suffix(".tmp")
        body = {"series": {d: dict(sorted(by.items())) for d, by in sorted(self.held.items())}}
        written.write_text(json.dumps(body, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(written, self.path)


def _expiration(osi: str) -> dt.date:
    from ...helpers import chains

    try:
        return chains.osi_terms(osi)[1]
    except ValueError:
        return dt.date.max


@dataclass
class _Done:
    """What a batch of series sent in parts did, as one answer."""

    recorded: int = 0
    restated: int = 0
    unchanged: int = 0

    def add(self, answer: Any) -> None:
        self.recorded += int(getattr(answer, "recorded", 0))
        self.restated += int(getattr(answer, "restated", 0))
        self.unchanged += int(getattr(answer, "unchanged", 0))


def _window(want: Any) -> tuple[dt.date | None, dt.date | None]:
    first = dt.date.fromisoformat(want.expiration_from) if want.expiration_from else None
    last = dt.date.fromisoformat(want.expiration_to) if want.expiration_to else None
    return first, last


class Feed(Role):
    """A source's option chains (see the module): the data role's class,
    registered by itself or held by another data role class given as
    `role`, whose connection it acts through."""

    def __init__(
        self,
        source: ChainSource | None,
        *,
        role: Any = None,
        key: str = OPTIONS,
        source_name: str = "",
        currency: str = "USD",
        market_days: Any = None,
        timeliness: str = "",
        datasets_by_timeliness: Mapping[str, str] | None = None,
        reads_per_minute: int = 10,
        cadence_seconds: int = 60,
        stream_limit: int = 1_000,
        remembered: int = 200_000,
        symbol_of: Callable[[str], Any] | None = None,
        clock_ns: Callable[[], int] = time.time_ns,
        series_path: Path | None = None,
    ) -> None:
        if reads_per_minute < 1 or cadence_seconds < 1 or stream_limit < 0:
            raise ValueError("reads_per_minute and cadence_seconds are at least 1")
        self.source = source
        self._within = role
        self.key = key
        self.source_name = source_name or getattr(role, "source_name", "")
        self.currency = currency
        self.market_days = market_days
        self._timeliness = timeliness
        self.datasets_by_timeliness = dict(datasets_by_timeliness or {})
        self._keys = {key, *self.datasets_by_timeliness.values()}
        self.reads_per_minute = reads_per_minute
        self.cadence_ns = cadence_seconds * NS
        self.stream_limit = stream_limit
        self.sent = SentRows(remembered)
        #: Each series' first valid time and terms as sent (SDK 0.36.2).
        self._first_times = _FirstTimes(series_path)
        #: The series a refusal of their first valid time was taken as
        #: recorded for, each said once.
        self._taken_as_recorded: set[tuple[str, str]] = set()
        self._symbol_of = symbol_of
        self.clock_ns = clock_ns
        self.counts = Counts()
        self.underlyings: dict[str, _Underlying] = {}
        self.by_want: dict[str, list[int]] = {}
        self._calls: deque[int] = deque()
        #: The series streamed, as OSI symbols, those past the limit, and the
        #: plugin's supervisor that streams them, where there is one.
        self.streamed: list[str] = []
        self.past_limit: set[str] = set()
        self.streamer: Any = None
        self.pending_trades: list[Trade] = []
        self.recent: OrderedDict[str, None] = OrderedDict()
        self._trades_at = 0
        self.alive_ns = 0
        self.liveness_ns = 0
        self.last_error = ""
        #: The plugin's `roles.Latency` and the edge's checks, where it keeps them.
        self.latency: Any = None
        self.quality: Any = None

    # ── The connection: its own, or the class it is held by ─────────────

    @property
    def plugin(self) -> Any:
        if self._within is not None:
            return self._within.plugin
        return super().plugin

    # ── Names ────────────────────────────────────────────────────────────

    @property
    def timeliness(self) -> str:
        """The plan's timeliness in force ("" for one dataset)."""
        return self._timeliness

    @timeliness.setter
    def timeliness(self, value: str) -> None:
        """The plan changed: what was wanted is let go, and the lake asks
        again of the dataset now in force."""
        if value != self._timeliness:
            self._timeliness = value
            self.underlyings.clear()
            self.restream()

    def in_force(self) -> str:
        """The dataset key the chain is recorded into now."""
        if self.datasets_by_timeliness and self._timeliness:
            return self.datasets_by_timeliness.get(self._timeliness, self.key)
        return self.key

    def dataset(self) -> str:
        """The dataset's ID the chain is recorded into now."""
        return f"{self.plugin.identity.instance_id}:{self.in_force()}"

    def serves(self, dataset: str) -> bool:
        """Whether a want of `dataset` is the chain's."""
        return dataset.rpartition(":")[2] in self._keys

    def _now(self) -> int:
        return int(self.clock_ns())

    def _today(self) -> dt.date:
        clock = getattr(self.market_days, "day_clock", None)
        if clock is not None:
            return dt.datetime.fromtimestamp(self._now() / NS, clock.zone).date()
        return dt.datetime.fromtimestamp(self._now() / NS, dt.UTC).date()

    async def _fetch(self, call: Callable[[], Any]) -> Any:
        """A blocking call to the source, in a thread; None where it failed."""
        try:
            answer = await asyncio.to_thread(call)
        except Exception as failed:  # noqa: BLE001 - the source's failure, said
            self.last_error = f"{type(failed).__name__}: {failed}"[:300]
            log.warning("the chain source failed: %s", self.last_error)
            return None
        self.last_error = ""
        return answer

    async def symbol_of(self, subject: str) -> str | None:
        """The underlying's symbol at the source: the plugin's `symbol_of`,
        else the class holding this one's, else the record's own symbol
        (this source's first)."""
        if self._symbol_of is not None:
            found: str | None = await self._symbol_of(subject)
            return found
        held = getattr(self._within, "symbol_of", None)
        if held is not None:
            answer: str | None = await held(subject)
            return answer
        try:
            found_record = await self.resolve_instrument(
                instrument_id=subject, as_of_ns=self._now()
            )
        except MeridianError:
            return None
        if not found_record.found:
            return None
        symbols = [i for i in found_record.instrument.identifiers if i.scheme == "symbol"]
        own = [i for i in symbols if i.source == self.source_name]
        chosen = (own or symbols)[:1]
        return chosen[0].value.upper() if chosen else None

    # ── Wants (W10.7) ────────────────────────────────────────────────────

    def refused(self, want: ops.ObservationsWantedEvent) -> str:
        """Why a want of the chain is not the plan's to answer, or ""."""
        if want.dataset.rpartition(":")[2] != self.in_force():
            return "not_covered"
        if want.data_type not in DATA_TYPES:
            return "not_covered"
        if self._timeliness not in ("", REAL_TIME) and want.data_type not in NOT_LIVE:
            # Quotes and trades are a real-time plan's alone.
            return "not_covered"
        if want.data_type == TRADE and not want.standing and not self.reads_trades:
            return "not_covered"
        if self.source is None:
            return "source_silent"
        return ""

    @property
    def reads_trades(self) -> bool:
        """Whether the source reads a series' trade history."""
        return self.source is not None and callable(getattr(self.source, "trades", None))

    async def on_observations_wanted(self, heard: Heard[ops.ObservationsWantedEvent]) -> None:
        """A want of a chain's series, statistics, quotes or trades: each
        subject an underlying, the expirations or series it names recorded
        (and kept current, standing), or declined with why."""
        want = heard.message
        subjects = [s.entity_id for s in want.subjects]
        self.counts.wants += 1
        reason = self.refused(want)
        if reason:
            await self.decline(want.want_id, subjects, reason)
            return
        first, last = _window(want)
        keys = frozenset(k.value for k in want.series_keys if k.scheme == "occ_osi")
        declined: dict[str, list[str]] = {}
        for subject in subjects:
            held = await self.underlying(subject)
            if isinstance(held, str):
                declined.setdefault(held, []).append(subject)
                continue
            days = frozenset(
                d for d in held.expirations
                if (first is None or d >= first) and (last is None or d <= last)
            )  # fmt: skip
            if not days:
                declined.setdefault("not_covered", []).append(subject)
                self._forget(held)
                continue
            if want.data_type == TRADE:
                if want.standing:
                    options = await self._chain(held, days)
                    if options is None:
                        declined.setdefault("source_silent", []).append(subject)
                        continue
                    held.trades[want.want_id] = sorted(
                        o.osi for o in options if not keys or o.osi in keys
                    )
                else:
                    why = await self._trades_between(held, days, keys, want)
                    if why:
                        declined.setdefault(why, []).append(subject)
                continue
            why = await self.record(held, want.data_type, days, keys, want.want_id)
            if why:
                declined.setdefault(why, []).append(subject)
            elif want.standing:
                held.standing[want.want_id] = (want.data_type, days, keys)
            self._forget(held)
        for why, refused in sorted(declined.items()):
            await self.decline(want.want_id, refused, why)
        if want.data_type == TRADE and want.standing:
            past = self.restream()
            over = [
                s
                for s in subjects
                if s in self.underlyings
                and any(o in past for o in self.underlyings[s].trades.get(want.want_id, []))
            ]
            await self.decline(want.want_id, over, "not_entitled")

    async def on_want_withdrawn(self, heard: Heard[ops.WantWithdrawnEvent]) -> None:
        """A standing want withdrawn: its chains no longer kept current, its
        series no longer streamed for it."""
        want_id = heard.message.want_id
        streamed = False
        for held in list(self.underlyings.values()):
            held.standing.pop(want_id, None)
            streamed = held.trades.pop(want_id, None) is not None or streamed
            self._forget(held)
        if streamed:
            self.restream()

    async def decline(self, want_id: str, subjects: Sequence[str], reason: str) -> None:
        """Decline `subjects` of a want with a reason, counted."""
        if not subjects or not want_id:
            return
        for start in range(0, len(subjects), BATCH):
            await self.decline_want(
                want_id=want_id,
                subjects=[SubjectRef(entity_id=s) for s in subjects[start : start + BATCH]],
                reason=reason,
            )
        self.counts.declined += len(subjects)
        self.counts.last_declined = reason
        self.by_want.setdefault(want_id, [0, 0])[1] += len(subjects)

    async def underlying(self, subject: str) -> _Underlying | str:
        """The underlying a subject is, its expirations read once a day; or
        why its chain is not read: no symbol, or none listed (`not_covered`),
        or the source not answering (`source_silent`)."""
        source = self.source
        held = self.underlyings.get(subject)
        if held is None:
            symbol = await self.symbol_of(subject)
            if symbol is None:
                return "not_covered"
            held = _Underlying(subject, symbol)
        today = self._today()
        if held.listed_on != today:
            if source is None:
                return "source_silent"
            symbol = held.symbol
            listed = await self._fetch(lambda: source.expirations(symbol))
            if listed is None:
                return "source_silent"
            held.expirations = sorted(d for d in listed if d >= today)
            held.listed_on = today
        if not held.expirations:
            return "not_covered"
        self.underlyings[subject] = held
        return held

    def _forget(self, held: _Underlying) -> None:
        if not held.standing and not held.trades:
            self.underlyings.pop(held.subject, None)

    # ── Reading ──────────────────────────────────────────────────────────

    def budget(self) -> int:
        """The chain reads still allowed this minute."""
        now = self._now()
        while self._calls and self._calls[0] <= now - MINUTE_NS:
            self._calls.popleft()
        return self.reads_per_minute - len(self._calls)

    async def _chain(
        self, held: _Underlying, days: frozenset[dt.date]
    ) -> list[ChainOption] | None:
        """The series of `days`' expirations, each read within the minute's
        budget; None where the source did not answer or the budget is spent."""
        source = self.source
        if source is None:
            return None
        found: list[ChainOption] = []
        symbol = held.symbol
        for day in sorted(days):
            if self.budget() <= 0:
                return found or None
            self._calls.append(self._now())
            self.counts.reads += 1
            read = await self._fetch(lambda day=day: source.chain(symbol, day))  # type: ignore[misc]
            if read is None:
                return None
            for each in read:
                if isinstance(each, ChainOption):
                    found.append(each)
                    self.counts.unconverted += len(each.unconverted)
                else:
                    self.counts.unconverted += 1
        held.read_at_ns = self._now()
        return found

    async def record(
        self,
        held: _Underlying,
        data_type: str,
        days: frozenset[dt.date],
        keys: frozenset[str],
        want_id: str,
    ) -> str:
        """The chain of `days`' expirations read and its rows of
        `data_type` recorded, each only where changed (or for a reader
        waiting); why none could be, or ""."""
        options = await self._chain(held, days)
        if options is None:
            return "source_silent"
        chosen = [o for o in options if not keys or o.osi in keys]
        if data_type == SERIES:
            rows = [r for o in chosen if (r := self._series(held, o, want_id)) is not None]
            try:
                await self.send(SERIES, rows, want_id)
            finally:
                # What no batch the lake has holds is staged no longer.
                self._first_times.discard()
        elif data_type == STATISTIC:
            stats = await self._statistics(held, chosen, want_id)
            if stats is None:
                return "source_silent"
            await self.send(STATISTIC, stats, want_id)
        else:
            self.alive_ns = self._now()
            rows = [r for o in chosen if (r := self._quote(held, o, want_id)) is not None]
            await self.send(QUOTE, rows, want_id)
            await self.alive()
        return ""

    def _raw(self, key: str) -> Any:
        return self.plugin.raw_record(key[:256]) if key else None

    def _day_clock(self) -> Any:
        return getattr(self.market_days, "day_clock", None)

    def _series(self, held: _Underlying, option: ChainOption, want_id: str) -> Any | None:
        """A series' terms to send, or None where they are as last sent and
        no reader waits. A row key fixes its valid time (the-lake rule 5):
        a series' terms keep their key's first valid time (`_first_times`);
        terms changed since are an adjustment, a new key effective from
        today (`helpers.chains.option_series`' `adjusted_on`)."""
        from ...helpers import chains

        dataset = self.dataset()

        def built(valid_from_ns: int, adjusted_on: str | None) -> Any:
            return chains.option_series(
                held.subject,
                option.osi,
                template_id=TEMPLATE_ID,
                template_version=TEMPLATE_VERSION,
                dataset=dataset,
                currency=self.currency,
                exercise_style=option.exercise_style,
                settlement_method=option.settlement_method,
                contract_multiplier=option.multiplier,
                deliverable=[(held.subject, option.multiplier)] if option.standard else (),
                valid_from_ns=valid_from_ns,
                raw=self._raw(option.raw_key),
                adjusted_on=adjusted_on,
                day_clock=self._day_clock(),
            )

        try:
            row = built(self._now(), None)
        except ValueError:
            self.counts.unconverted += 1
            return None
        terms = _digest([(f.path, f.value) for f in row.fields]).hex()
        kept = self._first_times.get(dataset, option.osi)
        if kept is None:
            self._first_times.stage(dataset, option.osi, row.meta.valid_from_ns, terms, "")
            return row
        if kept["terms"] == terms:
            if not want_id:
                return None
            return built(int(kept["valid_from_ns"]), kept["adjusted_on"] or None)
        row = built(0, self._today().isoformat())
        self._first_times.stage(
            dataset, option.osi, row.meta.valid_from_ns, terms, self._today().isoformat()
        )
        return row

    async def _record_series(self, rows: list[Any], want_id: str) -> _Done:
        """Series recorded; a series' terms the lake refuses naming their
        valid time -- held under another first valid time, as after the
        plugin's storage was lost -- taken as recorded where the feed has not
        changed them (its own key, never an adjustment's): said once per
        series, never sent again for it."""
        done = _Done()
        while rows:
            try:
                answer = await self.record_series(series=rows, want_id=want_id)
            except CallFailed as refused:
                at = self._held_already(refused, rows)
                if at is None:
                    raise
                if at < 0:
                    for row in rows:
                        done.add(await self._record_series([row], want_id))
                    return done
                self._take_as_recorded(rows.pop(at))
                done.unchanged += 1
                continue
            done.add(answer)
            break
        return done

    @staticmethod
    def _held_already(refused: CallFailed, rows: Sequence[Any]) -> int | None:
        """Which row a refusal naming a series' valid time is about, where
        it is a series' own key: its index, -1 where the refusal names no
        row of several, or None where it is another refusal."""
        named = [f for f in refused.fields if f.endswith("valid_from_ns")]
        if refused.kind != "invalid" or not named:
            return None
        found = _ROW.search(named[0])
        if found is None and len(rows) > 1:
            return -1
        at = int(found.group(1)) if found is not None else 0
        if at >= len(rows) or rows[at].meta.row_key.endswith(":ADJ"):
            return None
        return at

    def _take_as_recorded(self, row: Any) -> None:
        dataset, osi = row.meta.source.dataset, row.meta.row_key
        if (dataset, osi) not in self._taken_as_recorded:
            self._taken_as_recorded.add((dataset, osi))
            log.warning(
                "%s's terms are held in %s under another first valid time; taken as recorded",
                osi,
                dataset,
            )

    async def _statistics(
        self, held: _Underlying, options: Sequence[ChainOption], want_id: str
    ) -> list[Any] | None:
        """Each series' open interest, dated the market day before today, and
        volume, dated today where it is a market day; None where the
        calendar did not answer."""
        from ...helpers import chains

        if self.market_days is None:
            return None
        today = self._today()
        before = await self.market_days.previous_open(today)
        is_open = await self.market_days.is_open(today)
        if before is None or is_open is None:
            return None
        dataset = self.dataset()
        rows: list[Any] = []
        for option in options:
            for kind, value, day in (
                ("open_interest", option.open_interest, before),
                ("volume", option.volume, today if is_open else None),
            ):
                if value is None or day is None:
                    continue
                stat = chains.statistic(
                    held.subject,
                    chains.osi_key(option.osi),
                    kind,
                    value,
                    day,
                    dataset=dataset,
                    raw=self._raw(option.raw_key),
                    day_clock=getattr(self.market_days, "day_clock", None),
                )
                assert stat.meta is not None
                if self.sent.changed(STATISTIC, dataset, stat.meta.row_key, value) or want_id:
                    rows.append(stat)
        held.stats_on = today
        return rows

    def _quote(self, held: _Underlying, option: ChainOption, want_id: str) -> Quote | None:
        """A series' best bid and offer under the underlying, keyed by the
        series; none where the source states no side, or nothing changed."""
        from ...helpers import chains

        if option.bid is None and option.ask is None:
            return None
        dataset = self.dataset()
        at = option.quoted_at_ns or self._now()
        said = (option.bid, option.ask, option.bid_size, option.ask_size)
        if not self.sent.changed(QUOTE, dataset, option.osi, said) and not want_id:
            return None
        return Quote(
            meta=chains.series_meta(
                held.subject,
                chains.osi_key(option.osi),
                row_key=f"{option.osi}:q:{at}",
                dataset=dataset,
                valid_from_ns=at,
                raw=self._raw(option.raw_key),
                source_times=[SourceTime(kind="event", at_ns=at)],
            ),
            bid=None if option.bid is None else Money(option.bid, self.currency),
            ask=None if option.ask is None else Money(option.ask, self.currency),
            bid_quantity=option.bid_size if option.bid is not None else None,
            ask_quantity=option.ask_size if option.ask is not None else None,
        )

    def _standing(self, want_id: str) -> bool:
        return not want_id or any(
            want_id in held.standing or want_id in held.trades
            for held in self.underlyings.values()
        )

    async def send(self, data_type: str, rows: Sequence[Any], want_id: str) -> None:
        """Rows in the lake's batches against the want, aged and judged at
        the edge where recorded unasked or for a standing want; counted."""
        if not rows:
            return
        if data_type in (QUOTE, TRADE) and self._standing(want_id):
            from .listings import at_the_edge

            rows = at_the_edge(
                self.latency, self.quality, self.in_force(), self.dataset(), list(rows)
            )
        for start in range(0, len(rows), BATCH):
            batch = list(rows[start : start + BATCH])
            done: Any
            if data_type == SERIES:
                # A copy: a row taken as recorded leaves it, and is kept too.
                done = await self._record_series(list(batch), want_id)
                self._first_times.commit(batch, self._today())
            elif data_type == STATISTIC:
                done = await self.record_statistics(statistics=batch, want_id=want_id)
            elif data_type == QUOTE:
                done = await self.record_quotes(quotes=batch, want_id=want_id)
            else:
                done = await self.record_trades(trades=batch, want_id=want_id)
            recorded = int(getattr(done, "recorded", 0))
            restated = int(getattr(done, "restated", 0))
            self.counts.recorded += recorded
            self.counts.restated += restated
            self.counts.unchanged += int(getattr(done, "unchanged", 0))
            self.counts.last_recorded_at_ns = self._now()
            if want_id:
                self.by_want.setdefault(want_id, [0, 0])[0] += recorded + restated

    async def alive(self) -> bool:
        """The chain's sign of life since the last (ruling 418): the
        dataset's liveness, recorded once a pass, which confirms every quote
        in force. A refusal is said, never raised."""
        if self.alive_ns <= self.liveness_ns:
            return False
        self.liveness_ns = self.alive_ns
        try:
            await self.record_liveness(
                liveness=[
                    ops.DatasetLiveness(
                        dataset=self.dataset(), venue_id="", alive_at_ns=self.alive_ns
                    )
                ]
            )
        except (MeridianError, ValueError) as refused:
            log.warning("the chain's liveness not recorded: %s", refused)
            return False
        return True

    # ── Kept current ─────────────────────────────────────────────────────

    async def refresh(self) -> int:
        """What is due within the minute's budget: each standing want's
        chain read again at the cadence, unread longest first, and its
        statistics once a day. How many chains were read."""
        now = self._now()
        today = self._today()
        due = sorted(
            (held.read_at_ns, held.subject)
            for held in self.underlyings.values()
            if held.standing
            and (now - held.read_at_ns >= self.cadence_ns or held.stats_on != today)
        )
        read = 0
        for _, subject in due:
            if self.budget() <= 0:
                break
            held = self.underlyings.get(subject)
            if held is None:
                continue
            found = await self.underlying(subject)
            if isinstance(found, str):
                continue
            for data_type, days, keys in list(held.standing.values()):
                if data_type == STATISTIC and held.stats_on == today:
                    continue
                await self.record(held, data_type, days, keys, "")
            read += 1
        await self.flush()
        return read

    async def run(self) -> None:
        """Keep standing wants current, and record streamed trades, until
        cancelled."""
        while True:
            await self.refresh()
            await asyncio.sleep(1.0)

    # ── Trades ───────────────────────────────────────────────────────────

    async def _trades_between(
        self, held: _Underlying, days: frozenset[dt.date], keys: frozenset[str], want: Any
    ) -> str:
        source: Any = self.source
        if not keys:
            return "not_covered"  # a range of trades names its series
        rows: list[Trade] = []
        for osi in sorted(keys):
            found = await self._fetch(lambda osi=osi: source.trades(osi, want.valid_from_ns))  # type: ignore[misc]
            if found is None:
                return "source_silent"
            until = want.valid_until_ns or self._now()
            for each in found:
                if want.valid_from_ns <= each.at_ns < until:
                    row = self.trade_row(held.subject, each)
                    if row is not None:
                        rows.append(row)
        await self.send(TRADE, rows, want.want_id)
        return ""

    def restream(self) -> set[str]:
        """Stream the series under the standing wants of trades, in the order
        wanted, as many as one session may; those past that."""
        ordered: list[str] = []
        if self._timeliness in ("", REAL_TIME):
            for held in self.underlyings.values():
                for osis in held.trades.values():
                    for osi in osis:
                        if osi not in ordered:
                            ordered.append(osi)
        accepted = ordered[: self.stream_limit]
        self.streamed = accepted
        self.past_limit = set(ordered) - set(accepted)
        if self.streamer is not None:
            self.streamer.want(accepted)
        return self.past_limit

    def trade_row(self, subject: str, stated: SourceTrade) -> Trade | None:
        """An option's trade under its underlying, keyed by its series; its
        venue the source's code, kept as reported."""
        from ...edge import as_reported
        from ...helpers import chains

        if stated.price is None or stated.quantity is None:
            self.counts.unconverted += len(stated.unconverted) or 1
            return None
        meta: ObservationMeta = chains.series_meta(
            subject,
            chains.osi_key(stated.osi),
            row_key=f"{stated.row_key}@{subject}",
            dataset=self.dataset(),
            valid_from_ns=stated.at_ns,
            raw=self._raw(stated.raw_key),
            source_times=[SourceTime(kind="event", at_ns=stated.at_ns)],
        )
        reported = (
            [as_reported(f"{self.source_name or 'source'}:venue", stated.venue_code)]
            if stated.venue_code
            else []
        )
        from dataclasses import replace

        meta = replace(meta, unconverted=[*reported, *stated.unconverted])
        return Trade(
            meta=meta,
            price=Money(stated.price, self.currency),
            quantity=stated.quantity,
            aggressor=stated.aggressor or None,
        )

    async def heard(self, stated: Sequence[Any]) -> None:
        """What the stream stated: each trade of a series streamed made a
        row, waiting to be recorded."""
        self.alive_ns = self._now()
        streamed = set(self.streamed)
        for each in stated:
            if not isinstance(each, SourceTrade) or each.osi not in streamed:
                continue
            for held in self.underlyings.values():
                if any(each.osi in osis for osis in held.trades.values()):
                    row = self.trade_row(held.subject, each)
                    if row is not None:
                        self.pending_trades.append(row)

    async def flush(self, force: bool = False) -> None:
        """Record the trades heard every half second or 500 at a time, none
        twice; and the dataset's liveness."""
        await self.alive()
        now = self._now()
        due = (
            force
            or len(self.pending_trades) >= BATCH
            or now - self._trades_at >= TRADE_EVERY_NS
        )
        if not self.pending_trades or not due:
            return
        rows, self.pending_trades = self.pending_trades, []
        self._trades_at = now
        fresh: list[Trade] = []
        for row in rows:
            assert row.meta is not None
            if row.meta.row_key in self.recent:
                self.counts.unchanged += 1
                continue
            self.recent[row.meta.row_key] = None
            fresh.append(row)
        while len(self.recent) > RECENT_TRADES:
            self.recent.popitem(last=False)
        await self.send(TRADE, fresh, "")
