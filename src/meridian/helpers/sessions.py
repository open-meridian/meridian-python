"""A long-running session's restarts and supervision, shared by every role
(SDK 0.35; spec/each-role-is-one-generated-class, section 4, rulings 924,
1009 and 1017).

`Backoff` is the wait between one failure and the next try: the first wait
`first_s`, doubling to at most `most_s`, each within `jitter` of itself (a
fraction: 0.2 is up to a fifth either way) so a fleet of plugins restarting
together does not try again together; and back to `first_s` once the work
has run `steady_s` without failing. `meridian.run` restarts a role's `run()`
with one, as the `again` loop eight plugins copied did:

    backoff = Backoff(first_s=1, most_s=60, jitter=0.2, steady_s=60)
    while True:
        try:
            await work()
        except Exception:
            await asyncio.sleep(backoff.failed())
        else:
            backoff.steady()

**A supervised session** (924's item 2). `Supervisor` keeps one session
with a source open while anything is wanted on it, subscribed to exactly
what is, and opens it again after it breaks, closes or goes silent, after
its `Backoff`. The plugin supplies the `Link` -- its transport and its
vendor's protocol: opening and authenticating, subscribing, reading the
next statements, closing -- and the supervisor holds what every plugin
copied: the waits with jitter, never shorter than a source asked (a 429's
`Retry-After`, as the failure's `retry_after`), the silence timeout, a
refused key waited out longer, a restart when the settings change, a new
session where what is wanted changes and the source takes no subscription
in a session already open (`reopen_on_want`), the session's state for the
Connection page (`SessionState`), its signs of life and reconnects on the
plugin's `roles.Latency`, and one catch-up hook after a reopen,
`caught_up(last_heard_ns_by_subject) -> int`, given when each subject
wanted was last heard so the gap is read back from the source's history:

    supervisor = sessions.Supervisor(
        lambda: VendorLink(credentials),          # the plugin's Link, or None for no key
        heard=feed.heard,                          # each receive()'s statements, [] too
        flush=feed.flush,                          # what is due, recorded
        caught_up=feed.caught_up,                  # the gap after a reopen
        latency=latency, session="stocks", silent_seconds=600, refused=(Refused,),
    )
    supervisor.want(symbols); supervisor.restart(); await supervisor.run()

A source asking to be left alone a while (an HTTP 429's `Retry-After`)
says so on the failure its `Link` raises: an exception with a `retry_after`
in seconds is waited out at least that long, whatever the backoff's next
wait. A source whose subscriptions are its address -- server-sent events
naming the feeds in the URL, a socket taking no unsubscription -- is given
`reopen_on_want=True`: what is wanted changing then opens a new session for
it at once, never a drop counted or a backoff waited, rather than
`subscribe` being called on the session open.

How the source is reached -- a WebSocket, a line protocol over TCP, SSE, FIX
-- is the plugin's `Link`, never here: this module holds no transport, only
the supervision.

**The FX week** (SDK 0.35.5, ruling 1072): `FX_WEEK`, the `TradingSessions`
the spot FX market keeps, Sunday 17:00 to Friday 17:00 New York, its edges
the 17:00 New York roll and its time zone `America/New_York`, so it follows
daylight saving on both sides of the year. Use it wherever trading sessions
are taken -- `LiveValue.of(..., sessions=sessions.FX_WEEK)`,
`ems.ReferenceCheck.stale(..., sessions=sessions.FX_WEEK)`, `roles.in_session`
-- where an FX dataset names no calendar of its own
(spec/sessions-and-data-report-their-latency-and-quality, "In session").

A supervisor is also `data.pairs.Streamer` (`health`, `want`, `retarget`,
`run(once=)`, `silent_seconds`): `data.pairs.supervised` makes one for a
pairs feed over its market's own socket, so a pairs plugin needs no stream
class of its own.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import random
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from ..plugin.v1 import operations_pb2 as ops

__all__ = ["FX_WEEK", "Backoff", "CaughtUp", "Link", "SessionState", "Silent", "Supervisor"]

log = logging.getLogger("meridian.helpers.sessions")

#: The FX week (see the module): Sunday 17:00 to Friday 17:00 New York, the
#: 17:00 roll at each edge, in New York's own time, daylight saving and all.
#: One message, shared: read it, never change it.
FX_WEEK = ops.TradingSessions(
    time_zone="America/New_York",
    sessions=[
        ops.TradingSession(
            weekdays=[ops.WEEKDAY_SUNDAY], start_minute=17 * 60, end_minute=1440
        ),
        ops.TradingSession(
            weekdays=[
                ops.WEEKDAY_MONDAY,
                ops.WEEKDAY_TUESDAY,
                ops.WEEKDAY_WEDNESDAY,
                ops.WEEKDAY_THURSDAY,
            ],
            start_minute=0,
            end_minute=1440,
        ),
        ops.TradingSession(weekdays=[ops.WEEKDAY_FRIDAY], start_minute=0, end_minute=17 * 60),
    ],
)


class Backoff:
    """The wait after each failure, doubling within its jitter, and reset
    once steady (see the module). `clock` (seconds, monotonic) and `rng`
    are for a test, a behaviour case's fake clock and seed."""

    def __init__(
        self,
        first_s: float = 1.0,
        most_s: float = 60.0,
        jitter: float = 0.2,
        steady_s: float = 60.0,
        *,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        if first_s <= 0 or most_s < first_s:
            raise ValueError(f"first_s is above 0 and at most most_s: {first_s}, {most_s}")
        if not 0 <= jitter < 1:
            raise ValueError(f"jitter is a fraction from 0 to below 1: {jitter}")
        if steady_s < 0:
            raise ValueError(f"steady_s is 0 or more: {steady_s}")
        self.first_s = first_s
        self.most_s = most_s
        self.jitter = jitter
        self.steady_s = steady_s
        self._clock = clock
        self._rng = rng or random.Random()
        self._next = first_s
        self._since: float | None = None

    def failed(self) -> float:
        """The work failed: how long to wait before trying again. A failure
        after `steady_s` of steady running starts from `first_s` again."""
        now = self._clock()
        if self._since is not None and now - self._since >= self.steady_s:
            self._next = self.first_s
        base = self._next
        self._next = min(self._next * 2, self.most_s)
        self._since = now
        spread = base * self.jitter
        return base + self._rng.uniform(-spread, spread)

    def steady(self) -> None:
        """The work is running: once it has run `steady_s` since the last
        failure, the next failure waits `first_s` again."""
        if self._since is None or self._clock() - self._since >= self.steady_s:
            self._next = self.first_s
            self._since = None


# ── A supervised session (924's item 2) ──────────────────────────────────


class Link(Protocol):
    """One session with a source, the plugin's: its transport and its
    vendor's protocol. `open` connects and authenticates, raising one of the
    supervisor's `refused` exceptions where the source refuses the key;
    `subscribe` makes the session's subscriptions exactly `wanted` (called
    again whenever they change, unless the supervisor opens a new session
    then: `reopen_on_want`); `receive` answers the next statements read,
    converted ([] for a heartbeat), raising where the session broke (an
    exception with a `retry_after`, in seconds, where the source asked to be
    left that long); `close` ends it."""

    name: str

    async def open(self) -> None: ...

    async def subscribe(self, wanted: Sequence[str]) -> None: ...

    async def receive(self) -> list[Any]: ...

    async def close(self) -> None: ...


#: The catch-up hook after a reopen: given when each subject wanted was last
#: heard (ns), it reads the gap back and answers how many it recorded.
CaughtUp = Callable[[dict[str, int]], Awaitable[int]]


class Silent(Exception):
    """The session said nothing for its `silent_seconds`: taken for broken."""


class _Restart(Exception):
    """The session is to open again at once (a restart, its source moved)."""


@dataclass
class SessionState:
    """A supervised session as the Connection page shows it, never a key:
    `state` is "off" (nothing wanted), "no key", "connecting", "open",
    "waiting" (to open again) or "refused"; what it is subscribed to; how
    often it opened and dropped; its messages, the last one's moment and
    the last error; since when the session last opened."""

    state: str = "off"
    subscribed: tuple[str, ...] = ()
    opened: int = 0
    dropped: int = 0
    messages: int = 0
    last_message_ns: int = 0
    last_error: str = ""
    since_ns: int = 0

    @property
    def reconnects(self) -> int:
        """How often the session was opened again after it dropped."""
        return self.dropped

    @property
    def label(self) -> str:
        """The state as a page shows it (0.35.3): the SDK's own pages' words
        (`pairs`' Connection page), so a plugin's page draws a supervised
        session alike rather than keeping a map of its own."""
        return _LABELS.get(self.state, self.state.capitalize())


#: Each state's words on a page: the state's own word, capitalized, as the
#: SDK's pages have drawn it.
_LABELS = {
    "off": "Off",
    "no key": "No key",
    "connecting": "Connecting",
    "open": "Open",
    "waiting": "Waiting",
    "refused": "Refused",
}


def _asked(failure: BaseException) -> float:
    """The seconds a failure says its source asked to be left (its
    `retry_after`, a 429's `Retry-After`), else 0."""
    asked = getattr(failure, "retry_after", None)
    if isinstance(asked, bool) or not isinstance(asked, int | float):
        return 0.0
    return float(asked) if math.isfinite(asked) and asked > 0 else 0.0


def _symbol(item: Any) -> str | None:
    symbol = getattr(item, "symbol", None)
    return symbol if isinstance(symbol, str) and symbol else None


class Supervisor:
    """One session kept open while anything is wanted (see the module).

    `link` makes a fresh `Link` for each session, or None where it cannot
    yet (no key: said, and tried again when `restart` is called). `heard` is
    handed each `receive()`'s statements, every message received, one that
    states nothing (a heartbeat, a status) as []: each is the source's sign
    of life (ruling 418); `flush`, where given, is called
    after each and at least every `flush_seconds`; `opened(wanted)` each
    time a session opens, before anything is read; `caught_up` on every
    open after the first, with each wanted subject's last heard moment (by
    `subject_of`, a statement's `symbol` by default; the session's last
    message for one never heard). A handler's failure is said on the state
    and the session goes on. A session silent for `silent_seconds` (0 for
    never) is taken for broken; one whose `open` raises one of `refused` is
    waited out `refused_seconds` before it is tried again; any other failure
    waits the `backoff`'s next wait; and either never less than the
    failure's `retry_after` (seconds), where it has one. With
    `reopen_on_want`, what is wanted changing opens a new session for it
    rather than subscribing the open one. With `latency` (a `roles.Latency`),
    each message is the `session`'s sign of life and each drop a reconnect
    counted. `clock_ns`, `sleep` and `clock` (seconds, monotonic, for the
    silence) are for a test."""

    def __init__(
        self,
        link: Callable[[], Link | None],
        *,
        heard: Callable[[list[Any]], Awaitable[Any]],
        flush: Callable[[], Awaitable[Any]] | None = None,
        opened: Callable[[Sequence[str]], Awaitable[Any]] | None = None,
        caught_up: CaughtUp | None = None,
        latency: Any = None,
        session: str = "stream",
        silent_seconds: float = 30.0,
        refused: tuple[type[BaseException], ...] = (),
        refused_seconds: float = 300.0,
        flush_seconds: float = 0.5,
        backoff: Backoff | None = None,
        reopen_on_want: bool = False,
        subject_of: Callable[[Any], str | None] = _symbol,
        clock_ns: Callable[[], int] = time.time_ns,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if silent_seconds < 0 or refused_seconds < 0 or flush_seconds <= 0:
            raise ValueError(
                "silent_seconds and refused_seconds are 0 or more, flush_seconds above 0"
            )
        self.link = link
        self.heard, self.flush, self.opened, self.caught_up = heard, flush, opened, caught_up
        self.latency, self.session = latency, session
        self.silent_seconds = silent_seconds
        self.refused, self.refused_seconds = refused, refused_seconds
        self.flush_seconds = flush_seconds
        self.backoff = backoff or Backoff()
        self.reopen_on_want = reopen_on_want
        self.subject_of = subject_of
        self.clock_ns, self.sleep, self._clock = clock_ns, sleep, clock
        self.state = SessionState()
        #: When each subject was last heard, for the catch-up after a reopen.
        self.last_heard: dict[str, int] = {}
        self._wanted: tuple[str, ...] = ()
        self._changed = asyncio.Event()
        self._restart = False

    # ── What is wanted ───────────────────────────────────────────────────

    @property
    def wanted(self) -> tuple[str, ...]:
        """What the session is to be subscribed to."""
        return self._wanted

    @property
    def health(self) -> SessionState:
        """The state, by `data.pairs.Streamer`'s name for it."""
        return self.state

    def want(self, wanted: Sequence[str]) -> None:
        """Subscribe to these, and only these, from now on; none closes the
        session."""
        given = tuple(dict.fromkeys(wanted))
        if given != self._wanted:
            self._wanted = given
            self._changed.set()

    def restart(self) -> None:
        """Open the session again at once, made anew (the key, the plan or
        the source changed)."""
        self._restart = True
        self._changed.set()

    def retarget(self, link: Callable[[], Link | None]) -> None:
        """Answer from another source from now on: each session made by
        `link`, the one open now opened again."""
        self.link = link
        self.restart()

    # ── Running ──────────────────────────────────────────────────────────

    async def run(self, once: bool = False) -> None:
        """Keep the session open while anything is wanted, until cancelled;
        with `once`, hold one session (or none, where nothing is wanted or
        there is no key) and return when it ends."""
        while True:
            if not self._wanted:
                if await self._idle("off", once):
                    return
                continue
            made = self.link()
            if made is None:
                if await self._idle("no key", once):
                    return
                continue
            self._restart = False
            wait: float | None = None
            try:
                await self._session(made)
            except _Restart:
                pass
            except asyncio.CancelledError:
                raise
            except self.refused as refused:
                self.state.state = "refused"
                self.state.last_error = f"refused: {refused}"[:300]
                log.warning("%s refused the session: %s", made.name, refused)
                wait = max(self.refused_seconds, _asked(refused))
            except Exception as broken:  # noqa: BLE001 - said, and opened again
                self.state.dropped += 1
                self.state.last_error = f"{type(broken).__name__}: {broken}"[:300]
                log.warning("%s stopped: %s", made.name, self.state.last_error)
                if self.latency is not None:
                    self.latency.count(self.session, reconnects=1)
                wait = max(self.backoff.failed(), _asked(broken))
            finally:
                with contextlib.suppress(Exception):
                    await made.close()
            if once:
                if self.state.state == "open":
                    self.state.state = "waiting"
                return
            if wait is not None:
                if self.state.state != "refused":
                    self.state.state = "waiting"
                await self._pause(wait)

    async def _idle(self, state: str, once: bool) -> bool:
        """Nothing to hold: said, and waited until that changes. Whether to
        return (`once`)."""
        self.state.state, self.state.subscribed = state, ()
        if once:
            return True
        self._changed.clear()
        self._restart = False
        await self._changed.wait()
        return False

    async def _pause(self, seconds: float) -> None:
        """Wait, or less where what is wanted changes meanwhile."""
        if self._restart or seconds <= 0:
            return
        self._changed.clear()
        changed = asyncio.ensure_future(self._changed.wait())
        slept = asyncio.ensure_future(self.sleep(seconds))
        try:
            await asyncio.wait({changed, slept}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            changed.cancel()
            slept.cancel()

    async def _said(self, handler: Callable[..., Awaitable[Any]], *given: Any) -> Any:
        """A handler's failure said, never the session's end."""
        try:
            return await handler(*given)
        except asyncio.CancelledError:
            raise
        except Exception as failed:  # noqa: BLE001 - said; the session goes on
            self.state.last_error = f"not handled: {type(failed).__name__}: {failed}"[:300]
            log.warning("%s: a handler failed: %s", self.session, failed)
            return None

    async def _flush(self) -> None:
        if self.flush is not None:
            await self._said(self.flush)

    async def _session(self, link: Link) -> None:
        state = self.state
        state.state = "connecting"
        self._changed.clear()
        await link.open()
        state.opened += 1
        state.since_ns = self.clock_ns()
        await link.subscribe(self._wanted)
        state.subscribed = self._wanted
        state.state = "open"
        if self.latency is not None:
            self.latency.alive(self.session, state.since_ns)
        if self.opened is not None:
            await self._said(self.opened, self._wanted)
        if state.opened > 1 and self.caught_up is not None:
            since = {
                subject: self.last_heard.get(subject) or state.last_message_ns
                for subject in self._wanted
            }
            since = {subject: at for subject, at in since.items() if at}
            if since:
                await self._said(self.caught_up, since)
        pending: asyncio.Future[list[Any]] | None = None
        quiet_since = self._clock()
        try:
            while True:
                if pending is None:
                    pending = asyncio.ensure_future(link.receive())
                changed: asyncio.Future[Any] = asyncio.ensure_future(self._changed.wait())
                done, _ = await asyncio.wait(
                    {pending, changed},
                    timeout=self.flush_seconds,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if changed in done:
                    self._changed.clear()
                    if self._restart:
                        raise _Restart()
                    if not self._wanted:
                        return
                    if self.reopen_on_want and self._wanted != state.subscribed:
                        raise _Restart()
                    await link.subscribe(self._wanted)
                    state.subscribed = self._wanted
                else:
                    changed.cancel()
                if pending in done:
                    stated = pending.result()
                    pending = None
                    quiet_since = self._clock()
                    await self._heard(stated)
                elif self.silent_seconds and self._clock() - quiet_since > self.silent_seconds:
                    raise Silent(f"nothing heard for {self.silent_seconds:g} seconds")
                await self._flush()
        finally:
            if pending is not None:
                pending.cancel()
                with contextlib.suppress(BaseException):
                    await pending
            await self._flush()

    async def _heard(self, stated: list[Any]) -> None:
        now = self.clock_ns()
        state = self.state
        state.messages += 1
        state.last_message_ns = now
        self.backoff.steady()
        if self.latency is not None:
            self.latency.alive(self.session, now)
        for item in stated:
            subject = self.subject_of(item)
            if subject:
                self.last_heard[subject] = now
        # Every message is handed on, one stating nothing (a heartbeat, a
        # status) as []: it is the source's sign of life to the feed too
        # (ruling 418), as each was before the supervisor (0.35.3).
        await self._said(self.heard, stated)
