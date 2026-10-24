"""A data plugin's wants (W10.7), standing wants, recording (W10.4), licences
(W10.9) and the venue it names (W3.14): the bookkeeping every data plugin
does the same, whatever its venue, kept once here.

    wants = data.Wants(plugin, keys=("daily", "live"))

    async def answer(want, key, subjects, kinds) -> dict[str, str]:
        if want.standing:
            wants.stand(want, subjects, kinds)
        rows = [...]                                  # the plugin's own conversion
        await wants.record("prices", rows, key, want.want_id)
        return {subject: "not_covered" for subject in not_served}

    await plugin.receive(
        observations_wanted=lambda heard: wants.hear(heard, answer),
        want_withdrawn=lambda heard: wants.withdraw(heard.message.want_id),
    )

`hear` counts the want, asks the plugin's `answer` for what it declines by
subject and reason -- an answer that raises declines every subject
`source_silent`, said and not raised -- declines them grouped by reason, and
keeps the want for the Datasets page (`heard`, newest first). `record` sends
rows in the lake's batches of 500 and counts what the lake answered, overall
and per dataset (`sent_to`). What a want asks of the venue, and how a venue's
answer becomes a row, stays the plugin's.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ...errors import MeridianError, NotGranted
from ...operations import SubjectRef, Trade
from ...plugin.v1 import operations_pb2 as ops
from ._reading import Unread

log = logging.getLogger("meridian.roles.data")

#: The lake's batch: 1 to 500 rows (W10.4).
BATCH = 500
#: How many of the wants heard the Datasets page lists.
RECENT = 200

#: The rows `Wants.record` sends, by the operation's plural; from 0.32.0
#: (contract v27) rates too.
KINDS = ("prices", "bars", "trades", "quotes", "outcomes", "rates")


@dataclass(frozen=True)
class Standing:
    """A standing want, kept current until it is withdrawn."""

    want_id: str
    dataset: str
    data_type: str
    subjects: tuple[str, ...]
    kinds: tuple[int, ...]
    since_ns: int


@dataclass(frozen=True)
class Heard:
    """One want as the Datasets page lists it: what it asked, how many
    subjects, what was recorded against it and declined."""

    want_id: str
    dataset: str
    asked: str
    subjects: int
    recorded: int
    declined: int
    standing: bool
    at_ns: int


@dataclass
class Counts:
    """What the plugin has sent the lake since it started: rows recorded,
    restated and unchanged as the lake answered, values that did not read,
    subjects declined, wants heard, and when it last recorded (0 before)."""

    recorded: int = 0
    restated: int = 0
    unchanged: int = 0
    unread: int = 0
    declined: int = 0
    wants: int = 0
    last_ns: int = 0

    @property
    def sent(self) -> int:
        return self.recorded + self.restated + self.unchanged


#: The plugin's answer to one want: given the want, the key of its dataset
#: (empty for a dataset not its own), its subjects and kinds, what it
#: declines by subject and reason.
Answer = Callable[
    [ops.ObservationsWantedEvent, str, list[str], tuple[int, ...]], Awaitable[dict[str, str]]
]


@dataclass
class Wants:
    """A data plugin's wants and what it sent the lake (see the module)."""

    plugin: Any
    #: Its declared datasets' keys, as `DatasetDeclaration.key` names them.
    keys: tuple[str, ...]
    clock_ns: Callable[[], int] = time.time_ns
    standing: dict[str, Standing] = field(default_factory=dict)
    heard: deque[Heard] = field(default_factory=lambda: deque(maxlen=RECENT))
    counts: Counts = field(default_factory=Counts)
    #: What it sent each of its datasets, by key, since it started.
    by_dataset: dict[str, Counts] = field(default_factory=dict)
    #: Its datasets a deployment admin has licensed, as rows name them, as
    #: last read (contract v20); and whether the deployment answers that read.
    licensed: frozenset[str] = frozenset()
    reads_licences: bool = True
    #: Subjects whose restart's gap has been read back, once each per process.
    backfilled: set[str] = field(default_factory=set)
    #: From 0.32.0 (contract v27): the plugin's `roles.Latency`, where it
    #: keeps one -- each row recorded unasked or for a standing want has its
    #: age at the `edge` hop recorded against its dataset, the feed delay;
    #: a row pulled for a read of the past does not. `session` names the
    #: session that carried them, for its Sessions row.
    latency: Any = None
    session: str = ""

    # ── Names ────────────────────────────────────────────────────────────

    def dataset(self, key: str) -> str:
        """A dataset as rows name it: the instance, a colon and the key."""
        return f"{self.plugin.identity.instance_id}:{key}"

    def key_of(self, dataset: str) -> str:
        """The key of one of its own datasets; empty for another's."""
        instance, _, key = dataset.partition(":")
        return key if instance == self.plugin.identity.instance_id else ""

    def sent_to(self, key: str) -> Counts:
        """What it sent the dataset `key` since it started."""
        return self.by_dataset.setdefault(key, Counts())

    # ── Recording ────────────────────────────────────────────────────────

    def count(self, done: Any, key: str, overall: bool = True) -> None:
        """Count a record call's answer to `key`'s dataset, and overall where
        `overall` (rows recorded beside a want, an outcome say, may be kept
        apart from what the want recorded)."""
        now = self.clock_ns()
        for counted in (self.counts, self.sent_to(key)) if overall else (self.sent_to(key),):
            counted.recorded += int(getattr(done, "recorded", 0))
            counted.restated += int(getattr(done, "restated", 0))
            counted.unchanged += int(getattr(done, "unchanged", 0))
            counted.last_ns = now

    async def record(
        self,
        kind: str,
        rows: Sequence[Any],
        key: str,
        want_id: str = "",
        overall: bool = True,
    ) -> int:
        """Send `rows` -- `kind` one of prices, bars, trades, quotes,
        outcomes and rates -- in the lake's batches, against `want_id` where they
        answer one (an outcome answers none), each answer counted to `key`;
        how many rows were sent. A refusal raises, the batches before it
        sent and counted."""
        if kind not in KINDS:
            raise ValueError(f"{kind!r} is not one of {', '.join(KINDS)}")
        call = getattr(self.plugin, f"record_{kind}")
        if self.latency is not None and (not want_id or want_id in self.standing):
            for row in rows:
                self.latency.aged(self.dataset(key), "AGE_HOP_EDGE", row, self.session)
        sent = 0
        for start in range(0, len(rows), BATCH):
            batch = list(rows[start : start + BATCH])
            if kind == "outcomes":
                done = await call(outcomes=batch)
            else:
                done = await call(**{kind: batch}, want_id=want_id)
            self.count(done, key, overall)
            sent += len(batch)
        return sent

    async def liveness(self, key: str, alive_at_ns: int = 0, venue_id: str = "") -> int:
        """A dataset's sign of life (contract v27, W10.4; ruling 418): its
        source's heartbeat or poll, which confirms every value in force,
        recorded once for the dataset `key` and the venue (`venue_id`, empty
        for its consolidated view) -- never a row. How many the lake kept."""
        done = await self.plugin.record_liveness(
            liveness=[
                ops.DatasetLiveness(
                    dataset=self.dataset(key),
                    venue_id=venue_id,
                    alive_at_ns=alive_at_ns or self.clock_ns(),
                )
            ]
        )
        return int(getattr(done, "kept", 0))

    # ── Wants ────────────────────────────────────────────────────────────

    def stand(
        self, want: ops.ObservationsWantedEvent, subjects: Sequence[str], kinds: Sequence[int]
    ) -> Standing:
        """Keep a standing want current until it is withdrawn."""
        held = Standing(
            want.want_id, want.dataset, want.data_type, tuple(subjects), tuple(kinds),
            self.clock_ns(),
        )  # fmt: skip
        self.standing[want.want_id] = held
        return held

    def withdraw(self, want_id: str) -> Standing | None:
        """A standing want withdrawn: no longer kept current."""
        return self.standing.pop(want_id, None)

    def standing_of(self, key: str) -> list[Standing]:
        """The standing wants of one of its datasets, by key."""
        return [w for w in self.standing.values() if self.key_of(w.dataset) == key]

    async def decline(self, want_id: str, declined: dict[str, str], key: str) -> None:
        """Decline each subject with its reason, one call per reason, counted."""
        by_reason: dict[str, list[str]] = {}
        for subject, reason in declined.items():
            by_reason.setdefault(reason, []).append(subject)
        for reason, subjects in sorted(by_reason.items()):
            await self.plugin.decline_want(
                want_id=want_id,
                subjects=[SubjectRef(entity_id=s) for s in subjects],
                reason=reason,
            )
            self.counts.declined += len(subjects)
            self.sent_to(key).declined += len(subjects)

    async def hear(self, heard: Any, answer: Answer) -> None:
        """One want heard (`receive(observations_wanted=...)`): answered by
        the plugin, what it declines declined, and kept for the Datasets
        page. An answer that raises -- the venue or the lake refused -- is
        said, never raised, and declines every subject `source_silent`."""
        want: ops.ObservationsWantedEvent = heard.message
        self.counts.wants += 1
        subjects = [s.entity_id for s in want.subjects]
        key = self.key_of(want.dataset)
        before = self.counts.sent
        asked = want.business_date or (
            f"{want.valid_from_ns}..{want.valid_until_ns}" if want.valid_from_ns else "latest"
        )
        try:
            declined = await answer(want, key, subjects, tuple(want.kinds))
        except Exception as failed:  # noqa: BLE001 - the venue or the lake refused; said, not raised
            log.warning("want %s not answered: %s", want.want_id, failed)
            declined = {s: "source_silent" for s in subjects}
        await self.decline(want.want_id, declined, key)
        self.heard.appendleft(
            Heard(want.want_id, want.dataset, asked, len(subjects), self.counts.sent - before,
                  len(declined), want.standing, self.clock_ns())
        )  # fmt: skip

    # ── A restart's gap ──────────────────────────────────────────────────

    async def backfill(self, subjects: Sequence[str], history: History, key: str) -> int:
        """A restart's gap (contract v20, W10.6) for each subject not read back
        yet in this process: `backfill_restart` over it, its trades counted
        to `key`'s dataset. A refusal is said, and the plugin goes on; how
        many trades were sent."""
        fresh = [s for s in subjects if s not in self.backfilled]
        if not fresh:
            return 0
        self.backfilled.update(fresh)
        try:
            sent = await backfill_restart(_Counted(self, key), fresh, history)
        except (MeridianError, ValueError) as refused:
            log.warning(
                "a restart's gap not read back for %d subjects: %s", len(fresh), refused
            )
            return 0
        log.info("a restart's gap read back: %d trades for %d subjects", sent, len(fresh))
        return sent

    # ── Licences ─────────────────────────────────────────────────────────

    async def read_licences(self) -> frozenset[str]:
        """Its own declared datasets' licences (contract v20, W10.9): the
        datasets a deployment admin has licensed, by the names rows give
        them. A dataset with none is served by its catalogue's default terms
        until one is set. A runtime that does not grant the read is said
        once and leaves each "Not licensed yet"."""
        if not self.reads_licences:
            return self.licensed
        try:
            answered = await self.plugin.list_datasets()
        except NotGranted:
            log.warning("this data plugin may not read its datasets' licences")
            self.reads_licences = False
            return self.licensed
        mine = {self.dataset(key) for key in self.keys}
        self.licensed = frozenset(
            licence.dataset for licence in answered.licences if licence.dataset in mine
        )
        return self.licensed


