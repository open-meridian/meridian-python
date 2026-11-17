"""A storage per shard (step 3d, checkpoint 5, item 30): one storage shared
by an instance's pods, a folder per shard. The plugin learns its shard at
Register (`RegisterReply.shard`, `.shards`); `storage_dir()` is then its
shard's folder and `instance_storage_dir()` the whole; keys, archive objects
and a move's unit carry `shard-<n>/`; each shard keeps its own index, and
`find_record` reads whichever shard a key names. A key with no prefix is
what the instance kept before it ran as shards, copied under `shard-0/`. An
instance of one pod (`shards` 0) is as before. Against the fake sidecar,
which answers the shard at Register and records moves keyed by unit, as the
conductor does."""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import pytest

import meridian
from meridian import edge
from meridian.declaration import Declaration, RecordKind, Storage
from meridian.edge import RawStore, storage_root
from meridian.suites import Recorder
from meridian.testing import caller_header
from meridian.v1 import sidecar_pb2

DECLARATION = Declaration(
    settings=(meridian.Setting("consumer_key", secret=True, required=True),),
    storage=Storage(
        kinds=(
            RecordKind("activity", "Reported activity", window_days=2555, archivable=True),
            RecordKind("responses", "Raw responses", window_days=30, archivable=True),
        )
    ),
)
FIRST, LAST = 1_551_398_400_000_000_000, 1_554_076_799_000_000_000
UNIT = "activity/ACC-1/2019-03"
#: 2026-11-17 14:00 UTC.
AT = 1_794_924_000_000_000_000
ARCHIVED = sidecar_pb2.MOVE_OUTCOME_ARCHIVED


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


@pytest.fixture
def archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    given = tmp_path / "archive"
    given.mkdir()
    monkeypatch.setenv("MERIDIAN_ARCHIVE_DIR", str(given))
    return given


async def _pod(
    service: Any, address: str, shard: int, shards: int, past: str = "archived"
) -> meridian.Plugin:
    """A pod of the instance registered as `shard` of `shards`, its window
    settings delivered: `past` past the window, archived by default."""
    service.shard, service.shards = shard, shards
    service.settings = [
        sidecar_pb2.SettingsDelivery(
            values=[
                sidecar_pb2.SettingValue(name=name, value=value)
                for name, value in (
                    ("activity_window_days", "2555"),
                    ("activity_past_window", past),
                    ("responses_window_days", "30"),
                    ("responses_past_window", past),
                )
            ]
        )
    ]
    plugin = await meridian.connect(address, heartbeat=False, declaration=DECLARATION, roles=[])
    async for _ in plugin.settings():
        break
    return plugin


def _unit_in(folder: Path, says: str) -> None:
    unit = folder / UNIT
    unit.mkdir(parents=True)
    (unit / "act-77.json").write_text(json.dumps({"id": "act-77", "says": says}))


async def _archived(plugin: meridian.Plugin) -> None:
    await plugin.archive_unit(
        "activity", UNIT, record_count=1, first_received_ns=FIRST, last_received_ns=LAST
    )


# ── The shard learned at Register ───────────────────────────────────────────


async def test_the_pod_writes_its_shards_folder_once_registered(
    sidecar: Any, root: Path
) -> None:
    service, address = sidecar
    assert edge.storage_dir() == root, "no shard is known before Register"
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        assert edge.storage_dir() == root / "shard-1"
        assert edge.instance_storage_dir() == root
    finally:
        await plugin.leave()
    # Kept while the process waits for its sidecar again.
    assert edge.storage_dir() == root / "shard-1"


# ── Two shards on one root ──────────────────────────────────────────────────


