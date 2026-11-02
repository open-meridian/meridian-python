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
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import meridian
from conftest import FakeSidecar
from meridian.declaration import Declaration, RecordKind, Storage
from meridian.helpers.sessions import Backoff, Supervisor
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
