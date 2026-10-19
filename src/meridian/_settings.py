"""Typed settings: one class is a plugin's declaration and its value
(spec/plugins-share-one-framework-in-code, requirement 4, ruled 2026-10-02;
built with the role templates in 0.24.0, spec/plugin-pages-follow-their-role,
Q9).

    @meridian.settings
    class Config:
        environment: str = meridian.environment()   # sandbox, until a person chooses Live
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
`missing_required`, as delivered, and from 0.31.1 each required setting
whose saved value this version cannot read; `.refused` says each such value
(`meridian.RefusedSetting`), never raised. A secret field is never in `repr`
or `str`. `meridian.Setting` tuples keep working, and a class and a tuple
declare the same thing.
"""

from __future__ import annotations

import dataclasses
import logging
import typing
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, cast

from .client import AppliesWhen, Choice, Column, RefusedSetting, Setting

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


#: The values `meridian.environment()` offers, in its order: live, and the
#: vendor's demo environment by the word it uses -- a sandbox, or (contract
#: v26, G1 question 5) paper.
ENVIRONMENTS = (Choice("live", "Live"), Choice("sandbox", "Sandbox"))
#: The role-common setting's values (W6.11, contract v26): the demo ones are
#: `sandbox` and `paper`.
ENVIRONMENT_VALUES = ("live", "sandbox", "paper")
DEMO_ENVIRONMENTS = frozenset({"sandbox", "paper"})


def environment(
    *,
    default: str = "",
    description: str = "",
    roles: Sequence[str] = (),
    demo: str = "sandbox",
    demo_label: str = "",
) -> Any:
    """The vendor's environment, for a vendor with more than one
    (spec/plugin-pages-follow-their-role, Q12 as amended 2026-10-10): the
    setting `environment`, a required choice, label "Environment", values
    `live` ("Live") and the vendor's demo environment -- `sandbox`
    ("Sandbox"), or from 0.31.0 (contract v26) `paper` ("Paper") where the
    vendor calls it that (`demo="paper"`; Alpaca's paper trading, OANDA's
    practice with `demo_label="Practice"`) -- declared first, before every
    other setting; a credential differing by environment is gated on it with
    `applies_when=("environment", "sandbox")`.

    It defaults to the demo environment (SDK 0.28.0, approved by the product
    owner 2026-10-14): a plugin is Live only where a person chose Live, or
    where its own code says so, `environment(default="live")`, never because
    an upgrade added the setting or a value went missing. A plugin reading
    the value treats anything but `live` as the demo environment. The
    description says which it starts on, unless the plugin gives its own.

    A value saved that this version no longer offers -- `practice` or
    `sandbox` where the plugin now says `paper` -- is never mapped to one it
    does (0.31.1): it is delivered empty, not even the default, named among
    the missing and said in `refused`. Empty is not `live`, so the plugin
    still reaches the demo host; and it is not demo, so `is_demo` and the
    badge count it live until a person saves it again.

    The value is one key of the agents' demo-only guard (W11.38): a
    connection is demo only while this setting and the environment its
    session reports on its venue catalogue (`reached_environment`) both say
    `sandbox` or `paper`."""
    if demo not in DEMO_ENVIRONMENTS:
        raise ValueError(f"environment's demo is sandbox or paper, not {demo!r}")
    offered = (Choice("live", "Live"), Choice(demo, demo_label or demo.capitalize()))
    default = default or demo
    if default not in {choice.value for choice in offered}:
        raise ValueError(f"environment's default is {default!r}; it is one of live, {demo}")
    word = (demo_label or demo).lower()
    words = description or (
        "Which of the vendor's environments this plugin reads: its live service, or its "
        f"{word}. "
        + (
            f"Live unless a person chooses {demo_label or demo.capitalize()}."
            if default == "live"
            else f"{(demo_label or demo).capitalize()} until a person chooses Live."
        )
    )
    return Setting(
        "environment",
        str,
        required=True,
        default=default,
        label="Environment",
        description=words,
        choices=offered,
        roles=roles,
    )


