"""Two made-up venues for the data role's kinds of venue (0.30.0): a pairs
venue (`pairs_venue`) and an event-contract venue (`contracts_venue`), each a
module-like namespace holding what `meridian.roles.data.testing`'s producers
ask of a plugin's `venue_cases`. Nothing here is any vendor's: the values are
invented, the transport is a list of messages, and every number is a string
read by `meridian.roles.data.number`, as a plugin's conversion reads its
venue's."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from types import SimpleNamespace
from typing import Any

from meridian.roles.data import Endpoint, Limits, Session, day_start, number, pairs
from meridian.roles.data import event_contracts as ec
from meridian.roles.data.testing import BITCOIN

NOW_NS = 1_791_633_600 * 1_000_000_000  # 2026-10-10 12:00 UTC, the day forming
TODAY = date(2026, 10, 10)
CLOSED = date(2026, 10, 8)
SECOND = 1_000_000_000


class Dropped(Exception):
    """The made-up connection dropped."""


class Replayed:
    """A connection saying its messages once subscribed, then dropping."""

    def __init__(self, messages: Sequence[str]) -> None:
        self.messages = list(messages)
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def receive(self) -> str:
        if self.messages:
            return self.messages.pop(0)
        raise Dropped("the replay dropped the connection")

    async def close(self) -> None:
        return None


@dataclass
class Health:
    state: str = "off"
    subscribed: tuple[str, ...] = ()
    opened: int = 0
    dropped: int = 0
    messages: int = 0
    last_message_ns: int = 0
    last_error: str = ""


@dataclass
class Keeper:
    """The least a plugin's stream session does: one connection a run, its
    subscriptions sent, `opened` called, each message handed on."""

    address: str
    connect: Callable[[str], Awaitable[Any]]
    subscriptions: Callable[[Sequence[str]], list[str]]
    heard: Callable[[str], Awaitable[None]]
    opened: Callable[[Sequence[str]], Awaitable[None]]
    clock_ns: Callable[[], int] = lambda: NOW_NS
    silent_seconds: float = 0.0
    health: Health = field(default_factory=Health)
    wanted: tuple[str, ...] = ()

    def want(self, names: Sequence[str]) -> None:
        self.wanted = tuple(sorted(set(names)))

    def retarget(self, address: str, connect: Any, subscriptions: Any) -> None:
        self.address, self.connect, self.subscriptions = address, connect, subscriptions

    async def run(self, once: bool = False) -> None:
        if not self.wanted:
            return
        socket = await self.connect(self.address)
        self.health.opened += 1
        self.health.state, self.health.subscribed = "open", self.wanted
        for text in self.subscriptions(self.wanted):
            await socket.send(text)
        await self.opened(self.wanted)
        try:
            while True:
                text = await socket.receive()
                self.health.messages += 1
                await self.heard(text)
        except Dropped as dropped:
            self.health.dropped += 1
            self.health.last_error = str(dropped)
        self.health.state = "waiting"


# ── A pairs venue ───────────────────────────────────────────────────────

USD = pairs.Asset("USD", "currency", "iso4217", "USD", "US Dollar")
BTC = pairs.Asset("BTC", "token", "caip19", BITCOIN, "Bitcoin")
USDC = pairs.Asset("USDC", "token", name="Made-up USDC")
TKN = pairs.Asset("TKN", "token", name="Made-up token")
PLY = pairs.Asset("PLY", "token", name="Made-up asset met twice")
OLD = pairs.Asset("OLD", "token", name="Delisted")

LISTED = [
    pairs.Listed("BTC-USD", BTC, USD),
    pairs.Listed("BTC-USDC", BTC, USDC),
    pairs.Listed("TKN-USD", TKN, USD),
    pairs.Listed("PLY-USD", PLY, USD),
    pairs.Listed("OLD-USD", OLD, USD, tradable=False, status="delisted"),
]
CLOSES = {
    "BTC-USD": "62000.10",
    "BTC-USDC": "62004.90",
    "TKN-USD": "0.000012345678901234",
    "PLY-USD": "1.25",
}
#: The forming day's close, as read the first and the second time.
FORMING = ["61990.55", "62155.75"]
#: BTC-USD's history of trades: the restart's gap after 8804 is 8805, 8806.
HISTORY = [
    ("8803", "62001.00"),
    ("8804", "62002.00"),
    ("8805", "62003.00"),
    ("8806", "62004.00"),
]
MAKER_SELL = json.dumps(
    {
        "type": "trade",
        "product": "BTC-USD",
        "id": "8902",
        "price": "62510.01",
        "size": "0.0125",
        "side": "sell",
        "at": NOW_NS - 2 * SECOND,
    }
)
TOP = json.dumps(
    {
        "type": "top",
        "product": "BTC-USD",
        "bid": "62510.00",
        "bid_size": "0.84",
        "ask": "62510.02",
        "ask_size": "0.50",
        "at": NOW_NS - SECOND,
    }
)


class PairsMarket:
    """The made-up pairs venue, read into the module's values."""

    venue = "fakex"
    name = "Fake Exchange"
    venue_identifiers = (("symbol", "fakex", "fakex"),)
    stream_address = "wss://fakex.invalid/stream"

    def __init__(self, now_ns: int = NOW_NS, forming: int | None = None) -> None:
        self.now_ns, self.forming = now_ns, forming
        self.session = Session(
            "synthetic",
            (Endpoint("REST", "https://fakex.invalid", "products, candles, book, trades"),),
            Limits("10 requests a second", "5 a second", most_candles=300, history_days=0),
        )

    def listing(self) -> list[pairs.Listed]:
        return list(LISTED)

    def candles(self, product: str, first: date, last: date) -> list[pairs.Candle]:
        out = []
        if product in CLOSES and first <= CLOSED <= last:
            close = number(CLOSES[product])
            out.append(
                pairs.Candle(
                    product,
                    day_start(CLOSED),
                    close,
                    close,
                    close,
                    close,
                    number("12.5"),
                    raw_key=f"responses/candles/{product}",
                )
            )
        if product == "BTC-USD" and self.forming is not None and first <= TODAY <= last:
            close = number(FORMING[self.forming])
            out.append(
                pairs.Candle(
                    product,
                    day_start(TODAY),
                    close,
                    close,
                    close,
                    close,
                    number("1"),
                    raw_key=f"responses/candles/{product}#f",
                )
            )
        return out

    def last(self, product: str) -> pairs.Tick:
        return pairs.Tick(
            product,
            number(CLOSES[product]),
            self.now_ns,
            True,
            "t-1",
            raw_key=f"responses/ticker/{product}",
        )

    def top(self, product: str) -> pairs.Top:
        price = number(CLOSES[product])
        ask = None if product == "TKN-USD" else price
        return pairs.Top(
            product,
            price,
            ask,
            self.now_ns,
            True,
            raw_key=f"responses/book/{product}",
            bid_size=number("2"),
            ask_size=None if ask is None else number("3"),
        )

    def trades(self, product: str, since_ns: int = 0) -> list[pairs.Print]:
        if product != "BTC-USD":
            return []
        return [
            pairs.Print(
                product,
                number(price),
                number("0.01"),
                NOW_NS - (9000 - int(ident)) * SECOND,
                ident,
                "sell",
                pairs.MAKER,
                raw_key=f"responses/trades/{product}",
            )
            for ident, price in HISTORY
        ]

    async def connect(self, address: str) -> Replayed:
        return Replayed([])

    def subscriptions(self, names: Sequence[str]) -> list[str]:
        return [json.dumps({"subscribe": list(names)})]

    def heard(self, text: str, received_ns: int) -> list[pairs.Print | pairs.Top]:
        said = json.loads(text)
        if said["type"] == "trade":
            return [
                pairs.Print(
                    said["product"],
                    number(said["price"]),
                    number(said["size"]),
                    said["at"],
                    said["id"],
                    said["side"],
                    pairs.MAKER,
                    raw_key="responses/stream/trade#0",
                )
            ]
        return [
            pairs.Top(
                said["product"],
                number(said["bid"]),
                number(said["ask"]),
                said["at"],
                True,
                raw_key="responses/stream/top#0",
                bid_size=number(said["bid_size"]),
                ask_size=number(said["ask_size"]),
            )
        ]


