"""Views: a targeted read kept open, the copy kept by the SDK (W4.3; contract
v28, amended 2026-10-30; spec/one-data-access-model, step 2).

`plugin.subscribe(row, ...)` answers a `LiveView`: the current state of what
its selector names -- one row, and the read's own narrowing: `subjects`,
`series_keys` or `all_series` with an expiration window, and `fields` -- kept
current from deliveries, so a page reads it without a bus call and the
plugin keeps no copy of its own (822).

**The order** (spec/plugins-hear-and-read, Q1). The SDK subscribes, reads the
snapshot by the row's own read at a watermark, applies it, and then applies
held and later deliveries above the watermark: per partition for a record,
per dataset for the lake's rows. On a loss marker naming the row, or a broken
stream, it reads again for that selector alone; the sidecar is the one
matcher, each delivery naming the subscriptions it matched.

**Shared, ref-counted, lingering.** Identical selectors within a plugin are
one subscription. Each `subscribe` is one reader; `close()` lets it go, and
the subscription is dropped `linger` seconds (30 by default) after the last
reader leaves, so a page reloaded does not churn it.

**The page channel** (spec/plugins-hear-and-read, Q4; the kit's `om-live`).
`view.snapshot()` answers `{"sequence", "rows"}`; `view.events()` the
event stream, each event's id the view's own sequence. Changes are conflated
per row key over 250 ms here, before they leave the plugin (ruling 195):
every 250 ms at most one event carries each key's latest whole state.
`pages.live(path, ...)` serves both. Each event logs `record_to_send_ms`, a
row's recorded time to its send, and `conflation_wait_ms`, how long it
waited here -- the server's part of `quote_to_screen_p99_ms` (ruling 889).
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import itertools
import json
import logging
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any

import grpc
from google.protobuf.json_format import MessageToDict

from meridian.plugin.v1 import operations_pb2 as ops

from .operations import CONFLATED, DELIVERED, UNCONFLATED, SubjectRef

if TYPE_CHECKING:
    from .client import Plugin

_log = logging.getLogger("meridian.views")

#: How long changes are conflated per row key before they leave the plugin
#: (ruling 195).
CONFLATE_SECONDS = 0.25

#: The default linger: how long a view outlives its last reader.
LINGER_SECONDS = 30.0

#: The most trades a trades view keeps, the latest.
TRADES_KEPT = 500

#: How long to wait before opening a broken stream again.
RETRY_SECONDS = 1.0

_ids = itertools.count(1)


def _plain(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else value


@dataclass(frozen=True)
class _Selector:
    row: str
    subjects: tuple[str, ...]
    series_keys: tuple[tuple[str, str, str], ...]
    all_series: bool
    expiration_from: str
    expiration_to: str
    fields: tuple[str, ...]

    def request(self, subscription_id: str) -> ops.SubscribeRequest:
        return ops.SubscribeRequest(
            subscription_id=subscription_id,
            row=self.row,
            subjects=list(self.subjects),
            series_keys=[
                ops.Identifier(scheme=s, value=v, source=src) for s, v, src in self.series_keys
            ],
            all_series=self.all_series,
            expiration_from=self.expiration_from,
            expiration_to=self.expiration_to,
            fields=list(self.fields),
        )


def _row(name: str) -> tuple[str, Any]:
    """A row by its matrix name: its kind -- `record`, `latest` or `trades` --
    and its table entry."""
    for record in DELIVERED:
        if record.name == name:
            return "record", record
    for latest in CONFLATED:
        if latest.name == name:
            return "latest", latest
    for trades in UNCONFLATED:
        if trades.name == name:
            return "trades", trades
    raise ValueError(f"{name} is no row a view keeps: a record, or a lake row heard")


def _meta(message: Any) -> Any:
    """A lake row's envelope, the first field of its record."""
    return getattr(message, "meta", None)


