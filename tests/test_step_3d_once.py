"""A placement sent at most once, across takeovers and conversions (step 3d,
SDK part 5; sdk4-review H3 and H4).

H3: across a takeover's lapse a deposed holder and the new one share the
shard's folder, and each placement is noted there as a marker of its own,
`trading/sent/<pid>`, created exclusively: whichever pod creates it sends,
and the other is told it was sent before. The old `trading/sent.json` is
read, never written again, so no pod's note drops another's.

H4: on a claim its storage's copy converted (`.meridian/copied-from-*`),
`storage_dir()` read before Register fails loudly rather than answer the
claim's root, and `meridian plugin migrate` moves the old template's
trading files to its start. FAKES ONLY: nothing here reaches a broker."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from meridian import edge
from meridian.edge import RawStore, storage_root
from meridian.migrations import Migration, recorded
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import connectivity
from meridian.roles.connectivity import Sent, VenueOrder, place_once, testing
from meridian.suites import Recorder

ROOT = Path(__file__).resolve().parents[1]
PLACEMENT = "PLC-01JAE00000000000000000001"


@pytest.fixture(autouse=True)
def unregistered(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts as a process that has not registered."""
    monkeypatch.setattr(edge, "_serving", None, raising=False)


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The instance's shared storage, as every pod has it mounted."""
    shared = tmp_path / "shared"
    shared.mkdir()
    monkeypatch.setenv("MERIDIAN_STORAGE_DIR", str(shared))
    return shared


def _converted(root: Path) -> None:
    """The copy step's marker at the claim's root."""
    (root / ".meridian").mkdir()
    (root / ".meridian" / "copied-from-plugin-storage-broker").write_text("")


# ── H3: noted once across pods ──────────────────────────────────────────────


def test_two_pods_notes_on_one_folder_are_both_kept(tmp_path: Path) -> None:
    file = tmp_path / "trading" / "sent.json"
    a, b = Sent(file), Sent(file)  # each pod read the folder on start
    a.note("PLC-A")
    b.note("PLC-B")
    assert {"PLC-A", "PLC-B"} <= set(Sent(file)), "a later note never drops another pod's"


def test_a_second_sender_is_told_it_was_sent_before(tmp_path: Path) -> None:
    file = tmp_path / "trading" / "sent.json"
    a, b = Sent(file), Sent(file)
    assert a.note(PLACEMENT) is True
    assert b.note(PLACEMENT) is False, "the other pod noted it first"
    assert PLACEMENT in b
    assert (tmp_path / "trading" / "sent" / PLACEMENT).is_file()


def test_a_note_made_since_start_is_seen(tmp_path: Path) -> None:
    file = tmp_path / "trading" / "sent.json"
    a, b = Sent(file), Sent(file)
    b.note(PLACEMENT)
    assert PLACEMENT in a, "read from the folder, not only what it read on start"


def test_the_old_file_is_read_and_never_written_again(tmp_path: Path) -> None:
    file = tmp_path / "trading" / "sent.json"
    file.parent.mkdir(parents=True)
    file.write_text(json.dumps(["PLC-OLD"]))
    held = Sent(file)
    assert "PLC-OLD" in held
    assert held.note("PLC-OLD") is False
    assert held.note("PLC-NEW") is True
    assert json.loads(file.read_text()) == ["PLC-OLD"], "never rewritten whole"
    assert sorted(held) == ["PLC-NEW", "PLC-OLD"] and len(held) == 2
    assert set(Sent(file)) == {"PLC-NEW", "PLC-OLD"}


def test_any_name_is_kept_as_its_own_marker(tmp_path: Path) -> None:
    file = tmp_path / "enabled.json"
    names = ["101-001/2", "..", ".", "a b%c", "x" * 400, "Δ-account"]
    held = Sent(file)
    for name in names:
        assert held.note(name) is True
    again = Sent(file)
    assert set(again) == set(names)
    for name in names:
        assert name in again and again.note(name) is False
    assert all(p.parent == tmp_path / "enabled" for p in (tmp_path / "enabled").iterdir())


def test_in_memory_it_is_as_before() -> None:
    held = Sent(None)
    assert held.note(PLACEMENT) is True
    assert held.note(PLACEMENT) is False
    assert list(held) == [PLACEMENT]


def test_place_once_does_not_send_what_another_pod_noted(tmp_path: Path) -> None:
    file = tmp_path / "trading" / "sent.json"
    mine, theirs = Sent(file), Sent(file)
    theirs.note(PLACEMENT)
    sends: list[str] = []

    async def send() -> tuple[Any, str]:
        sends.append(PLACEMENT)
        return object(), "trading/placed-1.json"

    placed = asyncio.run(place_once(object(), mine, PLACEMENT, send, source="fakeb"))
    assert placed.state == "sent_before"
    assert sends == []