pairs_venue = SimpleNamespace(
    VENUE="fakex",
    NOW_NS=NOW_NS,
    TODAY=TODAY,
    CLOSED=CLOSED,
    BASE="BTC",
    STABLE_BASE="BTC",
    EXACT_BASE="TKN",
    BAR_BASE="BTC",
    FX_BASE="",
    AMBIGUOUS="PLY",
    ONE_SIDED_BASE="TKN",
    SIDE_OF=pairs.MAKER,
    STREAM_CASES={
        "a-trade-recorded": MAKER_SELL,
        "the-makers-side-inverted": MAKER_SELL,
        "a-standing-want-streamed": MAKER_SELL,
        "a-quote-recorded": TOP,
    },
    RESTARTED=("BTC-USD", "8804", NOW_NS - 196 * SECOND),
    BACKFILLED=["8805", "8806"],
    NOT_PRESENTED={
        "an-fx-rate": "it lists no product between two currencies",
        "a-condition-converted": "it states no condition codes",
        "a-condition-not-converted": "it states no condition codes",
        "a-trade-withdrawn": "it never withdraws a trade",
        "the-takers-side-stated": "it names the resting order's side",
        "reads-a-calendar": "it reads no settlement calendar",
        "asks-for-a-settlement-date": "it never computes a settlement date",
        "records-an-outcome": "it lists no event contract",
        "restates-a-disputed-outcome": "it lists no event contract",
        "records-a-partial-payout": "it lists no event contract",
        "reports-an-event-group": "it lists no event contract",
        "reports-a-flag-the-venue-does-not-state": "it lists no event contract",
    },
    market=lambda now_ns=NOW_NS, forming=None: PairsMarket(now_ns, forming),
    STREAM=Keeper,
    replayed=Replayed,
)


