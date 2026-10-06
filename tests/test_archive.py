"""An edge plugin's older records move to the archive (contract v16): the
kinds in the declaration, the window settings the SDK declares per kind, the
archive, the moves with their index, what is stored on the heartbeat, and the
restore route, against the fake sidecar, which records the moves and
enforces the hold."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import grpc
import pytest

import meridian
from meridian import edge
from meridian.declaration import Declaration, RecordKind, Storage
from meridian.errors import CommandRefused, NotGranted
from meridian.testing import PageClient, caller_header
from meridian.v1 import sidecar_pb2

DAY = 86_400 * 10**9
KINDS = (
    RecordKind("activity", "Reported activity", window_days=2555, archivable=True),
    RecordKind("responses", "Raw responses", window_days=30, archivable=True),
    RecordKind("session", "Session state", window_days=7, archivable=False),
)
DECLARATION = Declaration(
    settings=(meridian.Setting("consumer_key", secret=True, required=True),),
    storage=Storage(kinds=KINDS),
)
# A month of an account's activity, received in 2019 (the fixture's).
FIRST, LAST = 1_551_398_400_000_000_000, 1_554_076_799_000_000_000
UNIT = "activity/ACC-1/2019-03"


def _settings(**values: str) -> sidecar_pb2.SettingsDelivery:
    return sidecar_pb2.SettingsDelivery(
        values=[sidecar_pb2.SettingValue(name=n, value=v) for n, v in values.items()]
    )


@pytest.fixture
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    granted = tmp_path / "storage"
    granted.mkdir()
    monkeypatch.setenv("MERIDIAN_STORAGE_DIR", str(granted))
    unit = granted / UNIT
    unit.mkdir(parents=True)
    (unit / "act-77.json").write_text('{"id": "act-77"}')
    (unit / "act-78.json").write_text('{"id": "act-78"}')
    return granted


@pytest.fixture
def archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    given = tmp_path / "archive"
    given.mkdir()
    monkeypatch.setenv("MERIDIAN_ARCHIVE_DIR", str(given))
    return given


async def _connected(service: Any, address: str, **settings: str) -> meridian.Plugin:
    """A plugin declaring the three kinds, its settings delivered once."""
    service.settings = [_settings(**settings)]
    plugin = await meridian.connect(address, heartbeat=False, declaration=DECLARATION)
    async for _ in plugin.settings():
        break
    return plugin


# ── The declaration ─────────────────────────────────────────────────────────


def test_the_kinds_go_on_the_declaration_beside_the_longest_window_as_retention() -> None:
    wire = DECLARATION.to_wire().storage
    assert wire.retention_days == 2555
    assert [(k.name, k.label, k.window_days, k.archivable) for k in wire.record_kinds] == [
        ("activity", "Reported activity", 2555, True),
        ("responses", "Raw responses", 30, True),
        ("session", "Session state", 7, False),
    ]
    assert DECLARATION.to_json()["storage"]["record_kinds"][1] == {
        "name": "responses",
        "label": "Raw responses",
        "window_days": 30,
        "archivable": True,
    }
    # No kinds: the behaviour before v16, under retention_days alone.
    alone = Declaration(storage=Storage(retention_days=30)).to_wire().storage
    assert (alone.retention_days, list(alone.record_kinds)) == (30, [])


def test_the_register_fixtures_v16_case_is_what_the_sdk_sends() -> None:
    declared = Declaration(
        settings=(
            meridian.Setting("consumer_key", secret=True),
            meridian.Setting("user_secret", secret=True),
        ),
        storage=Storage(
            retention_days=2555,
            kinds=[
                RecordKind("activity", "Reported activity", window_days=2555),
                RecordKind("responses", "Raw responses", window_days=30),
            ],
        ),
    ).to_wire()
    assert list(declared.secret_settings) == ["consumer_key", "user_secret"]
    assert declared.storage.retention_days == 2555
    assert [k.name for k in declared.storage.record_kinds] == ["activity", "responses"]


@pytest.mark.parametrize(
    ("made", "said"),
    [
        (lambda: RecordKind("Activity", "A", 1), "lowercase letters"),
        (lambda: RecordKind("1st", "A", 1), "beginning with a letter"),
        (lambda: RecordKind("a" * 41, "A", 1), "1 to 40"),
        (lambda: RecordKind("activity", "", 1), "label is 1 to 40"),
        (lambda: RecordKind("activity", "x" * 41, 1), "label is 1 to 40"),
        (lambda: RecordKind("activity", "A", 0), "window_days is 1 to 36500"),
        (lambda: RecordKind("activity", "A", 36_501), "window_days is 1 to 36500"),
        (
            lambda: Storage(kinds=[RecordKind("a", "A", 1), RecordKind("a", "B", 2)]),
            "declared twice",
        ),
        (
            lambda: Storage(kinds=[RecordKind(f"k{n}", "K", 1) for n in range(17)]),
            "at most 16",
        ),
        (lambda: Storage(), "retention_days is 1 to 36500"),
    ],
)
def test_a_kind_breaking_a_bound_is_refused_as_the_sidecar_refuses_it(
    made: Any, said: str
) -> None:
    with pytest.raises(ValueError, match=said):
        made()


def test_a_setting_named_as_a_kinds_window_is_refused_the_names_are_the_sdks() -> None:
    for name in ("activity_window_days", "responses_past_window"):
        with pytest.raises(ValueError, match=f"the setting {name} is named as"):
            Declaration(
                settings=(meridian.Setting(name, kind=int),), storage=Storage(kinds=KINDS)
            )
    # A name of the same shape for a kind not declared is the plugin's own.
    Declaration(
        settings=(meridian.Setting("statements_window_days", kind=int),),
        storage=Storage(kinds=KINDS),
    )


async def test_the_sdk_declares_two_settings_per_kind_archived_by_default_with_an_archive(
    sidecar: Any, archive: Path, storage: Path
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False, declaration=DECLARATION)
    await plugin.leave()
    (sent,) = service.registered
    by_name = {s.name: s for s in sent.settings}
    assert list(by_name) == [
        "consumer_key",
        "activity_window_days",
        "activity_past_window",
        "responses_window_days",
        "responses_past_window",
        "session_window_days",
        "session_past_window",
    ]
    window = by_name["activity_window_days"]
    assert (window.type, window.default_value, window.unit) == (
        sidecar_pb2.SETTING_TYPE_INTEGER,
        "2555",
        "days",
    )
    past = by_name["responses_past_window"]
    assert past.type == sidecar_pb2.SETTING_TYPE_CHOICE
    assert [c.value for c in past.choices] == ["archived", "kept", "deleted"]
    assert past.default_value == "archived"
    # Not archivable: the same controls, kept by default; the deployment
    # refuses archived for it at the form.
    session = by_name["session_past_window"]
    assert [c.value for c in session.choices] == ["archived", "kept", "deleted"]
    assert session.default_value == "kept"


async def test_with_no_archive_past_the_window_is_kept_by_default(
    sidecar: Any, storage: Path
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False, declaration=DECLARATION)
    await plugin.leave()
    defaults = {s.name: s.default_value for s in service.registered[0].settings}
    assert defaults["activity_past_window"] == "kept"
    assert edge.archive_dir() is None


async def test_a_plugin_naming_roles_has_its_window_settings_serve_its_edge_roles(
    sidecar: Any,
) -> None:
    service, address = sidecar
    service.roles = ("custody", "operations")
    declared = Declaration(
        settings=(
            meridian.Setting("consumer_key", secret=True, roles=["custody"]),
            meridian.Setting("desk", roles=["operations"]),
        ),
        storage=Storage(kinds=KINDS[:1]),
    )
    plugin = await meridian.connect(address, heartbeat=False, declaration=declared)
    await plugin.leave()
    roles = {s.name: list(s.roles) for s in service.registered[0].settings}
    assert roles["activity_window_days"] == ["custody"]
    assert roles["activity_past_window"] == ["custody"]


# ── The moves ───────────────────────────────────────────────────────────────


async def test_a_unit_past_its_window_is_archived_checked_recorded_then_removed(
    sidecar: Any, storage: Path, archive: Path
) -> None:
    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="archived"
    )
    try:
        await plugin.archive_unit(
            "activity", UNIT, record_count=214, first_received_ns=FIRST, last_received_ns=LAST
        )
    finally:
        await plugin.leave()
    (move, person, _) = service.moves[0]
    assert (move.record_kind, move.unit, move.record_count) == ("activity", UNIT, 214)
    assert (move.first_received_ns, move.last_received_ns) == (FIRST, LAST)
    assert move.outcome == sidecar_pb2.MOVE_OUTCOME_ARCHIVED
    assert move.rule == "activity_window_days 2555"
    assert person == ""
    # In the archive, whole; in storage no more.
    assert (archive / UNIT / "act-77.json").read_text() == '{"id": "act-77"}'
    assert not (storage / UNIT).exists()
    assert (storage / "activity" / "ACC-1").is_dir()  # the plugin's own layout stands
    # A row's record_key resolves to "archived, restorable".
    found = plugin.find_record(f"{UNIT}/act-77.json")
    assert found is not None and found.outcome == sidecar_pb2.MOVE_OUTCOME_ARCHIVED
    assert plugin.find_record("activity/ACC-1/2019-04/act-1.json") is None


async def test_the_fixtures_request_is_what_archive_unit_sends(
    sidecar: Any, storage: Path, archive: Path
) -> None:
    """fixtures/sidecar/record-move.yaml's request, as the SDK builds it:
    the pinned bytes, which conformance asserts against design's file."""
    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="archived"
    )
    try:
        await plugin.archive_unit(
            "activity", UNIT, record_count=214, first_received_ns=FIRST, last_received_ns=LAST
        )
    finally:
        await plugin.leave()
    pinned = (
        "CghhY3Rpdml0eRIWYWN0aXZpdHkvQUNDLTEvMjAxOS0wMxjWASCAgPDIgJTrwxUogOzIsNaTzMgVMAE6"
        "GWFjdGl2aXR5X3dpbmRvd19kYXlzIDI1NTU="
    )
    assert service.moves[0][0].SerializeToString() == base64.b64decode(pinned)


