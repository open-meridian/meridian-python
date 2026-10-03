"""A route's one typed record of inputs, read alike from a browser's form and
an agent's JSON (contract v12; spec/a-deployment-serves-its-mcp, requirement
8 and Q3; the product owner, 2026-10-03: data entry is a typed table).

    @dataclass(frozen=True)
    class Lot:
        quantity: Decimal
        cost: Decimal | None = None
        acquired: date | None = None

    @dataclass(frozen=True)
    class Position:
        settled: Decimal | None = None
        lots: list[Lot] = field(default_factory=list)

    @dataclass(frozen=True)
    class Confirmation:
        account: str
        reason: str = ""
        positions: list[Position] = field(default_factory=list)

A record is a frozen dataclass whose fields are each `str`, `int`, `bool`,
`Decimal`, `date` or `datetime`, a record of the same kind, a `list` (or a
`tuple[X, ...]`) of one of those, or one of those or None. A field without a
default is required. `field(metadata=...)` may give a field's `description`,
its `max_length` (characters), `min` and `max` (a number's, a Decimal's as a
string), `places` (a Decimal's most decimal places) and `choices` (the
strings a text may be).

**Paths.** Every field is named by the data dictionary's path grammar
(meridian-design spec/every-store-publishes-a-versioned-data-dictionary,
"Paths"): `account`, `positions[3].settled`, `positions[3].lots[0].cost`. A
form's inputs carry those names -- the kit's `om-entry-grid` names its cells
so -- and so does a refusal: one path names one cell and one argument.

**JSON** (`from_json`), as an agent's tool call sends it: an object of the
record's fields and nothing else, an argument it does not have refused by
name; a Decimal a string (`"1500.25"`), never a JSON number, which a client
may have rounded; a date `YYYY-MM-DD` and a moment ISO 8601 with its offset;
an integer a JSON integer and a boolean a JSON boolean. Every field that
does not read is named, not only the first.

**A form** (`from_form`), as a browser posts it: every value text, an empty
one a field left blank (its default, or missing where it is required); a
number or a date typed as a person types it is read as the JSON one is, with
no grouping commas; a boolean is `on`, `true` or `1`, and absent is false. A
list's rows are taken in the order of their numbers, and a row with nothing
in it is no row, as the kit's grid and a page's plain table of inputs both
post. A field that does not read is named and left at its default, so the
page can show the person what they typed and what is wrong with it; the
record is None only where a field it requires is missing.

`schema(cls)` is the record's JSON Schema, the tool's input schema
(`ToolDeclaration.input_schema`); `to_json(value)` a record (or anything made
of the same kinds) as the JSON a tool answers, a Decimal as its string.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import re
import types
import typing
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

__all__ = ["Problem", "Unread", "from_form", "from_json", "schema", "to_json"]

#: A path's steps: a name, or an index in brackets.
_STEP = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]")
_DECIMAL = re.compile(r"-?(?:\d+)(?:\.\d+)?")
#: The largest index a form's path may name: a page's rows, not a memory test.
MOST_ROWS = 10_000


@dataclasses.dataclass(frozen=True)
class Problem:
    """One field that did not read, by its path, in the plugin's words."""

    path: str
    message: str


class Unread(ValueError):
    """The record could not be read: each field by its path."""

    def __init__(self, problems: Iterable[Problem]) -> None:
        self.problems = tuple(problems)
        super().__init__(
            "; ".join(f"{p.path or 'the record'}: {p.message}" for p in self.problems)
        )


# ── The record's shape ──────────────────────────────────────────────────────


def _hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls)


def _check_record(cls: Any) -> None:
    if not (isinstance(cls, type) and dataclasses.is_dataclass(cls)):
        raise TypeError(f"{cls!r} is not a record: a route's params are one frozen dataclass")
    if not cls.__dataclass_params__.frozen:  # type: ignore[attr-defined]
        raise TypeError(
            f"{cls.__name__} is not frozen: a route's record is @dataclass(frozen=True)"
        )


