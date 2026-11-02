"""SDK 0.35.3: the gaps the plugin step found on 0.35.2.

Liveness first (ruling 418): `helpers.sessions.Supervisor` handed `heard`
only a receive that stated something, so a heartbeat or a status message no
longer marked a listings or chains feed alive. Every message received is the
source's sign of life, rows or none.
"""

from __future__ import annotations

from typing import Any

from meridian.helpers.sessions import Backoff, Supervisor


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