async def test_archived_is_refused_before_anything_moves_where_it_cannot_be(
    sidecar: Any, storage: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="kept"
    )
    args = {"record_count": 2, "first_received_ns": FIRST, "last_received_ns": LAST}
    try:
        with pytest.raises(ValueError, match="activity_past_window is 'kept'"):
            await plugin.archive_unit("activity", UNIT, **args)
        with pytest.raises(ValueError, match="not a kind of raw record"):
            await plugin.archive_unit("statements", UNIT, **args)
        with pytest.raises(ValueError, match="declared not archivable"):
            await plugin.archive_unit("session", UNIT, **args)
        with pytest.raises(ValueError, match="not a path in the plugin's storage"):
            await plugin.archive_unit("activity", "../elsewhere", **args)
        with pytest.raises(ValueError, match="not a path in the plugin's storage"):
            await plugin.archive_unit("activity", ".meridian/archive", **args)
        with pytest.raises(ValueError, match="record_count is 1 to"):
            await plugin.archive_unit("activity", UNIT, **{**args, "record_count": 0})
        with pytest.raises(ValueError, match="before first_received_ns"):
            await plugin.archive_unit("activity", UNIT, **{**args, "last_received_ns": 1})
        monkeypatch.delenv("MERIDIAN_ARCHIVE_DIR")
        with pytest.raises(RuntimeError, match="allowed no archive"):
            await plugin.archive_unit("activity", UNIT, **args)
    finally:
        await plugin.leave()
    assert service.moves == []
    assert (storage / UNIT / "act-77.json").exists()


