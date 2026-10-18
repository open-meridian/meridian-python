"""A data plugin for a venue listing pairs -- a base asset priced in a quote
asset, as a crypto exchange's products are -- generic over the venue (0.30.0;
sdk-contract/the-sdk-carries-each-roles-common-logic). Coinbase's and
Kraken's plugins kept this byte for byte between them; it is the SDK's now,
each plugin keeping only its venue's client, its conversion and its stream's
transport.

    feed = pairs.Feed(plugin, CoinbaseMarket(client, "live"), pairs.ProductMap(path),
                      stream=Stream)                         # the plugin's transport
    await plugin.receive(observations_wanted=feed.on_want, want_withdrawn=feed.on_withdrawn)
    await asyncio.gather(feed.keep_current(), feed.keep_streaming())

**What the plugin supplies.** A `Market`: its venue's answers read into the
values below -- every number a `Decimal` from the venue's own text, never a
float; a value that would not read kept as sent (`Unread`) -- each answer
kept as a raw record before anything is read from it. Where it streams, a
`Streamer` factory (its own session layer over its own transport: a
WebSocket, a FIX line, anything) keeping the stream open and calling back
each message and each opening. How the venue is reached never enters here.

- `Asset`: one of the venue's assets, by its own code, with the one global
  identifier the venue's own statements give it: a currency's ISO 4217 code,
  or a token's CAIP-19 where the venue says which contract it is. A token
  the venue states no single network for is the venue's own instrument,
  known by its code alone (ruled 2026-10-03). A stablecoin is a token, never
  its currency.
- `Listed`: a product (a market), its base and quote assets. A product names
  a market, not an asset: its base is a row's subject, priced in its quote.
- `Candle`: one UTC day's open, high, low, close and volume, with a
  volume-weighted price and a trade count where the venue gives them.
- `Tick`: the last trade's price; `Top`: the best bid and offer, with each
  side's size where the venue states it.
- `Print`: one trade, with the side the venue names and whose side it is --
  the resting order's (MAKER) or the one that took liquidity (TAKER) -- so
  the aggressor is said in the contract's words, never guessed.

**Three datasets** (`daily`, `live`, `trades`): each day's close and bar on
the UTC day; the last trade's price and the best bid and offer as prices,
and the best bid and offer with their sizes as a quote, at most once a
second per subject and kind; every trade, from the venue's stream.

**Named before it is served** (W3.6, W3.1, W3.14): each subject the lake asks
for is the deployment's record, read and named as one of the venue's assets
by its identifiers -- the venue's own code first, then the global identifier
the venue states, then another source's symbol that is the venue's code,
never for a record that is a security -- never guessed from its description.
Where the record lacks the venue's identifiers, they are reported beside the
one it matched (W3.1); where that resolve meets another record it is
reported (W3.2) and the subject still served. Only a served product's quote
asset is resolved, a record minted only where none resolves. What does not
resolve is reported and never guessed: a product quoted in it is left out,
and a venue not held is left empty on each row with its code as reported.

**A row** names the base asset's instrument, its dataset, the venue's ID, its
times and the raw record it was read from. A daily close is keyed by the
product and the candle's start (`BTC-USD:1d:1791417600`), the day still
forming restated under the same key as it fills; a trade by its product and
the venue's trade ID (`BTC-USD:t:812345678`); a quote by its product and
instant. A price is a `Money` in the quote asset: a currency by its code, a
token -- a stablecoin among them -- by its own instrument, never a fiat
code. A crypto trade has no condition codes: regular, eligible for every
statistic in both views.

**Wants** (W10.7): a business date or a range of the daily dataset, or the
latest (the past week's days); the live dataset now; trades over a range
from the venue's history; quotes now. Declined `not_covered` where the record
names none of the venue's assets, `beyond_history` before the venue's
reach, `source_silent` where it has nothing. A standing want keeps its
subjects current until withdrawn: live prices polled once a second, the
forming day every five minutes, trades and quotes from the stream.

**The stream** keeps every subject under a standing want of `live` or
`trades` on it while any stands; each time it opens again after a drop, the
trades since the last one recorded are read from the venue's history, so the
lake has no gap. **A restart's gap** (W10.6): before a subject goes on the
stream, the trades the venue's history states after the last one this
instance recorded are recorded, once per subject per process.
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
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, cast

from ...errors import MeridianError, NotGranted
from ...figures import Figure
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
from . import figures as role_figures
from ._pages import connection_fields, connection_figure, served, want_rows
from ._reading import (
    NANOS_PER_SECOND,
    SECONDS_PER_DAY,
    Session,
    Unread,
    iso_time,
    utc_day,
)
from ._records import DatasetsRead as RoleDatasetsRead
from ._records import VenueConnection
from ._wants import BATCH, Counts, Heard, Standing, Venue, Wants, asked, same, unconverted

__all__ = [
    "DAILY",
    "LIVE",
    "MAKER",
    "TAKER",
    "TRADES",
    "Asset",
    "Candle",
    "ConnectionRead",
    "DatasetsRead",
    "Feed",
    "Listed",
    "Mapped",
    "Market",
    "Print",
    "ProductMap",
    "Socket",
    "StreamFactory",
    "StreamHealth",
    "Streamer",
    "Tick",
    "Top",
    "connection_read",
    "datasets_read",
    "figures_read",
]

log = logging.getLogger("meridian.roles.data.pairs")

DAILY, LIVE, TRADES = "daily", "live", "trades"
PRICE, BAR = "meridian.v1.Price", "meridian.v1.Bar"
TRADE, QUOTE = "meridian.v1.Trade", "meridian.v1.Quote"
#: A regular crypto trade: no condition codes, so eligible for every
#: statistic, in its venue's view and the consolidated one.
EVERY = Eligibility(high_low="eligible", open="eligible", close="eligible", volume="eligible")
#: The datasets whose standing wants put their subjects on the stream.
STREAMED = (LIVE, TRADES)
#: The live dataset's pace: each subject and kind at most once a second.
LIVE_EVERY_SECONDS = 1.0
#: A standing want on the daily dataset: its forming day, every five minutes.
DAILY_EVERY_SECONDS = 300.0
#: The product map read again from the venue's listing.
REMAP_SECONDS = 86_400
#: A want for the daily dataset's latest: the past week's days.
LATEST_DAYS = 7
#: How long a live venue's stream may say nothing before it is opened again.
SILENT_SECONDS = 30.0

#: A record's classes that may be a coin's or a currency's: none yet, a
#: crypto asset, cash.
_NOT_A_SECURITY = {
    ops.ASSET_CLASS_UNSPECIFIED,
    ops.ASSET_CLASS_CRYPTO_ASSET,
    ops.ASSET_CLASS_CASH,
}
#: Identifiers only a security carries.
_SECURITY_SCHEMES = {"cusip", "isin", "sedol", "figi"}

_DAILY_KINDS = {ops.PRICE_KIND_CLOSE}
_LIVE_KINDS = {ops.PRICE_KIND_LAST, ops.PRICE_KIND_BID, ops.PRICE_KIND_ASK}


# ── What the venue's answers are read into ──────────────────────────────


@dataclass(frozen=True)
class Asset:
    """One of the venue's assets."""

    #: The venue's own code (Coinbase's `BTC`, Kraken's `XXBT`).
    code: str
    #: "currency" or "token".
    kind: str
    #: Its global identifier's scheme and value -- ("iso4217", "USD"),
    #: ("caip19", "bip122:.../slip44:0") -- or empty where the venue states
    #: none (a token on several networks, or on none it says).
    scheme: str = ""
    value: str = ""
    #: The venue's own name for it, where it gives one, offered as stated.
    name: str = ""

    @property
    def currency_code(self) -> str:
        """Its ISO 4217 code, for a currency; empty for anything else."""
        return self.value if self.scheme == "iso4217" else ""


