"""The data role's checks, run unchanged by each plugin against its own
conversion (0.30.0; sdk-contract/the-sdk-carries-each-roles-common-logic):
the lake as a test stands it in, the data suite's producers for a pairs venue
and an event-contract venue, and the checks a plugin built on
`meridian.roles.data.pairs` or `.event_contracts` runs -- the suite, the
venue's work past the suite's cases, and the pages.

A plugin's tests hold one module, `venue_cases`, naming its synthetic
exchanges for what each check asks a source to present, and one class:

    # tests/test_data_role.py
    import venue_cases
    from meridian.roles.data.testing import PairsChecks

    class TestPairs(PairsChecks):
        venue = venue_cases

Each check runs the plugin's real client, raw records and conversion against
the SDK's `Recorder` answering as the lake does (`Lake`), never a mock of the
plugin's own code. What the venue never states is named in its
`NOT_PRESENTED`, with why (meridian.suites).

**A pairs venue's `venue_cases`** names: `VENUE`, `NOW_NS`, `TODAY`,
`CLOSED`; the bases `BASE`, `STABLE_BASE`, `EXACT_BASE`, `BAR_BASE`,
`FX_BASE` (empty for none), `AMBIGUOUS`, `ONE_SIDED_BASE`; `FORMING_PRODUCT`
and `FORMING`; `LIVE_LAST`, `STABLE_PRODUCT`, `STABLE`, `DELISTED`,
`CLOSED_CLOSE`, `EXACT_CLOSE`; `SIDE_OF`, `STREAM_NAMES`, `STREAMED`, `GAP`,
`AGGRESSORS`, `TRADE_PRICE`, `TRADE_QUANTITY`, `LAST_QUOTES`, `STREAM_CASES`;
`NOT_PRESENTED`; `RESTARTED`, `BACKFILLED`; `market(now_ns, forming=None)`;
`STREAM`, its stream factory; `replayed(messages)`, a socket saying them and
dropping; `stream_sessions(feed)`, the messages of each synthetic connection;
`raw_store(feed)`, its client's `RawStore`; `CONVERSION`, its modules no
float may reach; and `page`, its page module (`pages`, `hold`,
`figures_now`, `TITLE`, `ENTITLED`).

**An event-contract venue's** names: `VENUE`, `NOW_NS`, `TODAY`; `BASE`,
`LAST`, `BID`, `BID_SIZE`, `ASK`, `ASK_SIZE`, `PAYOUT`, `CASH`, `EXACT`,
`EXACT_LAST`, `ONE_SIDED`, `NOT_BINARY`, `STABLE`; `RESOLVED`,
`RESOLVED_STAGE`, `WORD`, `RESOLVED_LOSER`, `PARTIAL`, `PARTIAL_VALUE`,
`PENDING`, `LATER`, `DETERMINED`, `DISPUTED`; `NOT_PRESENTED`;
`market(now_ns, directory=None)`; `calls(market)`, the URLs asked; and
`page` as above, with `datasets_now`. From 0.31.0 (contract v26) also
`EVENT` and `EVENT_PLACEHOLDERS`, two of the venue's events as its
conversion reads them (`event_contracts.Event`): one whose members the
venue states mutually exclusive and exhaustive, and one adding outcomes
named later, which states no exhaustiveness. A venue whose module names
neither leaves `reports-an-event-group` and
`reports-a-flag-the-venue-does-not-state` to its own producers or to
`NOT_PRESENTED`, with why.

Every data plugin's suite holds `queries-the-lake-within-bounds` from
contract v26: one bounded query of a kind its role reads
(`lake_query(subject)` is the producer both venues' checks use).
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import re
import sys
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from ...errors import MeridianError, NotGranted
from ...operations import Money, SubjectRef, as_decimal, as_money
from ...plugin.v1 import operations_pb2 as ops
from ...suites import ANSWERED_BY_SDK, Recorder, names, run, suite
from ...testing import PageClient
from . import event_contracts, pairs
from ._wants import Standing

__all__ = [
    "BITCOIN",
    "OTHER",
    "EVENT_CONTRACTS_NOT_PRESENTED",
    "EventContractsChecks",
    "Instruments",
    "Lake",
    "PAIRS_NOT_PRESENTED",
    "PairsChecks",
    "event_contract_producers",
    "feed_delay",
    "held",
    "lake_query",
    "hear",
    "pairs_producers",
    "payout",
    "RATES_CASES",
    "RATES_NOT_PRESENTED",
    "rates_producers",
    "wanted",
]

Producer = Callable[[Recorder], Awaitable[None]]

PRICE, BAR = "meridian.v1.Price", "meridian.v1.Bar"
TRADE, QUOTE = "meridian.v1.Trade", "meridian.v1.Quote"
TOOLS = {"read_connection": "/", "read_datasets": "/datasets"}

#: Another source the deployment holds records from: a custodian's book.
OTHER = "custodian"
#: Bitcoin's CAIP-19, by its SLIP-44 coin type: the global identifier a
#: custodian's record may carry beside its own symbol, as an equity's carries
#: a CUSIP.
BITCOIN = "bip122:000000000019d6689c085ae165831e93/slip44:0"


def _same(one: Any, other: Any) -> bool:
    return bool(
        (one.scheme, one.value, one.source) == (other.scheme, other.value, other.source)
    )


def payout(
    amount: str, currency_code: str = "", instrument_id: str = ""
) -> ops.BinaryEventContract:
    """A binary event contract's attributes as a record states them: its
    payout, a Money naming its cash instrument by code or by record."""
    sign, digits, exponent = Decimal(amount).as_tuple()
    integer = int("".join(map(str, digits))) * (-1 if sign else 1)
    scale = -int(exponent) if int(exponent) < 0 else 0
    wire = ops.Decimal(high=integer >> 64, low=integer & (2**64 - 1), scale=scale)
    money = ops.Money(amount=wire, currency_code=currency_code, instrument_id=instrument_id)
    return ops.BinaryEventContract(payout=money)


class Instruments:
    """The deployment's instrument store as the tests hold it. ResolveInstrument
    reads a record by its ID (W3.6); ResolveIdentifier answers the one record
    the identifiers meet, the others joined to it and what it states offered,
    a record minted where they meet none, and ambiguous where they meet two
    (W3.1)."""

    def __init__(self) -> None:
        self.records: dict[str, list[ops.Identifier]] = {}
        self.classes: dict[str, int] = {}
        self.types: dict[str, int] = {}
        self.payouts: dict[str, ops.BinaryEventContract] = {}
        #: What each resolve offered, by the record it met: (class, type,
        #: description).
        self.offered: dict[str, tuple[int, int, str]] = {}

    def hold(
        self,
        instrument_id: str,
        *identifiers: ops.Identifier,
        asset_class: int = 0,
        instrument_type: int = 0,
        attributes: ops.BinaryEventContract | None = None,
    ) -> str:
        self.records[instrument_id] = list(identifiers)
        self.classes[instrument_id] = asset_class
        self.types[instrument_id] = instrument_type
        if attributes is not None:
            self.payouts[instrument_id] = attributes
        return instrument_id

    def read(self, params: Any) -> Any:
        held = self.records.get(params.instrument_id)
        if held is None:
            return ops.ResolveInstrumentResult(found=False)
        record = ops.InstrumentRecord(
            instrument_id=params.instrument_id,
            identifiers=held,
            asset_class=self.classes.get(params.instrument_id, 0),  # type: ignore[arg-type]
            instrument_type=self.types.get(params.instrument_id, 0),  # type: ignore[arg-type]
        )
        if params.instrument_id in self.payouts:
            record.binary_event_contract.CopyFrom(self.payouts[params.instrument_id])
        return ops.ResolveInstrumentResult(found=True, instrument=record)

    def resolve(self, params: Any) -> Any:
        given = list(params.identifiers)
        offer = (params.stated_asset_class, params.stated_instrument_type,
                 params.stated_description)  # fmt: skip
        met = [key for key, held in self.records.items()
               if any(_same(g, h) for g in given for h in held)]  # fmt: skip
        if len(met) > 1:
            return ops.ResolveIdentifierResult(
                found=False, miss_reason=ops.MISS_REASON_AMBIGUOUS
            )
        if met:
            held = self.records[met[0]]
            held.extend(g for g in given if not any(_same(g, h) for h in held))
            self.offered[met[0]] = offer
            return ops.ResolveIdentifierResult(found=True, instrument_id=met[0])
        minted = self.hold(f"LCL-{given[0].value[:24]}", *given)
        self.offered[minted] = offer
        return ops.ResolveIdentifierResult(found=True, instrument_id=minted, minted=True)

    def answering(self, recorder: Recorder) -> Instruments:
        recorder.answer("ResolveIdentifier", self.resolve)
        recorder.answer("ResolveInstrument", self.read)
        return self


async def held(store: Instruments, feed: Any, code: str, **kw: Any) -> str:
    """A record the deployment holds for one of the venue's assets or
    contracts, carrying the identifiers the venue's own statements give it,
    as a record resolved or completed from this venue would."""
    if isinstance(feed, pairs.Feed):
        await feed.ensure_mapped()
        asset = feed.products.asset(code)
        assert asset is not None, f"the venue trades no {code}"
        return store.hold(f"INS-{code}", *feed.identifiers(asset), **kw)
    contract = await feed.contract(code)
    assert contract is not None, f"the venue states no contract {code}"
    return store.hold(f"INS-{code[-12:]}", *feed.identifiers(contract), **kw)


_RESULTS: dict[str, Any] = {
    "price": ops.RecordPricesResult,
    "bar": ops.RecordBarsResult,
    "trade": ops.RecordTradesResult,
    "quote": ops.RecordQuotesResult,
    "outcome": ops.RecordOutcomesResult,
    "rate": ops.RecordRatesResult,
}
_FIELDS = {"RecordPrices": "prices", "RecordBars": "bars", "RecordTrades": "trades",
           "RecordQuotes": "quotes", "RecordOutcomes": "outcomes",
           "RecordRates": "rates"}  # fmt: skip


class Lake(Recorder):
    """The SDK's recorder, answering a batch as the lake does: a row key new is
    recorded, the same values again unchanged (by decimal value: 0.43 is
    0.4300), a changed value the next version; and resolving from its own
    instrument store (`instruments`)."""

    def __init__(self, instance_id: str = "data", **kw: Any) -> None:
        super().__init__(instance_id, **kw)
        self.versions: dict[tuple[str, str], tuple[int, tuple[Any, ...]]] = {}
        self.instruments = Instruments().answering(self)
        for row, kind in (("RecordPrices", "price"), ("RecordBars", "bar"),
                          ("RecordTrades", "trade"), ("RecordQuotes", "quote"),
                          ("RecordOutcomes", "outcome"), ("RecordRates", "rate")):  # fmt: skip
            self.answer(row, self._recording(row, kind))

    def _recording(self, row: str, kind: str) -> Callable[[Any], Any]:
        def recorded(params: Any) -> Any:
            return self._record(getattr(params, _FIELDS[row]), kind)

        return recorded

    def on(self, row: str) -> list[Any]:
        return list(super().on(row))

    @staticmethod
    def _values(row: Any, kind: str) -> tuple[Any, ...]:
        def amount(name: str) -> Any:
            return as_decimal(getattr(row, name).amount) if row.HasField(name) else None

        if kind == "price":
            return (as_decimal(row.price.amount),)
        if kind == "trade":
            return (as_decimal(row.price.amount), as_decimal(row.quantity), row.cancelled)
        if kind == "bar":
            return tuple(amount(f) for f in ("open", "high", "low", "close")) + (
                as_decimal(row.volume),
            )
        if kind == "rate":
            return (as_decimal(row.value.value), row.value.unit, row.preliminary)
        if kind == "outcome":
            return (row.determination, row.stage, as_decimal(row.settlement_value.amount),
                    row.settled_at_ns, row.determination_as_reported.code)  # fmt: skip
        return tuple(amount(f) for f in ("bid", "ask")) + tuple(
            as_decimal(getattr(row, f)) if row.HasField(f) else None
            for f in ("bid_quantity", "ask_quantity")
        )

    def _record(self, rows: Any, kind: str) -> Any:
        recorded = restated = unchanged = 0
        for row in rows:
            values = self._values(row, kind)
            key = (kind, row.meta.row_key)
            was = self.versions.get(key)
            if was is None:
                self.versions[key] = (1, values)
                recorded += 1
            elif was[1] == values:
                unchanged += 1
            else:
                self.versions[key] = (was[0] + 1, values)
                restated += 1
        return _RESULTS[kind](recorded=recorded, restated=restated, unchanged=unchanged)

    def rows(self, row: str = "RecordPrices") -> list[Any]:
        """Every row sent by one operation, in the order sent."""
        return [r for params in self.on(row) for r in getattr(params, _FIELDS[row])]

    async def held(self, feed: Any, code: str, **kw: Any) -> str:
        return await held(self.instruments, feed, code, **kw)


def wanted(
    feed: Any,
    want_id: str,
    key: str,
    subjects: list[str],
    *,
    data_type: str = PRICE,
    kinds: tuple[Any, ...] = (),
    day: date | None = None,
    standing: bool = False,
) -> ops.ObservationsWantedEvent:
    """A want as the lake sends one: for a business date, or the latest."""
    return ops.ObservationsWantedEvent(
        want_id=want_id,
        dataset=feed.dataset(key),
        data_type=data_type,
        kinds=list(kinds),
        subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
        business_date=day.isoformat() if day else "",
        standing=standing,
    )


async def hear(recorder: Recorder, feed: Any, event: ops.ObservationsWantedEvent) -> None:
    """The want delivered to the plugin's own handler, through its receive."""
    recorder.answer("ObservationsWanted", lambda _: event)
    await recorder.receive(observations_wanted=feed.on_want)


