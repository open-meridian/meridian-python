"""Typed settings: one class is a plugin's declaration and its value
(spec/plugins-share-one-framework-in-code, requirement 4, ruled 2026-10-02;
built with the role templates in 0.24.0, spec/plugin-pages-follow-their-role,
Q9).

    @meridian.settings
    class Config:
        environment: str = meridian.environment()
        api_key: str = meridian.setting("API key", required=True, secret=True)
        poll_seconds: int = meridian.setting("Read every", default=300, at_least=60)
        sample_data: bool = meridian.sample_data()

    plugin = await meridian.connect(settings=Config, interface=...)
    config = await plugin.first_settings(Config)      # a Config, defaults filled
    async for config in plugin.settings(Config): ...  # every delivery after
    Config.declared(); Config.label("api_key"); config.missing

A field's annotation is its kind -- `str`, `int`, `bool`, or `list` for a
table -- `choices` make a choice, and the order of the fields is the form's.
`at_least` and `at_most` are the SDK's, not the wire's: a value outside is
held to the bound, logged once per value. `.missing` is the sidecar's
`missing_required`, as delivered. A secret field is never in `repr` or
`str`. `meridian.Setting` tuples keep working, and a class and a tuple
declare the same thing.
"""

from __future__ import annotations

import dataclasses
import logging
import typing
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, cast

from .client import AppliesWhen, Choice, Column, Setting

log = logging.getLogger("meridian.settings")

_C = typing.TypeVar("_C")

#: The values a bound was held to and logged, so each is logged once.
_HELD: set[tuple[str, str, int]] = set()

#: A kind's value when nothing is set and the setting declares no default.
_EMPTY: dict[type, Any] = {str: "", int: 0, bool: False, list: ()}


@dataclasses.dataclass(frozen=True)
class _Field:
    """What `meridian.setting` answers: a setting, its name the field's."""

    label: str = ""
    default: str | int | bool | None = None
    required: bool = False
    secret: bool = False
    description: str = ""
    unit: str = ""
    choices: tuple[Choice, ...] = ()
    applies_when: AppliesWhen | tuple[str, str | Sequence[str]] | None = None
    developer: bool = False
    columns: tuple[Column, ...] = ()
    most_rows: int = 0
    roles: Sequence[str] = ()
    per_person: bool = False
    at_least: int | None = None
    at_most: int | None = None

    def declared(self, name: str, kind: type) -> Setting:
        applies = self.applies_when
        if isinstance(applies, tuple):
            setting, values = applies
            applies = AppliesWhen(
                setting, (values,) if isinstance(values, str) else tuple(values)
            )
        return Setting(
            name,
            kind,
            required=self.required,
            secret=self.secret,
            description=self.description,
            label=self.label,
            default=self.default,
            unit=self.unit,
            choices=tuple(self.choices),
            applies_when=applies,
            developer=self.developer,
            columns=tuple(self.columns),
            most_rows=self.most_rows,
            roles=self.roles,
            per_person=self.per_person,
        )


def setting(
    label: str = "",
    *,
    default: str | int | bool | None = None,
    required: bool = False,
    secret: bool = False,
    description: str = "",
    unit: str = "",
    choices: Sequence[Choice] = (),
    applies_when: AppliesWhen | tuple[str, str | Sequence[str]] | None = None,
    developer: bool = False,
    columns: Sequence[Column] = (),
    most_rows: int = 0,
    roles: Sequence[str] = (),
    per_person: bool = False,
    at_least: int | None = None,
    at_most: int | None = None,
) -> Any:
    """One field of a class decorated `@meridian.settings`: a setting named
    as the field, of the field's annotated kind. `applies_when` may be
    `("key_type", "commercial")`. `at_least` and `at_most` bound an integer,
    held by the SDK."""
    return _Field(
        label=label,
        default=default,
        required=required,
        secret=secret,
        description=description,
        unit=unit,
        choices=tuple(choices),
        applies_when=applies_when,
        developer=developer,
        columns=tuple(columns),
        most_rows=most_rows,
        roles=roles,
        per_person=per_person,
        at_least=at_least,
        at_most=at_most,
    )


#: Sample data's words, every plugin's (spec/plugins-share-one-framework-in-code, Q3).
SAMPLE_DATA_DESCRIPTION = (
    "Answer from built-in made-up data instead of the source, changing nothing else "
    "the plugin does. Development deployments only."
)


def sample_data(
    *, description: str = SAMPLE_DATA_DESCRIPTION, roles: Sequence[str] = ()
) -> Any:
    """The sample-data setting, one convention for every plugin that reads an
    outside source (ruled 2026-10-02): `sample_data`, a bool, off by
    default, labelled "Sample data", a developer setting, so shown and saved
    only on a development deployment. Last among the settings, in a class
    or a list alike."""
    return Setting(
        "sample_data",
        bool,
        default=False,
        label="Sample data",
        description=description,
        developer=True,
        roles=roles,
    )


