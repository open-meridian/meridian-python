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
"""

from __future__ import annotations

import base64
import os
import pathlib

# Importing the package registers every message in the default descriptor pool,
# which is how a type named in a fixture is found by name.
import meridian.v1.accounts_pb2  # noqa: F401
import meridian.v1.envelope_pb2  # noqa: F401
import meridian.v1.holdings_pb2  # noqa: F401
import meridian.v1.reference_pb2  # noqa: F401
import meridian.v1.sidecar_pb2  # noqa: F401
import pytest
import yaml
from google.protobuf import descriptor_pool, json_format, message_factory

SECTIONS = ("request", "reply", "event")


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
    json_format.ParseDict(body.get("fields") or {}, expected)
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