def _pairs_feed(
    venue: Any, recorder: Recorder, market: Any = None, now_ns: int | None = None, **kw: Any
) -> pairs.Feed:
    at = venue.NOW_NS if now_ns is None else now_ns
    return pairs.Feed(
        recorder,
        market or venue.market(at, **kw),
        pairs.ProductMap(),
        clock_ns=lambda: at,
        stream_factory=venue.STREAM,
    )


def _contracts_feed(venue: Any, recorder: Recorder, **kw: Any) -> event_contracts.Feed:
    return event_contracts.Feed(
        recorder, venue.market(venue.NOW_NS, **kw), event_contracts.ContractMap(),
        clock_ns=lambda: venue.NOW_NS,
    )  # fmt: skip


def _mutated(feed: Any, mutations: dict[str, Any]) -> Any:
    for name, mutated in mutations.items():
        setattr(feed, name, mutated.__get__(feed))
    return feed


# ── The data suite's producers ──────────────────────────────────────────


def lake_query(subject: str, kind: str = "prices") -> Producer:
    """`queries-the-lake-within-bounds` (contract v26, W10.10): one bounded
    query of a kind the role reads, naming the field it wants by its
    dictionary entry and a row limit."""

    async def produce(recorder: Recorder) -> None:
        await recorder.query_lake(
            kind=kind,
            subjects=[SubjectRef(entity_id=subject)],
            fields=["meridian.v1.Price.price"],
            row_limit=100,
        )

    return produce


def feed_delay(record: Callable[[Recorder, Any], Awaitable[None]]) -> Producer:
    """`reports-its-feed-delay` (W4.16; required from contract v28, ruling
    518): the plugin's own conversion run with a `roles.Latency` on its
    `Wants` -- `record(recorder, latency)` sets `wants.latency` and records
    rows that carry a source time -- then the interval's snapshots sent by
    `Latency.report`, the `edge` hop's age among them (0.33.0 sends
    ReportLatency; rulings 515 and 516)."""

    async def produce(recorder: Recorder) -> None:
        from .._latency import Latency

        latency = Latency(recorder)
        await record(recorder, latency)
        await latency.report()

    return produce


#: The cases a kind of venue never presents unless its module maps them
#: (contract v27): a pairs or event-contract venue publishes no rates; an
#: event-contract venue polls rather than streams, and records no trades;
#: and from contract v28 neither lists option chains or publishes filings,
#: and a polled venue numbers no message (ruling 602).
_RATES = (
    "a-rate-fixing",
    "a-same-day-revision",
    "a-curve-for-a-date",
    "a-tenor-not-published",
    "two-conventions-one-tenor",
    "an-index-level",
    "a-curve-point-from-another-source",
)
#: The data suite's cases contract v28 adds about kinds a venue's listing
#: or a publisher's feed may never present (ruling 602): option chains, and
#: the filings slice's filings, holdings, corporate actions and ratings.
_CHAINS = ("records-a-chains-series", "records-open-interest", "a-chain-row-is-never-resolved")
_FILINGS = (
    "a-filing-recorded", "a-fact-restated", "a-fact-confirmed", "resolves-a-filer",
    "a-complete-holdings-report", "a-cusip-used-as-key", "a-stake-crossed",
    "a-dividend-declared", "a-rating-action",
)  # fmt: skip
#: Its quality cases about `quotes` (ruling 602, amended): judged by the
#: edge's checks (`quality.EdgeChecks`) on the quotes a plugin records.
_QUALITY = (
    "a-crossed-quote-is-recorded-invalid",
    "a-duplicate-is-recorded-suspicious",
    "rows-after-a-gap-are-suspicious",
)
#: What no venue listing pairs or event contracts publishes (contract v28).
_NO_CHAINS_OR_FILINGS = {
    **{case: "it lists no option chains" for case in _CHAINS},
    **{case: "it publishes no filings" for case in _FILINGS},
}
PAIRS_NOT_PRESENTED = {
    **{case: "a pairs venue publishes no rates" for case in _RATES},
    **_NO_CHAINS_OR_FILINGS,
}
EVENT_CONTRACTS_NOT_PRESENTED = {
    **{case: "an event-contract venue publishes no rates" for case in _RATES},
    "records-a-datasets-liveness": "it polls its venue each second; it streams nothing",
    "queries-the-lake-within-bounds": "it records no trades",
    **_NO_CHAINS_OR_FILINGS,
    "a-duplicate-is-recorded-suspicious": "its quotes are polled; no message is numbered",
    "rows-after-a-gap-are-suspicious": "its quotes are polled; no message is numbered",
}
#: Why a rates-only plugin never presents a case about prices (ruling 537).
_NO_PRICES = "it records rates, never prices"
#: What a plugin recording only rates never presents (0.32.1; ruling 537):
#: every data case about a price -- `an-exact-price` and
#: `a-want-recorded-against` about `closes` from contract v27's ruling 537 --
#: a trade, a quote or an outcome; and from contract v28 the chains, the
#: filings slice and the quality of quotes (ruling 602). A plugin maps what
#: its publisher does present -- rates, wants and its feed delay among
#: them. From 0.32.2 `records-a-datasets-liveness` is not listed: a polled
#: plugin recording each poll as its dataset's liveness presents it; one
#: recording none names it itself, with why.
RATES_NOT_PRESENTED = {
    **{
        case: _NO_PRICES
        for case in (
            "a-daily-close",
            "the-forming-day-restated",
            "an-exact-price",
            "a-daily-bar",
            "an-fx-rate",
            "a-stablecoin-quote",
            "a-venue-resolved",
            "a-venue-not-held",
            "a-want-recorded-against",
            "a-subject-another-source-resolved",
        )
    },
    **{
        case: "it records rates, never trades"
        for case in (
            "a-trade-recorded",
            "the-takers-side-stated",
            "the-makers-side-inverted",
            "a-condition-converted",
            "a-condition-not-converted",
            "a-trade-withdrawn",
            "a-standing-want-streamed",
            "a-restarts-gap-backfilled",
            "queries-the-lake-within-bounds",
        )
    },
    "a-quote-recorded": "it records rates, never quotes",
    "a-one-sided-quote": "it records rates, never quotes",
    **{
        case: "it records rates, never an event contract's outcome"
        for case in (
            "records-an-outcome",
            "restates-a-disputed-outcome",
            "records-a-partial-payout",
            "reports-an-event-group",
            "reports-a-flag-the-venue-does-not-state",
        )
    },
    **_NO_CHAINS_OR_FILINGS,
    **{case: "it records rates, never quotes" for case in _QUALITY},
}


#: The rates cases of the data suite (contract v27), each about `rates`.
RATES_CASES = _RATES


def rates_producers(
    cases: Mapping[str, Callable[[Any, Instruments], Awaitable[None]]],
    *,
    source: str,
    now_ns: int = 0,
    day_zone: str = "UTC",
) -> dict[str, Producer]:
    """The data suite's rates cases (contract v27; ruling 345) for a plugin
    built on `meridian.roles.data.rates`: each case its own conversion of
    its publisher's recorded answer for the case, given a `rates.Feed` over
    the lake as a test stands it in (`Lake`, which records a row key's
    next version as a restatement) and the instrument store resolving its
    subjects (`Instruments`, where it holds the curves and rates as
    referential records). `cases` maps a case's name to
    `async def case(feed, instruments)`; a case the publisher never
    presents is named in the plugin's `NOT_PRESENTED`, with why."""
    from . import rates

    unknown = sorted(set(cases) - set(RATES_CASES))
    if unknown:
        raise ValueError(f"{unknown} are not the data suite's rates cases {RATES_CASES}")

    def made(case: Callable[[Any, Instruments], Awaitable[None]]) -> Producer:
        async def produce(recorder: Recorder) -> None:
            store = Instruments().answering(recorder)
            feed = rates.Feed(
                recorder,
                source,
                day_zone=day_zone,
                clock_ns=(lambda: now_ns) if now_ns else time.time_ns,
            )
            await case(feed, store)

        return produce

    return {name: made(case) for name, case in cases.items()}


def pairs_producers(venue: Any, **mutations: Any) -> dict[str, Producer]:
    """Each data-suite case's producer for a pairs venue: the plugin's own
    steps on its own exchange; `mutations` replace a `Feed` method, to prove
    the suite fails a plugin doing the wrong thing."""

    def made_on(recorder: Recorder, **kw: Any) -> tuple[pairs.Feed, Instruments]:
        store = Instruments().answering(recorder)
        return _pairs_feed(venue, recorder, **kw), store

    def want(want_id: str, dataset: str, subjects: list[str], day: date) -> Any:
        return ops.ObservationsWantedEvent(
            want_id=want_id, dataset=dataset, data_type=PRICE,
            subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
            kinds=[ops.PRICE_KIND_CLOSE], business_date=day.isoformat(),
        )  # fmt: skip

    def daily(code: str, data_type: str = "", **kw: Any) -> Producer:
        async def produce(recorder: Recorder) -> None:
            feed, store = made_on(recorder, **kw)
            _mutated(feed, mutations)
            subject = await held(store, feed, code)
            await feed.record_days([subject], venue.CLOSED, venue.CLOSED, data_type)

        return produce

    async def forming(recorder: Recorder) -> None:
        for read in (0, 1):
            feed, store = made_on(recorder, market=venue.market(venue.NOW_NS, forming=read))
            subject = await held(store, feed, venue.BASE)
            await feed.record_days([subject], venue.TODAY, venue.TODAY, PRICE)

    async def ambiguous(recorder: Recorder) -> None:
        # A custodian's record by its own symbol, which is the venue's code,
        # and another record already carrying the venue's: the two meet.
        feed, store = made_on(recorder)
        await held(store, feed, venue.AMBIGUOUS)
        subject = store.hold("INS-HELD", ops.Identifier(scheme="symbol",
                             value=venue.AMBIGUOUS, source=OTHER))  # fmt: skip
        await feed.record_days([subject], venue.CLOSED, venue.CLOSED, PRICE)

    async def venue_not_held(recorder: Recorder) -> None:
        recorder.answer(
            "ResolveVenue",
            lambda _: ops.ResolveVenueResult(
                found=False, miss_reason=ops.MISS_REASON_NOT_FOUND
            ),
        )
        await made_on(recorder)[0].venue_id()

    def covered(yes: bool) -> Producer:
        async def produce(recorder: Recorder) -> None:
            feed, store = made_on(recorder)
            subject = await held(store, feed, venue.BASE) if yes else "LCL-NOT-COVERED"
            event = want("WNT-1", feed.dataset(pairs.DAILY), [subject], venue.CLOSED)
            await hear(recorder, feed, event)

        return produce

    async def elsewhere(recorder: Recorder) -> None:
        # Bitcoin as a custodian's book holds it, by its global identifier
        # and the custodian's symbol, never resolved by this venue: the
        # record read (W3.6), the venue's asset named from it.
        feed, store = made_on(recorder)
        subject = store.hold(
            "INS-HELD",
            ops.Identifier(scheme="caip19", value=BITCOIN),
            ops.Identifier(scheme="symbol", value="BTC", source=OTHER),
        )
        await hear(recorder, feed, want("WNT-3", feed.dataset(pairs.DAILY), [subject],
                                        venue.CLOSED))  # fmt: skip

    async def withdrawn(recorder: Recorder) -> None:
        feed, store = made_on(recorder)
        subject = await held(store, feed, venue.BASE)
        feed.standing["WNT-2"] = Standing(
            "WNT-2", feed.dataset(pairs.LIVE), PRICE, (subject,), (ops.PRICE_KIND_LAST,),
            venue.NOW_NS,
        )  # fmt: skip
        recorder.answer(
            "WantWithdrawn",
            lambda _: [
                ops.WantWithdrawnEvent(want_id="WNT-2", dataset=feed.dataset(pairs.LIVE))
            ],
        )
        await recorder.receive(want_withdrawn=feed.on_withdrawn)
        await feed.current(daily=True)  # one pass keeping current: nothing stands now

    async def stream_on(
        recorder: Recorder, key: str, data_type: str, messages: Any, latency: Any = None
    ) -> None:
        # A standing want of a streamed dataset for BASE, then the venue's
        # stream stating the case's message, replayed through the plugin's
        # stream, which drops once it is said. From contract v28 a case may
        # state several (a duplicate, a gap): the first opens the stream,
        # the rest are heard on the same connection, each on its own pass.
        feed, store = made_on(recorder)
        _mutated(feed, mutations)
        if latency is not None:
            feed.wants.latency = latency
        subject = await held(store, feed, venue.BASE)
        event = ops.ObservationsWantedEvent(
            want_id="WNT-S", dataset=feed.dataset(key), data_type=data_type,
            subjects=[ops.SubjectRef(entity_id=subject)], standing=True,
        )  # fmt: skip
        await hear(recorder, feed, event)
        first, *rest = [messages] if isinstance(messages, str) else list(messages)

        async def said(_: str) -> Any:
            return venue.replayed([first])

        feed.stream.retarget(feed.market.stream_address, said, feed.market.subscriptions)
        await feed.stream.run(once=True)
        await feed.flush()
        for message in rest:
            await feed.on_message(message)
            await feed.flush()

    def streamed(messages: Any, key: str, data_type: str) -> Producer:
        async def produce(recorder: Recorder) -> None:
            await stream_on(recorder, key, data_type, messages)

        return produce

    def timed(messages: Any, key: str, data_type: str) -> Producer:
        # Its feed delay: the streamed rows' age at the edge, then reported.
        async def record(recorder: Recorder, latency: Any) -> None:
            await stream_on(recorder, key, data_type, messages, latency)

        return feed_delay(record)

    async def one_sided(recorder: Recorder) -> None:
        feed, store = made_on(recorder)
        _mutated(feed, mutations)
        subject = await held(store, feed, venue.ONE_SIDED_BASE)
        await feed.record_quotes([subject])

    async def restarted(recorder: Recorder) -> None:
        # The plugin started again: the lake holds the last trade this
        # instance recorded of BASE's product before it stopped, and the
        # venue's history states more since. The standing want of the trades
        # dataset, heard again, reads the gap back before streaming.
        feed, store = made_on(recorder)
        subject = await held(store, feed, venue.BASE)
        product, ident, at_ns = venue.RESTARTED
        last = ops.Trade(meta=ops.ObservationMeta(
            row_key=f"{product}:t:{ident}", subjects=[ops.SubjectRef(entity_id=subject)],
            source=ops.Source(dataset=feed.dataset(pairs.TRADES)), valid_from_ns=at_ns,
        ))  # fmt: skip
        recorder.answer("ListTrades", lambda _: ops.ListTradesResult(trades=[last]))
        event = ops.ObservationsWantedEvent(
            want_id="WNT-S", dataset=feed.dataset(pairs.TRADES), data_type=TRADE,
            subjects=[ops.SubjectRef(entity_id=subject)], standing=True,
        )  # fmt: skip
        await hear(recorder, feed, event)

    async def licences(recorder: Recorder) -> None:
        # A deployment admin has licensed the daily dataset and not the others.
        feed, _ = made_on(recorder)
        daily = ops.DatasetLicence(dataset=feed.dataset(pairs.DAILY), kept=True)
        recorder.answer("ListDatasets", lambda _: ops.ListDatasetsResult(licences=[daily]))
        await feed.read_licences()

    made: dict[str, Producer] = {
        "a-daily-close": daily(venue.BASE, PRICE),
        "the-forming-day-restated": forming,
        "an-exact-price": daily(venue.EXACT_BASE, PRICE),
        "a-daily-bar": daily(venue.BAR_BASE, BAR),
        "a-stablecoin-quote": daily(venue.STABLE_BASE, PRICE),
        "an-asset-that-does-not-resolve": ambiguous,
        "a-venue-resolved": daily(venue.BASE, PRICE),
        "a-venue-not-held": venue_not_held,
        "a-want-recorded-against": covered(True),
        "a-subject-another-source-resolved": elsewhere,
        "a-subject-declined": covered(False),
        "a-standing-want-withdrawn": withdrawn,
        "a-one-sided-quote": one_sided,
        "a-restarts-gap-backfilled": restarted,
        "reads-its-datasets-licences": licences,
        "queries-the-lake-within-bounds": lake_query("INS-suite-1"),
    }
    if venue.FX_BASE:
        made["an-fx-rate"] = daily(venue.FX_BASE, PRICE)
    for case, message in venue.STREAM_CASES.items():
        key, data_type = (
            (pairs.LIVE, QUOTE)
            if case == "a-quote-recorded" or case in _QUALITY
            else (pairs.TRADES, TRADE)
        )
        made[case] = streamed(message, key, data_type)
    # Contract v28 (ruling 518): its feed delay, the streamed quote's age at
    # the edge reported; else a streamed trade's.
    timed_on = [c for c in ("a-quote-recorded", "a-trade-recorded") if c in venue.STREAM_CASES]
    if timed_on:
        quoted = timed_on[0] == "a-quote-recorded"
        made["reports-its-feed-delay"] = timed(
            venue.STREAM_CASES[timed_on[0]],
            pairs.LIVE if quoted else pairs.TRADES,
            QUOTE if quoted else TRADE,
        )
    # Contract v27: a quote streamed is the stream's sign of life, recorded
    # as the live dataset's liveness; a trade streamed, its age at the edge.
    if "a-quote-recorded" in venue.STREAM_CASES:
        made["records-a-datasets-liveness"] = streamed(
            venue.STREAM_CASES["a-quote-recorded"], pairs.LIVE, QUOTE
        )
    skipped = {**PAIRS_NOT_PRESENTED, **venue.NOT_PRESENTED}
    return {case: produce for case, produce in made.items() if case not in skipped}


