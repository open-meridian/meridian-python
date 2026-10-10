"""What a version declares beside its roles (W8.1, W4.1, contract v11).

spec/vendor-differences-have-a-place-in-the-contract, requirements 16, 19 and
30, Q6 and Q15: the names of the secret settings it will ask for, so an admin
knows before launch what credentials it needs; what it receives from its
vendor and does not carry, by name only, per role, each with why -- the
evidence the common model may need to grow; and, for a plugin holding an edge
role, the storage it asks for and how long it keeps its raw records
(decisions/028). Nothing about what it supports: its roles say that. Never a
value, an account or an identifier.

Built from the plugin's code, once, and used twice: `connect(declaration=...)`
sends it at registration, and `meridian plugin upload` reads the same one
from the built image, naming it in pyproject.toml's `[tool.meridian]` as
`declaration = "my_plugin.declaration:DECLARATION"`, and running
`meridian-declaration my_plugin.declaration:DECLARATION` there, which prints
it as JSON.

    DECLARATION = Declaration(
        settings=SETTINGS,
        not_carried=[NotCarried("custody", "myvendor:position", "open_pnl",
                                "no_contract_meaning")],
        storage=Storage(retention_days=2555),
    )

From contract v16 a plugin at the edge also declares the kinds of raw record
it keeps (spec/an-edge-plugins-older-records-move-to-the-archive, W4.1):
each a `RecordKind` with the name its code and settings use, the label a
person reads, its default window in days, and whether a unit of it can be
archived (a FIX session's state, read and updated in place, cannot):

    storage=Storage(kinds=[
        RecordKind("activity", "Reported activity", window_days=2555, archivable=True),
        RecordKind("responses", "Raw responses", window_days=30, archivable=True),
    ])

For each kind the SDK declares two settings, the same for every edge plugin
(W6.11): `<kind>_window_days`, its window, defaulting to the kind's, and
`<kind>_past_window`, what is done with a record past it -- `archived`,
`kept` or `deleted` -- defaulting to `archived` where the deployment gives
the instance an archive and `kept` otherwise. Those names are the SDK's: a
plugin declaring a setting of one of them itself is refused here, as the
sidecar refuses its registration. A plugin declaring no kinds keeps the
behaviour before v16 under `retention_days`.

From contract v18 a `dgm` declares its catalogue (W8.1, W10.4; spec/the-lake,
"The catalogue"): each dataset it serves the lake, by its key, with its
vendor, the data types and optional fields it fills by their dictionary
entries, how its rows can arrive, its cadence and history, the terms its
vendor's standard terms impose, the day a daily value's business date is in,
and the venue it is, where it is one venue's:

    catalogue=[
        DatasetDeclaration(
            key="daily",
            vendor="Coinbase",
            data_types=["meridian.v1.Price", "meridian.v1.Bar"],
            modes=["pull", "push"],
            cadence=86_400,
            licence_default=DatasetLicence(kept=True, personal_use=True),
            day_time_zone="Etc/UTC",
            venue_id="VEN-01JA0000000000000CBEXC",
        ),
    ]

Its rows then name the dataset as the instance, a colon and the key
(`coinbase-1:daily`). The catalogue is the lake's, not a declaration of
support, and only a version holding `dgm` declares one.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from .bounds import (
    CATALOGUE_DATASETS_COUNT,
    DATASET_DECLARATION_AGGREGATOR_LENGTH,
    DATASET_DECLARATION_DATA_TYPES_COUNT,
    DATASET_DECLARATION_DAY_END_MINUTE_RANGE,
    DATASET_DECLARATION_DAY_TIME_ZONE_LENGTH,
    DATASET_DECLARATION_KEY_LENGTH,
    DATASET_DECLARATION_MODES_COUNT,
    DATASET_DECLARATION_VENDOR_LENGTH,
    DATASET_LICENCE_DEFAULT_FIELDS_COUNT,
    DATASET_LICENCE_RETENTION_DAYS_RANGE,
    NOT_CARRIED_NAME_LENGTH,
    NOT_CARRIED_ROLE_LENGTH,
    NOT_CARRIED_SCHEME_LENGTH,
    PLUGIN_DECLARATION_NOT_CARRIED_COUNT,
    RAW_RECORD_KIND_LABEL_LENGTH,
    RAW_RECORD_KIND_NAME_LENGTH,
    RAW_RECORD_KIND_WINDOW_DAYS_RANGE,
    STORAGE_DECLARATION_RECORD_KINDS_COUNT,
    STORAGE_DECLARATION_RETENTION_DAYS_RANGE,
)
from .v1 import sidecar_pb2

#: The roles at the edge, which alone may own storage for their raw records
#: (decisions/028).
EDGE_ROLES = frozenset(
    {"ccm", "custody", "dgm", "match", "reporting", "servicing", "settlement"}
)

Reason = Literal["no_contract_meaning", "not_converted"]
_REASONS: dict[str, int] = {
    "no_contract_meaning": sidecar_pb2.NOT_CARRIED_REASON_NO_CONTRACT_MEANING,
    "not_converted": sidecar_pb2.NOT_CARRIED_REASON_NOT_CONVERTED,
}


@dataclass(frozen=True)
class NotCarried:
    """One vendor field, or one code of a vendor's code set, the plugin
    receives in `role` and does not carry: `no_contract_meaning`, a place the
    model may grow, or `not_converted`, a meaning the contract has that the
    plugin does not yet convert to."""

    role: str
    scheme: str
    name: str
    reason: Reason

    def __post_init__(self) -> None:
        for part, text, bound in (
            ("role", self.role, NOT_CARRIED_ROLE_LENGTH),
            ("scheme", self.scheme, NOT_CARRIED_SCHEME_LENGTH),
            ("name", self.name, NOT_CARRIED_NAME_LENGTH),
        ):
            if not bound.least <= len(text) <= bound.most:
                raise ValueError(
                    f"a name not carried's {part} is {bound.least} to {bound.most} characters"
                )
        if self.reason not in _REASONS:
            raise ValueError(
                f"{self.reason!r} is not a reason: no_contract_meaning or not_converted"
            )


#: A kind's name: lowercase letters, digits and underscores, beginning with a
#: letter (RawRecordKind.name).
_KIND_NAME = re.compile(r"[a-z][a-z0-9_]*")

#: What is done with a record past its kind's window (W6.11): moved to the
#: archive, left in storage, or deleted, which only an admin chooses.
_PAST_WINDOW = ("archived", "kept", "deleted")


@dataclass(frozen=True)
class RecordKind:
    """One kind of raw record a plugin at the edge keeps (contract v16): the
    name its code and settings use, the label a person reads, its default
    window in days from when a record was received, and whether a unit of it
    can be moved to an archive."""

    name: str
    label: str
    window_days: int
    archivable: bool = True

    def __post_init__(self) -> None:
        if not RAW_RECORD_KIND_NAME_LENGTH.admits(len(self.name)) or not _KIND_NAME.fullmatch(
            self.name
        ):
            raise ValueError(
                f"a kind's name is {self.name!r}: 1 to {RAW_RECORD_KIND_NAME_LENGTH.most} "
                "lowercase letters, digits and underscores, beginning with a letter"
            )
        if not RAW_RECORD_KIND_LABEL_LENGTH.admits(len(self.label)):
            raise ValueError(
                f"the kind {self.name}'s label is 1 to {RAW_RECORD_KIND_LABEL_LENGTH.most} "
                "characters"
            )
        bound = RAW_RECORD_KIND_WINDOW_DAYS_RANGE
        if not bound.least <= self.window_days <= bound.most:
            raise ValueError(
                f"the kind {self.name}'s window_days is {bound.least} to {bound.most}"
            )

    @property
    def _window_setting(self) -> str:
        """The name of its window's setting, which the SDK declares."""
        return f"{self.name}_window_days"

    @property
    def _past_window_setting(self) -> str:
        """The name of the setting saying what is done past its window."""
        return f"{self.name}_past_window"