def test_two_traders_in_a_lapse_place_once(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A, the deposed holder, is paused after it heard P and before it sends;
    B takes the shard, starts and places P; A resumes. The venue is asked once."""
    from test_connectivity_trader import Rig  # the made-up venue's rig

    monkeypatch.setattr(edge, "_serving", (0, 1))

    async def lapse() -> None:
        a = Rig(Recorder("broker"))
        b = Rig(Recorder("broker"), broker=a.fake)  # one venue, as both pods reach it
        await a.trader.on_start()
        paused, resumed = asyncio.Event(), asyncio.Event()
        resolve = a.trader.resolve_instrument

        async def held_back(**kw: Any) -> Any:
            paused.set()
            await resumed.wait()
            return await resolve(**kw)

        a.trader.resolve_instrument = held_back  # type: ignore[method-assign]
        placement = a.placement(PLACEMENT)
        a.holds(placement)
        heard = asyncio.create_task(a.hear(placement))
        await paused.wait()
        # The Lease lapsed: B takes the shard and reads the folder on start.
        await b.trader.on_start()
        b.holds(b.placement(PLACEMENT))
        await b.hear(b.placement(PLACEMENT))
        resumed.set()
        await heard
        assert b.fake is a.fake
        placed = [x for x in a.fake.asked if x[0] == "place"]
        assert placed == [("place", PLACEMENT)], "sent once across both pods"
        # A asks the venue what became of it, never sends it again: it finds
        # B's order by the placement's ID.
        assert a.trader.working[PLACEMENT].unanswered
        await a.poll(1)
        assert a.trader.working[PLACEMENT].venue_order_id == "1"
        assert [x for x in a.fake.asked if x[0] == "place"] == [("place", PLACEMENT)]

    asyncio.run(lapse())


# ── H4: the storage read before Register ────────────────────────────────────


def test_storage_dir_before_register_on_a_converted_claim_fails_loudly(root: Path) -> None:
    _converted(root)
    with pytest.raises(RuntimeError, match="on_start"):
        edge.storage_dir()
    # The whole is the instance's, and a store made on it follows its shard.
    assert edge.instance_storage_dir() == root
    assert storage_root() == root
    store = RawStore(storage_root(), kind="responses")
    edge._registered_as(0, 1)
    assert edge.storage_dir() == root / "shard-0"
    key = store.keep("candles", "BTC-USD", {"received_at_ns": 1_794_924_000_000_000_000})
    assert key.startswith("shard-0/responses/") and (root / key).is_file()


def test_storage_dir_before_register_elsewhere_is_as_before(root: Path) -> None:
    assert edge.storage_dir() == root, "no copy marker: an unconverted claim"


def test_an_old_template_trader_on_a_converted_claim_fails_loudly(root: Path) -> None:
    _converted(root)
    with pytest.raises(RuntimeError, match="on_start"):
        sent, enabled, originated = connectivity.trading_files(edge.storage_dir())
    assert not (root / "trading").exists()


def _step() -> Migration:
    return next(m for m in recorded() if m.target == "0.37.0")


def test_the_old_template_is_migrated_to_read_its_files_on_start() -> None:
    module = _step().module()
    assert module is not None
    old = (ROOT / "src/meridian/migrations/to_0_35_0/entry/connectivity-0.35.0.txt").read_text()
    done = module.rewrite("src/reference_plugin/__main__.py", old)
    template = ROOT / "templates/connectivity/src/reference_plugin/__main__.py"
    assert done.text == template.read_text()
    assert done.rules == ("trading-files-on-start",)
    assert module.left("src/reference_plugin/__main__.py", done.text) == []
    # Migrated again, it is left as it is.
    assert module.rewrite("src/reference_plugin/__main__.py", done.text).text == done.text


def test_the_migrated_template_reads_shard_0_on_a_converted_claim(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The migrated template's Trader, given no files, started once registered
    as shard 0 of a standby instance, finds what the copy put under shard-0/."""
    from test_connectivity_trader import FakeVenue

    _converted(root)
    sent = root / "shard-0" / "trading" / "sent.json"
    sent.parent.mkdir(parents=True)
    sent.write_text(json.dumps([PLACEMENT]))
    venue = FakeVenue("ACC-NUMBER-1")
    trader = connectivity.Trader(  # as the migrated main() builds it
        lambda: venue, now=lambda: datetime.now(UTC), market_zone=UTC
    )
    edge._registered_as(0, 1)
    trader._from_storage()  # on_start's first step
    assert PLACEMENT in trader._sent
    assert not (root / "trading").exists()


def test_a_storage_read_outside_on_start_is_left_by_hand() -> None:
    module = _step().module()
    assert module is not None
    early = """\
from meridian import edge
from meridian.roles.data import option_chains


class Chains:
    def __init__(self) -> None:
        self.times = option_chains.SeriesTimes(edge.storage_dir() / "series.json")
        self.feed = option_chains.Feed(series_path=edge.storage_dir() / "series.json")

    async def on_start(self) -> None:
        self.later = option_chains.SeriesTimes(edge.storage_dir() / "series.json")
"""
    found = module.left("src/chains/feed.py", early)
    assert [(f.rule, f.line) for f in found] == [
        ("storage-read-before-register", 7),
        ("storage-read-before-register", 8),
    ]
    assert module.left("tests/test_feed.py", early) == []
    kept = """\
from meridian import edge
from meridian.roles import connectivity

sent = connectivity.Sent(edge.storage_dir() / "trading" / "sent.json")
"""
    assert [f.rule for f in module.left("src/p/__main__.py", kept)] == [
        "storage-read-before-register"
    ]


def test_a_noted_file_read_whole_is_left_by_hand() -> None:
    module = _step().module()
    assert module is not None
    test = """\
def test_sent(tmp_path):
    assert json.loads((tmp_path / "trading" / "sent.json").read_text()) == ["P"]
    assert json.loads((tmp_path / "trading" / "enabled.json").read_text()) == ["C"]
    Sent(tmp_path / "trading" / "sent.json").note("P")
"""
    found = module.left("tests/test_trading.py", test)
    assert [(f.rule, f.line) for f in found] == [
        ("noted-file-read-whole", 2),
        ("noted-file-read-whole", 3),
    ]


# ── sdk5-review: a marker with nothing behind it, charges, an RFQ ───────────


def _unknowns(recorder: Recorder) -> list[str]:
    return [
        p.placement_id
        for p in recorder.on("ReportPlacement")
        if p.event == ops.PLACEMENT_EVENT_OUTCOME_UNKNOWN
    ]


def test_a_marker_with_no_order_at_the_venue_is_said_unknown_once(tmp_path: Path) -> None:
    """H1: noted by a pod whose send failed or whose report was fenced, and
    not at the venue: said outcome unknown once, still looked for, and the
    account's venue-originated orders read meanwhile."""
    from test_connectivity_trader import Rig

    file = tmp_path / "trading" / "sent.json"
    Sent(file).note(PLACEMENT)  # the other pod's note
    recorder = Recorder("broker")
    rig = Rig(recorder, sent=Sent(file))
    originated: list[str] = []

    async def seen(venue: Any, code: str, record: VenueOrder, key: str) -> None:
        originated.append(record.order_id)

    rig.trader._originated = seen  # type: ignore[method-assign]
    held = rig.placement(PLACEMENT)
    rig.holds(held)
    rig.fake.held["9"] = VenueOrder("9", "app-order-1", "filled", placed_at=testing.NOW)
    rig.fake.held["10"] = VenueOrder("10", "", "filled", placed_at=testing.NOW)

    async def go() -> None:
        await rig.hear(held)
        await rig.poll(3)

    asyncio.run(go())
    assert [x for x in rig.fake.asked if x[0] == "place"] == []
    assert _unknowns(recorder) == [PLACEMENT], "said once, not each poll"
    assert rig.trader.working[PLACEMENT].unanswered, "still looked for"
    # Said unknown in the first poll, so no order is held back after it
    # (sdk5b-review B-M3; the brief's item 4).
    assert originated == ["9", "10"] * 3


def test_a_note_that_was_not_kept_leaves_no_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    file = tmp_path / "trading" / "sent.json"
    held = Sent(file)

    def failed(_: int) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "fsync", failed)
    with pytest.raises(OSError):
        held.note(PLACEMENT)
    monkeypatch.undo()
    assert not (tmp_path / "trading" / "sent" / PLACEMENT).exists()
    assert PLACEMENT not in Sent(file)
    assert Sent(file).note(PLACEMENT) is True