def _series_text(meta: Any) -> str:
    keys = getattr(meta, "series_key", ()) if meta is not None else ()
    return "|".join(sorted(f"{k.scheme}={k.value}@{k.source.upper()}" for k in keys))


def _asset(record: Any) -> str:
    for name in ("price", "bid", "ask", "close"):
        if name in record.DESCRIPTOR.fields_by_name and record.HasField(name):
            money = getattr(record, name)
            if hasattr(money, "instrument_id"):
                return str(money.instrument_id or getattr(money, "currency_code", ""))
    return ""


def _latest_key(record: Any) -> str:
    """A lake row's key in a view: its dataset, subject, venue, series, kind
    and asset -- what the readers' sidecars conflate it by."""
    meta = _meta(record)
    if meta is None:
        return ""
    subject = meta.subjects[0].entity_id if meta.subjects else ""
    kind = getattr(record, "kind", 0) if "kind" in record.DESCRIPTOR.fields_by_name else 0
    return "\x1f".join(
        [
            meta.source.dataset,
            subject,
            meta.source.venue_id,
            _series_text(meta),
            str(kind),
            _asset(record),
        ]
    )


def _record_key(record: Any) -> str:
    """A book record's key in a view: its entity, by every identifier it
    carries at its top level, in field order."""
    parts = [
        f"{f.name}={getattr(record, f.name)}"
        for f in record.DESCRIPTOR.fields
        if f.name.endswith("_id") and f.type == f.TYPE_STRING
    ]
    return "|".join(parts)


@dataclass
class _Shared:
    """One subscription and the copy it keeps, shared by its readers."""

    selector: _Selector
    subscription_id: str
    kind: str
    table: Any
    linger: float
    rows: dict[str, Any] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    readers: int = 0
    sequence: int = 0
    read_once: bool = False
    watermark: dict[str, int] = field(default_factory=dict)
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    held: list[Any] = field(default_factory=list)
    pending: dict[str, tuple[Any | None, float]] = field(default_factory=dict)
    listeners: set[asyncio.Queue[tuple[int, list[Any], list[str], list[float]]]] = field(
        default_factory=set
    )
    lingering: asyncio.Task[None] | None = None
    flushing: asyncio.Task[None] | None = None


class LiveView:
    """One reader's handle on a view (`plugin.subscribe`): the current state
    of its selector, kept current from deliveries."""

    def __init__(self, views: _Views, shared: _Shared) -> None:
        self._views = views
        self._shared = shared
        self._closed = False

    @property
    def subscription_id(self) -> str:
        return self._shared.subscription_id

    def rows(self) -> dict[str, Any]:
        """The current rows, by key: a lake row's latest per conflation key,
        a record by its entity, a trade by its place in the tail."""
        return dict(self._shared.rows)

    def get(self, key: str) -> Any | None:
        """One row by its key, or None."""
        return self._shared.rows.get(key)

    async def close(self) -> None:
        """Let the view go; its subscription is dropped `linger` seconds
        after its last reader leaves."""
        if not self._closed:
            self._closed = True
            await self._views._release(self._shared)

    async def __aenter__(self) -> LiveView:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    def snapshot(self) -> dict[str, Any]:
        """om-live's snapshot: the view's sequence and every row, as JSON."""
        return {
            "sequence": str(self._shared.sequence),
            "rows": [_json(row, key) for key, row in self._shared.rows.items()],
        }

    async def events(self) -> AsyncIterator[bytes]:
        """om-live's event stream: each event its id, the view's sequence, and
        its changed rows' whole states, at most one per key per 250 ms."""
        queue: asyncio.Queue[tuple[int, list[Any], list[str], list[float]]] = asyncio.Queue()
        self._shared.listeners.add(queue)
        try:
            yield b"retry: 1000\n\n"
            while True:
                sequence, rows, removed, waits = await queue.get()
                data = json.dumps({"rows": rows, "removed": removed}, separators=(",", ":"))
                yield f"id: {sequence}\ndata: {data}\n\n".encode()
                _sent(rows, waits)
        finally:
            self._shared.listeners.discard(queue)


