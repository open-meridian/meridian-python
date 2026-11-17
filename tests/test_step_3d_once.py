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
    assert originated == ["9", "9", "9"], "only an order that could be its is held back"


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