# ── An event-contract venue ─────────────────────────────────────────────

CASH = ec.Cash("USD", "currency", "iso4217", "USD", "US dollar")
FUTURE, PAST = NOW_NS + 30 * 86_400 * SECOND, NOW_NS - 86_400 * SECOND


def _contract(code: str, **kw: Any) -> ec.Contract:
    held: dict[str, Any] = {
        "title": f"Will {code} happen?",
        "binary": True,
        "payout": number("1.0000"),
        "closes_at_ns": FUTURE,
        "raw_key": f"responses/2026-10-10/market/{code}.json",
        "read_at_ns": NOW_NS,
    }
    held.update(kw)
    return ec.Contract(code, **held)


class ContractsMarket:
    """The made-up event-contract venue: `stage` is the later answer it gives
    for the resolved contract (None, "disputed" or "final")."""

    venue = "fakev"
    name = "Fake Events"
    venue_identifiers = (("iso10383", "XFKE", ""),)
    cash = CASH

    def __init__(self, now_ns: int = NOW_NS, directory: Any = None) -> None:
        self.now_ns, self.stage = now_ns, directory
        self.session = Session(
            "synthetic",
            (Endpoint("REST", "https://fakev.invalid", "markets, books"),),
            Limits("20 requests a second", "5 a second"),
        )

    def _resolved(self) -> ec.Resolution:
        if self.stage == "disputed":
            return ec.Resolution(ec.DISPUTED, None)
        stage = ec.FINAL if self.stage == "final" else ec.DETERMINED
        return ec.Resolution(stage, number("1.0000"), "fakev:result", "yes", "Yes")

    def contract(self, code: str, watching: bool = False) -> ec.Contract | None:
        self.session.health.calls += 1
        if code in ("BASE-1", "EXACT-1", "ONE-SIDED-1"):
            return _contract(code)
        if code == "RANGE-1":
            return _contract(code, binary=False)
        if code == "RESOLVED-1":
            return _contract(
                code, closes_at_ns=PAST, tradable=False, resolution=self._resolved()
            )
        if code == "PARTIAL-1":
            resolution = ec.Resolution(
                ec.DETERMINED, number("0.4500"), "fakev:result", "scalar"
            )
            return _contract(code, closes_at_ns=PAST, tradable=False, resolution=resolution)
        return None

    def last(self, contract: ec.Contract) -> ec.Tick:
        price = {"EXACT-1": "0.123456789012345678", "ONE-SIDED-1": None}.get(
            contract.code, "0.43"
        )
        return ec.Tick(
            contract.code,
            number(price),
            self.now_ns,
            True,
            "",
            raw_key=f"responses/2026-10-10/last/{contract.code}.jsonl#0",
        )

    def top(self, contract: ec.Contract) -> ec.Top:
        ask = None if contract.code == "ONE-SIDED-1" else number("0.44")
        return ec.Top(
            contract.code,
            number("0.43"),
            ask,
            number("55"),
            None if ask is None else number("30"),
            self.now_ns,
            True,
            raw_key=f"responses/2026-10-10/book/{contract.code}.jsonl#0",
        )


