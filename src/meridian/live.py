"""A page's live values: figures a plugin works out from its views, kept for
the page by the kit's `om-live` (SDK 0.35.4; ruling 1070, question 450;
spec/one-data-access-model §§2, 5 and 6; plans/the-step-3-build Track 4 and
5g, rule 1050).

A view (`plugin.subscribe`) is the copy of what a selector delivers, its
rows as recorded. A page shows something worked out from them -- a mid, a
cross through USD, a move since arrival -- so `pages.live` serves, beside a
view, the values a plugin works out from its views:

    @pages.live("/rates/live", levels="read")
    async def rates_live(request):
        return await pages.live_values(
            ("rates", tuple(pairs)),                       # what they are of
            compute,                                       # views -> its LiveValue rows
            views=lambda: opened(pairs),                   # the views they are worked out from
        )

    def compute(views):
        quotes = views[0].rows().values()
        return [
            LiveValue.of(f"pair:{name}", {"mid": text(mid(q))}, [q],
                         datasets=listed, liveness=liveness, sessions=fx_week)
            for name, q in by_pair(quotes)
        ]

**What a value carries** (rule 1050, never blind): what the page shows,
by field (`shown`), and its tones and hover text; its **source** dataset;
its **confirmed time**, from which the page counts its age on; when it
passes its **stale ceiling**; whether it is out of session (**closed**); and,
with nothing to show, **why**, so no cell is ever blank. `LiveValue.of`
works these out from the rows it is computed from: the oldest input's
confirmed time (`roles.confirmed_ns`: its source time, a quote stating none
timed by `valid_from_ns`, or its dataset's liveness after it), the tightest
of each input's ceilings -- its dataset's `stale_after_ns` after its
`declared_delay_ns`, or the plugin's own where an admin set one -- and the
newest recorded time.

**Staleness counts only in session** (ruling 1070, question 452;
spec/sessions-and-data-report-their-latency-and-quality): given its venue's
`TradingSessions`, a value out of session is `closed`, shown with its age
and never stale; in session it is stale past its ceiling, as the `ems`'s
pre-trade check judges (`roles.ems.ReferenceCheck`). With no ceiling
declared -- no dataset `stale_after_ns`, no admin's -- a value is never
flagged stale: the page says "no stale limit declared" beside its age.

**The page channel** is `om-live`'s, as a view's is: a snapshot,
`{"sequence", "rows", "now_ms"}`, and an event stream, each event the values
that changed since the last, `{"rows", "removed", "sent_ms"}`, its id the
values' own sequence. The values are worked out again on each event of the
views they are computed from (and of `wakes`, views held elsewhere), and
once a second besides so a liveness heard or a session closing is said, but
a change leaves at most every 250 ms (ruling 195: four redraws a second at
most). Each row in JSON:

    {"key", "f": {field: text}, "tone": {name: tone}, "title", "source",
     "at_ms", "stale_at_ms", "closed", "recorded_ms", "why"}

`at_ms` is the confirmed time and `stale_at_ms` when it is stale (0: no
stale limit declared), both on the deployment's clock (`clock`), which
`now_ms` and `sent_ms` let the page follow; `recorded_ms`, the newest
input's recorded time, with `sent_ms` is the server's part of
`quote_to_screen_p99_ms` (§5), which the SDK also logs per event
(`record_to_send_ms`).

**Shared, ref-counted, lingering**, as views are: `pages.live_values(key,
...)` answers the one `LiveValues` for `key`, made with the views `views`
opens the first time; each call is a reader, `close()` lets it go, and
`linger` seconds after its last reader the values are dropped and the views
they opened closed. The `compute` given last is the one used.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
import time
from collections.abc import (
    AsyncIterator,
    Callable,
    Hashable,
    Iterable,
    Mapping,
    MutableMapping,
    Sequence,
)
from dataclasses import dataclass, field
from typing import Any

from .plugin.v1 import operations_pb2 as ops
from .roles._latency import Liveness, confirmed_ns, in_session

__all__ = ["LiveValue", "LiveValues"]

_log = logging.getLogger("meridian.live")

#: The least time between two changes leaving for the page (ruling 195).
CONFLATE_SECONDS = 0.25
#: How often the values are worked out again with no view's event, so an
#: age's liveness, a session's close or a ceiling passed is said.
TICK_SECONDS = 1.0
#: The same, where no view wakes them (a stand-in's targeted reads).
READ_SECONDS = 5.0
#: How long values with no reader are kept, with the views they opened.
LINGER_SECONDS = 30.0

#: Why a value has nothing to show, where its plugin says nothing.
NOTHING_HEARD = "nothing heard yet"

#: What works a page's values out from its views: answering them, as a list
#: or by key, or awaitable of either.
Compute = Callable[[Sequence[Any]], Any]


#: One change as the streams are handed it: its sequence, the rows changed,
#: the keys removed, and the recorded times (ms) of the rows newly recorded.
_Change = tuple[int, list[dict[str, Any]], list[str], list[float]]


def _ms(ns: int) -> float:
    return round(ns / 1e6, 3) if ns else 0


@dataclass(frozen=True)
class LiveValue:
    """One value as a page shows it (see the module): `key` the element's
    `data-live`; `shown` its texts by field (`data-f`); `tone` its tones by
    name (`data-tone-<name>`); `title` its hover text; `source` the dataset
    it is from; `confirmed_ns` when it was last confirmed; `stale_at_ns`
    when it is stale, 0 for no stale limit declared; `recorded_ns` when its
    newest input was recorded; `sessions` its venue's trading sessions,
    out of which it is closed (None: always counted); `why` it has nothing
    to show."""

    key: str
    shown: Mapping[str, str] = field(default_factory=dict)
    tone: Mapping[str, str] = field(default_factory=dict)
    title: str = ""
    source: str = ""
    confirmed_ns: int = 0
    stale_at_ns: int = 0
    recorded_ns: int = 0
    sessions: ops.TradingSessions | None = None
    why: str = ""

    @classmethod
    def of(
        cls,
        key: str,
        shown: Mapping[str, str],
        rows: Iterable[Any],
        *,
        datasets: Iterable[ops.DatasetRef] = (),
        liveness: Liveness | None = None,
        sessions: ops.TradingSessions | None = None,
        stale_after_ns: int = 0,
        tone: Mapping[str, str] | None = None,
        title: str = "",
        why: str = "",
    ) -> LiveValue:
        """A value worked out from `rows` (lake rows, each with its `meta`):
        its source, the datasets its inputs are from; its confirmed time, the
        oldest input's (`roles.confirmed_ns` with `liveness`); when it is
        stale, the soonest any input passes its ceiling -- the tighter of its
        dataset's `stale_after_ns` (from `datasets`, the lake's listing) and
        `stale_after_ns`, an admin's own, after the dataset's declared delay
        -- or 0 where none is declared; its newest recorded time. With no
        rows it has nothing to show: `why`, else "nothing heard yet"."""
        held = [row for row in rows if row is not None]
        if not held:
            return cls(
                key,
                dict(shown),
                dict(tone or {}),
                title,
                sessions=sessions,
                why=why or NOTHING_HEARD,
            )
        listed = list(datasets)
        sources: list[str] = []
        confirmed: list[int] = []
        stale_at: list[int] = []
        recorded = 0
        for row in held:
            meta = getattr(row, "meta", None)
            source = getattr(meta, "source", None)
            name = str(getattr(source, "dataset", "") or "")
            if name and name not in sources:
                sources.append(name)
            at = confirmed_ns(row, liveness)
            confirmed.append(at)
            recorded = max(recorded, int(getattr(meta, "recorded_at_ns", 0) or 0))
            ref = _dataset(listed, str(getattr(source, "instance", "") or ""), name)
            ceilings = [c for c in (stale_after_ns, ref.stale_after_ns if ref else 0) if c > 0]
            if ceilings and at:
                delay = int(ref.declared_delay_ns) if ref is not None else 0
                stale_at.append(at + min(ceilings) + delay)
        return cls(
            key,
            dict(shown),
            dict(tone or {}),
            title,
            source=", ".join(sources),
            confirmed_ns=min(confirmed),
            stale_at_ns=min(stale_at, default=0),
            recorded_ns=recorded,
            sessions=sessions,
            why=why,
        )

    def closed(self, now_ns: int) -> bool:
        """Whether it is out of its venue's sessions at `now_ns`, so its
        staleness is not counted (ruling 1070, question 452)."""
        return self.sessions is not None and not in_session(self.sessions, now_ns)

    def stale(self, now_ns: int) -> bool:
        """Whether it is stale at `now_ns`: in session, something to show,
        a ceiling declared and passed."""
        return bool(
            not self.why
            and self.stale_at_ns
            and now_ns > self.stale_at_ns
            and not self.closed(now_ns)
        )

    def to_json(self, now_ns: int) -> dict[str, Any]:
        """The row `om-live` applies (see the module), judged at `now_ns`."""
        return {
            "key": self.key,
            "f": dict(self.shown),
            "tone": dict(self.tone),
            "title": self.title,
            "source": self.source,
            "at_ms": _ms(self.confirmed_ns),
            "stale_at_ms": _ms(self.stale_at_ns),
            "closed": self.closed(now_ns),
            "recorded_ms": _ms(self.recorded_ns),
            "why": self.why,
        }


def _dataset(
    listed: Sequence[ops.DatasetRef], instance: str, name: str
) -> ops.DatasetRef | None:
    """A row's dataset in the lake's listing: by its instance and name, the
    name as `<instance>:<dataset>`, else by name alone."""
    for ref in listed:
        if ref.dataset == name and (not instance or ref.instance == instance):
            return ref
    for ref in listed:
        if ref.instance and f"{ref.instance}:{ref.dataset}" == name:
            return ref
    for ref in listed:
        if ref.dataset == name:
            return ref
    return None


class LiveValues:
    """A page's values for one key, worked out from views (see the module):
    made by `pages.live_values`, served by `pages.live`."""

    def __init__(
        self,
        key: Hashable,
        compute: Compute,
        views: Sequence[Any],
        *,
        wakes: Callable[[], Sequence[Any]] | None,
        clock: Callable[[], int],
        linger: float,
        held: MutableMapping[Hashable, LiveValues],
    ) -> None:
        self.key = key
        self.compute = compute
        #: The views it opened, closed when it is dropped.
        self.views: tuple[Any, ...] = tuple(views)
        self.wakes = wakes
        self.clock = clock
        self.linger = linger
        self.sequence = 0
        self.cells: dict[str, dict[str, Any]] = {}
        self._held = held
        self._readers = 0
        self._lingering: asyncio.Task[None] | None = None
        self._listeners: set[asyncio.Queue[_Change]] = set()
        self._running: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._changed_at = 0.0
        self._failing = ""
        self._loop = asyncio.get_running_loop()
        self.dropped = False

    # ── Readers ───────────────────────────────────────────────────────────

    def _read(self) -> None:
        self._readers += 1
        if self._lingering is not None:
            self._lingering.cancel()
            self._lingering = None

    async def close(self) -> None:
        """Let one reader go; `linger` seconds after the last, the values
        are dropped and the views they opened closed."""
        self._readers = max(0, self._readers - 1)
        if self._readers == 0 and self._lingering is None and not self.dropped:
            self._lingering = asyncio.create_task(self._linger())

    async def __aenter__(self) -> LiveValues:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def _linger(self) -> None:
        await asyncio.sleep(self.linger)
        if self._readers > 0:
            return
        await self.drop()

    async def drop(self) -> None:
        """Dropped now: no more work, the views it opened closed."""
        self.dropped = True
        if self._held.get(self.key) is self:
            del self._held[self.key]
        if self._running is not None:
            self._running.cancel()
            self._running = None
        for view in self.views:
            with contextlib.suppress(Exception):
                await view.close()

    # ── Working them out ──────────────────────────────────────────────────

    async def values(self) -> list[LiveValue]:
        """The values worked out now, as `compute` answers them."""
        answered = self.compute(self.views)
        if inspect.isawaitable(answered):
            answered = await answered
        if isinstance(answered, Mapping):
            return list(answered.values())
        return list(answered)

    async def _refresh(self) -> None:
        """Worked out again; what changed kept as the next change and handed
        to every stream open."""
        async with self._lock:
            now = self.clock()
            fresh = {each.key: each.to_json(now) for each in await self.values()}
            changed = [row for key, row in fresh.items() if self.cells.get(key) != row]
            removed = [key for key in self.cells if key not in fresh]
            # The rows whose newest input is new: what quote-to-screen times.
            anew = [
                float(row["recorded_ms"])
                for row in changed
                if row["recorded_ms"]
                and row["recorded_ms"] != self.cells.get(row["key"], {}).get("recorded_ms")
            ]
            self.cells = fresh
            if not changed and not removed:
                return
            self.sequence += 1
            self._changed_at = time.monotonic()
            for queue in list(self._listeners):
                queue.put_nowait((self.sequence, changed, removed, anew))

    async def snapshot(self) -> dict[str, Any]:
        """`om-live`'s snapshot: the values worked out now, at their
        sequence, with the deployment's clock (`now_ms`)."""
        await self._refresh()
        return {
            "sequence": str(self.sequence),
            "rows": list(self.cells.values()),
            "now_ms": _ms(self.clock()),
        }

    async def events(self) -> AsyncIterator[bytes]:
        """`om-live`'s event stream: each change after the stream opened, in
        order, its id the values' sequence, at most one every 250 ms."""
        queue: asyncio.Queue[_Change] = asyncio.Queue()
        self._listeners.add(queue)
        if self._running is None or self._running.done():
            self._running = asyncio.create_task(self._run())
        try:
            yield b"retry: 1000\n\n"
            while True:
                sequence, rows, removed, anew = await queue.get()
                sent = self.clock()
                data = json.dumps(
                    {"rows": rows, "removed": removed, "sent_ms": _ms(sent)},
                    separators=(",", ":"),
                )
                _sent(anew, len(rows), sent)
                yield f"id: {sequence}\ndata: {data}\n\n".encode()
        finally:
            self._listeners.discard(queue)
            if not self._listeners and self._running is not None:
                self._running.cancel()
                self._running = None

    async def _run(self) -> None:
        """While a stream is open: worked out again on each event of the
        views, and once a second besides; never sooner than 250 ms after the
        last change. A failure is said once, and the next tick tries again."""
        wake = asyncio.Event()
        pumps: dict[int, asyncio.Task[None]] = {}
        try:
            while True:
                woken = {id(v): v for v in (*self.views, *(self.wakes() if self.wakes else ()))}
                for gone in set(pumps) - set(woken):
                    pumps.pop(gone).cancel()
                for key, view in woken.items():
                    if key not in pumps:
                        pumps[key] = asyncio.create_task(_pump(view, wake))
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(wake.wait(), TICK_SECONDS if woken else READ_SECONDS)
                wake.clear()
                wait = self._changed_at + CONFLATE_SECONDS - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                try:
                    await self._refresh()
                except Exception as failed:  # noqa: BLE001 - said; the next tick tries again
                    said = f"{type(failed).__name__}: {failed}"
                    if said != self._failing:
                        _log.warning("a page's live values could not be worked out (%s)", said)
                    self._failing = said
                else:
                    if self._failing:
                        _log.info("a page's live values are worked out again")
                    self._failing = ""
        finally:
            for pump in pumps.values():
                pump.cancel()


async def _pump(view: Any, wake: asyncio.Event) -> None:
    """Each change of a view, as a wake."""
    changes = view._changes() if hasattr(view, "_changes") else view.events()
    with contextlib.suppress(asyncio.CancelledError):
        async for _ in changes:
            wake.set()


def _sent(recorded: list[float], rows: int, sent_ns: int) -> None:
    """The server's part of quote-to-screen, logged per event (§5): from
    the oldest newly recorded input to the send."""
    if not recorded:
        return
    _log.info(
        "a page's live values sent",
        extra={"record_to_send_ms": round(sent_ns / 1e6 - min(recorded), 2), "rows": rows},
    )
