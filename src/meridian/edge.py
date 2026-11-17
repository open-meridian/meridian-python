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

    # in the custody role's class (SDK 0.35): its acts on self
    await self.report_external_accounts(accounts=[meridian.ExternalAccount(
        external_account_id="ACC-1",
        account_kind="ACCOUNT_KIND_UNSPECIFIED",
        account_kind_as_reported=as_reported("myvendor:account-type", "INDIVIDUAL"),
    )])
    await self.record_holding(
        ...,
        quantity=net_cash,
        raw_record=self.plugin.raw_record("balances/ACC-1/2026-09-08"),
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

**A storage per shard** (step 3d, item 30). An instance running as shards,
or with a standby, shares one storage among its pods, a folder per shard:
the plugin learns its shard when it registers (`RegisterReply.shard` and
`.shards`), and from then `storage_dir()` is its own shard's folder,
`<storage>/shard-<n>`, the only place it writes; `instance_storage_dir()` is
the whole, every shard's folder under it, which any pod reads. A key names a
record across the instance: `plugin.raw_record(key)` prefixes a key in the
shard's folder with `shard-<n>/` (one prefixed already is kept as it is), as
`RawStore` does, the archive's objects are kept under the same prefix, and a
move is reported with it on its unit, so two shards' units of one name stay
two. A key with no prefix names what the instance kept before it ran as
shards, which its storage's copy put under `shard-0/`. Each shard keeps its
own index of what moved; `find_record` reads the index of the shard a key
names, whichever pod wrote it; the archive's bound is the instance's, over
every shard's index. A restore or a deletion names a unit as the instance
does (one with no prefix is shard 0's), and one of another shard's is
refused, "the unit <unit> is shard <m>'s: its own pod restores it".
Before the plugin registers no shard is known, and `storage_dir()` is the
storage as a whole -- except on a storage its copy step converted for shards
(`.meridian/copied-from-<claim>`), or one holding a shard's folder, where it
raises: a plugin reads its
storage from its class's `on_start` (0.37.0); an instance of one pod (`shards` 0) has no shard
folders, its keys no prefix, as before.

**The archive** (contract v16; spec/an-edge-plugins-older-records-move-to-
the-archive). A plugin declaring its kinds of raw record
(`Storage(kinds=[RecordKind(...)])`) keeps each for its window, a setting
its admin sets, and past it the record is archived, kept or deleted as the
admin chose (`<kind>_window_days`, `<kind>_past_window`, which the SDK
declares). The archive is the instance's own, where a deployment admin
allowed it one: `archive_dir()` where it is mounted, or in a cloud the
bucket `MERIDIAN_ARCHIVE_BUCKET` names, reached through the same interface
(put, get, list by prefix, delete); neither, and records past their window
are kept. Its bound, where a deployment admin gave one, is
`MERIDIAN_ARCHIVE_MOST_BYTES` (unset, or 0, for none):
`archive_unit` refuses a unit that would take the archive past it, before
anything is written or reported, and the unit stays in storage.

A bucket is reached under the pod's account, which the bucket's workload
identity trusts by name. So `meridian.run` asks the bucket before each
Register, for at most one key under the instance's prefix (a list, the least
the account may do): refused on auth -- a 401 or 403, or no credential at
all -- the plugin does not register, says "the archive's bucket refuses this
instance's account <namespace>/<account>: its workload identity must trust
that account (pluginArchive in values.yaml)", naming the account from
`MERIDIAN_POD_NAMESPACE` and `MERIDIAN_POD_SERVICE_ACCOUNT` where the
deployment gives both ("this instance's account" alone otherwise), and asks
again once a minute, never
exiting, until the administrator's trust is in place. Anything else -- a
network fault, a 5xx, no answer in 30 s -- is said, and the plugin goes on.

The plugin moves its own records, in units it can find again: a unit is a
file or a directory in its storage, named by its path there
("activity/ACC-1/2019-03"), and the records it holds are the paths within
it, whose keys a row's `record_key` names. Its helpers keep an index of what
moved, in the storage:

    await plugin.archive_unit("activity", "activity/ACC-1/2019-03",
                              record_count=214, first_received_ns=..., last_received_ns=...)
    plugin.find_record("activity/ACC-1/2019-03/act-77")  # its last move: archived
    path = await plugin.restore_unit("activity", "activity/ACC-1/2019-03",
                                     for_caller=request.caller)
    await plugin.delete_unit("responses", "responses/ACC-1/2026-09", record_count=12, ...)

`archive_unit` writes the unit to the archive, checks each file landed (its
size and digest), reports the move through the sidecar (W4.13), and only
then removes it from storage; a move by a window names its rule, the window
setting and its value. `restore_unit` copies a unit back for the person who
asked, to a restore area in storage it answers the path of, readable there
until the restore period (seven days) passes and it is removed, its return
reported. `delete_unit` reports the deletion first, so a refusal --
`CommandRefused` with REFUSAL_REASON_WITHIN_HOLD inside the deployment's
hold -- keeps the unit; deleting an archived unit is an admin's act. Nothing
of a record's content is ever in a move: a count, two times and the key.

Moves are made one at a time, in the process and across the pods holding a
shard at once (a deposed holder in a takeover's lapse and the new one), by a
lock on the shard's index. A move waits for another's at most 30 seconds,
then is refused (TimeoutError) and the unit kept, for the next pass to try
again; the sidecar is given 30 seconds to record a move. The heartbeat never
waits on a move: it returns restored units only when nothing else holds the
lock. One `Plugin` per process makes the moves, from the loop it registered
on: while one declaring storage is registered, `connect` refuses a second,
and a move from another loop is refused. Neither the moves nor `RawStore`
are thread-safe.

What each kind holds in storage is the plugin's to say, as its figures are
(`plugin.stored`, one `StoredSpan` per kind), on every heartbeat; the bytes
each kind uses of the archive (`StoredSpan.bytes`) are the SDK's, summed
from its index on every heartbeat, and the deployment's Summary draws them
against the bound. Every edge
plugin with pages offers `POST /archive/restore`, which the SDK declares on
its host and the deployment derives as a tool: the kind and the unit, for a
person at `write`, the person read from the claims.

**Raw records as files** (0.30.0): `RawStore` keeps a vendor's answers in
storage, one unit a UTC day, before anything is read from them, and moves
the units past the kind's window (`tend`); `storage_root()` is the granted
storage, else a temporary directory. A convenience: any layout the plugin
finds again serves.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import time
import urllib.parse
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Protocol

from ._raw import RawStore as RawStore
from ._raw import StoredUnit as StoredUnit
from ._raw import _try_lock, _unlock
from ._raw import storage_root as storage_root
from .bounds import (
    AS_REPORTED_CODE_LENGTH,
    AS_REPORTED_SCHEME_LENGTH,
    AS_REPORTED_TEXT_LENGTH,
    PROVENANCE_FIELD_LENGTH,
    PROVENANCE_PERSON_LENGTH,
    PROVENANCE_RULE_LENGTH,
    PROVENANCE_SOURCE_LENGTH,
    RAW_RECORD_REF_KEY_LENGTH,
    RECORD_MOVE_REQUEST_RECORD_COUNT_RANGE,
    RECORD_MOVE_REQUEST_RULE_LENGTH,
    RECORD_MOVE_REQUEST_UNIT_LENGTH,
    Length,
)
from .operations import Provenance
from .plugin.v1.operations_pb2 import AsReported, Backfill, RawRecordRef
from .v1 import sidecar_pb2

if TYPE_CHECKING:
    from .client import Caller, Plugin
    from .declaration import RecordKind
    from .pages import Pages

NANOS_PER_DAY = 86_400 * 1_000_000_000

log = logging.getLogger("meridian.edge")

#: Where the deployment says it mounted the instance's own storage.
STORAGE_DIR = "MERIDIAN_STORAGE_DIR"

#: The instance's shard count, as the launcher sets it on every container of
#: a pod of an instance with several shards or a standby (1 for a standby
#: alone); unset on an instance's one pod (step 3d; PO 73).
_PLUGIN_SHARDS = "MERIDIAN_PLUGIN_SHARDS"


#: The shard this pod serves and how many its instance runs, as its sidecar
#: answered Register (`RegisterReply.shard`, `.shards`; step 3d, item 30):
#: None until the plugin has registered.
_serving: tuple[int, int] | None = None

#: Counted up at every Register: a pod admitted again in the same process,
#: as another shard or its own taken back, has what it remembered of its
#: storage's files read afresh (`RawStore`).
_generation = 0

#: A key's shard prefix: `shard-<n>/`, n as a whole number unpadded.
_SHARD_KEY = re.compile(r"shard-(0|[1-9][0-9]*)/")


def _registered_as(shard: int, shards: int) -> None:
    """What Register answered of this pod's shard; held while the process
    lives, so a pod waiting for its sidecar again writes where it wrote."""
    global _serving, _generation
    _serving = (shard, shards)
    _generation += 1


def _sharded() -> bool:
    return _serving is not None and _serving[1] >= 1


def _shard_prefix() -> str:
    """`shard-<n>/` once the plugin registered as a shard of its instance;
    "" for an instance of one pod, or before it registered."""
    return f"shard-{_serving[0]}/" if _serving is not None and _sharded() else ""


def instance_storage_dir() -> Path | None:
    """The storage the deployment grants the instance as a whole, every
    shard's folder under it, which any pod of the instance reads (step 3d,
    item 30); for an instance of one pod, `storage_dir()` itself. None where
    none is granted."""
    granted = os.environ.get(STORAGE_DIR, "")
    return Path(granted) if granted else None


def storage_dir() -> Path | None:
    """The storage the deployment grants this instance for its raw records
    (decisions/028), or None where it grants none: once the plugin has
    registered as a shard of its instance, its own shard's folder,
    `<storage>/shard-<n>`, where alone it writes (step 3d, item 30).

    Read before Register on an instance the launcher says runs shards or a
    standby (`MERIDIAN_PLUGIN_SHARDS` 1 or more), on a storage its copy step
    converted for shards (`.meridian/copied-from-<claim>` at its root), or
    on one holding a shard's folder (`shard-<n>/`), it raises RuntimeError:
    the shard's folder is known only once registered, and the root is no
    pod's to write. A plugin reads it from its class's `on_start`."""
    if _serving is None:
        _refuse_before_register()
    return _storage_dir()


def _refuse_before_register() -> None:
    """The refusal of a read of the shard's folder before Register, on a
    storage shared among an instance's pods: one its copy step converted for
    shards (`.meridian/copied-from-<claim>`), or one a pod of the instance
    has written a shard's folder in (`shard-<n>/`). A shared storage no pod
    has written in yet is not told from an instance's own (sdk4-review H4,
    sdk5-review M3)."""
    granted = instance_storage_dir()
    if granted is None:
        return
    shards = os.environ.get(_PLUGIN_SHARDS, "").strip()
    if shards.isdigit() and int(shards) >= 1:
        raise RuntimeError(
            f"storage_dir() was read before the plugin registered, on an instance of "
            f"{shards} shard(s) or a standby ({_PLUGIN_SHARDS}): its pods share its storage, "
            f"its shard's folder is known only once registered, and the root is no pod's "
            f"to write. Read storage from the class's on_start; `meridian plugin migrate` "
            f"to 0.37.0 rewrites the connectivity template's trading files and names any "
            f"other such read it finds"
        )
    with contextlib.suppress(OSError):
        shared = next((granted / ".meridian").glob("copied-from-*"), None) or next(
            (p for p in granted.glob("shard-*") if _SHARD_KEY.fullmatch(p.name + "/")), None
        )
        if shared is not None:
            raise RuntimeError(
                f"storage_dir() was read before the plugin registered, on storage its "
                f"instance's pods share ({shared.relative_to(granted)}): its shard's folder "
                f"is known only once registered, and the root is no pod's to write. Read "
                f"storage from the class's on_start; `meridian plugin migrate` to 0.37.0 "
                f"rewrites the connectivity template's trading files and names any other "
                f"such read it finds"
            )


def _storage_dir() -> Path | None:
    """`storage_dir()`, before Register too: the storage as a whole then."""
    granted = instance_storage_dir()
    prefix = _shard_prefix()
    if granted is None or not prefix:
        return granted
    return granted / prefix.rstrip("/")


def _split(key: str) -> tuple[int | None, str]:
    """A key's shard, where it is prefixed with one, and the key within it."""
    named = _SHARD_KEY.match(key)
    if named is None:
        return None, key
    return int(named.group(1)), key[named.end() :]


def _instance_key(key: str) -> str:
    """A key in this pod's storage as the instance names it: prefixed with
    its shard, where it serves one, storage is granted, and the key names
    none already."""
    if _SHARD_KEY.match(key) or instance_storage_dir() is None:
        return key
    return _shard_prefix() + key


def _shard_folder(key: str) -> tuple[Path | None, str]:
    """The folder a key across the instance is in, and the key within it:
    the shard its prefix names; with none, on an instance of shards, shard
    0's, where its storage's copy put what it kept before; the storage as a
    whole otherwise, as before shards."""
    granted = instance_storage_dir()
    if granted is None or not _sharded():
        return granted, key
    shard, within = _split(key)
    return granted / f"shard-{shard or 0}", within


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
    and the sidecar fills it where it is left empty and refuses another.
    On a shard of its instance, a key in the shard's folder is prefixed
    `shard-<n>/`; one prefixed already is kept as it is."""
    return RawRecordRef(
        instance_id=instance_id,
        key=_within(_instance_key(key), RAW_RECORD_REF_KEY_LENGTH, "key"),
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


def supplied_currency(
    rows: Sequence[Mapping[str, Any]],
    external_account_id: str,
    field: str = "stated_currency",
) -> tuple[str, Provenance] | None:
    """A linked account's currency from the `account_currency` setting's
    rows (`meridian.account_currency()`, contract v23, W3.1): the account's
    own row, else the plugin-wide one naming no account, as its ISO 4217 code
    with its provenance, supplied by the person the conductor stamped on the
    row (`changed_by`), for the value at `field`. None while no row covers
    the account, or its code is not three letters: the plugin then reports
    nothing that needs the currency, never a guess.

    By default the entry is ready to put on ResolveIdentifier, its field
    `stated_currency` (`ResolveIdentifierRequest.provenance`, approved
    2026-10-13): `code, entry = supplied_currency(rows, account)`, then
    `resolve_identifier(..., stated_currency=code, provenance=[entry])`. Name
    another field for a row's own value: `average_cost.currency_code` on a
    holding."""
    own = [row for row in rows if (row.get("external_account") or "") == external_account_id]
    every = [row for row in rows if not row.get("external_account")]
    for row in (own or every)[:1]:
        code = str(row.get("currency") or "").strip().upper()
        person = str(row.get("changed_by") or "")
        if len(code) == 3 and code.isalpha() and person:
            return code, supplied(field, person)
    return None


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


# ── The archive (contract v16) ──────────────────────────────────────────────

#: Where the deployment says it mounted the instance's archive, beside its
#: storage; and, in a cloud, the bucket it was given instead (W8.3, W8.7).
_ARCHIVE_DIR = "MERIDIAN_ARCHIVE_DIR"
_ARCHIVE_BUCKET = "MERIDIAN_ARCHIVE_BUCKET"

#: The archive's bound in bytes, beside where it is (W8.3; named
#: 2026-10-07): unset, or 0, for none.
_ARCHIVE_MOST_BYTES = "MERIDIAN_ARCHIVE_MOST_BYTES"

#: How long a restored unit stays readable in the restore area before it is
#: removed and its return reported: the deployment's restore period, seven
#: days (the plan's question 2, ruled 2026-10-05).
_RESTORE_DAYS = 7
_RESTORE_RULE = f"restore period {_RESTORE_DAYS} days"

#: Where the helpers keep their own, inside the instance's storage: the index
#: of what moved, and the restore area. Never a unit's path.
_OWN = ".meridian"
_INDEX = PurePosixPath(_OWN, "archive", "index.json")
#: The index's lock across processes: a file beside it that only `_Moves`
#: opens, so closing any other descriptor on the index never drops it.
_INDEX_LOCK = PurePosixPath(_OWN, "archive", "index.lock")
_RESTORED = PurePosixPath(_OWN, "restored")

_OUTCOMES = {
    "archived": sidecar_pb2.MOVE_OUTCOME_ARCHIVED,
    "restored": sidecar_pb2.MOVE_OUTCOME_RESTORED,
    "returned": sidecar_pb2.MOVE_OUTCOME_RETURNED,
    "deleted": sidecar_pb2.MOVE_OUTCOME_DELETED,
}


def archive_dir() -> Path | None:
    """The archive a deployment admin allowed this instance, where it is
    mounted (`MERIDIAN_ARCHIVE_DIR`, W8.7), or None where there is none --
    a test, an instance allowed none, or a cloud's bucket instead."""
    given = os.environ.get(_ARCHIVE_DIR, "")
    return Path(given) if given else None


def _archive_most_bytes() -> int:
    """The archive's bound, in bytes, as the deployment gave it
    (`MERIDIAN_ARCHIVE_MOST_BYTES`, W8.3), or 0 where it gave none. A value
    that is not a whole number of bytes is refused: the bound is not guessed."""
    given = os.environ.get(_ARCHIVE_MOST_BYTES, "").strip()
    if not given:
        return 0
    if not given.isdigit():
        raise ValueError(
            f"{_ARCHIVE_MOST_BYTES} is {given!r}: the archive's bound is a whole number of "
            "bytes, or unset for none"
        )
    return int(given)


class _Objects(Protocol):
    """The archive as the helpers use it, one interface over its two
    backends (kernel/edge-plugins-own-storage-for-raw-records, ruling 1): a
    directory where it is mounted, a bucket in a cloud."""

    def put(self, key: str, data: bytes) -> None: ...

    def get(self, key: str) -> bytes: ...

    def list(self, prefix: str) -> list[str]: ...

    def delete(self, key: str) -> None: ...

    def landed(self, key: str) -> tuple[int, str] | None:
        """Its size and SHA-256 as the archive holds it, or None."""
        ...


class _Directory:
    """The archive mounted as a directory: a key is a path under it."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root.joinpath(*PurePosixPath(key).parts)

    def put(self, key: str, data: bytes) -> None:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_whole(target, data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def list(self, prefix: str) -> list[str]:
        found = []
        for path in sorted(self.root.rglob("*")):
            if path.is_file():
                key = path.relative_to(self.root).as_posix()
                if key.startswith(prefix):
                    found.append(key)
        return found

    def delete(self, key: str) -> None:
        path = self._path(key)
        path.unlink(missing_ok=True)
        _prune(path.parent, self.root)

    def landed(self, key: str) -> tuple[int, str] | None:
        path = self._path(key)
        if not path.is_file():
            return None
        data = path.read_bytes()
        return len(data), hashlib.sha256(data).hexdigest()


class _Bucket:
    """The archive as a cloud's bucket (`s3://bucket/prefix`), reached with
    the credential the pod's workload identity scopes to it, never a key.
    Read through boto3, which a plugin deployed with a bucket installs: the
    SDK carries no cloud's library for every plugin."""

    def __init__(self, url: str, client: Any = None) -> None:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "s3" or not parsed.netloc:
            raise ValueError(
                f"{_ARCHIVE_BUCKET} is {url!r}: this SDK reads an s3:// bucket, and no "
                "other yet"
            )
        self.bucket = parsed.netloc
        self.prefix = parsed.path.strip("/")
        if client is None:
            try:
                import boto3  # type: ignore[import-not-found]
            except ImportError as missing:
                raise RuntimeError(
                    f"{_ARCHIVE_BUCKET} names a bucket, and boto3 is not installed: a plugin "
                    "deployed with a bucket for its archive installs it"
                ) from missing
            client = boto3.client("s3")
        self.client = client

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=self._key(key), Body=data, ChecksumAlgorithm="SHA256"
        )

    def get(self, key: str) -> bytes:
        try:
            answer = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        except Exception as failed:
            if "InvalidObjectState" not in str(failed):
                raise
            # In the cold class: asked back, and readable once it returns.
            with contextlib.suppress(Exception):
                self.client.restore_object(
                    Bucket=self.bucket,
                    Key=self._key(key),
                    RestoreRequest={"Days": _RESTORE_DAYS},
                )
            raise RuntimeError(
                f"{key} is in the archive's cold class: asked back, and restorable once the "
                "archive returns it; ask again later"
            ) from failed
        return bytes(answer["Body"].read())

    def list(self, prefix: str) -> list[str]:
        found: list[str] = []
        token: str | None = None
        while True:
            asked: dict[str, Any] = {"Bucket": self.bucket, "Prefix": self._key(prefix)}
            if token:
                asked["ContinuationToken"] = token
            page = self.client.list_objects_v2(**asked)
            cut = len(self.prefix) + 1 if self.prefix else 0
            found.extend(str(each["Key"])[cut:] for each in page.get("Contents", ()))
            token = page.get("NextContinuationToken")
            if not token:
                return found

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._key(key))

    def landed(self, key: str) -> tuple[int, str] | None:
        try:
            head = self.client.head_object(
                Bucket=self.bucket, Key=self._key(key), ChecksumMode="ENABLED"
            )
        except Exception:
            return None
        import base64

        held = str(head.get("ChecksumSHA256", ""))
        digest = base64.b64decode(held).hex() if held else ""
        return int(head["ContentLength"]), digest

    def answers(self) -> None:
        """The least the instance's account may be asked: a list of at most
        one key under its own prefix. What the bucket refuses is raised."""
        self.client.list_objects_v2(Bucket=self.bucket, Prefix=self._key(""), MaxKeys=1)