async def test_a_move_before_the_settings_arrived_is_refused_it_names_its_window(
    sidecar: Any, storage: Path, archive: Path
) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False, declaration=DECLARATION)
    try:
        with pytest.raises(RuntimeError, match="the settings have not arrived"):
            await plugin.archive_unit(
                "activity", UNIT, record_count=2, first_received_ns=FIRST, last_received_ns=LAST
            )
    finally:
        await plugin.leave()


async def test_a_move_the_sidecar_refuses_keeps_the_unit_and_takes_the_copy_back(
    sidecar: Any, storage: Path, archive: Path
) -> None:
    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="archived"
    )
    service.registered[-1].declaration.storage.ClearField("record_kinds")
    try:
        with pytest.raises(meridian.CallFailed, match="invalid"):
            await plugin.archive_unit(
                "activity", UNIT, record_count=2, first_received_ns=FIRST, last_received_ns=LAST
            )
    finally:
        await plugin.leave()
    assert (storage / UNIT / "act-77.json").exists()
    assert list(archive.rglob("*.json")) == []
    assert plugin.find_record(UNIT) is None


async def test_a_restore_is_copied_back_for_the_person_and_its_return_follows(
    sidecar: Any, storage: Path, archive: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="archived"
    )
    ben = caller_header("write", subject="local|ben", display_name="Ben", roles=["custody"])
    try:
        await plugin.archive_unit(
            "activity", UNIT, record_count=2, first_received_ns=FIRST, last_received_ns=LAST
        )
        restored = await plugin.restore_unit("activity", UNIT, for_caller=ben)
        assert (restored / "act-78.json").read_text() == '{"id": "act-78"}'
        assert restored.is_relative_to(storage)
        assert not (storage / UNIT).exists()  # the restore area, not the unit's place
        found = plugin.find_record(f"{UNIT}/act-78.json")
        assert found is not None and found.outcome == sidecar_pb2.MOVE_OUTCOME_RESTORED
        # Asked again meanwhile: the same path, nothing reported.
        assert await plugin.restore_unit("activity", UNIT, for_caller=ben) == restored
        assert len(service.moves) == 2

        # Past the restore period: removed, its return reported as the plugin.
        later = edge._now_ns() + 8 * DAY
        monkeypatch.setattr(edge, "_now_ns", lambda: later)
        async with plugin._moves().lock:
            await plugin._moves().return_due()
        assert not restored.exists()
    finally:
        await plugin.leave()
    outcomes = [(m.outcome, m.rule, person) for m, person, _ in service.moves]
    assert outcomes == [
        (sidecar_pb2.MOVE_OUTCOME_ARCHIVED, "activity_window_days 2555", ""),
        (sidecar_pb2.MOVE_OUTCOME_RESTORED, "", ben),
        (sidecar_pb2.MOVE_OUTCOME_RETURNED, "restore period 7 days", ""),
    ]
    found = plugin.find_record(UNIT)
    assert found is not None and found.outcome == sidecar_pb2.MOVE_OUTCOME_ARCHIVED
    assert (archive / UNIT / "act-78.json").exists()