def test_an_earlier_releases_note_made_since_start_is_seen(tmp_path: Path) -> None:
    """L1: a 0.36 pod writing sent.json whole inside a lapse."""
    file = tmp_path / "trading" / "sent.json"
    file.parent.mkdir(parents=True)
    file.write_text(json.dumps([]))
    held = Sent(file)
    file.write_text(json.dumps([PLACEMENT]))
    import os

    os.utime(file, ns=(1, 1))
    assert PLACEMENT in held
    assert held.note(PLACEMENT) is False


def test_a_charge_whose_report_failed_is_not_noted(tmp_path: Path) -> None:
    """M1: a deposed pod's charge report is fenced; the holder reports it."""
    from test_connectivity_trader import Rig

    file = tmp_path / "trading" / "charged.json"
    deposed = Rig(Recorder("broker"))
    deposed.trader.charged = Sent(file)

    async def fenced(**_: Any) -> None:
        raise RuntimeError("fenced: this shard's epoch is no longer the instance's")

    deposed.trader.report_charge = fenced  # type: ignore[method-assign]
    charge = {"kind": "commission", "amount": "1.25", "currency": "USD"}
    with pytest.raises(RuntimeError):
        asyncio.run(deposed.trader._charge(PLACEMENT, "act-1", charge))
    recorder = Recorder("broker")
    holder = Rig(recorder)
    holder.trader.charged = Sent(file)
    asyncio.run(holder.trader._charge(PLACEMENT, "act-1", charge))
    assert len(recorder.on("ReportCharge")) == 1
    assert f"act-1|{PLACEMENT}" in Sent(file)


