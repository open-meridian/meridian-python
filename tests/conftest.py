"""A sidecar that answers, so the client can be tested without a runtime.

Deliberately not a mock. It is a real gRPC server on a real socket speaking the
real generated stubs, because the things worth catching here are wire-level:
a field set on the wrong message, a stream that does not terminate, a status
code the client does not translate. A mock would agree with whatever the client
did and prove nothing.

What it does not do is enforce anything. It refuses what a test tells it to
refuse. Access control is the sidecar's job and is tested in meridian-core
against the real grant table; repeating a weaker version of it here would make
this suite look like it covers something it does not.

It does keep the tickets filed on it (contract v13), folding a repeat under an
open ticket's key as the dashboard does, so a filing can be followed through
to what the plugin reads back; and, as the sidecar does, it refuses a filing
or a read made for nobody, since the client's shape rests on that refusal.

And it keeps the custodian's activity and each sync status reported on it
(contract v14), as the street keeps them, so what one plugin reports another
reads back and hears: an activity once per source, account and
`external_activity_id`, a redelivery answered `already_recorded`; every sync
status heard; each numbered in the street's partition, against the account
`links` names for its external account, or none. From contract v15 it keeps
each re-resolution beside the activity as first recorded, numbered apart from
the activities, one naming what the latest resolution names answered
`already_recorded`, and one of nothing recorded refused as the street refuses
it; and reads them back in `re_resolutions`.

And it holds what a plugin declares to the roles it was launched with, as the
sidecar does at registration (W4.1, contract v15), in the sidecar's words: a
page or setting naming a role it does not hold refuses the registration, and
so, on a plugin built at v15 holding several roles, does one naming none;
what it admits it keeps with its roles filled, as the sidecar reports them.
Its access table carries one entry per role it was launched with.

And from contract v16 it records the moves of raw records reported on it
(W4.13), as the conductor records them: each with the person it was made
for, or none for a window's move. It holds a move to the kinds the plugin
declared, as the sidecar does, and enforces the hold over the instance
(`hold_days`): a deletion whose last record was received inside it is
refused FAILED_PRECONDITION with REFUSAL_REASON_WITHIN_HOLD, nothing
recorded. A restore is for a person, and deleting an archived unit an
admin's act: refused PERMISSION_DENIED for nobody. `read_moves` answers
core's ReadMoves from what it recorded, newest first, with the archive's
spans per kind summed from the moves, which carry no bytes, as the
conductor's carry none. A heartbeat's `stored` is held as core's sidecar
holds it: one entry per declared kind, at most 16, no span without records,
refused INVALID_ARGUMENT naming the field otherwise; any `bytes` (what the
kind uses of the archive) accepted, with records in storage or none; and
`report_stored` answers what the last accepted one said, as the plugin's
report carries it to the Summary.

And from contract v18 it mirrors the lake (W10), as core's sidecar and lake
answer it. A `dgm`'s catalogue is held from its registration, refused from a
plugin not launched with `dgm`. A batch of prices or bars is recorded whole
or refused, INVALID_ARGUMENT naming the item and field, as the sidecar
refuses one: 1 to 500 rows; a dataset the instance's catalogue does not
declare; no subject, no row key; a date that is no date; a venue the
deployment does not hold; a Money naming no asset, a code that is no ISO
4217 code it holds (a token's), or a code and an instrument naming two
assets; a bar's amounts in two assets. Each Money is resolved, dated, to its
cash instrument (`cash`, each code's instruments by the date from which it
holds), and kept naming it. A row is recorded once per dataset and row key:
the same values again (by decimal value, 764.2 equal to 764.20) change
nothing, a changed one is the next version; each is stamped with the
instance, sequenced in its dataset from 1, chained per subject, data type and
dataset, and given the time it was recorded (`clock`), and published
(`published`, as PricesRecorded and BarsRecorded, for a test to deliver). The
reads answer by business date, at a valid time (the latest in force) or over
a range, as of a recorded time, from the default dataset per subject (the
first in `priority`, then the catalogue's order, that holds one), named
datasets in order, or side by side; with each dataset named once and each
subject no dataset covers unanswered. Venues resolve by their identifiers
(`venues`); a miss is reported. A want's decline is kept (`declined`).

And it answers ResolveInstrument (W3.6) from the deployment's records
(`instruments`), as the instrument store does, to any role that asks: a
dgm reads the record of an instrument another source resolved (contract
v18, ruled 2026-10-10) -- a custodian's QQQ, by its symbol and CUSIP --
and a record the store does not hold is not found. Who may ask is the
sidecar's to enforce, tested in meridian-core.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import grpc
import pytest
import pytest_asyncio

from meridian.plugin.v1 import operations_pb2, operations_pb2_grpc
from meridian.v1 import sidecar_pb2, sidecar_pb2_grpc


@dataclass
class Stream:
    """One opening of the delivery stream, as a test scripts it: what is sent
    in order, and then whether it breaks (a status) or stays open."""

    deliveries: list[operations_pb2.Delivery] = field(default_factory=list)
    breaks: grpc.StatusCode | None = None


@dataclass
class FakeOperations(operations_pb2_grpc.PluginOperationsServicer):
    """The typed operations, answering fixed results and keeping what was sent."""

    refuse: tuple[grpc.StatusCode, str] | None = None
    # Sent beside the refusal, as the sidecar sends a refusal's code.
    refuse_metadata: tuple[tuple[str, bytes], ...] = ()
    sent: list[object] = field(default_factory=list)

    # The delivery stream, one script per opening, the last kept open; and
    # the reads a catch-up makes, answered by `store` (W2.7, W2.9).
    streams: list[Stream] = field(default_factory=list)
    receive_refused: tuple[grpc.StatusCode, str] | None = None
    received: list[operations_pb2.ReceiveRequest] = field(default_factory=list)
    store: object | None = None
    reads: list[object] = field(default_factory=list)

    # The custodian's activity and each sync status (W2.10 to W2.14), kept as
    # the street keeps them; the account an external account is linked to.
    links: dict[str, str] = field(default_factory=lambda: {"SNAP-ACC-1": "ACC-1"})
    activities: list[operations_pb2.ActivityRecordedEvent] = field(default_factory=list)
    sync_statuses: list[operations_pb2.SyncStatusRecordedEvent] = field(default_factory=list)
    head: int = 0
    # Each re-resolution of an activity (W2.15, W2.16, contract v15), kept
    # beside it: numbered in the street's partition, chained per account
    # apart from the activities.
    re_resolutions: list[operations_pb2.ActivityReResolution] = field(default_factory=list)
    # The lake (W10, contract v18).
    lake: FakeLake = field(default_factory=lambda: FakeLake())
    # The deployment's instrument records, as ResolveInstrument answers them.
    instruments: dict[str, operations_pb2.InstrumentRecord] = field(
        default_factory=lambda: dict(INSTRUMENTS)
    )

    async def _lake(self, params, context, answer):
        """A lake call kept as sent and answered, or refused as the sidecar
        refuses it: INVALID_ARGUMENT, naming the field."""
        self.sent.append(params)
        if self.refuse is not None:
            await context.abort(*self.refuse, trailing_metadata=self.refuse_metadata)
        try:
            return answer()
        except LakeRefused as refused:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(refused))

    async def RecordPrices(self, request, context):  # noqa: N802
        return await self._lake(
            request, context, lambda: self.lake.record(list(request.prices), "prices")
        )

    async def RecordBars(self, request, context):  # noqa: N802
        return await self._lake(
            request, context, lambda: self.lake.record(list(request.bars), "bars")
        )

    async def ListPrices(self, request, context):  # noqa: N802
        self.reads.append(request)
        return await self._lake(
            request, context, lambda: self.lake.read(request, operations_pb2.Price, "prices")
        )

    async def ListBars(self, request, context):  # noqa: N802
        self.reads.append(request)
        return await self._lake(
            request, context, lambda: self.lake.read(request, operations_pb2.Bar, "bars")
        )

    async def ListDatasets(self, request, context):  # noqa: N802
        self.reads.append(request)
        return await self._lake(request, context, self.lake.listing)

    async def DeclineWant(self, request, context):  # noqa: N802
        def declined() -> object:
            if not 1 <= len(request.subjects) <= 500:
                raise LakeRefused("subjects: a decline names 1 to 500 subjects")
            self.lake.declined.append(request)
            return operations_pb2.DeclineWantResult()

        return await self._lake(request, context, declined)

    async def ResolveVenue(self, request, context):  # noqa: N802
        return await self._lake(request, context, lambda: self.lake.resolve_venue(request))

    async def ReportMissingVenue(self, request, context):  # noqa: N802
        def missed() -> object:
            self.lake.missed_venues.append(request)
            return operations_pb2.Published(
                message_id=f"msg-venue-{len(self.lake.missed_venues)}"
            )

        return await self._lake(request, context, missed)

    async def Receive(self, request, context):  # noqa: N802
        self.received.append(request)
        if self.receive_refused is not None:
            await context.abort(*self.receive_refused)
        await context.send_initial_metadata(())
        opening = len(self.received) - 1
        script = self.streams[opening] if opening < len(self.streams) else Stream()
        for delivery in script.deliveries:
            yield delivery
        if script.breaks is not None:
            await context.abort(script.breaks, "the stream broke")
        await asyncio.Event().wait()

    async def ListCustodialPositions(self, request, context):  # noqa: N802
        self.reads.append(request)
        return self.store.positions(request)  # type: ignore[union-attr]

    async def ListStatements(self, request, context):  # noqa: N802
        self.reads.append(request)
        return self.store.statements(request)  # type: ignore[union-attr]

    async def _answer(
        self, params: object, answer: object, context: grpc.aio.ServicerContext
    ) -> object:
        self.sent.append(params)
        if self.refuse is not None:
            await context.abort(*self.refuse, trailing_metadata=self.refuse_metadata)
        return answer

    async def ReportExternalAccounts(self, request, context):  # noqa: N802
        return await self._answer(
            request, operations_pb2.Published(message_id="msg-0"), context
        )

    async def ReportSyncStatus(self, request, context):  # noqa: N802
        if self.refuse is None:
            status = operations_pb2.SyncStatusEvent.FromString(
                request.SerializeToString(deterministic=True)
            )
            status.account_id = self.links.get(request.external_account_id, "")
            journal, cause = self._numbered()
            self.sync_statuses.append(
                operations_pb2.SyncStatusRecordedEvent(
                    status=status,
                    recorded_at_ns=cause.committed_at_ns,
                    journal=journal,
                    cause=cause,
                )
            )
        return await self._answer(
            request, operations_pb2.Published(message_id="msg-1"), context
        )

    def _numbered(self) -> tuple[operations_pb2.JournalRef, operations_pb2.ChangeCause]:
        """The next number in the street's partition, and its cause."""
        previous, self.head = self.head, self.head + 1
        journal = operations_pb2.JournalRef(
            partition="street", sequence=self.head, previous_sequence=previous
        )
        cause = operations_pb2.ChangeCause(
            instance_id="custody-snaptrade-1",
            causation_id=f"msg-{self.head}",
            committed_at_ns=1_791_100_800_000_000_000 + self.head,
        )
        return journal, cause

    def _as_of(self) -> operations_pb2.Watermark:
        return operations_pb2.Watermark(
            partitions=[
                operations_pb2.PartitionSequence(partition="street", sequence=self.head)
            ]
        )

    async def RecordActivity(self, request, context):  # noqa: N802
        account = self.links.get(request.external_account_id, "")
        key = (request.source, account, request.activity.external_activity_id)
        held = next(
            (
                a
                for a in self.activities
                if (a.source, a.account_id, a.activity.external_activity_id) == key
            ),
            None,
        )
        if held is not None:
            answer = operations_pb2.RecordActivityResult(
                activity_id=held.activity_id, already_recorded=True
            )
        else:
            answer = operations_pb2.RecordActivityResult(
                activity_id=f"ACT-{len(self.activities) + 1}"
            )
            if self.refuse is None:
                journal, cause = self._numbered()
                self.activities.append(
                    operations_pb2.ActivityRecordedEvent(
                        activity_id=answer.activity_id,
                        account_id=account,
                        external_account_id=request.external_account_id,
                        source=request.source,
                        activity=request.activity,
                        recorded_at_ns=cause.committed_at_ns,
                        journal=journal,
                        cause=cause,
                    )
                )
        return await self._answer(request, answer, context)

    async def ReResolveActivity(self, request, context):  # noqa: N802
        """The activity named by source, the linked account and the
        custodian's identifier, re-resolved beside its first record; one
        naming what the latest resolution names is already recorded, and one
        of nothing recorded is refused, ABORTED, as the street refuses it."""
        account = self.links.get(request.external_account_id, "")
        key = (request.source, account, request.external_activity_id)
        held = next(
            (
                a
                for a in self.activities
                if (a.source, a.account_id, a.activity.external_activity_id) == key
            ),
            None,
        )
        self.sent.append(request)
        if self.refuse is not None:
            await context.abort(*self.refuse, trailing_metadata=self.refuse_metadata)
        if held is None:
            await context.abort(
                grpc.StatusCode.ABORTED,
                f"no activity is recorded as {request.external_activity_id} from "
                f"{request.source} on {account}; a re-resolution re-resolves an activity "
                "already recorded",
            )
        latest = next(
            (
                r.instrument_id
                for r in reversed(self.re_resolutions)
                if r.activity_id == held.activity_id
            ),
            held.activity.instrument_id,
        )
        if latest == request.instrument_id:
            return operations_pb2.ReResolveActivityResult(
                activity_id=held.activity_id, already_recorded=True
            )
        journal, cause = self._numbered()
        journal.previous_sequence = next(
            (
                r.journal.sequence
                for r in reversed(self.re_resolutions)
                if r.account_id == account
            ),
            0,
        )
        self.re_resolutions.append(
            operations_pb2.ActivityReResolution(
                activity_id=held.activity_id,
                account_id=account,
                instrument_id=request.instrument_id,
                provenance=request.provenance,
                resolved_at_ns=request.resolved_at_ns,
                recorded_at_ns=cause.committed_at_ns,
                journal=journal,
            )
        )
        return operations_pb2.ReResolveActivityResult(activity_id=held.activity_id)

    async def ListActivities(self, request, context):  # noqa: N802
        """By trade date, inclusive, or since a watermark in the order
        recorded; paged; with the named account's `history_from` as its
        latest sync status said it; and the re-resolutions beside the
        activities answered, or, since a watermark, every one after it."""
        self.reads.append(request)
        found = [
            a
            for a in self.activities
            if (not request.account_id or a.account_id == request.account_id)
            and (
                not request.trade_date_from or a.activity.trade_date >= request.trade_date_from
            )
            and (not request.trade_date_to or a.activity.trade_date <= request.trade_date_to)
        ]
        if request.HasField("since"):
            since = request.since.partitions[0].sequence
            found = [a for a in found if a.journal.sequence > since]
            re_resolved = [
                r
                for r in self.re_resolutions
                if (not request.account_id or r.account_id == request.account_id)
                and r.journal.sequence > since
            ]
        else:
            found.sort(key=lambda a: (a.activity.trade_date, a.journal.sequence))
        page, following = _page(found, request.page_size, request.cursor)
        if not request.HasField("since"):
            answered = {a.activity_id for a in page}
            re_resolved = [r for r in self.re_resolutions if r.activity_id in answered]
        history_from = next(
            (
                s.status.history_from
                for s in reversed(self.sync_statuses)
                if request.account_id and s.status.account_id == request.account_id
            ),
            "",
        )
        return operations_pb2.ListActivitiesResult(
            activities=page,
            next_cursor=following,
            as_of=self._as_of(),
            history_from=history_from,
            re_resolutions=re_resolved,
        )

    async def ListSyncStatuses(self, request, context):  # noqa: N802
        """The latest of each connection, or every one since a watermark in
        the order recorded; paged."""
        self.reads.append(request)
        found = [
            s
            for s in self.sync_statuses
            if not request.account_id or s.status.account_id == request.account_id
        ]
        if request.HasField("since"):
            since = request.since.partitions[0].sequence
            found = [s for s in found if s.journal.sequence > since]
        else:
            latest = {
                (s.status.account_id, s.status.source, s.status.external_account_id): s
                for s in found
            }
            found = [latest[connection] for connection in sorted(latest)]
        page, following = _page(found, request.page_size, request.cursor)
        return operations_pb2.ListSyncStatusesResult(
            statuses=page, next_cursor=following, as_of=self._as_of()
        )

    async def RecordHoldingsStatement(self, request, context):  # noqa: N802
        answer = operations_pb2.RecordHoldingsStatementResult(statement_id="S-1")
        return await self._answer(request, answer, context)

    async def RecordHolding(self, request, context):  # noqa: N802
        answer = operations_pb2.RecordHoldingResult(holding_id="H-1", resolved=True)
        return await self._answer(request, answer, context)

    async def ResolveInstrument(self, request, context):  # noqa: N802
        held = self.instruments.get(request.instrument_id)
        answer = (
            operations_pb2.ResolveInstrumentResult(found=True, instrument=held)
            if held is not None
            else operations_pb2.ResolveInstrumentResult(found=False)
        )
        return await self._answer(request, answer, context)

    async def ResolveIdentifier(self, request, context):  # noqa: N802
        answer = operations_pb2.ResolveIdentifierResult(found=True, instrument_id="INS-1")
        return await self._answer(request, answer, context)

    async def ReportMissingInstrument(self, request, context):  # noqa: N802
        return await self._answer(
            request, operations_pb2.Published(message_id="msg-2"), context
        )

    async def LinkExternalAccount(self, request, context):  # noqa: N802
        # What the conductor answers: the link, naming the account made for
        # a new account's name, or none for an unlink.
        account = request.account_id or ("ACC-NEW" if request.new_account_name else "")
        answer = operations_pb2.LinkExternalAccountResult(
            plugin_instance_id="snaptrade-1",
            external_account_id=request.external_account_id,
            account_id=account,
        )
        return await self._answer(request, answer, context)

    # The book of record (contract v8): each command answered with its entry,
    # each read from `store` where a test gives one.
    async def RecordOpeningBalance(self, request, context):  # noqa: N802
        return await self._answer(request, _entry("opening-balance"), context)

    async def RecordBreak(self, request, context):  # noqa: N802
        return await self._answer(request, _entry("break-recorded"), context)

    async def RecordAccountFigures(self, request, context):  # noqa: N802
        return await self._answer(request, _entry("figures-recorded"), context)

    async def HandleBreak(self, request, context):  # noqa: N802
        return await self._answer(request, _entry("break-handled"), context)

    async def ResolveBreak(self, request, context):  # noqa: N802
        return await self._answer(request, _entry("adjustment"), context)

    async def CloseBreaksAsCleared(self, request, context):  # noqa: N802
        return await self._answer(request, _entry("breaks-cleared"), context)

    async def RecordEncumbrances(self, request, context):  # noqa: N802
        return await self._answer(request, _entry("encumbrances-recorded"), context)

    async def ListPositions(self, request, context):  # noqa: N802
        self.reads.append(request)
        return self.store.book_positions(request)  # type: ignore[union-attr]

    async def ListBreaks(self, request, context):  # noqa: N802
        self.reads.append(request)
        return self.store.book_breaks(request)  # type: ignore[union-attr]

    async def ReadAccountsForLinking(self, request, context):  # noqa: N802
        answer = operations_pb2.ReadAccountsForLinkingResult(
            accounts=[
                operations_pb2.AccountRecord(
                    account_id="ACC-1",
                    name="Growth",
                    state=operations_pb2.ACCOUNT_STATE_OPEN,
                    custodian="Fidelity",
                    account_type="Roth IRA",
                    owner="Fund I",
                    note="Rollover, 2026.",
                )
            ]
        )
        return await self._answer(request, answer, context)