async def test_a_restore_for_nobody_is_refused_and_leaves_no_copy(
    sidecar: Any, storage: Path, archive: Path
) -> None:
    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="archived"
    )
    try:
        await plugin.archive_unit(
            "activity", UNIT, record_count=2, first_received_ns=FIRST, last_received_ns=LAST
        )
        with pytest.raises(ValueError, match="names nobody"):
            await plugin.restore_unit("activity", UNIT, for_caller="")
        with pytest.raises(ValueError, match="is not archived"):
            await plugin.restore_unit(
                "activity", "activity/ACC-1/2019-04", for_caller=caller_header("write")
            )
    finally:
        await plugin.leave()
    assert not (storage / ".meridian" / "restored").exists()


async def test_a_copy_that_comes_back_altered_is_refused(
    sidecar: Any, storage: Path, archive: Path
) -> None:
    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="archived"
    )
    try:
        await plugin.archive_unit(
            "activity", UNIT, record_count=2, first_received_ns=FIRST, last_received_ns=LAST
        )
        (archive / UNIT / "act-77.json").write_text("altered")
        with pytest.raises(OSError, match="did not come back"):
            await plugin.restore_unit("activity", UNIT, for_caller=caller_header("write"))
    finally:
        await plugin.leave()
    assert len(service.moves) == 1


