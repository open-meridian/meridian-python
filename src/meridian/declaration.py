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

From contract v18 a data plugin declares its catalogue (W8.1, W10.4; spec/the-lake,
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
support, and only a version holding `data` declares one.

From contract v22 a version declares the algorithms its autonomous work may
name (W4.1, W4.9): each an `AlgorithmDeclaration`, its identifier stable
across versions and reinstalls -- what `reporting` maps to a regime's
decision-maker and executor -- with a description a person reads on the
plugin's page:

    algorithms=[
        AlgorithmDeclaration("twap-v1", "Time-weighted slices over the order's window."),
    ]

`meridian.runs_as(role, algorithm_id="twap-v1")` then names one on every
call its block makes; one the version does not declare is refused. A
version declaring none names none.

From contract v25 the declaration is the whole of what a version says about
itself (W4.1, W8.1; plans/a-plugin-carries-its-own-documentation): beside
the above, its `interface` -- its pages and the tools their typed routes
make -- whether it `reads_external_accounts`, and the vendor's
`documentation`, the plugin's `docs/` folder, each fixed section named by
its digest and size. An operations plugin also declares its
`affirmation_deadline`, minutes after midnight in the deployment's time zone
(W11.34). The upload carries all of it, the texts beside it, and a plugin
declaring v25 registers exactly the declaration its version was uploaded
with, or its sidecar refuses it naming the first difference:

    INTERFACE = meridian.Interface(port=8000, title=TITLE, pages=pages)
    DECLARATION = Declaration(
        settings=Config,
        interface=INTERFACE,
        reads_external_accounts=True,
        documentation="docs",
    )

`connect(declaration=DECLARATION)` then registers its interface; one given
to `connect` as well must be the same. The interface's port is fixed here,
never read from the environment, since the upload and the registration must
agree on it; the module naming the declaration imports every module
declaring a page or a route, so the tools it carries are all of them.

`documentation` names the folder, relative to where the plugin runs: in its
image, `/plugin`, so `docs` is `/plugin/docs`. Each section is
`docs/<section>.md` -- `overview`, `setup`, `troubleshooting`, `terms` and
`pages` -- UTF-8, 1 to 65,536 bytes, the five at most 256 KiB; any other
file there is the repository's own and is not uploaded. The SDK reads and
digests them and parses no Markdown: `meridian plugin check` checks them and
the dashboard renders them. `meridian-declaration --documentation
module:attribute` prints the texts, which `meridian plugin upload` sends.

The settings the SDK declares for each kind of raw record
(`<kind>_window_days`, `<kind>_past_window`) are not in the declaration's
settings: they follow from its storage's kinds, and the past window's
default from whether the deployment gives the instance an archive, which is
known only where it runs.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from .bounds import (
    ALGORITHM_DECLARATION_DESCRIPTION_LENGTH,
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
    DOCUMENTATION_SECTION_BYTES_RANGE,
    NOT_CARRIED_NAME_LENGTH,
    NOT_CARRIED_ROLE_LENGTH,
    NOT_CARRIED_SCHEME_LENGTH,
    PLUGIN_DECLARATION_AFFIRMATION_DEADLINE_RANGE,
    PLUGIN_DECLARATION_NOT_CARRIED_COUNT,
    RAW_RECORD_KIND_LABEL_LENGTH,
    RAW_RECORD_KIND_NAME_LENGTH,
    RAW_RECORD_KIND_WINDOW_DAYS_RANGE,
    STORAGE_DECLARATION_RECORD_KINDS_COUNT,
    STORAGE_DECLARATION_RETENTION_DAYS_RANGE,
)
from .v1 import sidecar_pb2

if TYPE_CHECKING:
    from .client import Interface, Setting

#: The roles at the edge, which alone may own storage for their raw records
#: (decisions/028).
EDGE_ROLES = frozenset(
    {"confirmation", "connectivity", "custody", "data", "reporting", "servicing", "settlement"}
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
    deployment meets them.

    From 0.32.0 (contract v27, ruling 479) the derived-data answer is one of
    three, `derived_use_terms` -- `not_restricted`, `internal_only` or
    `redistribution_needs_licence` -- and a v27 writer sets both it and the
    boolean `derived_use`, deprecated for one release: given the boolean
    alone, the terms are `not_restricted` for true and `internal_only` for
    false, as a reader reads it; given the terms alone, the boolean is true
    but for `internal_only`; given both, they agree or the licence is
    refused.

    From 0.32.2 the attribution and redistribution terms the v27 wire
    carries, by the wire's names: `redistribution` -- `not_allowed`,
    `licence_required` or `allowed_with_attribution`, empty for not stated;
    `attribution_required`, whether `attribution_text` travels with the data;
    `attribution_text`, a template such as "Source: central bank statistics",
    shown on every page that shows the dataset, in exports and in every MCP
    answer carrying its fields (ruling 386); `copyright_class` --
    `public_domain`, `copyright_citation_required` or
    `copyright_preapproval_required`, empty for not stated, one class per
    dataset; and `no_more_restrictive_terms`, whether the vendor forbids
    adding restrictions downstream."""

    kept: bool = False
    retention_days: int = 0
    derived_use: bool | None = None
    display: bool = False
    default_fields: Sequence[str] = ()
    personal_use: bool = False
    derived_use_terms: str = ""
    redistribution: str = ""
    attribution_required: bool = False
    attribution_text: str = ""
    copyright_class: str = ""
    no_more_restrictive_terms: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_fields", tuple(self.default_fields))
        for name, prefix, words in (
            ("redistribution", "redistribution_",
             ("not_allowed", "licence_required", "allowed_with_attribution")),
            ("copyright_class", "copyright_class_",
             ("public_domain", "copyright_citation_required",
              "copyright_preapproval_required")),
        ):  # fmt: skip
            said = str(getattr(self, name) or "").strip().lower().removeprefix(prefix)
            if said and said not in words:
                raise ValueError(f"a licence's {name} is one of {', '.join(words)}")
            object.__setattr__(self, name, said)
        terms = str(self.derived_use_terms or "").strip().lower()
        terms = terms.removeprefix("derived_use_")
        words = ("not_restricted", "internal_only", "redistribution_needs_licence")
        if terms and terms not in words:
            raise ValueError(f"a licence's derived_use_terms is one of {', '.join(words)}")
        if not terms:
            terms = "not_restricted" if self.derived_use else "internal_only"
        flag = terms != "internal_only"
        if self.derived_use is not None and bool(self.derived_use) != flag:
            raise ValueError(
                f"a licence's derived_use {self.derived_use} disagrees with its "
                f"derived_use_terms {terms}: a v27 writer sets both alike (ruling 479)"
            )
        object.__setattr__(self, "derived_use_terms", terms)
        object.__setattr__(self, "derived_use", flag)
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
            derived_use=bool(self.derived_use),
            derived_use_terms=cast(
                Any,
                sidecar_pb2.DerivedUse.Value("DERIVED_USE_" + self.derived_use_terms.upper()),
            ),
            display=self.display,
            default_fields=list(self.default_fields),
            personal_use=self.personal_use,
            redistribution=cast(
                Any,
                sidecar_pb2.Redistribution.Value(
                    "REDISTRIBUTION_" + (self.redistribution or "unspecified").upper()
                ),
            ),
            attribution_required=self.attribution_required,
            attribution_text=self.attribution_text,
            copyright_class=cast(
                Any,
                sidecar_pb2.CopyrightClass.Value(
                    "COPYRIGHT_CLASS_" + (self.copyright_class or "unspecified").upper()
                ),
            ),
            no_more_restrictive_terms=self.no_more_restrictive_terms,
        )

    def _to_json(self) -> dict[str, Any]:
        return {
            "kept": self.kept,
            "retention_days": self.retention_days,
            "derived_use": self.derived_use,
            "derived_use_terms": self.derived_use_terms,
            "display": self.display,
            "default_fields": list(self.default_fields),
            "personal_use": self.personal_use,
            "redistribution": self.redistribution,
            "attribution_required": self.attribution_required,
            "attribution_text": self.attribution_text,
            "copyright_class": self.copyright_class,
            "no_more_restrictive_terms": self.no_more_restrictive_terms,
        }


@dataclass(frozen=True, kw_only=True)
class DatasetDeclaration:
    """One dataset a data plugin serves the lake (contract v18): its identity in a
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
    one venue's, which is the consolidated view. `calendar_id` is the
    settlement calendar its business dates follow, its `CAL-` ID (W10.1,
    contract v22; carried from SDK 0.28.0), empty for none: the lake flags a
    daily value dated on a day it says is closed, and refuses nothing by
    it. `declared_delay_ns` (contract v27, rulings 368, 369 and 382) is how
    far behind real time the vendor serves it, 0 for real time: its
    staleness and edge age are judged against the delay plus the ceiling,
    one dataset per timeliness."""

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
    calendar_id: str = ""
    declared_delay_ns: int = 0

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
        if (
            isinstance(self.declared_delay_ns, bool)
            or not isinstance(self.declared_delay_ns, int)
            or self.declared_delay_ns < 0
        ):
            raise ValueError(f"{at}'s declared_delay_ns is 0 or more nanoseconds")
        if self.calendar_id and not self.calendar_id.startswith("CAL-"):
            raise ValueError(
                f"{at}'s calendar_id {self.calendar_id!r} is no calendar's ID (CAL-): the "
                "deployment's Calendars name each (list_calendars, read_calendar)"
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
            calendar_id=self.calendar_id,
            declared_delay_ns=self.declared_delay_ns,
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
            "calendar_id": self.calendar_id,
            "declared_delay_ns": self.declared_delay_ns,
        }


@dataclass(frozen=True)
class AlgorithmDeclaration:
    """One algorithm identifier a version declares (contract v22): stable
    across versions and reinstalls, with what it is, in plain text, for a
    person reading the plugin's page (1 to 1,024 characters)."""

    algorithm_id: str
    description: str

    def __post_init__(self) -> None:
        if not isinstance(self.algorithm_id, str) or not self.algorithm_id.strip():
            raise ValueError("an algorithm's algorithm_id is empty; name it, stably")
        if self.algorithm_id != self.algorithm_id.strip():
            raise ValueError(
                f"the algorithm {self.algorithm_id!r}: its algorithm_id has spaces around it"
            )
        if not ALGORITHM_DECLARATION_DESCRIPTION_LENGTH.admits(len(self.description)):
            raise ValueError(
                f"the algorithm {self.algorithm_id}'s description is 1 to "
                f"{ALGORITHM_DECLARATION_DESCRIPTION_LENGTH.most} characters"
            )

    def _wire(self) -> sidecar_pb2.AlgorithmDeclaration:
        return sidecar_pb2.AlgorithmDeclaration(
            algorithm_id=self.algorithm_id, description=self.description
        )


#: The vendor's documentation's sections, each `docs/<name>.md`, in the order
#: a version's declaration names them (W8.1, contract v25): `overview` and
#: `setup`, which `meridian plugin check` requires; `troubleshooting` and
#: `terms`, which it prompts for; and `pages`, optional.
_SECTIONS = ("overview", "setup", "troubleshooting", "terms", "pages")

#: The most bytes the sections hold together (W8.1): the conductor refuses an
#: upload past it, naming it.
_DOCUMENTATION_BUNDLE_BYTES = 262_144


@dataclass(frozen=True)
class _Section:
    """One section of the vendor's documentation, as the version ships it:
    its fixed name, its text exactly as the file holds it, and the digest and
    size the declaration names it by."""

    name: str
    markdown: str
    digest: str
    bytes: int


def _read_documentation(folder: str | os.PathLike[str]) -> tuple[_Section, ...]:
    """The sections in `folder`, each file `<section>.md` that is there, in
    the declaration's order: read and digested, never parsed. Refused,
    naming the file, where one is not UTF-8 or is empty or past 64 KiB, and
    where together they pass 256 KiB; a folder that is not there is refused
    too, naming where it was looked for. Any other file is the repository's
    own and is left out."""
    root = Path(folder)
    if not root.is_dir():
        raise ValueError(
            f"documentation names {str(folder)!r}, and there is no folder at "
            f"{root.absolute()}: it is relative to where the plugin runs (in its image, "
            "/plugin), the folder holding overview.md, setup.md and the rest"
        )
    found: list[_Section] = []
    total = 0
    bound = DOCUMENTATION_SECTION_BYTES_RANGE
    for name in _SECTIONS:
        path = root / f"{name}.md"
        if not path.is_file():
            continue
        data = path.read_bytes()
        if not bound.admits(len(data)):
            raise ValueError(
                f"{path}: a section is {bound.least:,} to {bound.most:,} bytes, and this is "
                f"{len(data):,}"
            )
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as failed:
            raise ValueError(f"{path} is not UTF-8 text: {failed.reason}") from None
        total += len(data)
        found.append(
            _Section(
                name=name,
                markdown=text,
                digest=f"sha256:{hashlib.sha256(data).hexdigest()}",
                bytes=len(data),
            )
        )
    if total > _DOCUMENTATION_BUNDLE_BYTES:
        raise ValueError(
            f"{root}: the sections hold {total:,} bytes together, and the most is "
            f"{_DOCUMENTATION_BUNDLE_BYTES:,}"
        )
    return tuple(found)


def _as_json(message: Any) -> dict[str, Any]:
    """A declaration's message as the upload carries it: protobuf's JSON, the
    fields by their proto names and each enum by its value's name, as the
    dashboard reads them (`SETTING_TYPE_CHOICE`, `ACCESS_LEVEL_ADMIN`)."""
    from google.protobuf import json_format

    return json_format.MessageToDict(message, preserving_proto_field_name=True)


@dataclass(frozen=True)
class Declaration:
    """A version's declaration. `settings` are the ones it declares at
    registration (`meridian.Setting`), or a class decorated
    `@meridian.settings` declaring them.
    From contract v18 a data plugin's `catalogue`: the datasets it serves the lake.
    From contract v22 the `algorithms` its autonomous work may name, each
    identifier once.
    From contract v25 its `interface` (`meridian.Interface`), whether it
    `reads_external_accounts`, its `documentation` folder, and an
    operations plugin's `affirmation_deadline` in minutes after midnight
    (1 to 1440; 0 declares none)."""

    settings: Sequence[Any] | type[Any] = ()
    not_carried: Sequence[NotCarried] = field(default=())
    storage: Storage | None = None
    catalogue: Sequence[DatasetDeclaration] = ()
    algorithms: Sequence[AlgorithmDeclaration] = ()
    interface: Interface | None = None
    reads_external_accounts: bool = False
    documentation: str | os.PathLike[str] | None = None
    affirmation_deadline: int = 0
    _read: dict[str, tuple[_Section, ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        from ._settings import declared_by

        object.__setattr__(self, "settings", declared_by(self.settings))
        if self.interface is not None:
            from .client import Interface as _Interface

            if not isinstance(self.interface, _Interface):
                raise TypeError(
                    f"interface is a {type(self.interface).__name__}, not a meridian.Interface"
                )
        if not isinstance(self.reads_external_accounts, bool):
            raise TypeError("reads_external_accounts is True or False")
        deadline = self.affirmation_deadline
        bound = PLUGIN_DECLARATION_AFFIRMATION_DEADLINE_RANGE
        if (
            isinstance(deadline, bool)
            or not isinstance(deadline, int)
            or not bound.admits(deadline)
        ):
            raise ValueError(
                "affirmation_deadline is minutes after midnight in the deployment's time "
                f"zone, 1 to {bound.most}, or 0 for none; not {deadline!r}"
            )
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
        algorithms = tuple(self.algorithms)
        object.__setattr__(self, "algorithms", algorithms)
        named = [held.algorithm_id for held in algorithms]
        again = next((one for one in named if named.count(one) > 1), None)
        if again is not None:
            raise ValueError(f"the algorithm {again} is declared twice; each identifier once")
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
        if self.catalogue and "data" not in roles:
            return (
                "a catalogue is declared by a plugin not holding data; "
                "only a data plugin serves the lake"
            )
        if self.affirmation_deadline and "operations" not in roles:
            return (
                "an affirmation deadline is declared by a plugin not holding operations; "
                "only an operations plugin affirms its trades (W11.34)"
            )
        return None

    def _sections(self) -> tuple[_Section, ...]:
        """The vendor's documentation this version ships (contract v25), read
        from `documentation` once, where the plugin runs: none where it names
        no folder."""
        if self.documentation is None:
            return ()
        key = os.fspath(self.documentation)
        if key not in self._read:
            self._read[key] = _read_documentation(key)
        return self._read[key]

    def _interface_wire(self) -> tuple[sidecar_pb2.InterfaceDeclaration | None, list[Any]]:
        """Its interface and the tools its typed routes make, as registration
        sends them. The restore route the SDK serves for a kind of raw record
        (contract v16) is declared on the pages first, as `connect` declares
        it, so both name the same tools."""
        if self.interface is None:
            return None, []
        from .client import _edge_roles
        from .pages import Pages as _Pages

        if (
            self.storage is not None
            and self.storage.kinds
            and isinstance(self.interface.pages, _Pages)
        ):
            from .edge import _restore_route

            _restore_route(
                self.interface.pages,
                _edge_roles(cast("tuple[Setting, ...]", self.settings), self.interface),
            )
        return self.interface._declared(), self.interface._tools()

    def to_wire(self) -> sidecar_pb2.PluginDeclaration:
        """As registration carries it: from contract v25 with its settings,
        interface, tools, whether it reads external accounts, and its
        documentation's sections by digest."""
        interface, tools = self._interface_wire()
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
            algorithms=[held._wire() for held in self.algorithms],
            settings=[setting._declared() for setting in self.settings],
            interface=interface,
            tools=tools,
            reads_external_accounts=self.reads_external_accounts,
            documentation=[
                sidecar_pb2.DocumentationSection(
                    name=section.name, digest=section.digest, bytes=section.bytes
                )
                for section in self._sections()
            ],
            affirmation_deadline=self.affirmation_deadline,
        )

    def to_json(self) -> dict[str, Any]:
        """As an upload carries it, which the dashboard reads (W8.1): a
        catalogue only where one is declared, so a version declaring none
        uploads what it did before v18; and its algorithms only where it
        declares any (contract v22), likewise. From contract v25 its
        settings, its interface and tools where it declares one, whether it
        reads external accounts, and each section of its documentation by
        name, digest and size -- the settings, interface and tools as
        protobuf's JSON of what registration sends -- and an affirmation
        deadline where it declares one."""
        interface, tools = self._interface_wire()
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
        if self.algorithms:
            out["algorithms"] = [
                {"algorithm_id": held.algorithm_id, "description": held.description}
                for held in self.algorithms
            ]
        out["settings"] = [_as_json(setting._declared()) for setting in self.settings]
        if interface is not None:
            out["interface"] = _as_json(interface)
            out["tools"] = [_as_json(tool) for tool in tools]
        out["reads_external_accounts"] = self.reads_external_accounts
        out["documentation"] = [
            {"name": section.name, "digest": section.digest, "bytes": section.bytes}
            for section in self._sections()
        ]
        if self.affirmation_deadline:
            out["affirmation_deadline"] = self.affirmation_deadline
        return out

    def _texts(self) -> list[dict[str, str]]:
        """The documentation's texts as the upload carries them beside the
        declaration (`RecordPluginUploadRequest.documentation`, each a
        `DocumentationText`): each section's name and its Markdown, exactly as
        the file holds it, so its digest is the declaration's."""
        return [
            {"section": section.name, "markdown": section.markdown}
            for section in self._sections()
        ]


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
    standard output, for `meridian plugin upload` to send (W8.1).

    `meridian-declaration --documentation module:attribute` (contract v25):
    the documentation's texts instead, as JSON, a list of each section's
    `section` and `markdown`, which the upload sends beside the declaration.
    Both read the same files, so what is uploaded is what the image holds."""
    args = list(sys.argv[1:] if argv is None else argv)
    texts = "--documentation" in args
    named = [arg for arg in args if arg != "--documentation"]
    if len(named) != 1 or named[0].startswith("-"):
        print("usage: meridian-declaration [--documentation] module:attribute", file=sys.stderr)
        return 2
    try:
        declared = load(named[0])
        printed: Any = declared._texts() if texts else declared.to_json()
    except (ImportError, AttributeError, TypeError, ValueError) as failed:
        print(f"meridian-declaration: {failed}", file=sys.stderr)
        return 1
    print(json.dumps(printed, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