# ── The lake (contract v18) ───────────────────────────────────────────────


def _venue(venue_id: str, name: str, mic: str, kind: int, zone: str) -> object:
    return operations_pb2.VenueRecord(
        venue_id=venue_id,
        name=name,
        country_code="US",
        kind=kind,
        identifiers=[operations_pb2.Identifier(scheme="iso10383", value=mic)],
        time_zone=zone,
    )


#: The venues the fake deployment holds, by ID.
#: An instrument the book holds from a custodian, known by the custodian's
#: symbol and its CUSIP, which no dgm resolved (contract v18, W3.6).
INSTRUMENTS = {
    "LCL-01JA0000000000000QQQ1": operations_pb2.InstrumentRecord(
        instrument_id="LCL-01JA0000000000000QQQ1",
        identifiers=[
            operations_pb2.Identifier(scheme="cusip", value="46090E103"),
            operations_pb2.Identifier(scheme="symbol", value="QQQ", source="snaptrade"),
        ],
        asset_class=operations_pb2.ASSET_CLASS_FUND,
        currency="USD",
    ),
}

VENUES = {
    venue.venue_id: venue
    for venue in (
        _venue("VEN-01JA00000000000000XNAS", "Nasdaq", "XNAS", 1, "America/New_York"),
        _venue(
            "VEN-01JA00000000000000XNYS",
            "New York Stock Exchange",
            "XNYS",
            1,
            "America/New_York",
        ),
        _venue("VEN-01JA0000000000000CBEXC", "Coinbase Exchange", "CBSX", 3, "Etc/UTC"),
    )
}