#: Where the deployment names the pod's namespace and account, from the
#: downward API (PO item 64): what a refusal names the account by.
_POD_NAMESPACE = "MERIDIAN_POD_NAMESPACE"
_POD_SERVICE_ACCOUNT = "MERIDIAN_POD_SERVICE_ACCOUNT"


def _refused_text() -> str:
    """What a plugin says while the archive's bucket refuses its account
    (PO items 60, 61 and 64): the account as `<namespace>/<account>` where
    the deployment gives both, else "this instance's account" alone."""
    namespace = os.environ.get(_POD_NAMESPACE, "").strip()
    account = os.environ.get(_POD_SERVICE_ACCOUNT, "").strip()
    named = f" {namespace}/{account}" if namespace and account else ""
    return (
        f"the archive's bucket refuses this instance's account{named}: its workload identity "
        "must trust that account (pluginArchive in values.yaml)"
    )


#: The codes a refusal of the account is answered with where its HTTP
#: status alone does not say so: STS's, as the pod's web identity is
#: exchanged for a credential before the bucket is asked.
_AUTH_CODES = frozenset({"AccessDenied", "InvalidIdentityToken", "InvalidClientTokenId"})

#: The pod holds no credential at all: no identity is associated with its
#: account (EKS Pod Identity's refusal; botocore's name for it).
_NO_CREDENTIAL = frozenset({"NoCredentialsError"})


