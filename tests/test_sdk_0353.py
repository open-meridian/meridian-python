"""SDK 0.35.3: the gaps the plugin step found on 0.35.2.

1. Liveness first (ruling 418): `helpers.sessions.Supervisor` handed
   `heard` only a receive that stated something, so a heartbeat or a status
   message no longer marked a listings or chains feed alive. Every message
   received is the source's sign of life, rows or none.
2. The supervisor's waits are never shorter than a source asked (a 429's
   `Retry-After`, as the failure's `retry_after`), and `reopen_on_want`
   opens a new session where what is wanted changes, for a source whose
   subscriptions are its address (server-sent events) -- and for
   `pairs.supervised`, whose socket was closed under its pending receive.
3. A table setting's rows are a list of dicts whether delivered typed or
   untyped: the kind a table is declared as (`Setting(kind=list)`) and
   what `meridian.Settings.values` has always held.
4. `RawStore.tend` reads from the settings only what it is not given, a
   window alone keeping what is past it; a setting missing from settings
   given is refused, as are a window below 0 and a `past` it cannot act on.
   A typed delivery's SDK settings are held read only; `Recorder.hear`
   hears the rows given alone; a session's state has a page's words.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import date
from pathlib import Path
from typing import Any

import pytest

import meridian
from conftest import FakeSidecar
from meridian.declaration import Declaration, RecordKind, Storage
from meridian.edge import RawStore
from meridian.helpers.sessions import Backoff, SessionState, Supervisor
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import reporting
from meridian.suites import Recorder
from meridian.v1 import sidecar_pb2


class _Link:
    """A link answering what it is told, then a break."""

    name = "fake"

    def __init__(self, said: list[list[Any]]) -> None:
        self.said = said
        self.subscribed: list[tuple[str, ...]] = []
        self.opened = 0
        self.closed = 0

    async def open(self) -> None:
        self.opened += 1

    async def subscribe(self, wanted: Any) -> None:
        self.subscribed.append(tuple(wanted))

    async def receive(self) -> list[Any]:
        if self.said:
            return self.said.pop(0)
        raise ConnectionError("the source dropped the session")

    async def close(self) -> None:
        self.closed += 1


# ── 1. Every message received is a sign of life (ruling 418) ────────────


async def test_a_message_stating_nothing_is_still_handed_to_heard() -> None:
    """Fails on 0.35.2: the heartbeat ([]) was never handed on."""
    handed: list[list[Any]] = []

    async def hear(stated: list[Any]) -> None:
        handed.append(list(stated))

    supervisor = Supervisor(
        lambda: _Link([[], ["trade"], []]),
        heard=hear,
        backoff=Backoff(1, 60, 0, 60),
        flush_seconds=0.001,
    )
    supervisor.want(["SPY"])
    await supervisor.run(once=True)
    assert handed == [[], ["trade"], []]
    assert supervisor.state.messages == 3


async def test_a_heartbeat_alone_marks_a_listings_feed_alive() -> None:
    """A listings feed on a supervisor: a stream saying only heartbeats is
    alive, and the pass's flush records the live dataset's liveness."""
    from test_listings import EVENING, Broker, lake

    feed, recorder = lake(Broker())
    supervisor = Supervisor(
        lambda: _Link([[]]),
        heard=feed.heard,
        flush=feed.flush,
        backoff=Backoff(1, 60, 0, 60),
        flush_seconds=0.001,
        clock_ns=lambda: EVENING,
    )
    supervisor.want(["SPY"])
    await supervisor.run(once=True)
    assert feed.alive_ns == EVENING


async def test_a_pairs_feed_supervised_hears_each_text_heartbeats_too() -> None:
    """`pairs.supervised` hands the market each raw text, a heartbeat's too:
    it kept its liveness on 0.35.2, and keeps it."""
    from fake_venues import Replayed, pairs_venue, top
    from meridian.roles.data import pairs

    heartbeat = '{"type":"heartbeat"}'
    texts: list[str] = []

    async def connect(address: str) -> Replayed:
        return Replayed([heartbeat, top(1)])

    async def heard(text: str) -> None:
        texts.append(text)

    async def on_opened(names: Any) -> None:
        return None

    stream = pairs.supervised(
        address=pairs_venue.market().stream_address,
        connect=connect,
        subscriptions=lambda names: [f"subscribe {n}" for n in names],
        heard=heard,
        opened=on_opened,
        silent_seconds=0,
    )
    stream.want(["BTC-USD"])
    await stream.run(once=True)
    assert texts == [heartbeat, top(1)]


# ── 2. A source's Retry-After, and a new session for what is wanted ─────


class _Asked(Exception):
    """A source's 429, with the seconds it asked to be left."""

    def __init__(self, retry_after: float) -> None:
        super().__init__("429 Too Many Requests")
        self.retry_after = retry_after