@dataclass
class _Counted:
    """The plugin's two operations a restart's backfill uses, its trades
    counted to one dataset."""

    wants: Wants
    key: str

    async def list_trades(self, **asked: Any) -> Any:
        return await self.wants.plugin.list_trades(**asked)

    async def record_trades(self, **sent: Any) -> Any:
        done = await self.wants.plugin.record_trades(**sent)
        self.wants.count(done, self.key)
        return done


#: What `backfill_restart` asks of the plugin: the trades the venue's history
#: states after the last one recorded, given as the lake answered it (its
#: subject, dataset, venue and time in `meta`).
History = Callable[[ops.Trade], Awaitable[Sequence[Trade]]]


async def backfill_restart(plugin: Any, subjects: Sequence[str], history: History) -> int:
    """Backfill a restart's gap (contract v20, W10.6), before resuming the
    stream: read the last trade this instance recorded of each subject in
    `subjects` (`list_trades(..., latest_recorded=True)`, its own rows only,
    per dataset and venue), ask `history` for the trades the venue states
    after each, and record them in batches of 500. A trade recorded again is
    answered unchanged by its row key. A subject never recorded answers
    nothing and starts from the stream; a venue whose history reaches back
    less far leaves the rest missing, for the plugin's Datasets page to say.
    Answers how many trades were sent."""
    sent = 0
    for start in range(0, len(subjects), BATCH):
        asked_for = [SubjectRef(entity_id=each) for each in subjects[start : start + BATCH]]
        cursor = ""
        while True:
            answer = await plugin.list_trades(
                subjects=asked_for, latest_recorded=True, cursor=cursor
            )
            for last in answer.trades:
                missed = list(await history(last))
                for at in range(0, len(missed), BATCH):
                    batch = missed[at : at + BATCH]
                    await plugin.record_trades(trades=batch)
                    sent += len(batch)
            cursor = answer.next_cursor
            if not cursor:
                break
    return sent