def _refused_on_auth(failed: BaseException) -> bool:
    """Whether the bucket's answer refuses the pod's account: an HTTP 401 or
    403, a code that says so, or no credential at all. A network fault, a
    timeout or a 5xx says nothing of the account, and is not one. Read by
    shape, as botocore raises it, with no cloud's library imported."""
    if any(kind.__name__ in _NO_CREDENTIAL for kind in type(failed).__mro__):
        return True
    response = getattr(failed, "response", None)
    if not isinstance(response, Mapping):
        return False
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    code = (response.get("Error") or {}).get("Code", "")
    return status in (401, 403) or code in _AUTH_CODES


def _archive_is_bucket() -> bool:
    """Whether the instance's archive is a bucket rather than mounted: the
    one asked before the plugin registers."""
    return archive_dir() is None and bool(os.environ.get(_ARCHIVE_BUCKET, ""))


def _archive_refused() -> str | None:
    """Asked before the plugin registers: where the instance's archive is a
    bucket, the bucket's answer where it refuses the pod's account, else
    None -- no bucket, a bucket that answers, or one that failed otherwise
    (said, and the plugin goes on as with no ask). A client made afresh
    each time, so no credential refused earlier is kept."""
    try:
        archive = _archive()
        if not isinstance(archive, _Bucket):
            return None
        archive.answers()
    except Exception as failed:
        answer = f"{type(failed).__name__}: {failed}"
        if _refused_on_auth(failed):
            return answer
        log.warning("the archive's bucket was not reached at start (%s); going on", answer)
    return None


