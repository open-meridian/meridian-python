"""A data plugin for a broker's US equity listings, generic over the broker
(0.31.0; ruling 213: Alpaca's and Tradier's plugins kept this, their
lake.py, nearly byte for byte between them; it is the SDK's now, each plugin
keeping its broker's client, its conversion and its trade conditions).

    class Lake(listings.Feed):
        source_name = "alpaca"                    # a symbol's source
        history_from = dt.date(2016, 1, 1)        # the earliest daily history

        def attributes(self, stated):             # a trade's conditions, converted
            return conditions.trade_attributes(stated.codes, stated.tape)

    lake = Lake(plugin, source, listings.Listings(storage / "products.json"))
    await plugin.receive(observations_wanted=lake.on_want, want_withdrawn=lake.on_withdrawn)

Three datasets, apart (the lake plan's Q21 and Q40), each the plugin
declares in its catalogue:

- **daily**: each listing's close and daily bar for a business date, from
  the source's consolidated daily bars. Pulled: recorded when a reader's read
  is wanted (W10.7). Pushed: once a session's close is final, the day's
  closes of every listing it has served, unasked. A day still forming is
  recorded and restated under the same row key as it fills, until final.
- **live**: the latest trade's price (`last`) and the best bid and ask, as
  prices, and the best bid and offer as a quote, each side with its size.
  Pulled for a read; while a standing want stands, its prices kept current
  at the dataset's cadence and its quotes streamed, at most one a second
  per listing (the latest); nothing once it is withdrawn.
  From 0.32.3 any stream message heard is the dataset's liveness
  (`RecordLiveness`, its consolidated view), recorded once a pass by
  `flush`.
- **trades**: each trade with the platform's trade attributes, converted
  from what the broker states by the plugin (`attributes`), and no
  aggressor, which a broker's stock trades never state; a withdrawal or a
  correction the next version under the trade's row key. Streamed for the
  listings under any standing want, and only those, in batches of up to
  500. Where the source reads its trade history (`Source.trades`), also
  pulled for a range a reader wants, and after the stream reconnects, or the
  plugin restarts, the gap caught up from it, a trade already recorded never
  sent again; where it does not, a range is declined, not covered.

**Each row under its own record's key**: where the deployment holds two
records of one listing (one this source resolved, one a custodian's, not
yet merged), a row is recorded for each, its key naming the record it is
about beside what the source said (`SPY:1d:2026-10-08@LCL-...`). An
identical repeat carries the raw record it was first recorded with, so the
lake keeps it unchanged.

**Every subject is the deployment's own instrument** (W3.6): the plugin asks
the instrument store what the record is and takes the listing's symbol from
its identifiers -- the one this source reported, else another source's, in
this source's one spelling of a share class (`spelled`), reporting its own
beside it (W3.1); where that resolve is ambiguous it is reported as a miss
(W3.2). A subject whose record carries no symbol is declined, not covered,
and so is one whose symbol the source answered it cannot take
(`Source.invalid`), once for the date where the plugin settles declines
(`settles_declines`). Which symbol each subject is, is kept in the plugin's
storage (`Listings`), to rebuild from.

**Every venue is the venue master's** (W3.14): a price's exchange is
resolved by the code the source prints, as a `symbol` at this source; a
venue the deployment does not hold is reported (W3.15), and the row is
recorded with no venue and the code as reported beside it.

**What the plugin supplies**: a `Source` (its broker's client, blocking calls
run in a thread) answering daily bars, live prices and latest quotes, and
optionally its trade history; and, overriding `Feed`'s methods, what is its
broker's alone -- a trade's attributes from its conditions (`attributes`),
what a withdrawal of a trade not recorded here becomes
(`withdrawn_unrecorded`), a quote's characteristics
(`quote_characteristics`) and a trade's sequence number (`sequence_of`).
The values it reads its broker's answers into carry these fields, each
number a `Decimal` read from the broker's own text: a daily bar (symbol,
business_date, open, high, low, close, volume, vwap, trade_count, raw_key,
unconverted, row_key, complete), a live price (symbol, kind, amount, at_ns,
venue_code, raw_key, unconverted, row_key), a trade (symbol, at_ns,
venue_code, price, quantity, cancelled, raw_key, unconverted, row_key) and a
quote (symbol, at_ns, bid, ask, bid_size, ask_size, raw_key, unconverted,
row_key, and a venue_code where it names one).

What it recorded, declined and could not convert is counted here for the
Datasets page (`Feed.counts`).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import re
import time
from collections import OrderedDict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from ...errors import MeridianError, NotGranted
from ...operations import (
    Bar,
    Eligibility,
    Money,
    ObservationMeta,
    Price,
    Quote,
    SourceTime,
    Trade,
    TradeAttributes,
)
from ...plugin.v1 import operations_pb2 as ops
from ...plugin.v1.operations_pb2 import Identifier
from ...receive import Heard
from ._wants import backfill_restart

__all__ = [
    "BAR",
    "DAILY",
    "LIVE",
    "LIVE_CADENCE_SECONDS",
    "LIVE_KINDS",
    "NOT_KNOWN",
    "PRICE",
    "QUOTE",
    "TRADE",
    "TRADES",
    "Attributes",
    "Counts",
    "Feed",
    "Forming",
    "Listings",
    "Source",
    "Standing",
    "close_of",
    "new_york_date",
    "previous_close_of",
    "row_key",
    "spelled",
]

log = logging.getLogger("meridian.roles.data.listings")

NS = 1_000_000_000
NEW_YORK = ZoneInfo("America/New_York")
#: A US listing's session closes at 16:00 New York.
DAY_END_MINUTE = 16 * 60
#: A US listing's symbol in its one spelling: `BRK.B`.
SYMBOL = re.compile(r"[A-Z][A-Z0-9]{0,5}(?:\.[A-Z0-9]{1,4})?")

DAILY = "daily"
LIVE = "live"
TRADES = "trades"
PRICE = "meridian.v1.Price"
BAR = "meridian.v1.Bar"
TRADE = "meridian.v1.Trade"
QUOTE = "meridian.v1.Quote"
DAY_NS = 86_400 * NS
#: The most rows one batch carries (W10.4).
BATCH = 500
#: The live dataset's cadence: a standing want is kept current this often.
LIVE_CADENCE_SECONDS = 60
#: How long after a session's close its day is still read again for a
#: restatement: the extended session's end, and the source's delay, past it.
FINAL_AFTER_NS = (4 * 60 + 15) * 60 * NS
#: How often a day still forming is read again.
FORMING_EVERY_NS = 5 * 60 * NS
#: A venue the deployment did not hold is asked again after this long.
VENUE_MISS_NS = 3600 * NS
LIVE_KINDS = ("last", "bid", "ask")
#: Streamed trades wait at most this long before they are recorded.
TRADE_EVERY_NS = NS // 2
#: A listing's quote is recorded at most once a second: the latest.
QUOTE_EVERY_NS = NS
#: How many trades recorded are remembered, so none is sent twice.
RECENT_TRADES = 50_000
#: How many rows' last sending is remembered, for an identical repeat.
REMEMBERED_ROWS = 100_000
#: How many declines are remembered, each for the date it was for.
REMEMBERED_DECLINES = 100_000


def spelled(symbol: str) -> str | None:
    """The listing in its one spelling (`BRK.B`), from a symbol in any of the
    usual spellings (`BRK.B`, `BRK/B`, `BRK-B`, `brk.b`), or None where it
    is not a US listing's symbol."""
    candidate = symbol.strip().upper().replace("/", ".").replace("-", ".")
    return candidate if SYMBOL.fullmatch(candidate) else None