@dataclass(frozen=True)
class Storage:
    """The storage a plugin at the edge asks for, for its raw records, and
    how many days it keeps one: the reach of a backfill.

    From contract v16, the kinds of raw record it keeps (`kinds`), each with
    its own window; `retention_days` is then the longest of their windows
    unless given, and a version declaring no kinds keeps one under it."""

    retention_days: int = 0
    kinds: Sequence[RecordKind] = ()

    def __post_init__(self) -> None:
        kinds = tuple(self.kinds)
        object.__setattr__(self, "kinds", kinds)
        if not STORAGE_DECLARATION_RECORD_KINDS_COUNT.admits(len(kinds)):
            raise ValueError(
                f"at most {STORAGE_DECLARATION_RECORD_KINDS_COUNT.most} kinds of raw record"
            )
        names = [kind.name for kind in kinds]
        twice = next((name for name in names if names.count(name) > 1), None)
        if twice is not None:
            raise ValueError(f"the kind {twice} is declared twice")
        if self.retention_days == 0 and kinds:
            object.__setattr__(self, "retention_days", max(kind.window_days for kind in kinds))
        bound = STORAGE_DECLARATION_RETENTION_DAYS_RANGE
        if not bound.least <= self.retention_days <= bound.most:
            raise ValueError(f"retention_days is {bound.least} to {bound.most}")

    def _to_json(self) -> dict[str, Any]:
        """As an upload carries it: the kinds only where it declares them,
        so a version declaring none uploads what it did before v16."""
        out: dict[str, Any] = {"retention_days": self.retention_days}
        if self.kinds:
            out["record_kinds"] = [
                {
                    "name": kind.name,
                    "label": kind.label,
                    "window_days": kind.window_days,
                    "archivable": kind.archivable,
                }
                for kind in self.kinds
            ]
        return out

    def _kind(self, name: str) -> RecordKind | None:
        """The kind declared by `name`, or None."""
        return next((kind for kind in self.kinds if kind.name == name), None)

    @property
    def _reserved(self) -> frozenset[str]:
        """The settings' names the SDK declares for the kinds, and no other
        setting may take."""
        return frozenset(
            name
            for kind in self.kinds
            for name in (kind._window_setting, kind._past_window_setting)
        )