def _archive() -> _Objects | None:
    """The instance's archive, where it was given one."""
    mounted = archive_dir()
    if mounted is not None:
        return _Directory(mounted)
    bucket = os.environ.get(_ARCHIVE_BUCKET, "")
    return _Bucket(bucket) if bucket else None


def _write_whole(target: Path, data: bytes) -> None:
    """Written whole or not at all: to a file beside it, flushed, renamed."""
    handle, temporary = tempfile.mkstemp(dir=target.parent, prefix=".part-")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, target)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


def _prune(directory: Path, root: Path) -> None:
    """Empty directories removed up to `root`, which stays."""
    while directory != root and root in directory.parents:
        try:
            directory.rmdir()
        except OSError:
            return
        directory = directory.parent


def _unit_path(unit: str) -> PurePosixPath:
    """A unit's path in storage, refused where it is not one: empty or past
    its length, absolute, stepping out, or into the helpers' own."""
    if not RECORD_MOVE_REQUEST_UNIT_LENGTH.admits(len(unit)):
        raise ValueError(f"a unit is 1 to {RECORD_MOVE_REQUEST_UNIT_LENGTH.most} characters")
    path = PurePosixPath(unit)
    if (
        path.is_absolute()
        or "\\" in unit
        or any(part in ("", ".", "..") for part in unit.split("/"))
        or path.parts[0] == _OWN
    ):
        raise ValueError(
            f"the unit {unit!r} is not a path in the plugin's storage: relative, with no "
            f"empty, . or .. part, and not under {_OWN}/"
        )
    return path


def _reported(prefix: str, unit: str) -> str:
    """A new move's unit as it is reported, with its shard's prefix,
    refused past its length."""
    named = prefix + unit
    if not RECORD_MOVE_REQUEST_UNIT_LENGTH.admits(len(named)):
        raise ValueError(f"a unit is 1 to {RECORD_MOVE_REQUEST_UNIT_LENGTH.most} characters")
    return named


def _files(root: Path) -> Iterator[tuple[str, Path]]:
    """A unit's files, by their path within it: the unit's own file as ""."""
    if root.is_file():
        yield "", root
        return
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path.relative_to(root).as_posix(), path