#: Each ISO 4217 code's cash instrument, by the date from which it holds: a
#: currency's instrument is resolved for the date a row is about.
CASH = {
    "USD": [("1792-04-02", "LCL-CASH-USD")],
    "EUR": [("1999-01-01", "LCL-CASH-EUR")],
    "CHF": [("1850-05-07", "LCL-CASH-CHF")],
    # A redenomination: the same code, a new instrument from its date.
    "XTS": [("2000-01-01", "LCL-CASH-XTS-1"), ("2026-07-01", "LCL-CASH-XTS-2")],
}

#: What a token's code would be, which a Money's currency_code never holds.
TOKENS = {"USDC", "USDT", "BTC", "ETH"}


class LakeRefused(Exception):
    """A batch or a read refused, naming the field, as the sidecar names it."""


def _when(meta: object) -> str:
    """The date a row is about, which its Money is resolved for: its business
    date, else its valid time's date in UTC."""
    import datetime as _dt

    if meta.business_date:
        return meta.business_date
    at = meta.valid_from_ns or 0
    return _dt.datetime.fromtimestamp(at / 1e9, tz=_dt.UTC).date().isoformat()


def _a_date(text: str) -> bool:
    try:
        return date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def _value(money: object) -> tuple[Decimal, str]:
    from meridian.operations import as_decimal

    return as_decimal(money.amount), money.instrument_id