async def test_two_shards_on_one_root_do_not_collide(sidecar: Any, root: Path) -> None:
    service, address = sidecar
    kept: dict[int, tuple[str, str]] = {}
    for shard in (0, 1):
        plugin = await _pod(service, address, shard=shard, shards=2)
        try:
            # Made as a plugin makes it, on the granted storage.
            store = RawStore(storage_root(), kind="responses")
            record = {"received_at_ns": AT, "body": f"shard {shard}"}
            key = store.keep("candles", "BTC-USD", record)
            ref = plugin.raw_record(key)
            kept[shard] = (key, ref.key)
        finally:
            await plugin.leave()
    (key0, ref0), (key1, ref1) = kept[0], kept[1]
    assert key0.startswith("shard-0/responses/2026-11-17/") and ref0 == key0
    assert key1.startswith("shard-1/responses/2026-11-17/") and ref1 == key1
    assert key0 != key1
    assert not (root / "responses").exists(), "nothing written at the storage's root"
    # Any pod reads either shard's record by its key.
    reader = RawStore(storage_root(), kind="responses")
    assert reader.get(key0) == {"received_at_ns": AT, "body": "shard 0"}
    assert reader.get(key1) == {"received_at_ns": AT, "body": "shard 1"}


async def test_a_store_made_before_register_writes_in_its_shard(
    sidecar: Any, root: Path
) -> None:
    service, address = sidecar
    store = RawStore(storage_root(), kind="responses")
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        key = store.keep("candles", "BTC-USD", {"received_at_ns": AT, "body": "x"})
    finally:
        await plugin.leave()
    assert key.startswith("shard-1/")
    assert (root / key).is_file()


async def test_a_takeover_resumes_the_shards_line(sidecar: Any, root: Path) -> None:
    service, address = sidecar
    holder = await _pod(service, address, shard=1, shards=2)
    try:
        store = RawStore(storage_root(), kind="responses")
        first = store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT, "body": "a"})
        second = store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT + 1, "body": "b"})
        assert holder.raw_record(second).key == second, "a key prefixed once"
    finally:
        await holder.leave()
    assert (first, second) == (
        "shard-1/responses/2026-11-17/ticker/BTC-USD.jsonl#0",
        "shard-1/responses/2026-11-17/ticker/BTC-USD.jsonl#1",
    )
    # The standby takes shard 1 over: a new process, a new store.
    edge._serving = None
    standby = await _pod(service, address, shard=1, shards=2)
    try:
        taken = RawStore(storage_root(), kind="responses")
        third = taken.keep_line("ticker", "BTC-USD", {"received_at_ns": AT + 2, "body": "c"})
        assert third == "shard-1/responses/2026-11-17/ticker/BTC-USD.jsonl#2"
        assert taken.get(first) == {"received_at_ns": AT, "body": "a"}
        assert taken.received(second, 0) == AT + 1
    finally:
        await standby.leave()


# ── The archive across shards ───────────────────────────────────────────────


async def test_archive_keys_are_unique_across_shards_and_both_moves_recorded(
    sidecar: Any, root: Path, archive: Path
) -> None:
    service, address = sidecar
    for shard in (0, 1):
        _unit_in(root / f"shard-{shard}", f"shard {shard}")
    for shard in (0, 1):
        plugin = await _pod(service, address, shard=shard, shards=2)
        try:
            await _archived(plugin)
        finally:
            await plugin.leave()
    for shard in (0, 1):
        held = json.loads((archive / f"shard-{shard}" / UNIT / "act-77.json").read_text())
        assert held["says"] == f"shard {shard}"
        assert not (root / f"shard-{shard}" / UNIT).exists()
    assert not (archive / UNIT).exists()
    # Both recorded: the conductor keys moves by unit, and the units are two.
    assert [(m.unit, m.outcome) for m, _, _ in service.moves] == [
        (f"shard-0/{UNIT}", ARCHIVED),
        (f"shard-1/{UNIT}", ARCHIVED),
    ]
    # Each shard keeps its own index.
    for shard in (0, 1):
        assert (root / f"shard-{shard}" / ".meridian" / "archive" / "index.json").is_file()
    assert not (root / ".meridian").exists()