def _object_key(unit: str, within: str) -> str:
    return f"{unit}/{within}" if within else unit


@dataclasses.dataclass
class _Moved:
    """One unit as the index holds it: what it is, where it is now, and the
    files it was archived as, each with its size and digest."""

    record_kind: str
    unit: str
    record_count: int
    first_received_ns: int
    last_received_ns: int
    state: str
    files: dict[str, list[Any]] = dataclasses.field(default_factory=dict)
    at_ns: int = 0
    restored_at_ns: int = 0
    rule: str = ""
    #: Its shard's prefix, `shard-<n>/`, where it moved on a shard of its
    #: instance: on its unit as reported, and on its objects in the archive.
    #: "" for one moved by an instance of one pod, as before shards.
    prefix: str = ""

    @property
    def named(self) -> str:
        """The unit as the instance names it: in its moves and the archive."""
        return self.prefix + self.unit

    @property
    def archive_bytes(self) -> int:
        """What the unit uses of the archive: its files' sizes while the
        archive holds it, a restored unit still counted; none once deleted."""
        if self.state not in ("archived", "restored"):
            return 0
        return sum(int(held[0]) for held in self.files.values())

    def move(self, outcome: str, rule: str = "") -> sidecar_pb2.RecordMoveRequest:
        return sidecar_pb2.RecordMoveRequest(
            record_kind=self.record_kind,
            unit=self.named,
            record_count=self.record_count,
            first_received_ns=self.first_received_ns,
            last_received_ns=self.last_received_ns,
            outcome=_OUTCOMES[outcome],
            rule=rule,
        )


_MOVED_FIELDS = frozenset(field.name for field in dataclasses.fields(_Moved))


