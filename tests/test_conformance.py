"""This SDK and the Rust runtime answer to the same bytes.

A fixture pins field values, which shows two implementations agree about the
shape of a message. It does not show they agree on the wire, and field agreement
with byte divergence is the failure this project has already paid for twice:
once when one side spelled a lifecycle state the way its database column did,
once when the two sides invented different audiences for a signed assertion.
Both suites passed throughout, because each asserted against its own constant.

So the assertion here is against the pin, never against meridian-core. Neither
implementation becomes the authority by being written first.

It also catches the drift that packaging makes possible. This SDK pins a schema
revision; the design repo's pins are generated from whatever revision it reads.
If those diverge, a plugin is building against types the contract no longer
describes, and the first symptom would otherwise be a decode failure inside a
customer's deployment.

A fixture writes a number as a person reads one, `quantity: "12.5"`
(decisions/023). It is put on the wire here by this SDK's own conversion, the
one every typed operation uses, so the pin checks that conversion too: a
scale this SDK chose differently from the contract's fixture tooling would
be bytes that do not match.
"""

from __future__ import annotations

import base64
import importlib
import os
import pathlib
import pkgutil
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
import yaml
from google.protobuf import descriptor_pool, json_format, message_factory

import meridian.v1
from meridian import Figure
from meridian.operations import _decimal
from meridian.testing import heartbeat

# Importing a generated module registers its messages in the default
# descriptor pool, which is how a type named in a fixture is found by name.
# Every module found, rather than a list: a list was edited by hand each time
# core added a proto file, and a file it missed read as a contract whose
# messages did not exist (W8's did, on 2026-09-25).
for _module in pkgutil.iter_modules(meridian.v1.__path__):
    if _module.name.endswith("_pb2"):
        importlib.import_module(f"meridian.v1.{_module.name}")

SECTIONS = ("request", "reply", "event")

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

# The domain's Decimal and its plugin-facing mirror, which are one shape.
DECIMALS = {"meridian.v1.Decimal", "meridian.plugin.v1.Decimal"}


def on_the_wire(descriptor: Any, fields: Any, where: str) -> Any:
    """The fixture's fields with every Decimal in them as the wire carries it,
    found by the schema wherever it sits: inside a Money, inside a position."""
    if not isinstance(fields, dict):
        return fields
    out = {}
    for key, value in fields.items():
        field = descriptor.fields_by_name.get(key)
        target = field.message_type if field is not None else None
        if target is None or target.GetOptions().map_entry:
            out[key] = value
        elif isinstance(value, list):
            out[key] = [one(target, item, f"{where}.{key}") for item in value]
        else:
            out[key] = one(target, value, f"{where}.{key}")
    return out


def one(descriptor: Any, value: Any, where: str) -> Any:
    if descriptor.full_name not in DECIMALS:
        return on_the_wire(descriptor, value, where)
    assert isinstance(value, str), f"{where} is written {value!r}, not as a quoted decimal"
    wire = _decimal(Decimal(value), where)
    return {"high": str(wire.high), "low": str(wire.low), "scale": wire.scale}


def fixtures_root() -> pathlib.Path:
    """Where the contract's fixtures are.

    Not vendored and not optional. A conformance suite that skips itself when it
    cannot find what it checks against is indistinguishable from one that
    passes, which is the whole failure mode this file exists to catch.
    """
    raw = os.environ.get("MERIDIAN_FIXTURES")
    if not raw:
        raise RuntimeError(
            "MERIDIAN_FIXTURES is not set. These tests check this SDK against the "
            "contract's pinned bytes, which live in meridian-design; run them with "
            "`make conformance`."
        )
    root = pathlib.Path(raw)
    if not root.is_dir():
        raise RuntimeError(f"MERIDIAN_FIXTURES points at {root}, which is not a directory")
    return root