#: A dataset's key: lowercase letters, digits and underscores, beginning with
#: a letter (DatasetDeclaration.key).
_DATASET_KEY = re.compile(r"[a-z][a-z0-9_]*")

#: The largest whole number a uint32 field carries.
_UINT32 = 2**32 - 1


def _entry_named(name: str) -> bool:
    """Whether `name` is a dictionary entry, or a message the dictionary has
    entries for: a data type by its message, a field by its entry."""
    from .dictionary import _by_name

    entries = _by_name()
    return name in entries or any(held.startswith(f"{name}.") for held in entries)


def _zone_refused(zone: str) -> bool:
    """Whether `zone` is no IANA time zone, where this machine has the zone
    database to tell; the sidecar refuses one all the same."""
    import zoneinfo

    if not zone or not zoneinfo.available_timezones():
        return False
    try:
        zoneinfo.ZoneInfo(zone)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return True
    return False


@dataclass(frozen=True, kw_only=True)
class DatasetLicence:
    """The terms a dataset's vendor's standard terms impose, as its catalogue
    declares them (contract v18; spec/the-lake, Q8): what the deployment's
    licence confirms or replaces. Whether the lake may keep its rows (false
    serves them, not kept), for how many days (0 for no limit set), whether
    derived data may be made and shown, the fields readable by default by
    their dictionary entries (none for every field), and whether its terms
    are one person's. Records what the vendor's terms say, never whether a
    deployment meets them."""

    kept: bool = False
    retention_days: int = 0
    derived_use: bool = False
    display: bool = False
    default_fields: Sequence[str] = ()
    personal_use: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_fields", tuple(self.default_fields))
        bound = DATASET_LICENCE_RETENTION_DAYS_RANGE
        if not bound.admits(self.retention_days):
            raise ValueError(f"a licence's retention_days is {bound.least} to {bound.most}")
        if not DATASET_LICENCE_DEFAULT_FIELDS_COUNT.admits(len(self.default_fields)):
            raise ValueError(
                f"a licence names at most {DATASET_LICENCE_DEFAULT_FIELDS_COUNT.most} "
                "default fields"
            )
        unknown = next((f for f in self.default_fields if not _entry_named(f)), None)
        if unknown is not None:
            raise ValueError(
                f"a licence's default field {unknown!r} is no entry of the data dictionary"
            )

    def _wire(self) -> sidecar_pb2.DatasetLicence:
        return sidecar_pb2.DatasetLicence(
            kept=self.kept,
            retention_days=self.retention_days,
            derived_use=self.derived_use,
            display=self.display,
            default_fields=list(self.default_fields),
            personal_use=self.personal_use,
        )

    def _to_json(self) -> dict[str, Any]:
        return {
            "kept": self.kept,
            "retention_days": self.retention_days,
            "derived_use": self.derived_use,
            "display": self.display,
            "default_fields": list(self.default_fields),
            "personal_use": self.personal_use,
        }