def _optional(hint: Any) -> tuple[Any, bool]:
    """The type a `X | None` holds, and whether None is allowed."""
    origin = typing.get_origin(hint)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(hint) if a is not type(None)]
        if len(args) == 1 and len(typing.get_args(hint)) == 2:
            return args[0], True
        raise TypeError(f"{hint!r}: a field is one kind or that kind or None")
    return hint, False


def _sequence(hint: Any) -> Any | None:
    """The row type of a list or `tuple[X, ...]`; None for anything else."""
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)
    if origin is list and len(args) == 1:
        return args[0]
    if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
        return args[0]
    return None


def _is_record(hint: Any) -> bool:
    return isinstance(hint, type) and dataclasses.is_dataclass(hint)


_SCALARS = (str, int, bool, Decimal, _dt.date, _dt.datetime)


def _kind(hint: Any, where: str) -> None:
    inner, _ = _optional(hint)
    row = _sequence(inner)
    if row is not None:
        _kind(row, f"{where}[]")
        return
    if _is_record(inner):
        _check_record(inner)
        for f in dataclasses.fields(inner):
            _kind(_hints(inner)[f.name], f"{where}.{f.name}")
        return
    if inner in _SCALARS or (isinstance(inner, type) and issubclass(inner, Enum)):
        return
    raise TypeError(
        f"{where} is a {inner!r}: a record's field is text, a number, a Decimal, a "
        "date, a moment, a boolean, a record, or a list of one"
    )


def check(cls: Any) -> None:
    """Refuse a record a route cannot declare, naming the field: when the
    route is declared, not when the first person posts it."""
    _check_record(cls)
    for f in dataclasses.fields(cls):
        _kind(_hints(cls)[f.name], f.name)


def _required(f: dataclasses.Field[Any]) -> bool:
    return f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING


def _default(f: dataclasses.Field[Any]) -> Any:
    if f.default is not dataclasses.MISSING:
        return f.default
    if f.default_factory is not dataclasses.MISSING:
        return f.default_factory()
    return None


# ── The JSON Schema ─────────────────────────────────────────────────────────


def _scalar_schema(hint: Any, meta: Mapping[str, Any]) -> dict[str, Any]:
    if hint is bool:
        return {"type": "boolean"}
    if hint is int:
        out: dict[str, Any] = {"type": "integer"}
        if "min" in meta:
            out["minimum"] = int(meta["min"])
        if "max" in meta:
            out["maximum"] = int(meta["max"])
        return out
    if hint is Decimal:
        out = {
            "type": "string",
            "format": "decimal",
            "pattern": r"^-?\d+(\.\d+)?$",
            "description": "A decimal written as a string, exactly, with no grouping commas.",
        }
        return out
    if hint is _dt.datetime:
        return {"type": "string", "format": "date-time"}
    if hint is _dt.date:
        return {"type": "string", "format": "date"}
    if isinstance(hint, type) and issubclass(hint, Enum):
        return {"type": "string", "enum": [str(each.value) for each in hint]}
    out = {"type": "string"}
    if "max_length" in meta:
        out["maxLength"] = int(meta["max_length"])
    if "choices" in meta:
        out["enum"] = list(meta["choices"])
    return out


def _schema(hint: Any, meta: Mapping[str, Any]) -> dict[str, Any]:
    inner, nullable = _optional(hint)
    row = _sequence(inner)
    if row is not None:
        out: dict[str, Any] = {"type": "array", "items": _schema(row, {})}
    elif _is_record(inner):
        out = schema(inner)
    else:
        out = _scalar_schema(inner, meta)
    if "description" in meta:
        out = {**out, "description": str(meta["description"])}
    if nullable:
        out = {"anyOf": [out, {"type": "null"}]}
    return out


def schema(cls: type) -> dict[str, Any]:
    """The record's JSON Schema: an object of its fields, those without a
    default required, and no other property."""
    check(cls)
    hints = _hints(cls)
    properties = {f.name: _schema(hints[f.name], f.metadata) for f in dataclasses.fields(cls)}
    out: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    required = [f.name for f in dataclasses.fields(cls) if _required(f)]
    if required:
        out["required"] = required
    return out


# ── Reading ─────────────────────────────────────────────────────────────────


def _join(path: str, name: str) -> str:
    return f"{path}.{name}" if path else name