class _Index:
    """What moved, kept in the instance's storage, so a unit is found again
    after a restart and a record's key resolves to its unit."""

    def __init__(self, storage: Path) -> None:
        self.storage = storage
        self.path = storage.joinpath(*_INDEX.parts)

    def read(self, *, held: bool = False, lenient: bool = False) -> dict[str, _Moved]:
        """What moved, as the index holds it now. `held`, under the shard's
        lock (`_Moves`): opened to create it, so on NFS the open goes to the
        server even where this pod's client cached the file as missing
        before another pod made it, and the index read is the last
        writer's; never looked up first. Otherwise a missing file is an
        empty index, and a read that fails (a file renamed over meanwhile:
        ESTALE on NFS) is tried once more. `lenient`, for summing bytes
        alone: fields a newer SDK added are passed over."""
        flags = os.O_RDONLY | (os.O_CREAT if held else 0)
        for attempt in (1, 2):
            try:
                fd = os.open(self.path, flags, 0o644)
                with os.fdopen(fd, "rb") as handle:
                    text = handle.read()
                break
            except FileNotFoundError:
                return {}
            except OSError:
                if attempt == 2:
                    raise
        if not text.strip():
            return {}
        whole = json.loads(text)
        if not isinstance(whole, dict):
            raise ValueError(f"{self.path} holds a {type(whole).__name__}, not the index")
        units = whole.get("units", {})
        if lenient:
            units = {
                unit: {name: value for name, value in entry.items() if name in _MOVED_FIELDS}
                for unit, entry in units.items()
            }
        return {unit: _Moved(**entry) for unit, entry in units.items()}

    def write(self, units: dict[str, _Moved]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {"units": {unit: dataclasses.asdict(moved) for unit, moved in units.items()}}
        _write_whole(self.path, json.dumps(body, sort_keys=True, indent=1).encode())

    def archive_bytes(self) -> dict[str, int]:
        """The bytes each kind uses of the archive, as this index holds it."""
        used: dict[str, int] = {}
        for moved in self.read(lenient=True).values():
            if moved.archive_bytes:
                used[moved.record_kind] = used.get(moved.record_kind, 0) + moved.archive_bytes
        return used

    def holding(self, key: str) -> _Moved | None:
        """The unit a record's key is in: the unit itself, or a path in it."""
        units = self.read()
        found = units.get(key)
        if found is not None:
            return found
        for unit, moved in units.items():
            if key.startswith(unit + "/"):
                return moved
        return None


def _storage() -> Path:
    granted = storage_dir()
    if granted is None:
        raise RuntimeError(
            "no storage is granted to this instance (MERIDIAN_STORAGE_DIR): only a plugin at "
            "the edge keeps raw records, and moves them"
        )
    return granted


def _now_ns() -> int:
    return time.time_ns()


def _span(record_count: int, first_received_ns: int, last_received_ns: int) -> None:
    """A unit's count and span within the move's bounds, refused as the
    sidecar refuses them."""
    bound = RECORD_MOVE_REQUEST_RECORD_COUNT_RANGE
    if not bound.least <= record_count <= bound.most:
        raise ValueError(f"record_count is {bound.least} to {bound.most}")
    if first_received_ns <= 0 or last_received_ns <= 0:
        raise ValueError("first_received_ns and last_received_ns are never 0")
    if last_received_ns < first_received_ns:
        raise ValueError("last_received_ns is before first_received_ns")


#: How long a move waits for the shard's index while another move holds it,
#: here or in another pod, at most: past it the move is refused
#: (TimeoutError), the unit kept for the next pass.
_MOVE_WAIT_SECONDS = 30.0
#: The deadline of RecordMove, which a move awaits holding the index's lock.
_RECORD_MOVE_SECONDS = 30.0


class _Moves:
    """The lock a move holds while it reads, changes and writes the shard's
    index: this process's moves one at a time, and across the pods holding
    the shard at once -- a deposed holder still writing through a
    takeover's lapse and the new one (PO item 79) -- one writer of the
    index at a time, by a lock on `_INDEX_LOCK` held by its descriptor
    (`_raw._try_lock`), so neither writes over a move the other recorded.
    Waited for without blocking the loop, and at most `within` seconds."""

    def __init__(self) -> None:
        self._local = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    @contextlib.asynccontextmanager
    async def held(
        self, storage: Path | None, within: float | None = None
    ) -> AsyncIterator[None]:
        """The lock on `storage`'s index -- the storage the move named, never
        found again after an await -- taken within `within` seconds
        (`_MOVE_WAIT_SECONDS` where not given; 0: only where free now), else
        TimeoutError and nothing done."""
        if within is None:
            within = _MOVE_WAIT_SECONDS
        loop = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = loop
        elif self._loop is not loop:
            raise RuntimeError(
                "the plugin's moves are made on the loop it registered on, not another "
                "thread's: the archive's helpers are not thread-safe"
            )
        ends = loop.time() + within
        busy = TimeoutError(
            f"the shard's index of what moved is held by another move, here or in another "
            f"pod, past {within:g} s: nothing moved, and the next pass tries again"
        )
        fd = None
        try:
            if self._local.locked() and within <= 0:
                raise busy
            try:
                async with asyncio.timeout(max(within, 0.001)):
                    await self._local.acquire()
            except TimeoutError:
                raise busy from None
        except TimeoutError:
            if within > 0:
                log.warning("%s", busy)
            raise
        try:
            if storage is not None:
                try:
                    fd = await _lock_file(storage.joinpath(*_INDEX_LOCK.parts), ends, busy)
                except TimeoutError:
                    if within > 0:
                        log.warning("%s", busy)
                    raise
            yield
        finally:
            try:
                if fd is not None:
                    try:
                        _unlock(fd)
                    except OSError as failed:
                        # Closing it lets the lock go all the same; a move
                        # done is not turned into a failure here.
                        log.warning("the index's lock was let go by closing it: %s", failed)
                    finally:
                        os.close(fd)
            finally:
                self._local.release()


async def _lock_file(path: Path, ends: float, busy: TimeoutError) -> int:
    """`path` opened and locked by its descriptor, waited for while another
    holds it until the loop's time `ends`, then `busy` raised: its
    descriptor, closed to let it go."""
    path.parent.mkdir(parents=True, exist_ok=True)
    held = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    loop = asyncio.get_running_loop()
    try:
        wait = 0.005
        while not _try_lock(held):
            left = ends - loop.time()
            if left <= 0:
                raise busy
            await asyncio.sleep(min(wait, left))
            wait = min(wait * 2, 0.05)
        return held
    except BaseException:
        os.close(held)
        raise


async def _in_thread(work: Any, *args: Any) -> Any:
    """`work(*args)` on a worker thread, waited for to its end even when the
    move awaiting it is cancelled, so the index's lock is never let go while
    the thread still writes; the cancellation is raised after."""
    running = asyncio.ensure_future(asyncio.to_thread(work, *args))
    try:
        return await asyncio.shield(running)
    except asyncio.CancelledError:
        while not running.done():
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.wait({running})
        if not running.cancelled():
            running.exception()
        raise


class _Mover:
    """The plugin's moves of its raw records, through its sidecar."""

    def __init__(self, plugin: Plugin) -> None:
        self.plugin = plugin
        self.lock = _Moves()

    # What the plugin declared, and its admin set.

    def kind(self, record_kind: str) -> RecordKind:
        storage = self.plugin._storage
        declared = storage._kind(record_kind) if storage is not None else None
        if declared is None:
            raise ValueError(
                f"{record_kind!r} is not a kind of raw record this version declares "
                "(Storage(kinds=...))"
            )
        return declared

    def setting(self, name: str) -> Any:
        """A window setting as last delivered; refused before any was."""
        held = self.plugin._settings_now
        if held is None:
            raise RuntimeError(
                f"the settings have not arrived, so {name} is not known: a window's move "
                "names the window it was made under. Read plugin.settings() first"
            )
        return held.get(name)

    def window_rule(self, kind: RecordKind, chosen: str) -> str:
        """The rule a window's move carries, refused where the admin chose
        otherwise for the kind past its window."""
        past = self.setting(kind._past_window_setting)
        if past != chosen:
            raise ValueError(
                f"{kind._past_window_setting} is {past!r}: a record of {kind.name} past its "
                f"window is {past}, not {chosen}"
            )
        if chosen == "deleted":
            return f"{kind._past_window_setting} deleted"
        return f"{kind._window_setting} {self.setting(kind._window_setting)}"

    # Reporting.

    async def report(
        self, move: sidecar_pb2.RecordMoveRequest, for_caller: Caller | str | None
    ) -> None:
        """One move reported through the sidecar, before anything is removed
        (W4.13): as the plugin itself, or for the person it acts for."""
        from .client import _caller_metadata

        if not RECORD_MOVE_REQUEST_RULE_LENGTH.admits(len(move.rule)):
            raise ValueError(
                f"a rule is at most {RECORD_MOVE_REQUEST_RULE_LENGTH.most} characters"
            )
        metadata = _caller_metadata(for_caller) if for_caller is not None else ()
        await self.plugin._for_person(
            "RecordMove",
            self.plugin._stub.RecordMove(move, metadata=metadata, timeout=_RECORD_MOVE_SECONDS),
        )

    # The moves.

    async def archive(
        self,
        record_kind: str,
        unit: str,
        record_count: int,
        first_received_ns: int,
        last_received_ns: int,
    ) -> None:
        kind = self.kind(record_kind)
        unit = _own_unit(unit, strict=False)
        path = _unit_path(unit)
        _reported(_shard_prefix(), unit)
        _span(record_count, first_received_ns, last_received_ns)
        if not kind.archivable:
            raise ValueError(f"the kind {kind.name} is declared not archivable")
        archive = _archive()
        if archive is None:
            raise RuntimeError(
                "this instance is allowed no archive: its records past their window are kept"
            )
        storage = _storage()
        source = storage.joinpath(*path.parts)
        async with self.lock.held(storage):
            await self.return_due(storage)
            index = _Index(storage)
            units = index.read(held=True)
            held = units.get(unit)
            if held is not None and held.state in ("archived", "restored"):
                if source.exists():
                    # Archived and recorded before a restart removed it.
                    await _in_thread(_remove, source)
                    return
                raise ValueError(f"the unit {unit} is archived already")
            if not source.exists():
                raise FileNotFoundError(f"the unit {unit} is not in the plugin's storage")
            rule = self.window_rule(kind, "archived")
            most = _archive_most_bytes()
            if most:
                size = await _in_thread(_size, source)
                used = await _in_thread(_archive_used, units)
                if used + size > most:
                    raise RuntimeError(
                        f"the archive holds {used:,} of its {most:,} bytes "
                        f"({_ARCHIVE_MOST_BYTES}), and the unit {unit} ({size:,} bytes) would "
                        "take it past: it stays in storage, and no move is recorded"
                    )
            prefix = _shard_prefix()
            if prefix == "shard-0/" and await _in_thread(
                _archived_before_shards, archive, unit, source
            ):
                # Archived and reported by the instance as one pod, which
                # stopped before its index was written: as it was then.
                prefix = ""
            files = await _in_thread(_copy_out, archive, prefix + unit, source)
            moved = _Moved(
                record_kind=record_kind,
                unit=unit,
                record_count=record_count,
                first_received_ns=first_received_ns,
                last_received_ns=last_received_ns,
                state="archived",
                files=files,
                at_ns=_now_ns(),
                rule=rule,
                prefix=prefix,
            )
            try:
                await self.report(moved.move("archived", rule), None)
            except BaseException:
                # Not recorded, so not archived: the unit stays in storage.
                await _in_thread(_forget, archive, moved.named, files)
                raise
            units[unit] = moved
            index.write(units)
            await _in_thread(_remove, source)

    async def restore(self, record_kind: str, unit: str, for_caller: Caller | str) -> Path:
        self.kind(record_kind)
        unit = _own_unit(unit)
        _unit_path(unit)
        storage = _storage()
        target = storage.joinpath(*_RESTORED.parts, *PurePosixPath(unit).parts)
        async with self.lock.held(storage):
            await self.return_due(storage)
            index = _Index(storage)
            units = index.read(held=True)
            held = units.get(unit)
            if held is None or held.record_kind != record_kind or held.state == "deleted":
                raise ValueError(f"the unit {unit} of {record_kind} is not archived")
            if held.state == "restored" and target.exists():
                return target
            archive = _archive()
            if archive is None:
                raise RuntimeError(
                    "this instance is given no archive now: what it holds is kept, and "
                    "restorable once a deployment admin allows it again"
                )
            await _in_thread(_copy_back, archive, held, target)
            try:
                await self.report(held.move("restored"), for_caller)
            except BaseException:
                await _in_thread(_remove, target, storage)
                raise
            held.state, held.restored_at_ns = "restored", _now_ns()
            index.write(units)
            return target

    async def delete(
        self,
        record_kind: str,
        unit: str,
        record_count: int,
        first_received_ns: int,
        last_received_ns: int,
        for_caller: Caller | str | None,
    ) -> None:
        kind = self.kind(record_kind)
        unit = _own_unit(unit)
        path = _unit_path(unit)
        storage = _storage()
        async with self.lock.held(storage):
            await self.return_due(storage)
            index = _Index(storage)
            units = index.read(held=True)
            held = units.get(unit)
            if held is not None and held.state == "deleted":
                raise ValueError(f"the unit {unit} is deleted already")
            if held is not None:
                # From the archive: an admin's act, after the hold (requirement 9).
                if for_caller is None:
                    raise ValueError(
                        f"the unit {unit} is archived: deleting it is an admin's act, "
                        "for_caller the person"
                    )
                await self.report(held.move("deleted"), for_caller)
                archive = _archive()
                if archive is not None:
                    await _in_thread(_forget, archive, held.named, held.files)
                await _in_thread(
                    _remove, storage.joinpath(*_RESTORED.parts, *path.parts), storage
                )
                held.state, held.at_ns = "deleted", _now_ns()
                index.write(units)
                return
            source = storage.joinpath(*path.parts)
            if not source.exists():
                raise FileNotFoundError(f"the unit {unit} is not in the plugin's storage")
            _span(record_count, first_received_ns, last_received_ns)
            prefix = _shard_prefix()
            _reported(prefix, unit)
            rule = "" if for_caller is not None else self.window_rule(kind, "deleted")
            moved = _Moved(
                record_kind=record_kind,
                unit=unit,
                record_count=record_count,
                first_received_ns=first_received_ns,
                last_received_ns=last_received_ns,
                state="deleted",
                at_ns=_now_ns(),
                rule=rule,
                prefix=prefix,
            )
            await self.report(moved.move("deleted", rule), for_caller)
            units[unit] = moved
            index.write(units)
            await _in_thread(_remove, source)

    async def return_due(self, granted: Path | None) -> None:
        """Each restored unit past the restore period removed from the
        restore area of `granted`, the storage whose index's lock is held,
        its return reported first; the archive still holds it."""
        if granted is None or self.plugin._storage is None:
            return
        index = _Index(granted)
        units = index.read(held=True)
        due = _now_ns() - _RESTORE_DAYS * NANOS_PER_DAY
        for unit, held in units.items():
            if held.state != "restored" or held.restored_at_ns > due:
                continue
            try:
                await self.report(held.move("returned", _RESTORE_RULE), None)
            except Exception as failed:
                # Kept in the restore area, and tried again at the next move
                # or heartbeat: a return not recorded is not done.
                log.warning("the return of %s was not recorded: %s", unit, failed)
                continue
            target = granted.joinpath(*_RESTORED.parts, *PurePosixPath(unit).parts)
            await _in_thread(_remove, target, granted)
            held.state, held.restored_at_ns = "archived", 0
            index.write(units)

    def find(self, key: str) -> sidecar_pb2.RecordMoveRequest | None:
        folder, within = _shard_folder(key)
        if folder is None:
            return None
        held = _Index(folder).holding(within)
        if held is None:
            return None
        return held.move(held.state, held.rule if held.state in ("archived", "deleted") else "")


def _own_unit(unit: str, strict: bool = True) -> str:
    """A unit a move names, in this shard's storage: on an instance of
    shards, the shard's own prefix taken off, and another shard's unit
    refused, since only its own pod writes its storage (PO item 71). A
    restore or a deletion (`strict`) names a unit as the instance does, so
    one with no prefix is shard 0's, what the instance kept before it ran
    as shards; an archive's own unit may be named in its shard's storage."""
    if _serving is None or not _sharded():
        return unit
    shard, within = _split(unit)
    if shard is None:
        if strict and _serving[0] != 0:
            shard, within = 0, unit
        else:
            return unit
    if shard != _serving[0]:
        raise ValueError(f"the unit {unit} is shard {shard}'s: its own pod restores it")
    return within


def _archive_used(units: dict[str, _Moved]) -> int:
    """The bytes the instance's archive holds, as the indexes say: this
    shard's (`units`, as read), and on an instance of shards every other
    shard's, the bound being the instance's (W8.3). Another shard's index
    that cannot be read, tried twice, refuses the archive, never counted as
    holding nothing; one holding fields a newer SDK added is counted. The
    lock is the shard's, so two shards archiving at once may each count
    the other before its move: the bound can be passed by what they moved
    together, never by one alone."""
    used = sum(moved.archive_bytes for moved in units.values())
    granted = instance_storage_dir()
    if granted is None or _serving is None or not _sharded():
        return used
    for folder in sorted(granted.glob("shard-*")):
        shard, _ = _split(folder.name + "/")
        if shard is None or shard == _serving[0]:
            continue
        try:
            held = _Index(folder).read(lenient=True)
            used += sum(moved.archive_bytes for moved in held.values())
        except (OSError, ValueError, TypeError, AttributeError) as unread:
            raise RuntimeError(
                f"shard {shard}'s archive index could not be read ({unread}): the archive's "
                f"bound ({_ARCHIVE_MOST_BYTES}) is the instance's, so nothing is archived "
                "until it can be counted, and the unit stays in storage"
            ) from unread
    return used


def _archived_before_shards(archive: _Objects, unit: str, source: Path) -> bool:
    """Whether the archive holds a unit's first file under its name with no
    prefix, as the instance of one pod archived it before it ran as shards."""
    for within, _ in _files(source):
        return archive.landed(_object_key(unit, within)) is not None
    return False


def _size(source: Path) -> int:
    """A unit's bytes in storage: its files' sizes."""
    return sum(path.stat().st_size for _, path in _files(source))


def _copy_out(archive: _Objects, unit: str, source: Path) -> dict[str, list[Any]]:
    """The unit written to the archive, each file checked to have landed;
    every file it wrote taken back where one did not."""
    files: dict[str, list[Any]] = {}
    try:
        for within, path in _files(source):
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            key = _object_key(unit, within)
            files[within] = [len(data), digest]
            archive.put(key, data)
            if archive.landed(key) != (len(data), digest):
                raise OSError(f"{key} did not land in the archive whole")
    except BaseException:
        _forget(archive, unit, files)
        raise
    if not files:
        raise ValueError(f"the unit {unit} holds no file")
    return files


def _copy_back(archive: _Objects, held: _Moved, target: Path) -> None:
    """The unit copied from the archive to the restore area, each file
    checked against what was archived."""
    staging = target.parent / f".part-{target.name}"
    _remove(staging, target.parent)
    for within, (size, digest) in held.files.items():
        data = archive.get(_object_key(held.named, within))
        if (len(data), hashlib.sha256(data).hexdigest()) != (size, digest):
            _remove(staging, target.parent)
            raise OSError(f"{held.unit} did not come back from the archive as it was archived")
        out = staging.joinpath(*PurePosixPath(within).parts) if within else staging
        out.parent.mkdir(parents=True, exist_ok=True)
        _write_whole(out, data)
    _remove(target, target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, target)


def _forget(archive: _Objects, unit: str, files: dict[str, list[Any]]) -> None:
    for within in files:
        with contextlib.suppress(Exception):
            archive.delete(_object_key(unit, within))


def _remove(path: Path, root: Path | None = None) -> None:
    """A file or directory removed, and the empty directories above it up to
    `root` where one is given: the helpers' own areas, never the plugin's."""
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)
    if root is not None:
        _prune(path.parent, root)


