"""Session latency, data age and liveness, measured cheaply (contract v27;
spec/sessions-and-data-report-their-latency-and-quality, rulings 358 to 376
and 415 to 427; W4.16): the recorders the `data` and `connectivity` helpers
and an `ems` use, written once here.

**Histograms, never per-message records** (ruling 416): one per (session,
metric) and per (dataset, hop), log-linear at 2 significant digits from 1
µs to 1 hour, HdrHistogram's layout -- a value's bucket is HdrHistogram's
counts-array index for `lowest_ns` 1000 and 2 significant digits, so core
merges two snapshots by adding their counts. Recording is an index and an
increment. Every value is recorded, never sampled.

    latency = roles.Latency(plugin)
    latency.rtt("pricing-stream", 41_000_000)          # a ping to its pong
    latency.age("oanda-1:live", AGE_HOP_EDGE, now_ns - source_ns)
    await latency.report()                             # every 10 seconds

**Every 10 seconds** `report` takes the counts, resets them and sends them
as sparse snapshots (`ReportLatency`), each with its counters, clock skew,
the session's last sign of life and the ceilings in force from the
plugin's `session_ceilings` (`ceilings`); `run` does it in a loop.
`session_latency` answers each session's `SessionLatency` -- p50, p95 and
p99 over the last minute, congestion over the last hour -- for the
connection page's Sessions section and its tool.

**Liveness** (ruling 418): a stream that sends only on change confirms
every value in force by its heartbeat; a data plugin records it
(`Wants.liveness`, `RecordLiveness`), and a reader keeps the latest heard
(`Liveness`), a value's confirmed time being the later of its source time
and its dataset's liveness after it.

**Trading sessions** (ruling 419, W3.19): `in_session` says whether a
moment falls in a venue's sessions, its early closes in place of the
weekday's; staleness counts only in session.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..bounds import REPORT_LATENCY_REQUEST_SNAPSHOTS_COUNT
from ..operations import LatencySnapshot
from ..plugin.v1 import operations_pb2 as ops

__all__ = [
    "LOWEST_NS",
    "HIGHEST_NS",
    "SIGNIFICANT_DIGITS",
    "INTERVAL_NS",
    "FeedDelay",
    "Histogram",
    "Latency",
    "Liveness",
    "Percentiles",
    "SessionCeilings",
    "SessionLatency",
    "confirmed_ns",
    "in_session",
    "source_ns",
]

#: The layout (ruling 416): 1 µs to 1 hour at 2 significant digits.
LOWEST_NS = 1_000
HIGHEST_NS = 3_600 * 1_000_000_000
SIGNIFICANT_DIGITS = 2
#: A snapshot's interval: 10 seconds.
INTERVAL_NS = 10 * 1_000_000_000
#: How many snapshots `SessionLatency`'s percentiles cover (a minute) and
#: its counts (an hour).
_MINUTE = 6
_HOUR = 360

# HdrHistogram's layout for LOWEST_NS and SIGNIFICANT_DIGITS.
_UNIT_MAGNITUDE = LOWEST_NS.bit_length() - 1
_SUB_BUCKET_COUNT_MAGNITUDE = (2 * 10**SIGNIFICANT_DIGITS - 1).bit_length()
_SUB_BUCKET_HALF_COUNT_MAGNITUDE = _SUB_BUCKET_COUNT_MAGNITUDE - 1
_SUB_BUCKET_COUNT = 1 << _SUB_BUCKET_COUNT_MAGNITUDE
_SUB_BUCKET_HALF_COUNT = _SUB_BUCKET_COUNT >> 1
_SUB_BUCKET_MASK = (_SUB_BUCKET_COUNT - 1) << _UNIT_MAGNITUDE


def bucket_of(value_ns: int) -> int:
    """A value's bucket: HdrHistogram's counts-array index. A value below 0
    is 0, and one past `HIGHEST_NS` is held to it."""
    value = min(max(int(value_ns), 0), HIGHEST_NS)
    pow2ceiling = (value | _SUB_BUCKET_MASK).bit_length()
    bucket = pow2ceiling - _UNIT_MAGNITUDE - (_SUB_BUCKET_HALF_COUNT_MAGNITUDE + 1)
    sub = value >> (bucket + _UNIT_MAGNITUDE)
    return int(
        ((bucket + 1) << _SUB_BUCKET_HALF_COUNT_MAGNITUDE) + (sub - _SUB_BUCKET_HALF_COUNT)
    )


def value_of(index: int) -> int:
    """The lowest value a bucket holds."""
    bucket = (index >> _SUB_BUCKET_HALF_COUNT_MAGNITUDE) - 1
    sub = (index & (_SUB_BUCKET_HALF_COUNT - 1)) + _SUB_BUCKET_HALF_COUNT
    if bucket < 0:
        sub -= _SUB_BUCKET_HALF_COUNT
        bucket = 0
    return int(sub << (bucket + _UNIT_MAGNITUDE))


def _highest_of(index: int) -> int:
    """The highest value a bucket holds: the next bucket's lowest, less one."""
    return value_of(index + 1) - 1