def _decimal(text: str, path: str, meta: Mapping[str, Any], problems: list[Problem]) -> Any:
    if not _DECIMAL.fullmatch(text):
        problems.append(
            Problem(
                path,
                f"{text!r} is not a decimal: write it like 1234.5, with no grouping commas",
            )
        )
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        problems.append(Problem(path, f"{text!r} is not a decimal"))
        return None
    places = meta.get("places")
    if places is not None and -int(value.normalize().as_tuple().exponent) > int(places):
        problems.append(Problem(path, f"{text} has more than {places} decimal places"))
    if "min" in meta and value < Decimal(str(meta["min"])):
        problems.append(Problem(path, f"{text} is less than {meta['min']}"))
    if "max" in meta and value > Decimal(str(meta["max"])):
        problems.append(Problem(path, f"{text} is more than {meta['max']}"))
    return value


def _scalar(
    hint: Any,
    value: Any,
    path: str,
    meta: Mapping[str, Any],
    form: bool,
    problems: list[Problem],
) -> Any:
    """`value` read as `hint`, or None with a problem named."""
    if hint is bool:
        if form:
            return str(value).strip().lower() in ("on", "true", "1", "yes")
        if isinstance(value, bool):
            return value
        problems.append(Problem(path, "a boolean is true or false"))
        return None
    if hint is int:
        if form:
            text = str(value).strip()
            if re.fullmatch(r"-?\d+", text):
                value = int(text)
            else:
                problems.append(Problem(path, f"{text!r} is not a whole number"))
                return None
        if isinstance(value, bool) or not isinstance(value, int):
            problems.append(Problem(path, "a whole number is a JSON integer"))
            return None
        if "min" in meta and value < int(meta["min"]):
            problems.append(Problem(path, f"{value} is less than {meta['min']}"))
        if "max" in meta and value > int(meta["max"]):
            problems.append(Problem(path, f"{value} is more than {meta['max']}"))
        return value
    if not isinstance(value, str):
        what = (
            "a decimal is a string, never a JSON number, which may have been rounded"
            if hint is Decimal
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            else "this is text"
        )
        problems.append(Problem(path, what))
        return None
    text = value.strip()
    if hint is Decimal:
        return _decimal(text, path, meta, problems)
    if hint is _dt.datetime:
        try:
            moment = _dt.datetime.fromisoformat(text)
        except ValueError:
            moment = None
        if moment is None or moment.tzinfo is None:
            problems.append(
                Problem(path, f"{text!r} is not a moment: ISO 8601 with its offset")
            )
            return None
        return moment
    if hint is _dt.date:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            problems.append(Problem(path, f"{text!r} is not a date: YYYY-MM-DD"))
            return None
        try:
            return _dt.date.fromisoformat(text)
        except ValueError:
            problems.append(Problem(path, f"{text!r} is no day in the calendar"))
            return None
    if isinstance(hint, type) and issubclass(hint, Enum):
        for each in hint:
            if str(each.value) == text:
                return each
        problems.append(
            Problem(path, f"{text!r} is not one of {', '.join(str(e.value) for e in hint)}")
        )
        return None
    # Text: as given in JSON; a form's trimmed, as a person meant it.
    said = text if form else value
    if "max_length" in meta and len(said) > int(meta["max_length"]):
        problems.append(Problem(path, f"longer than {meta['max_length']} characters"))
    if "choices" in meta and said and said not in meta["choices"]:
        problems.append(Problem(path, f"{said!r} is not one of {', '.join(meta['choices'])}"))
    return said


def _blank(value: Any) -> bool:
    """A form's value that says nothing: an empty text, or a row of them."""
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, dict):
        return all(_blank(each) for each in value.values())
    if isinstance(value, list):
        return all(_blank(each) for each in value)
    return value is None