async def test_find_record_finds_another_shards_unit(
    sidecar: Any, root: Path, archive: Path
) -> None:
    service, address = sidecar
    _unit_in(root / "shard-1", "shard 1")
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        await _archived(plugin)
        key = plugin.raw_record(f"{UNIT}/act-77.json").key
    finally:
        await plugin.leave()
    assert key == f"shard-1/{UNIT}/act-77.json"
    other = await _pod(service, address, shard=0, shards=2)
    try:
        found = other.find_record(key)
        assert found is not None and found.outcome == ARCHIVED
        assert found.unit == f"shard-1/{UNIT}"
        assert other.find_record(f"shard-0/{UNIT}/act-77.json") is None
    finally:
        await other.leave()


async def test_a_restore_takes_its_own_prefix_and_refuses_another_shards_unit(
    sidecar: Any, root: Path, archive: Path
) -> None:
    service, address = sidecar
    ben = caller_header("write", subject="local|ben", display_name="Ben", roles=["custody"])
    _unit_in(root / "shard-1", "shard 1")
    owner = await _pod(service, address, shard=1, shards=2)
    try:
        await _archived(owner)
        # As the page lists it: with the shard's prefix.
        restored = await owner.restore_unit("activity", f"shard-1/{UNIT}", for_caller=ben)
        assert restored.is_relative_to(root / "shard-1")
        assert json.loads((restored / "act-77.json").read_text())["says"] == "shard 1"
    finally:
        await owner.leave()
    other = await _pod(service, address, shard=0, shards=2)
    try:
        said = f"the unit shard-1/{UNIT} is shard 1's: its own pod restores it"
        with pytest.raises(ValueError, match=f"^{said}$"):
            await other.restore_unit("activity", f"shard-1/{UNIT}", for_caller=ben)
        with pytest.raises(ValueError, match=f"^{said}$"):
            await other.delete_unit("activity", f"shard-1/{UNIT}", for_caller=ben)
    finally:
        await other.leave()
    assert [m.outcome for m, _, _ in service.moves] == [
        ARCHIVED,
        sidecar_pb2.MOVE_OUTCOME_RESTORED,
    ]


# ── What the instance kept before it ran as shards ─────────────────────────


async def test_an_unprefixed_key_from_before_the_copy_resolves_under_shard_0(
    sidecar: Any, tmp_path: Path, root: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    # The instance as one pod, on its own claim: a raw record kept, a unit
    # archived, both under keys with no prefix.
    claim = tmp_path / "claim"
    claim.mkdir()
    monkeypatch.setenv("MERIDIAN_STORAGE_DIR", str(claim))
    _unit_in(claim, "before")
    alone = await _pod(service, address, shard=0, shards=0)
    try:
        old = RawStore(storage_root(), kind="responses").keep(
            "candles", "BTC-USD", {"received_at_ns": AT, "body": "before"}
        )
        await _archived(alone)
    finally:
        await alone.leave()
    assert not old.startswith("shard-")
    # The copy step: the old claim into the shared one's shard-0/.
    shutil.copytree(claim, root / "shard-0")
    monkeypatch.setenv("MERIDIAN_STORAGE_DIR", str(root))
    pod = await _pod(service, address, shard=1, shards=2)
    try:
        assert RawStore(storage_root(), kind="responses").get(old) == {
            "received_at_ns": AT,
            "body": "before",
        }
        found = pod.find_record(f"{UNIT}/act-77.json")
        assert found is not None and found.outcome == ARCHIVED
        assert found.unit == UNIT, "as it was recorded then"
        ben = caller_header("write", subject="local|ben", display_name="Ben", roles=["custody"])
        with pytest.raises(ValueError, match=f"^the unit {UNIT} is shard 0's"):
            await pod.restore_unit("activity", UNIT, for_caller=ben)
    finally:
        await pod.leave()
    # Shard 0's pod restores it from where it was archived then.
    first = await _pod(service, address, shard=0, shards=2)
    try:
        restored = await first.restore_unit("activity", UNIT, for_caller=ben)
        assert json.loads((restored / "act-77.json").read_text())["says"] == "before"
        assert restored.is_relative_to(root / "shard-0")
    finally:
        await first.leave()
    assert (archive / UNIT / "act-77.json").is_file()
    assert service.moves[-1][0].unit == UNIT


# ── An instance of one pod, as before ───────────────────────────────────────


async def test_an_instance_of_one_pod_is_as_before(
    sidecar: Any, root: Path, archive: Path
) -> None:
    service, address = sidecar
    _unit_in(root, "alone")
    plugin = await _pod(service, address, shard=0, shards=0)
    try:
        assert edge.storage_dir() == root == edge.instance_storage_dir()
        store = RawStore(storage_root(), kind="responses")
        key = store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT, "body": "a"})
        assert key == "responses/2026-11-17/ticker/BTC-USD.jsonl#0"
        assert plugin.raw_record(key).key == key
        assert (root / "responses/2026-11-17/ticker/BTC-USD.jsonl").is_file()
        await _archived(plugin)
        assert (archive / UNIT / "act-77.json").is_file()
        found = plugin.find_record(f"{UNIT}/act-77.json")
        assert found is not None and found.unit == UNIT
    finally:
        await plugin.leave()
    assert service.moves[0][0].unit == UNIT
    assert (root / ".meridian" / "archive" / "index.json").is_file()
    assert not any(p.name.startswith("shard-") for p in root.iterdir())