@dataclass(frozen=True, kw_only=True)
class DatasetDeclaration:
    """One dataset a `dgm` serves the lake (contract v18): its identity in a
    deployment is the instance and its key (spec/the-lake, Q19).

    `data_types` are the lake's data types it serves and the optional fields
    it fills, each by its dictionary entry (`meridian.v1.Price`,
    `meridian.v1.Bar.vwap`); `modes` how its rows can arrive -- pull, push or
    stream, each once; `cadence` the seconds between its source's updates (0
    for a dataset updated only when asked) and `history` the days its source
    reaches back (0 for none stated). `day_time_zone` and `day_end_minute`
    are the day a daily value's business date is in: an IANA zone and the
    minute after local midnight the day ends, which say which candle or
    session counts as the date and when it is final. `venue_id` is the venue
    the dataset is, the venue master's ID, empty for a dataset that is not
    one venue's, which is the consolidated view."""

    key: str
    vendor: str
    data_types: Sequence[str]
    modes: Sequence[str | int]
    aggregator: str = ""
    cadence: int = 0
    history: int = 0
    licence_default: DatasetLicence | None = None
    day_time_zone: str = ""
    day_end_minute: int = 0
    venue_id: str = ""

    def __post_init__(self) -> None:
        from .operations import _enum

        object.__setattr__(self, "data_types", tuple(self.data_types))
        modes = tuple(
            _enum(sidecar_pb2.ObservationMode, mode, f"the dataset {self.key}'s modes")
            for mode in self.modes
        )
        object.__setattr__(self, "modes", modes)
        at = f"the dataset {self.key!r}"
        if not DATASET_DECLARATION_KEY_LENGTH.admits(
            len(self.key)
        ) or not _DATASET_KEY.fullmatch(self.key):
            raise ValueError(
                f"{at}: a key is 1 to {DATASET_DECLARATION_KEY_LENGTH.most} lowercase letters, "
                "digits and underscores, beginning with a letter"
            )
        if not DATASET_DECLARATION_VENDOR_LENGTH.admits(len(self.vendor)):
            raise ValueError(
                f"{at}'s vendor is 1 to {DATASET_DECLARATION_VENDOR_LENGTH.most} characters"
            )
        if not DATASET_DECLARATION_AGGREGATOR_LENGTH.admits(len(self.aggregator)):
            raise ValueError(
                f"{at}'s aggregator is at most {DATASET_DECLARATION_AGGREGATOR_LENGTH.most} "
                "characters"
            )
        if not DATASET_DECLARATION_DATA_TYPES_COUNT.admits(len(self.data_types)):
            raise ValueError(
                f"{at} names 1 to {DATASET_DECLARATION_DATA_TYPES_COUNT.most} data types "
                "and fields"
            )
        for named in self.data_types:
            if self.data_types.count(named) > 1:
                raise ValueError(f"{at} names {named} twice")
            if not _entry_named(named):
                raise ValueError(
                    f"{at} names {named!r}, which is no data type or field of the data "
                    "dictionary: a type by its message (meridian.v1.Price), a field by its "
                    "entry (meridian.v1.Bar.vwap)"
                )
        if not DATASET_DECLARATION_MODES_COUNT.admits(len(modes)) or not all(modes):
            raise ValueError(f"{at} arrives by 1 to 3 modes: pull, push or stream")
        if len(set(modes)) != len(modes):
            raise ValueError(f"{at} names a mode twice; each once")
        for name, value in (("cadence", self.cadence), ("history", self.history)):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= _UINT32
            ):
                raise ValueError(f"{at}'s {name} is a whole number, 0 or more")
        if not DATASET_DECLARATION_DAY_TIME_ZONE_LENGTH.admits(len(self.day_time_zone)):
            raise ValueError(f"{at}'s day_time_zone is an IANA zone, at most 64 characters")
        if _zone_refused(self.day_time_zone):
            raise ValueError(
                f"{at}'s day_time_zone {self.day_time_zone!r} is no IANA time zone "
                "(Etc/UTC, America/New_York)"
            )
        bound = DATASET_DECLARATION_DAY_END_MINUTE_RANGE
        if not bound.admits(self.day_end_minute):
            raise ValueError(
                f"{at}'s day_end_minute is {bound.least} to {bound.most}: minutes after local "
                "midnight"
            )
        if self.venue_id and not self.venue_id.startswith("VEN-"):
            raise ValueError(
                f"{at}'s venue_id {self.venue_id!r} is no venue master ID (VEN-): a MIC or "
                "a vendor's code is resolved to one first (resolve_venue)"
            )

    def _wire(self) -> sidecar_pb2.DatasetDeclaration:
        return sidecar_pb2.DatasetDeclaration(
            key=self.key,
            vendor=self.vendor,
            aggregator=self.aggregator,
            data_types=list(self.data_types),
            modes=list(self.modes),  # type: ignore[arg-type]
            cadence=self.cadence,
            history=self.history,
            licence_default=(
                None if self.licence_default is None else self.licence_default._wire()
            ),
            day_time_zone=self.day_time_zone,
            day_end_minute=self.day_end_minute,
            venue_id=self.venue_id,
        )

    def _to_json(self) -> dict[str, Any]:
        """As an upload carries it: each mode in its word, as a reason not
        carried is."""
        words = {
            value: name.removeprefix("OBSERVATION_MODE_").lower()
            for name, value in sidecar_pb2.ObservationMode.items()
        }
        return {
            "key": self.key,
            "vendor": self.vendor,
            "aggregator": self.aggregator,
            "data_types": list(self.data_types),
            "modes": [words[int(mode)] for mode in self.modes],
            "cadence": self.cadence,
            "history": self.history,
            "licence_default": (
                None if self.licence_default is None else self.licence_default._to_json()
            ),
            "day_time_zone": self.day_time_zone,
            "day_end_minute": self.day_end_minute,
            "venue_id": self.venue_id,
        }