@dataclass
class FakeLake:
    """The lake behind the fake sidecar: what was recorded, as kept."""

    instance_id: str = "dgm-coinbase-1"
    # The datasets the registered catalogue declares, by their ID.
    datasets: dict[str, object] = field(default_factory=dict)
    cash: dict[str, list[tuple[str, str]]] = field(default_factory=lambda: dict(CASH))
    venues: dict[str, object] = field(default_factory=lambda: dict(VENUES))
    # Every version recorded, prices and bars, in order.
    rows: list[object] = field(default_factory=list)
    published: list[object] = field(default_factory=list)
    heads: dict[str, int] = field(default_factory=dict)
    clock: int = 1_791_417_600_000_000_000
    # The deployment's default order per data type, by dataset ID.
    priority: dict[str, list[str]] = field(default_factory=dict)
    declined: list[object] = field(default_factory=list)
    missed_venues: list[object] = field(default_factory=list)

    def declare(self, instance_id: str, catalogue: object) -> None:
        self.instance_id = instance_id
        self.datasets = {f"{instance_id}:{each.key}": each for each in catalogue.datasets}

    def _money(self, money: object, at: str, when: str) -> None:
        """Resolved, dated, to its cash instrument, or refused naming `at`."""
        code, held = money.currency_code, money.instrument_id
        if not code and not held:
            raise LakeRefused(f"{at}: names no asset: a currency_code or an instrument_id")
        if code:
            if code in TOKENS or code not in self.cash:
                raise LakeRefused(
                    f"{at}.currency_code: {code} is no ISO 4217 code the deployment holds; "
                    "an asset with none is named by its instrument_id"
                )
            resolved = [i for since, i in self.cash[code] if since <= when][-1:]
            if not resolved:
                raise LakeRefused(f"{at}.currency_code: {code} names no instrument on {when}")
            if held and held != resolved[0]:
                raise LakeRefused(f"{at}: {code} and {held} name two assets")
            money.instrument_id = resolved[0]

    def _meta(self, meta: object, at: str) -> None:
        if not meta.row_key:
            raise LakeRefused(f"{at}.row_key: a row is keyed by its source's record")
        if not 1 <= len(meta.subjects) <= 8:
            raise LakeRefused(f"{at}.subjects: a row is about 1 to 8 subjects")
        if meta.source.dataset not in self.datasets:
            raise LakeRefused(
                f"{at}.source.dataset: {meta.source.dataset!r} is no dataset this "
                "instance's catalogue declares"
            )
        venue = meta.source.venue_id
        if venue and venue not in self.venues:
            raise LakeRefused(f"{at}.source.venue_id: {venue} is no venue the deployment holds")
        if meta.business_date and not _a_date(meta.business_date):
            raise LakeRefused(f"{at}.business_date: {meta.business_date!r} is no date")

    def record(self, rows: list[object], kind: str) -> object:
        """A batch recorded whole, or refused naming the item and field."""
        if not 1 <= len(rows) <= 500:
            raise LakeRefused(f"{kind}: holds {len(rows)} rows; a batch is 1 to 500")
        kept = []
        for i, row in enumerate(rows):
            at = f"{kind}[{i}]"
            self._meta(row.meta, f"{at}.meta")
            when = _when(row.meta)
            copy = type(row)()
            copy.CopyFrom(row)
            if kind == "prices":
                self._money(copy.price, f"{at}.price", when)
            else:
                amounts = ["open", "high", "low", "close"] + (
                    ["vwap"] if copy.HasField("vwap") else []
                )
                for name in amounts:
                    self._money(getattr(copy, name), f"{at}.{name}", when)
                assets = {getattr(copy, name).instrument_id for name in amounts}
                if len(assets) > 1:
                    raise LakeRefused(f"{at}: a bar's amounts are in one asset")
            kept.append(copy)
        recorded = restated = unchanged = 0
        dataset = ""
        for copy in kept:
            meta = copy.meta
            dataset = meta.source.dataset
            held = self._version(type(copy), dataset, meta.row_key, 0)
            if held is not None and self._same(held, copy):
                unchanged += 1
                continue
            meta.source.instance = self.instance_id
            meta.version = 1 if held is None else held.meta.version + 1
            self.heads[dataset] = self.heads.get(dataset, 0) + 1
            meta.sequence = self.heads[dataset]
            meta.previous_sequence = next(
                (
                    r.meta.sequence
                    for r in reversed(self.rows)
                    if type(r) is type(copy)
                    and r.meta.source.dataset == dataset
                    and [s.entity_id for s in r.meta.subjects]
                    == [s.entity_id for s in meta.subjects]
                ),
                0,
            )
            self.clock += 1_000_000_000
            meta.recorded_at_ns = self.clock
            self.rows.append(copy)
            if kind == "prices":
                self.published.append(operations_pb2.PricesRecordedEvent(price=copy))
            else:
                self.published.append(operations_pb2.BarsRecordedEvent(bar=copy))
            if held is None:
                recorded += 1
            else:
                restated += 1
        result = (
            operations_pb2.RecordPricesResult
            if kind == "prices"
            else operations_pb2.RecordBarsResult
        )
        return result(
            recorded=recorded,
            restated=restated,
            unchanged=unchanged,
            watermark=operations_pb2.Watermark(
                partitions=[
                    operations_pb2.PartitionSequence(
                        partition=dataset, sequence=self.heads.get(dataset, 0)
                    )
                ]
            ),
        )

    def _version(self, kind: type, dataset: str, row_key: str, as_of: int) -> object | None:
        """The latest version of a row key, as of a recorded time (0 for now)."""
        return next(
            (
                r
                for r in reversed(self.rows)
                if type(r) is kind
                and r.meta.source.dataset == dataset
                and r.meta.row_key == row_key
                and (not as_of or r.meta.recorded_at_ns <= as_of)
            ),
            None,
        )

    @staticmethod
    def _same(held: object, copy: object) -> bool:
        """Whether a row says what the version in force says: by decimal
        value, each Money and number compared as numbers."""

        def said(row: object) -> tuple[object, ...]:
            if isinstance(row, operations_pb2.Price):
                return (row.kind, _value(row.price), row.meta.valid_until_ns)
            return (
                *(_value(getattr(row, n)) for n in ("open", "high", "low", "close")),
                _value(row.vwap) if row.HasField("vwap") else None,
                row.meta.valid_until_ns,
            )

        return said(held) == said(copy)

    def _ref(self, dataset: str, declared: bool = False) -> object:
        held = self.datasets.get(dataset)
        ref = operations_pb2.DatasetRef(dataset=dataset, instance=dataset.split(":", 1)[0])
        if held is not None:
            ref.vendor = held.vendor
            ref.aggregator = held.aggregator
            if declared:
                ref.declaration.CopyFrom(
                    operations_pb2.DatasetDeclaration.FromString(held.SerializeToString())
                )
        return ref

    def read(self, request: object, kind: type, records: str) -> object:
        """A read of prices or bars, as the lake answers it."""
        if not 1 <= len(request.subjects) <= 500:
            raise LakeRefused("subjects: a read names 1 to 500 subjects")
        if request.business_date and not _a_date(request.business_date):
            raise LakeRefused(f"business_date: {request.business_date!r} is no date")
        as_of = request.as_of_ns
        latest = {}
        for row in self.rows:
            if type(row) is not kind:
                continue
            held = self._version(kind, row.meta.source.dataset, row.meta.row_key, as_of)
            if held is not None:
                latest[(row.meta.source.dataset, row.meta.row_key)] = held
        wanted = [s.entity_id for s in request.subjects]
        choice = request.sources
        found: list[object] = []
        unanswered = []
        for entity in wanted:
            mine = [
                r
                for r in latest.values()
                if entity in [s.entity_id for s in r.meta.subjects]
                and self._in_time(r, request)
            ]
            if kind is operations_pb2.Price and request.kinds:
                mine = [r for r in mine if r.kind in request.kinds]
            if kind is operations_pb2.Bar and request.interval_ns:
                mine = [
                    r
                    for r in mine
                    if r.meta.valid_until_ns - r.meta.valid_from_ns == request.interval_ns
                ]
            if choice.named:
                order = list(choice.named)
            elif choice.side_by_side:
                order = list(self.datasets)
            else:
                order = self.priority.get(kind.DESCRIPTOR.full_name.replace("plugin.", ""), [])
                order = [*order, *(d for d in self.datasets if d not in order)]
            chosen = [r for r in mine if r.meta.source.dataset in order]
            if not choice.side_by_side and chosen:
                first = next(
                    d for d in order if any(r.meta.source.dataset == d for r in chosen)
                )
                chosen = [r for r in chosen if r.meta.source.dataset == first]
            if not request.business_date and not request.valid_from_ns:
                # At a valid time: the latest in force per dataset, kind and venue.
                newest: dict[tuple[object, ...], object] = {}
                for r in sorted(chosen, key=lambda r: r.meta.valid_from_ns):
                    k = (r.meta.source.dataset, getattr(r, "kind", 0), r.meta.source.venue_id)
                    newest[k] = r
                chosen = list(newest.values())
            if not chosen:
                unanswered.append(
                    operations_pb2.Unanswered(
                        subject=operations_pb2.SubjectRef(entity_id=entity),
                        reason=operations_pb2.UNANSWERED_REASON_NOT_COVERED,
                    )
                )
            found.extend(chosen)
        found.sort(key=lambda r: (r.meta.source.dataset, r.meta.sequence))
        page, following = _page(found, request.page_size, request.cursor)
        named = list(dict.fromkeys(r.meta.source.dataset for r in page))
        result = (
            operations_pb2.ListPricesResult
            if kind is operations_pb2.Price
            else operations_pb2.ListBarsResult
        )
        return result(
            **{records: page},
            unanswered=unanswered,
            datasets=[self._ref(d) for d in named],
            watermark=operations_pb2.Watermark(
                partitions=[
                    operations_pb2.PartitionSequence(partition=d, sequence=self.heads.get(d, 0))
                    for d in named
                ]
            ),
            next_cursor=following,
        )

    @staticmethod
    def _in_time(row: object, request: object) -> bool:
        meta = row.meta
        if request.business_date:
            return bool(meta.business_date == request.business_date)
        if request.valid_from_ns:
            until = request.valid_until_ns or 2**63 - 1
            return bool(request.valid_from_ns <= meta.valid_from_ns < until)
        if request.at_ns:
            return bool(meta.valid_from_ns <= request.at_ns)
        return True

    def listing(self) -> object:
        licences = []
        for dataset, held in self.datasets.items():
            if held.HasField("licence_default"):
                licence = operations_pb2.DatasetLicence.FromString(
                    held.licence_default.SerializeToString()
                )
                licence.dataset = dataset
                licences.append(licence)
        return operations_pb2.ListDatasetsResult(
            datasets=[self._ref(d, declared=True) for d in self.datasets], licences=licences
        )

    def resolve_venue(self, request: object) -> object:
        asked = {(i.scheme, i.value) for i in request.identifiers}
        found = [
            v
            for v in self.venues.values()
            if asked & {(i.scheme, i.value) for i in v.identifiers}
        ]
        if len(found) == 1:
            return operations_pb2.ResolveVenueResult(found=True, venue=found[0])
        return operations_pb2.ResolveVenueResult(
            found=False,
            miss_reason=(
                operations_pb2.MISS_REASON_AMBIGUOUS
                if found
                else operations_pb2.MISS_REASON_NOT_FOUND
            ),
        )