def environment(
    *,
    description: str = "Which of the vendor's environments this plugin reads: its live "
    "service, or its sandbox.",
    roles: Sequence[str] = (),
) -> Any:
    """The vendor's environment, for a vendor with more than one
    (spec/plugin-pages-follow-their-role, Q12 as amended 2026-10-10): the
    setting `environment`, a required choice, label "Environment", values
    `live` ("Live") and `sandbox` ("Sandbox"), default `live`, declared
    first, before every other setting; a credential differing by
    environment is gated on it with `applies_when=("environment",
    "sandbox")`."""
    return Setting(
        "environment",
        str,
        required=True,
        default="live",
        label="Environment",
        description=description,
        choices=(Choice("live", "Live"), Choice("sandbox", "Sandbox")),
        roles=roles,
    )


class Typed:
    """The base a class decorated `@meridian.settings` is given: its
    declaration, each field's label, and the settings missing."""

    __meridian_settings__: ClassVar[tuple[Setting, ...]] = ()
    __meridian_bounds__: ClassVar[dict[str, tuple[int | None, int | None]]] = {}
    missing: tuple[str, ...]

    @classmethod
    def declared(cls) -> tuple[Setting, ...]:
        """The settings the class declares, in its order: what `connect`
        registers."""
        return cls.__meridian_settings__

    @classmethod
    def label(cls, name: str) -> str:
        """The label the Settings form shows for `name`, or its name where it
        declares none."""
        for each in cls.__meridian_settings__:
            if each.name == name:
                return each.label or name
        raise KeyError(f"{cls.__name__} declares no setting {name!r}")

    @classmethod
    def _of(cls, values: Mapping[str, Any], missing: Sequence[str] = ()) -> Any:
        given: dict[str, Any] = {}
        for each in cls.__meridian_settings__:
            if each.name in values:
                value = values[each.name]
            elif each.default is not None:
                value = each.default
            else:
                value = _EMPTY[each.kind]
            if each.kind is list:
                value = tuple(dict(row) for row in value)
            least, most = cls.__meridian_bounds__.get(each.name, (None, None))
            if isinstance(value, int) and not isinstance(value, bool):
                value = _held(cls.__name__, each.name, value, least, most)
            given[each.name] = value
        return cast(Any, cls)(**given, missing=tuple(missing))


def _held(owner: str, name: str, value: int, least: int | None, most: int | None) -> int:
    bound = least if least is not None and value < least else None
    if bound is None and most is not None and value > most:
        bound = most
    if bound is None:
        return value
    if (owner, name, value) not in _HELD:
        _HELD.add((owner, name, value))
        log.warning("setting %s is %s; held to %s", name, value, bound)
    return bound


def _kind(hint: Any, where: str) -> type:
    origin = typing.get_origin(hint) or hint
    if origin in (str, int, bool, list, tuple):
        return list if origin in (list, tuple) else origin
    raise TypeError(f"{where} is annotated {hint!r}; a setting is a str, int, bool or list")


def settings(cls: type[_C]) -> type[_C]:
    """Make `cls` a plugin's typed settings: each annotated field declared
    with `meridian.setting(...)`, `meridian.environment()` or
    `meridian.sample_data()` is a setting named as the field. The class
    becomes a frozen dataclass of the values, with `declared()`,
    `label(name)` and `.missing`."""
    hints = typing.get_type_hints(cls)
    declared: list[Setting] = []
    bounds: dict[str, tuple[int | None, int | None]] = {}
    fields: list[tuple[str, Any, Any]] = []
    for name in hints:
        given = cls.__dict__.get(name)
        where = f"{cls.__name__}.{name}"
        kind = _kind(hints[name], where)
        if isinstance(given, _Field):
            made = given.declared(name, kind)
            if given.at_least is not None or given.at_most is not None:
                if kind is not int:
                    raise TypeError(f"{where} has at_least or at_most, so it is an int")
                bounds[name] = (given.at_least, given.at_most)
        elif isinstance(given, Setting):
            if given.name != name or given.kind is not kind:
                raise TypeError(
                    f"{where} is the setting {given.name}, a {given.kind.__name__}; name the "
                    f"field {given.name} and annotate it {given.kind.__name__}"
                )
            made = given
        else:
            raise TypeError(
                f"{where} is not declared with meridian.setting(...), "
                "meridian.environment() or meridian.sample_data()"
            )
        made._declared()  # refused now, naming it, as registration would
        declared.append(made)
        fields.append(
            (
                name,
                hints[name],
                dataclasses.field(repr=not made.secret, compare=not made.secret),
            )
        )
    fields.append(("missing", tuple[str, ...], dataclasses.field(default=())))
    made_class = dataclasses.make_dataclass(
        cls.__name__,
        fields,
        bases=(Typed,),
        frozen=True,
        namespace={
            "__module__": cls.__module__,
            "__qualname__": cls.__qualname__,
            "__doc__": cls.__doc__,
            "__meridian_settings__": tuple(declared),
            "__meridian_bounds__": bounds,
        },
    )
    made_class.__str__ = made_class.__repr__  # type: ignore[method-assign]
    return cast(type[_C], made_class)


def declared_by(settings: Sequence[Setting] | type) -> tuple[Setting, ...]:
    """A declaration's settings, from a list of `Setting`s or a class
    decorated `@meridian.settings`."""
    if isinstance(settings, type):
        if not issubclass(settings, Typed):
            raise TypeError(
                f"settings is the class {settings.__name__}, which is not decorated "
                "@meridian.settings"
            )
        return settings.declared()
    return tuple(settings)