class _Refused(Exception):
    """The source refused the key, and asked to be left a while."""

    retry_after = 900.0


async def _first_wait(supervisor: Supervisor) -> float:
    """The supervisor's first wait after a failure, its run then ended."""
    waited: asyncio.Future[float] = asyncio.get_running_loop().create_future()

    async def sleep(seconds: float) -> None:
        if not waited.done():
            waited.set_result(seconds)
        await asyncio.Event().wait()

    supervisor.sleep = sleep
    supervisor.want(["SPY"])
    task = asyncio.ensure_future(supervisor.run())
    try:
        return await asyncio.wait_for(waited, 2)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


class _Failing(_Link):
    """A link whose session fails as it is told, at once."""

    def __init__(self, failure: BaseException, at: str = "receive") -> None:
        super().__init__([])
        self.failure, self.at = failure, at

    async def open(self) -> None:
        if self.at == "open":
            raise self.failure

    async def receive(self) -> list[Any]:
        raise self.failure


async def _nothing(stated: list[Any]) -> None:
    return None


async def test_a_reconnect_waits_at_least_the_retry_after_asked() -> None:
    supervisor = Supervisor(
        lambda: _Failing(_Asked(42)), heard=_nothing, backoff=Backoff(1, 60, 0, 60)
    )
    assert await _first_wait(supervisor) == 42


async def test_a_backoff_longer_than_the_retry_after_is_kept() -> None:
    supervisor = Supervisor(
        lambda: _Failing(_Asked(0.5)), heard=_nothing, backoff=Backoff(5, 60, 0, 60)
    )
    assert await _first_wait(supervisor) == 5


async def test_a_retry_after_that_is_not_a_number_of_seconds_is_not_waited() -> None:
    failure = _Asked(0)
    failure.retry_after = "soon"  # type: ignore[assignment]
    supervisor = Supervisor(
        lambda: _Failing(failure), heard=_nothing, backoff=Backoff(2, 60, 0, 60)
    )
    assert await _first_wait(supervisor) == 2


async def test_a_refused_key_waits_at_least_the_retry_after_asked() -> None:
    supervisor = Supervisor(
        lambda: _Failing(_Refused("401"), at="open"),
        heard=_nothing,
        refused=(_Refused,),
        refused_seconds=300,
    )
    assert await _first_wait(supervisor) == 900
    assert supervisor.state.state == "refused"


class _Held(_Link):
    """A link holding its session open until it is closed."""

    def __init__(self) -> None:
        super().__init__([])
        self.gone = asyncio.Event()

    async def receive(self) -> list[Any]:
        await self.gone.wait()
        raise ConnectionError("closed under its receive")

    async def close(self) -> None:
        await super().close()
        self.gone.set()


async def _settled(done: Any) -> None:
    for _ in range(400):
        if done():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("never settled")