async def test_a_deletion_inside_the_hold_is_refused_by_its_code_and_keeps_the_unit(
    sidecar: Any, storage: Path
) -> None:
    service, address = sidecar
    service.hold_days, service.now_ns = 2190, LAST + 30 * DAY
    plugin = await _connected(
        service, address, responses_window_days="30", responses_past_window="deleted"
    )
    unit = storage / "responses" / "ACC-1" / "2019-03.json.gz"
    unit.parent.mkdir(parents=True)
    unit.write_bytes(b"\x1f\x8b")
    try:
        with pytest.raises(CommandRefused) as refused:
            await plugin.delete_unit(
                "responses",
                "responses/ACC-1/2019-03.json.gz",
                record_count=1,
                first_received_ns=FIRST,
                last_received_ns=LAST,
            )
        assert refused.value.reason == sidecar_pb2.REFUSAL_REASON_WITHIN_HOLD
        assert unit.exists()
        assert service.moves == []

        # Past the hold, deleted: reported first, as the window's rule.
        service.now_ns = LAST + 2200 * DAY
        await plugin.delete_unit(
            "responses",
            "responses/ACC-1/2019-03.json.gz",
            record_count=1,
            first_received_ns=FIRST,
            last_received_ns=LAST,
        )
    finally:
        await plugin.leave()
    (move, person, _) = service.moves[0]
    assert (move.outcome, move.rule, person) == (
        sidecar_pb2.MOVE_OUTCOME_DELETED,
        "responses_past_window deleted",
        "",
    )
    assert not unit.exists()
    found = plugin.find_record("responses/ACC-1/2019-03.json.gz")
    assert found is not None and found.outcome == sidecar_pb2.MOVE_OUTCOME_DELETED


async def test_deleting_an_archived_unit_is_an_admins_act(
    sidecar: Any, storage: Path, archive: Path
) -> None:
    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="archived"
    )
    admin = caller_header("admin", subject="local|ada", roles=["custody"])
    try:
        await plugin.archive_unit(
            "activity", UNIT, record_count=2, first_received_ns=FIRST, last_received_ns=LAST
        )
        with pytest.raises(ValueError, match="an admin's act"):
            await plugin.delete_unit("activity", UNIT)
        await plugin.delete_unit("activity", UNIT, for_caller=admin)
    finally:
        await plugin.leave()
    (move, person, _) = service.moves[-1]
    assert (move.outcome, move.record_count, move.rule, person) == (
        sidecar_pb2.MOVE_OUTCOME_DELETED,
        2,
        "",
        admin,
    )
    assert list(archive.rglob("*.json")) == []


async def test_a_sidecar_refusing_the_person_is_not_granted(
    sidecar: Any, storage: Path, archive: Path
) -> None:
    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="archived"
    )
    try:
        await plugin.archive_unit(
            "activity", UNIT, record_count=2, first_received_ns=FIRST, last_received_ns=LAST
        )
        service.move_refused = (grpc.StatusCode.PERMISSION_DENIED, "Ben holds read on custody")
        with pytest.raises(NotGranted, match="holds read"):
            await plugin.restore_unit("activity", UNIT, for_caller=caller_header("read"))
    finally:
        await plugin.leave()
    assert not (storage / ".meridian" / "restored" / UNIT).exists()


