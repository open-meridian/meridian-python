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
from meridian.roles import connectivity
from meridian.roles.connectivity import Sent, place_once
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
        a, b = Rig(Recorder("broker")), Rig(Recorder("broker"))
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
        placed = [x for x in (*a.fake.asked, *b.fake.asked) if x[0] == "place"]
        assert placed == [("place", PLACEMENT)], "sent once across both pods"
        # A asks the venue what became of it, never sends it again.
        assert a.trader.working[PLACEMENT].unanswered

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