async def test_reopen_on_want_opens_a_new_session_for_what_is_wanted() -> None:
    """An SSE-style source names its subscriptions in its address: what is
    wanted changing opens a new session at once, never a drop or a wait."""
    links: list[_Held] = []
    opened: list[tuple[str, ...]] = []

    def link() -> _Held:
        links.append(_Held())
        return links[-1]

    async def on_open(wanted: Any) -> None:
        opened.append(tuple(wanted))

    supervisor = Supervisor(
        link, heard=_nothing, opened=on_open, reopen_on_want=True, flush_seconds=0.001
    )
    supervisor.want(["BTC"])
    task = asyncio.ensure_future(supervisor.run())
    try:
        await _settled(lambda: supervisor.state.state == "open")
        supervisor.want(["BTC", "ETH"])
        await _settled(
            lambda: supervisor.state.opened == 2 and supervisor.state.state == "open"
        )
        state = supervisor.state
        assert (state.dropped, state.last_error, state.subscribed) == (0, "", ("BTC", "ETH"))
        assert [each.subscribed for each in links] == [[("BTC",)], [("BTC", "ETH")]]
        assert links[0].closed == 1 and opened == [("BTC",), ("BTC", "ETH")]
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def test_without_reopen_on_want_the_open_session_is_subscribed_again() -> None:
    links: list[_Held] = []

    def link() -> _Held:
        links.append(_Held())
        return links[-1]

    supervisor = Supervisor(link, heard=_nothing, flush_seconds=0.001)
    supervisor.want(["BTC"])
    task = asyncio.ensure_future(supervisor.run())
    try:
        await _settled(lambda: supervisor.state.state == "open")
        supervisor.want(["BTC", "ETH"])
        await _settled(lambda: len(links[0].subscribed) == 2)
        assert supervisor.state.opened == 1 and len(links) == 1
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def test_a_pairs_feed_supervised_reopens_for_new_names_without_a_drop() -> None:
    """Fails on 0.35.2: the market's socket was closed under its pending
    receive, a drop counted and a backoff waited for each change wanted."""
    from meridian.roles.data import pairs

    sockets: list[_Socket] = []

    async def connect(address: str) -> _Socket:
        sockets.append(_Socket())
        return sockets[-1]

    async def heard(text: str) -> None:
        return None

    opened: list[tuple[str, ...]] = []

    async def on_opened(names: Any) -> None:
        opened.append(tuple(names))

    stream = pairs.supervised(
        address="wss://venue.example/ws",
        connect=connect,
        subscriptions=lambda names: [f"subscribe {n}" for n in names],
        heard=heard,
        opened=on_opened,
        silent_seconds=0,
    )
    stream.want(["BTC-USD"])
    task = asyncio.ensure_future(stream.run())
    try:
        await _settled(lambda: stream.health.state == "open")
        stream.want(["BTC-USD", "ETH-USD"])
        await _settled(lambda: stream.health.opened == 2 and stream.health.state == "open")
        assert stream.health.dropped == 0
        assert opened == [("BTC-USD",), ("BTC-USD", "ETH-USD")]
        assert sockets[1].sent == ["subscribe BTC-USD", "subscribe ETH-USD"]
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


class _Socket:
    """A venue's socket: silent until closed, when its receive raises."""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.gone = asyncio.Event()

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def receive(self) -> str:
        await self.gone.wait()
        raise ConnectionError("closed under its receive")

    async def close(self) -> None:
        self.gone.set()


# ── 3. A table's rows are one type, typed or not ────────────────────────


@meridian.settings
class _Tabled:
    funds: list[dict[str, str]] = meridian.setting(
        "Funds", columns=[meridian.Column("ticker", label="Ticker", required=True)]
    )
    empty: list[dict[str, str]] = meridian.setting(
        "Empty", columns=[meridian.Column("ticker", label="Ticker")]
    )


_TABLED = Declaration(
    settings=_Tabled,
    storage=Storage(kinds=[RecordKind("responses", "Raw responses", window_days=30)]),
)