async def test_read_moves_answers_the_moves_newest_first_and_the_archives_spans(
    sidecar: Any, storage: Path, archive: Path
) -> None:
    from meridian.v1 import config_pb2

    service, address = sidecar
    plugin = await _connected(
        service, address, activity_window_days="2555", activity_past_window="archived"
    )
    try:
        await plugin.archive_unit(
            "activity", UNIT, record_count=214, first_received_ns=FIRST, last_received_ns=LAST
        )
        await plugin.restore_unit("activity", UNIT, for_caller=caller_header("write"))
    finally:
        await plugin.leave()
    read = service.read_moves(
        config_pb2.ReadMovesRequest(plugin_instance_id="custody-snaptrade-1")
    )
    assert [m.move.outcome for m in read.moves] == [
        sidecar_pb2.MOVE_OUTCOME_RESTORED,
        sidecar_pb2.MOVE_OUTCOME_ARCHIVED,
    ]
    assert read.moves[1].person == ""
    (span,) = read.archived
    assert (span.record_kind, span.record_count, span.first_received_ns) == (
        "activity",
        214,
        FIRST,
    )


# ── What is stored, on the heartbeat ────────────────────────────────────────


async def test_what_each_kind_holds_in_storage_goes_on_every_heartbeat(sidecar: Any) -> None:
    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False, declaration=DECLARATION)
    try:
        plugin.stored = [
            meridian.StoredSpan(
                record_kind="activity",
                record_count=48210,
                first_received_ns=1554076800000000000,
                last_received_ns=1790380500000000000,
            ),
            meridian.StoredSpan(record_kind="responses", record_count=0),
        ]
        await plugin.report(healthy=True)
        with pytest.raises(ValueError, match=r"stored\[0\]\.record_kind 'statements'"):
            plugin.stored = [meridian.StoredSpan(record_kind="statements", record_count=3)]
        with pytest.raises(ValueError, match="holds no record, and so no span"):
            plugin.stored = [meridian.StoredSpan(record_kind="activity", last_received_ns=1)]
        with pytest.raises(ValueError, match="names activity twice"):
            plugin.stored = [
                meridian.StoredSpan(record_kind="activity"),
                meridian.StoredSpan(record_kind="activity"),
            ]
    finally:
        await plugin.leave()
    stored = service.heartbeats[-1].stored
    assert [(s.record_kind, s.record_count) for s in stored] == [
        ("activity", 48210),
        ("responses", 0),
    ]
    assert len(plugin.stored) == 2  # what was refused left the last standing


# ── The restore route ───────────────────────────────────────────────────────