def event_contract_producers(venue: Any, **mutations: Any) -> dict[str, Producer]:
    """Each data-suite case's producer for an event-contract venue: the
    plugin's own steps on its own exchange; `mutations` replace a `Feed`
    method, to prove the suite fails a plugin doing the wrong thing."""

    def made_on(recorder: Recorder, mutate: bool = False) -> tuple[Any, Instruments]:
        store = Instruments().answering(recorder)
        feed = _contracts_feed(venue, recorder)
        return (_mutated(feed, mutations) if mutate else feed), store

    def live(code: str, data_type: str) -> Producer:
        async def produce(recorder: Recorder) -> None:
            feed, store = made_on(recorder, mutate=True)
            subject = await held(store, feed, code)
            await feed.record_live([subject], data_type=data_type)

        return produce

    async def ambiguous(recorder: Recorder) -> None:
        # Two records already carry the venue's cash's identifiers: the cash
        # its prices are in meets both, and nothing is priced in it.
        feed, store = made_on(recorder)
        for n in (1, 2):
            store.hold(f"INS-CASH-{n}", *feed.cash_identifiers())
        subject = await held(store, feed, venue.BASE)
        await feed.record_live([subject], data_type=PRICE)

    async def venue_not_held(recorder: Recorder) -> None:
        recorder.answer(
            "ResolveVenue",
            lambda _: ops.ResolveVenueResult(
                found=False, miss_reason=ops.MISS_REASON_NOT_FOUND
            ),
        )
        await made_on(recorder)[0].venue_id()

    def covered(yes: bool) -> Producer:
        async def produce(recorder: Recorder) -> None:
            feed, store = made_on(recorder)
            subject = await held(store, feed, venue.BASE) if yes else "LCL-NOT-COVERED"
            await hear(recorder, feed, wanted(feed, "WNT-1", event_contracts.LIVE, [subject]))

        return produce

    async def withdrawn(recorder: Recorder) -> None:
        feed, store = made_on(recorder)
        subject = await held(store, feed, venue.BASE)
        feed.standing["WNT-2"] = Standing(
            "WNT-2", feed.dataset(event_contracts.LIVE), PRICE, (subject,),
            (ops.PRICE_KIND_LAST,), venue.NOW_NS,
        )  # fmt: skip
        recorder.answer("WantWithdrawn", lambda _: [ops.WantWithdrawnEvent(
            want_id="WNT-2", dataset=feed.dataset(event_contracts.LIVE))])  # fmt: skip
        await recorder.receive(want_withdrawn=feed.on_withdrawn)
        await feed.current()  # one pass keeping current: nothing stands now

    def outcome(code: str | None, later: tuple[Path, ...] = ()) -> Producer | None:
        # Contract v23: a contract the venue has determined, named for a
        # subject, its outcome recorded; then each later answer of the venue
        # for it, read again as a contract past its close is.
        if code is None:
            return None

        async def produce(recorder: Recorder) -> None:
            feed, store = made_on(recorder, mutate=True)
            subject = await held(store, feed, code)
            await feed.name([subject])
            await feed.record_outcomes([feed.contracts.serving(subject)])
            for directory in later:
                feed.market = venue.market(venue.NOW_NS, directory=directory)
                await feed.watch_outcomes()

        return produce

    async def licences(recorder: Recorder) -> None:
        # On start (contract v20): a deployment admin has licensed its live
        # dataset, and another plugin's dataset is no concern of this one's.
        feed, _ = made_on(recorder)
        recorder.answer("ListDatasets", lambda _: ops.ListDatasetsResult(licences=[
            ops.DatasetLicence(dataset=feed.dataset(event_contracts.LIVE)),
            ops.DatasetLicence(dataset="another-1:live"),
        ]))  # fmt: skip
        assert await feed.read_licences() == frozenset({feed.dataset(event_contracts.LIVE)})

    made: dict[str, Producer] = {
        "an-exact-price": live(venue.EXACT, PRICE),
        "a-stablecoin-quote": live(venue.BASE, PRICE),
        "an-asset-that-does-not-resolve": ambiguous,
        "a-venue-resolved": live(venue.BASE, PRICE),
        "a-venue-not-held": venue_not_held,
        "a-want-recorded-against": covered(True),
        "a-subject-declined": covered(False),
        "a-standing-want-withdrawn": withdrawn,
        "a-quote-recorded": live(venue.BASE, QUOTE),
        "a-one-sided-quote": live(venue.ONE_SIDED, QUOTE),
        "reads-its-datasets-licences": licences,
    }
    # Contract v28 (ruling 424): a contract the venue quotes crossed, where
    # its module names one (`CROSSED`), recorded invalid by the edge.
    if getattr(venue, "CROSSED", None):
        made["a-crossed-quote-is-recorded-invalid"] = live(venue.CROSSED, QUOTE)

    async def timed(recorder: Recorder, latency: Any) -> None:
        # Its feed delay (required from contract v28, ruling 518): a standing
        # want's subject kept current, its rows' age at the edge recorded.
        feed, store = made_on(recorder, mutate=True)
        feed.wants.latency = latency
        subject = await held(store, feed, venue.BASE)
        feed.standing["WNT-T"] = Standing(
            "WNT-T", feed.dataset(event_contracts.LIVE), PRICE, (subject,),
            (ops.PRICE_KIND_LAST,), venue.NOW_NS,
        )  # fmt: skip
        await feed.current()

    made["reports-its-feed-delay"] = feed_delay(timed)

    def grouped(event: Any) -> Producer | None:
        # Contract v26 (W3.29): the venue's event, as its conversion read
        # it, its members resolved and the grouping reported as stated.
        if event is None:
            return None

        async def produce(recorder: Recorder) -> None:
            feed, store = made_on(recorder, mutate=True)
            for code in event.members:
                await held(store, feed, code)
            answer = await feed.report_event(event)
            if answer is None:
                raise AssertionError(f"the event {event.ref} was held back")

        return produce

    groups = {
        "reports-an-event-group": grouped(getattr(venue, "EVENT", None)),
        "reports-a-flag-the-venue-does-not-state": grouped(
            getattr(venue, "EVENT_PLACEHOLDERS", None)
        ),
    }
    made.update({name: each for name, each in groups.items() if each is not None})
    outcomes = {
        "records-an-outcome": outcome(venue.DETERMINED),
        "restates-a-disputed-outcome": outcome(*venue.DISPUTED) if venue.DISPUTED else None,
        "records-a-partial-payout": outcome(venue.PARTIAL),
    }
    made.update({name: each for name, each in outcomes.items() if each is not None})
    skipped = {**EVENT_CONTRACTS_NOT_PRESENTED, **venue.NOT_PRESENTED}
    return {name: made[name] for name in made if name not in skipped}


# ── What every data plugin's pages hold ─────────────────────────────────


def _sections(text: str) -> list[str]:
    return re.findall(r"<h2>([^<]*)</h2>", text)


class _PageChecks:
    """The checks every one-venue data plugin's two pages pass, after it has
    answered wants on its synthetic exchange (`worked`)."""

    venue: Any

    async def worked(self) -> tuple[Any, Lake]:
        raise NotImplementedError

    def ran(self) -> tuple[Any, Lake]:
        """`worked`, run in a loop of its own: a page is asked as the sidecar
        asks it, outside any loop (`meridian.testing.PageClient`)."""
        return asyncio.run(self.worked())

    def shown(self, lake: Lake) -> set[str]:
        """Every figure the plugin recorded that a page must never show."""
        raise NotImplementedError

    def test_each_page_is_served_under_manage_alone(self) -> None:
        self.ran()
        client = PageClient(self.venue.page.pages)
        served = {(r.page.path, r.level): r.response.status for r in client.every_page()}
        assert {path for path, _ in served} == {"/", "/datasets"}
        for (_, level), status in served.items():
            assert status == (200 if level == "admin" else 403), (level, status)

    def test_no_page_shows_a_recorded_figure(self) -> None:
        _, lake = self.ran()
        figures = self.shown(lake)
        assert figures, "the plugin recorded figures for the pages to leave out"
        for path in TOOLS.values():
            text = PageClient(self.venue.page.pages).get(path, "admin").text
            shown = [
                p for p in figures if re.search(rf"(?<![\d.]){re.escape(p)}(?![\d.])", text)
            ]
            assert not shown, (path, shown)

    def test_every_table_is_one_line_rows(self) -> None:
        self.ran()
        for path in TOOLS.values():
            text = PageClient(self.venue.page.pages).get(path, "admin").text
            tables = re.findall(r"<table[^>]*>", text)
            assert tables and all('class="one-line"' in t for t in tables), (path, tables)

    def test_the_wants_carry_the_kits_search_beside_its_pager(self) -> None:
        self.ran()
        client = PageClient(self.venue.page.pages)
        text = client.get("/datasets", "admin").text
        assert re.findall(r"<om-pager[^>]*>", text) == ['<om-pager search="Search wants">']
        wants = text[text.index("<h2>Wants</h2>") : text.index("<h2>Subjects</h2>")]
        assert '<om-pager search="Search wants"><table class="one-line">' in wants
        assert "</table></om-pager>" in wants
        assert len(client.call_tool("read_datasets", level="admin").data["wants"]) == 2

    def test_with_no_wants_datasets_says_the_next_step(self) -> None:
        self.venue.page.hold(self.feed(Lake(self.venue.VENUE)))
        asked = PageClient(self.venue.page.pages).get("/datasets", "admin").text
        assert "No wants yet" in asked and "Ask a deployment admin to license them." in asked
        assert "<om-pager" not in asked
        admin = (
            PageClient(self.venue.page.pages, deployment_admin=True)
            .get("/datasets", "admin")
            .text
        )
        assert 'data-om-opens="data-sources"' in admin

    def test_a_tool_is_refused_below_manage(self) -> None:
        self.ran()
        client = PageClient(self.venue.page.pages)
        for name in TOOLS:
            assert client.call_tool(name, level="read").status == 403

    def test_the_pages_say_nothing_of_the_venues_terms(self) -> None:
        self.ran()
        client = PageClient(self.venue.page.pages)
        for path in TOOLS.values():
            text = client.get(path, "admin").text.lower()
            assert (
                "terms allow" not in text and "regulat" not in text and "complian" not in text
            )

    def feed(self, lake: Lake) -> Any:
        raise NotImplementedError