# ── Connectivity's trading files ────────────────────────────────────────────


def test_a_converted_instance_reads_shard_0s_sent_placements_never_sending_twice(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_connectivity_trader import Rig  # the made-up venue's rig

    # Before: one pod, its placement noted in trading/sent.json; the copy
    # step put it under shard-0/.
    placement = "PLC-01JAE00000000000000000001"
    sent = root / "shard-0" / "trading" / "sent.json"
    sent.parent.mkdir(parents=True)
    sent.write_text(json.dumps([placement]))
    # Now a standby instance: shard 0 of 1, the Trader given no files, as
    # the template makes it, started once registered.
    monkeypatch.setattr(edge, "_serving", (0, 1))
    recorder = Recorder("broker")
    rig = Rig(recorder)
    asyncio.run(rig.trader.on_start())
    held = rig.placement(placement)
    rig.holds(held)
    asyncio.run(rig.hear(held))
    assert [a for a in rig.fake.asked if a[0] == "place"] == []
    assert not (root / "trading").exists()


# ── The review's findings (sdk4-review) ─────────────────────────────────────


async def test_h1_a_deletion_on_a_shard_reports_its_prefixed_unit(
    sidecar: Any, root: Path
) -> None:
    service, address = sidecar
    day = "responses/2026-11-17"
    for shard in (0, 1):
        plugin = await _pod(service, address, shard=shard, shards=2, past="deleted")
        try:
            store = RawStore(storage_root(), kind="responses")
            store.keep("candles", "BTC-USD", {"received_at_ns": AT, "body": f"{shard}"})
            await store.tend(plugin, window_days=1, past="deleted", today=date(2026, 12, 1))
        finally:
            await plugin.leave()
        assert not (root / f"shard-{shard}" / day).exists()
    assert [(m.unit, m.outcome) for m, _, _ in service.moves] == [
        (f"shard-0/{day}", sidecar_pb2.MOVE_OUTCOME_DELETED),
        (f"shard-1/{day}", sidecar_pb2.MOVE_OUTCOME_DELETED),
    ]
    reader = await _pod(service, address, shard=0, shards=2, past="deleted")
    try:
        found = reader.find_record(f"shard-1/{day}/candles/x.json")
        assert found is not None and found.unit == f"shard-1/{day}"
    finally:
        await reader.leave()


async def test_h2_a_store_admitted_again_as_another_shard_writes_only_there(
    sidecar: Any, root: Path
) -> None:
    service, address = sidecar
    line = "responses/2026-11-17/ticker/BTC-USD.jsonl"
    plugin = await _pod(service, address, shard=1, shards=2)
    store = RawStore(storage_root(), kind="responses")
    try:
        store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT, "body": "a"})
        store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT + 1, "body": "b"})
    finally:
        await plugin.leave()
    # Its Lease lost, the process takes shard 0's: the same store.
    plugin = await _pod(service, address, shard=0, shards=2)
    try:
        key = store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT + 2, "body": "c"})
    finally:
        await plugin.leave()
    assert len((root / "shard-1" / line).read_text().splitlines()) == 2
    assert key == f"shard-0/{line}#0"
    assert store.get(key) == {"received_at_ns": AT + 2, "body": "c"}