class _Restoring:
    """A stand-in for the plugin a view reaches: what it was asked."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, str, str]] = []

    async def restore_unit(self, record_kind: str, unit: str, *, for_caller: Any) -> Path:
        if record_kind != "activity":
            raise ValueError(
                f"{record_kind!r} is not a kind of raw record this version declares"
            )
        self.asked.append((record_kind, unit, for_caller.subject))
        return Path("/restored") / unit


def _restorable_pages() -> meridian.Pages:
    pages = meridian.Pages("Raw records")

    @pages.page("/", "Raw records", levels=["write", "read"])
    async def home(request: meridian.Request) -> str:
        return "<p>archived units</p>"

    edge._restore_route(pages, ())
    return pages


def test_every_edge_plugin_with_pages_offers_the_restore_route_as_a_tool() -> None:
    pages = _restorable_pages()
    (tool,) = [t for t in pages.tools if t.path == "/archive/restore"]
    assert (tool.name, tool.method, tool.reads) == ("restore_unit", "POST", False)
    assert tool.levels == (sidecar_pb2.ACCESS_LEVEL_WRITE,)
    schema = json.loads(tool.declared().input_schema)
    assert schema["required"] == ["record_kind", "unit"]
    edge._restore_route(pages, ())  # declared once
    assert len([t for t in pages.tools if t.path == "/archive/restore"]) == 1


def test_the_restore_tool_restores_for_the_person_from_the_claims() -> None:
    plugin = _Restoring()
    client = PageClient(_restorable_pages(), plugin, subject="local|ben")
    answer = client.call_tool("restore_unit", {"record_kind": "activity", "unit": UNIT})
    assert answer.status == 200 and answer.outcome == "made"
    assert answer.data == {"record_kind": "activity", "unit": UNIT, "outcome": "restored"}
    assert plugin.asked == [("activity", UNIT, "local|ben")]
    refused = client.call_tool("restore_unit", {"record_kind": "statements", "unit": UNIT})
    assert refused.status == 422 and refused.paths == ["record_kind"]
    # Not at read: refused before the view.
    assert (
        client.call_tool(
            "restore_unit", {"record_kind": "activity", "unit": UNIT}, level="read"
        ).status
        == 403
    )


def test_a_browsers_restore_answers_back_to_the_page_it_came_from() -> None:
    plugin = _Restoring()
    client = PageClient(_restorable_pages(), plugin)
    answer = client.post(
        "/archive/restore",
        "write",
        {"record_kind": "activity", "unit": UNIT},
        headers={"Referer": "https://custody.example/raw?x=1"},
    )
    assert answer.status == 303
    assert dict(answer.headers)["location"] == "/raw"


async def test_connect_declares_the_restore_route_for_a_plugin_declaring_kinds(
    sidecar: Any,
) -> None:
    service, address = sidecar
    pages = meridian.Pages("Raw records")

    @pages.page("/", "Raw records", levels=["write"])
    async def home(request: meridian.Request) -> str:
        return ""

    plugin = await meridian.connect(
        address,
        heartbeat=False,
        declaration=DECLARATION,
        interface=meridian.Interface(port=8000, title="Raw", pages=pages),
    )
    await plugin.leave()
    assert "restore_unit" in [t.name for t in service.registered[0].tools]


# ── The archive's two backends ──────────────────────────────────────────────


class _FakeS3:
    """What boto3's client answers, for the bucket backend's shape."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ChecksumAlgorithm: str) -> None:  # noqa: N803
        assert (Bucket, ChecksumAlgorithm) == ("archive-custody-1", "SHA256")
        self.objects[Key] = Body

    def head_object(self, *, Bucket: str, Key: str, ChecksumMode: str) -> dict[str, Any]:  # noqa: N803
        data = self.objects[Key]
        digest = base64.b64encode(hashlib.sha256(data).digest()).decode()
        return {"ContentLength": len(data), "ChecksumSHA256": digest}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803
        import io

        return {"Body": io.BytesIO(self.objects[Key])}

    def list_objects_v2(self, *, Bucket: str, Prefix: str, **_: Any) -> dict[str, Any]:  # noqa: N803
        return {"Contents": [{"Key": k} for k in sorted(self.objects) if k.startswith(Prefix)]}

    def delete_object(self, *, Bucket: str, Key: str) -> None:  # noqa: N803
        self.objects.pop(Key, None)


@pytest.mark.parametrize("backend", ["directory", "bucket"])
def test_both_backends_put_get_list_by_prefix_and_delete(backend: str, tmp_path: Path) -> None:
    store: Any = (
        edge._Directory(tmp_path)
        if backend == "directory"
        else edge._Bucket("s3://archive-custody-1/instance", client=_FakeS3())
    )
    store.put("activity/ACC-1/2019-03/a.json", b"a")
    store.put("activity/ACC-1/2019-04/b.json", b"bb")
    assert store.get("activity/ACC-1/2019-03/a.json") == b"a"
    assert store.list("activity/ACC-1/2019-0") == [
        "activity/ACC-1/2019-03/a.json",
        "activity/ACC-1/2019-04/b.json",
    ]
    assert store.landed("activity/ACC-1/2019-04/b.json") == (
        2,
        hashlib.sha256(b"bb").hexdigest(),
    )
    store.delete("activity/ACC-1/2019-03/a.json")
    assert store.list("activity/") == ["activity/ACC-1/2019-04/b.json"]


def test_a_bucket_of_another_kind_is_refused_naming_it() -> None:
    with pytest.raises(ValueError, match="s3:// bucket, and no other"):
        edge._Bucket("gs://archive", client=object())