contracts_venue = SimpleNamespace(
    VENUE="fakev",
    NOW_NS=NOW_NS,
    TODAY=TODAY,
    BASE="BASE-1",
    EXACT="EXACT-1",
    ONE_SIDED="ONE-SIDED-1",
    NOT_BINARY="RANGE-1",
    STABLE=False,
    DETERMINED="RESOLVED-1",
    DISPUTED=("RESOLVED-1", ("disputed",)),
    PARTIAL="PARTIAL-1",
    NOT_PRESENTED={
        "a-daily-close": "it publishes live prices and quotes, and no daily closes",
        "the-forming-day-restated": "it publishes no daily closes",
        "a-daily-bar": "it publishes no bars",
        "an-fx-rate": "it prices event contracts",
        "a-stablecoin-quote": "its prices are in US dollars",
        "a-subject-another-source-resolved": "its subjects are event contracts",
        "a-trade-recorded": "it publishes no trades",
        "the-makers-side-inverted": "it publishes no trades",
        "a-condition-converted": "it publishes no trades",
        "a-condition-not-converted": "it publishes no trades",
        "a-trade-withdrawn": "it publishes no trades",
        "a-standing-want-streamed": "it publishes no trades to stream",
        "the-takers-side-stated": "it publishes no trades",
        "a-restarts-gap-backfilled": "it publishes no trades, so no gap to read back",
        "reads-a-calendar": "it reads no settlement calendar",
        "asks-for-a-settlement-date": "an event contract settles on its outcome",
    },
    market=lambda now_ns=NOW_NS, directory=None: ContractsMarket(now_ns, directory),
    # Contract v26: the venue's events, as its conversion reads them.
    EVENT=ec.Event(
        ref="FAKEV-EVENT-1",
        title="Which of two",
        members=("BASE-1", "EXACT-1"),
        mutually_exclusive=True,
        exhaustive=True,
        raw_key="responses/2026-10-10/event/FAKEV-EVENT-1.jsonl#0",
    ),
    EVENT_PLACEHOLDERS=ec.Event(
        ref="FAKEV-EVENT-2",
        title="Which of two, and others named later",
        members=("BASE-1", "EXACT-1"),
        mutually_exclusive=True,
        exhaustive=None,
        raw_key="responses/2026-10-10/event/FAKEV-EVENT-2.jsonl#0",
    ),
)