# ── A pairs venue ───────────────────────────────────────────────────────


class PairsChecks(_PageChecks):
    """What a data plugin built on `meridian.roles.data.pairs` passes, run
    against its own exchange (`venue`, its venue_cases module): the data
    suite unchanged, its work past the suite's cases, and its pages."""

    venue: Any

    def feed(self, lake: Lake, **kw: Any) -> pairs.Feed:
        return _pairs_feed(self.venue, lake, **kw)

    def lake(self) -> Lake:
        return Lake(self.venue.VENUE)

    def not_presented(self) -> dict[str, str]:
        """The cases the venue never presents: its module's `NOT_PRESENTED`,
        over those its kind never does (contract v27)."""
        return {**PAIRS_NOT_PRESENTED, **self.venue.NOT_PRESENTED}

    # ── The suite ───────────────────────────────────────────────────────

    def test_every_case_is_mapped_or_said_not_presented_with_why(self) -> None:
        made = pairs_producers(self.venue)
        presented = set(self.not_presented())
        assert set(names("data")) == set(made) | presented | set(ANSWERED_BY_SDK)
        assert not set(made) & presented
        assert all(why.strip() for why in self.not_presented().values())

    def test_every_case_the_venue_presents_passes_unchanged(self) -> None:
        v = self.venue
        made = pairs_producers(v)
        report = run("data", made, not_presented=self.not_presented(), instance_id=v.VENUE)
        assert report.passed, report.failures
        expected = len(list(names("data"))) - len(self.not_presented())
        assert len(report.passed_cases) == expected
        assert report.answered_by_sdk == list(ANSWERED_BY_SDK)

    def test_only_a_case_the_venue_cannot_present_is_not_presented(self) -> None:
        about = {case.name: case.about or case.about_field for case in suite("data").cases}
        assert all(about[case] for case in self.not_presented()), "about data or a field"
        sides = {"the-makers-side-inverted", "the-takers-side-stated"}
        assert len(sides & set(self.not_presented())) == 1, "one side or the other"

    def _fails(self, case: str, **mutations: Any) -> bool:
        v = self.venue
        made = pairs_producers(v, **mutations)
        report = run("data", made, not_presented=self.not_presented(), instance_id=v.VENUE)
        return case in report.failures

    def test_a_candle_read_through_a_float_fails_the_suite(self) -> None:
        def through_float(feed: Any, mapped: Any, candle: Any) -> Any:
            lossy = replace(candle, close=Decimal(float(candle.close)))
            return type(feed).close(feed, mapped, lossy)

        assert self._fails("an-exact-price", close=through_float)

    def test_a_stablecoin_price_as_its_currency_fails_the_suite(self) -> None:
        def as_fiat(feed: Any, amount: Any, mapped: Any) -> Any:
            return Money(amount, mapped.quote.currency_code or "USD")

        assert self._fails("a-stablecoin-quote", _money=as_fiat)

    def _side_case(self) -> str:
        return next(case for case in ("the-takers-side-stated", "the-makers-side-inverted")
                    if case not in self.not_presented())  # fmt: skip

    def test_the_side_passed_through_fails_the_suite_where_it_is_the_makers(self) -> None:
        failed = self._fails(self._side_case(), aggressor=lambda feed, seen: seen.side)
        assert failed == (self.venue.SIDE_OF == pairs.MAKER)

    def test_the_side_read_the_other_way_fails_the_suite(self) -> None:
        def other_way(feed: Any, seen: Any) -> str:
            said = type(feed).aggressor(feed, seen)
            return {"buy": "sell", "sell": "buy"}.get(said, "")

        assert self._fails(self._side_case(), aggressor=other_way)

    def test_an_empty_side_recorded_as_zero_fails_the_suite(self) -> None:
        def zero(feed: Any, mapped: Any, best: Any) -> Any:
            filled = replace(best, ask=best.ask if best.ask is not None else Decimal(0))
            return type(feed).quote(feed, mapped, filled)

        assert self._fails("a-one-sided-quote", quote=zero)

    async def test_a_restarts_gap_is_the_trades_after_the_last_one_recorded(self) -> None:
        recorder = Recorder(self.venue.VENUE)
        await pairs_producers(self.venue)["a-restarts-gap-backfilled"](recorder)
        listed: list[Any] = list(recorder.on("ListTrades"))
        [asked] = listed
        assert asked.latest_recorded and [s.entity_id for s in asked.subjects]
        recorded: list[Any] = list(recorder.on("RecordTrades"))
        sent = [t.meta.row_key for r in recorded for t in r.trades]
        product, _, _ = self.venue.RESTARTED
        assert sent == [f"{product}:t:{ident}" for ident in self.venue.BACKFILLED]

    async def test_a_restarts_gap_is_read_once_per_subject(self) -> None:
        recorder = Recorder(self.venue.VENUE)
        await pairs_producers(self.venue)["a-restarts-gap-backfilled"](recorder)
        # The same process hearing the standing want again, as the lake
        # delivers it each minute: the gap is not read back a second time.
        store = Instruments().answering(recorder)
        feed = _pairs_feed(self.venue, recorder)
        subject = await held(store, feed, self.venue.BASE)
        for want_id in ("WNT-S", "WNT-S"):
            event = wanted(
                feed, want_id, pairs.TRADES, [subject], data_type=TRADE, standing=True
            )
            await hear(recorder, feed, event)
        assert len(recorder.on("ListTrades")) == 2, "once in the producer's process, once here"
        assert feed.backfilled

    async def test_the_licensed_datasets_are_those_a_deployment_admin_licensed(self) -> None:
        recorder = Recorder(self.venue.VENUE)
        feed = _pairs_feed(self.venue, recorder)
        recorder.answer("ListDatasets", lambda _: ops.ListDatasetsResult(licences=[
            ops.DatasetLicence(dataset=feed.dataset(pairs.DAILY), kept=True),
            ops.DatasetLicence(dataset="another-1:daily", kept=True),
        ]))  # fmt: skip
        assert await feed.read_licences() == frozenset({feed.dataset(pairs.DAILY)})

    # ── Its work past the suite's cases ─────────────────────────────────

    async def test_the_forming_day_read_again_is_restated_and_a_repeat_unchanged(self) -> None:
        v, lake = self.venue, self.lake()
        first = self.feed(lake, market=v.market(v.NOW_NS, forming=0))
        btc = await lake.held(first, v.BASE)
        await first.record_days([btc], v.TODAY, v.TODAY, PRICE)
        again = self.feed(lake, market=v.market(v.NOW_NS, forming=1))
        await again.record_days([btc], v.TODAY, v.TODAY, PRICE)
        await again.record_days([btc], v.TODAY, v.TODAY, PRICE)
        key = ("price", f"{v.FORMING_PRODUCT}:1d:{v.FORMING[0][0]}")
        assert lake.versions[key][0] == 2
        assert again.counts.restated == 1
        assert again.counts.unchanged >= 1
        forming = [r for r in lake.rows() if r.meta.row_key == key[1]]
        assert all(r.meta.valid_until_ns > v.NOW_NS for r in forming)
        assert all(not r.meta.source_times for r in forming), (
            "a forming day has no published time"
        )

    async def test_a_completed_day_is_a_plain_date_with_its_published_time(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        await feed.record_days([btc], v.CLOSED, v.CLOSED, PRICE)
        product, text = v.CLOSED_CLOSE
        [row] = [r for r in lake.rows() if r.meta.row_key.startswith(f"{product}:1d:")]
        assert row.meta.business_date == v.CLOSED.isoformat()
        assert [t.kind for t in row.meta.source_times] == [ops.SOURCE_TIME_KIND_PUBLISHED]
        assert row.meta.source_times[0].at_ns == row.meta.valid_until_ns
        assert str(as_decimal(row.price.amount)) == text
        assert row.meta.source.dataset == f"{v.VENUE}:daily"

    async def test_a_price_past_a_float_is_recorded_exactly(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.EXACT_BASE)
        await feed.record_days([subject], v.CLOSED, v.CLOSED, PRICE)
        assert v.EXACT_CLOSE in {str(as_decimal(r.price.amount)) for r in lake.rows()}

    async def test_a_stablecoin_quote_names_the_tokens_instrument_never_a_currency(
        self,
    ) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.STABLE_BASE)
        await feed.record_days([btc], v.CLOSED, v.CLOSED, PRICE)
        stable = feed.products.ids[v.STABLE]
        [row] = [r for r in lake.rows() if r.meta.row_key.startswith(f"{v.STABLE_PRODUCT}:")]
        money = as_money(row.price)
        assert (money.instrument_id, money.currency_code) == (stable, "")
        others = [as_money(r.price) for r in lake.rows() if r is not row]
        assert all(m.currency_code and not m.instrument_id for m in others), "fiat by its code"

    async def test_wants_are_recorded_against_or_declined_with_why(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        future = v.TODAY + timedelta(days=3)
        for want_id, day, subjects in (
            ("WNT-1", v.CLOSED, [btc, "LCL-NOT-COVERED"]),
            ("WNT-2", future, [btc]),
        ):
            await hear(lake, feed, wanted(feed, want_id, pairs.DAILY, subjects, day=day))
        recorded = [p for p in lake.on("RecordPrices") if p.want_id == "WNT-1"]
        assert recorded and all(r.meta.subjects[0].entity_id == btc for r in recorded[0].prices)
        declined = {
            (d.want_id, s.entity_id, d.reason)
            for d in lake.on("DeclineWant")
            for s in d.subjects
        }
        assert declined == {
            ("WNT-1", "LCL-NOT-COVERED", ops.UNANSWERED_REASON_NOT_COVERED),
            ("WNT-2", btc, ops.UNANSWERED_REASON_SOURCE_SILENT),
        }
        assert [h.want_id for h in feed.heard] == ["WNT-2", "WNT-1"]

    async def test_the_daily_datasets_latest_is_the_past_weeks_days(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        await hear(lake, feed, wanted(feed, "WNT-7", pairs.DAILY, [btc]))
        days = {r.meta.business_date for r in lake.rows()}
        assert v.CLOSED.isoformat() in days and not lake.on("DeclineWant"), days
        week = (v.TODAY - timedelta(days=6)).isoformat()
        assert all(r.meta.business_date >= week for r in lake.rows())

    async def test_a_day_before_the_venues_reach_is_declined_beyond_history(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        reach = feed.market.session.limits.history_days
        if not reach:
            return  # the venue states no reach
        btc = await lake.held(feed, v.BASE)
        old = v.TODAY - timedelta(days=reach + 5)
        assert await feed.record_days([btc], old, old) == {btc: "beyond_history"}

    async def test_the_live_dataset_records_last_bid_and_ask_once_per_change(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        await feed.record_live([btc])
        await feed.record_live([btc])
        rows = lake.rows()
        kinds = {(r.meta.row_key.split(":")[0], r.kind) for r in rows}
        for product in v.LIVE_LAST:
            assert {
                (product, k)
                for k in (ops.PRICE_KIND_LAST, ops.PRICE_KIND_BID, ops.PRICE_KIND_ASK)
            } <= kinds
        last = {r.meta.row_key.split(":")[0]: str(as_decimal(r.price.amount)) for r in rows
                if r.kind == ops.PRICE_KIND_LAST}  # fmt: skip
        assert last == v.LIVE_LAST
        assert all(not r.meta.business_date and r.meta.valid_until_ns == 0 for r in rows)
        assert all(r.meta.source.dataset == f"{v.VENUE}:live" for r in rows)
        assert feed.counts.unchanged == feed.counts.recorded, "the same answer changes nothing"

    async def test_a_standing_live_want_is_kept_current_until_withdrawn(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        event = wanted(feed, "WNT-9", pairs.LIVE, [btc], kinds=(ops.PRICE_KIND_LAST,),
                       standing=True)  # fmt: skip
        await hear(lake, feed, event)
        assert set(feed.standing) == {"WNT-9"}
        sent = len(lake.on("RecordPrices"))
        await feed.current()
        assert len(lake.on("RecordPrices")) == sent + 1
        assert {r.kind for r in lake.rows()} == {ops.PRICE_KIND_LAST}
        lake.answer("WantWithdrawn", lambda _: ops.WantWithdrawnEvent(want_id="WNT-9"))
        await lake.receive(want_withdrawn=feed.on_withdrawn)
        await feed.current()
        assert not feed.standing and len(lake.on("RecordPrices")) == sent + 1

    async def test_what_a_dataset_does_not_serve_is_not_covered(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        for dataset, data_type, kinds in (
            ("live", BAR, []),
            ("daily", PRICE, [ops.PRICE_KIND_NAV]),
            ("elsewhere", PRICE, []),
        ):
            event = wanted(feed, f"W-{dataset}", dataset, [btc], data_type=data_type,
                           kinds=tuple(kinds), day=v.CLOSED)  # fmt: skip
            await hear(lake, feed, event)
        assert not lake.on("RecordPrices") and not lake.on("RecordBars")
        assert {d.reason for d in lake.on("DeclineWant")} == {ops.UNANSWERED_REASON_NOT_COVERED}

    async def test_a_venue_not_held_is_reported_once_and_named_as_reported(self) -> None:
        v, lake = self.venue, self.lake()
        lake.answer("ResolveVenue", lambda _: ops.ResolveVenueResult(
            found=False, miss_reason=ops.MISS_REASON_NOT_FOUND))  # fmt: skip
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        await feed.record_days([btc], v.CLOSED, v.CLOSED)
        await feed.record_live([btc])
        assert len(lake.on("ReportMissingVenue")) == 1
        for row in lake.rows() + lake.rows("RecordBars"):
            assert row.meta.source.venue_id == ""
            assert [(u.scheme, u.code) for u in row.meta.unconverted] == [
                (f"{v.VENUE}:venue", v.VENUE)
            ]

    async def test_a_venue_held_is_named_by_its_id_on_every_row(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        await feed.record_days([btc], v.CLOSED, v.CLOSED)
        [asked] = lake.on("ResolveVenue")
        assert {(i.scheme, i.value, i.source) for i in asked.identifiers} == set(
            feed.market.venue_identifiers
        ), "the identifiers its conversion declares"
        assert {r.meta.source.venue_id for r in lake.rows()} == {feed.venue.venue_id}
        assert feed.venue.venue_id

    async def test_the_product_map_is_kept_and_read_back_without_resolving_again(
        self, tmp_path: Path
    ) -> None:
        v, lake = self.venue, self.lake()
        kept = pairs.ProductMap(tmp_path / "products-synthetic.json")
        feed = self.feed(lake)
        feed.products = kept
        btc = await lake.held(feed, v.BASE)
        await feed.record_days([btc], v.CLOSED, v.CLOSED)
        assert lake.on("ResolveInstrument") and lake.on("ResolveIdentifier")
        assert kept.path is not None and kept.path.is_file()
        again = pairs.ProductMap(kept.path)
        assert again.load() and again.ids == kept.ids and again.subjects == {btc: v.BASE}
        second = self.lake()
        restarted = self.feed(second)
        restarted.products = again
        await restarted.map_products()
        await restarted.record_days([btc], v.CLOSED, v.CLOSED)
        assert not second.on("ResolveIdentifier"), "an asset resolved once is not asked again"
        assert not second.on("ResolveInstrument"), "a subject named once is not read again"
        assert v.DELISTED not in {m.product for m in again.mapped()}

    async def test_reading_the_listing_mints_no_record_for_each_asset(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        await feed.map_products()
        assert feed.products.listed and not lake.on("ResolveIdentifier")
        assert not feed.products.mapped()
        btc = await lake.held(feed, v.BASE)
        await feed.record_days([btc], v.CLOSED, v.CLOSED)
        quotes = {q.code for q in feed.products.quotes(v.BASE)}
        assert set(feed.products.ids) == quotes, "only the quotes of the subject's products"
        assert len(lake.on("ResolveIdentifier")) == len(quotes)
        assert {m.base_id for m in feed.products.mapped()} == {btc}

    async def test_a_custodians_record_is_named_by_its_global_identifier_and_joined(
        self,
    ) -> None:
        v, lake = self.venue, self.lake()
        custodian = lake.instruments.hold(
            "INS-CUSTODIAN",
            ops.Identifier(scheme="caip19", value=BITCOIN),
            ops.Identifier(scheme="symbol", value="BTC", source=OTHER),
        )
        feed = self.feed(lake)
        await hear(lake, feed, wanted(feed, "WNT-1", pairs.DAILY, [custodian], day=v.CLOSED))
        (read,) = lake.on("ResolveInstrument")
        assert read.instrument_id == custodian and read.as_of_ns == v.NOW_NS
        joined = lake.on("ResolveIdentifier")[0]
        assert ("symbol", v.BASE, v.VENUE) in {(i.scheme, i.value, i.source)
                                               for i in joined.identifiers}  # fmt: skip
        assert not lake.on("ReportMissingInstrument") and not lake.on("DeclineWant")
        assert feed.products.subjects == {custodian: v.BASE}
        sent = [p for p in lake.on("RecordPrices") if p.want_id == "WNT-1"]
        assert sent and {r.meta.subjects[0].entity_id for p in sent for r in p.prices} == {
            custodian
        }
        product, text = v.CLOSED_CLOSE
        assert text in {str(as_decimal(r.price.amount)) for p in sent for r in p.prices
                        if r.meta.row_key.startswith(f"{product}:1d:")}  # fmt: skip

    async def test_another_sources_symbol_that_is_the_venues_code_names_the_asset(self) -> None:
        v, lake = self.venue, self.lake()
        custodian = lake.instruments.hold(
            "INS-CUSTODIAN", ops.Identifier(scheme="symbol", value=v.EXACT_BASE, source=OTHER)
        )
        feed = self.feed(lake)
        declined = await feed.record_days([custodian], v.CLOSED, v.CLOSED, PRICE)
        assert not declined and feed.products.subjects == {custodian: v.EXACT_BASE}
        first = lake.on("ResolveIdentifier")[0]
        joined = [(i.scheme, i.value, i.source) for i in first.identifiers]
        assert ("symbol", v.EXACT_BASE, v.VENUE) in joined
        assert joined[-1] == ("symbol", v.EXACT_BASE, OTHER), "beside the one it matched"
        assert v.EXACT_CLOSE in {str(as_decimal(r.price.amount)) for r in lake.rows()}

    async def test_a_record_naming_none_of_the_venues_assets_is_not_covered(self) -> None:
        v, lake = self.venue, self.lake()
        equity = lake.instruments.hold(
            "INS-EQUITY",
            ops.Identifier(scheme="cusip", value="74347X831"),
            ops.Identifier(scheme="symbol", value="TQQQ", source=OTHER),
        )
        feed = self.feed(lake)
        for _ in range(2):
            assert await feed.record_days([equity], v.CLOSED, v.CLOSED) == {
                equity: "not_covered"
            }
        assert len(lake.on("ResolveInstrument")) == 1, (
            "read once until the listing is read again"
        )
        assert not lake.on("ResolveIdentifier") and not lake.on("ReportMissingInstrument")
        await feed.map_products()
        await feed.record_days([equity], v.CLOSED, v.CLOSED)
        assert len(lake.on("ResolveInstrument")) == 2

    async def test_a_securitys_ticker_that_is_a_coins_code_names_no_asset(self) -> None:
        # A share whose ticker is the venue's code for a token (ETH is a
        # share's): by its CUSIP, or by its class, it is no coin.
        v, lake = self.venue, self.lake()
        ticker = ops.Identifier(scheme="symbol", value=v.EXACT_BASE, source=OTHER)
        by_cusip = lake.instruments.hold(
            "INS-SHARE", ops.Identifier(scheme="cusip", value="297602104"), ticker
        )
        feed = self.feed(lake)
        by_class = "INS-SHARE-CLASSED"

        def read(params: Any) -> Any:
            if params.instrument_id != by_class:
                return lake.instruments.read(params)
            record = ops.InstrumentRecord(instrument_id=by_class, identifiers=[ticker],
                                          asset_class=ops.ASSET_CLASS_EQUITY)  # fmt: skip
            return ops.ResolveInstrumentResult(found=True, instrument=record)

        lake.answer("ResolveInstrument", read)
        for subject in (by_cusip, by_class):
            declined = await feed.record_days([subject], v.CLOSED, v.CLOSED)
            assert declined == {subject: "not_covered"}
        assert not lake.on("ResolveIdentifier") and not feed.products.subjects

    async def test_with_no_read_of_an_instrument_nothing_is_named(self) -> None:
        v, lake = self.venue, self.lake()

        def refused(_: Any) -> Any:
            raise NotGranted("platform.reference.query.resolve-instrument", "not granted")

        lake.answer("ResolveInstrument", refused)
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        assert await feed.record_days([btc], v.CLOSED, v.CLOSED) == {btc: "not_covered"}
        await feed.record_days([btc], v.CLOSED, v.CLOSED)
        assert len(lake.on("ResolveInstrument")) == 1 and not feed.reads_instruments

    async def test_an_asset_that_does_not_resolve_is_reported_once_and_left_out(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        await feed.ensure_mapped()
        usd = next(q for q in feed.products.quotes(v.BASE) if q.currency_code)
        for n in (1, 2):
            lake.instruments.hold(f"INS-{usd.code}-{n}", *feed.identifiers(usd))
        btc = await lake.held(feed, v.BASE)
        await feed.record_days([btc], v.CLOSED, v.CLOSED)
        await feed.map_products()
        await feed.record_days([btc], v.CLOSED, v.CLOSED)
        assert len(lake.on("ReportMissingInstrument")) == 1
        assert feed.products.missing == {usd.code: "MISS_REASON_AMBIGUOUS"}
        assert all(usd.code != m.quote.code for m in feed.products.mapped())
        assert lake.rows(), "its products quoted in other assets still recorded"

    async def test_a_join_meeting_another_record_is_reported_and_the_subject_served(
        self,
    ) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        await lake.held(feed, v.BASE)
        custodian = lake.instruments.hold(
            "INS-CUSTODIAN", ops.Identifier(scheme="symbol", value="BTC", source=OTHER),
            ops.Identifier(scheme="caip19", value=BITCOIN),
        )  # fmt: skip
        declined = await feed.record_days([custodian], v.CLOSED, v.CLOSED, PRICE)
        (miss,) = lake.on("ReportMissingInstrument")
        assert miss.reason == ops.MISS_REASON_AMBIGUOUS
        assert not declined and feed.products.subjects == {custodian: v.BASE}
        assert {r.meta.subjects[0].entity_id for r in lake.rows()} == {custodian}

    async def test_every_row_names_a_raw_record_its_storage_holds(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        await feed.record_days([btc], v.CLOSED - timedelta(days=1), v.CLOSED)
        await feed.record_live([btc])
        store = v.raw_store(feed)
        for row in lake.rows() + lake.rows("RecordBars"):
            assert row.meta.raw.key and store.get(row.meta.raw.key) is not None, (
                row.meta.raw.key
            )

    def test_no_float_reaches_a_row(self) -> None:
        for module in (*self.venue.CONVERSION, Path(pairs.__file__)):
            tree = ast.parse(Path(module).read_text())
            floats = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                      and getattr(n.func, "id", "") == "float"]  # fmt: skip
            assert not floats, f"{module} calls float() at {floats}"

    async def test_a_product_the_venue_refuses_leaves_the_subjects_others_recorded(
        self,
    ) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        asked = feed.market.candles

        def refusing(product: str, *days: Any) -> Any:
            if product == v.STABLE_PRODUCT:
                raise OSError("refused")
            return asked(product, *days)

        feed.market.candles = refusing  # type: ignore[method-assign,assignment]
        declined = await feed.record_days([btc], v.CLOSED, v.CLOSED, PRICE)
        assert not declined
        assert {r.meta.row_key.split(":")[0] for r in lake.rows()} == {v.CLOSED_CLOSE[0]}

    # ── Trades and quotes (contract v19) ────────────────────────────────

    async def _streaming(
        self, lake: Lake, key: str = pairs.TRADES, data_type: str = TRADE
    ) -> tuple[pairs.Feed, str]:
        """The feed with a standing want of `key` for BASE, its stream not run."""
        feed = self.feed(lake)
        btc = await lake.held(feed, self.venue.BASE)
        await hear(lake, feed, wanted(feed, "WNT-S", key, [btc], data_type=data_type,
                                      standing=True))  # fmt: skip
        return feed, btc

    async def _drive(self, feed: pairs.Feed) -> None:
        """Each of the synthetic venue's connections in turn, as the stream
        opens them, each dropping once it has said everything; then what is
        held sent."""
        for session in self.venue.stream_sessions(feed):

            async def said(_: str, messages: list[str] = session) -> Any:
                return self.venue.replayed(messages)

            feed.stream.retarget(feed.market.stream_address, said, feed.market.subscriptions)
            await feed.stream.run(once=True)
        await feed.flush()

    async def test_a_standing_want_puts_its_subjects_products_on_the_stream_until_withdrawn(
        self,
    ) -> None:
        lake = self.lake()
        feed, _ = await self._streaming(lake)
        assert sorted(feed.streams) == self.venue.STREAM_NAMES
        lake.answer("WantWithdrawn", lambda _: [ops.WantWithdrawnEvent(want_id="WNT-S")])
        await lake.receive(want_withdrawn=feed.on_withdrawn)
        assert feed.streams == {}

    async def test_the_stream_records_every_trade_and_reads_back_the_gap_a_drop_leaves(
        self,
    ) -> None:
        v, lake = self.venue, self.lake()
        feed, btc = await self._streaming(lake)
        await self._drive(feed)
        trades = lake.rows("RecordTrades")
        by_product: dict[str, list[str]] = {}
        for row in trades:
            product, kind, ident = row.meta.row_key.split(":")
            assert kind == "t"
            by_product.setdefault(product, []).append(ident)
        assert {p: sorted(ids, key=int) for p, ids in by_product.items()} == v.STREAMED
        assert all(len(ids) == len(set(ids)) for ids in by_product.values()), "each trade once"
        assert feed.stream.health.opened == 2 and feed.stream.health.dropped == 2
        yes = ops.ELIGIBLE_ELIGIBLE
        every = ops.Eligibility(high_low=yes, open=yes, close=yes, volume=yes)
        for row in trades:
            ident = row.meta.row_key.rsplit(":", 1)[1]
            assert ops.Aggressor.Name(row.aggressor) == v.AGGRESSORS[ident], ident
            assert row.meta.source.dataset == f"{v.VENUE}:trades"
            assert [s.entity_id for s in row.meta.subjects] == [btc]
            assert not row.meta.business_date and row.meta.valid_from_ns
            assert [t.kind for t in row.meta.source_times] == [ops.SOURCE_TIME_KIND_EVENT]
            assert row.source_sequence == int(ident)
            assert (
                row.attributes.consolidated == every and row.attributes.market_centre == every
            )
            assert not row.attributes.characteristics
            gap = ident in v.GAP
            assert ("/trades/" in row.meta.raw.key.lower()) == gap, (ident, row.meta.raw.key)
            assert ("/stream/" in row.meta.raw.key) != gap, (ident, row.meta.raw.key)
        (product, ident), (price, quantity) = v.TRADE_PRICE, v.TRADE_QUANTITY
        [stated] = [r for r in trades if r.meta.row_key == f"{product}:t:{ident}"]
        assert (str(as_decimal(stated.price.amount)), str(as_decimal(stated.quantity))) == (
            price,
            quantity,
        )

    async def test_the_streams_quotes_are_each_products_latest_with_their_sizes(self) -> None:
        v, lake = self.venue, self.lake()
        feed, _ = await self._streaming(lake, pairs.LIVE, QUOTE)
        await self._drive(feed)
        latest: dict[str, Any] = {}
        for row in lake.rows("RecordQuotes"):
            product, kind, at = row.meta.row_key.split(":")
            assert kind == "q" and int(at) == row.meta.valid_from_ns
            assert row.meta.source.dataset == f"{v.VENUE}:live" and not row.meta.business_date
            latest[product] = row
        for params in lake.on("RecordQuotes"):
            products = [q.meta.row_key.split(":")[0] for q in params.quotes]
            assert len(products) == len(set(products)), "at most one a product each time sent"
        for product, (bid, bid_size, ask, ask_size) in v.LAST_QUOTES.items():
            row = latest[product]
            said = (as_decimal(row.bid.amount), as_decimal(row.bid_quantity),
                    as_decimal(row.ask.amount), as_decimal(row.ask_quantity))  # fmt: skip
            assert said == tuple(Decimal(x) for x in (bid, bid_size, ask, ask_size)), product

    async def test_a_quote_now_is_read_from_the_book_and_an_empty_side_left_unset(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        one_sided = await lake.held(feed, v.ONE_SIDED_BASE)
        await hear(lake, feed, wanted(feed, "WNT-Q", pairs.LIVE, [btc, one_sided],
                                      data_type=QUOTE))  # fmt: skip
        quotes = lake.rows("RecordQuotes")
        assert {r.meta.subjects[0].entity_id for r in quotes} == {btc, one_sided}
        for row in quotes:
            if row.meta.subjects[0].entity_id == one_sided:
                assert row.HasField("bid") and row.HasField("bid_quantity")
                assert not row.HasField("ask") and not row.HasField("ask_quantity")
            else:
                assert row.HasField("ask") and row.HasField("ask_quantity")
        assert all(params.want_id == "WNT-Q" for params in lake.on("RecordQuotes"))
        assert feed.streams == {}, "a quote wanted now puts nothing on the stream"

    async def test_a_range_of_trades_is_read_from_the_history_and_one_before_it_declined(
        self,
    ) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        start = v.NOW_NS - 60 * 1_000_000_000
        event = wanted(feed, "WNT-R", pairs.TRADES, [btc], data_type=TRADE)
        event.valid_from_ns, event.valid_until_ns = start, v.NOW_NS
        await hear(lake, feed, event)
        trades = lake.rows("RecordTrades")
        assert trades and all(start <= r.meta.valid_from_ns < v.NOW_NS for r in trades)
        assert all(params.want_id == "WNT-R" for params in lake.on("RecordTrades"))
        before = wanted(feed, "WNT-B", pairs.TRADES, [btc], data_type=TRADE)
        before.valid_from_ns = v.NOW_NS - 10 * 86_400 * 1_000_000_000
        before.valid_until_ns = before.valid_from_ns + 3_600 * 1_000_000_000
        await hear(lake, feed, before)
        [declined] = [d for d in lake.on("DeclineWant") if d.want_id == "WNT-B"]
        assert declined.reason == ops.UNANSWERED_REASON_BEYOND_HISTORY

    async def test_a_trade_heard_again_is_not_sent_again(self) -> None:
        lake = self.lake()
        feed, _ = await self._streaming(lake)
        await self._drive(feed)
        sent = len(lake.rows("RecordTrades"))
        await self._drive(feed)
        assert len(lake.rows("RecordTrades")) == sent

    async def test_a_trade_or_quote_the_dataset_does_not_hold_is_not_covered(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        for want_id, key, data_type in (("WNT-1", pairs.DAILY, TRADE),
                                        ("WNT-2", pairs.TRADES, QUOTE),
                                        ("WNT-3", pairs.DAILY, QUOTE)):  # fmt: skip
            await hear(lake, feed, wanted(feed, want_id, key, [btc], data_type=data_type))
        declined = {d.want_id: d.reason for d in lake.on("DeclineWant")}
        assert declined == dict.fromkeys(("WNT-1", "WNT-2", "WNT-3"),
                                         ops.UNANSWERED_REASON_NOT_COVERED)  # fmt: skip

    async def test_a_batch_the_lake_refuses_is_said_and_the_stream_goes_on(self) -> None:
        lake = self.lake()
        feed, _ = await self._streaming(lake)

        def refused(_: Any) -> Any:
            raise MeridianError("refused: trades[0].quantity")

        lake.answer("RecordTrades", refused)
        await self._drive(feed)
        assert feed.stream.health.opened == 2, "both connections opened, the refusal said"
        assert feed.pending_trades == [], "a refused batch is not sent again and again"

    async def test_a_restarts_gap_refused_is_said_and_the_stream_goes_on(self) -> None:
        lake = self.lake()

        def refused(_: Any) -> Any:
            raise NotGranted("platform.lake.query.list-trades", "not granted")

        lake.answer("ListTrades", refused)
        feed, _ = await self._streaming(lake)
        assert feed.backfilled and feed.streams, "the subject went on the stream all the same"
        assert not lake.rows("RecordTrades")

    async def test_licences_not_answered_leave_each_not_licensed_yet(self) -> None:
        lake = self.lake()

        def refused(_: Any) -> Any:
            raise NotGranted("platform.lake.query.list-datasets", "not granted")

        lake.answer("ListDatasets", refused)
        feed = self.feed(lake)
        assert await feed.read_licences() == frozenset() and feed.wants.reads_licences is False
        assert await feed.read_licences() == frozenset(), "asked once, then said"
        assert len(lake.on("ListDatasets")) <= 1

    async def test_each_dataset_counts_what_it_recorded(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        await hear(lake, feed, wanted(feed, "WNT-1", pairs.DAILY, [btc], day=v.CLOSED))
        daily = feed.sent_to(pairs.DAILY)
        assert daily.recorded > 0 and daily.last_ns == v.NOW_NS
        assert (
            feed.sent_to(pairs.LIVE).recorded == 0 and feed.sent_to(pairs.TRADES).last_ns == 0
        )

    # ── Its pages ───────────────────────────────────────────────────────

    async def worked(self) -> tuple[Any, Lake]:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        btc = await lake.held(feed, v.BASE)
        for want_id, dataset, standing in (("WNT-1", pairs.DAILY, False),
                                           ("WNT-2", pairs.LIVE, True)):  # fmt: skip
            day = None if standing else v.CLOSED
            await hear(lake, feed, wanted(feed, want_id, dataset, [btc], day=day,
                                          standing=standing))  # fmt: skip
        # The stream's first connection, as the synthetic venue answers it: it
        # opens, says its messages and drops.
        first = v.stream_sessions(feed)[0]

        async def said(_: str) -> Any:
            return v.replayed(first)

        feed.stream.retarget(feed.market.stream_address, said, feed.market.subscriptions)
        await feed.stream.run(once=True)
        v.page.hold(feed)
        return feed, lake

    def shown(self, lake: Lake) -> set[str]:
        return {str(as_decimal(r.price.amount)) for r in lake.rows()}

    def test_each_page_holds_the_roles_sections_in_its_order(self) -> None:
        self.ran()
        client = PageClient(self.venue.page.pages)
        # "Sessions" only once a session is measured (0.32.2).
        measured = client.call_tool("read_connection", level="admin").data["session_latency"]
        assert _sections(client.get("/", "admin").text) == [
            "Key",
            "Limits and use",
            "Stream",
        ] + (["Sessions"] if measured else [])
        assert _sections(client.get("/datasets", "admin").text) == [
            "Served", "Wants", "Subjects", self.venue.page.TITLE,
        ]  # fmt: skip

    def test_the_tools_answer_what_the_pages_show(self) -> None:
        v = self.venue
        feed, _ = self.ran()
        client = PageClient(v.page.pages)
        assert {t.name for t in v.page.pages.tools} >= set(TOOLS)
        connection = client.call_tool("read_connection", level="admin")
        assert connection.outcome == "unchanged", connection.json
        data = connection.data
        assert (data["mode"], data["credentials"], data["entitled_at_vendor"]) == (
            "Sample data", [], v.page.ENTITLED,
        )  # fmt: skip
        assert data["calls"] > 0 and data["last_call_at"] and data["sessions"] == 0
        assert (data["venue"], data["venue_id"], data["healthy"]) == (
            feed.market.name, feed.venue.venue_id, True,
        )  # fmt: skip
        page = client.get("/", "admin").text.replace("&#39;", "'")
        assert "No key needed" in page and v.page.ENTITLED in page
        assert "Sample data: the plugin answers from recorded responses" in page
        assert feed.venue.venue_id in page and data["allowed"] in page
        assert (data["stream_state"], data["streaming"], data["stream_opened"],
                data["stream_dropped"]) == ("waiting", len(v.STREAM_NAMES), 1, 1)  # fmt: skip
        assert data["stream_messages"] > 0 and data["last_message_at"]
        assert f"{data['streaming']} products on it;" in page
        datasets = client.call_tool("read_datasets", level="admin").data
        assert [d["dataset"] for d in datasets["served"]] == [
            f"{v.VENUE}:daily", f"{v.VENUE}:live", f"{v.VENUE}:trades",
        ]  # fmt: skip
        assert all(d["day"] == "Etc/UTC, ends 00:00" for d in datasets["served"])
        daily, live, _ = datasets["served"]
        assert daily["recorded"] > 0 and daily["last_recorded"] and live["recorded"] > 0
        assert datasets["standing_wants"] == 1
        assert [(w["want_id"], w["kept_current"]) for w in datasets["wants"]] == [
            ("WNT-2", True),
            ("WNT-1", False),
        ]
        shown = client.get("/datasets", "admin").text
        mapped = (
            f"{datasets['products_mapped']} of {datasets['products_listed']} products mapped"
        )
        assert mapped in shown
        assert datasets["subjects_named"] == 1 and datasets["reads_instruments"] is True
        assert "for 1 subject the lake asked for" in shown
        assert "Kept current" in shown

    def test_datasets_says_which_a_deployment_admin_licensed(self) -> None:
        feed, _ = self.ran()
        client = PageClient(self.venue.page.pages)
        served = client.call_tool("read_datasets", level="admin").data["served"]
        assert not any(d["licensed"] for d in served)
        assert client.get("/datasets", "admin").text.count("Not licensed yet") == 6
        feed.licensed = frozenset({feed.dataset(pairs.DAILY)})
        served = client.call_tool("read_datasets", level="admin").data["served"]
        assert [d["licensed"] for d in served] == [True, False, False]
        assert client.get("/datasets", "admin").text.count("Not licensed yet") == 4

    def test_the_roles_figures_in_its_order(self) -> None:
        self.ran()
        figures = self.venue.page.figures_now()
        assert [f.label for f in figures] == [
            "Connection", "Entitled at the vendor", "Stream", "Last recorded",
        ]  # fmt: skip
        assert figures[0].value == "Sample data" and figures[1].value == "3 of 3 datasets"
        streamed = f"{len(self.venue.STREAM_NAMES)} listings"
        assert figures[2].value == streamed and figures[2].state == "warn"


# ── An event-contract venue ─────────────────────────────────────────────


class EventContractsChecks(_PageChecks):
    """What a data plugin built on `meridian.roles.data.event_contracts`
    passes, run against its own exchange (`venue`, its venue_cases module):
    the data suite unchanged, its work past the suite's cases, its outcomes,
    and its pages."""

    venue: Any

    def feed(self, lake: Lake, **kw: Any) -> event_contracts.Feed:
        return _contracts_feed(self.venue, lake, **kw)

    def lake(self) -> Lake:
        return Lake(self.venue.VENUE)

    @staticmethod
    def _amounts(rows: list[Any], kind: int) -> list[str]:
        return [str(as_decimal(r.price.amount)) for r in rows if r.kind == kind]

    def not_presented(self) -> dict[str, str]:
        """The cases the venue never presents: its module's `NOT_PRESENTED`,
        over those its kind never does (contract v27)."""
        return {**EVENT_CONTRACTS_NOT_PRESENTED, **self.venue.NOT_PRESENTED}

    # ── The suite ───────────────────────────────────────────────────────

    def test_every_case_is_mapped_or_said_not_presented_with_why(self) -> None:
        made = event_contract_producers(self.venue)
        presented = set(self.not_presented())
        assert set(names("data")) == set(made) | presented | set(ANSWERED_BY_SDK)
        assert not set(made) & presented
        assert all(why.strip() for why in self.not_presented().values())

    def test_only_a_case_about_a_kind_never_published_is_not_presented(self) -> None:
        about = {case.name: case.about or case.about_field for case in suite("data").cases}
        assert all(about[name] for name in self.not_presented()), "a required case skipped"
        assert "reads-its-datasets-licences" not in self.not_presented()

    def test_every_case_the_venue_presents_passes_unchanged(self) -> None:
        v = self.venue
        made = event_contract_producers(v)
        report = run("data", made, not_presented=self.not_presented(), instance_id=v.VENUE)
        assert report.passed, report.failures
        expected = len(list(names("data"))) - len(self.not_presented())
        assert len(report.passed_cases) == expected

    def _fails(self, case: str, **mutations: Any) -> bool:
        v = self.venue
        made = event_contract_producers(v, **mutations)
        report = run("data", made, not_presented=self.not_presented(), instance_id=v.VENUE)
        return case in report.failures

    def test_a_price_read_through_a_float_fails_the_suite(self) -> None:
        def through_float(feed: Any, mapped: Any, kind: str, amount: Any, seen: Any) -> Any:
            return type(feed).price(feed, mapped, kind, Decimal(float(amount)), seen)

        assert self._fails("an-exact-price", price=through_float)

    def test_a_quote_dropping_its_sizes_fails_the_suite(self) -> None:
        def sizeless(feed: Any, mapped: Any, top: Any) -> Any:
            return type(feed).quote(feed, mapped, replace(top, bid_size=None, ask_size=None))

        assert self._fails("a-quote-recorded", quote=sizeless)

    def test_a_token_price_as_its_currency_fails_the_suite(self) -> None:
        if not self.venue.STABLE:
            return  # a venue pricing in a currency names it by its code, as it should

        def as_fiat(feed: Any, amount: Any, mapped: Any) -> Any:
            return Money(amount, "USD")

        assert self._fails("a-stablecoin-quote", _money=as_fiat)

    def test_an_outcome_read_as_its_full_payout_fails_the_suite(self) -> None:
        def in_full(feed: Any, value: Any, contract: Any) -> str:
            return "pays"

        assert self._fails("records-a-partial-payout", _determination=in_full)

    # ── Its work past the suite's cases ─────────────────────────────────

    async def test_a_contracts_prices_are_its_last_bid_and_ask_per_contract(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        declined = await feed.record_live([subject], data_type=PRICE)
        rows = lake.rows()
        assert not declined
        assert self._amounts(rows, ops.PRICE_KIND_LAST) == [v.LAST]
        assert self._amounts(rows, ops.PRICE_KIND_BID) == [v.BID]
        assert self._amounts(rows, ops.PRICE_KIND_ASK) == [v.ASK]
        assert all(r.basis == ops.PRICE_BASIS_PER_UNIT for r in rows)
        assert all(r.meta.subjects[0].entity_id == subject for r in rows)
        assert all(not r.meta.business_date and r.meta.valid_until_ns == 0 for r in rows)
        assert all(r.meta.source.dataset == f"{v.VENUE}:live" for r in rows)
        assert all(r.meta.raw.key.startswith("responses/") for r in rows)
        assert all(r.meta.row_key.startswith(f"{v.BASE}:") for r in rows)

    async def test_a_quote_carries_both_sides_with_their_sizes(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await feed.record_live([subject], data_type=QUOTE)
        [quote] = lake.rows("RecordQuotes")
        assert str(as_decimal(quote.bid.amount)) == v.BID
        assert str(as_decimal(quote.ask.amount)) == v.ASK
        assert str(as_decimal(quote.bid_quantity)) == v.BID_SIZE
        assert str(as_decimal(quote.ask_quantity)) == v.ASK_SIZE
        assert quote.meta.valid_from_ns > 0 and quote.meta.row_key.startswith(
            f"{v.BASE}:quote:"
        )
        assert not lake.rows(), "a quote's want records no prices"

    async def test_a_side_with_no_order_is_left_unset(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.ONE_SIDED)
        await feed.record_live([subject])
        [quote] = lake.rows("RecordQuotes")
        assert quote.HasField("bid") and not quote.HasField("ask")
        assert quote.HasField("bid_quantity") and not quote.HasField("ask_quantity")
        assert not self._amounts(lake.rows(), ops.PRICE_KIND_ASK)

    async def test_a_price_past_a_float_is_recorded_exactly(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.EXACT)
        await feed.record_live([subject], data_type=PRICE)
        assert v.EXACT_LAST in self._amounts(lake.rows(), ops.PRICE_KIND_LAST)

    async def test_every_price_names_the_venues_cash(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await feed.record_live([subject])
        monies = [as_money(r.price) for r in lake.rows()]
        monies += [as_money(q.bid) for q in lake.rows("RecordQuotes")]
        cash = feed.contracts.cash_id
        assert cash, "the cash resolved once a subject was named"
        if v.STABLE:
            assert all((m.instrument_id, m.currency_code) == (cash, "") for m in monies)
        else:
            assert all((m.currency_code, m.instrument_id) == (v.CASH, "") for m in monies)

    async def test_an_answer_read_again_unchanged_is_the_same_row(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await feed.record_live([subject])
        await feed.record_live([subject])
        assert feed.counts.recorded == 4 and feed.counts.unchanged == 4, feed.counts

    async def test_a_price_beyond_the_payout_is_left_unrecorded_and_counted(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        real_top = feed.market.top

        def past(contract: Any) -> Any:
            return replace(real_top(contract), ask=Decimal("1.5"))

        feed.market.top = past  # type: ignore[method-assign]
        await feed.record_live([subject])
        assert not self._amounts(lake.rows(), ops.PRICE_KIND_ASK)
        [quote] = lake.rows("RecordQuotes")
        assert not quote.HasField("ask") and feed.counts.unread >= 1

    async def test_only_the_contracts_wanted_are_read_never_the_venues_list(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await feed.record_live([subject])
        asked = v.calls(feed.market)
        assert asked and all(v.BASE in url for url in asked), asked
        assert not lake.instruments.records.keys() - {subject, feed.contracts.cash_id}, (
            "no record minted but the cash's"
        )

    async def test_a_custodians_symbol_is_named_and_joined_with_the_offers(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = lake.instruments.hold(
            "INS-HELD", ops.Identifier(scheme="symbol", value=v.BASE, source=OTHER)
        )
        declined = await feed.record_live([subject], data_type=PRICE)
        assert not declined and feed.contracts.subjects == {subject: v.BASE}
        kept = lake.instruments.records[subject]
        assert any((i.scheme, i.value, i.source) == ("symbol", v.BASE, v.VENUE) for i in kept)
        stated_class, stated_type, words = lake.instruments.offered[subject]
        assert stated_class == ops.ASSET_CLASS_EVENT_CONTRACT
        assert stated_type == ops.INSTRUMENT_TYPE_BINARY_EVENT_CONTRACT
        assert words, "the venue's words offered as its description"

    async def test_a_record_already_complete_is_not_resolved_again(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        contract = await feed.contract(v.BASE)
        assert contract is not None
        # Complete: every identifier the plugin states -- the symbol, and the
        # ticker with the venue's MIC or VEN- ID as source (ruling 312).
        subject = lake.instruments.hold(
            "INS-DONE", *await feed.stated_identifiers(contract),
            asset_class=ops.ASSET_CLASS_EVENT_CONTRACT,
            instrument_type=ops.INSTRUMENT_TYPE_BINARY_EVENT_CONTRACT,
        )  # fmt: skip
        await feed.record_live([subject], data_type=PRICE)
        resolved = [r for r in lake.on("ResolveIdentifier") if r.stated_instrument_type]
        assert not resolved and lake.rows()

    async def test_a_security_or_another_type_is_never_named_by_anothers_symbol(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        symbol = ops.Identifier(scheme="symbol", value=v.BASE, source=OTHER)
        equity = lake.instruments.hold("INS-EQ", symbol, asset_class=ops.ASSET_CLASS_EQUITY)
        fund = lake.instruments.hold(
            "INS-MMF", symbol, asset_class=ops.ASSET_CLASS_EVENT_CONTRACT,
            instrument_type=ops.INSTRUMENT_TYPE_MONEY_MARKET_FUND,
        )  # fmt: skip
        declined = await feed.record_live([equity, fund])
        assert declined == {equity: "not_covered", fund: "not_covered"}
        assert not v.calls(feed.market), "nothing asked of the venue for either"

    async def test_a_market_the_venue_does_not_state_as_binary_is_not_covered(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        contract = await feed.contract(v.NOT_BINARY)
        assert contract is not None and not contract.binary
        subject = lake.instruments.hold("INS-RANGE", *feed.identifiers(contract))
        unknown = lake.instruments.hold(
            "INS-NONE", ops.Identifier(scheme="symbol", value="NOT-A-CONTRACT", source=OTHER)
        )
        declined = await feed.record_live([subject, unknown])
        assert declined == {subject: "not_covered", unknown: "not_covered"}
        assert set(feed.unnamed.values()) == {sys.modules[type(feed).__module__].NOT_A_CONTRACT}

    async def test_a_payout_the_record_states_otherwise_is_not_served(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE, attributes=payout("1", currency_code="EUR"))
        double = await lake.held(feed, v.EXACT, attributes=payout("2", currency_code=v.CASH))
        declined = await feed.record_live([subject, double])
        assert declined == {subject: "not_covered", double: "not_covered"}
        v.page.hold(feed)
        assert v.page.datasets_now().payouts_differ == 2

    async def test_a_payout_the_record_states_as_the_venues_is_served(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        cash = await feed.cash_id()
        by_code = payout("1", currency_code=v.CASH) if not v.STABLE else None
        stated = by_code or payout("1.0", instrument_id=cash)
        subject = await lake.held(feed, v.BASE, attributes=stated)
        by_id = await lake.held(feed, v.EXACT, attributes=payout(v.PAYOUT, instrument_id=cash))
        declined = await feed.record_live([subject, by_id], data_type=PRICE)
        assert not declined
        assert {r.meta.subjects[0].entity_id for r in lake.rows()} == {subject, by_id}

    async def test_wants_are_recorded_against_or_declined_with_why(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        past, coming = v.TODAY - timedelta(days=2), v.TODAY + timedelta(days=3)
        live = event_contracts.LIVE
        for want_id, day, subjects in (
            ("WNT-1", None, [subject, "LCL-NOT-COVERED"]),
            ("WNT-2", past, [subject]),
            ("WNT-3", coming, [subject]),
            ("WNT-4", v.TODAY, [subject]),
        ):
            await hear(lake, feed, wanted(feed, want_id, live, subjects, day=day))
        await hear(lake, feed, wanted(feed, "WNT-5", live, [subject], data_type=BAR))
        await hear(lake, feed, wanted(feed, "WNT-6", "daily", [subject]))
        assert {p.want_id for p in lake.on("RecordPrices")} == {"WNT-1", "WNT-4"}
        declined = {(d.want_id, s.entity_id, d.reason) for d in lake.on("DeclineWant")
                    for s in d.subjects}  # fmt: skip
        assert declined == {
            ("WNT-1", "LCL-NOT-COVERED", ops.UNANSWERED_REASON_NOT_COVERED),
            ("WNT-2", subject, ops.UNANSWERED_REASON_BEYOND_HISTORY),
            ("WNT-3", subject, ops.UNANSWERED_REASON_SOURCE_SILENT),
            ("WNT-5", subject, ops.UNANSWERED_REASON_NOT_COVERED),
            ("WNT-6", subject, ops.UNANSWERED_REASON_NOT_COVERED),
        }
        assert [h.want_id for h in feed.heard][:2] == ["WNT-6", "WNT-5"]

    async def test_a_quotes_want_records_quotes_against_it(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await hear(lake, feed, wanted(feed, "WNT-Q", event_contracts.LIVE, [subject],
                                      data_type=QUOTE))  # fmt: skip
        [sent] = lake.on("RecordQuotes")
        assert sent.want_id == "WNT-Q" and not lake.on("RecordPrices")

    async def test_a_contract_with_nothing_stated_is_declined_source_silent(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.ONE_SIDED)
        declined = await feed.record_live(
            [subject], kinds=[ops.PRICE_KIND_LAST], data_type=PRICE
        )
        assert declined == {subject: "source_silent"}

    async def test_a_standing_want_is_kept_current_until_withdrawn(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        event = wanted(feed, "WNT-9", event_contracts.LIVE, [subject], data_type=QUOTE,
                       standing=True)  # fmt: skip
        await hear(lake, feed, event)
        assert set(feed.standing) == {"WNT-9"}
        before = len(lake.on("RecordQuotes"))
        await feed.current()
        assert len(lake.on("RecordQuotes")) == before + 1
        lake.answer("WantWithdrawn", lambda _: [ops.WantWithdrawnEvent(want_id="WNT-9")])
        await lake.receive(want_withdrawn=feed.on_withdrawn)
        await feed.current()
        assert not feed.standing and len(lake.on("RecordQuotes")) == before + 1

    async def test_keep_current_paces_itself_and_survives_a_failure(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        feed.standing["WNT-K"] = Standing(
            "WNT-K", feed.dataset(event_contracts.LIVE), PRICE, (subject,),
            (ops.PRICE_KIND_LAST,), v.NOW_NS,
        )  # fmt: skip
        slept: list[float] = []

        def down(contract: Any) -> Any:
            raise OSError("down")

        async def sleep(seconds: float) -> None:
            slept.append(seconds)
            if len(slept) == 1:
                feed.market.last = down  # type: ignore[method-assign]
            if len(slept) == 3:
                raise RuntimeError("stop")

        with contextlib.suppress(RuntimeError):
            await feed.keep_current(sleep=sleep)
        assert slept == [1.0, 1.0, 1.0] and self._amounts(lake.rows(), ops.PRICE_KIND_LAST)

    async def test_the_venue_resolved_names_each_row(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await feed.record_live([subject])
        [asked] = lake.on("ResolveVenue")
        named = {(i.scheme, i.value, i.source) for i in asked.identifiers}
        assert named == set(feed.market.venue_identifiers)
        assert all(r.meta.source.venue_id == feed.venue.venue_id != "" for r in lake.rows())

    async def test_a_venue_not_held_is_left_empty_and_named_as_reported(self) -> None:
        v, lake = self.venue, self.lake()
        lake.answer("ResolveVenue", lambda _: ops.ResolveVenueResult(found=False))
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await feed.record_live([subject])
        await feed.record_live([subject])
        assert len(lake.on("ReportMissingVenue")) == 1, "reported once"
        for row in lake.rows():
            assert row.meta.source.venue_id == ""
            assert [u.scheme for u in row.meta.unconverted] == [f"{v.VENUE}:venue"]

    async def test_reading_again_asks_the_venue_and_each_contract_again(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await feed.record_live([subject])
        await feed.reread()
        assert len(lake.on("ResolveVenue")) == 2 and feed.contracts.read_at_ns == v.NOW_NS

    async def test_the_cash_not_resolving_is_reported_once_and_nothing_priced(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        for n in (1, 2):
            lake.instruments.hold(f"INS-CASH-{n}", *feed.cash_identifiers())
        subject = await lake.held(feed, v.BASE)
        for _ in range(2):
            assert await feed.record_live([subject]) == {subject: "not_covered"}
        [missed] = lake.on("ReportMissingInstrument")
        assert missed.reason == ops.MISS_REASON_AMBIGUOUS and not lake.rows()

    async def test_a_record_that_cannot_be_read_names_nothing(self) -> None:
        lake = self.lake()

        def refused(_: Any) -> Any:
            raise NotGranted("ResolveInstrument", "not granted to a data plugin")

        lake.answer("ResolveInstrument", refused)
        feed = self.feed(lake)
        declined = await feed.record_live(["INS-ANY", "INS-OTHER"])
        assert declined == {"INS-ANY": "not_covered", "INS-OTHER": "not_covered"}
        assert feed.reads_instruments is False and len(lake.on("ResolveInstrument")) == 1

    async def test_the_contract_map_is_kept_and_read_back(self, tmp_path: Path) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        feed.contracts = event_contracts.ContractMap(tmp_path / "contracts-synthetic.json")
        subject = await lake.held(feed, v.BASE)
        await feed.record_live([subject])
        again = event_contracts.ContractMap(tmp_path / "contracts-synthetic.json")
        assert again.load()
        assert again.subjects == feed.contracts.subjects
        assert again.cash_id == feed.contracts.cash_id
        assert again.contracts[v.BASE] == feed.contracts.contracts[v.BASE]
        assert str(again.contracts[v.BASE].payout) == v.PAYOUT

    async def test_licences_not_answered_leave_it_not_licensed_yet(self) -> None:
        lake = self.lake()

        def refused(_: Any) -> Any:
            raise NotGranted("platform.lake.query.list-datasets", "not granted")

        lake.answer("ListDatasets", refused)
        feed = self.feed(lake)
        assert await feed.read_licences() == frozenset() and feed.wants.reads_licences is False
        assert await feed.read_licences() == frozenset(), "asked once, then said"

    async def test_what_it_recorded_is_counted_with_when(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await hear(lake, feed, wanted(feed, "WNT-1", event_contracts.LIVE, [subject]))
        assert feed.counts.recorded > 0 and feed.counts.last_ns == v.NOW_NS

    # ── Outcomes (contract v23) ─────────────────────────────────────────

    async def _resolved(self, lake: Lake, feed: Any, code: str) -> str:
        """A subject named as one of the venue's contracts, its outcome
        recorded."""
        subject = await lake.held(feed, code)
        await feed.record_live([subject], data_type=PRICE)
        return subject

    @staticmethod
    def _outcome(row: Any) -> tuple[str, str]:
        return (ops.OutcomeDetermination.Name(row.determination),
                ops.OutcomeStage.Name(row.stage))  # fmt: skip

    async def test_a_resolved_contract_records_its_outcome_from_its_own_side(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await self._resolved(lake, feed, v.RESOLVED)
        [row] = lake.rows("RecordOutcomes")
        assert self._outcome(row) == ("OUTCOME_DETERMINATION_PAYS", v.RESOLVED_STAGE)
        assert as_decimal(row.settlement_value.amount) == Decimal(v.PAYOUT)
        reported = row.determination_as_reported
        assert (reported.scheme, reported.code) == v.WORD
        assert row.meta.row_key == f"{v.RESOLVED}:outcome"
        assert row.meta.source.dataset == f"{v.VENUE}:outcomes"
        assert row.meta.subjects[0].entity_id == subject and not row.meta.business_date
        assert row.meta.raw.key.startswith("responses/") and row.meta.valid_from_ns > 0
        assert feed.outcome_counts.recorded == 1

    async def test_a_contract_that_pays_nothing_settles_at_nothing(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        await self._resolved(lake, feed, v.RESOLVED_LOSER)
        [row] = lake.rows("RecordOutcomes")
        determination = ops.OutcomeDetermination.Name(row.determination)
        assert determination == "OUTCOME_DETERMINATION_PAYS_NOTHING"
        assert as_decimal(row.settlement_value.amount) == 0

    async def test_a_partial_payout_settles_at_its_part(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        await self._resolved(lake, feed, v.PARTIAL)
        [row] = lake.rows("RecordOutcomes")
        determination = ops.OutcomeDetermination.Name(row.determination)
        assert determination == "OUTCOME_DETERMINATION_PAYS_PART"
        assert str(as_decimal(row.settlement_value.amount)) == v.PARTIAL_VALUE

    async def test_an_outcome_stated_again_unchanged_sends_nothing_even_after_a_restart(
        self, tmp_path: Path
    ) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        feed.contracts = event_contracts.ContractMap(tmp_path / "contracts-synthetic.json")
        subject = await self._resolved(lake, feed, v.RESOLVED)
        await feed.record_live([subject], data_type=PRICE)
        assert await feed.watch_outcomes() == 0
        again = self.feed(lake)
        again.contracts = event_contracts.ContractMap(tmp_path / "contracts-synthetic.json")
        assert again.contracts.load()
        assert await again.watch_outcomes() == 0 and await again.reread() is again.contracts
        assert len(lake.rows("RecordOutcomes")) == 1

    async def test_each_later_stage_is_a_new_version_valid_from_the_determination(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        await self._resolved(lake, feed, v.RESOLVED)
        [first] = lake.rows("RecordOutcomes")
        for directory, stage, settled_at_ns in v.LATER:
            feed.market = v.market(v.NOW_NS, directory=directory)
            assert await feed.watch_outcomes() == 1
            row = lake.rows("RecordOutcomes")[-1]
            assert (
                ops.OutcomeStage.Name(row.stage) == stage and row.settled_at_ns == settled_at_ns
            )
            assert row.meta.row_key == first.meta.row_key
            assert row.meta.valid_from_ns == first.meta.valid_from_ns
            assert row.determination == first.determination
        assert lake.versions[("outcome", first.meta.row_key)][0] == 1 + len(v.LATER)

    async def test_a_contract_past_its_close_not_yet_determined_records_nothing(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        await self._resolved(lake, feed, v.PENDING)
        asked = feed.market.session.health.calls
        assert await feed.watch_outcomes() == 0
        assert feed.market.session.health.calls == asked + 1, "read again, past its close"
        assert not lake.on("RecordOutcomes")

    async def test_a_contract_still_trading_or_final_is_not_read_again(self) -> None:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        await self._resolved(lake, feed, v.BASE)
        asked = feed.market.session.health.calls
        assert await feed.watch_outcomes() == 0
        assert feed.market.session.health.calls == asked, "trading before its close"
        await self._resolved(lake, feed, v.RESOLVED)
        for directory, _, _ in v.LATER:
            feed.market = v.market(v.NOW_NS, directory=directory)
            await feed.watch_outcomes()
        asked = feed.market.session.health.calls
        assert await feed.watch_outcomes() == 0
        assert feed.market.session.health.calls == asked, "final: not read again"

    # ── Its pages ───────────────────────────────────────────────────────

    async def worked(self) -> tuple[Any, Lake]:
        v, lake = self.venue, self.lake()
        feed = self.feed(lake)
        subject = await lake.held(feed, v.BASE)
        await hear(lake, feed, wanted(feed, "WNT-1", event_contracts.LIVE, [subject]))
        await hear(lake, feed, wanted(feed, "WNT-2", event_contracts.LIVE, [subject],
                                      data_type=QUOTE, standing=True))  # fmt: skip
        v.page.hold(feed)
        return feed, lake

    def shown(self, lake: Lake) -> set[str]:
        figures = {str(as_decimal(r.price.amount)) for r in lake.rows()}
        for quote in lake.rows("RecordQuotes"):
            figures |= {str(as_decimal(getattr(quote, f).amount)) for f in ("bid", "ask")
                        if quote.HasField(f)}  # fmt: skip
            figures |= {str(as_decimal(getattr(quote, f))) for f in ("bid_quantity",
                        "ask_quantity") if quote.HasField(f)}  # fmt: skip
        return figures

    def test_each_page_holds_the_roles_sections_in_its_order(self) -> None:
        self.ran()
        client = PageClient(self.venue.page.pages)
        # "Sessions" only once a session is measured (0.32.2).
        measured = client.call_tool("read_connection", level="admin").data["session_latency"]
        assert _sections(client.get("/", "admin").text) == [
            "Key",
            "Limits and use",
            "Stream",
        ] + (["Sessions"] if measured else [])
        assert _sections(client.get("/datasets", "admin").text) == [
            "Served", "Wants", "Subjects", self.venue.page.TITLE,
        ]  # fmt: skip

    def test_the_tools_answer_what_the_pages_show(self) -> None:
        v = self.venue
        feed, _ = self.ran()
        client = PageClient(v.page.pages)
        assert {t.name for t in v.page.pages.tools} >= set(TOOLS)
        connection = client.call_tool("read_connection", level="admin")
        assert connection.outcome == "unchanged", connection.json
        data = connection.data
        assert (data["mode"], data["credentials"], data["entitled_at_vendor"]) == (
            "Sample data", [], v.page.ENTITLED,
        )  # fmt: skip
        assert data["calls"] > 0 and data["last_call_at"] and data["sessions"] is None
        assert (data["venue"], data["venue_id"], data["healthy"]) == (
            feed.market.name, feed.venue.venue_id, True,
        )  # fmt: skip
        page = client.get("/", "admin").text.replace("&#39;", "'")
        assert "No key needed" in page and "Does not stream" in page
        assert feed.venue.venue_id in page and data["allowed"] in page
        datasets = client.call_tool("read_datasets", level="admin").data
        assert [d["dataset"] for d in datasets["served"]] == [
            f"{v.VENUE}:live", f"{v.VENUE}:outcomes",
        ]  # fmt: skip
        assert [d["data"] for d in datasets["served"]] == ["Price, Quote", "Outcome"]
        assert [d["arrives"] for d in datasets["served"]] == ["pull, stream", "push"]
        assert datasets["served"][1]["default_terms"].startswith("kept"), "outcomes are kept"
        assert all(d["day"] == "Etc/UTC, ends 00:00" for d in datasets["served"])
        assert datasets["served"][0]["recorded"] > 0 and datasets["served"][0]["last_recorded"]
        assert datasets["served"][1]["recorded"] == 0, "no contract it serves is determined"
        assert datasets["standing_wants"] == 1
        assert [(w["want_id"], w["kept_current"]) for w in datasets["wants"]] == [
            ("WNT-2", True),
            ("WNT-1", False),
        ]
        assert (datasets["contracts_mapped"], datasets["subjects_named"]) == (1, 1)
        assert datasets["cash"] == v.CASH
        assert datasets["cash_instrument"] == feed.contracts.cash_id
        assert datasets["payouts"] == [f"{v.PAYOUT} {v.CASH}"]
        assert datasets["reads_instruments"] is True
        shown = client.get("/datasets", "admin").text.replace("&#39;", "'")
        assert "1 contract mapped for 1 subject the lake asked for" in shown
        assert f"each contract pays {v.PAYOUT} {v.CASH}" in shown
        assert feed.contracts.cash_id in shown and "Kept current" in shown
        assert datasets["vendor_note"] in shown

    def test_datasets_says_whether_a_deployment_admin_licensed_it(self) -> None:
        feed, _ = self.ran()
        client = PageClient(self.venue.page.pages)
        served = client.call_tool("read_datasets", level="admin").data["served"]
        assert served[0]["licensed"] is False
        assert "Not licensed yet" in client.get("/datasets", "admin").text
        feed.licensed = frozenset(
            {feed.dataset(event_contracts.LIVE), feed.dataset(event_contracts.OUTCOMES)}
        )
        served = client.call_tool("read_datasets", level="admin").data["served"]
        assert [d["licensed"] for d in served] == [True, True]
        shown = client.get("/datasets", "admin").text
        assert "Not licensed yet" not in shown and "Licensed" in shown

    def test_an_outcome_recorded_counts_on_its_own_dataset(self) -> None:
        feed, lake = self.ran()
        live = feed.counts.recorded

        async def resolved() -> None:
            subject = await lake.held(feed, self.venue.RESOLVED)
            await feed.name([subject])
            await feed.record_outcomes([feed.contracts.serving(subject)])

        asyncio.run(resolved())
        tool = PageClient(self.venue.page.pages).call_tool("read_datasets", level="admin")
        served = tool.data["served"]
        assert [d["recorded"] for d in served] == [live, 1] and served[1]["last_recorded"]

    def test_the_roles_figures_in_its_order(self) -> None:
        self.ran()
        figures = self.venue.page.figures_now()
        assert [f.label for f in figures] == [
            "Connection", "Entitled at the vendor", "Stream", "Last recorded",
        ]  # fmt: skip
        assert [f.value for f in figures[:3]] == ["Sample data", "2 of 2 datasets",
                                                 "Does not stream"]  # fmt: skip