def pinned_messages() -> list[tuple[str, str, str, dict]]:
    """Every (fixture, section, proto type, declared fields) that carries a pin."""
    found: list[tuple[str, str, str, dict]] = []
    for path in sorted(fixtures_root().rglob("*.yaml")):
        fixture = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        pins = fixture.get("expected_proto_bytes_b64") or {}
        for section in SECTIONS:
            body = fixture.get(section)
            if not isinstance(body, dict) or "proto_type" not in body:
                continue
            if section not in pins:
                continue
            found.append((path.name, section, body["proto_type"], body))
    return found


def case_ids(case: tuple[str, str, str, dict]) -> str:
    return f"{case[0]}:{case[1]}"


@pytest.mark.parametrize("case", pinned_messages(), ids=case_ids)
def test_the_pinned_bytes_decode_and_re_encode_identically(
    case: tuple[str, str, str, dict],
) -> None:
    name, section, type_name, body = case
    fixture = yaml.safe_load((fixtures_root() / _find(name)).read_text(encoding="utf-8"))
    pin = base64.b64decode(fixture["expected_proto_bytes_b64"][section])

    pool = descriptor_pool.Default()
    # Raises when this SDK's schema revision has no such message, which is the
    # drift worth catching: the contract describes something the plugin cannot
    # build.
    klass = message_factory.GetMessageClass(pool.FindMessageTypeByName(type_name))

    decoded = klass()
    decoded.ParseFromString(pin)

    # Round-trip, so a field this SDK cannot represent shows up as bytes that
    # do not come back rather than as a value silently dropped.
    assert decoded.SerializeToString(deterministic=True) == pin

    # And the decoded message carries what the fixture says it carries, so a pin
    # that is self-consistent but wrong is still caught.
    expected = klass()
    json_format.ParseDict(
        on_the_wire(klass.DESCRIPTOR, body.get("fields") or {}, "fields"), expected
    )
    assert decoded == expected


def _find(name: str) -> pathlib.Path:
    (match,) = (p for p in fixtures_root().rglob(name))
    return match.relative_to(fixtures_root())


def test_there_are_pins_to_check() -> None:
    """A suite that found nothing is a suite that proves nothing.

    Without this, moving or renaming the fixtures directory turns every check
    above into zero collected tests and a green run.
    """
    assert len(pinned_messages()) >= 30