@dataclass
class Histogram:
    """One sparse log-linear histogram over an interval (ruling 416)."""

    counts: dict[int, int] = field(default_factory=dict)
    min_ns: int = 0
    max_ns: int = 0
    total: int = 0

    def record(self, value_ns: int) -> None:
        index = bucket_of(value_ns)
        self.counts[index] = self.counts.get(index, 0) + 1
        value = int(value_ns)
        self.min_ns = value if self.total == 0 else min(self.min_ns, value)
        self.max_ns = value if self.total == 0 else max(self.max_ns, value)
        self.total += 1

    def add(self, other: Histogram) -> None:
        """Merge another's counts, as core merges snapshots."""
        if other.total == 0:
            return
        for index, count in other.counts.items():
            self.counts[index] = self.counts.get(index, 0) + count
        self.min_ns = other.min_ns if self.total == 0 else min(self.min_ns, other.min_ns)
        self.max_ns = other.max_ns if self.total == 0 else max(self.max_ns, other.max_ns)
        self.total += other.total

    def percentile(self, p: float) -> int:
        """The value at percentile `p` (0 to 100): the highest value of the
        bucket the p-th value falls in, held within min and max; 0 when
        nothing was recorded."""
        if self.total == 0:
            return 0
        rank = max(1, -(-int(p * self.total) // 100)) if p > 0 else 1
        seen = 0
        for index in sorted(self.counts):
            seen += self.counts[index]
            if seen >= rank:
                return max(self.min_ns, min(self.max_ns, _highest_of(index)))
        return self.max_ns

    def message(self) -> ops.LatencyHistogram:
        return ops.LatencyHistogram(
            lowest_ns=LOWEST_NS,
            significant_digits=SIGNIFICANT_DIGITS,
            buckets=[
                ops.LatencyBucket(bucket=index, count=count)
                for index, count in sorted(self.counts.items())
            ],
            min_ns=self.min_ns,
            max_ns=self.max_ns,
            total=self.total,
        )


@dataclass(frozen=True)
class Percentiles:
    """A metric's p50, p95 and p99 over the last minute, in nanoseconds; 0
    where nothing was measured."""

    p50_ns: int = 0
    p95_ns: int = 0
    p99_ns: int = 0


@dataclass(frozen=True)
class FeedDelay:
    """One dataset's feed delay, the `edge` hop's age, over the last minute."""

    dataset: str
    p50_ns: int = 0
    p95_ns: int = 0
    p99_ns: int = 0


@dataclass(frozen=True)
class SessionCeilings:
    """A session's ceilings in force, as the plugin admin's
    `session_ceilings` sets them: durations in nanoseconds, counts a number,
    0 for none."""

    rtt_p99_ns: int = 0
    order_ack_p99_ns: int = 0
    fill_delay_p99_ns: int = 0
    feed_delay_p99_ns: int = 0
    clock_skew_max_ns: int = 0
    gaps_per_hour: int = 0
    reconnects_per_hour: int = 0
    backlog_max: int = 0


@dataclass(frozen=True)
class SessionLatency:
    """One open session's latency, as the connection page's Sessions
    section shows it and `read_connection` answers it (the spec's "Session
    latency fields"): the session by the plugin's own name, its transport
    (`fix`, `websocket`, `rest`, `other`), its round trip over the last
    minute, a connectivity session's order acknowledgement and fill delay,
    the feed delay of each dataset it carries, congestion over the last
    hour, the send backlog now and at its peak, the clock skew, its last
    sign of life and the ceilings in force."""

    session: str
    transport: str = "other"
    rtt: Percentiles = field(default_factory=Percentiles)
    order_ack: Percentiles = field(default_factory=Percentiles)
    fill_delay: Percentiles = field(default_factory=Percentiles)
    feed_delay: list[FeedDelay] = field(default_factory=list)
    gaps: int = 0
    resends: int = 0
    reconnects: int = 0
    rate_limited: int = 0
    backlog: int = 0
    backlog_peak: int = 0
    clock_skew_ns: int = 0
    alive_at_ns: int = 0
    ceiling: SessionCeilings | None = None


def _percentiles(histogram: Histogram) -> Percentiles:
    return Percentiles(
        histogram.percentile(50), histogram.percentile(95), histogram.percentile(99)
    )


_COUNTERS = ("gaps", "resends", "reconnects", "rate_limited")


@dataclass
class _Session:
    transport: str = "other"
    histograms: dict[int, Histogram] = field(default_factory=dict)
    minute: dict[int, deque[Histogram]] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=lambda: dict.fromkeys(_COUNTERS, 0))
    hour: deque[dict[str, int]] = field(default_factory=lambda: deque(maxlen=_HOUR))
    backlog: int = 0
    backlog_peak: int = 0
    clock_skew_ns: int = 0
    alive_at_ns: int = 0
    datasets: set[str] = field(default_factory=set)


class Latency:
    """A data or connectivity plugin's recorders (W4.16), or an `ems`'s for
    its pre-trade check's age: what each session and hop measured, taken
    and sent every 10 seconds (see the module).

    `ceilings`, where given, answers a session's ceilings in force from the
    plugin's `session_ceilings` (`ceilings_from`), sent with each of its
    snapshots, since core never reads a plugin's settings to judge a
    breach."""

    def __init__(
        self,
        plugin: Any,
        *,
        clock_ns: Any = time.time_ns,
        ceilings: Any = None,
    ) -> None:
        self.plugin = plugin
        self.clock_ns = clock_ns
        self.ceilings = ceilings
        self.sessions: dict[str, _Session] = {}
        self.ages: dict[tuple[str, int], Histogram] = {}
        self.feed_minute: dict[str, deque[Histogram]] = {}
        self.started_ns = clock_ns()
        #: Snapshots sent since the plugin started, and the last refusal.
        self.sent = 0
        self.refused = ""

    # ── Recording ────────────────────────────────────────────────────────

    def session(self, name: str, transport: str = "") -> _Session:
        held = self.sessions.setdefault(name, _Session())
        if transport:
            held.transport = transport
        return held

    def _record(self, name: str, metric: int, value_ns: int) -> None:
        held = self.session(name)
        held.histograms.setdefault(metric, Histogram()).record(value_ns)

    def rtt(self, session: str, value_ns: int) -> None:
        """A round trip: FIX TestRequest to its Heartbeat, a WebSocket ping
        to its pong, a REST call's duration."""
        self._record(session, ops.LATENCY_METRIC_RTT, value_ns)

    def order_ack(self, session: str, value_ns: int) -> None:
        """Connectivity: a placement sent to the venue's acknowledgement."""
        self._record(session, ops.LATENCY_METRIC_ORDER_ACK, value_ns)

    def fill_delay(self, session: str, value_ns: int) -> None:
        """Connectivity: the venue's transaction time to the fill received."""
        self._record(session, ops.LATENCY_METRIC_FILL_DELAY, value_ns)

    def age(self, dataset: str, hop: int | str, value_ns: int, session: str = "") -> None:
        """A dataset's age at a hop: the hop's clock less the row's source
        time (`source_ns`); at the `edge` hop, the feed delay, shown on the
        session that carried it where one is named."""
        number = ops.AgeHop.Value(hop) if isinstance(hop, str) else int(hop)
        self.ages.setdefault((dataset, number), Histogram()).record(value_ns)
        if session:
            self.session(session).datasets.add(dataset)

    def aged(self, dataset: str, hop: int | str, row: Any, session: str = "") -> int:
        """A row's age at a hop, recorded now: how old it was, or -1 for a
        row with no source time, which records nothing."""
        held = source_ns(row)
        if not held:
            return -1
        age = int(self.clock_ns()) - held
        self.age(dataset, hop, age, session)
        return age

    def count(
        self,
        session: str,
        *,
        gaps: int = 0,
        resends: int = 0,
        reconnects: int = 0,
        rate_limited: int = 0,
    ) -> None:
        """Congestion: a stream's sequence gap or a FIX MsgSeqNum gap, a
        ResendRequest, a reconnect, an HTTP 429."""
        held = self.session(session)
        for name, value in zip(
            _COUNTERS, (gaps, resends, reconnects, rate_limited), strict=True
        ):
            held.counters[name] += value

    def backlog(self, session: str, queued: int) -> None:
        """Messages queued to send, now."""
        held = self.session(session)
        held.backlog = queued
        held.backlog_peak = max(held.backlog_peak, queued)

    def alive(self, session: str, at_ns: int = 0) -> None:
        """The session's last message or heartbeat."""
        self.session(session).alive_at_ns = at_ns or self.clock_ns()

    def clock_skew(self, session: str, source_at_ns: int, rtt_ns: int = 0) -> None:
        """The source's clock less ours, corrected by half the round trip:
        FIX SendingTime, a heartbeat's own time."""
        self.session(session).clock_skew_ns = source_at_ns - (self.clock_ns() - rtt_ns // 2)

    # ── Sending ──────────────────────────────────────────────────────────

    def snapshots(self) -> list[LatencySnapshot]:
        """Every histogram's counts since the last, taken and reset, as
        sparse snapshots over the interval since; a session with nothing
        measured sends its counters and liveness alone."""
        now = self.clock_ns()
        start, self.started_ns = self.started_ns, now
        out: list[LatencySnapshot] = []
        for name, held in sorted(self.sessions.items()):
            counters = ops.LatencyCounters(**held.counters, backlog_peak=held.backlog_peak)
            ceilings = self._ceilings(name)
            metrics = sorted(held.histograms.items()) or [(ops.LATENCY_METRIC_RTT, Histogram())]
            for metric, histogram in metrics:
                out.append(
                    LatencySnapshot(
                        interval_start_ns=start,
                        interval_ns=now - start,
                        session=name,
                        metric=ops.LatencyMetric.Name(metric),
                        histogram=histogram.message(),
                        counters=counters,
                        clock_skew_ns=held.clock_skew_ns,
                        alive_at_ns=held.alive_at_ns,
                        ceilings=ceilings,
                    )
                )
                held.minute.setdefault(metric, deque(maxlen=_MINUTE)).append(histogram)
            held.hour.append(dict(held.counters))
            held.histograms = {}
            held.counters = dict.fromkeys(_COUNTERS, 0)
            held.backlog_peak = held.backlog
        for (dataset, hop), histogram in sorted(self.ages.items()):
            out.append(
                LatencySnapshot(
                    interval_start_ns=start,
                    interval_ns=now - start,
                    dataset=dataset,
                    hop=ops.AgeHop.Name(hop),
                    metric=ops.LATENCY_METRIC_AGE,
                    histogram=histogram.message(),
                )
            )
            if hop == ops.AGE_HOP_EDGE:
                self.feed_minute.setdefault(dataset, deque(maxlen=_MINUTE)).append(histogram)
        self.ages = {}
        return out

    def _ceilings(self, session: str) -> ops.LatencyCeilings | None:
        if self.ceilings is None:
            return None
        found = self.ceilings(session)
        return found if isinstance(found, ops.LatencyCeilings) else None

    async def report(self) -> int:
        """Send the snapshots taken now, in `ReportLatency`'s batches of 1 to
        500; how many were sent. A refusal is kept (`refused`) and the next
        interval's sent all the same."""
        taken = self.snapshots()
        most = REPORT_LATENCY_REQUEST_SNAPSHOTS_COUNT.most
        sent = 0
        for start in range(0, len(taken), most):
            batch = taken[start : start + most]
            try:
                await self.plugin.report_latency(snapshots=batch)
            except Exception as failed:  # noqa: BLE001 - kept, said on the page; never stops the plugin
                self.refused = str(failed)
                continue
            sent += len(batch)
        self.sent += sent
        return sent

    async def run(self, interval_s: float = INTERVAL_NS / 1e9) -> None:
        """`report` every interval until cancelled."""
        import asyncio

        while True:
            await asyncio.sleep(interval_s)
            await self.report()

    # ── Reading ──────────────────────────────────────────────────────────

    def session_latency(self) -> list[SessionLatency]:
        """Each session's latency over the last minute and hour, by name."""
        out = []
        for name, held in sorted(self.sessions.items()):

            def over(metric: int, held: _Session = held) -> Histogram:
                merged = Histogram()
                for each in held.minute.get(metric, ()):
                    merged.add(each)
                merged.add(held.histograms.get(metric, Histogram()))
                return merged

            rtt, ack, fill = (
                over(m)
                for m in (
                    ops.LATENCY_METRIC_RTT,
                    ops.LATENCY_METRIC_ORDER_ACK,
                    ops.LATENCY_METRIC_FILL_DELAY,
                )
            )
            hour = {c: held.counters[c] + sum(each[c] for each in held.hour) for c in _COUNTERS}
            feed = []
            for dataset in sorted(held.datasets):
                merged = Histogram()
                for each in self.feed_minute.get(dataset, ()):
                    merged.add(each)
                merged.add(self.ages.get((dataset, ops.AGE_HOP_EDGE), Histogram()))
                taken = _percentiles(merged)
                feed.append(FeedDelay(dataset, taken.p50_ns, taken.p95_ns, taken.p99_ns))
            ceilings = self._ceilings(name)
            out.append(
                SessionLatency(
                    session=name,
                    transport=held.transport,
                    rtt=_percentiles(rtt),
                    order_ack=_percentiles(ack),
                    fill_delay=_percentiles(fill),
                    feed_delay=feed,
                    backlog=held.backlog,
                    backlog_peak=held.backlog_peak,
                    clock_skew_ns=held.clock_skew_ns,
                    alive_at_ns=held.alive_at_ns,
                    ceiling=None
                    if ceilings is None
                    else SessionCeilings(
                        **{
                            f.name: int(getattr(ceilings, f.name))
                            for f in fields(SessionCeilings)
                        }
                    ),
                    **hour,
                )
            )
        return out


# ── Source times, liveness and sessions ─────────────────────────────────────


def source_ns(row: Any) -> int:
    """A row's source time (the spec's "The hops"): its `event` source time
    where it has one, else its earliest; 0 for none. A row is a typed
    operation's dataclass or the wire's message alike."""
    meta = getattr(row, "meta", None)
    times = list(getattr(meta, "source_times", ()) or ()) if meta is not None else []
    if not times:
        return 0
    for each in times:
        kind = each.kind
        if kind in ("event", "SOURCE_TIME_KIND_EVENT", ops.SOURCE_TIME_KIND_EVENT):
            return int(each.at_ns)
    held = [int(each.at_ns) for each in times if each.at_ns]
    return min(held) if held else 0


@dataclass
class Liveness:
    """The latest liveness heard per dataset and venue (W10.5, W10.9;
    ruling 418), from `receive(liveness_recorded=liveness.heard)` and a
    listing's `DatasetRef.liveness`, for a value's confirmed time."""

    alive: dict[tuple[str, str], int] = field(default_factory=dict)

    def keep(self, item: ops.DatasetLiveness) -> bool:
        """One liveness item; whether it is later than the one held."""
        key = (item.dataset, item.venue_id)
        if int(item.alive_at_ns) <= self.alive.get(key, 0):
            return False
        self.alive[key] = int(item.alive_at_ns)
        return True

    async def heard(self, heard: Any) -> None:
        """A `receive` handler for `liveness_recorded`."""
        self.keep(heard.message.liveness)

    def listed(self, datasets: Iterable[ops.DatasetRef]) -> None:
        """The liveness a dataset listing carries (`list_datasets`)."""
        for ref in datasets:
            for item in ref.liveness:
                self.keep(item)

    def at(self, dataset: str, venue_id: str = "") -> int:
        """The latest liveness of a dataset's venue, else its consolidated
        view's; 0 for none heard."""
        return self.alive.get((dataset, venue_id)) or self.alive.get((dataset, ""), 0)


def confirmed_ns(row: Any, liveness: Liveness | None = None) -> int:
    """A value's confirmed time (the spec's staleness): the later of its
    source time and its dataset's liveness after it."""
    held = source_ns(row)
    if liveness is None:
        return held
    meta = getattr(row, "meta", None)
    source = getattr(meta, "source", None)
    dataset = str(getattr(source, "dataset", "") or "")
    venue = str(getattr(source, "venue_id", "") or "")
    alive = liveness.at(dataset, venue) if dataset else 0
    return max(held, alive)


_WEEKDAY = {
    "WEEKDAY_MONDAY": 0,
    "WEEKDAY_TUESDAY": 1,
    "WEEKDAY_WEDNESDAY": 2,
    "WEEKDAY_THURSDAY": 3,
    "WEEKDAY_FRIDAY": 4,
    "WEEKDAY_SATURDAY": 5,
    "WEEKDAY_SUNDAY": 6,
}


def _weekday(value: int) -> int:
    name = ops.Weekday.Name(value) if value in ops.Weekday.values() else ""
    return _WEEKDAY.get(name, -1)


def in_session(sessions: ops.TradingSessions, at_ns: int, *, extended: bool = False) -> bool:
    """Whether `at_ns` falls in a venue's trading sessions (W3.19; ruling
    419), in its local time: a dated day's sessions in place of its
    weekday's (an early close, a late open, a day closed), and an extended
    session only where `extended`. A calendar with no sessions is never in
    session."""
    zone = ZoneInfo(sessions.time_zone or "UTC")
    local = datetime.fromtimestamp(at_ns / 1e9, tz=UTC).astimezone(zone)
    minute = local.hour * 60 + local.minute
    day = local.date().isoformat()
    dated = [d for d in sessions.early_closes if d.date == day]
    candidates: Sequence[ops.TradingSession]
    if dated:
        candidates = list(dated[-1].sessions)
    else:
        weekday = local.weekday()
        candidates = [
            s for s in sessions.sessions if weekday in {_weekday(w) for w in s.weekdays}
        ]
    return any(
        (extended or not s.extended) and s.start_minute <= minute < s.end_minute
        for s in candidates
    )