@dataclass(frozen=True)
class Listed:
    """One product the venue lists: a market, its base asset priced in its
    quote asset."""

    product: str
    base: Asset
    quote: Asset
    #: Whether the venue trades it now; a product it does not is still kept
    #: with its status, since its history still converts.
    tradable: bool = True
    status: str = ""
    #: Its name on the venue's stream, where that differs from `product`
    #: (Kraken's v2 symbols); empty where it is the same.
    stream: str = ""

    @property
    def stream_name(self) -> str:
        return self.stream or self.product


@dataclass(frozen=True)
class Candle:
    """One UTC day of a product's trading, as the venue stated it."""

    product: str
    start_s: int
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: Decimal | None
    #: The day's volume-weighted price and trade count, where the venue
    #: states them for a day that traded; None otherwise, never zero.
    vwap: Decimal | None = None
    trade_count: int | None = None
    #: The raw record it was read from, and where in it.
    raw_key: str = ""
    unread: tuple[Unread, ...] = ()

    @property
    def day(self) -> date:
        return utc_day(self.start_s)

    @property
    def end_ns(self) -> int:
        return (self.start_s + SECONDS_PER_DAY) * NANOS_PER_SECOND


@dataclass(frozen=True)
class Tick:
    """The last trade's price."""

    product: str
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
    """The best bid and offer, the level-1 book; a side with no order is None,
    and a size None where the venue states none."""

    product: str
    bid: Decimal | None
    ask: Decimal | None
    at_ns: int
    stated: bool
    ident: str = ""
    raw_key: str = ""
    unread: tuple[Unread, ...] = ()
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None


#: Whose side a venue names on a trade.
MAKER, TAKER = "maker", "taker"


@dataclass(frozen=True)
class Print:
    """One trade, as the venue stated it."""

    product: str
    price: Decimal | None
    quantity: Decimal | None
    #: When it traded, as the venue stated it.
    at_ns: int
    #: The venue's identity for it: its trade ID.
    ident: str
    #: The side the venue names, "buy" or "sell", and whose side that is:
    #: MAKER, the resting order's, or TAKER, the one that took liquidity;
    #: both empty where the venue names neither.
    side: str = ""
    side_of: str = ""
    raw_key: str = ""
    unread: tuple[Unread, ...] = ()

    @property
    def sequence(self) -> int:
        """The trade ID as a number, where it is one: the venue's order."""
        return int(self.ident) if self.ident.isdigit() else 0


class Socket(Protocol):
    """What a stream's connection is to this module: text sent and received,
    whatever carries it."""

    async def send(self, text: str) -> None: ...

    async def receive(self) -> str: ...

    async def close(self) -> None: ...


class Market(Protocol):
    """A venue's public market data, read into the values above by the
    plugin's own client and conversion; every answer kept as a raw record
    before anything is read from it."""

    #: The venue's code as a `symbol`'s source (`coinbase`, `kraken`).
    venue: str
    #: The identifiers the venue is known by in the venue master, each
    #: (scheme, value, source).
    venue_identifiers: tuple[tuple[str, str, str], ...]
    #: The venue's name, as people know it.
    name: str
    session: Session

    def listing(self) -> list[Listed]:
        """Every product the venue lists, each side read as an asset."""
        ...

    def candles(self, product: str, first: date, last: date) -> list[Candle]:
        """The product's daily candles from `first` to `last`, inclusive,
        oldest first; a day the venue has no candle for is missing."""
        ...

    def last(self, product: str) -> Tick: ...

    def top(self, product: str) -> Top: ...

    def trades(self, product: str, since_ns: int = 0) -> list[Print]:
        """The product's trades from `since_ns` to now, oldest first, as far
        as the venue's history reaches; its latest page where `since_ns` is
        0."""
        ...

    @property
    def stream_address(self) -> str: ...

    async def connect(self, address: str) -> Socket:
        """The stream opened: the venue itself, or its messages replayed."""
        ...

    def subscriptions(self, names: Sequence[str]) -> list[str]:
        """The texts to send for the venue's stream names."""
        ...

    def heard(self, text: str, received_ns: int) -> list[Print | Top]:
        """One stream message -- kept as a raw record first -- read into the
        trades and best bids and offers it states."""
        ...


class StreamHealth(Protocol):
    """How the stream has gone: "off", "connecting", "open" or "waiting"; the
    names on it; how often it opened and dropped; its messages."""

    state: str
    subscribed: tuple[str, ...]
    opened: int
    dropped: int
    messages: int
    last_message_ns: int
    last_error: str


class Streamer(Protocol):
    """The plugin's own session over its own transport, kept open while
    anything is wanted on it: `heard` given each message, `opened` each time
    it opens before any message is read; `retarget` points it at another
    source (sample data switched, or a test's replay). Made by the factory
    `Feed` is given: `stream(address=, connect=, subscriptions=, heard=,
    opened=, clock_ns=, silent_seconds=)`."""

    silent_seconds: float

    @property
    def health(self) -> StreamHealth: ...

    def want(self, names: Sequence[str]) -> None: ...

    def retarget(
        self,
        address: str,
        connect: Callable[[str], Awaitable[Socket]],
        subscriptions: Callable[[Sequence[str]], list[str]],
    ) -> None: ...

    async def run(self, once: bool = False) -> None: ...


@dataclass
class _Quiet:
    """The health of a stream that is never opened."""

    state: str = "off"
    subscribed: tuple[str, ...] = ()
    opened: int = 0
    dropped: int = 0
    messages: int = 0
    last_message_ns: int = 0
    last_error: str = ""


