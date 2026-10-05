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
`links` names for its external account, or none.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

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

    async def ListActivities(self, request, context):  # noqa: N802
        """By trade date, inclusive, or since a watermark in the order
        recorded; paged; with the named account's `history_from` as its
        latest sync status said it."""
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
        else:
            found.sort(key=lambda a: (a.activity.trade_date, a.journal.sequence))
        page, following = _page(found, request.page_size, request.cursor)
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
    heartbeats: list[sidecar_pb2.HeartbeatRequest] = field(default_factory=list)
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
    # Told of each heartbeat as it is heard, so a test waits for the beats it
    # asserts on instead of sleeping and counting what happened to arrive.
    beat: asyncio.Condition = field(default_factory=asyncio.Condition, repr=False)

    async def Register(  # noqa: N802 - the generated name
        self, request: sidecar_pb2.RegisterRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.RegisterReply:
        self.registered.append(request)
        if not self.admitted:
            return sidecar_pb2.RegisterReply(admitted=False, refusal_reason=self.refusal_reason)
        return sidecar_pb2.RegisterReply(
            admitted=True,
            deployment_id="dep-local-1",
            instance_id=self.instance_id,
            roles=list(self.roles),
            publish_grants=list(self.publish_grants),
            subscribe_grants=list(self.subscribe_grants),
        )

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
        return sidecar_pb2.PluginAccessReply(
            user_groups=[sidecar_pb2.UserGroupAccess(user_group_id="UG-1", name="Operations")]
        )

    async def Heartbeat(  # noqa: N802
        self, request: sidecar_pb2.HeartbeatRequest, context: grpc.aio.ServicerContext
    ) -> sidecar_pb2.HeartbeatReply:
        self.heartbeats.append(request)
        async with self.beat:
            self.beat.notify_all()
        return sidecar_pb2.HeartbeatReply()

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


__all__ = ["FakeOperations", "FakeSidecar", "Stream", "asyncio", "sidecar"]