async def test_h2_a_shard_taken_back_names_the_line_its_standby_left(
    sidecar: Any, root: Path
) -> None:
    service, address = sidecar
    line = root / "shard-1" / "responses/2026-11-17/ticker/BTC-USD.jsonl"
    plugin = await _pod(service, address, shard=1, shards=2)
    store = RawStore(storage_root(), kind="responses")
    try:
        store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT, "body": "a"})
    finally:
        await plugin.leave()
    # Its standby held shard 1 meanwhile, and kept a line.
    with line.open("a") as out:
        out.write(json.dumps({"received_at_ns": AT + 1, "body": "b"}) + "\n")
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        key = store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT + 2, "body": "c"})
    finally:
        await plugin.leave()
    assert key.endswith("#2")
    assert store.get(key) == {"received_at_ns": AT + 2, "body": "c"}


async def test_m1_a_lagging_holder_and_the_new_one_each_name_their_own_line(
    sidecar: Any, root: Path
) -> None:
    service, address = sidecar
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        old = RawStore(storage_root(), kind="responses")
        new = RawStore(storage_root(), kind="responses")
        kept = [
            (old, {"received_at_ns": AT, "body": "a"}),
            (new, {"received_at_ns": AT + 1, "body": "b"}),
            (old, {"received_at_ns": AT + 2, "body": "c"}),
            (new, {"received_at_ns": AT + 3, "body": "d"}),
        ]
        keys = [store.keep_line("ticker", "BTC-USD", record) for store, record in kept]
        for key, (_, record) in zip(keys, kept, strict=True):
            assert new.get(key) == record
        # A line a crash left unfinished is ended, and the next is named past it.
        path = root / "shard-1" / "responses/2026-11-17/ticker/BTC-USD.jsonl"
        with path.open("a") as out:
            out.write('{"received_at_ns": ')
        record = {"received_at_ns": AT + 4, "body": "e"}
        key = new.keep_line("ticker", "BTC-USD", record)
        assert new.get(key) == record
    finally:
        await plugin.leave()


