"""SDK 0.37.1: a raw record kept from two threads at once waits instead of
being refused, so no stream message is dropped.

`pairs.Feed` asks its market's REST calls on worker threads and converts
stream messages on the loop, both keeping lines in one `RawStore`. Until
0.37.1 a second thread's `keep_line` while one was in it was refused
(RuntimeError), and the stream message it kept was dropped. It now waits,
at most as long as for another pod's lock on the file (`_LINE_WAIT_SECONDS`),
then TimeoutError and nothing written."""

from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path
from typing import Any

import pytest

from meridian import _raw
from meridian.edge import RawStore
from meridian.plugin.v1 import operations_pb2 as ops

NS = 1_000_000_000
AT = 1_791_633_600 * NS  # 2026-10-10 12:00 UTC


def _stalled_fsync(
    monkeypatch: pytest.MonkeyPatch, on: threading.Thread | None = None
) -> tuple[threading.Event, threading.Event]:
    """`os.fsync` stalled on its first call from the thread `on` (from any
    thread but the main one where None) until `release` is set: `inside`
    set once it is stalled."""
    inside, release = threading.Event(), threading.Event()
    real = os.fsync
    main = threading.main_thread()

    def fsync(fd: int) -> None:
        here = threading.current_thread()
        stalls = (here is on) if on is not None else (here is not main)
        if stalls and not inside.is_set():
            inside.set()
            release.wait(10)
        real(fd)

    monkeypatch.setattr(_raw.os, "fsync", fsync)
    return inside, release


def test_two_threads_keeping_lines_in_one_store_both_keep_theirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Thread A held inside `keep_line` (its fsync stalled), thread B's
    `keep_line` on the same store and file waits for it: both kept, each
    naming its own line."""
    store = RawStore(tmp_path, kind="responses")
    kept: dict[str, str] = {}
    failed: list[BaseException] = []

    def keep(who: str, body: str, at: int) -> None:
        try:
            record = {"received_at_ns": at, "body": body}
            kept[who] = store.keep_line("trade", "BTC-USD", record)
        except BaseException as raised:  # noqa: BLE001
            failed.append(raised)

    first = threading.Thread(target=keep, args=("a", "a", AT))
    inside, release = _stalled_fsync(monkeypatch, on=first)
    first.start()
    assert inside.wait(10)
    second = threading.Thread(target=keep, args=("b", "b", AT + 1))
    second.start()
    # B is waiting while A is held: let A go a little later.
    second.join(0.2)
    assert second.is_alive(), "B waits for A rather than being refused"
    release.set()
    first.join(10)
    second.join(10)
    assert failed == []
    assert {kept["a"].rpartition("#")[2], kept["b"].rpartition("#")[2]} == {"0", "1"}
    assert store.get(kept["a"])["body"] == "a"  # type: ignore[index]
    assert store.get(kept["b"])["body"] == "b"  # type: ignore[index]
    (day,) = (tmp_path / "responses").iterdir()
    assert len((day / "trade" / "BTC-USD.jsonl").read_text().splitlines()) == 2


def test_a_second_thread_waits_at_most_the_line_bound_then_nothing_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Past the bound the second thread is refused, TimeoutError in the
    pod lock's words, and nothing of its line written; the first's kept."""
    monkeypatch.setattr(_raw, "_LINE_WAIT_SECONDS", 0.1)
    store = RawStore(tmp_path, kind="responses")
    kept: list[str] = []
    first = threading.Thread(
        target=lambda: kept.append(
            store.keep_line("trade", "BTC-USD", {"received_at_ns": AT, "body": "a"})
        )
    )
    inside, release = _stalled_fsync(monkeypatch, on=first)
    first.start()
    assert inside.wait(10)
    try:
        refused = r"another thread past 0\.1 s: nothing was written"
        with pytest.raises(TimeoutError, match=refused):
            store.keep_line("trade", "BTC-USD", {"received_at_ns": AT + 1, "body": "b"})
    finally:
        release.set()
        first.join(10)
    assert kept and kept[0].endswith("#0")
    (day,) = (tmp_path / "responses").iterdir()
    lines = (day / "trade" / "BTC-USD.jsonl").read_text().splitlines()
    assert len(lines) == 1 and '"body": "a"' in lines[0]


class _Keeping:
    """The fake pairs venue keeping its raw records in one store, as a
    plugin's market does: a REST answer (`top`, asked on a worker thread)
    and each stream message (`heard`, on the loop) a line each."""

    def __init__(self, store: RawStore) -> None:
        from fake_venues import pairs_venue

        self.market = pairs_venue.market()
        self.store = store

    def __getattr__(self, name: str) -> Any:
        return getattr(self.market, name)

    def top(self, product: str) -> Any:
        self.store.keep_line("book", product, {"received_at_ns": AT, "body": "top"})
        return self.market.top(product)

    def heard(self, text: str, received_ns: int) -> list[Any]:
        self.store.keep_line("stream", "message", {"received_at_ns": received_ns, "body": text})
        return self.market.heard(text, received_ns)


async def test_a_stream_trade_heard_while_a_rest_ask_keeps_its_line_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One store; a REST ask held inside `keep_line` on its worker thread
    while a stream message arrives on the loop: the message waits its turn
    and its trade is recorded, never dropped."""
    from fake_venues import MAKER_SELL, pairs_venue
    from meridian.roles.data import pairs
    from meridian.roles.data.testing import TRADE, Lake, hear, wanted

    store = RawStore(tmp_path, kind="responses")
    market = _Keeping(store)
    lake = Lake(pairs_venue.VENUE)
    feed = lake.bind(
        pairs.Feed(
            market,  # type: ignore[arg-type]
            pairs.ProductMap(),
            clock_ns=lambda: pairs_venue.NOW_NS,
            stream_factory=pairs_venue.STREAM,
        )
    )
    btc = await lake.held(feed, "BTC")
    await hear(lake, feed, wanted(feed, "WNT-T", pairs.TRADES, [btc],
                                  data_type=TRADE, standing=True))  # fmt: skip
    inside, release = _stalled_fsync(monkeypatch)
    asking = asyncio.create_task(feed.record_live([btc], kinds=[ops.PRICE_KIND_BID]))
    assert await asyncio.to_thread(inside.wait, 10), "the REST ask is held in keep_line"
    # The worker thread lets go a moment after the message arrives; the loop
    # waits for it inside the message's keep_line meanwhile.
    timer = threading.Timer(0.2, release.set)
    timer.start()
    try:
        await feed.on_message(MAKER_SELL)
        await asking
        await feed.flush()
    finally:
        release.set()
        timer.cancel()
    trades = [t for each in lake.on("RecordTrades") for t in each.trades]
    assert [t.meta.row_key for t in trades] == ["BTC-USD:t:8902"]
    bids = [p for each in lake.on("RecordPrices") for p in each.prices]
    assert bids, "the REST ask's price recorded too"
