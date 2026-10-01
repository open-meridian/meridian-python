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
    )
    pin = base64.b64decode(fixture["expected_proto_bytes_b64"]["request"])
    assert built.SerializeToString(deterministic=True) == pin