def new_york_date(at_ns: int) -> dt.date:
    """The New York calendar date a moment falls on."""
    return dt.datetime.fromtimestamp(at_ns / NS, NEW_YORK).date()


def close_of(day: dt.date) -> int:
    """The moment a business date's session closes: 16:00 New York."""
    moment = dt.datetime(day.year, day.month, day.day, tzinfo=NEW_YORK)
    return int(moment.timestamp()) * NS + DAY_END_MINUTE * 60 * NS


def previous_close_of(day: dt.date) -> int:
    """The previous calendar day's 16:00, where the business date begins."""
    return close_of(day - dt.timedelta(days=1))


@dataclass(frozen=True)
class Attributes:
    """A trade's attributes as the plugin converted them: each eligibility
    True, False, or None where what the broker said did not convert (not
    known)."""

    characteristics: tuple[str, ...]
    consolidated: tuple[bool | None, bool | None, bool | None, bool | None]
    market_centre: tuple[bool | None, bool | None, bool | None, bool | None]
    unconverted: tuple[ops.AsReported, ...] = ()


NOT_KNOWN: tuple[None, None, None, None] = (None, None, None, None)


class Source(Protocol):
    """The broker, as the feed asks it: blocking calls, run in a thread. It
    may also read its trade history, `trades(symbols, start_ns, end_ns)`,
    and say which symbols it answered it cannot take, never asked again
    (`invalid`); the feed asks either only where the source has it."""

    def daily(self, symbols: Sequence[str], first: dt.date, last: dt.date) -> list[Any]: ...

    def live(self, symbols: Sequence[str]) -> list[Any]: ...

    def quotes(self, symbols: Sequence[str]) -> list[Any]: ...


@dataclass
class Counts:
    """What one dataset did since the plugin started, for the Datasets page."""

    recorded: int = 0
    restated: int = 0
    unchanged: int = 0
    declined: int = 0
    unconverted: int = 0
    wants: int = 0
    withdrawn: int = 0
    caught_up: int = 0
    #: Withdrawals naming no trade recorded here, counted and not sent.
    unmatched: int = 0
    last_recorded_at_ns: int = 0
    last_declined: str = ""


@dataclass
class Standing:
    """A standing want, kept current until withdrawn: a live one's prices at
    the cadence, and every one's listings streamed."""

    want_id: str
    subjects: tuple[str, ...]
    kinds: tuple[str, ...]
    last_at_ns: int = 0
    dataset: str = LIVE
    data_type: str = PRICE


@dataclass(frozen=True)
class Forming:
    """A day recorded before its close was final, to be read again."""

    entity_id: str
    symbol: str
    day: dt.date
    data_type: str