def _page(found: list, size: int, cursor: str) -> tuple[list, str]:
    """One page of what was found, 100 to a page unless asked, and the
    cursor to the next, where there is one."""
    start, size = int(cursor or 0), size or 100
    following = str(start + size) if len(found) > start + size else ""
    return found[start : start + size], following


def _entry(kind: str) -> object:
    """The book's answer to a command: the entry it journalled."""
    return operations_pb2.RecordOpeningBalanceResult(
        entry=operations_pb2.EntryMeta(entry_id="ENT-1", kind=kind),
        journal=operations_pb2.JournalRef(partition="P0", sequence=1),
    )


@dataclass
class FakeSidecar(sidecar_pb2_grpc.SidecarServiceServicer):
    admitted: bool = True
    refusal_reason: str = ""
    instance_id: str = "custody-snaptrade-1"
    roles: tuple[str, ...] = ("custody",)
    publish_grants: tuple[str, ...] = ("platform.street.command.record-holding",)
    subscribe_grants: tuple[str, ...] = ("platform.reference.event.instrument-applied",)

    # What the streams send, each item once and then the stream ends.
    settings: list[sidecar_pb2.SettingsDelivery] = field(default_factory=list)
    scopes: list[sidecar_pb2.AccountScopeDelivery] = field(default_factory=list)

    # What the client actually sent, so a test can assert the client did not
    # supply something it must not be able to supply.
    registered: list[sidecar_pb2.RegisterRequest] = field(default_factory=list)
    # What was admitted, each declaration's roles as served (contract v15).
    reported: list[sidecar_pb2.RegisterRequest] = field(default_factory=list)
    heartbeats: list[sidecar_pb2.HeartbeatRequest] = field(default_factory=list)
    # What the last accepted heartbeat said each kind holds (PluginReport.stored).
    report_stored: list[sidecar_pb2.StoredSpan] = field(default_factory=list)
    left: list[sidecar_pb2.LeaveRequest] = field(default_factory=list)
    operations: FakeOperations = field(default_factory=FakeOperations)
    # The tickets filed here (W4.12), each filing with the person it was
    # filed for, each read of them likewise; and a refusal a test scripts.
    tickets: list[sidecar_pb2.FiledTicket] = field(default_factory=list)
    filings: list[tuple[sidecar_pb2.FileTicketRequest, str]] = field(default_factory=list)
    filed_reads: list[tuple[sidecar_pb2.ReadFiledTicketsRequest, str]] = field(
        default_factory=list
    )
    ticket_refused: tuple[grpc.StatusCode, str] | None = None
    # The moves recorded here (W4.13, contract v16), each with the person it
    # was made for and when; the hold over the instance, in days; the clock
    # the hold is read against.
    moves: list[tuple[sidecar_pb2.RecordMoveRequest, str, int]] = field(default_factory=list)
    hold_days: int = 0
    now_ns: int = 0
    move_refused: tuple[grpc.StatusCode, str] | None = None
    # Told of each heartbeat as it is heard, so a test waits for the beats it
    # asserts on instead of sleeping and counting what happened to arrive.
    beat: asyncio.Condition = field(default_factory=asyncio.Condition, repr=False)

    async def Register(  # noqa: N802 - the generated name
        self, request: sidecar_pb2.RegisterRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.RegisterReply:
        self.registered.append(request)
        if not self.admitted:
            return sidecar_pb2.RegisterReply(admitted=False, refusal_reason=self.refusal_reason)
        refused = self._roles_refused(request)
        if refused:
            return sidecar_pb2.RegisterReply(admitted=False, refusal_reason=refused)
        if request.declaration.HasField("catalogue"):
            if "dgm" not in self.roles:
                return sidecar_pb2.RegisterReply(
                    admitted=False,
                    refusal_reason="declaration.catalogue: only a plugin holding dgm serves "
                    "the lake",
                )
            self.operations.lake.declare(self.instance_id, request.declaration.catalogue)
        return sidecar_pb2.RegisterReply(
            admitted=True,
            deployment_id="dep-local-1",
            instance_id=self.instance_id,
            roles=list(self.roles),
            publish_grants=list(self.publish_grants),
            subscribe_grants=list(self.subscribe_grants),
        )

    def _roles_refused(self, request: sidecar_pb2.RegisterRequest) -> str:
        """Each page and setting held to the roles this sidecar was launched
        with (W4.1, contract v15), as core's sidecar holds them and in its
        words; filled where it names none and may, so `reported` carries
        what was served. Empty when everything is admitted."""
        built_at = int(request.schema_version.removeprefix("v") or 0)
        launched = list(self.roles)
        holds = f"it holds {' and '.join(launched)}" if launched else "it holds no role"

        def served(named: list[str]) -> list[str] | str:
            stranger = next((role for role in named if role not in launched), None)
            if stranger is not None:
                return f"serves {stranger}, which this plugin was not launched with: {holds}"
            if named:
                return list(dict.fromkeys(named))
            if len(launched) > 1 and built_at >= 15:
                return (
                    f"names no role, and {holds}: on a plugin holding several roles each "
                    "page, tool and setting names the roles it serves"
                )
            return launched

        kept = sidecar_pb2.RegisterRequest()
        kept.CopyFrom(request)
        for page in kept.interface.pages:
            roles = served(list(page.roles))
            if isinstance(roles, str):
                return f"the page {page.path} ({page.title}) {roles}"
            page.roles[:] = roles
        for setting in kept.settings:
            roles = served(list(setting.roles))
            if isinstance(roles, str):
                return f"the setting {setting.name} {roles}"
            setting.roles[:] = roles
        for tool in kept.tools:
            roles = served(list(tool.roles))
            if not isinstance(roles, str):
                tool.roles[:] = roles
        self.reported.append(kept)
        return ""

    async def WatchSettings(  # noqa: N802
        self, request: sidecar_pb2.WatchSettingsRequest, context: grpc.aio.ServicerContext
    ) -> AsyncIterator[sidecar_pb2.SettingsDelivery]:
        for delivered in self.settings:
            yield delivered

    async def WatchAccountScope(  # noqa: N802
        self, request: sidecar_pb2.WatchAccountScopeRequest, context: grpc.aio.ServicerContext
    ) -> AsyncIterator[sidecar_pb2.AccountScopeDelivery]:
        for delivered in self.scopes:
            yield delivered

    async def PluginAccess(  # noqa: N802
        self, request: sidecar_pb2.PluginAccessRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.PluginAccessReply:
        # One group writing ACC-1 and reading ACC-2 through every role this
        # sidecar was launched with, each role's entry its accounts as
        # positions in the group's read accounts (W4.10, contract v15).
        return sidecar_pb2.PluginAccessReply(
            user_groups=[
                sidecar_pb2.UserGroupAccess(
                    user_group_id="UG-1",
                    name="Operations",
                    read_account_ids=["ACC-1", "ACC-2"],
                    write_account_ids=["ACC-1"],
                    roles=[
                        sidecar_pb2.RoleAccess(
                            role=role,
                            level=sidecar_pb2.ACCESS_LEVEL_WRITE,
                            read_positions=[0, 1],
                            write_positions=[0],
                        )
                        for role in self.roles
                    ],
                )
            ]
        )

    async def Heartbeat(  # noqa: N802
        self, request: sidecar_pb2.HeartbeatRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.HeartbeatReply:
        self.heartbeats.append(request)
        async with self.beat:
            self.beat.notify_all()
        refused = self._stored_refused(request.stored)
        if refused:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, refused)
        self.report_stored = list(request.stored)
        return sidecar_pb2.HeartbeatReply()

    def _stored_refused(self, stored: object) -> str:
        """Why a heartbeat's `stored` cannot stand, naming the field, as
        core's sidecar says it (W4.5, contract v16); or nothing."""
        spans = list(stored)  # type: ignore[call-overload]
        if not spans:
            return ""
        if len(spans) > 16:
            return f"stored: stored names {len(spans)} kinds; at most 16"
        declared = {
            kind.name
            for registered in self.registered[-1:]
            for kind in registered.declaration.storage.record_kinds
        }
        seen: set[str] = set()
        for n, span in enumerate(spans):
            if span.record_kind not in declared:
                return (
                    f"stored[{n}].record_kind: a kind this version's declaration does not name"
                )
            if span.record_kind in seen:
                return f"stored: stored names {span.record_kind} twice; one entry per kind"
            seen.add(span.record_kind)
            if not span.record_count and (span.first_received_ns or span.last_received_ns):
                at = f"stored[{n}]"
                return f"{at}.first_received_ns: {at} holds no record, and so no span"
        return ""

    def mark(self) -> int:
        """Where the heartbeats built from now on begin.

        Past those already heard, and past one more: the beat the plugin's
        loop may have in flight, built from what stood before. The loop awaits
        each beat before it builds the next, so there is never more than one.
        """
        return len(self.heartbeats) + 1

    async def beats_from(self, mark: int, count: int = 2) -> list[sidecar_pb2.HeartbeatRequest]:
        """The heartbeats heard from `mark` on, once `count` of them have been.

        The timeout bounds a plugin that never beats; it is not a guess at how
        long beats take, so a slow machine waits longer rather than failing.
        """
        async with asyncio.timeout(10), self.beat:
            await self.beat.wait_for(lambda: len(self.heartbeats) >= mark + count)
        return self.heartbeats[mark:]

    async def Leave(  # noqa: N802
        self, request: sidecar_pb2.LeaveRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.LeaveReply:
        self.left.append(request)
        return sidecar_pb2.LeaveReply()

    async def FileTicket(  # noqa: N802
        self, request: sidecar_pb2.FileTicketRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.FileTicketReply:
        """Keeps what was filed, and the person it was filed for, and folds a
        repeat into the open ticket filed under its key, as the dashboard
        does (W4.12). A filing with no person is refused, as the sidecar
        refuses one: the one refusal the client's own shape depends on."""
        caller = _caller(context)
        self.filings.append((request, caller))
        if not caller:
            await context.abort(
                grpc.StatusCode.PERMISSION_DENIED,
                "a plugin files a ticket only for a person it acts for",
            )
        if self.ticket_refused is not None:
            await context.abort(*self.ticket_refused)
        key = request.idempotency_key
        open_one = next(
            (
                t
                for t in self.tickets
                if t.idempotency_key == key and t.state == sidecar_pb2.TICKET_STATE_OPEN
            ),
            None,
        )
        if open_one is not None:
            open_one.seen_count += 1
            open_one.last_seen_ns += 1
            return sidecar_pb2.FileTicketReply(
                ticket_id=open_one.ticket_id,
                outcome="unchanged",
                seen_count=open_one.seen_count,
            )
        filed = sidecar_pb2.FiledTicket(
            ticket_id=f"TKT-{len(self.tickets) + 1}",
            idempotency_key=key,
            state=sidecar_pb2.TICKET_STATE_OPEN,
            seen_count=1,
            first_seen_ns=1_791_100_800_000_000_000,
            last_seen_ns=1_791_100_800_000_000_000,
        )
        self.tickets.append(filed)
        return sidecar_pb2.FileTicketReply(
            ticket_id=filed.ticket_id, outcome="made", seen_count=1
        )

    async def FiledTickets(  # noqa: N802
        self, request: sidecar_pb2.ReadFiledTicketsRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.ReadFiledTicketsReply:
        """What was filed here: by the tickets named, by the keys named, or
        every one after the cursor, two to a page."""
        caller = _caller(context)
        self.filed_reads.append((request, caller))
        if not caller:
            await context.abort(
                grpc.StatusCode.PERMISSION_DENIED,
                "a plugin reads what it filed only for a person it acts for",
            )
        if request.ticket_ids:
            found = [t for t in self.tickets if t.ticket_id in request.ticket_ids]
            return sidecar_pb2.ReadFiledTicketsReply(tickets=found)
        if request.idempotency_keys:
            found = [t for t in self.tickets if t.idempotency_key in request.idempotency_keys]
            return sidecar_pb2.ReadFiledTicketsReply(tickets=found)
        after = next(
            (n + 1 for n, t in enumerate(self.tickets) if t.ticket_id == request.cursor), 0
        )
        page = self.tickets[after : after + 2]
        following = len(self.tickets) > after + 2
        return sidecar_pb2.ReadFiledTicketsReply(
            tickets=page, next_cursor=page[-1].ticket_id if following else ""
        )

    async def RecordMove(  # noqa: N802
        self, request: sidecar_pb2.RecordMoveRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.RecordMoveReply:
        """Recorded with its person, or refused as the sidecar refuses it:
        a kind not declared, archived of a kind not archivable, a restore for
        nobody, an archived unit deleted for nobody, a deletion inside the
        hold."""
        import time

        caller = _caller(context)
        if self.move_refused is not None:
            await context.abort(*self.move_refused)
        declared = {
            kind.name: kind
            for registered in self.registered[-1:]
            for kind in registered.declaration.storage.record_kinds
        }
        kind = declared.get(request.record_kind)
        archived = sidecar_pb2.MOVE_OUTCOME_ARCHIVED
        if kind is None or (request.outcome == archived and not kind.archivable):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "record_kind")
        if request.outcome == sidecar_pb2.MOVE_OUTCOME_RESTORED and not caller:
            await context.abort(
                grpc.StatusCode.PERMISSION_DENIED, "a restore is for a person at write"
            )
        if request.outcome == sidecar_pb2.MOVE_OUTCOME_DELETED:
            was_archived = any(
                move.unit == request.unit and move.outcome == archived
                for move, _, _ in self.moves
            )
            if was_archived and not caller:
                await context.abort(
                    grpc.StatusCode.PERMISSION_DENIED,
                    "deleting an archived unit is an admin's act",
                )
            now = self.now_ns or time.time_ns()
            if (
                self.hold_days
                and request.last_received_ns > now - self.hold_days * 86_400 * 10**9
            ):
                refusal = sidecar_pb2.Refusal(reason=sidecar_pb2.REFUSAL_REASON_WITHIN_HOLD)
                await context.abort(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    f"the unit's last record was received inside the hold of {self.hold_days} "
                    "days",
                    trailing_metadata=(("meridian-refusal-bin", refusal.SerializeToString()),),
                )
        kept = sidecar_pb2.RecordMoveRequest()
        kept.CopyFrom(request)
        self.moves.append((kept, caller, self.now_ns or time.time_ns()))
        return sidecar_pb2.RecordMoveReply()

    def read_moves(self, request: object) -> object:
        """Core's ReadMoves (W6.9) over what was recorded here: the moves
        newest first, each with its person, and per kind what the archive
        holds -- the units archived and not deleted."""
        from meridian.v1 import config_pb2

        asked = config_pb2.ReadMovesRequest()
        asked.CopyFrom(request)
        reply = config_pb2.ReadMovesReply(
            moves=[
                config_pb2.MoveRecord(move=move, person=person, at_ns=at_ns)
                for move, person, at_ns in reversed(self.moves)
            ]
        )
        held: dict[str, sidecar_pb2.RecordMoveRequest] = {}
        for move, _, _ in self.moves:
            if move.outcome == sidecar_pb2.MOVE_OUTCOME_ARCHIVED:
                held[move.unit] = move
            elif move.outcome == sidecar_pb2.MOVE_OUTCOME_DELETED:
                held.pop(move.unit, None)
        for name in dict.fromkeys(move.record_kind for move in held.values()):
            units = [move for move in held.values() if move.record_kind == name]
            reply.archived.append(
                sidecar_pb2.StoredSpan(
                    record_kind=name,
                    record_count=sum(move.record_count for move in units),
                    first_received_ns=min(move.first_received_ns for move in units),
                    last_received_ns=max(move.last_received_ns for move in units),
                )
            )
        return reply


def _caller(context: grpc.aio.ServicerContext) -> str:
    """The person a call was made for: its `meridian-caller` metadata."""
    return next(
        (
            str(value)
            for key, value in context.invocation_metadata() or ()
            if key == "meridian-caller"
        ),
        "",
    )


@pytest_asyncio.fixture
async def sidecar() -> AsyncIterator[tuple[FakeSidecar, str]]:
    """A running fake on an ephemeral loopback port."""
    service = FakeSidecar()
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(service.operations, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield service, f"127.0.0.1:{port}"
    finally:
        await server.stop(grace=None)


@pytest.fixture(autouse=True)
def no_ambient_address(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests name their address.

    Without this a developer with the variable set in their shell would run a
    different suite from CI, and the one that passes is the one nobody trusts.

    test_interop.py wants the opposite and reads the variable at import, before
    this runs. Do not "fix" that by narrowing this fixture: the protection is
    worth more than the tidiness, and the interop suite is the exception rather
    than the rule.
    """
    monkeypatch.delenv("MERIDIAN_SIDECAR_ADDRESS", raising=False)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


__all__ = ["FakeLake", "FakeOperations", "FakeSidecar", "Stream", "asyncio", "sidecar"]