class _NoStream:
    """A venue the plugin does not stream from: nothing is ever opened."""

    def __init__(self, **_: Any) -> None:
        self.silent_seconds = 0.0
        self._health = _Quiet()

    async def connect(self, address: str) -> Socket:
        raise OSError("this plugin does not stream")

    @property
    def health(self) -> _Quiet:
        return self._health

    def want(self, names: Sequence[str]) -> None:
        self._health.subscribed = ()

    def retarget(self, address: str, connect: Any, subscriptions: Any) -> None:
        return None

    async def run(self, once: bool = False) -> None:
        if once:
            return
        await asyncio.Event().wait()


# ── The product map ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class Mapped:
    """A product serving a subject, its quote asset resolved."""

    product: str
    base: Asset
    quote: Asset
    base_id: str
    quote_id: str


class ProductMap:
    """The venue's listing and what each asset resolved to, kept in the
    plugin's own storage (`path`, `products-<mode>.json` beside its raw
    records), read at start, and the listing read again once a day. Nothing
    else reads it (decisions/028)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.listed: list[Listed] = []
        #: The deployment's instrument for each quote asset resolved, by the
        #: venue's code.
        self.ids: dict[str, str] = {}
        #: Which of the venue's assets each subject is, by the deployment's
        #: instrument ID, read from its record.
        self.subjects: dict[str, str] = {}
        #: Each asset reported as missing, by the venue's code, and why.
        self.missing: dict[str, str] = {}
        #: When the listing was last read, in UTC nanoseconds.
        self.read_at_ns = 0

    def load(self) -> bool:
        """Read the map kept in storage; whether there was one."""
        if self.path is None or not self.path.is_file():
            return False
        held: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        self.listed = [
            Listed(
                product=item["product"],
                base=Asset(**item["base"]),
                quote=Asset(**item["quote"]),
                tradable=item["tradable"],
                status=item["status"],
                stream=item.get("stream", ""),
            )
            for item in held.get("listed", [])
        ]
        self.ids = dict(held.get("ids", {}))
        self.subjects = dict(held.get("subjects", {}))
        self.missing = dict(held.get("missing", {}))
        self.read_at_ns = int(held.get("read_at_ns", 0))
        return True

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "listed": [asdict(item) for item in self.listed],
            "ids": self.ids,
            "subjects": self.subjects,
            "missing": self.missing,
            "read_at_ns": self.read_at_ns,
        }
        written = self.path.with_suffix(".tmp")
        written.write_text(json.dumps(body, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(written, self.path)

    def assets(self) -> list[Asset]:
        """Each asset of a product the venue trades, once, by its code."""
        seen: dict[str, Asset] = {}
        for item in self.listed:
            if item.tradable:
                seen.setdefault(item.base.code, item.base)
                seen.setdefault(item.quote.code, item.quote)
        return [seen[code] for code in sorted(seen)]

    def asset(self, code: str) -> Asset | None:
        """The asset of a product the venue trades, by its code."""
        return next((a for a in self.assets() if a.code == code), None)

    def quotes(self, code: str) -> list[Asset]:
        """The quote assets of each product the venue trades on `code`, once."""
        seen: dict[str, Asset] = {}
        for item in self.listed:
            if item.tradable and item.base.code == code:
                seen.setdefault(item.quote.code, item.quote)
        return [seen[c] for c in sorted(seen)]

    def _serving(self, subject: str) -> list[Mapped]:
        code = self.subjects.get(subject, "")
        return [
            Mapped(item.product, item.base, item.quote, subject, self.ids[item.quote.code])
            for item in self.listed
            if code and item.tradable and item.base.code == code and item.quote.code in self.ids
        ]

    def mapped(self) -> list[Mapped]:
        """Every product the venue trades serving a subject, its quote
        resolved; each once, for the first subject it serves."""
        seen: dict[str, Mapped] = {}
        for subject in sorted(self.subjects):
            for mapped in self._serving(subject):
                seen.setdefault(mapped.product, mapped)
        return [seen[p] for p in sorted(seen)]

    def for_subjects(self, subjects: Iterable[str]) -> dict[str, list[Mapped]]:
        """The products each subject is the base asset of, by subject; a
        subject the map holds none for is given an empty list."""
        return {subject: self._serving(subject) for subject in subjects}

    def stream_name(self, product: str) -> str:
        """A product's name on the venue's stream."""
        item = next((i for i in self.listed if i.product == product), None)
        return item.stream_name if item else product

    def product(self, product: str) -> Mapped | None:
        for mapped in self.mapped():
            if mapped.product == product:
                return mapped
        return None

    def code_of(self, instrument_id: str) -> str:
        """The venue's code a subject is, or a quote asset was resolved from;
        empty if none."""
        if instrument_id in self.subjects:
            return self.subjects[instrument_id]
        for code, held in self.ids.items():
            if held == instrument_id:
                return code
        return ""


# ── The work ────────────────────────────────────────────────────────────

#: The plugin's own session over its own transport (see `Streamer`).
StreamFactory = Callable[..., Streamer]


@dataclass
class Feed:
    """A pairs venue's work: resolving, recording, answering wants and keeping
    them current (see the module). `plugin` is a `meridian.Plugin`, or the
    suites' `Recorder`."""

    plugin: Any
    market: Market
    products: ProductMap
    clock_ns: Callable[[], int] = time.time_ns
    #: The plugin's stream factory; None for a venue it does not stream from.
    stream_factory: StreamFactory | None = None
    venue: Venue = field(default_factory=Venue)
    #: Whether the deployment answers this plugin's ResolveInstrument (W3.6).
    reads_instruments: bool = True
    #: Subjects whose record named none of the venue's assets, until the
    #: listing is read again.
    unnamed: set[str] = field(default_factory=set)
    #: Trades heard and not sent yet, in the order heard; and each product's
    #: best bid and offer last heard and not sent yet, by product.
    pending_trades: list[Trade] = field(default_factory=list)
    pending_quotes: dict[str, Quote] = field(default_factory=dict)
    #: Each product's last trade recorded: where a reopened stream catches up
    #: from, and below which a trade heard again is not sent again.
    last_trade: dict[str, Print] = field(default_factory=dict)
    #: The products on the stream, by their names on it.
    streams: dict[str, Mapped] = field(default_factory=dict)
    wants: Wants = field(init=False)
    stream: Streamer = field(init=False)

    def __post_init__(self) -> None:
        self.wants = Wants(self.plugin, (DAILY, LIVE, TRADES), clock_ns=self.clock_ns)
        made = self.stream_factory or cast(StreamFactory, _NoStream)
        self.stream = made(
            address=self.market.stream_address,
            connect=self.market.connect,
            subscriptions=self.market.subscriptions,
            heard=self.on_message,
            opened=self.on_opened,
            clock_ns=self.clock_ns,
            silent_seconds=self._silent(self.market),
        )

    @staticmethod
    def _silent(market: Market) -> float:
        """How long the venue's stream may say nothing: a replay may for ever."""
        return SILENT_SECONDS if market.session.mode == "live" else 0.0

    # ── What the Datasets page and the suites read ───────────────────────

    @property
    def standing(self) -> dict[str, Standing]:
        return self.wants.standing

    @property
    def counts(self) -> Counts:
        return self.wants.counts

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

    @property
    def backfilled(self) -> set[str]:
        return self.wants.backfilled

    def dataset(self, key: str) -> str:
        """A dataset as rows name it: the instance, a colon and the key."""
        return self.wants.dataset(key)

    def sent_to(self, key: str) -> Counts:
        """What it sent the dataset `key` since it started."""
        return self.wants.sent_to(key)

    async def read_licences(self) -> frozenset[str]:
        """Its own declared datasets' licences (contract v20, W10.9)."""
        return await self.wants.read_licences()

    def use(self, market: Market, products: ProductMap) -> None:
        """Answer from another source (sample data switched): its own map, the
        venue asked again, its own stream; standing wants carry over, and are
        streamed from it once named against its map."""
        self.market, self.products, self.venue = market, products, Venue()
        self.pending_trades, self.pending_quotes, self.last_trade = [], {}, {}
        self.streams = {}
        self.stream.want([])  # nothing asked of the new source until named against its map
        self.stream.silent_seconds = self._silent(market)
        self.stream.retarget(market.stream_address, market.connect, market.subscriptions)

    # ── Resolving ────────────────────────────────────────────────────────

    def venue_identifiers(self) -> list[ops.Identifier]:
        """The identifiers the venue is known by in the venue master."""
        return [
            ops.Identifier(scheme=scheme, value=value, source=source)
            for scheme, value, source in self.market.venue_identifiers
        ]

    async def venue_id(self) -> str:
        """The venue master's ID for the venue, asked once per mapping; a
        venue not held is reported once and left empty."""
        return await self.venue.resolve(
            self.plugin, self.market.venue_identifiers, self.market.venue, self.clock_ns()
        )

    def identifiers(self, asset: Asset) -> list[ops.Identifier]:
        """The identifiers the venue's own statements give an asset: its
        global one, and a token's code as a `symbol` at the venue."""
        named: list[ops.Identifier] = []
        if asset.scheme:
            named.append(ops.Identifier(scheme=asset.scheme, value=asset.value))
        if asset.kind != "currency":
            named.append(
                ops.Identifier(scheme="symbol", value=asset.code, source=self.market.venue)
            )
        return named

    @staticmethod
    def described(asset: Asset) -> str:
        """What the venue states an asset is called: its own name where it
        gives one, else its code. A resolve that may mint states a
        description (contract v24, W3.7)."""
        return asset.name or asset.code

    async def _resolve(self, asset: Asset, now: int) -> None:
        cash = asset.kind == "currency"
        found = await self.plugin.resolve_identifier(
            identifiers=self.identifiers(asset),
            as_of_ns=now,
            stated_asset_class="cash" if cash else "crypto_asset",
            stated_description=self.described(asset),
        )
        if found.found and found.instrument_id:
            self.products.ids[asset.code] = found.instrument_id
            self.products.missing.pop(asset.code, None)
            return
        reason = ops.MissReason.Name(found.miss_reason or ops.MISS_REASON_NOT_FOUND)
        if self.products.missing.get(asset.code) != reason:
            await self.plugin.report_missing_instrument(
                source=self.market.venue,
                asset_class="cash" if cash else "crypto_asset",
                identifiers=self.identifiers(asset),
                as_of_ns=now,
                reason=found.miss_reason or "not_found",
                observed_at_ns=now,
            )
        self.products.missing[asset.code] = reason

    async def _quotes(self, code: str, now: int) -> None:
        """Resolve the quote assets of each product on `code` not resolved yet."""
        for quote in self.products.quotes(code):
            if quote.code not in self.products.ids:
                await self._resolve(quote, now)

    def _asset_of(self, record: ops.InstrumentRecord) -> tuple[Asset, ops.Identifier] | None:
        """The venue's asset a record is, by its identifiers, and the one it
        matched: the venue's own code, then the global identifier the venue
        states, then another source's symbol that is the venue's code -- the
        last never for a record that is a security (a class other than a
        crypto asset or cash, or a security's identifier): a ticker can be
        a coin's code too (ETH is a share's)."""
        assets = self.products.assets()
        venue = self.market.venue
        held = list(record.identifiers)
        for i in held:
            if i.scheme == "symbol" and i.source == venue:
                found = next((a for a in assets if a.code == i.value), None)
                if found:
                    return found, i
        for i in held:
            found = next((a for a in assets if a.scheme and (a.scheme, a.value)
                          == (i.scheme, i.value)), None)  # fmt: skip
            if found:
                return found, i
        if record.asset_class not in _NOT_A_SECURITY or any(
            i.scheme in _SECURITY_SCHEMES for i in held
        ):
            return None
        for i in held:
            if i.scheme == "symbol" and i.source != venue:
                found = next((a for a in assets if a.code.upper() == i.value.upper()), None)
                if found:
                    return found, i
        return None

    async def _join(
        self,
        subject: str,
        asset: Asset,
        matched: ops.Identifier,
        held: Sequence[ops.Identifier],
    ) -> None:
        """Report the venue's identifiers beside the one the record matched
        (W3.1), where it lacks them: one identifier in common is one
        security, so the record gains the venue's. Meeting another record is
        a miss (W3.2), reported once; the subject is served all the same."""
        own = self.identifiers(asset)
        if all(any(same(o, h) for h in held) for o in own):
            return
        named = own + ([] if any(same(matched, o) for o in own) else [matched])
        cash = asset.kind == "currency"
        now = self.clock_ns()
        found = await self.plugin.resolve_identifier(
            identifiers=named,
            as_of_ns=now,
            stated_asset_class="cash" if cash else "crypto_asset",
            stated_description=self.described(asset),
        )
        if found.found and found.instrument_id == subject:
            return
        # Matched another record: two records for one asset, which a person
        # merges (W3.13).
        miss = ops.MISS_REASON_AMBIGUOUS if found.found else found.miss_reason
        reason = ops.MissReason.Name(miss or ops.MISS_REASON_AMBIGUOUS)
        if self.products.missing.get(asset.code) != reason:
            await self.plugin.report_missing_instrument(
                source=self.market.venue,
                asset_class="cash" if cash else "crypto_asset",
                identifiers=named,
                as_of_ns=now,
                reason=miss or ops.MISS_REASON_AMBIGUOUS,
                observed_at_ns=now,
            )
        self.products.missing[asset.code] = reason

    async def _named(self, subject: str) -> str:
        """The venue's code a subject is, read from its record; empty where
        the record names none of the venue's assets, or cannot be read."""
        if not self.reads_instruments:
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
            return ""
        if not found.found:
            return ""
        held = list(found.instrument.identifiers)
        named = self._asset_of(found.instrument)
        if named is None:
            return ""
        asset, matched = named
        await self._join(subject, asset, matched, held)
        return asset.code

    async def name(self, subjects: Iterable[str]) -> None:
        """Name each subject not named yet as one of the venue's assets, and
        resolve the quote assets of its products; the map kept in storage."""
        now = self.clock_ns()
        changed = False
        for subject in subjects:
            if subject in self.products.subjects or subject in self.unnamed:
                continue
            code = await self._named(subject)
            if not code:
                self.unnamed.add(subject)
                continue
            self.products.subjects[subject] = code
            await self._quotes(code, now)
            changed = True
        if changed:
            self.products.save()

    async def map_products(self) -> ProductMap:
        """Read the venue's listing, and resolve the quote assets of any
        product newly serving a subject; the map kept in storage. The venue
        is asked again too, and a subject not named is read again when next
        asked."""
        listed = await asyncio.to_thread(self.market.listing)
        now = self.clock_ns()
        self.products.listed = listed
        self.products.read_at_ns = now
        self.unnamed.clear()
        for code in sorted(set(self.products.subjects.values())):
            await self._quotes(code, now)
        self.products.save()
        self.venue.asked = False
        await self.venue_id()
        await self.restream()
        return self.products

    async def ensure_mapped(self) -> None:
        if not self.products.read_at_ns:
            await self.map_products()
        elif not self.venue.asked:
            await self.venue_id()

    # ── Rows ─────────────────────────────────────────────────────────────

    def _money(self, amount: Any, mapped: Mapped) -> Money:
        """An amount in the product's quote asset: a currency by its code, any
        token by its own instrument, never a fiat code."""
        if mapped.quote.currency_code:
            return Money(amount, mapped.quote.currency_code)
        return Money(amount, instrument_id=mapped.quote_id)

    def _unconverted(self, unread: Iterable[Unread]) -> list[ops.AsReported]:
        return unconverted(self.market.venue, unread, self.venue, self.market.name)

    def _meta(
        self,
        row_key: str,
        mapped: Mapped,
        key: str,
        valid_from_ns: int,
        valid_until_ns: int,
        times: Sequence[SourceTime],
        raw_key: str,
        unread: Iterable[Unread] = (),
        business_date: date | None = None,
    ) -> ObservationMeta:
        return ObservationMeta(
            row_key=row_key,
            subjects=[ops.SubjectRef(entity_id=mapped.base_id)],
            source=ops.Source(dataset=self.dataset(key), venue_id=self.venue.venue_id),
            valid_from_ns=valid_from_ns,
            valid_until_ns=valid_until_ns,
            business_date=business_date or "",
            source_times=list(times),
            raw=self.plugin.raw_record(raw_key),
            unconverted=self._unconverted(unread),
        )

    def _daily_meta(
        self, mapped: Mapped, candle: Candle, optional: Iterable[Unread] = ()
    ) -> Any:
        now = self.clock_ns()
        forming = candle.end_ns > now
        times = [] if forming else [SourceTime(kind="published", at_ns=candle.end_ns)]
        return self._meta(
            f"{mapped.product}:1d:{candle.start_s}",
            mapped,
            DAILY,
            candle.start_s * NANOS_PER_SECOND,
            candle.end_ns,
            times,
            candle.raw_key,
            optional,
            candle.day,
        )

    def close(self, mapped: Mapped, candle: Candle) -> Price | None:
        """The day's close: the dataset's declared close for its business
        date, the last price of the UTC day."""
        if candle.close is None:
            return None
        return Price(
            meta=self._daily_meta(mapped, candle),
            kind="close",
            price=self._money(candle.close, mapped),
            basis="per_unit",
        )

    def bar(self, mapped: Mapped, candle: Candle) -> Bar | None:
        """The day's bar; a volume-weighted price and a trade count only where
        the venue states them for a day that traded, never zero."""
        open_, high, low, close, volume = (
            candle.open, candle.high, candle.low, candle.close, candle.volume
        )  # fmt: skip
        if open_ is None or high is None or low is None or close is None or volume is None:
            return None
        optional = [u for u in candle.unread if u.field.endswith(("vwap", "count"))]
        return Bar(
            meta=self._daily_meta(mapped, candle, optional),
            open=self._money(open_, mapped),
            high=self._money(high, mapped),
            low=self._money(low, mapped),
            close=self._money(close, mapped),
            volume=volume,
            vwap=None if candle.vwap is None else self._money(candle.vwap, mapped),
            trade_count=candle.trade_count,
        )

    def _live(self, mapped: Mapped, kind: str, amount: Any, seen: Tick | Top) -> Price:
        times = [SourceTime(kind="event", at_ns=seen.at_ns)] if seen.stated else []
        ident = seen.ident or str(seen.at_ns)
        return Price(
            meta=self._meta(
                f"{mapped.product}:{kind}:{ident}",
                mapped,
                LIVE,
                seen.at_ns,
                0,
                times,
                seen.raw_key,
            ),  # fmt: skip
            kind=kind,
            price=self._money(amount, mapped),
            basis="per_unit",
        )

    def aggressor(self, seen: Print) -> str:
        """The side that took liquidity, in the contract's words: the venue's
        side as sent where it names the taker's, the other where it names the
        resting order's, and none where it names neither."""
        if seen.side not in ("buy", "sell"):
            return ""
        if seen.side_of == TAKER:
            return seen.side
        if seen.side_of == MAKER:
            return "sell" if seen.side == "buy" else "buy"
        return ""

    def trade(self, mapped: Mapped, seen: Print) -> Trade | None:
        """One trade: a regular crypto trade, eligible for every statistic in
        both views, its aggressor as the venue said it. None where its price or
        quantity did not read, or is not more than zero."""
        if seen.price is None or seen.quantity is None or seen.quantity <= 0:
            return None
        return Trade(
            meta=self._meta(
                f"{mapped.product}:t:{seen.ident}",
                mapped,
                TRADES,
                seen.at_ns,
                0,
                [SourceTime(kind="event", at_ns=seen.at_ns)],
                seen.raw_key,
                seen.unread,
            ),
            price=self._money(seen.price, mapped),
            quantity=seen.quantity,
            attributes=TradeAttributes(consolidated=EVERY, market_centre=EVERY),
            aggressor=self.aggressor(seen) or None,
            source_sequence=seen.sequence,
        )

    def quote(self, mapped: Mapped, best: Top) -> Quote | None:
        """The best bid and offer with their sizes, in force from its time; a
        side with no order, or whose price did not read, left unset. None where
        neither side has one."""
        if best.bid is None and best.ask is None:
            return None
        times = [SourceTime(kind="event", at_ns=best.at_ns)] if best.stated else []
        return Quote(
            meta=self._meta(
                f"{mapped.product}:q:{best.at_ns}",
                mapped,
                LIVE,
                best.at_ns,
                0,
                times,
                best.raw_key,
                best.unread,
            ),
            bid=None if best.bid is None else self._money(best.bid, mapped),
            ask=None if best.ask is None else self._money(best.ask, mapped),
            bid_quantity=best.bid_size if best.bid is not None else None,
            ask_quantity=best.ask_size if best.ask is not None else None,
        )

    # ── Recording ────────────────────────────────────────────────────────

    async def _send(self, prices: list[Price], bars: list[Bar], want_id: str, key: str) -> int:
        sent = await self.wants.record("prices", prices, key, want_id)
        return sent + await self.wants.record("bars", bars, key, want_id)

    async def _send_trades(
        self, trades: list[Trade], quotes: list[Quote], want_id: str
    ) -> None:
        await self.wants.record("trades", trades, TRADES, want_id)
        await self.wants.record("quotes", quotes, LIVE, want_id)

    async def _asked(self, call: Callable[..., Any], *args: Any) -> Any:
        return await asked(call, *args, of=self.market.name)

    async def record_days(
        self,
        subjects: Iterable[str],
        first: date,
        last: date,
        data_type: str = "",
        want_id: str = "",
    ) -> dict[str, str]:
        """Each subject's closes and bars from `first` to `last` from every
        product it is the base of; what was declined, by subject and reason."""
        await self.ensure_mapped()
        subjects = list(subjects)
        await self.name(subjects)
        today = utc_day(self.clock_ns() // NANOS_PER_SECOND)
        reach = self.market.session.limits.history_days
        declined: dict[str, str] = {}
        prices: list[Price] = []
        bars: list[Bar] = []
        for subject, products in self.products.for_subjects(subjects).items():
            if not products:
                declined[subject] = "not_covered"
                continue
            if first > today:
                declined[subject] = "source_silent"
                continue
            if reach and last < today - timedelta(days=reach - 1):
                declined[subject] = "beyond_history"
                continue
            found = 0
            for mapped in products:
                read = await self._asked(
                    self.market.candles, mapped.product, first, min(last, today)
                )
                for candle in read or []:
                    if candle.unread and candle.close is None:
                        self.counts.unread += 1
                    if data_type in ("", PRICE) and (row := self.close(mapped, candle)):
                        prices.append(row)
                        found += 1
                    if data_type in ("", BAR) and (bar := self.bar(mapped, candle)):
                        bars.append(bar)
                        found += 1
            if not found:
                declined[subject] = "source_silent"
        await self._send(prices, bars, want_id, DAILY)
        return declined

    async def record_live(
        self, subjects: Iterable[str], kinds: Iterable[int] = (), want_id: str = ""
    ) -> dict[str, str]:
        """Each subject's last price and best bid and offer now, from every
        product it is the base of."""
        await self.ensure_mapped()
        subjects = list(subjects)
        await self.name(subjects)
        wanted = set(kinds) or set(_LIVE_KINDS)
        declined: dict[str, str] = {}
        prices: list[Price] = []
        for subject, products in self.products.for_subjects(subjects).items():
            if not products:
                declined[subject] = "not_covered"
                continue
            before = len(prices)
            for mapped in products:
                if ops.PRICE_KIND_LAST in wanted:
                    tick = await self._asked(self.market.last, mapped.product)
                    if tick and tick.price is not None:
                        prices.append(self._live(mapped, "last", tick.price, tick))
                    elif tick:
                        self.counts.unread += 1
                if wanted & {ops.PRICE_KIND_BID, ops.PRICE_KIND_ASK}:
                    best = await self._asked(self.market.top, mapped.product)
                    if best and ops.PRICE_KIND_BID in wanted and best.bid is not None:
                        prices.append(self._live(mapped, "bid", best.bid, best))
                    if best and ops.PRICE_KIND_ASK in wanted and best.ask is not None:
                        prices.append(self._live(mapped, "ask", best.ask, best))
                    self.counts.unread += len(best.unread) if best else 0
            if len(prices) == before:
                declined[subject] = "source_silent"
        await self._send(prices, [], want_id, LIVE)
        return declined

    async def record_trades(
        self, subjects: Iterable[str], from_ns: int = 0, until_ns: int = 0, want_id: str = ""
    ) -> dict[str, str]:
        """Each subject's trades from `from_ns` to `until_ns` (now where it is
        0), from the venue's history, as far as it reaches: a want for a
        range, not a stream."""
        await self.ensure_mapped()
        subjects = list(subjects)
        await self.name(subjects)
        now = self.clock_ns()
        until = until_ns or now
        declined: dict[str, str] = {}
        rows: list[Trade] = []
        for subject, products in self.products.for_subjects(subjects).items():
            if not products:
                declined[subject] = "not_covered"
                continue
            if from_ns > now:
                declined[subject] = "source_silent"
                continue
            found, reached = 0, 0
            for mapped in products:
                for seen in (
                    await self._asked(self.market.trades, mapped.product, from_ns) or []
                ):
                    reached = min(reached, seen.at_ns) if reached else seen.at_ns
                    if from_ns <= seen.at_ns < until and (row := self.trade(mapped, seen)):
                        rows.append(row)
                        found += 1
                    elif seen.price is None or seen.quantity is None:
                        self.counts.unread += 1
            if not found:
                before = reached and until <= reached
                declined[subject] = "beyond_history" if before else "source_silent"
        await self._send_trades(rows, [], want_id)
        return declined

    async def record_quotes(self, subjects: Iterable[str], want_id: str = "") -> dict[str, str]:
        """Each subject's best bid and offer with their sizes now, from every
        product it is the base of, read from the venue's level-1 book."""
        await self.ensure_mapped()
        subjects = list(subjects)
        await self.name(subjects)
        declined: dict[str, str] = {}
        quotes: list[Quote] = []
        for subject, products in self.products.for_subjects(subjects).items():
            if not products:
                declined[subject] = "not_covered"
                continue
            before = len(quotes)
            for mapped in products:
                best = await self._asked(self.market.top, mapped.product)
                if best and (row := self.quote(mapped, best)):
                    quotes.append(row)
                self.counts.unread += len(best.unread) if best else 0
            if len(quotes) == before:
                declined[subject] = "source_silent"
        await self._send_trades([], quotes, want_id)
        return declined

    # ── The stream ───────────────────────────────────────────────────────

    async def restream(self) -> None:
        """Put on the stream the products of every subject under a standing
        want of the live or the trades dataset, each subject named first; the
        stream closed where none stands."""
        streamed = [
            w for w in self.standing.values() if self.wants.key_of(w.dataset) in STREAMED
        ]
        subjects = sorted({s for w in streamed for s in w.subjects})
        if subjects:
            await self.ensure_mapped()
            await self.name(subjects)
        self.streams = {
            self.products.stream_name(mapped.product): mapped
            for products in self.products.for_subjects(subjects).values()
            for mapped in products
        }
        await self.backfill(subjects)
        self.stream.want(sorted(self.streams))

    async def backfill(self, subjects: Sequence[str]) -> int:
        """A restart's gap (contract v20, W10.6) for each subject it streams,
        once per subject per process (`Wants.backfill`)."""
        return await self.wants.backfill(subjects, self._missed, TRADES)

    async def _missed(self, last: ops.Trade) -> list[Trade]:
        """The trades the venue's history states after `last`, the last one
        this instance recorded of a product, as the lake answered it: by the
        venue's trade ID where it is a number, else by time. The product's
        last trade becomes the newest read, so the stream does not send one
        again."""
        product, keyed, ident = last.meta.row_key.rpartition(":t:")
        if not keyed or last.meta.source.dataset != self.dataset(TRADES):
            return []
        mapped = next((m for m in self.streams.values() if m.product == product), None)
        if mapped is None:
            return []
        since = last.meta.valid_from_ns
        missed: list[Trade] = []
        for seen in await self._asked(self.market.trades, product, since) or []:
            after = (
                seen.sequence > int(ident)
                if seen.sequence and ident.isdigit()
                else (seen.at_ns > since)
            )
            if not after:
                continue
            row = self.trade(mapped, seen)
            if row is None:
                self.counts.unread += 1
                continue
            missed.append(row)
            held = self.last_trade.get(product)
            if held is None or seen.sequence > held.sequence or seen.at_ns > held.at_ns:
                self.last_trade[product] = seen
        return missed

    def _hear_trade(self, mapped: Mapped, seen: Print) -> None:
        last = self.last_trade.get(mapped.product)
        if last is not None and seen.sequence and seen.sequence <= last.sequence:
            return  # heard again: from a snapshot, or the history read on reopening
        row = self.trade(mapped, seen)
        if row is None:
            self.counts.unread += 1
            return
        self.pending_trades.append(row)
        self.last_trade[mapped.product] = seen

    async def on_message(self, text: str) -> None:
        """One message of the stream: its trades kept to send, each product's
        best bid and offer kept as its latest; sent at once where a batch is
        full, else by the next pass keeping current."""
        for seen in self.market.heard(text, self.clock_ns()):
            mapped = self.streams.get(seen.product)
            if mapped is None:
                continue
            if isinstance(seen, Print):
                self._hear_trade(mapped, seen)
            elif row := self.quote(mapped, seen):
                self.pending_quotes[mapped.product] = row
        if len(self.pending_trades) >= BATCH:
            await self.flush()

    async def on_opened(self, names: Sequence[str]) -> None:
        """The stream opened: each product's trades since the last one recorded
        read from the venue's history, so a drop leaves the lake no gap. A
        product with none recorded yet has no gap to fill."""
        for name in names:
            mapped = self.streams.get(name)
            last = self.last_trade.get(mapped.product) if mapped else None
            if mapped is None or last is None:
                continue
            for seen in await self._asked(self.market.trades, mapped.product, last.at_ns) or []:
                self._hear_trade(mapped, seen)
        await self.flush()

    async def flush(self) -> None:
        """Send the trades heard, in batches, and each product's latest best bid
        and offer: at most once a pass, so a quote at most once a second."""
        trades, self.pending_trades = self.pending_trades, []
        quotes, self.pending_quotes = list(self.pending_quotes.values()), {}
        if not trades and not quotes:
            return
        try:
            await self._send_trades(trades, quotes, "")
        except (MeridianError, ValueError) as refused:
            # Refused whole (W10.4): said, and the stream goes on; a trade the
            # lake did not take is read back from the history only if the
            # stream drops and opens again, so it is logged here.
            log.warning("%d trades and %d quotes not recorded: %s",
                        len(trades), len(quotes), refused)  # fmt: skip

    async def keep_streaming(
        self, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    ) -> None:
        """Keep the stream open while anything stands on it, until cancelled; a
        failure said, and the stream opened again a second later."""
        while True:
            try:
                await self.stream.run()
            except Exception as failed:  # noqa: BLE001 - said, and opened again
                log.warning("the stream stopped, opening it again: %s", failed)
            await sleep(LIVE_EVERY_SECONDS)

    # ── Wants ────────────────────────────────────────────────────────────

    async def on_want(self, heard: Any) -> None:
        """Record what the lake wants, or decline it per subject."""
        await self.wants.hear(heard, self._answer)

    @staticmethod
    def _serves(key: str, data_type: str, kinds: tuple[int, ...]) -> bool:
        """Whether a want of `data_type` and `kinds` asks of `key` what it holds."""
        if key == DAILY:
            return data_type in ("", PRICE, BAR) and (
                not kinds or bool(set(kinds) & _DAILY_KINDS)
            )
        if key == LIVE:
            if data_type == QUOTE:
                return True
            return data_type in ("", PRICE) and (not kinds or bool(set(kinds) & _LIVE_KINDS))
        return key == TRADES and data_type in ("", TRADE)

    async def _answer(
        self,
        want: ops.ObservationsWantedEvent,
        key: str,
        subjects: list[str],
        kinds: tuple[int, ...],
    ) -> dict[str, str]:
        if not self._serves(key, want.data_type, kinds):
            return {s: "not_covered" for s in subjects}
        if want.standing:
            self.wants.stand(want, subjects, kinds)
            if key in STREAMED:
                await self.restream()
        if key == TRADES:
            if want.standing:
                # Kept current from the stream: nothing to record yet.
                served_now = self.products.for_subjects(subjects)
                return {s: "not_covered" for s in subjects if not served_now[s]}
            return await self.record_trades(
                subjects, want.valid_from_ns, want.valid_until_ns, want.want_id
            )
        if key == LIVE and want.data_type == QUOTE:
            return await self.record_quotes(subjects, want.want_id)
        if key == LIVE:
            return await self.record_live(subjects, kinds, want.want_id)
        if want.business_date:
            day = date.fromisoformat(want.business_date)
            return await self.record_days(subjects, day, day, want.data_type, want.want_id)
        if want.valid_from_ns:
            until = want.valid_until_ns or self.clock_ns()
            first = utc_day(want.valid_from_ns // NANOS_PER_SECOND)
            last = utc_day(max(until - 1, want.valid_from_ns) // NANOS_PER_SECOND)
            return await self.record_days(subjects, first, last, want.data_type, want.want_id)
        # The latest: the days of the past week the venue has, the forming one
        # among them, so a subject the venue still trades is never declined
        # for a day that has barely begun (a decline stands a day).
        today = utc_day(self.clock_ns() // NANOS_PER_SECOND)
        first = today - timedelta(days=LATEST_DAYS - 1)
        return await self.record_days(subjects, first, today, want.data_type, want.want_id)

    async def on_withdrawn(self, heard: Any) -> None:
        """A standing want withdrawn: its subjects are no longer kept current,
        nor streamed unless another stands for them."""
        withdrawn = self.wants.withdraw(heard.message.want_id)
        if withdrawn is not None and self.wants.key_of(withdrawn.dataset) in STREAMED:
            await self.restream()

    # ── Keeping current ──────────────────────────────────────────────────

    async def current(self, daily: bool = False) -> None:
        """One pass keeping each standing want's subjects current: what the
        stream heard sent, the live dataset's prices polled, and with `daily`
        the daily dataset's forming day. A standing want of quotes or trades
        is kept current by the stream alone, put on it again here where the
        source changed under it."""
        await self.flush()
        if not self.streams and any(self.wants.key_of(w.dataset) in STREAMED
                                    for w in self.standing.values()):  # fmt: skip
            await self.restream()
        live = [w for w in self.wants.standing_of(LIVE) if w.data_type in ("", PRICE)]
        for subjects, kinds in _grouped(live):
            await self.record_live(subjects, kinds)
        if daily:
            today = utc_day(self.clock_ns() // NANOS_PER_SECOND)
            for want in self.wants.standing_of(DAILY):
                await self.record_days(want.subjects, today - timedelta(days=1), today,
                                       want.data_type)  # fmt: skip

    async def keep_current(
        self, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    ) -> None:
        """Keep each standing want's subjects current, until cancelled: the live
        dataset at most once a second, the daily one's forming day every five
        minutes; the product map read again once a day."""
        last_daily = 0.0
        last_map = time.monotonic()
        while True:
            now = time.monotonic()
            try:
                if now - last_map >= REMAP_SECONDS:
                    await self.map_products()
                    last_map = now
                due = now - last_daily >= DAILY_EVERY_SECONDS
                await self.current(daily=due)
                if due:
                    last_daily = now
            except Exception as failed:  # noqa: BLE001 - said, and tried again next time
                log.warning("keeping current stopped this time: %s", failed)
            await sleep(LIVE_EVERY_SECONDS)


def _grouped(wants: Iterable[Standing]) -> list[tuple[list[str], tuple[int, ...]]]:
    """The live standing wants' subjects, once each, by the kinds asked."""
    by_kinds: dict[tuple[int, ...], set[str]] = {}
    for want in wants:
        by_kinds.setdefault(tuple(sorted(want.kinds)), set()).update(want.subjects)
    return [(sorted(subjects), kinds) for kinds, subjects in sorted(by_kinds.items())]


# ── The pages ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConnectionRead(VenueConnection):
    """The role's Connection for a pairs venue: the venue's part
    (`VenueConnection`), and its stream's session -- "off" while nothing
    stands to stream, "connecting", "open", or "waiting" to open again after
    a drop; the products on it, how often it opened and dropped, its
    messages."""

    stream_state: str = "off"
    streaming: int = 0
    stream_opened: int = 0
    stream_dropped: int = 0
    stream_messages: int = 0
    last_message_at: str = ""
    stream_error: str = ""


@dataclass(frozen=True)
class DatasetsRead(RoleDatasetsRead):
    """The role's Datasets for a pairs venue, and the venue's product map and
    counts: wants kept current, products listed and mapped, subjects named,
    assets not resolved, when the listing was read, and rows restated,
    unchanged and not read."""

    standing_wants: int = 0
    products_listed: int = 0
    products_mapped: int = 0
    subjects_named: int = 0
    assets_not_resolved: list[str] = field(default_factory=list)
    map_read_at: str = ""
    restated: int = 0
    unchanged: int = 0
    not_read: int = 0


def connection_read(
    feed: Feed | None, venue_name: str, entitled_at_vendor: str
) -> ConnectionRead:
    """Connection's record (`read_connection`), drawn by the template
    `meridian/roles/data/pairs/connection.html`."""
    if feed is None:
        return ConnectionRead(
            mode="Live", entitled_at_vendor=entitled_at_vendor, sessions=0, venue=venue_name
        )
    stream = feed.stream.health
    return ConnectionRead(
        **connection_fields(
            feed.market.session, feed.market.name, feed.venue, entitled_at_vendor
        ),
        sessions=1 if stream.state == "open" else 0,
        stream_state=stream.state,
        streaming=len(stream.subscribed),
        stream_opened=stream.opened,
        stream_dropped=stream.dropped,
        stream_messages=stream.messages,
        last_message_at=iso_time(stream.last_message_ns),
        stream_error=stream.last_error,
    )


def datasets_read(
    feed: Feed | None, catalogue: Sequence[Any], instance: str, entitled_at_vendor: str
) -> DatasetsRead:
    """Datasets' record (`read_datasets`), drawn by the template
    `meridian/roles/data/pairs/datasets.html`; `instance` names the datasets
    before the plugin has started."""
    if feed is None:
        return DatasetsRead(served=served(catalogue, instance, None, entitled_at_vendor))
    named = feed.plugin.identity.instance_id
    return DatasetsRead(
        served=served(catalogue, named, feed.wants, entitled_at_vendor),
        wants=list(want_rows(feed.wants)),
        reads_instruments=feed.reads_instruments,
        standing_wants=len(feed.standing),
        products_listed=len(feed.products.listed),
        products_mapped=len(feed.products.mapped()),
        subjects_named=len(feed.products.subjects),
        assets_not_resolved=sorted(feed.products.missing),
        map_read_at=iso_time(feed.products.read_at_ns),
        restated=feed.counts.restated,
        unchanged=feed.counts.unchanged,
        not_read=feed.counts.unread,
    )


def figures_read(feed: Feed | None, catalogue: Sequence[Any]) -> list[Figure]:
    """The data role's figures on the Summary, in its order: Connection,
    Entitled at the vendor, Stream and Last recorded. A venue stating no
    running rate to measure against leaves Rate use out."""
    if feed is None:
        return role_figures(connection="Answering")
    said = connection_read(feed, feed.market.name, "")
    stream: str | Figure = "Off"
    if said.stream_state != "off":
        listings = f"{said.streaming} {'listing' if said.streaming == 1 else 'listings'}"
        stream = Figure(
            "",
            listings,
            state=None if said.stream_state == "open" else "warn",
            why=None if said.stream_state == "open" else f"The stream is {said.stream_state}",
        )
    last = max((feed.sent_to(key).last_ns for key in (DAILY, LIVE, TRADES)), default=0)
    return role_figures(
        connection=connection_figure(said.mode, said.healthy, said.last_error),
        entitled_at_vendor=f"{len(catalogue)} of {len(catalogue)} datasets",
        stream=stream,
        last_recorded=datetime.fromtimestamp(last / 1e9, tz=UTC) if last else None,
    )