def _read(
    hint: Any,
    value: Any,
    path: str,
    meta: Mapping[str, Any],
    form: bool,
    problems: list[Problem],
) -> Any:
    inner, nullable = _optional(hint)
    if value is None or (form and _blank(value) and _sequence(inner) is None):
        if not nullable and not form:
            problems.append(Problem(path, "required"))
        return None
    row = _sequence(inner)
    if row is not None:
        if form and isinstance(value, dict):
            # A form's rows by their numbers, in order, blank ones dropped.
            rows = [value[k] for k in sorted(value)]
            rows = [each for each in rows if not _blank(each)]
        elif isinstance(value, list):
            rows = value
        else:
            problems.append(Problem(path, "a list"))
            return None
        read = [
            _read(row, each, f"{path}[{n}]", {}, form, problems) for n, each in enumerate(rows)
        ]
        return tuple(read) if typing.get_origin(inner) is tuple else read
    if _is_record(inner):
        return _record(inner, value, path, form, problems)
    return _scalar(inner, value, path, meta, form, problems)


def _record(cls: type, given: Any, path: str, form: bool, problems: list[Problem]) -> Any:
    if not isinstance(given, Mapping):
        problems.append(Problem(path, "an object"))
        return None
    hints = _hints(cls)
    fields = {f.name: f for f in dataclasses.fields(cls)}
    if not form:
        for name in given:
            if name not in fields:
                problems.append(
                    Problem(_join(path, str(name)), f"{name!r} is not an input this takes")
                )
    values: dict[str, Any] = {}
    complete = True
    for name, f in fields.items():
        at = _join(path, name)
        present = name in given and not (
            form and _blank(given[name]) and _sequence(_optional(hints[name])[0]) is None
        )
        if not present:
            if _required(f):
                problems.append(Problem(at, "required"))
                complete = False
            continue
        before = len(problems)
        read = _read(hints[name], given[name], at, f.metadata, form, problems)
        if len(problems) > before and read is None:
            if _required(f):
                complete = False
            continue
        if read is None and not _optional(hints[name])[1] and not _required(f):
            continue
        values[name] = read
    if not complete:
        return None
    try:
        return cls(**values)
    except (TypeError, ValueError) as refused:
        problems.append(Problem(path, str(refused)))
        return None


def from_json(cls: type, arguments: Any) -> Any:
    """The record `arguments` makes, an agent's JSON object; `Unread` naming
    every field that does not read, and every argument it does not take."""
    check(cls)
    problems: list[Problem] = []
    record = _record(cls, arguments, "", False, problems)
    if problems or record is None:
        raise Unread(problems or [Problem("", "the arguments do not make the record")])
    return record


def _nest(form: Mapping[str, str], names: set[str]) -> dict[str, Any]:
    """A form's path-named fields as nested objects, rows as dicts by their
    numbers; a name whose first step is not one of the record's is left out,
    as is one that does not parse as a path."""
    tree: dict[str, Any] = {}
    for name, value in form.items():
        steps: list[str | int] = []
        at = 0
        while at < len(name):
            m = _STEP.match(name, at)
            if m is None:
                steps = []
                break
            steps.append(m.group(1) if m.group(1) is not None else int(m.group(2)))
            at = m.end()
            if at < len(name) and name[at] == ".":
                at += 1
        if not steps or not isinstance(steps[0], str) or steps[0] not in names:
            continue
        if any(isinstance(s, int) and s > MOST_ROWS for s in steps):
            continue
        node: Any = tree
        for step in steps[:-1]:
            if not isinstance(node, dict):
                break
            node = node.setdefault(step, {})
        else:
            if isinstance(node, dict):
                node[steps[-1]] = value
    return tree


def from_form(cls: type, form: Mapping[str, str]) -> tuple[Any, tuple[Problem, ...]]:
    """The record a form posted, and every field that did not read, by its
    path. A field that does not read is left at its default; the record is
    None only where one it requires is missing."""
    check(cls)
    problems: list[Problem] = []
    tree = _nest(form, {f.name for f in dataclasses.fields(cls)})
    record = _record(cls, tree, "", True, problems)
    return record, tuple(problems)


# ── Answering ───────────────────────────────────────────────────────────────


def to_json(value: Any) -> Any:
    """A record, or anything made of the same kinds, as JSON: a Decimal as
    its string, a date or a moment ISO 8601, an enum its value."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_json(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {str(k): to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_json(each) for each in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (_dt.date, _dt.datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"a {type(value).__name__} is not something a tool answers")