@dataclass
class Venue:
    """The venue's ID in the venue master, resolved once per reading of the
    venue (W3.14): a venue not held is reported once (W3.15) and left empty,
    each row then naming the venue as reported (`unconverted`)."""

    venue_id: str = ""
    missing: bool = False
    asked: bool = False

    async def resolve(
        self,
        plugin: Any,
        identifiers: Sequence[tuple[str, str, str]],
        source: str,
        now_ns: int,
    ) -> str:
        """The venue master's ID for the venue known by `identifiers`, each
        (scheme, value, source), asked once until `asked` is cleared."""
        if self.asked:
            return self.venue_id
        named = [ops.Identifier(scheme=s, value=v, source=o) for s, v, o in identifiers]
        found = await plugin.resolve_venue(identifiers=named, as_of_ns=now_ns)
        self.asked = True
        if found.found and found.venue.venue_id:
            self.venue_id, self.missing = found.venue.venue_id, False
        else:
            self.venue_id, self.missing = "", True
            await plugin.report_missing_venue(
                source=source,
                identifiers=named,
                as_of_ns=now_ns,
                reason=found.miss_reason or "not_found",
                observed_at_ns=now_ns,
            )
        return self.venue_id


def unconverted(
    source: str, unread: Iterable[Unread], venue: Venue | None = None, venue_name: str = ""
) -> list[ops.AsReported]:
    """What a row carries as reported: each value that did not read, under
    `<source>:<field>`, and the venue by its code where the venue master
    does not hold it; each within the contract's bounds."""
    said = [
        ops.AsReported(scheme=f"{source}:{u.field}"[:64], code=u.text[:128] or "?",
                       text=u.text[:256] or "?")
        for u in unread
    ]  # fmt: skip
    if venue is not None and venue.missing:
        said.append(ops.AsReported(scheme=f"{source}:venue"[:64], code=source[:128],
                                   text=(venue_name or source)[:256]))  # fmt: skip
    return said


def same(one: ops.Identifier, other: ops.Identifier) -> bool:
    """Whether two identifiers are one: scheme, value and source."""
    return bool(
        (one.scheme, one.value, one.source) == (other.scheme, other.value, other.source)
    )


async def asked(call: Callable[..., Any], *args: Any, of: str = "the venue") -> Any:
    """One question of a venue's client, off the event loop: what it
    answered, or None where it refused or did not answer -- said, kept in
    its raw record by the client, and the plugin's other questions still
    asked."""
    try:
        return await asyncio.to_thread(call, *args)
    except Exception as failed:  # noqa: BLE001 - the venue's refusal, kept in its raw record
        log.warning("%s asked of %s, not answered: %s", args[0] if args else "", of, failed)
        return None


async def cancelled(task: asyncio.Task[Any]) -> None:
    """Cancel a task and wait for it."""
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