def test_the_heartbeats_figures_built_with_the_sdk_are_the_pinned_bytes() -> None:
    """A plugin's figures, given as meridian.Figure and put on the wire by the
    SDK's own conversion, are the bytes the heartbeat fixture pins: each kind
    of value, an as-of, a state and a why (W4.5)."""
    fixture = yaml.safe_load(
        (fixtures_root() / _find("heartbeat.yaml")).read_text(encoding="utf-8")
    )
    fields = fixture["request"]["fields"]
    assert {key for f in fields["figures"] for key in f} >= {
        "count",
        "decimal",
        "text",
        "at_ns",
        "as_of_ns",
        "state",
        "why",
    }

    def moment(ns: str | int) -> datetime:
        assert int(ns) % 1000 == 0, f"{ns} is finer than a datetime holds"
        return EPOCH + timedelta(microseconds=int(ns) // 1000)

    def figure(given: dict[str, Any]) -> Figure:
        if "count" in given:
            value: Any = int(given["count"])
        elif "decimal" in given:
            value = Decimal(given["decimal"])
        elif "text" in given:
            value = given["text"]
        else:
            value = moment(given["at_ns"])
        return Figure(
            given["label"],
            value,
            as_of=moment(given["as_of_ns"]) if "as_of_ns" in given else None,
            state=given.get("state"),
            why=given.get("why"),
        )

    built = heartbeat(
        healthy=fields["healthy"],
        detail=fields["detail"],
        figures=[figure(given) for given in fields["figures"]],
        not_carried_seen={
            (seen["scheme"], seen["name"]): int(seen["count"])
            for seen in fields.get("not_carried_seen", [])
        },
    )
    pin = base64.b64decode(fixture["expected_proto_bytes_b64"]["request"])
    assert built.SerializeToString(deterministic=True) == pin


async def test_a_filing_and_a_read_made_with_the_sdk_are_the_pinned_bytes(sidecar) -> None:
    """A ticket filed for a person through `plugin.file_ticket`, and what it
    filed read back through `plugin.filed_tickets`, reach the sidecar as the
    bytes the two fixtures pin (W4.12, contract v13), each with the person's
    assertion as the call's `meridian-caller` metadata."""
    import meridian
    from meridian.testing import caller_header

    def pinned(name: str) -> tuple[dict[str, Any], bytes]:
        fixture = yaml.safe_load((fixtures_root() / _find(name)).read_text(encoding="utf-8"))
        return (
            fixture["request"]["fields"],
            base64.b64decode(fixture["expected_proto_bytes_b64"]["request"]),
        )

    filed, filed_pin = pinned("file-ticket-for-person.yaml")
    read, read_pin = pinned("filed-tickets.yaml")
    ben = caller_header("read", read={"ACC-GROWTH"}, subject="local|ben")

    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        await plugin.file_ticket(
            title=filed["title"],
            seen=filed["seen"],
            kind=filed["kind"],
            concerns=filed["concerns"]["kind"],
            step=filed["step"],
            operation=filed["operation"],
            references=[meridian.TicketReference(**given) for given in filed["references"]],
            idempotency_key=filed["idempotency_key"],
            for_caller=ben,
        )
        await plugin.filed_tickets(for_caller=ben, idempotency_keys=read["idempotency_keys"])
    finally:
        await plugin.leave()

    ((sent, filed_for),) = service.filings
    ((asked, read_for),) = service.filed_reads
    assert sent.SerializeToString(deterministic=True) == filed_pin
    assert asked.SerializeToString(deterministic=True) == read_pin
    assert filed_for == read_for == ben


async def test_activity_and_its_reads_made_with_the_sdk_are_the_pinned_bytes(sidecar) -> None:
    """An activity reported through `plugin.record_activity`, its numbers put
    on the wire by the SDK's own conversion, is the request the
    record-activity fixture pins once the sidecar stamps its account from the
    link; the reads of activity and of sync statuses are their fixtures'
    requests as sent (W2.10, W2.11, W2.14, contract v14)."""
    import meridian
    from meridian.plugin.v1 import operations_pb2 as ops
    from meridian.v1 import holdings_pb2

    def pinned(name: str, section: str = "request") -> tuple[dict[str, Any], bytes]:
        fixture = yaml.safe_load((fixtures_root() / _find(name)).read_text(encoding="utf-8"))
        return (
            fixture[section]["fields"],
            base64.b64decode(fixture["expected_proto_bytes_b64"][section]),
        )

    recorded, recorded_pin = pinned("record-activity.yaml")
    listed, listed_pin = pinned("list-activities.yaml")
    statuses, statuses_pin = pinned("list-sync-statuses.yaml")
    given = recorded["activity"]

    service, address = sidecar
    service.operations.links[recorded["external_account_id"]] = recorded["account_id"]
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        await plugin.record_activity(
            external_account_id=recorded["external_account_id"],
            source=recorded["source"],
            activity=meridian.CustodialActivity(
                external_activity_id=given["external_activity_id"],
                kind=given["kind"],
                instrument_id=given["instrument_id"],
                trade_date=given["trade_date"],
                settlement_date=given["settlement_date"],
                units=Decimal(given["units"]),
                price=meridian.Money(Decimal(given["price"]["amount"]), "USD"),
                amount=meridian.Money(Decimal(given["amount"]["amount"]), "USD"),
                description=given["description"],
                raw_record=meridian.RawRecordRef(**given["raw_record"]),
            ),
        )
        await plugin.list_activities(
            account_id=listed["account_id"],
            trade_date_from=listed["trade_date_from"],
            trade_date_to=listed["trade_date_to"],
            page_size=listed["page_size"],
            cursor=listed["cursor"],
        )
        await plugin.list_sync_statuses(
            account_id=statuses["account_id"],
            page_size=statuses["page_size"],
            cursor=statuses["cursor"],
        )
    finally:
        await plugin.leave()

    sent, read_activity, read_statuses = (
        service.operations.sent[0],
        *service.operations.reads,
    )
    # The sidecar's half: the account the link names (stamped.tsv).
    stamped = holdings_pb2.RecordActivityRequest.FromString(sent.SerializeToString())
    stamped.account_id = recorded["account_id"]
    assert stamped.SerializeToString(deterministic=True) == recorded_pin
    assert read_activity.SerializeToString(deterministic=True) == listed_pin
    assert read_statuses.SerializeToString(deterministic=True) == statuses_pin

    # And what the street answers reads back whole as the SDK's results.
    for name, result in (
        ("list-activities.yaml", ops.ListActivitiesResult),
        ("list-sync-statuses.yaml", ops.ListSyncStatusesResult),
    ):
        _, reply_pin = pinned(name, "reply")
        assert result.FromString(reply_pin).SerializeToString(deterministic=True) == reply_pin


async def test_a_re_resolution_made_with_the_sdk_is_the_pinned_bytes(sidecar) -> None:
    """An activity re-resolved through `plugin.re_resolve_activity`, its
    provenance put on the wire by the SDK's own conversion, is the request
    the re-resolve-activity fixture pins once the sidecar stamps its account
    from the link; the reply, and the event and record operations hears and
    reads, read back whole as the SDK's types (W2.15, W2.16, contract v15)."""
    import meridian
    from meridian.plugin.v1 import operations_pb2 as ops
    from meridian.v1 import holdings_pb2

    def pinned(name: str, section: str = "request") -> tuple[dict[str, Any], bytes]:
        fixture = yaml.safe_load((fixtures_root() / _find(name)).read_text(encoding="utf-8"))
        return (
            fixture[section]["fields"],
            base64.b64decode(fixture["expected_proto_bytes_b64"][section]),
        )

    asked, asked_pin = pinned("re-resolve-activity.yaml")
    _, reply_pin = pinned("re-resolve-activity.yaml", "reply")
    heard, heard_pin = pinned("activity-re-resolved.yaml", "event")

    service, address = sidecar
    service.operations.links[asked["external_account_id"]] = asked["account_id"]
    # The activity it names, recorded first, as the street holds it.
    service.operations.activities.append(
        ops.ActivityRecordedEvent(
            activity_id="ACT-1",
            account_id=asked["account_id"],
            source=asked["source"],
            activity=ops.CustodialActivity(external_activity_id=asked["external_activity_id"]),
        )
    )
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        await plugin.re_resolve_activity(
            external_account_id=asked["external_account_id"],
            source=asked["source"],
            external_activity_id=asked["external_activity_id"],
            instrument_id=asked["instrument_id"],
            provenance=meridian.Provenance(**asked["provenance"]),
            resolved_at_ns=asked["resolved_at_ns"],
        )
    finally:
        await plugin.leave()

    (sent,) = service.operations.sent
    stamped = holdings_pb2.ReResolveActivityRequest.FromString(sent.SerializeToString())
    stamped.account_id = asked["account_id"]
    assert stamped.SerializeToString(deterministic=True) == asked_pin

    reply = ops.ReResolveActivityResult.FromString(reply_pin)
    assert reply.SerializeToString(deterministic=True) == reply_pin
    event = ops.ActivityReResolvedEvent.FromString(heard_pin)
    assert event.SerializeToString(deterministic=True) == heard_pin
    assert event.re_resolution.account_id == heard["re_resolution"]["account_id"]
    assert event.re_resolution.provenance.kind == ops.PROVENANCE_KIND_SUPPLIED


@pytest.mark.parametrize(
    ("name", "role", "reads", "writes"),
    [
        ("open-plugin-interface.yaml", "oms", {"ACC-1", "ACC-2"}, {"ACC-1"}),
        ("act-for-person.yaml", "custody", {"ACC-GROWTH"}, {"ACC-GROWTH"}),
    ],
)
def test_the_pinned_claims_read_as_each_roles_level_and_accounts(
    name: str, role: str, reads: set[str], writes: set[str]
) -> None:
    """The claims the dashboard mints, as their fixtures pin them from
    contract v15: each role's entry read by `Caller`, its accounts resolved
    from their positions in the claims' read accounts (W6.9, W4.9)."""
    from meridian import Caller
    from meridian.v1 import sidecar_pb2

    fixture = yaml.safe_load((fixtures_root() / _find(name)).read_text(encoding="utf-8"))
    if name == "open-plugin-interface.yaml":
        assertion = base64.b64decode(fixture["expected_proto_bytes_b64"]["request"])
    else:
        given = fixture["request"]["fields"]["acting_for"]
        assertion = sidecar_pb2.CallerAssertion(
            claims=base64.b64decode(given["claims"]),
            signature=base64.b64decode(given["signature"]),
            key_id=given["key_id"],
        ).SerializeToString()
    caller = Caller.from_header(base64.urlsafe_b64encode(assertion).decode().rstrip("="))
    assert caller.level == sidecar_pb2.ACCESS_LEVEL_WRITE
    assert caller.roles == {role: sidecar_pb2.ACCESS_LEVEL_WRITE}
    assert caller.level_for(role) == sidecar_pb2.ACCESS_LEVEL_WRITE
    assert caller.read_for(role) == reads and caller.write_for(role) == writes
    assert (caller.read, caller.write) == (reads, writes), "equal to the whole, one role"


async def test_a_move_made_with_the_sdk_is_the_pinned_bytes(
    sidecar, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A unit archived through `plugin.archive_unit`, its rule the kind's
    window setting and value as the SDK names it, is the request the
    record-move fixture pins; the reply reads back whole (W4.13, contract
    v16). The kind it names is declared as the register fixture's v16 case
    declares it."""
    import meridian
    from meridian.v1 import sidecar_pb2

    fixture = yaml.safe_load((fixtures_root() / _find("record-move.yaml")).read_text("utf-8"))
    asked = fixture["request"]["fields"]
    pins = fixture["expected_proto_bytes_b64"]
    register = yaml.safe_load((fixtures_root() / _find("register.yaml")).read_text("utf-8"))
    (v16,) = [
        case
        for case in register["cases"]
        if case.get("request_fields", {}).get("schema_version") == "v16"
    ]
    declared = v16["request_fields"]["declaration"]["storage"]
    storage = meridian.Storage(
        retention_days=declared["retention_days"],
        kinds=[meridian.RecordKind(**kind) for kind in declared["record_kinds"]],
    )

    granted, archive = tmp_path / "storage", tmp_path / "archive"
    (granted / asked["unit"]).mkdir(parents=True)
    (granted / asked["unit"] / "act-1.json").write_text("{}")
    archive.mkdir()
    monkeypatch.setenv("MERIDIAN_STORAGE_DIR", str(granted))
    monkeypatch.setenv("MERIDIAN_ARCHIVE_DIR", str(archive))
    window, value = asked["rule"].split(" ")

    service, address = sidecar
    service.settings = [
        sidecar_pb2.SettingsDelivery(
            values=[
                sidecar_pb2.SettingValue(name=window, value=value),
                sidecar_pb2.SettingValue(
                    name=f"{asked['record_kind']}_past_window", value="archived"
                ),
            ]
        )
    ]
    plugin = await meridian.connect(
        address, heartbeat=False, declaration=meridian.Declaration(storage=storage)
    )
    try:
        async for _ in plugin.settings():
            break
        await plugin.archive_unit(
            asked["record_kind"],
            asked["unit"],
            record_count=asked["record_count"],
            first_received_ns=asked["first_received_ns"],
            last_received_ns=asked["last_received_ns"],
        )
    finally:
        await plugin.leave()

    ((sent, _, _),) = service.moves
    assert sent.SerializeToString(deterministic=True) == base64.b64decode(pins["request"])
    reply = sidecar_pb2.RecordMoveReply.FromString(base64.b64decode(pins["reply"]))
    assert reply.SerializeToString() == base64.b64decode(pins["reply"])


async def test_the_v16_declaration_and_heartbeat_cases_are_what_the_sdk_sends(
    sidecar, tmp_path, monkeypatch
) -> None:
    """The register fixture's v16 case is the declaration the SDK sends, its
    four window settings beside it; the heartbeat fixture's v16 cases are what
    `plugin.stored` puts on the heartbeat (W4.1, W4.5, W6.11), each kind's
    `bytes` the SDK's, from an index holding that much archived."""
    import json

    from google.protobuf import json_format as _json

    import meridian
    from meridian.v1 import sidecar_pb2

    register = yaml.safe_load((fixtures_root() / _find("register.yaml")).read_text("utf-8"))
    (v16,) = [
        case
        for case in register["cases"]
        if case.get("request_fields", {}).get("schema_version") == "v16"
    ]
    given = v16["request_fields"]["declaration"]
    declaration = meridian.Declaration(
        settings=[meridian.Setting(name, secret=True) for name in given["secret_settings"]],
        storage=meridian.Storage(
            retention_days=given["storage"]["retention_days"],
            kinds=[meridian.RecordKind(**kind) for kind in given["storage"]["record_kinds"]],
        ),
    )
    expected = sidecar_pb2.PluginDeclaration()
    _json.ParseDict(given, expected)
    beat = yaml.safe_load((fixtures_root() / _find("heartbeat.yaml")).read_text("utf-8"))
    accepted = [
        case["request_fields"]["stored"]
        for case in beat["cases"]
        if "status" not in case and "stored" in case.get("request_fields", {})
    ]
    assert len(accepted) == 2, "the fixture's two accepted v16 cases"

    # The SDK's index, holding as many bytes archived of each kind as the
    # fixture says: the bytes are its, never the plugin's.
    monkeypatch.setenv("MERIDIAN_STORAGE_DIR", str(tmp_path))
    index = tmp_path / ".meridian" / "archive" / "index.json"
    index.parent.mkdir(parents=True)
    units = {}
    for span in accepted[0]:
        if int(span.get("bytes", 0)):
            unit = f"{span['record_kind']}/archived"
            units[unit] = {
                "record_kind": span["record_kind"],
                "unit": unit,
                "record_count": 1,
                "first_received_ns": 1,
                "last_received_ns": 1,
                "state": "archived",
                "files": {"": [int(span["bytes"]), "0" * 64]},
            }
    index.write_text(json.dumps({"units": units}))

    service, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False, declaration=declaration)
    heard = []
    try:
        for stored in accepted:
            plugin.stored = [
                _json.ParseDict({**span, "bytes": "0"}, sidecar_pb2.StoredSpan())
                for span in stored
            ]
            await plugin.report(healthy=True)
            heard.append(list(service.heartbeats[-1].stored))
    finally:
        await plugin.leave()

    (sent,) = service.registered
    assert sent.schema_version == "v16"
    assert sent.declaration.SerializeToString(deterministic=True) == expected.SerializeToString(
        deterministic=True
    )
    names = [s.name for s in sent.settings if not s.secret]
    assert names == [
        "activity_window_days",
        "activity_past_window",
        "responses_window_days",
        "responses_past_window",
    ]
    for stored, beat_heard in zip(accepted, heard, strict=True):
        wanted = [_json.ParseDict(span, sidecar_pb2.StoredSpan()) for span in stored]
        assert beat_heard == wanted