def test_charges_are_read_from_storage_on_start(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L2: a Trader given no `charged` keeps it in its shard's folder."""
    from test_connectivity_trader import Rig

    monkeypatch.setattr(edge, "_serving", (1, 2))
    rig = Rig(Recorder("broker"))
    asyncio.run(rig.trader.on_start())
    rig.trader.charged.note("act-1|P")
    assert (root / "shard-1" / "trading" / "charged" / "act-1%7CP").is_file()


def test_an_rfq_acceptance_is_sent_once_across_a_restart(tmp_path: Path) -> None:
    """M2: the acceptance makes the venue's order; a restart before its order
    was reported accepts nothing again."""
    from test_v27 import RfqRig, _minted

    file = tmp_path / "trading" / "sent.json"

    def rig_on(venue: Any = None) -> Any:
        recorder = Recorder("dealers-1")
        recorder.answer(
            "ResolveVenue",
            lambda p: ops.ResolveVenueResult(
                found=True, venue=ops.VenueRecord(venue_id=f"VEN-{p.identifiers[0].value}")
            ),
        )
        recorder.answer("ReportPlacementQuote", _minted)
        return RfqRig(recorder, sent=Sent(file), broker=venue)

    async def go() -> None:
        first = rig_on()
        held = first.placement(placement_type=ops.PLACEMENT_TYPE_RFQ)
        first.holds(held, order_type=ops.ORDER_TYPE_REQUEST_FOR_QUOTE)
        await first.hear(held)
        picked = ops.Placement()
        picked.CopyFrom(held)
        picked.picked_quote_id = "PQT-Q-B"
        picked.quotes.extend(
            [
                ops.PlacementQuote(quote_id="PQT-Q-B", dealer_id="VEN-DLR-B",
                                   dealer_quote_id="Q-B", side=ops.SIDE_SELL,
                                   outcome=ops.PLACEMENT_QUOTE_OUTCOME_PICKED,
                                   price=testing.money("1.0850")),
            ]
        )  # fmt: skip
        await first.hear(picked)
        venue = first.venue
        assert venue.accepted == ["Q-B"]
        # Restarted (or the shard taken) before the order was reported.
        again = rig_on(venue)
        again.holds(held, order_type=ops.ORDER_TYPE_REQUEST_FOR_QUOTE)
        await again.hear(held)
        await again.hear(picked)
        assert venue.accepted == ["Q-B"], "accepted once in all"

    asyncio.run(go())


def test_storage_dir_before_register_on_a_claim_holding_a_shards_folder_fails(
    root: Path,
) -> None:
    """M3: a shared claim made new has no copy marker; a shard's folder in it
    says it is shared."""
    (root / "shard-1").mkdir()
    with pytest.raises(RuntimeError, match="on_start"):
        edge.storage_dir()
    (root / "shard-1").rmdir()
    (root / "shard-notes").mkdir()
    assert edge.storage_dir() == root, "only a shard's folder by its name"


def test_a_sharded_trader_with_no_storage_says_so(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """M4: with no storage on a standby instance, at most once does not hold."""
    from test_connectivity_trader import Rig

    monkeypatch.delenv("MERIDIAN_STORAGE_DIR", raising=False)
    monkeypatch.setattr(edge, "_serving", (0, 1))
    rig = Rig(Recorder("broker"))
    with caplog.at_level("ERROR"):
        asyncio.run(rig.trader.on_start())
    assert any("no storage is granted" in r.getMessage() for r in caplog.records)


# ── sdk5b-review: an unknown said once, said resolved, the hold bounded ─────


def _said(held: ops.Placement) -> ops.Placement:
    """The placement as the book holds it once said outcome unknown: queued,
    with the condition."""
    said = ops.Placement()
    said.CopyFrom(held)
    said.status.conditions.add(condition=ops.PLACEMENT_CONDITION_OUTCOME_UNKNOWN)
    return said


def _events(recorder: Recorder, pid: str = PLACEMENT) -> list[str]:
    return [
        ops.PlacementEvent.Name(p.event)
        for p in recorder.on("ReportPlacement")
        if p.placement_id == pid
    ]


def test_an_unknown_the_book_holds_is_not_said_again_after_a_restart(tmp_path: Path) -> None:
    """B-M1: restarted (or the shard taken), the placement still queued with
    its condition: said already, so said no more."""
    from test_connectivity_trader import Rig

    file = tmp_path / "trading" / "sent.json"
    Sent(file).note(PLACEMENT)
    recorder = Recorder("broker")
    rig = Rig(recorder, sent=Sent(file))
    held = _said(rig.placement(PLACEMENT))
    rig.holds(held)

    async def go() -> None:
        await rig.hear(held)
        await rig.poll(3)

    asyncio.run(go())
    assert _unknowns(recorder) == []
    assert rig.trader.working[PLACEMENT].unanswered, "still looked for"


def test_an_unknown_said_is_noted_so_the_next_pod_says_it_no_more(tmp_path: Path) -> None:
    """B-M1: the report is noted beside the send's marker, made exclusively;
    a pod after it, reading the placement before the book shows the
    condition, says nothing again."""
    from test_connectivity_trader import Rig

    file = tmp_path / "trading" / "sent.json"
    Sent(file).note(PLACEMENT)
    first = Recorder("broker")
    rig = Rig(first, sent=Sent(file))
    held = rig.placement(PLACEMENT)
    rig.holds(held)

    async def go(on: Any) -> None:
        await on.hear(held)
        await on.poll(2)

    asyncio.run(go(rig))
    assert _unknowns(first) == [PLACEMENT]
    assert f"unknown:{PLACEMENT}" in Sent(file)
    again = Recorder("broker")
    restarted = Rig(again, sent=Sent(file))
    restarted.holds(held)
    asyncio.run(go(restarted))
    assert _unknowns(again) == []


def test_a_send_unanswered_is_noted_as_said_unknown(tmp_path: Path) -> None:
    """B-M1, place_once's own path: the send unanswered is said unknown and
    noted; a restart finding nothing at the venue says it no more."""
    from test_connectivity_trader import LOST, Rig

    file = tmp_path / "trading" / "sent.json"
    first = Recorder("broker")
    rig = Rig(first, symbol=LOST, sent=Sent(file))
    held = rig.placement(PLACEMENT)
    rig.holds(held)
    asyncio.run(rig.hear(held))
    assert _unknowns(first) == [PLACEMENT]
    assert f"unknown:{PLACEMENT}" in Sent(file)
    again = Recorder("broker")
    restarted = Rig(again, symbol=LOST, sent=Sent(file))  # its venue holds nothing
    restarted.holds(held)

    async def go() -> None:
        await restarted.hear(held)
        await restarted.poll(2)

    asyncio.run(go())
    assert _unknowns(again) == []


def test_an_unknown_found_at_the_venue_is_said_resolved_once(tmp_path: Path) -> None:
    """B-M2: the order lands after the unknown was said: resolved, then
    acknowledged, each once."""
    from test_connectivity_trader import Rig

    file = tmp_path / "trading" / "sent.json"
    Sent(file).note(PLACEMENT)
    recorder = Recorder("broker")
    rig = Rig(recorder, sent=Sent(file))
    held = rig.placement(PLACEMENT)
    rig.holds(held)

    async def go() -> None:
        await rig.hear(held)
        await rig.poll(1)
        rig.fake.held["1"] = VenueOrder(
            "1", PLACEMENT, "open", placed_at=testing.NOW, updated_at=testing.NOW
        )
        await rig.poll(3)

    asyncio.run(go())
    assert _events(recorder) == [
        "PLACEMENT_EVENT_OUTCOME_UNKNOWN",
        "PLACEMENT_EVENT_OUTCOME_RESOLVED",
        "PLACEMENT_EVENT_ACKNOWLEDGED",
    ]


def test_a_send_unanswered_then_found_is_said_resolved() -> None:
    from test_connectivity_trader import LOST, placed

    recorder = Recorder("broker")
    rig = placed(recorder, symbol=LOST)
    asyncio.run(rig.poll(2))
    assert _events(recorder) == [
        "PLACEMENT_EVENT_OUTCOME_UNKNOWN",
        "PLACEMENT_EVENT_OUTCOME_RESOLVED",
        "PLACEMENT_EVENT_ACKNOWLEDGED",
    ]


def test_an_unknown_the_book_holds_is_said_resolved_by_the_next_pod(tmp_path: Path) -> None:
    """B-M2 on resume: the book's condition says it was said; the next pod
    finding its order says it resolved."""
    from test_connectivity_trader import Rig

    file = tmp_path / "trading" / "sent.json"
    Sent(file).note(PLACEMENT)
    recorder = Recorder("broker")
    rig = Rig(recorder, sent=Sent(file))
    rig.fake.held["1"] = VenueOrder(
        "1", PLACEMENT, "open", placed_at=testing.NOW, updated_at=testing.NOW
    )
    held = _said(rig.placement(PLACEMENT))
    rig.holds(held)

    async def go() -> None:
        await rig.hear(held)
        await rig.poll(2)

    asyncio.run(go())
    assert _events(recorder) == [
        "PLACEMENT_EVENT_OUTCOME_RESOLVED",
        "PLACEMENT_EVENT_ACKNOWLEDGED",
    ]


def test_a_status_mapped_at_last_is_said_resolved() -> None:
    from test_connectivity_trader import ODD, placed

    recorder = Recorder("broker")
    rig = placed(recorder, symbol=ODD)
    asyncio.run(rig.poll())
    from dataclasses import replace

    rig.fake.held["1"] = replace(rig.fake.held["1"], status="open")
    asyncio.run(rig.poll(2))
    assert _events(recorder) == [
        "PLACEMENT_EVENT_OUTCOME_UNKNOWN",
        "PLACEMENT_EVENT_OUTCOME_RESOLVED",
        "PLACEMENT_EVENT_ACKNOWLEDGED",
    ]


def test_the_hold_on_the_venues_own_orders_ends_once_said_unknown(tmp_path: Path) -> None:
    """B-M3: an order naming no client order ID is held back only until the
    unanswered placement is said unknown; a report that failed keeps it."""
    from meridian.errors import MeridianError
    from test_connectivity_trader import Rig

    file = tmp_path / "trading" / "sent.json"
    Sent(file).note(PLACEMENT)
    recorder = Recorder("broker")
    rig = Rig(recorder, sent=Sent(file))
    originated: list[str] = []

    async def seen(venue: Any, code: str, record: VenueOrder, key: str) -> None:
        originated.append(record.order_id)

    rig.trader._originated = seen  # type: ignore[method-assign]
    held = rig.placement(PLACEMENT)
    rig.holds(held)
    rig.fake.held["10"] = VenueOrder("10", "", "filled", placed_at=testing.NOW)
    report = rig.trader.report_placement
    failures = [MeridianError("the shard's epoch is not the instance's")]

    async def once_failing(**kw: Any) -> Any:
        if failures and kw.get("event") == ops.PLACEMENT_EVENT_OUTCOME_UNKNOWN:
            raise failures.pop()
        return await report(**kw)

    rig.trader.report_placement = once_failing  # type: ignore[method-assign]

    async def go() -> None:
        await rig.hear(held)
        await rig.poll(1)
        assert originated == [], "held back while not said"
        await rig.poll(3)

    asyncio.run(go())
    assert _unknowns(recorder) == [PLACEMENT]
    assert originated == ["10", "10", "10"]


def test_a_failed_unknown_report_is_not_made_again_where_the_book_holds_it(
    tmp_path: Path,
) -> None:
    """B-L6: the report failed (its reply lost, say), and the book shows it
    said: read before reporting again, it is not."""
    from meridian.errors import MeridianError
    from test_connectivity_trader import Rig

    file = tmp_path / "trading" / "sent.json"
    Sent(file).note(PLACEMENT)
    recorder = Recorder("broker")
    rig = Rig(recorder, sent=Sent(file))
    held = rig.placement(PLACEMENT)
    rig.holds(held)
    report = rig.trader.report_placement

    async def landed_unanswered(**kw: Any) -> Any:
        if kw.get("event") == ops.PLACEMENT_EVENT_OUTCOME_UNKNOWN:
            await report(**kw)
            rig.holds(_said(held))
            raise MeridianError("no answer in time")
        return await report(**kw)

    rig.trader.report_placement = landed_unanswered  # type: ignore[method-assign]

    async def go() -> None:
        await rig.hear(held)
        await rig.poll(3)

    asyncio.run(go())
    assert _unknowns(recorder) == [PLACEMENT]


def _rfq_rig(file: Path, venue: Any = None) -> Any:
    from test_v27 import RfqRig, _minted

    recorder = Recorder("dealers-1")
    recorder.answer(
        "ResolveVenue",
        lambda p: ops.ResolveVenueResult(
            found=True, venue=ops.VenueRecord(venue_id=f"VEN-{p.identifiers[0].value}")
        ),
    )
    recorder.answer("ReportPlacementQuote", _minted)
    return RfqRig(recorder, sent=Sent(file), broker=venue)


def _picked(held: ops.Placement) -> ops.Placement:
    picked = ops.Placement()
    picked.CopyFrom(held)
    picked.picked_quote_id = "PQT-Q-B"
    picked.quotes.extend(
        [
            ops.PlacementQuote(quote_id="PQT-Q-B", dealer_id="VEN-DLR-B",
                               dealer_quote_id="Q-B", side=ops.SIDE_SELL,
                               outcome=ops.PLACEMENT_QUOTE_OUTCOME_PICKED,
                               price=testing.money("1.0850")),
            ops.PlacementQuote(quote_id="PQT-Q-A", dealer_id="VEN-DLR-A",
                               dealer_quote_id="Q-A", side=ops.SIDE_SELL,
                               outcome=ops.PLACEMENT_QUOTE_OUTCOME_OPEN,
                               price=testing.money("1.0852")),
        ]
    )  # fmt: skip
    return picked


def test_an_rfq_acceptance_noted_with_nothing_behind_it_is_said_unknown_once(
    tmp_path: Path,
) -> None:
    """B-M4: the pod that noted the acceptance never reached the venue; the
    next one accepts nothing, says it unknown once, and still looks for it."""
    file = tmp_path / "trading" / "sent.json"

    async def go() -> None:
        first = _rfq_rig(file)
        held = first.placement(placement_type=ops.PLACEMENT_TYPE_RFQ)
        first.holds(held, order_type=ops.ORDER_TYPE_REQUEST_FOR_QUOTE)
        await first.hear(held)
        venue = first.venue

        def lost(*_: Any) -> Any:
            raise RuntimeError("the process ended before the venue was asked")

        venue.accept_quote = lost
        with pytest.raises(RuntimeError):
            await first.hear(_picked(held))
        del venue.accept_quote
        again = _rfq_rig(file, venue)
        again.holds(held, order_type=ops.ORDER_TYPE_REQUEST_FOR_QUOTE)
        await again.hear(held)
        await again.hear(_picked(held))
        await again.hear(_picked(held))
        await again.poll(2)
        assert venue.accepted == [], "never accepted"
        assert _unknowns(again.recorder) == [held.placement_id]
        assert again.trader.working[held.placement_id].unanswered

    asyncio.run(go())


def test_an_rfq_acceptance_found_after_a_restart_records_its_quote_outcomes(
    tmp_path: Path,
) -> None:
    """B-L1: the restarted pod finds the acceptance's order by the
    placement's ID and records the picked quote accepted, the other not
    picked, under the keys the first used."""
    file = tmp_path / "trading" / "sent.json"

    async def go() -> None:
        first = _rfq_rig(file)
        held = first.placement(placement_type=ops.PLACEMENT_TYPE_RFQ)
        first.holds(held, order_type=ops.ORDER_TYPE_REQUEST_FOR_QUOTE)
        await first.hear(held)
        venue = first.venue
        accept = venue.accept_quote

        def unanswered(*args: Any) -> Any:
            from meridian.roles.connectivity import VenueUnanswered

            accept(*args)
            raise VenueUnanswered("timed out", "rfq/lost")

        venue.accept_quote = unanswered
        await first.hear(_picked(held))
        assert venue.accepted == ["Q-B"]
        del venue.accept_quote
        venue.orders = lambda code: (
            [VenueOrder("V-RFQ-1", held.placement_id, "open", placed_at=testing.NOW)],
            "rfq/orders",
        )
        again = _rfq_rig(file, venue)
        again.holds(held, order_type=ops.ORDER_TYPE_REQUEST_FOR_QUOTE)
        await again.hear(held)
        await again.hear(_picked(held))
        await again.poll(1)
        assert venue.accepted == ["Q-B"], "accepted once in all"
        said = {
            (q.quote_id, ops.PlacementQuoteOutcome.Name(q.outcome), q.idempotency_key)
            for q in again.recorder.on("ReportPlacementQuote")
            if q.quote_id
        }
        assert {
            ("PQT-Q-B", "PLACEMENT_QUOTE_OUTCOME_ACCEPTED", "quote:PQT-Q-B:accepted"),
            ("PQT-Q-A", "PLACEMENT_QUOTE_OUTCOME_NOT_PICKED", "quote:PQT-Q-A:not-picked"),
        } <= said
        assert "PLACEMENT_EVENT_ACKNOWLEDGED" in _events(again.recorder, held.placement_id)

    asyncio.run(go())


def test_a_pick_whose_note_failed_is_taken_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B-L2: the acceptance's note raised (a full disk): nothing was sent,
    and the pick heard again is accepted then."""
    file = tmp_path / "trading" / "sent.json"

    async def go() -> None:
        rig = _rfq_rig(file)
        held = rig.placement(placement_type=ops.PLACEMENT_TYPE_RFQ)
        rig.holds(held, order_type=ops.ORDER_TYPE_REQUEST_FOR_QUOTE)
        await rig.hear(held)
        note = rig.trader._sent.note

        def full(name: str) -> bool:
            if name.startswith("accept:"):
                raise OSError(28, "No space left on device")
            return note(name)

        monkeypatch.setattr(rig.trader._sent, "note", full)
        with pytest.raises(OSError):
            await rig.hear(_picked(held))
        monkeypatch.undo()
        assert rig.venue.accepted == []
        await rig.hear(_picked(held))
        assert rig.venue.accepted == ["Q-B"]

    asyncio.run(go())


def test_a_held_placements_order_is_not_read_as_the_venues_own(tmp_path: Path) -> None:
    """B-L3: P sent, then a stop holds it when the next pod hears it; its
    order, naming P, is not reported on no placement."""
    from test_connectivity_trader import Rig

    file = tmp_path / "trading" / "sent.json"
    Sent(file).note(PLACEMENT)
    rig = Rig(Recorder("broker"), sent=Sent(file))
    originated: list[str] = []

    async def seen(venue: Any, code: str, record: VenueOrder, key: str) -> None:
        originated.append(record.order_id)

    rig.trader._originated = seen  # type: ignore[method-assign]
    rig.fake.held["1"] = VenueOrder("1", PLACEMENT, "filled", placed_at=testing.NOW)
    held = rig.placement(PLACEMENT)
    rig.holds(held)

    async def go() -> None:
        await rig.instruct(ops.TRADING_INSTRUCTION_VALUE_STOP)
        await rig.hear(held)
        await rig.poll(2)

    asyncio.run(go())
    assert PLACEMENT in rig.trader.held
    assert originated == []


def test_an_earlier_releases_rewrite_in_the_same_tick_is_seen(tmp_path: Path) -> None:
    """B-L4: keyed on the file's time, size and inode, and a torn read
    tried again."""
    import os

    file = tmp_path / "trading" / "sent.json"
    file.parent.mkdir(parents=True)
    file.write_text(json.dumps([]))
    os.utime(file, ns=(5, 5))
    held = Sent(file)
    file.write_text('["PLC-')  # caught half written
    os.utime(file, ns=(6, 6))
    assert "PLC-X" not in held
    file.write_text(json.dumps(["PLC-X"]))
    os.utime(file, ns=(6, 6))  # finished in the same tick
    assert "PLC-X" in held
    file.write_text(json.dumps(["PLC-X", PLACEMENT]))
    os.utime(file, ns=(6, 6))  # rewritten again in the same tick, longer
    assert PLACEMENT in held


def test_a_digest_marker_is_never_seen_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B-L5: a name too long for a file is written whole before its marker
    appears; a crash between leaves no marker."""
    import os

    file = tmp_path / "trading" / "sent.json"
    name = "x" * 400

    def crashed(*_: Any) -> None:
        raise KeyboardInterrupt  # the process ends here

    monkeypatch.setattr(os, "link", crashed)
    with pytest.raises(KeyboardInterrupt):
        Sent(file).note(name)
    monkeypatch.undo()
    folder = tmp_path / "trading" / "sent"
    assert [p.name for p in folder.iterdir()] == []
    assert Sent(file).note(name) is True and name in Sent(file)


def test_each_folder_a_note_makes_is_made_durable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B-L5: `trading/` and `trading/sent/` both new: each one's entry synced
    in the folder above it."""
    from meridian.roles.connectivity import _bookkeeping

    synced: list[Path] = []
    monkeypatch.setattr(_bookkeeping, "_sync_folder", synced.append)
    Sent(tmp_path / "trading" / "sent.json").note(PLACEMENT)
    assert {tmp_path, tmp_path / "trading"} <= set(synced)


# ── PO 73: the launcher's shard count ───────────────────────────────────────


def test_storage_dir_before_register_on_a_sharded_instance_fails(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A storage no pod has written in yet: the launcher's shard count says
    it is shared."""
    monkeypatch.setenv("MERIDIAN_PLUGIN_SHARDS", "1")
    with pytest.raises(RuntimeError, match="MERIDIAN_PLUGIN_SHARDS"):
        edge.storage_dir()
    monkeypatch.setenv("MERIDIAN_PLUGIN_SHARDS", "3")
    with pytest.raises(RuntimeError, match="on_start"):
        edge.storage_dir()
    edge._registered_as(2, 3)
    assert edge.storage_dir() == root / "shard-2"


def test_storage_dir_before_register_on_an_instances_one_pod_is_as_before(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MERIDIAN_PLUGIN_SHARDS", raising=False)
    assert edge.storage_dir() == root
    monkeypatch.setenv("MERIDIAN_PLUGIN_SHARDS", "")
    assert edge.storage_dir() == root