def _json(row: Any, key: str) -> dict[str, Any]:
    said = MessageToDict(row, preserving_proto_field_name=True)
    said["key"] = key
    return said


def _sent(rows: list[dict[str, Any]], waits: list[float]) -> None:
    """The server's part of quote-to-screen, logged per event (ruling 889)."""
    now_ns = time.time_ns()
    recorded = [
        int(row.get("meta", {}).get("recorded_at_ns", 0) or 0)
        for row in rows
        if row.get("meta")
    ]
    recorded = [r for r in recorded if r > 0]
    if not recorded:
        return
    _log.info(
        "a view's event sent",
        extra={
            "record_to_send_ms": round((now_ns - min(recorded)) / 1e6, 2),
            "conflation_wait_ms": round(max(waits, default=0.0) * 1000, 2),
            "rows": len(rows),
        },
    )


class _Views:
    """A plugin's views, by selector: the subscriptions, the stream they are
    delivered on, and the copies."""

    def __init__(self, plugin: Plugin) -> None:
        self.plugin = plugin
        self.by_selector: dict[_Selector, _Shared] = {}
        self.by_id: dict[str, _Shared] = {}
        self.stream: asyncio.Task[None] | None = None
        self.opened = asyncio.Event()
        self.lock = asyncio.Lock()

    # ── Readers ───────────────────────────────────────────────────────────

    async def subscribe(self, selector: _Selector, linger: float) -> LiveView:
        kind, table = _row(selector.row)
        async with self.lock:
            shared = self.by_selector.get(selector)
            if shared is None:
                shared = _Shared(
                    selector=selector,
                    subscription_id=f"view-{next(_ids)}",
                    kind=kind,
                    table=table,
                    linger=linger,
                )
                await self._ensure_stream(selector.row)
                await self._open(shared)
                self.by_selector[selector] = shared
                self.by_id[shared.subscription_id] = shared
            shared.readers += 1
            if shared.lingering is not None:
                shared.lingering.cancel()
                shared.lingering = None
        await shared.ready.wait()
        return LiveView(self, shared)

    async def _release(self, shared: _Shared) -> None:
        async with self.lock:
            shared.readers -= 1
            if shared.readers > 0 or shared.lingering is not None:
                return
            shared.lingering = asyncio.create_task(self._linger(shared))

    async def _linger(self, shared: _Shared) -> None:
        await asyncio.sleep(shared.linger)
        async with self.lock:
            if shared.readers > 0:
                return
            self.by_selector.pop(shared.selector, None)
            self.by_id.pop(shared.subscription_id, None)
            if shared.flushing is not None:
                shared.flushing.cancel()
        with contextlib.suppress(grpc.aio.AioRpcError):
            await self.plugin._operations().Unsubscribe(
                ops.UnsubscribeRequest(subscription_id=shared.subscription_id)
            )

    async def stop(self) -> None:
        """The plugin is leaving: every view's work stopped."""
        tasks: list[asyncio.Task[None]] = []
        if self.stream is not None:
            tasks.append(self.stream)
        for shared in self.by_id.values():
            tasks.extend(t for t in (shared.flushing, shared.lingering) if t is not None)
        for shared in self.by_selector.values():
            tasks.extend(t for t in (shared.flushing, shared.lingering) if t is not None)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task

    # ── The stream ────────────────────────────────────────────────────────

    async def _ensure_stream(self, row: str) -> None:
        if self.stream is None or self.stream.done():
            self.opened.clear()
            self.stream = asyncio.create_task(self._hear(row))
        await self.opened.wait()

    async def _hear(self, row: str) -> None:
        """The views' own stream: what their subscriptions deliver, opened
        again when it breaks, every view subscribed and read again on it.
        It names the first view's row, so it is not every row the plugin's
        roles hear; what it hears of that row beyond its subscriptions names
        none of them, and no view takes it."""
        while True:
            call = self.plugin._operations().Receive(
                ops.ReceiveRequest(rows=[row], subjects=[])
            )
            try:
                await call.initial_metadata()
                reopened = self.opened.is_set() or bool(self.by_id)
                self.opened.set()
                if reopened:
                    await self.reopened()
                async for delivery in call:
                    await self.delivered(delivery)
                _log.warning("the views' stream ended; opening it again")
            except grpc.aio.AioRpcError as failed:
                _log.warning("the views' stream broke (%s); opening it again", failed.code())
            finally:
                call.cancel()
            await asyncio.sleep(RETRY_SECONDS)

    async def reopened(self) -> None:
        """A stream broke: each view subscribed again, on the stream open
        now, and read again."""
        for shared in list(self.by_id.values()):
            await self._open(shared)

    # ── A view's order ───────────────────────────────────────────────────

    async def _open(self, shared: _Shared) -> None:
        """Subscribe, read the snapshot at a watermark, apply it, then the
        deliveries held meanwhile above it."""
        shared.ready.clear()
        await self.plugin._operations().Subscribe(
            shared.selector.request(shared.subscription_id)
        )
        await self._read(shared)
        if shared.flushing is None or shared.flushing.done():
            shared.flushing = asyncio.create_task(self._flush(shared))

    async def _read(self, shared: _Shared) -> None:
        shared.ready.clear()
        rows, watermark = await self._snapshot(shared)
        shared.watermark = watermark
        fresh = {key: row for key, row in rows}
        if shared.read_once:
            # Read again: the pages hear what changed, as one event.
            for key in set(shared.rows) - set(fresh):
                shared.pending[key] = (None, time.monotonic())
            for key, row in fresh.items():
                shared.pending[key] = (row, time.monotonic())
        shared.read_once = True
        shared.rows = fresh
        shared.order = list(fresh)
        held, shared.held = shared.held, []
        shared.ready.set()
        for delivery in held:
            self._apply(shared, delivery)

    async def _snapshot(self, shared: _Shared) -> tuple[list[tuple[str, Any]], dict[str, int]]:
        sel, table = shared.selector, shared.table
        if shared.kind == "trades":
            # A tail from now: the trades heard after the subscription.
            return [], {}
        method = getattr(self.plugin, table.caught_up_by)
        accepted = inspect.signature(method).parameters
        if shared.kind == "record":
            asked: dict[str, Any] = {}
            if table.account_param:
                asked[table.account_param] = ""
            rows: list[tuple[str, Any]] = []
            watermark: dict[str, int] = {}
            accounts = sel.subjects or ("",)
            for account in accounts:
                if table.account_param:
                    asked[table.account_param] = account
                cursor = ""
                while True:
                    page = await method(**asked, cursor=cursor)
                    for held in page.as_of.partitions:
                        watermark[held.partition] = max(
                            watermark.get(held.partition, 0), held.sequence
                        )
                    for record in getattr(page, table.records):
                        rows.append((_record_key(record), record))
                    cursor = page.next_cursor
                    if not cursor:
                        break
            return rows, watermark
        offered = {
            "subjects": [SubjectRef(entity_id=s) for s in sel.subjects],
            "series_keys": [
                ops.Identifier(scheme=s, value=v, source=src) for s, v, src in sel.series_keys
            ],
            "all_series": sel.all_series,
            "expiration_from": sel.expiration_from,
            "expiration_to": sel.expiration_to,
            "fields": list(sel.fields),
        }
        asked = {name: value for name, value in offered.items() if name in accepted and value}
        rows = []
        watermark = {}
        cursor = ""
        while True:
            page = await method(**asked, **({"cursor": cursor} if "cursor" in accepted else {}))
            for held in page.watermark.partitions:
                watermark[held.partition] = max(watermark.get(held.partition, 0), held.sequence)
            for record in getattr(page, table.records):
                rows.append((_latest_key(record), record))
            cursor = getattr(page, "next_cursor", "")
            if not cursor:
                break
        return rows, watermark

    # ── Deliveries ───────────────────────────────────────────────────────

    async def delivered(self, delivery: ops.Delivery) -> None:
        """A delivery from any stream: handed to each view it names; a loss
        reads again each view of the rows it names, every view where it names
        none."""
        if delivery.WhichOneof("item") == "lost":
            named = set(delivery.lost.rows)
            for shared in list(self.by_id.values()):
                if not named or shared.selector.row in named:
                    await self._read(shared)
            return
        for subscription_id in delivery.meta.subscription_ids:
            matched = self.by_id.get(subscription_id)
            if matched is None:
                continue
            if not matched.ready.is_set():
                matched.held.append(delivery)
                continue
            self._apply(matched, delivery)

    def _apply(self, shared: _Shared, delivery: ops.Delivery) -> None:
        """One delivery above the view's watermark applied; one at or below
        it is already in the snapshot and dropped."""
        message = getattr(delivery, delivery.WhichOneof("item"))
        table = shared.table
        if shared.kind == "record":
            journal = delivery.meta.journal
            if journal.sequence and journal.sequence <= shared.watermark.get(
                journal.partition, 0
            ):
                return
            record = getattr(message, table.within) if table.within else message
            key = _record_key(record)
        else:
            record = getattr(message, table.within) if table.within else message
            meta = _meta(record)
            dataset = meta.source.dataset if meta is not None else ""
            if meta is not None and meta.sequence <= shared.watermark.get(dataset, 0):
                return
            if shared.kind == "trades":
                key = f"{dataset}\x1f{meta.sequence if meta is not None else 0}"
            else:
                key = _latest_key(record)
        shared.rows[key] = record
        if shared.kind == "trades":
            shared.order.append(key)
            while len(shared.order) > TRADES_KEPT:
                gone = shared.order.pop(0)
                shared.rows.pop(gone, None)
                shared.pending[gone] = (None, time.monotonic())
        previous = shared.pending.get(key)
        shared.pending[key] = (record, previous[1] if previous else time.monotonic())

    async def _flush(self, shared: _Shared) -> None:
        """Every 250 ms, the view's changes since as one event, the latest
        whole state per key (ruling 195)."""
        while True:
            await asyncio.sleep(CONFLATE_SECONDS)
            if not shared.pending:
                continue
            pending, shared.pending = shared.pending, {}
            shared.sequence += 1
            now = time.monotonic()
            rows = [_json(row, key) for key, (row, _) in pending.items() if row is not None]
            removed = [key for key, (row, _) in pending.items() if row is None]
            waits = [now - since for _, since in pending.values()]
            for queue in list(shared.listeners):
                queue.put_nowait((shared.sequence, rows, removed, waits))


def selector(
    row: str,
    *,
    subjects: Sequence[str] = (),
    series_keys: Sequence[ops.Identifier] = (),
    all_series: bool = False,
    expiration_from: date | str = "",
    expiration_to: date | str = "",
    fields: Sequence[str] = (),
) -> _Selector:
    if isinstance(subjects, str):
        raise TypeError("subjects is a sequence of entity IDs, not one string")
    return _Selector(
        row=row,
        subjects=tuple(dict.fromkeys(subjects)),
        series_keys=tuple(sorted({(k.scheme, k.value, k.source) for k in series_keys})),
        all_series=all_series,
        expiration_from=_plain(expiration_from),
        expiration_to=_plain(expiration_to),
        fields=tuple(sorted(set(fields))),
    )


def views_of(plugin: Plugin) -> _Views:
    views: _Views | None = getattr(plugin, "_views_kept", None)
    if views is None:
        views = _Views(plugin)
        plugin._views_kept = views  # type: ignore[attr-defined]
    return views