def reached_environment(
    address: str,
    *,
    live: Sequence[str] = (),
    paper: Sequence[str] = (),
    sandbox: Sequence[str] = (),
) -> str:
    """The environment a connectivity plugin's session actually reached
    (contract v26, W11.20; G1 question 5), read from the vendor's host --
    OANDA's `api-fxpractice.oanda.com` against `api-fxtrade.oanda.com`,
    Alpaca's `paper-api.alpaca.markets`, Tradier's `sandbox.tradier.com` --
    for `VenueCatalogue.environment`: `live`, `paper` or `sandbox` for a host
    named under it (exactly, without regard to case), and empty -- no report,
    which the guard counts live -- for any other. `address` is the URL the
    session called, or its host."""
    host = address.strip().lower()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/", 1)[0].split("@")[-1].split(":", 1)[0]
    for value, hosts in (("live", live), ("paper", paper), ("sandbox", sandbox)):
        if host and host in {h.strip().lower() for h in hosts}:
            return value
    return ""


def is_demo(setting: str, reported: str) -> bool:
    """Whether a connection is demo for the agents' guard (contract v26,
    W11.38): its environment setting and the environment its session
    reported both `sandbox` or `paper`. No setting, any other value, no
    report or a disagreement is live, failing closed."""
    return setting in DEMO_ENVIRONMENTS and reported in DEMO_ENVIRONMENTS


def connection_badge(setting: str, reported: str) -> str:
    """The badge a connection is drawn with (contract v26, W11.8): "Demo"
    where both keys say demo, "Live" where neither does, and "Live
    (environment not confirmed)" where the setting and the session
    disagree."""
    if is_demo(setting, reported):
        return "Demo"
    if (setting in DEMO_ENVIRONMENTS) != (reported in DEMO_ENVIRONMENTS):
        return "Live (environment not confirmed)"
    return "Live"


#: The account's currency's words, every plugin's (contract v23).
ACCOUNT_CURRENCY_DESCRIPTION = (
    "The currency of a linked account whose source states none, as an ISO 4217 code "
    "(USD): a row naming no account is every linked account's, a row naming one is that "
    "account's own. The plugin reports nothing it needs the currency for until it is set."
)


def account_currency(
    *, description: str = ACCOUNT_CURRENCY_DESCRIPTION, roles: Sequence[str] = ()
) -> Any:
    """The linked account's currency, supplied by the plugin's admin
    (contract v23, W3.1; its name approved 2026-10-13): `account_currency`, a
    table labelled "Account currency", each row an `external_account` (one
    this plugin reported, or none for the plugin-wide default) and its
    `currency`, an ISO 4217 code. A plugin whose source states no currency
    for an account's securities declares it and gives the currency with its
    provenance, supplied by the person who set the row
    (`meridian.edge.supplied_currency`), never a guess; until a row covers an
    account it reports nothing that needs the currency."""
    return Setting(
        "account_currency",
        list,
        label="Account currency",
        description=description,
        columns=(
            Column(
                "external_account",
                kind="external_account",
                label="Account",
                description="A linked account, or none for every linked account without a row",
            ),
            Column(
                "currency",
                label="Currency",
                required=True,
                description="An ISO 4217 code, such as USD",
            ),
        ),
        roles=roles,
    )


class Typed:
    """The base a class decorated `@meridian.settings` is given: its
    declaration, each field's label, and the settings missing."""

    __meridian_settings__: ClassVar[tuple[Setting, ...]] = ()
    __meridian_bounds__: ClassVar[dict[str, tuple[int | None, int | None]]] = {}
    missing: tuple[str, ...]
    refused: tuple[RefusedSetting, ...]

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
    def _of(
        cls,
        values: Mapping[str, Any],
        missing: Sequence[str] = (),
        refused: Sequence[RefusedSetting] = (),
    ) -> Any:
        given: dict[str, Any] = {}
        unread = {r.name for r in refused}
        for each in cls.__meridian_settings__:
            if each.name in values:
                value = values[each.name]
            elif each.name in unread and each.required:
                # Refused and required: unset, never its default (0.31.1).
                value = _EMPTY[each.kind]
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
        return cast(Any, cls)(**given, missing=tuple(missing), refused=tuple(refused))


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
    with `meridian.setting(...)`, `meridian.environment()`,
    `meridian.sample_data()` or `meridian.account_currency()` is a setting
    named as the field. The class
    becomes a frozen dataclass of the values, with `declared()`,
    `label(name)`, `.missing` and `.refused`."""
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
    fields.append(("refused", tuple[RefusedSetting, ...], dataclasses.field(default=())))
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
