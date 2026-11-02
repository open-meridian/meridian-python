"""SDK 0.35.1: the SDK acts through the role object, never the connection
(ruling 1023), and the suites' recorder no longer hides an act made through
the connection.

0.35.0's pairs and event-contract feeds resolved their venue through
`self.plugin`, the connection, which makes no act under `meridian.run`: every
such data plugin failed there ("'Plugin' object has no attribute
'resolve_venue'"), while the suites passed, their `Recorder.plugin` being the
recorder itself, which makes every act.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import meridian
from conftest import FakeSidecar
from meridian.roles import custody, data
from meridian.roles.data import event_contracts, pairs
from meridian.suites import Recorder


def _pairs_feed() -> pairs.Feed:
    from fake_venues import pairs_venue

    return pairs.Feed(
        pairs_venue.market(),
        pairs.ProductMap(),
        clock_ns=lambda: pairs_venue.NOW_NS,
        stream_factory=pairs_venue.STREAM,
    )


def _contracts_feed() -> event_contracts.Feed:
    from fake_venues import contracts_venue

    return event_contracts.Feed(
        contracts_venue.market(contracts_venue.NOW_NS), event_contracts.ContractMap()
    )


# ── Each fixed site, on a real connection ─────────────────────────────────


@pytest.mark.parametrize(
    "feed", [_pairs_feed, _contracts_feed], ids=["pairs", "event_contracts"]
)
async def test_a_feed_resolves_its_venue_through_itself_on_a_real_connection(
    sidecar: tuple[FakeSidecar, str], feed: Any
) -> None:
    """`Feed.venue_id()` asks `resolve_venue`, and reports the venue missing,
    on the feed, as a role class registered on a real connection does: on
    0.35.0 it asked the connection and failed."""
    service, address = sidecar
    service.roles = ("data",)
    lake = feed()
    plugin = await meridian.connect(address, heartbeat=False, roles=[lake])
    try:
        assert lake.plugin is plugin and not hasattr(plugin, "resolve_venue")
        assert await lake.venue_id() == ""  # the fake deployment holds no venue
        assert lake.venue.missing
        (missed,) = service.operations.lake.missed_venues
        assert [(i.scheme, i.value) for i in missed.identifiers] == [
            (scheme, value) for scheme, value, _ in lake.market.venue_identifiers
        ]
    finally:
        await plugin.leave()


# ── The recorder's connection makes no act ────────────────────────────────


def test_a_class_bound_to_the_recorder_reaches_a_connection_that_makes_no_act() -> None:
    recorder = Recorder("lake-1")

    class Lake(data.Role):
        async def on_observations_wanted(self, heard: Any) -> None:
            await self.plugin.decline_want(want_id="WNT-1")

    lake = recorder.bind(Lake())
    assert lake.plugin is recorder.plugin and lake.plugin is not recorder
    # What the connection holds is the recorder's ...
    assert lake.plugin.identity.instance_id == "lake-1"
    assert lake.plugin.raw_record("daily/BTC").key == recorder.raw_record("daily/BTC").key
    lake.plugin.note_not_carried("scheme", "name")
    assert recorder.seen == {("scheme", "name"): 1}
    # ... and no act is: refused as the connection refuses it, naming where.
    with pytest.raises(AttributeError, match="'resolve_venue'.*role object"):
        _ = lake.plugin.resolve_venue
    # Nor the recorder's own tools, which the connection does not hold.
    with pytest.raises(AttributeError, match="no attribute 'answer'"):
        _ = lake.plugin.answer
    # A class acting through its connection fails here, as under meridian.run.
    with pytest.raises(AttributeError, match="'decline_want'"):
        asyncio.run(lake.on_observations_wanted(None))
    assert recorder.sent == []


async def test_a_helper_given_the_recorders_connection_fails_as_it_does_on_a_real_one() -> None:
    """The mask 0.35.0's suites had: a helper handed the connection where the
    role object belongs passed against the recorder."""
    recorder = Recorder("fakex-1")
    feed = recorder.bind(_pairs_feed())
    venue = data.Venue()
    with pytest.raises(AttributeError, match="'resolve_venue'"):
        await venue.resolve(feed.plugin, feed.market.venue_identifiers, "fakex", 0)
    # Given the role object, it resolves, and the recorder records it.
    assert (await venue.resolve(feed, feed.market.venue_identifiers, "fakex", 0)).startswith(
        "VEN-"
    )
    assert [sent.row for sent in recorder.sent] == ["ResolveVenue"]


@pytest.mark.parametrize(
    "feed", [_pairs_feed, _contracts_feed], ids=["pairs", "event_contracts"]
)
async def test_a_feed_bound_to_the_recorder_resolves_its_venue(feed: Any) -> None:
    recorder = Recorder("feed-1")
    lake = recorder.bind(feed())
    assert (await lake.venue_id()).startswith("VEN-")
    assert [sent.row for sent in recorder.sent] == ["ResolveVenue"]


# ── An event-contract feed asks for its venue once a contract is served ───


async def test_a_bars_pass_and_a_reread_ask_for_no_venue_until_a_contract_is_served() -> None:
    """The pilot's kalshi e2e: `Feed.run()` resolved the venue on start,
    through its bars pass, before any contract was served."""
    from fake_venues import NOW_NS, BarsMarket, contracts_catalogue, contracts_venue
    from meridian.roles.data.testing import Lake

    lake = Lake(contracts_venue.VENUE)
    feed = lake.bind(
        event_contracts.Feed(
            BarsMarket(),
            event_contracts.ContractMap(),
            clock_ns=lambda: NOW_NS,
            bars_declared=contracts_catalogue("bars")[0],
        )
    )
    assert await feed.keep_bars(once=True) == 0
    await feed.reread()
    assert lake.on("ResolveVenue") == []
    # Once a contract is served, a pass asks for it.
    subject = await lake.held(feed, "BASE-1")
    await feed.record_live([subject], data_type="meridian.v1.Price")
    assert feed.contracts.mapped()
    asked = len(lake.on("ResolveVenue"))
    feed.venue.asked = False
    await feed.keep_bars(once=True)
    assert len(lake.on("ResolveVenue")) == asked + 1


# ── meridian.run: the first settings before on_start; the watch kept ──────


class _Started(custody.Role):
    def __init__(self, applied: list[Any]) -> None:
        self.applied = applied
        self.seen_at_start: list[Any] | None = None

    async def on_start(self) -> None:
        self.seen_at_start = list(self.applied)


async def test_runs_settings_watch_is_opened_again_when_its_stream_ends(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A settings stream that broke was not watched again: a change made
    after it never reached the plugin. The watch is kept as a `run()` is."""
    from meridian import _run
    from meridian.helpers.sessions import Backoff
    from meridian.v1 import sidecar_pb2

    service, address = sidecar
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    monkeypatch.setattr(_run, "Backoff", lambda: Backoff(first_s=0.01, most_s=0.02))
    # The fake's stream sends its deliveries and ends, each time it is opened.
    service.settings = [sidecar_pb2.SettingsDelivery()]
    applied: list[Any] = []
    task = asyncio.create_task(
        meridian.run_async(
            meridian.Declaration(), [_Started(applied)], on_settings=applied.append
        )
    )
    try:
        for _ in range(300):
            if len(applied) >= 3:
                break
            await asyncio.sleep(0.01)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert len(applied) >= 3