def _with_bytes(
    spans: tuple[sidecar_pb2.StoredSpan, ...], storage: Any
) -> tuple[sidecar_pb2.StoredSpan, ...]:
    """What the plugin set, each kind given the bytes it uses of the archive
    from the SDK's index (`StoredSpan.bytes`, named 2026-10-07), and a kind
    the plugin left out that the archive holds some of added with no records
    in storage. The plugin's own `bytes` is not taken: the index is what
    knows the archive. As set, where nothing has moved."""
    granted = storage_dir()
    if granted is None or storage is None or not storage.kinds:
        return spans
    try:
        used = _Index(granted).archive_bytes()
    except (OSError, ValueError, TypeError, AttributeError) as unread:
        log.warning("the archive's index could not be read for the heartbeat: %s", unread)
        return spans
    if not used and not any(span.bytes for span in spans):
        return spans
    given = []
    for span in spans:
        filled = sidecar_pb2.StoredSpan()
        filled.CopyFrom(span)
        filled.bytes = used.get(span.record_kind, 0)
        given.append(filled)
    named = {span.record_kind for span in spans}
    for kind in storage.kinds:
        if kind.name not in named and used.get(kind.name):
            given.append(sidecar_pb2.StoredSpan(record_kind=kind.name, bytes=used[kind.name]))
    return tuple(given)