async def test_m2_the_archives_bound_holds_across_every_shard(
    sidecar: Any, root: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    for shard in (0, 1):
        _unit_in(root / f"shard-{shard}", "x" * 100)
    size = (root / "shard-0" / UNIT / "act-77.json").stat().st_size
    monkeypatch.setenv("MERIDIAN_ARCHIVE_MOST_BYTES", str(size * 3 // 2))
    first = await _pod(service, address, shard=0, shards=2)
    try:
        await _archived(first)
    finally:
        await first.leave()
    second = await _pod(service, address, shard=1, shards=2)
    try:
        with pytest.raises(RuntimeError, match="would take it past"):
            await _archived(second)
    finally:
        await second.leave()
    assert (root / "shard-1" / UNIT).exists()


async def test_m3_a_store_on_a_folder_in_the_storage_follows_its_shard(
    sidecar: Any, root: Path
) -> None:
    service, address = sidecar
    store = RawStore(storage_root() / "raw", kind="responses")
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        key = store.keep("candles", "BTC-USD", {"received_at_ns": AT, "body": "x"})
        ref = plugin.raw_record(key).key
    finally:
        await plugin.leave()
    assert key.startswith("shard-1/raw/responses/") and ref == key
    assert (root / key).is_file()
    assert store.get(ref) == {"received_at_ns": AT, "body": "x"}


def _old_entry(folder: Path, unit: str, files: dict[str, list[Any]]) -> None:
    """An index entry as an instance of one pod wrote it: no prefix."""
    edge._Index(folder).write(
        {
            unit: edge._Moved(
                record_kind="activity",
                unit=unit,
                record_count=1,
                first_received_ns=FIRST,
                last_received_ns=LAST,
                state="archived",
                files=files,
            )
        }
    )


async def test_l1_on_shard_1_a_unit_with_no_prefix_is_shard_0s(
    sidecar: Any, root: Path, archive: Path
) -> None:
    service, address = sidecar
    ben = caller_header("write", subject="local|ben", display_name="Ben", roles=["custody"])
    _old_entry(root / "shard-0", UNIT, {})
    _unit_in(root / "shard-1", "shard 1")
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        await _archived(plugin)
        with pytest.raises(ValueError, match=f"^the unit {UNIT} is shard 0's"):
            await plugin.restore_unit("activity", UNIT, for_caller=ben)
        restored = await plugin.restore_unit("activity", f"shard-1/{UNIT}", for_caller=ben)
        assert restored.is_relative_to(root / "shard-1")
    finally:
        await plugin.leave()


async def test_l2_a_unit_archived_before_the_copy_but_not_indexed_is_not_archived_again(
    sidecar: Any, root: Path, archive: Path
) -> None:
    service, address = sidecar
    _unit_in(root / "shard-0", "before")
    # The pod of one pod archived it and reported it, and stopped before
    # its index was written.
    (archive / UNIT).mkdir(parents=True)
    shutil.copy(root / "shard-0" / UNIT / "act-77.json", archive / UNIT / "act-77.json")
    service.moves.append(
        (
            sidecar_pb2.RecordMoveRequest(
                record_kind="activity", unit=UNIT, record_count=1, outcome=ARCHIVED
            ),
            "",
            AT,
        )
    )
    plugin = await _pod(service, address, shard=0, shards=2)
    try:
        await _archived(plugin)
        found = plugin.find_record(f"shard-0/{UNIT}/act-77.json")
    finally:
        await plugin.leave()
    assert len(service.moves) == 1, "the conductor's again"
    assert not (archive / "shard-0").exists()
    assert not (root / "shard-0" / UNIT).exists()
    assert found is not None and found.unit == UNIT


async def test_l3_a_key_is_not_prefixed_where_no_storage_is_granted(
    sidecar: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    monkeypatch.delenv("MERIDIAN_STORAGE_DIR", raising=False)
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        assert plugin.raw_record("responses/x.json").key == "responses/x.json"
    finally:
        await plugin.leave()


def test_l3_the_traders_unkept_names_no_shard(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_connectivity_trader import Rig

    monkeypatch.setattr(edge, "_serving", (1, 2))
    rig = Rig(Recorder("broker"))
    assert rig.trader._raw("").key == "unkept"


async def test_l4_an_old_units_length_is_its_own(
    sidecar: Any, root: Path, archive: Path
) -> None:
    service, address = sidecar
    ben = caller_header("write", subject="local|ben", display_name="Ben", roles=["custody"])
    unit = "/".join(["u" * 50] * 10)  # 509 characters, as reported then
    data = b'{"id": "long"}'
    (archive / unit).mkdir(parents=True)
    (archive / unit / "f.json").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    _old_entry(root / "shard-0", unit, {"f.json": [len(data), digest]})
    plugin = await _pod(service, address, shard=0, shards=2)
    try:
        restored = await plugin.restore_unit("activity", unit, for_caller=ben)
    finally:
        await plugin.leave()
    assert (restored / "f.json").read_bytes() == data


def test_l5_a_stores_root_is_set_as_before(tmp_path: Path) -> None:
    store = RawStore(tmp_path / "a", kind="responses")
    store.root = tmp_path / "b"
    key = store.keep("candles", "BTC-USD", {"received_at_ns": AT, "body": "x"})
    assert (tmp_path / "b" / key).is_file()