@dataclass(frozen=True)
class Declaration:
    """A version's declaration. `settings` are the ones it declares at
    registration (`meridian.Setting`), whose secret ones' names it carries.
    From contract v18 a `dgm`'s `catalogue`: the datasets it serves the lake."""

    settings: Sequence[Any] = ()
    not_carried: Sequence[NotCarried] = field(default=())
    storage: Storage | None = None
    catalogue: Sequence[DatasetDeclaration] = ()

    def __post_init__(self) -> None:
        if len(self.not_carried) > PLUGIN_DECLARATION_NOT_CARRIED_COUNT.most:
            raise ValueError(
                f"at most {PLUGIN_DECLARATION_NOT_CARRIED_COUNT.most} names not carried"
            )
        catalogue = tuple(self.catalogue)
        object.__setattr__(self, "catalogue", catalogue)
        if not CATALOGUE_DATASETS_COUNT.admits(len(catalogue)):
            raise ValueError(
                f"a catalogue holds at most {CATALOGUE_DATASETS_COUNT.most} datasets"
            )
        keys = [dataset.key for dataset in catalogue]
        twice = next((key for key in keys if keys.count(key) > 1), None)
        if twice is not None:
            raise ValueError(f"the dataset {twice} is declared twice; each key once")
        reserved = self.storage._reserved if self.storage is not None else frozenset()
        taken = next(
            (setting.name for setting in self.settings if setting.name in reserved), None
        )
        if taken is not None:
            raise ValueError(
                f"the setting {taken} is named as a declared kind's window setting, which "
                "the SDK declares; name it otherwise"
            )

    def _window_settings(self, archive: bool, roles: Sequence[str] = ()) -> list[Any]:
        """The two settings the SDK declares for each kind (W6.11): its
        window, and what is done past it, the same three choices for every
        kind -- the deployment refuses `archived` for a kind not archivable
        or an instance allowed no archive -- `archived` by default where the
        instance is given an archive and the kind is archivable, `kept`
        otherwise, never `deleted` unless an admin chooses it. `roles` the
        edge roles they serve, on a plugin naming roles."""
        from .client import Choice, Setting

        if self.storage is None:
            return []
        made: list[Any] = []
        for kind in self.storage.kinds:
            choices = [
                Choice("archived", "Archived", "Moved to the archive, and restorable."),
                Choice("kept", "Kept", "Left in this plugin's storage."),
                Choice("deleted", "Deleted", "Deleted, never inside the deployment's hold."),
            ]
            made.append(
                Setting(
                    kind._window_setting,
                    kind=int,
                    label=f"{kind.label}: window",
                    default=kind.window_days,
                    unit="days",
                    description=(
                        f"How long a record of {kind.label.lower()} stays in this plugin's "
                        "storage, from when it was received. Never below the deployment's "
                        "hold."
                    ),
                    roles=tuple(roles),
                )
            )
            made.append(
                Setting(
                    kind._past_window_setting,
                    label=f"{kind.label}: past the window",
                    default="archived" if archive and kind.archivable else "kept",
                    choices=tuple(choices),
                    description=f"What is done with a record of {kind.label.lower()} past "
                    "its window.",
                    roles=tuple(roles),
                )
            )
        return made

    @property
    def secret_settings(self) -> list[str]:
        """The names of the secret settings, in their order."""
        return [setting.name for setting in self.settings if getattr(setting, "secret", False)]

    def refused_for(self, roles: Sequence[str]) -> str | None:
        """Why this declaration cannot stand for a version holding `roles`,
        as `meridian plugin check` and the conductor say it, or None."""
        for held in self.not_carried:
            if held.role not in roles:
                return (
                    f"a name not carried is declared in {held.role}, which is not a role held"
                )
        if self.storage is not None and not EDGE_ROLES.intersection(roles):
            return (
                "storage is asked for by a plugin holding no edge role; only "
                + ", ".join(sorted(EDGE_ROLES))
                + " own storage (decisions/028)"
            )
        if self.catalogue and "dgm" not in roles:
            return (
                "a catalogue is declared by a plugin not holding dgm; "
                "only a dgm serves the lake"
            )
        return None

    def to_wire(self) -> sidecar_pb2.PluginDeclaration:
        """As registration carries it."""
        return sidecar_pb2.PluginDeclaration(
            secret_settings=self.secret_settings,
            not_carried=[
                sidecar_pb2.NotCarried(
                    role=held.role,
                    scheme=held.scheme,
                    name=held.name,
                    reason=_REASONS[held.reason],  # type: ignore[arg-type]
                )
                for held in self.not_carried
            ],
            storage=(
                None
                if self.storage is None
                else sidecar_pb2.StorageDeclaration(
                    retention_days=self.storage.retention_days,
                    record_kinds=[
                        sidecar_pb2.RawRecordKind(
                            name=kind.name,
                            label=kind.label,
                            window_days=kind.window_days,
                            archivable=kind.archivable,
                        )
                        for kind in self.storage.kinds
                    ],
                )
            ),
            catalogue=(
                sidecar_pb2.Catalogue(datasets=[dataset._wire() for dataset in self.catalogue])
                if self.catalogue
                else None
            ),
        )

    def to_json(self) -> dict[str, Any]:
        """As an upload carries it, which the dashboard reads (W8.1): a
        catalogue only where one is declared, so a version declaring none
        uploads what it did before v18."""
        out: dict[str, Any] = {
            "secret_settings": self.secret_settings,
            "not_carried": [
                {
                    "role": held.role,
                    "scheme": held.scheme,
                    "name": held.name,
                    "reason": held.reason,
                }
                for held in self.not_carried
            ],
            "storage": None if self.storage is None else self.storage._to_json(),
        }
        if self.catalogue:
            out["catalogue"] = {"datasets": [dataset._to_json() for dataset in self.catalogue]}
        return out


def load(named: str) -> Declaration:
    """The declaration `module:attribute` names, imported as the plugin runs."""
    module, _, attribute = named.partition(":")
    if not module or not attribute:
        raise ValueError(f"{named!r} does not name a declaration as module:attribute")
    found = getattr(importlib.import_module(module), attribute)
    if not isinstance(found, Declaration):
        raise TypeError(f"{named} is a {type(found).__name__}, not a meridian Declaration")
    return found


def main(argv: Sequence[str] | None = None) -> int:
    """`meridian-declaration module:attribute`: the declaration as JSON, on
    standard output, for `meridian plugin upload` to send (W8.1)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: meridian-declaration module:attribute", file=sys.stderr)
        return 2
    try:
        declared = load(args[0])
    except (ImportError, AttributeError, TypeError, ValueError) as failed:
        print(f"meridian-declaration: {failed}", file=sys.stderr)
        return 1
    print(json.dumps(declared.to_json(), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