async def test_a_tables_rows_are_a_list_whether_delivered_typed_or_untyped(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """Fails on 0.35.2: the typed delivery gave a tuple, the untyped a list."""
    service, address = sidecar
    delivery = sidecar_pb2.SettingsDelivery(
        values=[sidecar_pb2.SettingValue(name="funds", value='[{"ticker": "VIGIX"}]')]
    )
    service.settings = [delivery, delivery]
    async with await meridian.connect(
        address, heartbeat=False, declaration=_TABLED, roles=[]
    ) as plugin:
        typed = await plugin.first_settings(_Tabled)
        untyped = await anext(plugin.settings())
    rows = [{"ticker": "VIGIX"}]
    assert typed.funds == rows and type(typed.funds) is list
    assert type(typed.empty) is list and typed.empty == []
    assert type(typed.values["funds"]) is list and typed.values["funds"] == rows
    assert type(untyped.values["funds"]) is list and untyped.values["funds"] == rows


# ── 4. tend's windows, the delivery held read only, one row heard, labels ─

DAY_NS = 86_400 * 1_000_000_000
OCT_1 = 1_790_812_800 * 1_000_000_000


class _Mover:
    def __init__(self) -> None:
        self.moved: list[tuple[str, str]] = []
        self.stored: Any = None

    async def archive_unit(self, kind: str, unit: str, **span: int) -> None:
        self.moved.append(("archived", unit))

    async def delete_unit(self, kind: str, unit: str, **span: int) -> None:
        self.moved.append(("deleted", unit))


def _kept(root: Path) -> RawStore:
    store = RawStore(root)
    for day in range(10):
        store.keep("candles", "BTC-USD", {"received_at_ns": OCT_1 + day * DAY_NS, "body": "[]"})
    return store


async def test_tend_given_a_window_alone_moves_nothing_past_it(tmp_path: Path) -> None:
    """Refused on 0.35.2 (no settings): `past` defaults to `kept`."""
    store, mover = _kept(tmp_path), _Mover()
    await store.tend(mover, window_days=3, today=date(2026, 10, 10))
    assert mover.moved == [] and mover.stored[0].record_count == 10


async def test_tend_needs_from_the_settings_only_what_is_not_given(tmp_path: Path) -> None:
    """Refused on 0.35.2: the window given, the settings holding only what
    is done past it were refused for lacking the window setting."""
    store, mover = _kept(tmp_path), _Mover()
    held = {"responses_past_window": "deleted"}
    await store.tend(mover, window_days=8, settings=held, today=date(2026, 10, 10))
    assert [unit for _, unit in mover.moved] == ["responses/2026-10-01"]


async def test_tend_refuses_a_setting_the_settings_do_not_hold(tmp_path: Path) -> None:
    """The SDK fills both settings in every delivery for a declared kind:
    one missing is a kind not declared, refused naming it, never guessed."""
    store = _kept(tmp_path)
    with pytest.raises(ValueError, match="responses_past_window"):
        await store.tend(
            _Mover(), window_days=8, settings={"responses_window_days": 8}, today=date.today()
        )
    with pytest.raises(ValueError, match="responses_window_days"):
        await store.tend(_Mover(), past="deleted", settings={}, today=date.today())
    with pytest.raises(TypeError, match="settings="):
        await store.tend(_Mover(), past="archived", today=date.today())


@pytest.mark.parametrize(
    ("window", "past", "named"),
    [
        (-1, "kept", "responses_window_days is 0 or more"),
        (True, "kept", "responses_window_days is a whole number"),
        ("thirty", "kept", "responses_window_days is a whole number"),
        (30, "archive", "responses_past_window is one of archived, kept, deleted"),
    ],
)
async def test_tend_refuses_a_window_or_a_past_it_cannot_act_on(
    tmp_path: Path, window: Any, past: str, named: str
) -> None:
    """0.35.2 held a negative window at 0 and did nothing for a `past` it
    did not know, so a typo never moved a unit."""
    with pytest.raises(ValueError, match=named):
        await _kept(tmp_path).tend(_Mover(), window, past, date(2026, 10, 10))


async def test_tend_reads_a_window_given_as_text_and_a_window_of_none(tmp_path: Path) -> None:
    mover = _Mover()
    await _kept(tmp_path).tend(
        mover, settings={"responses_window_days": "0", "responses_past_window": "archived"},
        today=date(2026, 10, 10),
    )  # fmt: skip
    assert len(mover.moved) == 9


def test_a_typed_deliverys_sdk_settings_are_held_read_only() -> None:
    config = _Tabled._of({"responses_window_days": 30})
    with pytest.raises(TypeError):
        config._more["responses_window_days"] = 1  # type: ignore[index]
    assert config.values["responses_window_days"] == 30
    assert config == _Tabled._of({"responses_window_days": 30})


class _Reader(reporting.Role):
    """A reporting class hearing two rows."""

    def __init__(self) -> None:
        super().__init__()
        self.positions: list[Any] = []
        self.orders: list[Any] = []

    async def on_position_changed(self, heard: Any) -> None:
        self.positions.append(heard.message)

    async def on_order_updated(self, heard: Any) -> None:
        self.orders.append(heard.message)


async def test_recorder_hears_one_row_given_it() -> None:
    """0.35.2's `hear(role)` delivered every row answered again each call."""
    recorder = Recorder()
    reader = recorder.bind(_Reader())
    recorder.answer("PositionChanged", lambda _: ops.PositionChangedEvent())
    recorder.answer("OrderUpdated", lambda _: ops.OrderUpdatedEvent())
    await recorder.hear(reader, "OrderUpdated")
    await recorder.hear(reader, "OrderUpdated")
    assert (len(reader.positions), len(reader.orders)) == (0, 2)
    await recorder.hear(reader)
    assert (len(reader.positions), len(reader.orders)) == (1, 3)
    with pytest.raises(ValueError, match="hears no ObservationsWanted"):
        await recorder.hear(reader, "ObservationsWanted")


def test_a_sessions_state_has_the_words_a_page_shows() -> None:
    words = {state: SessionState(state=state).label for state in _STATES}
    assert words == {
        "off": "Off",
        "no key": "No key",
        "connecting": "Connecting",
        "open": "Open",
        "waiting": "Waiting",
        "refused": "Refused",
    }


_STATES = ("off", "no key", "connecting", "open", "waiting", "refused")