def _stored(spans: Any, storage: Any) -> tuple[sidecar_pb2.StoredSpan, ...]:
    """What the plugin says each kind holds in storage, refused here as the
    sidecar refuses it: a kind not declared, a kind twice, more than 16."""
    from .bounds import HEARTBEAT_REQUEST_STORED_COUNT

    given = tuple(spans)
    if not HEARTBEAT_REQUEST_STORED_COUNT.admits(len(given)):
        raise ValueError(f"at most {HEARTBEAT_REQUEST_STORED_COUNT.most} kinds stored")
    seen: set[str] = set()
    for n, span in enumerate(given):
        if not isinstance(span, sidecar_pb2.StoredSpan):
            raise TypeError(f"stored[{n}] is a {type(span).__name__}, not a StoredSpan")
        if storage is None or storage._kind(span.record_kind) is None:
            raise ValueError(f"stored[{n}].record_kind {span.record_kind!r} is not declared")
        if span.record_kind in seen:
            raise ValueError(f"stored names {span.record_kind} twice")
        seen.add(span.record_kind)
        if not span.record_count and (span.first_received_ns or span.last_received_ns):
            raise ValueError(f"stored[{n}] holds no record, and so no span")
        if span.record_count and (
            span.last_received_ns < span.first_received_ns or span.first_received_ns <= 0
        ):
            raise ValueError(f"stored[{n}]'s span is not from the first record to the last")
    return given


# ── The restore route (the names' choice b, ruled 2026-10-06) ────────────────

#: The write route every edge plugin's host offers, derived as a tool.
_RESTORE_PATH = "/archive/restore"


@dataclasses.dataclass(frozen=True)
class _Restore:
    record_kind: str = dataclasses.field(
        metadata={"description": "The kind of raw record.", "max_length": 40}
    )
    unit: str = dataclasses.field(
        metadata={
            "description": "The archived unit, as the plugin's page lists it.",
            "max_length": 512,
        }
    )


def _restore_route(pages: Pages, roles: tuple[str, ...]) -> None:
    """`POST /archive/restore` on the plugin's host, for a person at write
    on one of its edge roles: the unit copied back to the restore area, its
    restore reported for them. Declared once."""
    if (_RESTORE_PATH, "POST") in pages._routes:
        return
    from .errors import CallFailed, NotGranted
    from .pages import Response

    async def restore_unit(request: Any) -> Response:
        """Restore an archived unit of this plugin's raw records, readable on
        its pages for seven days, for the person asking."""
        asked = request.params
        if asked is None:
            pages.refuse("say the kind and the unit to restore", "record_kind", "unit")
        try:
            await request.plugin.restore_unit(
                asked.record_kind, asked.unit, for_caller=request.caller
            )
        except (ValueError, FileNotFoundError) as refused:
            at = "record_kind" if "kind" in str(refused) else "unit"
            pages.refuse(str(refused), at)
        except NotGranted as refused:
            pages.refuse(refused.reason, reason="not_granted")
        except (CallFailed, RuntimeError, OSError) as failed:
            pages.refuse(str(failed), reason="not_restored")
        data = {"record_kind": asked.record_kind, "unit": asked.unit, "outcome": "restored"}
        if request.tool_name:
            return pages.answer("", data)
        back = request.headers.get("referer", "") or "/"
        return Response("", 303, headers=(("location", urllib.parse.urlsplit(back).path),))

    pages.route(
        _RESTORE_PATH, levels=["write"], roles=roles, methods=["POST"], params=_Restore
    )(restore_unit)