class Listings:
    """Which listing each subject is: the deployment's instrument ID to this
    source's symbol, kept in the plugin's storage (decisions/028) so a new
    process rebuilds from it rather than asking again."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.symbols: dict[str, str] = {}
        if path is not None and path.exists():
            try:
                self.symbols = {str(k): str(v) for k, v in json.loads(path.read_text()).items()}
            except (OSError, ValueError):
                log.warning("the listing map in storage did not read; asking again")

    def put(self, entity_id: str, symbol: str) -> None:
        if self.symbols.get(entity_id) == symbol:
            return
        self.symbols[entity_id] = symbol
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            partial = self.path.with_suffix(".partial")
            partial.write_text(json.dumps(self.symbols, sort_keys=True, indent=1))
            partial.replace(self.path)


def _chunks(items: Sequence[Any], size: int = BATCH) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def row_key(stated: str, entity_id: str) -> str:
    """A row's key: what the source said, and the record it is about, so two
    records of one listing are never one row (ObservationMeta.row_key: at
    most 128 characters)."""
    return f"{stated}@{entity_id}"[:128]


def _eligibility(flags: Sequence[bool | None]) -> Eligibility:
    """Whether a trade may set each statistic: eligible, not eligible, or
    unset where a code did not convert (not known)."""

    def one(flag: bool | None) -> str | None:
        return None if flag is None else ("eligible" if flag else "not_eligible")

    high_low, opening, closing, volume = flags
    return Eligibility(
        high_low=one(high_low), open=one(opening), close=one(closing), volume=one(volume)
    )


def _kind_name(value: int) -> str:
    return str(ops.PriceKind.Name(value)).removeprefix("PRICE_KIND_").lower()


class Feed:
    """The plugin's half of the lake, on whatever operations it is given: the
    sidecar's (`meridian.Plugin`) or the suite's `Recorder`. A plugin
    subclasses it, naming its source and overriding what is its broker's."""

    #: The broker's code as a `symbol`'s source (`alpaca`).
    source_name: str = ""
    #: The earliest day the source's daily history reaches.
    history_from: dt.date = dt.date(2016, 1, 1)
    #: The currency every listing is priced in.
    currency: str = "USD"
    #: Whether a settled decline (the source does not have it) is sent once
    #: for the date it is for, never again each minute a standing want is
    #: kept current; False sends it each time.
    settles_declines: bool = True
    #: How far back a restart's gap is backfilled at most: the trades
    #: dataset's default retention, past which the lake keeps none.
    backfill_ns: int = 2 * DAY_NS

    def __init__(
        self,
        plugin: Any,
        source: Source | None,
        products: Listings | None = None,
        clock_ns: Callable[[], int] = time.time_ns,
    ) -> None:
        if not self.source_name:
            raise TypeError("a listings feed names its source (source_name)")
        self.plugin = plugin
        self.source = source
        self.products = products or Listings(None)

        self.clock_ns = clock_ns
        self.counts = {DAILY: Counts(), LIVE: Counts(), TRADES: Counts()}
        self.standing: dict[str, Standing] = {}
        #: What is streamed, and what one session may stream (None: no
        #: limit); the streamer that streams it, where there is one.
        self.streamed: list[str] = []
        self.past_limit: set[str] = set()
        self.stream_limit: int | None = None
        self.streamer: Any = None
        self.pending_trades: list[Trade] = []
        self.pending_quotes: dict[str, Any] = {}
        #: The stream's last message, and the liveness last recorded (0.32.3;
        #: contract v27, ruling 418): a message with no price changed still
        #: confirms the quotes in force, recorded for the live dataset once
        #: a pass.
        self.alive_ns = 0
        self.liveness_ns = 0
        self._trades_at = 0
        self._quotes_at = 0
        #: The trades recorded, by row key, latest last: none sent twice.
        self.recent: OrderedDict[str, Trade] = OrderedDict()
        #: Each row's last sending, by (data type, row key): its values
        #: without the raw record, and the raw record it carried.
        self._sent: OrderedDict[tuple[str, str, str], tuple[str, Any]] = OrderedDict()
        self.forming: dict[Forming, str] = {}
        self.pushed: dt.date | None = None
        self._venues: dict[str, tuple[str, int]] = {}
        self._forming_at = 0
        #: Each subject declined, by its dataset and the date it was declined
        #: for: a subject the source does not have (an unknown symbol, a
        #: record with none) is declined once for that date, never again each
        #: minute a standing want is kept current or delivered again; the
        #: lake's decline stands for the date asked (v19). Not a source that
        #: failed, or no key: those are asked again.
        self.declined: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        #: What each want was answered with since start: recorded, declined.
        self.by_want: dict[str, list[int]] = {}
        #: The subjects whose restart gap this process has backfilled.
        self.backfilled: set[str] = set()
        #: Whether the deployment answers this plugin's ResolveInstrument.
        self.reads_instruments = True
        self.last_error = ""
        #: Whether the source streams now: one that does not (a broker's
        #: sandbox) streams none and declines none, its live prices kept
        #: current at the cadence.
        self.streaming = True

    # ── What is the broker's: override in the plugin ─────────────────────

    def attributes(self, stated: Any) -> Attributes:
        """A trade's attributes from what the broker states of it (its
        conditions, its session): the plugin's conversion. Not known by
        default."""
        return Attributes((), NOT_KNOWN, NOT_KNOWN)

    def withdrawn_unrecorded(self, stated: Any) -> Attributes | None:
        """A withdrawal of a trade not recorded here: by default sent with
        what it could set not known, since its conditions are not stated
        again; None counts it unmatched and sends nothing, for a broker that
        names the trade by no more than a sequence number."""
        return Attributes((), NOT_KNOWN, NOT_KNOWN)

    def quote_characteristics(
        self, stated: Any
    ) -> tuple[tuple[str, ...], tuple[ops.AsReported, ...]]:
        """A quote's characteristics, and what did not convert: none by
        default."""
        return (), ()

    def sequence_of(self, stated: Any) -> int | None:
        """The broker's sequence number for a trade, where it gives one."""
        return None

    @property
    def reads_history(self) -> bool:
        """Whether the source reads its trade history."""
        return self.source is not None and callable(getattr(self.source, "trades", None))

    # ── Names ────────────────────────────────────────────────────────────

    def dataset(self, key: str) -> str:
        """A dataset's ID in the deployment: the instance, a colon, its key."""
        return f"{self.plugin.identity.instance_id}:{key}"

    def _key_of(self, dataset: str) -> str:
        return dataset.rpartition(":")[2]

    def streamed_subjects(self, symbol: str) -> list[str]:
        """The records under a standing want that a streamed listing is: a
        streamed row is recorded for each."""
        out: list[str] = []
        for standing in self.standing.values():
            for subject in standing.subjects:
                if self.products.symbols.get(subject) == symbol and subject not in out:
                    out.append(subject)
        return out

    # ── Subjects and venues (W3.6, W3.1, W3.2, W3.14, W3.15) ─────────────

    async def symbol_of(self, entity_id: str) -> str | None:
        """The listing a subject is, in this source's spelling; None where
        its record carries no symbol, or is no record the deployment holds."""
        known = self.products.symbols.get(entity_id)
        if known:
            return known
        if not self.reads_instruments:
            return None
        try:
            found = await self.plugin.resolve_instrument(
                instrument_id=entity_id, as_of_ns=self.clock_ns()
            )
        except NotGranted:
            # A runtime from before the ruling of 2026-10-10 grants a data plugin no
            # read of what an instrument is (W3.6): a subject it did not
            # resolve itself is not one it can name to its source. Asked
            # once, and said on the Datasets page.
            log.warning("this data plugin may not read an instrument's record; serving its own")
            self.reads_instruments = False
            return None
        if not found.found:
            return None
        record = found.instrument
        if record.currency and record.currency != self.currency:
            return None
        symbols = [i for i in record.identifiers if i.scheme == "symbol"]
        own = next(
            (i for i in symbols if i.source == self.source_name and spelled(i.value)), None
        )
        if own is not None:
            symbol = spelled(own.value) or own.value
        else:
            other = next((i for i in symbols if spelled(i.value)), None)
            if other is None:
                return None
            symbol = spelled(other.value) or other.value
            await self._join(entity_id, symbol, other)
        self.products.put(entity_id, symbol)
        return symbol

    async def _join(self, entity_id: str, symbol: str, other: ops.Identifier) -> None:
        """Report this source's symbol beside the one another source gave the
        record (W3.1): one identifier in common is one security, so the
        record gains this source's code. Ambiguous is a miss (W3.2)."""
        own = Identifier(scheme="symbol", value=symbol, source=self.source_name)
        given = Identifier(scheme=other.scheme, value=other.value, source=other.source)
        now = self.clock_ns()
        found = await self.plugin.resolve_identifier(
            identifiers=[own, given], as_of_ns=now, stated_currency=self.currency
        )
        if found.found and found.instrument_id == entity_id:
            return
        reason = found.miss_reason or ops.MISS_REASON_AMBIGUOUS
        if found.found:
            # Matched another record: two records for one listing, which a
            # person merges (W3.13).
            reason = ops.MISS_REASON_AMBIGUOUS
        await self.plugin.report_missing_instrument(
            source=self.source_name, identifiers=[own, given], as_of_ns=now, reason=reason
        )

    async def seed(self, symbols: Iterable[str]) -> None:
        """Resolve listings by this source's own symbol (W3.1), so the lake's
        wants for them can be answered: the deployment's record of each,
        found or minted, kept in the product map. What does not resolve is
        reported (W3.2)."""
        now = self.clock_ns()
        for symbol in symbols:
            if symbol in self.products.symbols.values():
                continue
            own = Identifier(scheme="symbol", value=symbol, source=self.source_name)
            found = await self.plugin.resolve_identifier(
                identifiers=[own], as_of_ns=now, stated_currency=self.currency
            )
            if found.instrument_id:
                self.products.put(found.instrument_id, symbol)
                continue
            await self.plugin.report_missing_instrument(
                source=self.source_name,
                identifiers=[own],
                as_of_ns=now,
                reason=found.miss_reason or ops.MISS_REASON_NOT_FOUND,
            )

    async def venue_of(self, code: str) -> tuple[str, list[ops.AsReported]]:
        """The venue master's ID for an exchange the source printed, and what
        to keep as reported where the deployment does not hold it."""
        if not code:
            return "", []
        now = self.clock_ns()
        held = self._venues.get(code)
        if held is not None and (held[0] or now - held[1] < VENUE_MISS_NS):
            return held[0], [] if held[0] else [self._venue_reported(code)]
        identifier = Identifier(scheme="symbol", value=code, source=self.source_name)
        found = await self.plugin.resolve_venue(identifiers=[identifier], as_of_ns=now)
        if found.found and found.venue.venue_id:
            self._venues[code] = (found.venue.venue_id, now)
            return found.venue.venue_id, []
        await self.plugin.report_missing_venue(
            source=self.source_name,
            identifiers=[identifier],
            as_of_ns=now,
            reason=found.miss_reason or ops.MISS_REASON_NOT_FOUND,
        )
        self._venues[code] = ("", now)
        return "", [self._venue_reported(code)]

    def _venue_reported(self, code: str) -> ops.AsReported:
        from ...edge import as_reported

        return as_reported(f"{self.source_name}:venue", code)

    # ── Rows ─────────────────────────────────────────────────────────────

    def _daily_meta(self, entity_id: str, bar: Any, final: bool) -> ObservationMeta:
        day = bar.business_date
        return ObservationMeta(
            row_key=row_key(bar.row_key, entity_id),
            subjects=[ops.SubjectRef(entity_id=entity_id)],
            source=ops.Source(dataset=self.dataset(DAILY)),
            valid_from_ns=previous_close_of(day),
            valid_until_ns=close_of(day),
            business_date=day,
            source_times=[SourceTime(kind="published", at_ns=close_of(day))] if final else [],
            raw=self.plugin.raw_record(bar.raw_key[:256]),
        )

    def final(self, day: dt.date) -> bool:
        """Whether a business date's close is final: its session has closed."""
        return self.clock_ns() >= close_of(day)

    def close(self, entity_id: str, bar: Any) -> Price | None:
        if bar.close is None:
            return None
        return Price(
            meta=self._daily_meta(entity_id, bar, self.final(bar.business_date)),
            kind="close",
            price=Money(bar.close, self.currency),
            basis="per_unit",
        )

    def bar(self, entity_id: str, bar: Any) -> Bar | None:
        if not bar.complete or bar.volume is None:
            return None
        assert bar.open is not None and bar.high is not None and bar.low is not None
        assert bar.close is not None
        return Bar(
            meta=self._daily_meta(entity_id, bar, self.final(bar.business_date)),
            open=Money(bar.open, self.currency),
            high=Money(bar.high, self.currency),
            low=Money(bar.low, self.currency),
            close=Money(bar.close, self.currency),
            volume=bar.volume,
            vwap=None if bar.vwap is None else Money(bar.vwap, self.currency),
            trade_count=bar.trade_count,
        )

    async def live_price(self, entity_id: str, quoted: Any) -> Price | None:
        if quoted.amount is None:
            return None
        venue, reported = await self.venue_of(quoted.venue_code)
        return Price(
            meta=ObservationMeta(
                row_key=row_key(quoted.row_key, entity_id),
                subjects=[ops.SubjectRef(entity_id=entity_id)],
                source=ops.Source(dataset=self.dataset(LIVE), venue_id=venue),
                valid_from_ns=quoted.at_ns,
                source_times=[SourceTime(kind="event", at_ns=quoted.at_ns)],
                raw=self.plugin.raw_record(quoted.raw_key[:256]),
                unconverted=reported,
            ),
            kind=quoted.kind,
            price=Money(quoted.amount, self.currency),
            basis="per_unit",
        )

    def _as_sent_before(self, data_type: str, row: Any) -> Any:
        """The row, carrying the raw record it was last sent with where its
        values are those it was sent with: an identical repeat, which the
        lake keeps unchanged rather than taking a new raw record for a
        restatement."""
        assert row.meta is not None
        key = (data_type, row.meta.source.dataset, row.meta.row_key)
        said = repr(replace(row, meta=replace(row.meta, raw=None)))
        held = self._sent.get(key)
        if held is not None and held[0] == said:
            row = replace(row, meta=replace(row.meta, raw=held[1]))
        self._sent[key] = (said, row.meta.raw)
        self._sent.move_to_end(key)
        while len(self._sent) > REMEMBERED_ROWS:
            self._sent.popitem(last=False)
        return row

    async def _record(
        self, key: str, data_type: str, rows: Sequence[Any], want_id: str
    ) -> None:
        counts = self.counts[key]
        rows = [self._as_sent_before(data_type, row) for row in rows]
        for batch in _chunks(rows):
            if data_type == BAR:
                done = await self.plugin.record_bars(bars=list(batch), want_id=want_id)
            elif data_type == TRADE:
                done = await self.plugin.record_trades(trades=list(batch), want_id=want_id)
            elif data_type == QUOTE:
                done = await self.plugin.record_quotes(quotes=list(batch), want_id=want_id)
            else:
                done = await self.plugin.record_prices(prices=list(batch), want_id=want_id)
            counts.recorded += done.recorded
            if want_id:
                self.by_want.setdefault(want_id, [0, 0])[0] += done.recorded + done.restated
            counts.restated += done.restated
            counts.unchanged += done.unchanged
            counts.last_recorded_at_ns = self.clock_ns()

    def today(self) -> str:
        """Today's New York date, which a live want's decline is for."""
        return new_york_date(self.clock_ns()).isoformat()

    def settled(self, key: str, subjects: Sequence[str], day: str = "") -> list[str]:
        """The subjects not yet declined for `day` (today, by default): those
        worth asking the source for."""
        if not self.settles_declines:
            return list(subjects)
        day = day or self.today()
        return [s for s in subjects if (key, s, day) not in self.declined]

    async def _decline(
        self,
        key: str,
        want_id: str,
        subjects: Sequence[str],
        reason: str,
        *,
        day: str = "",
        settled: bool = True,
    ) -> None:
        """Decline `subjects` of a want, with a reason. A settled decline (the
        source does not have it, or may not serve it) is sent once for the
        date it is for -- today, or the dates a daily want named -- and a
        subject already declined for it is left out; an unsettled one (the
        source failed, no key yet) is sent each time."""
        if not subjects or not want_id:
            return
        if settled and self.settles_declines:
            day = day or self.today()
            subjects = self.settled(key, subjects, day)
            for subject in subjects:
                self.declined[(key, subject, day)] = reason
                self.declined.move_to_end((key, subject, day))
            while len(self.declined) > REMEMBERED_DECLINES:
                self.declined.popitem(last=False)
            if not subjects:
                return
        counts = self.counts[key]
        for batch in _chunks(list(subjects)):
            await self.plugin.decline_want(
                want_id=want_id,
                subjects=[ops.SubjectRef(entity_id=s) for s in batch],
                reason=reason,
            )
        counts.declined += len(subjects)
        counts.last_declined = reason
        self.by_want.setdefault(want_id, [0, 0])[1] += len(subjects)

    def _not_covered(self, symbols: dict[str, str]) -> list[str]:
        """The subjects whose symbol the source answered it cannot take,
        taken out of `symbols`: declined as not covered, settled."""
        invalid = getattr(self.source, "invalid", ()) if self.source is not None else ()
        refused = [subject for subject, symbol in symbols.items() if symbol in invalid]
        for subject in refused:
            del symbols[subject]
        return refused

    async def _fetch(self, call: Callable[[], Any]) -> Any:
        """A blocking call to the source, in a thread; None where it failed,
        which is said on the Connection page."""
        try:
            answer = await asyncio.to_thread(call)
        except Exception as failed:  # noqa: BLE001 - the source's failure, shown
            self.last_error = f"{type(failed).__name__}: {failed}"[:300]
            log.warning("the source failed: %s", self.last_error)
            return None
        self.last_error = ""
        return answer

    # ── Daily ────────────────────────────────────────────────────────────

    def _days_wanted(self, want: ops.ObservationsWantedEvent) -> tuple[dt.date, dt.date, bool]:
        """The New York dates a want covers, and whether it asks the latest."""
        if want.business_date:
            day = dt.date.fromisoformat(want.business_date)
            return day, day, False
        if want.valid_from_ns or want.valid_until_ns:
            first = new_york_date(want.valid_from_ns or self.clock_ns())
            last = new_york_date((want.valid_until_ns or self.clock_ns()) - 1)
            return first, max(first, last), False
        today = new_york_date(self.clock_ns())
        return today - dt.timedelta(days=7), today, True

    async def daily(
        self,
        subjects: Sequence[str],
        first: dt.date,
        last: dt.date,
        *,
        data_type: str = PRICE,
        want_id: str = "",
        latest: bool = False,
    ) -> list[str]:
        """Record the closes (or daily bars) of `subjects` over New York dates
        `first` to `last`; the subjects the source had nothing for."""
        counts = self.counts[DAILY]
        span = first.isoformat() if first == last else f"{first}..{last}"
        if want_id:
            subjects = self.settled(DAILY, subjects, span)
        symbols: dict[str, str] = {}
        uncovered: list[str] = []
        for subject in subjects:
            symbol = await self.symbol_of(subject)
            if symbol is None:
                uncovered.append(subject)
            else:
                symbols[subject] = symbol
        await self._decline(DAILY, want_id, uncovered, "not_covered", day=span)
        today = new_york_date(self.clock_ns())
        if last < self.history_from or first > today:
            reason = "beyond_history" if last < self.history_from else "source_silent"
            await self._decline(DAILY, want_id, list(symbols), reason, day=span)
            return list(symbols)
        if not symbols or self.source is None:
            await self._decline(DAILY, want_id, list(symbols), "source_silent", settled=False)
            return list(symbols)
        source = self.source
        wanted = sorted(set(symbols.values()))
        bars = await self._fetch(
            lambda: source.daily(wanted, max(first, self.history_from), last)
        )
        if bars is None:
            await self._decline(DAILY, want_id, list(symbols), "source_silent", settled=False)
            return list(symbols)
        refused = self._not_covered(symbols)
        await self._decline(DAILY, want_id, refused, "not_covered", day=span)
        by_symbol: dict[str, list[Any]] = {}
        for bar in bars:
            counts.unconverted += len(bar.unconverted)
            if first <= bar.business_date <= last:
                by_symbol.setdefault(bar.symbol, []).append(bar)
        rows: list[Any] = []
        silent: list[str] = []
        for subject, symbol in symbols.items():
            days = by_symbol.get(symbol, [])
            if latest and days:
                days = [max(days, key=lambda b: b.business_date)]
            made = [
                row
                for row in (
                    self.bar(subject, b) if data_type == BAR else self.close(subject, b)
                    for b in days
                )
                if row is not None
            ]
            if not made:
                silent.append(subject)
                continue
            rows.extend(made)
            for b in days:
                forming = Forming(subject, symbol, b.business_date, data_type)
                if self.clock_ns() < close_of(b.business_date) + FINAL_AFTER_NS:
                    self.forming[forming] = want_id
                else:
                    self.forming.pop(forming, None)
        if rows:
            await self._record(DAILY, data_type, rows, want_id)
        await self._decline(DAILY, want_id, silent, "source_silent", day=span)
        return refused + silent

    # ── Live ─────────────────────────────────────────────────────────────

    async def live(
        self, subjects: Sequence[str], kinds: Sequence[str] = LIVE_KINDS, want_id: str = ""
    ) -> list[str]:
        """Record the latest live prices of `subjects`; those the source had
        nothing for. A subject declined today is not asked again today."""
        subjects = self.settled(LIVE, subjects)
        if not subjects:
            return []
        symbols: dict[str, str] = {}
        uncovered: list[str] = []
        for subject in subjects:
            symbol = await self.symbol_of(subject)
            if symbol is None:
                uncovered.append(subject)
            else:
                symbols[subject] = symbol
        await self._decline(LIVE, want_id, uncovered, "not_covered")
        if not symbols or self.source is None:
            await self._decline(LIVE, want_id, list(symbols), "source_silent", settled=False)
            return list(symbols)
        source = self.source
        wanted = sorted(set(symbols.values()))
        quoted = await self._fetch(lambda: source.live(wanted))
        if quoted is None:
            await self._decline(LIVE, want_id, list(symbols), "source_silent", settled=False)
            return list(symbols)
        refused = self._not_covered(symbols)
        await self._decline(LIVE, want_id, refused, "not_covered")
        counts = self.counts[LIVE]
        by_symbol: dict[str, list[Any]] = {}
        for each in quoted:
            counts.unconverted += len(each.unconverted)
            if each.kind in kinds:
                by_symbol.setdefault(each.symbol, []).append(each)
        rows: list[Price] = []
        silent: list[str] = []
        for subject, symbol in symbols.items():
            made = [await self.live_price(subject, q) for q in by_symbol.get(symbol, [])]
            kept = [row for row in made if row is not None]
            if not kept:
                silent.append(subject)
                continue
            rows.extend(kept)
        if rows:
            await self._record(LIVE, PRICE, rows, want_id)
        await self._decline(LIVE, want_id, silent, "source_silent")
        return refused + silent

    # ── Wants (W10.7) ────────────────────────────────────────────────────

    async def on_want(self, heard: Heard[ops.ObservationsWantedEvent]) -> None:
        """Record what a want asks, against it, or decline it per subject."""
        want = heard.message
        key = self._key_of(want.dataset)
        subjects = [s.entity_id for s in want.subjects]
        if key not in self.counts:
            log.warning("a want for a dataset this plugin does not declare: %s", want.dataset)
            return
        self.counts[key].wants += 1
        kinds = [_kind_name(k) for k in want.kinds]
        if key == DAILY:
            ok_type = want.data_type in (PRICE, BAR)
            ok_kind = want.data_type == BAR or not kinds or "close" in kinds
            ok_interval = want.data_type != BAR or want.interval_ns in (0, DAY_NS)
            if not (ok_type and ok_kind and ok_interval):
                await self._decline(DAILY, want.want_id, subjects, "not_covered", settled=False)
                return
            first, last, latest = self._days_wanted(want)
            await self.daily(
                subjects,
                first,
                last,
                data_type=want.data_type,
                want_id=want.want_id,
                latest=latest,
            )
            return
        if key == TRADES:
            if want.data_type != TRADE:
                await self._decline(
                    TRADES, want.want_id, subjects, "not_covered", settled=False
                )
                return
            if want.standing:
                await self.stand(want, subjects)
                return
            if not self.reads_history:
                # Streamed only: a range is not this source's to answer.
                await self._decline(
                    TRADES, want.want_id, subjects, "not_covered", settled=False
                )
                return
            await self.trades_between(
                subjects, want.valid_from_ns, want.valid_until_ns, want.want_id
            )
            return
        if want.data_type == QUOTE:
            await self.quotes_now(subjects, want.want_id)
            if want.standing:
                await self.stand(want, subjects)
            return
        live_kinds = tuple(k for k in (kinds or LIVE_KINDS) if k in LIVE_KINDS)
        if want.data_type != PRICE or not live_kinds:
            await self._decline(LIVE, want.want_id, subjects, "not_covered", settled=False)
            return
        await self.live(subjects, live_kinds, want.want_id)
        if want.standing:
            await self.stand(want, subjects, live_kinds)

    async def on_withdrawn(self, heard: Heard[ops.WantWithdrawnEvent]) -> None:
        """A standing want nobody read within the cadence: no longer kept
        current, and its listings no longer streamed for it."""
        self.standing.pop(heard.message.want_id, None)
        for forming, want_id in list(self.forming.items()):
            if want_id == heard.message.want_id:
                self.forming.pop(forming, None)
        self.restream()

    # ── Streaming (contract v19) ─────────────────────────────────────────

    async def stand(
        self,
        want: ops.ObservationsWantedEvent,
        subjects: Sequence[str],
        kinds: Sequence[str] = (),
    ) -> None:
        """Keep a standing want: its listings streamed from now on, those
        past what one session may stream declined, not entitled."""
        key = self._key_of(want.dataset)
        covered: list[str] = []
        uncovered: list[str] = []
        for subject in subjects:
            (covered if await self.symbol_of(subject) else uncovered).append(subject)
        if key == TRADES:
            await self._decline(TRADES, want.want_id, uncovered, "not_covered")
            await self.backfill(covered)
        self.standing[want.want_id] = Standing(
            want.want_id,
            tuple(covered if key == TRADES else subjects),
            tuple(kinds),
            self.clock_ns(),
            dataset=key,
            data_type=want.data_type,
        )
        past = self.restream()
        over = [s for s in covered if self.products.symbols.get(s) in past]
        # Past what one session may stream: settled for today's stream
        # alone, so the same subject's prices are still asked.
        await self._decline(
            key, want.want_id, over, "not_entitled", day=f"{self.today()}:stream"
        )

    async def backfill(self, subjects: Sequence[str]) -> int:
        """A restart's gap (contract v20, W10.6), before the stream resumes:
        for each subject streamed that this process has not backfilled, the
        last trade this instance recorded of it, read from the lake, and the
        trades the source's history states since, recorded (a trade recorded
        again is answered unchanged by its row key). The gap is read back
        `backfill_ns` at most, the trades dataset's default retention. How
        many trades were sent."""
        fresh = [s for s in subjects if s not in self.backfilled]
        if not fresh or not self.reads_history:
            return 0
        self.backfilled.update(fresh)
        try:
            sent = await backfill_restart(self.plugin, fresh, self._history)
        except MeridianError as failed:
            self.last_error = f"the restart's gap was not backfilled: {failed}"[:300]
            log.warning("%s", self.last_error)
            return 0
        self.counts[TRADES].caught_up += sent
        return sent

    async def _history(self, last: ops.Trade) -> list[Trade]:
        """The trades the source states of `last`'s subject since it, as rows."""
        subject = last.meta.subjects[0].entity_id if last.meta.subjects else ""
        symbol = self.products.symbols.get(subject)
        if not symbol or self.source is None:
            return []
        since, now = last.meta.valid_from_ns, self.clock_ns()
        source: Any = self.source
        found = await self._fetch(
            lambda: source.trades([symbol], max(since, now - self.backfill_ns), now)
        )
        rows: list[Trade] = []
        for stated in found or []:
            if stated.symbol == symbol and stated.at_ns >= since:
                row = await self.trade_row(stated, subject)
                if row is not None:
                    rows.append(row)
        return rows

    def restream(self) -> set[str]:
        """Stream the listings under the standing wants, in the order they
        were wanted, as many as one session may; the listings past that."""
        ordered: list[str] = []
        for standing in self.standing.values() if self.streaming else ():
            for subject in standing.subjects:
                symbol = self.products.symbols.get(subject)
                if symbol and symbol not in ordered:
                    ordered.append(symbol)
        limit = self.stream_limit
        accepted = ordered if limit is None else ordered[:limit]
        self.streamed = accepted
        self.past_limit = set(ordered) - set(accepted)
        if self.streamer is not None:
            self.streamer.want(accepted)
        return self.past_limit

    async def heard(self, stated: Sequence[Any]) -> None:
        """What the stream stated: each trade of a listing streamed made a
        row, waiting to be recorded; each quote kept, the latest a listing's.
        Any message heard is the stream's sign of life (`alive_ns`), recorded
        by the next `flush`."""
        self.alive_ns = self.clock_ns()
        streamed = set(self.streamed)
        for each in stated:
            if each.symbol not in streamed:
                continue
            if hasattr(each, "bid"):
                self.pending_quotes[each.symbol] = each
                continue
            for subject in self.streamed_subjects(each.symbol):
                row = await self.trade_row(each, subject)
                if row is not None:
                    self.pending_trades.append(row)

    async def flush(self, force: bool = False) -> None:
        """Record what the stream stated, when it is due: trades every half
        second or 500 at a time, quotes once a second; and, where a message
        was heard since the last, the live dataset's liveness (`alive`)."""
        await self.alive()
        now = self.clock_ns()
        due = (
            force
            or len(self.pending_trades) >= BATCH
            or now - self._trades_at >= TRADE_EVERY_NS
        )
        if self.pending_trades and due:
            rows, self.pending_trades = self.pending_trades, []
            self._trades_at = now
            await self._record_trades(rows, "")
        if self.pending_quotes and (force or now - self._quotes_at >= QUOTE_EVERY_NS):
            quotes, self.pending_quotes = list(self.pending_quotes.values()), {}
            self._quotes_at = now
            made = [
                row
                for q in quotes
                for subject in self.streamed_subjects(q.symbol)
                if (row := await self.quote_row(q, subject)) is not None
            ]
            if made:
                await self._record(LIVE, QUOTE, made, "")

    async def alive(self) -> bool:
        """The stream's sign of life since the last (0.32.3; contract v27,
        ruling 418): the live dataset's liveness, recorded once a pass for
        its consolidated view (no venue), which confirms every quote in
        force. Whether it was recorded; a refusal is said, never raised."""
        if self.alive_ns <= self.liveness_ns:
            return False
        self.liveness_ns = self.alive_ns
        try:
            await self.plugin.record_liveness(
                liveness=[
                    ops.DatasetLiveness(
                        dataset=self.dataset(LIVE), venue_id="", alive_at_ns=self.alive_ns
                    )
                ]
            )
        except (MeridianError, ValueError) as refused:
            log.warning("the stream's liveness not recorded: %s", refused)
            return False
        return True

    async def caught_up(self, since: dict[str, int]) -> int:
        """After the stream reconnected: the trades since the last heard of
        each listing streamed, from the source's trade history; those already
        recorded are not sent again. How many were recorded."""
        symbols = sorted(s for s in since if s in set(self.streamed))
        if not symbols or not self.reads_history:
            return 0
        source: Any = self.source
        start, end = min(since[s] for s in symbols), self.clock_ns()
        found = await self._fetch(lambda: source.trades(symbols, start, end))
        if not found:
            return 0
        rows = [
            row
            for t in found
            if t.at_ns >= since[t.symbol]
            for subject in self.streamed_subjects(t.symbol)
            if (row := await self.trade_row(t, subject)) is not None
        ]
        before = self.counts[TRADES].recorded
        await self._record_trades(rows, "")
        caught = self.counts[TRADES].recorded - before
        self.counts[TRADES].caught_up += caught
        return caught

    async def trades_between(
        self, subjects: Sequence[str], from_ns: int, until_ns: int, want_id: str = ""
    ) -> list[str]:
        """Record the trades of `subjects` over a range a reader wants, from
        the source's trade history; the subjects it had nothing for."""
        symbols: dict[str, str] = {}
        uncovered: list[str] = []
        for subject in subjects:
            symbol = await self.symbol_of(subject)
            if symbol is None:
                uncovered.append(subject)
            else:
                symbols[subject] = symbol
        await self._decline(TRADES, want_id, uncovered, "not_covered")
        now = self.clock_ns()
        if not symbols or self.source is None or not from_ns or from_ns >= now:
            await self._decline(TRADES, want_id, list(symbols), "source_silent", settled=False)
            return list(symbols)
        history: Any = self.source
        wanted = sorted(set(symbols.values()))
        end = min(until_ns or now, now)
        found = await self._fetch(lambda: history.trades(wanted, from_ns, end))
        if found is None:
            await self._decline(TRADES, want_id, list(symbols), "source_silent", settled=False)
            return list(symbols)
        refused = self._not_covered(symbols)
        await self._decline(TRADES, want_id, refused, "not_covered")
        rows = [
            row
            for t in found
            for subject, symbol in symbols.items()
            if symbol == t.symbol and (row := await self.trade_row(t, subject)) is not None
        ]
        held = {t.symbol for t in found}
        silent = [s for s, symbol in symbols.items() if symbol not in held]
        if rows:
            await self._record_trades(rows, want_id)
        await self._decline(TRADES, want_id, silent, "source_silent")
        return refused + silent

    async def quotes_now(self, subjects: Sequence[str], want_id: str = "") -> list[str]:
        """Record the latest quote of `subjects`, from the source's latest quotes;
        the subjects it had nothing for. A subject declined today is not
        asked again today."""
        subjects = self.settled(LIVE, subjects)
        if not subjects:
            return []
        symbols: dict[str, str] = {}
        uncovered: list[str] = []
        for subject in subjects:
            symbol = await self.symbol_of(subject)
            if symbol is None:
                uncovered.append(subject)
            else:
                symbols[subject] = symbol
        await self._decline(LIVE, want_id, uncovered, "not_covered")
        if not symbols or self.source is None:
            await self._decline(LIVE, want_id, list(symbols), "source_silent", settled=False)
            return list(symbols)
        source, wanted = self.source, sorted(set(symbols.values()))
        found = await self._fetch(lambda: source.quotes(wanted))
        if found is None:
            await self._decline(LIVE, want_id, list(symbols), "source_silent", settled=False)
            return list(symbols)
        refused = self._not_covered(symbols)
        await self._decline(LIVE, want_id, refused, "not_covered")
        rows = [
            row
            for q in found
            for subject, symbol in symbols.items()
            if symbol == q.symbol and (row := await self.quote_row(q, subject)) is not None
        ]
        held = {q.symbol for q in found}
        silent = [s for s, symbol in symbols.items() if symbol not in held]
        if rows:
            await self._record(LIVE, QUOTE, rows, want_id)
        await self._decline(LIVE, want_id, silent, "source_silent")
        return refused + silent

    async def trade_row(self, stated: Any, subject: str) -> Trade | None:
        """A trade as recorded for one record of its listing: the venue it printed
        on, its price and size, its attributes from its conditions, and no
        aggressor, which a broker's stock trades never state. A withdrawal of a
        trade recorded is that trade again, withdrawn."""
        counts = self.counts[TRADES]
        key = row_key(stated.row_key, subject)
        if stated.cancelled:
            pending = [t for t in self.pending_trades if t.meta and t.meta.row_key == key]
            held = pending[-1] if pending else self.recent.get(key)
            if held is not None and held.meta is not None and not held.cancelled:
                raw = self.plugin.raw_record(stated.raw_key[:256])
                return replace(held, cancelled=True, meta=replace(held.meta, raw=raw))
        if stated.price is None or stated.quantity is None:
            counts.unconverted += len(stated.unconverted) or 1
            return None
        if stated.cancelled:
            # A withdrawal of a trade not recorded here.
            unrecorded = self.withdrawn_unrecorded(stated)
            if unrecorded is None:
                counts.unmatched += 1
                return None
            said = unrecorded
        else:
            said = self.attributes(stated)
        venue, reported = await self.venue_of(stated.venue_code)
        counts.unconverted += len(said.unconverted)
        return Trade(
            meta=ObservationMeta(
                row_key=key,
                subjects=[ops.SubjectRef(entity_id=subject)],
                source=ops.Source(dataset=self.dataset(TRADES), venue_id=venue),
                valid_from_ns=stated.at_ns,
                source_times=[SourceTime(kind="event", at_ns=stated.at_ns)],
                raw=self.plugin.raw_record(stated.raw_key[:256]),
                unconverted=[*reported, *said.unconverted, *stated.unconverted],
            ),
            price=Money(stated.price, self.currency),
            quantity=stated.quantity,
            attributes=TradeAttributes(
                consolidated=_eligibility(said.consolidated),
                market_centre=_eligibility(said.market_centre),
                characteristics=list(said.characteristics),
            ),
            cancelled=stated.cancelled,
            source_sequence=self.sequence_of(stated) or 0,
        )

    async def quote_row(self, stated: Any, subject: str) -> Quote | None:
        """A quote as recorded for one record of its listing: the venue it names, if
        any (a consolidated best names none), each side unset where it is
        empty, its sizes in shares."""
        if stated.bid is None and stated.ask is None:
            if stated.unconverted:
                self.counts[LIVE].unconverted += len(stated.unconverted)
            return None
        venue, reported = await self.venue_of(getattr(stated, "venue_code", ""))
        characteristics, unread = self.quote_characteristics(stated)
        self.counts[LIVE].unconverted += len(stated.unconverted)
        return Quote(
            meta=ObservationMeta(
                row_key=row_key(stated.row_key, subject),
                subjects=[ops.SubjectRef(entity_id=subject)],
                source=ops.Source(dataset=self.dataset(LIVE), venue_id=venue),
                valid_from_ns=stated.at_ns,
                source_times=[SourceTime(kind="event", at_ns=stated.at_ns)],
                raw=self.plugin.raw_record(stated.raw_key[:256]),
                unconverted=[*reported, *unread, *stated.unconverted],
            ),
            bid=None if stated.bid is None else Money(stated.bid, self.currency),
            ask=None if stated.ask is None else Money(stated.ask, self.currency),
            bid_quantity=stated.bid_size if stated.bid is not None else None,
            ask_quantity=stated.ask_size if stated.ask is not None else None,
            characteristics=list(characteristics),
        )

    async def _record_trades(self, rows: Sequence[Trade], want_id: str) -> None:
        """Record trades, none twice: a trade recorded already, or a
        withdrawal already recorded, is left out."""
        counts = self.counts[TRADES]
        fresh: list[Trade] = []
        seen: dict[str, Trade] = {}
        for row in rows:
            assert row.meta is not None
            key = row.meta.row_key
            held = seen.get(key) or self.recent.get(key)
            if held is not None and held.cancelled == row.cancelled:
                counts.unchanged += 1
                continue
            fresh.append(row)
            seen[key] = row
        if not fresh:
            return
        await self._record(TRADES, TRADE, fresh, want_id)
        for key, row in seen.items():
            self.recent[key] = row
            self.recent.move_to_end(key)
        counts.withdrawn += sum(1 for row in fresh if row.cancelled)
        while len(self.recent) > RECENT_TRADES:
            self.recent.popitem(last=False)

    # ── The timetable ────────────────────────────────────────────────────

    async def tick(self) -> None:
        """What is due now: each standing want of live prices kept current at
        the live cadence (quotes and trades are streamed); each day still
        forming read again; and, once a session's close is final, the day's
        closes of every listing served, pushed."""
        now = self.clock_ns()
        for standing in list(self.standing.values()):
            if standing.dataset != LIVE or standing.data_type != PRICE:
                continue  # streamed, not asked again
            if now - standing.last_at_ns >= LIVE_CADENCE_SECONDS * NS:
                standing.last_at_ns = now
                await self.live(standing.subjects, standing.kinds, standing.want_id)
        if now - self._forming_at >= FORMING_EVERY_NS:
            self._forming_at = now
            for forming, want_id in list(self.forming.items()):
                await self.daily(
                    [forming.entity_id],
                    forming.day,
                    forming.day,
                    data_type=forming.data_type,
                    want_id=want_id,
                )
        await self.push()

    async def push(self) -> None:
        """Once today's close is final, its closes and bars for every listing
        served, unasked (the daily dataset's push mode)."""
        today = new_york_date(self.clock_ns())
        if self.pushed == today or not self.products.symbols:
            return
        if self.clock_ns() < close_of(today) + FINAL_AFTER_NS:
            return
        self.pushed = today
        subjects = sorted(self.products.symbols)
        for data_type in (PRICE, BAR):
            await self.daily(subjects, today, today, data_type=data_type)
