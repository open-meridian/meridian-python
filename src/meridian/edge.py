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

What each kind holds in storage is the plugin's to say, as its figures are
(`plugin.stored`, one `StoredSpan` per kind), on every heartbeat; the bytes
each kind uses of the archive (`StoredSpan.bytes`) are the SDK's, summed
from its index on every heartbeat, and the deployment's Summary draws them
against the bound. Every edge
plugin with pages offers `POST /archive/restore`, which the SDK declares on
its host and the deployment derives as a tool: the kind and the unit, for a
person at `write`, the person read from the claims.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
import urllib.parse
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Protocol

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
            unit=self.unit,
            record_count=self.record_count,
            first_received_ns=self.first_received_ns,
            last_received_ns=self.last_received_ns,
            outcome=_OUTCOMES[outcome],
            rule=rule,
        )


class _Index:
    """What moved, kept in the instance's storage, so a unit is found again
    after a restart and a record's key resolves to its unit."""

    def __init__(self, storage: Path) -> None:
        self.storage = storage
        self.path = storage.joinpath(*_INDEX.parts)

    def read(self) -> dict[str, _Moved]:
        if not self.path.is_file():
            return {}
        held = json.loads(self.path.read_text())
        return {unit: _Moved(**entry) for unit, entry in held.get("units", {}).items()}

    def write(self, units: dict[str, _Moved]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {"units": {unit: dataclasses.asdict(moved) for unit, moved in units.items()}}
        _write_whole(self.path, json.dumps(body, sort_keys=True, indent=1).encode())

    def archive_bytes(self) -> dict[str, int]:
        """The bytes each kind uses of the archive, as this index holds it."""
        used: dict[str, int] = {}
        for moved in self.read().values():
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


class _Mover:
    """The plugin's moves of its raw records, through its sidecar."""

    def __init__(self, plugin: Plugin) -> None:
        self.plugin = plugin
        self.lock = asyncio.Lock()

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
            "RecordMove", self.plugin._stub.RecordMove(move, metadata=metadata)
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
        path = _unit_path(unit)
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
        async with self.lock:
            await self.return_due()
            index = _Index(storage)
            units = index.read()
            held = units.get(unit)
            if held is not None and held.state in ("archived", "restored"):
                if source.exists():
                    # Archived and recorded before a restart removed it.
                    await asyncio.to_thread(_remove, source)
                    return
                raise ValueError(f"the unit {unit} is archived already")
            if not source.exists():
                raise FileNotFoundError(f"the unit {unit} is not in the plugin's storage")
            rule = self.window_rule(kind, "archived")
            most = _archive_most_bytes()
            if most:
                size = await asyncio.to_thread(_size, source)
                used = sum(moved.archive_bytes for moved in units.values())
                if used + size > most:
                    raise RuntimeError(
                        f"the archive holds {used:,} of its {most:,} bytes "
                        f"({_ARCHIVE_MOST_BYTES}), and the unit {unit} ({size:,} bytes) would "
                        "take it past: it stays in storage, and no move is recorded"
                    )
            files = await asyncio.to_thread(_copy_out, archive, unit, source)
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
            )
            try:
                await self.report(moved.move("archived", rule), None)
            except BaseException:
                # Not recorded, so not archived: the unit stays in storage.
                await asyncio.to_thread(_forget, archive, unit, files)
                raise
            units[unit] = moved
            index.write(units)
            await asyncio.to_thread(_remove, source)

    async def restore(self, record_kind: str, unit: str, for_caller: Caller | str) -> Path:
        self.kind(record_kind)
        _unit_path(unit)
        storage = _storage()
        target = storage.joinpath(*_RESTORED.parts, *PurePosixPath(unit).parts)
        async with self.lock:
            await self.return_due()
            index = _Index(storage)
            units = index.read()
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
            await asyncio.to_thread(_copy_back, archive, held, target)
            try:
                await self.report(held.move("restored"), for_caller)
            except BaseException:
                await asyncio.to_thread(_remove, target, storage)
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
        path = _unit_path(unit)
        storage = _storage()
        async with self.lock:
            await self.return_due()
            index = _Index(storage)
            units = index.read()
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
                    await asyncio.to_thread(_forget, archive, unit, held.files)
                await asyncio.to_thread(
                    _remove, storage.joinpath(*_RESTORED.parts, *path.parts), storage
                )
                held.state, held.at_ns = "deleted", _now_ns()
                index.write(units)
                return
            source = storage.joinpath(*path.parts)
            if not source.exists():
                raise FileNotFoundError(f"the unit {unit} is not in the plugin's storage")
            _span(record_count, first_received_ns, last_received_ns)
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
            )
            await self.report(moved.move("deleted", rule), for_caller)
            units[unit] = moved
            index.write(units)
            await asyncio.to_thread(_remove, source)

    async def return_due(self) -> None:
        """Each restored unit past the restore period removed from the
        restore area, its return reported first; the archive still holds it."""
        granted = storage_dir()
        if granted is None or self.plugin._storage is None:
            return
        index = _Index(granted)
        units = index.read()
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
            await asyncio.to_thread(_remove, target, granted)
            held.state, held.restored_at_ns = "archived", 0
            index.write(units)

    def find(self, key: str) -> sidecar_pb2.RecordMoveRequest | None:
        granted = storage_dir()
        if granted is None:
            return None
        held = _Index(granted).holding(key)
        if held is None:
            return None
        return held.move(held.state, held.rule if held.state in ("archived", "deleted") else "")


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
        data = archive.get(_object_key(held.unit, within))
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
    except (OSError, ValueError, TypeError) as unread:
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
