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
import contextlib
import errno
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import _raw, edge
from meridian.declaration import Declaration, RecordKind, Storage
from meridian.edge import RawStore, storage_root
from meridian.errors import CallFailed
from meridian.plugin.v1 import operations_pb2_grpc
from meridian.suites import Recorder
from meridian.testing import caller_header
from meridian.v1 import sidecar_pb2, sidecar_pb2_grpc

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


#: Another pod's try for the line file's lock, not waiting: "refused" or "taken".
_TRY_LOCK = """
import fcntl, os, sys
fd = os.open(sys.argv[1], os.O_RDWR)
try:
    fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    print("refused")
else:
    print("taken")
"""


@pytest.mark.parametrize("left", ["a whole line", "an unfinished line"])
def test_the_line_files_lock_is_held_from_its_count_to_its_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, left: str
) -> None:
    """Counting another pod's lines never lets the lock go: POSIX record
    locks are the process's, and closing any descriptor on the file drops
    them, so the line written after the count would be named unlocked."""
    store = RawStore(tmp_path, kind="responses")
    path = tmp_path / "responses/2026-11-17/ticker/BTC-USD.jsonl"
    path.parent.mkdir(parents=True)
    line = json.dumps({"received_at_ns": AT, "body": "a"})
    path.write_text(line + "\n" if left == "a whole line" else line[:9])
    tried: list[str] = []
    count = RawStore._count

    def counted(self: RawStore, key: str, out: Any) -> int:
        lines = count(self, key, out)
        another = subprocess.run(
            [sys.executable, "-c", _TRY_LOCK, str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        tried.append(another.stdout.strip())
        return lines

    monkeypatch.setattr(RawStore, "_count", counted)
    record = {"received_at_ns": AT + 1, "body": "b"}
    key = store.keep_line("ticker", "BTC-USD", record)
    assert tried == ["refused"]
    assert key.endswith("#1") and store.get(key) == record


async def test_m2_an_unreadable_index_of_another_shard_refuses_the_archive(
    sidecar: Any, root: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bound is the instance's: another shard's index that cannot be
    read is never counted as an empty archive, so nothing is archived past
    the bound unseen."""
    service, address = sidecar
    _unit_in(root / "shard-1", "x" * 100)
    index = root.joinpath("shard-0", *edge._INDEX.parts)
    index.parent.mkdir(parents=True)
    index.write_text('{"units": {"activity/ACC-1/2019-0')
    monkeypatch.setenv("MERIDIAN_ARCHIVE_MOST_BYTES", str(1 << 30))
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        with pytest.raises(RuntimeError, match="shard 0's archive index could not be read"):
            await _archived(plugin)
    finally:
        await plugin.leave()
    assert (root / "shard-1" / UNIT).exists()
    assert not any(archive.rglob("*.json"))


def _two_holders(tmp_path: Path, *runs: list[str]) -> list[list[str]]:
    """Two pods holding one shard at once (PO item 79), each its own process
    and its own sidecar, on the one storage: started together, released at
    once, and what each printed."""
    go = tmp_path / "go"
    helper = Path(__file__).with_name("_two_holders.py")
    pods = [
        subprocess.Popen(
            [sys.executable, str(helper), run[0], str(go), *run[1:]],
            cwd=helper.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for run in runs
    ]
    # Each registers and says so before it waits; once both have, the file
    # lets them go together.
    ends = time.monotonic() + 60
    try:
        while len(list(tmp_path.glob(f"{go.name}.ready-*"))) < len(pods):
            assert all(pod.poll() is None for pod in pods), "a pod ended before it was ready"
            assert time.monotonic() < ends, "the pods were not ready within 60 s"
            time.sleep(0.01)
    except AssertionError:
        for pod in pods:
            pod.kill()
        raise
    go.touch()
    printed = []
    for pod in pods:
        out, err = pod.communicate(timeout=120)
        assert pod.returncode == 0, err
        printed.append(json.loads(out.strip().splitlines()[-1]))
    return printed


def test_two_holders_of_one_shard_name_every_line_once(tmp_path: Path, root: Path) -> None:
    """A deposed holder and the new one writing one live file at once each
    name their own lines: under the file's lock no #line is given twice, and
    every key names the line it was given for."""
    deposed, new = _two_holders(tmp_path, ["lines", "deposed", "300"], ["lines", "new", "300"])
    keys = deposed + new
    assert len(set(keys)) == 600, "a #line was given twice"
    store = RawStore(root / "shard-0", kind="responses")
    for who, given in (("deposed", deposed), ("new", new)):
        for n, key in enumerate(given):
            assert key.startswith("shard-0/responses/")
            line = store.get(key.removeprefix("shard-0/"))
            assert line is not None and line["body"] == f"{who} {n}", key
    (path,) = (root / "shard-0" / "responses").rglob("*.jsonl")
    assert len(path.read_text().splitlines()) == 600


def test_two_holders_of_one_shard_keep_the_index_whole(
    tmp_path: Path, root: Path, archive: Path
) -> None:
    """A deposed holder and the new one archiving at once: the shard's index
    is read, added to and written under a lock both hold in turn, so it
    stays whole and records every unit either moved; none leaves storage
    unrecorded."""
    units = {
        who: [f"activity/ACC-{who}/2019-{month:02d}" for month in range(1, 13)]
        for who in ("A", "B")
    }
    for given in units.values():
        for unit in given:
            folder = root / "shard-0" / unit
            folder.mkdir(parents=True)
            (folder / "act.json").write_text(json.dumps({"unit": unit}))
    _two_holders(tmp_path, ["archive", *units["A"]], ["archive", *units["B"]])
    index = json.loads(root.joinpath("shard-0", *edge._INDEX.parts).read_text())
    every = units["A"] + units["B"]
    assert sorted(index["units"]) == sorted(every), "a move was lost from the index"
    assert all(index["units"][unit]["state"] == "archived" for unit in every)
    assert not any((root / "shard-0" / unit).exists() for unit in every)


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


# ── sdk56-review: the locks bounded, held by their descriptor, read fresh ───

#: Another pod holding a file's lock (lockf) for argv[2] seconds, then gone:
#: "held" once it holds it.
_HOLD = """
import fcntl, os, sys, time
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o644)
fcntl.lockf(fd, fcntl.LOCK_EX)
print("held", flush=True)
time.sleep(float(sys.argv[2]))
"""

_OFD = pytest.mark.skipif(
    not hasattr(fcntl, "F_OFD_SETLK"), reason="open-file-description locks are Linux's"
)


@contextlib.contextmanager
def _held_by_another_pod(path: Path, seconds: float) -> Iterator[None]:
    """`path` locked by another process for `seconds` at most: a holder that
    does not let go meanwhile, as a deposed pod stuck in a move does."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pod = subprocess.Popen(
        [sys.executable, "-c", _HOLD, str(path), str(seconds)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert pod.stdout is not None and pod.stdout.readline().strip() == "held"
        yield
    finally:
        pod.kill()
        pod.wait()


def _cached_as_missing(index: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """This pod's client holds `index` cached as missing (H1), as an NFS
    client does for a file another client made since it looked, until its
    directory's attributes time out: every lookup by name says it is not
    there, and only an open that may create it goes to the server."""
    real_open = os.open

    def opened(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if Path(path) == index and not flags & os.O_CREAT:
            raise FileNotFoundError(errno.ENOENT, "cached as missing", str(path))
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", opened)
    for name in ("stat", "open", "read_text", "read_bytes"):
        real = getattr(Path, name)

        def missing(self: Path, *args: Any, _real: Any = real, **kwargs: Any) -> Any:
            if self == index:
                raise FileNotFoundError(errno.ENOENT, "cached as missing", str(self))
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(Path, name, missing)


def _units_in(folder: Path, *units: str) -> None:
    for unit in units:
        (folder / unit).mkdir(parents=True)
        (folder / unit / "act.json").write_text(json.dumps({"unit": unit}))


async def test_h1_an_index_cached_as_missing_never_loses_a_move(
    sidecar: Any, root: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shard's index, written by another pod since this pod's client
    found none there, is read under the lock all the same: opened as a
    create, which goes to the server, never looked up first; so the move
    the other recorded stays in it."""
    service, address = sidecar
    units = ["activity/ACC-1/2019-03", "activity/ACC-1/2019-04"]
    _units_in(root / "shard-0", *units)
    index = root.joinpath("shard-0", *edge._INDEX.parts)
    plugin = await _pod(service, address, shard=0, shards=2)
    try:
        for n, unit in enumerate(units):
            with monkeypatch.context() as stale:
                if n:
                    _cached_as_missing(index, stale)
                await plugin.archive_unit(
                    "activity",
                    unit,
                    record_count=1,
                    first_received_ns=FIRST,
                    last_received_ns=LAST,
                )
    finally:
        await plugin.leave()
    assert sorted(json.loads(index.read_text())["units"]) == units, "a move was lost"


async def test_m1_a_holder_that_never_lets_go_never_stops_the_heartbeat(
    sidecar: Any, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Restored units are returned beside the heartbeat, only where the
    index is free: another pod holding it, however long, never holds up a
    beat."""
    service, address = sidecar
    monkeypatch.setattr(meridian.client, "HEARTBEAT_SECONDS", 0.05)
    service.shard, service.shards = 0, 2
    with _held_by_another_pod(root.joinpath("shard-0", *edge._INDEX_LOCK.parts), 30):
        plugin = await meridian.connect(address, declaration=DECLARATION, roles=[])
        try:
            await service.beats_from(service.mark(), count=10)
        finally:
            await plugin.leave()


async def test_m1_a_move_waits_for_the_index_at_most_its_bound(
    sidecar: Any, root: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    _unit_in(root / "shard-0", "waited")
    monkeypatch.setattr(edge, "_MOVE_WAIT_SECONDS", 0.3, raising=False)
    plugin = await _pod(service, address, shard=0, shards=2)
    try:
        with _held_by_another_pod(root.joinpath("shard-0", *edge._INDEX_LOCK.parts), 5):
            began = time.monotonic()
            with pytest.raises(TimeoutError, match="held by another move"):
                await _archived(plugin)
            assert time.monotonic() - began < 3
    finally:
        await plugin.leave()
    assert (root / "shard-0" / UNIT).exists() and not service.moves


class _Stalled(FakeSidecar):
    """A sidecar that takes `stall` seconds to record a move."""

    stall = 3.0

    async def RecordMove(self, request: Any, context: Any) -> Any:  # noqa: N802
        await asyncio.sleep(self.stall)
        return await super().RecordMove(request, context)


async def test_m1_the_sidecar_is_given_a_deadline_to_record_a_move(
    root: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lock is held while the move is recorded, so RecordMove has a
    deadline: past it the move is not recorded, and the unit stays."""
    monkeypatch.setattr(edge, "_RECORD_MOVE_SECONDS", 0.3, raising=False)
    _unit_in(root / "shard-0", "slow")
    service = _Stalled()
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(service.operations, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        plugin = await _pod(service, f"127.0.0.1:{port}", shard=0, shards=2)
        try:
            began = time.monotonic()
            with pytest.raises(CallFailed):
                await _archived(plugin)
            assert time.monotonic() - began < 2.5
        finally:
            await plugin.leave()
    finally:
        await server.stop(grace=None)
    assert (root / "shard-0" / UNIT).exists()
    assert not any(archive.rglob("*.json"))


def test_m1_a_line_waits_for_another_pods_lock_at_most_its_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`keep_line` runs on the loop: another pod's lock on the live file is
    waited for at most its bound, then the line is refused."""
    monkeypatch.setattr(_raw, "_LINE_WAIT_SECONDS", 0.3, raising=False)
    store = RawStore(tmp_path, kind="responses")
    path = tmp_path / "responses/2026-11-17/ticker/BTC-USD.jsonl"
    record = {"received_at_ns": AT, "body": "a"}
    with _held_by_another_pod(path, 5):
        began = time.monotonic()
        with pytest.raises(TimeoutError, match="locked by another pod"):
            store.keep_line("ticker", "BTC-USD", record)
        assert time.monotonic() - began < 3
    assert store.keep_line("ticker", "BTC-USD", record).endswith("#0")


@_OFD
def test_m2_a_read_on_another_thread_never_drops_the_line_files_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The live file's lock is its descriptor's: a worker thread opening and
    closing the day's file between the count and the write -- an archive's
    copy, a plugin's `get` -- never lets it go."""
    store = RawStore(tmp_path, kind="responses")
    path = tmp_path / "responses/2026-11-17/ticker/BTC-USD.jsonl"
    tried: list[str] = []
    count = RawStore._count

    def counted(self: RawStore, key: str, out: Any) -> int:
        lines = count(self, key, out)
        reader = threading.Thread(target=path.read_bytes)
        reader.start()
        reader.join()
        another = subprocess.run(
            [sys.executable, "-c", _TRY_LOCK, str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        tried.append(another.stdout.strip())
        return lines

    monkeypatch.setattr(RawStore, "_count", counted)
    store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT, "body": "a"})
    assert tried == ["refused"]


@_OFD
async def test_m2_two_movers_in_one_process_take_the_index_in_turn(tmp_path: Path) -> None:
    """Two holders of the index's lock in one process -- a plugin left and
    its untracked move still running, beside the next -- conflict as two
    pods do."""
    first, second = edge._Moves(), edge._Moves()
    async with first.held(tmp_path):
        with pytest.raises(TimeoutError):
            async with second.held(tmp_path, within=0.2):
                pass
    async with second.held(tmp_path, within=0.2):
        pass


async def test_m2_one_plugin_per_process_keeps_raw_records(sidecar: Any, root: Path) -> None:
    service, address = sidecar
    first = await _pod(service, address, shard=0, shards=2)
    try:
        with pytest.raises(RuntimeError, match="one Plugin per process"):
            await meridian.connect(address, heartbeat=False, declaration=DECLARATION, roles=[])
        assert len(service.registered) == 1, "refused before anything is sent"
    finally:
        await first.leave()
    second = await _pod(service, address, shard=0, shards=2)
    await second.leave()


async def test_m2_a_move_from_another_threads_loop_is_refused(
    sidecar: Any, root: Path, archive: Path
) -> None:
    service, address = sidecar
    ben = caller_header("write", subject="local|ben", display_name="Ben", roles=["custody"])
    _unit_in(root / "shard-0", "x")
    plugin = await _pod(service, address, shard=0, shards=2)
    try:
        await _archived(plugin)
        answered: list[BaseException | None] = []

        def elsewhere() -> None:
            try:
                asyncio.run(plugin.restore_unit("activity", UNIT, for_caller=ben))
                answered.append(None)
            except BaseException as raised:  # noqa: BLE001
                answered.append(raised)

        thread = threading.Thread(target=elsewhere, daemon=True)
        thread.start()
        await asyncio.to_thread(thread.join, 10)
        assert len(answered) == 1 and isinstance(answered[0], RuntimeError), answered
        assert "the loop it registered on" in str(answered[0])
    finally:
        await plugin.leave()


@_OFD
def test_a_storage_refusing_descriptor_locks_is_locked_by_lockf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = fcntl.fcntl

    def refusing(fd: int, cmd: int, arg: Any = 0) -> Any:
        if cmd == fcntl.F_OFD_SETLK:
            raise OSError(errno.EINVAL, "not on this storage")
        return real(fd, cmd, arg)

    monkeypatch.setattr(fcntl, "fcntl", refusing)
    monkeypatch.setattr(_raw, "_OFD_SETLK", fcntl.F_OFD_SETLK)
    store = RawStore(tmp_path, kind="responses")
    key = store.keep_line("ticker", "BTC-USD", {"received_at_ns": AT, "body": "a"})
    assert key.endswith("#0") and _raw._OFD_SETLK is None


async def test_l2_another_shards_index_from_a_newer_sdk_is_counted(
    sidecar: Any, root: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In a rolling upgrade another shard's index may hold a field this SDK
    does not know: its bytes are counted all the same, and the archive goes
    on."""
    service, address = sidecar
    _unit_in(root / "shard-1", "x")
    other = root.joinpath("shard-0", *edge._INDEX.parts)
    other.parent.mkdir(parents=True)
    entry = {
        "record_kind": "activity",
        "unit": "activity/ACC-9/2019-01",
        "record_count": 1,
        "first_received_ns": FIRST,
        "last_received_ns": LAST,
        "state": "archived",
        "files": {"f.json": [10, "0" * 64]},
        "added_later": "by a newer SDK",
    }
    other.write_text(json.dumps({"units": {entry["unit"]: entry}}))
    monkeypatch.setenv("MERIDIAN_ARCHIVE_MOST_BYTES", str(1 << 30))
    plugin = await _pod(service, address, shard=1, shards=2)
    try:
        await _archived(plugin)
    finally:
        await plugin.leave()
    assert not (root / "shard-1" / UNIT).exists()


async def test_l4_a_cancelled_move_lets_go_of_the_index_only_once_its_copy_ends(
    sidecar: Any, root: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A move cancelled while its copy runs on a worker thread holds the
    index's lock until the thread ends, so another pod's move never runs
    beside a copy still writing."""
    service, address = sidecar
    _unit_in(root / "shard-0", "x")
    started, copied = threading.Event(), threading.Event()
    copy_out = edge._copy_out

    def slow(*args: Any) -> Any:
        started.set()
        time.sleep(0.5)
        try:
            return copy_out(*args)
        finally:
            copied.set()

    monkeypatch.setattr(edge, "_copy_out", slow)
    plugin = await _pod(service, address, shard=0, shards=2)
    try:
        moving = asyncio.ensure_future(_archived(plugin))
        assert await asyncio.to_thread(started.wait, 10)
        moving.cancel()
        with pytest.raises(asyncio.CancelledError):
            await moving
        assert copied.is_set(), "the lock was let go while the copy still wrote"
    finally:
        await plugin.leave()
    assert (root / "shard-0" / UNIT).exists() and not service.moves


async def test_l4_a_lock_not_let_go_cleanly_does_not_fail_a_move_done(
    sidecar: Any, root: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    _unit_in(root / "shard-0", "x")

    def failing(fd: int) -> None:
        raise OSError(errno.EIO, "the storage did not answer")

    monkeypatch.setattr(edge, "_unlock", failing)
    plugin = await _pod(service, address, shard=0, shards=2)
    try:
        await _archived(plugin)
    finally:
        await plugin.leave()
    index = json.loads(root.joinpath("shard-0", *edge._INDEX.parts).read_text())
    assert list(index["units"]) == [UNIT] and len(service.moves) == 1
