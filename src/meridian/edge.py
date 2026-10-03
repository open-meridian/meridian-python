"""What the edge keeps of its own (contract v11).

spec/vendor-differences-have-a-place-in-the-contract, slice A: a vendor's
knowledge stops at the plugin that speaks to it. A custody plugin converts its
vendor's codes into the contract's values; what it cannot convert it sends as
the field's not-known value with the vendor's value beside it, as reported; it
references, on every row, the raw record the row was converted from, in its
own storage; and every value it closed rather than read carries its
provenance -- reported by the vendor, from a second source, supplied by a
named person, or derived by a named rule.

    from meridian.edge import as_reported, derived

    await plugin.report_external_accounts(accounts=[meridian.ExternalAccount(
        external_account_id="ACC-1",
        account_kind="ACCOUNT_KIND_UNSPECIFIED",
        account_kind_as_reported=as_reported("myvendor:account-type", "INDIVIDUAL"),
    )])
    await plugin.record_holding(
        ...,
        quantity=net_cash,
        raw_record=plugin.raw_record("balances/ACC-1/2026-09-08"),
        provenance=[derived("quantity", "cash net of money market funds counted in cash")],
    )

A backfill (W2.4) re-sends a row already recorded, under its statement, with
a field a contract revision added, re-converted from the plugin's raw records
as far back as its declared retention; the street journals it as an amendment
beside the row as first recorded. `backfill("v11", "raw_record")` is the mark
`record_holding(backfill=...)` takes, and `within_retention` says whether a
raw record received at a moment is still in reach.

The raw records live in the storage the deployment grants a plugin holding an
edge role, for its instance alone (decisions/028): `storage_dir()` is where
it is mounted, or None where none is granted (a test, a deployment before
it, a plugin holding no edge role). The plugin keeps what it likes there and
rebuilds from it; no other plugin reaches it.
"""

from __future__ import annotations

import os
from pathlib import Path

from .bounds import (
    AS_REPORTED_CODE_LENGTH,
    AS_REPORTED_SCHEME_LENGTH,
    AS_REPORTED_TEXT_LENGTH,
    PROVENANCE_FIELD_LENGTH,
    PROVENANCE_PERSON_LENGTH,
    PROVENANCE_RULE_LENGTH,
    PROVENANCE_SOURCE_LENGTH,
    RAW_RECORD_REF_KEY_LENGTH,
    Length,
)
from .operations import Provenance
from .plugin.v1.operations_pb2 import AsReported, Backfill, RawRecordRef

NANOS_PER_DAY = 86_400 * 1_000_000_000

#: Where the deployment says it mounted the instance's own storage.
STORAGE_DIR = "MERIDIAN_STORAGE_DIR"


def storage_dir() -> Path | None:
    """The storage the deployment grants this instance for its raw records
    (decisions/028), or None where it grants none."""
    granted = os.environ.get(STORAGE_DIR, "")
    return Path(granted) if granted else None


def _within(text: str, bound: Length, name: str) -> str:
    least, most = bound.least, bound.most
    if not least <= len(text) <= most:
        raise ValueError(f"{name} is {len(text)} characters; {least} to {most}")
    return text


def as_reported(scheme: str, code: str, text: str | None = None) -> AsReported:
    """A vendor's value that did not convert, beside the field's not-known
    value: whose vocabulary (`plugin:code-set`), the code as sent, and the
    vendor's own words for it -- the code again where it gives none. Refused,
    as the sidecar refuses it, for a part empty or past its length."""
    return AsReported(
        scheme=_within(scheme, AS_REPORTED_SCHEME_LENGTH, "scheme"),
        code=_within(code, AS_REPORTED_CODE_LENGTH, "code"),
        text=_within(code if text is None else text, AS_REPORTED_TEXT_LENGTH, "text"),
    )


def raw_record(key: str, instance_id: str = "") -> RawRecordRef:
    """A reference to a raw record in the plugin's own storage, by its own
    key. The instance is the plugin's own: `plugin.raw_record(key)` sets it,
    and the sidecar fills it where it is left empty and refuses another."""
    return RawRecordRef(
        instance_id=instance_id, key=_within(key, RAW_RECORD_REF_KEY_LENGTH, "key")
    )


def derived(field: str, rule: str) -> Provenance:
    """A value derived by a named rule in the plugin's code, from what the
    vendor did send: `field` is its path in the message."""
    return Provenance(
        field=_within(field, PROVENANCE_FIELD_LENGTH, "field"),
        kind="PROVENANCE_KIND_DERIVED",
        rule=_within(rule, PROVENANCE_RULE_LENGTH, "rule"),
    )


def supplied(field: str, person: str) -> Provenance:
    """A value a named person supplied on the plugin's page."""
    return Provenance(
        field=_within(field, PROVENANCE_FIELD_LENGTH, "field"),
        kind="PROVENANCE_KIND_SUPPLIED",
        person=_within(person, PROVENANCE_PERSON_LENGTH, "person"),
    )


def second_source(field: str, source: str, record: RawRecordRef | None = None) -> Provenance:
    """A value from a second source of the plugin's own -- never another
    plugin's storage -- by name, and the raw record it was read from."""
    return Provenance(
        field=_within(field, PROVENANCE_FIELD_LENGTH, "field"),
        kind="PROVENANCE_KIND_SECOND_SOURCE",
        source=_within(source, PROVENANCE_SOURCE_LENGTH, "source"),
        raw_record=record,
    )


def reported(field: str, record: RawRecordRef) -> Provenance:
    """A value the vendor reported in a raw record other than the message's
    own: its activity, say, beside the positions a row came from."""
    return Provenance(
        field=_within(field, PROVENANCE_FIELD_LENGTH, "field"),
        kind="PROVENANCE_KIND_REPORTED",
        raw_record=record,
    )


def backfill(contract_version: str, field: str) -> Backfill:
    """The mark on a row sent again to fill `field`, which `contract_version`
    added (W2.4): the amendment's cause."""
    if not contract_version.startswith("v") or not contract_version[1:].isdigit():
        raise ValueError(f"contract_version {contract_version!r} is not of the form v<N>")
    return Backfill(contract_version=contract_version, field=field)


def within_retention(received_at_ns: int, now_ns: int, retention_days: int) -> bool:
    """Whether a raw record received at `received_at_ns` is within the
    retention the plugin declared: a backfill reaches no further back."""
    return now_ns - received_at_ns <= retention_days * NANOS_PER_DAY
