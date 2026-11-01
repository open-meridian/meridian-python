"""open-meridian 0.34.0 to 0.35.0: each role is one generated class
(spec/each-role-is-one-generated-class; rulings 1004, 1005, 1009 to 1023).

A role's acts leave the connection for the role's class, and `receive` is
gone. What can be read off the plugin's own code is rewritten, the whole
plugin read first (`given`), since a `receive` call in one file names the
methods of a class in another:

- `receive-to-role-methods`: a `<conn>.receive(<row>=<obj>.<method>, ...)`
  call, outside the tests, whose handlers are all methods of one class the
  plugin defines, on the events of one role it declares. The class gains
  that role's base, its handler methods are renamed `on_<row>` (every
  reference with them), `seed=False` becomes its `seed = False`, a `plugin`
  it was given leaves it, and the call is removed;
- `sdk-handlers-dropped`: a Trader's and a Pricer's handlers dropped from a
  `receive` call, those classes being registered by themselves;
- `common-logic-renamed`: the SDK's renamed methods and arguments, and the
  connection given first to a Trader, a Pricer or a feed dropped (a
  recorder's call becoming `recorder.bind(...)`);
- `self-plugin-act-to-self`: in a role class, `self.plugin.<act>(...)` on
  `self`, and a helper given `self.plugin` given `self`;
- `template-entry-to-run`: an entry point a role's 0.34.0 template wrote and
  the plugin left unchanged, replaced by 0.35.0's;
- `listings-edge-glue-dropped` and `copied-bodies-to-sdk`: 924's items 3, 4,
  6 and 9, rewritten once the SDK carries what replaces them (924's helpers,
  SDK 0.35's second part): until then neither finds anything to rewrite.

What is left by hand is found in each file as it ends: an entry point
connecting by hand, an act on the connection, a `receive` no rewrite
reached, a role class lacking a required event, a suite test hearing
through `recorder.receive`, and a helper 924 placed that the plugin adopts
by hand. The roles' surfaces are 0.35.0's, as `roles.json` beside this
records them, so the step reads the same whatever SDK runs it later.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import libcst as cst
from libcst.metadata import MetadataWrapper, ParentNodeProvider, PositionProvider

from .. import Finding, Rewritten
from .._cst import add_import, dotted, is_test, line_of

HERE = Path(__file__).parent
TARGET = "0.35.0"

#: Each role's events (row: method), its required events and its acts, as
#: 0.35.0's generated bases hold them.
SURFACES: dict[str, dict[str, Any]] = json.loads((HERE / "roles.json").read_text())
#: A row by the keyword `receive` named it by (`observations_wanted`).
ROW_OF: dict[str, str] = {
    method.removeprefix("on_"): row
    for surface in SURFACES.values()
    for row, method in surface["events"].items()
}
#: The roles hearing each row.
HEARERS: dict[str, set[str]] = {}
for _role, _surface in SURFACES.items():
    for _row in _surface["events"]:
        HEARERS.setdefault(_row, set()).add(_role)
ACTS: dict[str, set[str]] = {role: set(s["acts"]) for role, s in SURFACES.items()}
EVERY_ACT: set[str] = set().union(*ACTS.values())

#: The SDK's common logic, each a role's class from 0.35.0.
TRADER = "meridian.roles.connectivity.Trader"
PRICER = "meridian.roles.pricing.Pricer"
PAIRS = "meridian.roles.data.pairs.Feed"
CONTRACTS = "meridian.roles.data.event_contracts.Feed"
LISTINGS = "meridian.roles.data.listings.Feed"
LOGIC = {TRADER: "connectivity", PRICER: "pricing", PAIRS: "data", CONTRACTS: "data",
         LISTINGS: "data"}  # fmt: skip
#: A Trader's handlers and a Pricer's, which `receive` was handed.
TRADER_HANDLERS = {
    "on_placement": "on_placement_updated",
    "on_instruction": "on_trading_instruction_changed",
    "on_execution": "on_execution_recorded",
}
FEED_HANDLERS = {"on_want": "on_observations_wanted", "on_withdrawn": "on_want_withdrawn"}
#: The feeds' methods renamed where a role's act has the name (0.35.0).
FEED_METHODS = {
    PAIRS: {"record_trades": "record_trades_of", "record_quotes": "record_quotes_of"},
    CONTRACTS: {"record_outcomes": "record_outcomes_of", "record_bars": "record_bars_of"},
    LISTINGS: {"seed": "seed_symbols"},
}
#: The templates whose 0.34.0 entry point is replaced while unchanged.
ENTRIES = ("data", "operations", "connectivity", "pricing")
#: What a 0.34.0 entry point did on start that 0.35.0's leaves to the class's
#: `on_start`, where the class has none: the data template's licences read
#: and its products resolved, in its convert.py's `Converter`.
STARTS: dict[str, tuple[str, str, str]] = {
    "data": (
        "convert.py",
        "Converter",
        "async def on_start(self) -> None:\n"
        '    """Before anything is heard: its datasets\' licences read, and the\n'
        '    vendor\'s symbols resolved."""\n'
        "    await self.read_licences()\n"
        "    await self.map_products(time.time_ns())\n",
    ),
}
_TEMPLATE_PACKAGE = "reference_plugin"
_MAIN = re.compile(r"^src/(?P<package>[A-Za-z_][A-Za-z0-9_]*)/__main__\.py$")


#: 924's copies the fit review found, which the SDK's helpers replace once
#: they carry them (SDK 0.35's second part): a definition's body, its
#: vendor's names normalised (`_normalised`), by its digest, and the SDK's
#: module and name replacing it. Empty until those helpers land, so
#: `copied-bodies-to-sdk` rewrites nothing before then.
COPIED: dict[str, tuple[str, str]] = {}


def _normalised(code: str) -> str:
    """A definition as the fit review compared copies: its own name and its
    vendor's words dropped, its layout ignored."""
    code = re.sub(r"#[^\n]*", "", code)
    code = re.sub(r'"""(?:.|\n)*?"""', "", code)
    return re.sub(r"\s+", " ", code).strip()


def _feed_keeps_the_edge() -> bool:
    """Whether the SDK's listings feed does the edge glue itself (924's item
    4): until it does, a plugin's own glue is kept."""
    from ...roles.data import listings

    return callable(getattr(listings.Feed, "at_the_edge", None))


def _entries() -> dict[str, tuple[str, str]]:
    """Each template's 0.34.0 entry point, by its text: its role, and 0.35.0's."""
    return {
        (HERE / "entry" / f"{role}-0.34.0.txt").read_text(): (
            role,
            (HERE / "entry" / f"{role}-0.35.0.txt").read_text(),
        )
        for role in ENTRIES
    }


def _template_of(path: str, text: str) -> tuple[str, str] | None:
    """The role whose 0.34.0 template wrote this entry point, unchanged, and
    0.35.0's in its place; None for any other file."""
    match = _MAIN.match(path)
    if match is None:
        return None
    package = match.group("package")
    for before, (role, after) in _entries().items():
        # As `meridian plugin new` wrote it: the template's package renamed.
        if before.replace(_TEMPLATE_PACKAGE, package) == text:
            return role, after.replace(_TEMPLATE_PACKAGE, package)
    return None


# ── The plugin, read whole ──────────────────────────────────────────────


class _Names(cst.CSTVisitor):
    """What each name a file imports is, in full: `data` for `from
    meridian.roles import data` is `meridian.roles.data`."""

    def __init__(self) -> None:
        self.full: dict[str, str] = {}

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            name = dotted(alias.name) or ""
            if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
                self.full[alias.asname.name.value] = name
            else:
                self.full[name.split(".")[0]] = name.split(".")[0]

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.relative or node.module is None or isinstance(node.names, cst.ImportStar):
            return
        module = dotted(node.module) or ""
        for alias in node.names:
            name = dotted(alias.name) or ""
            local = name
            if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
                local = alias.asname.name.value
            self.full[local] = f"{module}.{name}"


def _resolved(node: cst.BaseExpression, names: dict[str, str]) -> str:
    """A dotted name as the SDK's full name, through the file's imports."""
    text = dotted(node) or ""
    head, _, rest = text.partition(".")
    if head in names:
        return names[head] + (f".{rest}" if rest else "")
    return text


@dataclass
class _Class:
    name: str
    path: str
    methods: set[str] = field(default_factory=set)
    bases: list[str] = field(default_factory=list)
    # A `plugin` dataclass field, or an `__init__` taking `plugin` and
    # keeping it as `self.plugin` or `self._plugin`.
    given_plugin: bool = False


@dataclass
class _Plan:
    """What `receive-to-role-methods` does to one class."""

    role: str
    renames: dict[str, str] = field(default_factory=dict)
    seed_false: bool = False
    add_base: bool = True


@dataclass
class _Receive:
    """One `receive` call and what becomes of it."""

    path: str
    line: int
    column: int
    # The keywords dropped (the SDK's own handlers) and whether the call goes.
    dropped: set[str] = field(default_factory=set)
    removed: bool = False


@dataclass
class _Plugin:
    declared: list[str] = field(default_factory=list)
    classes: dict[str, _Class] = field(default_factory=dict)
    plans: dict[str, _Plan] = field(default_factory=dict)
    receives: list[_Receive] = field(default_factory=list)
    # Objects bound to the SDK's common logic, by their dotted name in a
    # file (`trader`, `self.trader`), and what each is.
    objects: dict[str, str] = field(default_factory=dict)
    # The method renames reaching every reference in the plugin.
    renames: dict[str, str] = field(default_factory=dict)
    # An `on_start` added to a class whose template's entry point is replaced.
    starts: dict[str, str] = field(default_factory=dict)


_plugin = _Plugin()


def _logic_of(name: str, classes: dict[str, _Class], seen: set[str] | None = None) -> str:
    """The SDK common logic a class is or extends (its full name), or ""."""
    if name in LOGIC:
        return name
    held = classes.get(name.rsplit(".", 1)[-1])
    if held is None or (seen is not None and held.name in seen):
        return ""
    for base in held.bases:
        found = _logic_of(base, classes, (seen or set()) | {held.name})
        if found:
            return found
    return ""


def _role_of(name: str, classes: dict[str, _Class], seen: set[str] | None = None) -> str:
    """The role a class is the class of: by its base, its SDK common logic,
    or the plan this step made for it; "" for none."""
    match = re.fullmatch(r"meridian\.roles\.(\w+)\.Role", name)
    if match and match.group(1) in SURFACES:
        return match.group(1)
    if name in LOGIC:
        return LOGIC[name]
    local = name.rsplit(".", 1)[-1]
    if local in _plugin.plans:
        return _plugin.plans[local].role
    held = classes.get(local)
    if held is None or (seen is not None and held.name in seen):
        return ""
    for base in held.bases:
        found = _role_of(base, classes, (seen or set()) | {held.name})
        if found:
            return found
    return ""


class _Reader(cst.CSTVisitor):
    """A file's classes, the SDK's common logic it builds, and its `receive`
    calls."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, path: str, names: dict[str, str]) -> None:
        super().__init__()
        self.path = path
        self.names = names
        self.classes: list[_Class] = []
        self.built: list[tuple[str, str]] = []
        self.receives: list[tuple[int, int, cst.Call]] = []
        self._in: list[_Class] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        held = _Class(
            node.name.value,
            self.path,
            bases=[_resolved(arg.value, self.names) for arg in node.bases],
        )
        for statement in node.body.body:
            if isinstance(statement, cst.FunctionDef):
                held.methods.add(statement.name.value)
                if statement.name.value == "__init__":
                    params = [p.name.value for p in statement.params.params]
                    held.given_plugin |= "plugin" in params[1:2]
            elif isinstance(statement, cst.SimpleStatementLine):
                for small in statement.body:
                    if (
                        isinstance(small, cst.AnnAssign)
                        and isinstance(small.target, cst.Name)
                        and small.target.value == "plugin"
                    ):
                        held.given_plugin = True
        self.classes.append(held)
        self._in.append(held)

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        self._in.pop()

    def visit_Assign(self, node: cst.Assign) -> None:
        if not isinstance(node.value, cst.Call):
            return
        built = _resolved(node.value.func, self.names)
        for target in node.targets:
            name = dotted(target.target)
            if name is not None:
                self.built.append((name, built))

    def visit_Call(self, node: cst.Call) -> None:
        if (
            isinstance(node.func, cst.Attribute)
            and node.func.attr.value == "receive"
            and any(arg.keyword is not None for arg in node.args)
        ):
            at = self.get_metadata(PositionProvider, node).start
            self.receives.append((at.line, at.column, node))


def given(files: dict[str, str]) -> None:
    """The plugin read whole, before any file is rewritten."""
    global _plugin
    plugin = _Plugin()
    pyproject = files.get("pyproject.toml", "")
    try:
        held = tomllib.loads(pyproject).get("tool", {}).get("meridian", {}).get("roles", [])
        plugin.declared = [str(role) for role in held if str(role) in SURFACES]
    except tomllib.TOMLDecodeError:
        plugin.declared = []
    readers: list[_Reader] = []
    for path, text in sorted(files.items()):
        if not path.endswith(".py") or "meridian" not in text and "class " not in text:
            continue
        try:
            module = cst.parse_module(text)
        except cst.ParserSyntaxError:
            continue
        names = _Names()
        module.visit(names)
        reader = _Reader(path, names.full)
        MetadataWrapper(module).visit(reader)
        readers.append(reader)
        for each in reader.classes:
            plugin.classes.setdefault(each.name, each)
    _plugin = plugin
    for path, text in files.items():
        found = _template_of(path, text)
        if found is not None and found[0] in STARTS:
            held_in, name, start = STARTS[found[0]]
            held = plugin.classes.get(name)
            folder = path.rsplit("/", 1)[0]
            if (
                held is not None
                and held.path == f"{folder}/{held_in}"
                and "on_start" not in held.methods
            ):
                plugin.starts[name] = start
    for reader in readers:
        for name, built in reader.built:
            logic = _logic_of(built, plugin.classes)
            if logic:
                plugin.objects[name] = logic
    owners: dict[str, list[str]] = {}
    for each in plugin.classes.values():
        for method in each.methods:
            owners.setdefault(method, []).append(each.name)
    for reader in readers:
        if is_test(reader.path):
            continue
        for line, column, call in reader.receives:
            _plan_receive(plugin, reader.path, line, column, call, owners)
    # A class renamed's methods are renamed wherever they are named, when no
    # other class of the plugin has a method of the same name.
    for name, plan in plugin.plans.items():
        for old, new in plan.renames.items():
            if owners.get(old) == [name]:
                plugin.renames[old] = new


def _plan_receive(
    plugin: _Plugin,
    path: str,
    line: int,
    column: int,
    call: cst.Call,
    owners: dict[str, list[str]],
) -> None:
    handlers: dict[str, cst.BaseExpression] = {}
    seed_false = False
    for arg in call.args:
        if arg.keyword is None:
            return
        keyword = arg.keyword.value
        if keyword == "seed":
            seed_false = isinstance(arg.value, cst.Name) and arg.value.value == "False"
        elif keyword == "subjects":
            return  # what a class answers in `subjects()`: by hand
        elif keyword in ROW_OF:
            handlers[keyword] = arg.value
        else:
            return
    receive = _Receive(path, line, column)
    mine: dict[str, str] = {}
    for keyword, value in handlers.items():
        if not isinstance(value, cst.Attribute):
            return
        owner = dotted(value.value) or ""
        method = value.attr.value
        logic = plugin.objects.get(owner, "")
        if (logic == TRADER and method in TRADER_HANDLERS) or (
            logic == PRICER and method == "heard"
        ):
            receive.dropped.add(keyword)
            continue
        mine[keyword] = method
    if mine:
        classes = set.intersection(*(set(owners.get(m, ())) for m in mine.values()))
        if len(classes) != 1:
            if receive.dropped:
                plugin.receives.append(receive)
            return
        (name,) = classes
        rows = [ROW_OF[keyword] for keyword in mine]
        hearing = set.intersection(*(HEARERS[row] for row in rows))
        already = _role_of(name, plugin.classes)
        roles = {already} if already else hearing & set(plugin.declared)
        if len(roles) != 1 or not roles <= hearing:
            if receive.dropped:
                plugin.receives.append(receive)
            return
        (role,) = roles
        plan = plugin.plans.setdefault(name, _Plan(role, add_base=not already))
        for keyword, method in mine.items():
            wanted = SURFACES[role]["events"][ROW_OF[keyword]]
            if method != wanted:
                plan.renames[method] = wanted
        plan.seed_false |= seed_false
    receive.removed = len(receive.dropped) + len(mine) == len(handlers)
    plugin.receives.append(receive)


# ── Rewriting a file ────────────────────────────────────────────────────


def _recorder(arg: cst.BaseExpression) -> cst.BaseExpression | None:
    """The recorder a call was given in the connection's place: `recorder`
    or `cast(meridian.Plugin, recorder)`; None for anything else."""
    if isinstance(arg, cst.Call) and (dotted(arg.func) or "").endswith("cast") and arg.args:
        arg = arg.args[-1].value
    if isinstance(arg, cst.Call):
        # A recorder made in place: `Recorder("x")`, a `Lake(...)` subclass.
        made = (dotted(arg.func) or "").rsplit(".", 1)[-1]
        return arg if made.endswith("Recorder") or made == "Lake" else None
    name = dotted(arg) or ""
    return arg if "recorder" in name.lower() or name.endswith("lake") else None


class _Rewriter(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider, ParentNodeProvider)

    def __init__(self, path: str, names: dict[str, str]) -> None:
        super().__init__()
        self.path = path
        self.names = names
        self.rules: list[str] = []
        self.classes: list[str] = []
        self.imports: set[str] = set()
        self.imports_plain: set[str] = set()
        self.findings: list[tuple[str, int]] = []
        self.cancelled: set[str] = set()
        self.receives = {
            (each.line, each.column): each for each in _plugin.receives if each.path == path
        }

    # ── classes ──

    def _role(self) -> str:
        for name in reversed(self.classes):
            role = _role_of(name, _plugin.classes)
            if role:
                return role
        return ""

    def _logic(self) -> str:
        return _logic_of(self.classes[-1], _plugin.classes) if self.classes else ""

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.classes.append(node.name.value)

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        name = self.classes.pop()
        if _logic_of(name, _plugin.classes) == LISTINGS and _feed_keeps_the_edge():
            body: list[Any] = [s for s in updated_node.body.body if not _edge_glue(s)]
            if len(body) != len(updated_node.body.body):
                self.rules.append("listings-edge-glue-dropped")
                updated_node = updated_node.with_changes(
                    body=updated_node.body.with_changes(body=body)
                )
        plan = _plugin.plans.get(name)
        if plan is None or _plugin.classes.get(name, _Class("", "")).path != self.path:
            return updated_node
        body = list(updated_node.body.body)
        if plan.add_base:
            base = cst.Arg(value=cst.Attribute(cst.Name(plan.role), cst.Name("Role")))
            updated_node = updated_node.with_changes(bases=[*updated_node.bases, base])
            self.imports.add(plan.role)
            self.rules.append("receive-to-role-methods")
        kept: list[Any] = []
        carried: Any = None
        for statement in body:
            if _plugin.classes[name].given_plugin and _is_plugin_field(statement):
                self.rules.append("receive-to-role-methods")
                # Its blank lines and comments stay, on the next statement.
                carried = statement.leading_lines
                continue
            if carried is not None and isinstance(
                statement, cst.SimpleStatementLine | cst.BaseCompoundStatement
            ):
                statement = statement.with_changes(
                    leading_lines=[*carried, *statement.leading_lines]
                )
                carried = None
            kept.append(statement)
        if name in _plugin.starts:
            indented = "".join(f"    {line}" for line in _plugin.starts[name].splitlines(True))
            parsed = cst.parse_module(f"class _:\n{indented}").body[0]
            assert isinstance(parsed, cst.ClassDef)
            method: Any = parsed.body.body[0]
            at = next(
                (i for i, s in enumerate(kept) if isinstance(s, cst.FunctionDef)), len(kept)
            )
            while (
                at < len(kept)
                and isinstance(kept[at], cst.FunctionDef)
                and kept[at].name.value.startswith("__")
            ):
                at += 1
            kept.insert(at, method.with_changes(leading_lines=[cst.EmptyLine(indent=False)]))
            self.imports_plain.add("time")
            self.rules.append("template-entry-to-run")
        if plan.seed_false:
            at = 1 if kept and _is_docstring(kept[0]) else 0
            seed = cst.parse_statement("seed = False\n")
            kept.insert(at, seed.with_changes(leading_lines=[cst.EmptyLine(indent=False)]))
            self.rules.append("receive-to-role-methods")
        return updated_node.with_changes(body=updated_node.body.with_changes(body=kept))

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        name = updated_node.name.value
        owner = self.classes[-1] if self.classes else ""
        plan = _plugin.plans.get(owner)
        if plan is not None and name in plan.renames:
            self.rules.append("receive-to-role-methods")
            return updated_node.with_changes(name=cst.Name(plan.renames[name]))
        logic = self._logic()
        renamed = _logic_rename(logic, name)
        if renamed and self.classes:
            self.rules.append("common-logic-renamed")
            return updated_node.with_changes(name=cst.Name(renamed))
        if name == "__init__" and plan is not None and _plugin.classes[owner].given_plugin:
            params = list(updated_node.params.params)
            if len(params) > 1 and params[1].name.value == "plugin":
                if len(params) == 2:
                    params[0] = params[0].with_changes(comma=cst.MaybeSentinel.DEFAULT)
                del params[1]
                kept_body: list[Any] = [
                    s for s in updated_node.body.body if not _keeps_plugin(s)
                ]
                self.rules.append("receive-to-role-methods")
                return updated_node.with_changes(
                    params=updated_node.params.with_changes(params=params),
                    body=updated_node.body.with_changes(body=kept_body),
                )
        return updated_node

    # ── references ──

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.BaseExpression:
        name = updated_node.attr.value
        owner = dotted(updated_node.value) or ""
        if name in _plugin.renames:
            self.rules.append("receive-to-role-methods")
            return updated_node.with_changes(attr=cst.Name(_plugin.renames[name]))
        logic = _plugin.objects.get(owner, "")
        if owner == "self":
            logic = self._logic()
        renamed = _logic_rename(logic, name)
        if renamed:
            self.rules.append("common-logic-renamed")
            return updated_node.with_changes(attr=cst.Name(renamed))
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        at = self.get_metadata(PositionProvider, original_node).start
        receive = self.receives.get((at.line, at.column))
        if receive is not None and receive.dropped and not receive.removed:
            args = [
                arg
                for arg in updated_node.args
                if arg.keyword is None or arg.keyword.value not in receive.dropped
            ]
            self.rules.append("sdk-handlers-dropped")
            updated_node = updated_node.with_changes(args=_without(updated_node.args, args))
        func = updated_node.func
        # self.plugin.<act>(...) on self, inside a role class.
        role = self._role()
        if (
            role
            and isinstance(func, cst.Attribute)
            and dotted(func.value) in ("self.plugin", "self._plugin")
            and func.attr.value in ACTS[role]
        ):
            self.rules.append("self-plugin-act-to-self")
            updated_node = updated_node.with_changes(
                func=func.with_changes(value=cst.Name("self"))
            )
        # A helper given self.plugin, given self.
        helper = _resolved(updated_node.func, self.names).startswith("meridian.") or (
            isinstance(updated_node.func, cst.Attribute)
            and updated_node.func.attr.value in ROLE_FIRST
            and bool(updated_node.args)
            and dotted(updated_node.args[0].value) in ("self.plugin", "self._plugin")
        )
        if role and helper:
            args = []
            for arg in updated_node.args:
                if dotted(arg.value) in ("self.plugin", "self._plugin"):
                    self.rules.append("self-plugin-act-to-self")
                    arg = arg.with_changes(value=cst.Name("self"))
                args.append(arg)
            updated_node = updated_node.with_changes(args=args)
        # Trader.run(poll_seconds, hear=...): its arguments leave it.
        if (
            isinstance(func, cst.Attribute)
            and func.attr.value == "run"
            and _plugin.objects.get(dotted(func.value) or "") == TRADER
            and updated_node.args
        ):
            self.rules.append("common-logic-renamed")
            return updated_node.with_changes(args=[])
        # The connection given first to the SDK's logic, or a class given it.
        built = _resolved(updated_node.func, self.names)
        local = built.rsplit(".", 1)[-1]
        logic = bool(_logic_of(built, _plugin.classes))
        # A class this step makes a role class took the connection first,
        # whatever it was given there; the SDK's own only where it is one.
        given = local in _plugin.plans and _plugin.classes[local].given_plugin
        positional = [arg for arg in updated_node.args if arg.keyword is None and not arg.star]
        connection = bool(positional) and _is_connection(positional[0].value)
        if positional and given and not connection and is_test(self.path):
            # A stand-in for the connection, which a class no longer takes.
            line = self.get_metadata(PositionProvider, original_node).start.line
            self.findings.append(("suite-producer-to-role", line))
        if positional and ((logic and connection) or given):
            first = positional[0]
            rest = [arg for arg in updated_node.args if arg is not first]
            made = updated_node.with_changes(args=_without(updated_node.args, rest))
            self.rules.append(
                "common-logic-renamed"
                if _logic_of(built, _plugin.classes)
                else "receive-to-role-methods"
            )
            recorder = _recorder(first.value)
            if recorder is not None:
                return cst.Call(
                    func=cst.Attribute(recorder, cst.Name("bind")), args=[cst.Arg(made)]
                )
            return made
        return updated_node

    # ── statements ──

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        for small in original_node.body:
            call = _call_of(small)
            if call is not None:
                at = self.get_metadata(PositionProvider, call).start
                receive = self.receives.get((at.line, at.column))
                if receive is not None and receive.removed:
                    if isinstance(small, cst.Assign):
                        name = dotted(small.targets[0].target)
                        if name is not None:
                            self.cancelled.add(name)
                    self.rules.append("receive-to-role-methods")
                    return cst.RemovalSentinel.REMOVE
            if (
                isinstance(small, cst.Expr)
                and isinstance(small.value, cst.Call)
                and isinstance(small.value.func, cst.Attribute)
                and small.value.func.attr.value == "cancel"
                and dotted(small.value.func.value) in self.cancelled
            ):
                return cst.RemovalSentinel.REMOVE
        return updated_node


def _edge_glue(statement: Any) -> bool:
    """An `at_the_edge` method, or a `_record` override that only calls it
    and then `super()._record`."""
    if not isinstance(statement, cst.FunctionDef):
        return False
    if statement.name.value == "at_the_edge":
        return True
    if statement.name.value != "_record":
        return False
    code = cst.Module(body=[statement]).code
    calls = [s for s in statement.body.body if not _is_docstring(cast(Any, s))]
    return len(calls) <= 2 and "at_the_edge(" in code and "super()._record(" in code


def _copied(statement: cst.BaseStatement) -> tuple[str, str] | None:
    """The SDK's module and name replacing a definition the fit review found
    copied (`COPIED`), or None."""
    if not COPIED or not isinstance(statement, cst.FunctionDef | cst.ClassDef):
        return None
    import hashlib

    code = _normalised(cst.Module(body=[statement]).code)
    return COPIED.get(hashlib.sha256(code.encode()).hexdigest())


def _import_plain(module: cst.Module, name: str) -> cst.Module:
    """`import name`, where the file has none."""
    from libcst.codemod import CodemodContext
    from libcst.codemod.visitors import AddImportsVisitor

    context = CodemodContext()
    AddImportsVisitor.add_needed_import(context, name)
    return AddImportsVisitor(context).transform_module(module)


def _logic_rename(logic: str, name: str) -> str:
    if logic == TRADER:
        return TRADER_HANDLERS.get(name, "")
    if logic in (PAIRS, CONTRACTS, LISTINGS):
        return FEED_HANDLERS.get(name, "") or FEED_METHODS[logic].get(name, "")
    return ""


def _call_of(small: cst.BaseSmallStatement) -> cst.Call | None:
    """The `receive` call a statement is wholly: awaited, called, or handed
    to `create_task` and kept."""
    value: cst.BaseExpression | None = None
    if isinstance(small, cst.Expr) or isinstance(small, cst.Assign) and len(small.targets) == 1:
        value = small.value
    if isinstance(value, cst.Await):
        value = value.expression
    if (
        isinstance(value, cst.Call)
        and (dotted(value.func) or "").endswith("create_task")
        and value.args
    ):
        value = value.args[0].value
    if (
        isinstance(value, cst.Call)
        and isinstance(value.func, cst.Attribute)
        and value.func.attr.value == "receive"
    ):
        return value
    return None


def _without(given: Sequence[cst.Arg], kept: list[cst.Arg]) -> list[cst.Arg]:
    """The arguments kept, each with its own comma, so a call written one
    argument a line stays so; the last kept takes the last given's comma."""
    if kept and given and kept[-1] is not given[-1]:
        kept[-1] = kept[-1].with_changes(comma=given[-1].comma)
    return kept


def _is_docstring(statement: Any) -> bool:
    return (
        isinstance(statement, cst.SimpleStatementLine)
        and isinstance(statement.body[0], cst.Expr)
        and isinstance(statement.body[0].value, cst.SimpleString | cst.ConcatenatedString)
    )


def _is_plugin_field(statement: Any) -> bool:
    return (
        isinstance(statement, cst.SimpleStatementLine)
        and isinstance(statement.body[0], cst.AnnAssign)
        and isinstance(statement.body[0].target, cst.Name)
        and statement.body[0].target.value == "plugin"
    )


def _keeps_plugin(statement: Any) -> bool:
    """`self.plugin = plugin` or `self._plugin = plugin`."""
    if not isinstance(statement, cst.SimpleStatementLine):
        return False
    small = statement.body[0]
    return (
        isinstance(small, cst.Assign)
        and dotted(small.targets[0].target) in ("self.plugin", "self._plugin")
        and dotted(small.value) == "plugin"
    )


def _is_connection(arg: cst.BaseExpression) -> bool:
    """Whether a first argument is the connection a 0.34.0 constructor took:
    `plugin`, `self.plugin`, `request.plugin`, or a recorder in its place."""
    name = dotted(arg) or ""
    return name.rsplit(".", 1)[-1] in ("plugin", "_plugin") or _recorder(arg) is not None


#: The SDK's methods given a role object first from 0.35.0, where 0.34.0's
#: were given the connection: a venue resolved, the replacements and event
#: groups caught up, the template catalogue read, a job run, the `ems`'s
#: reference check.
ROLE_FIRST = frozenset(
    {"resolve", "catch_up", "load", "template", "read", "run", "permitted", "hold"}
)


def _entry(path: str, text: str) -> Rewritten | None:
    found = _template_of(path, text)
    if found is None:
        return None
    return Rewritten(found[1], ("template-entry-to-run",))


def rewrite(path: str, text: str) -> Rewritten:
    entry = _entry(path, text)
    if entry is not None:
        return entry
    if not path.endswith(".py"):
        return Rewritten(text)
    module = cst.parse_module(text)
    names = _Names()
    module.visit(names)
    rewriter = _Rewriter(path, names.full)
    written = MetadataWrapper(module).visit(rewriter)
    replaced = []
    body = []
    for statement in written.body:
        found = _copied(statement)
        if found is None:
            body.append(statement)
        else:
            replaced.append(found)
            rewriter.rules.append("copied-bodies-to-sdk")
    if replaced:
        written = written.with_changes(body=body)
        for source, name in replaced:
            written = add_import(written, source, name)
    for role in sorted(rewriter.imports):
        written = add_import(written, "meridian.roles", role)
    for name in sorted(rewriter.imports_plain):
        written = _import_plain(written, name)
    if not rewriter.rules:
        return Rewritten(text)
    findings = tuple(
        Finding(rule, path, line, line_of(text, line)) for rule, line in rewriter.findings
    )
    return Rewritten(written.code, tuple(rewriter.rules), findings)


# ── Left by hand ────────────────────────────────────────────────────────


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, path: str, names: dict[str, str]) -> None:
        super().__init__()
        self.path = path
        self.names = names
        self.found: list[tuple[str, int, str]] = []
        self.classes: list[str] = []
        self.connected: set[str] = set()

    def _line(self, node: cst.CSTNode) -> int:
        return self.get_metadata(PositionProvider, node).start.line

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.classes.append(node.name.value)
        role = _role_of(node.name.value, _plugin.classes)
        if not role or _logic_of(node.name.value, _plugin.classes):
            return
        bases = [_resolved(arg.value, self.names) for arg in node.bases]
        if f"meridian.roles.{role}.Role" not in bases:
            return
        held = _plugin.classes.get(node.name.value)
        methods = held.methods if held is not None else set()
        for row in SURFACES[role]["required"]:
            method = SURFACES[role]["events"][row]
            if method not in methods:
                self.found.append(("required-event-missing", self._line(node), method))

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        self.classes.pop()

    def visit_WithItem(self, node: cst.WithItem) -> None:
        if node.asname is not None and _is_connect(node.item, self.names):
            name = dotted(node.asname.name)
            if name:
                self.connected.add(name)

    def visit_Assign(self, node: cst.Assign) -> None:
        if _is_connect(node.value, self.names):
            for target in node.targets:
                name = dotted(target.target)
                if name:
                    self.connected.add(name)

    def visit_Call(self, node: cst.Call) -> None:
        if _is_connect(node, self.names) and not is_test(self.path):
            self.found.append(("connect-to-run", self._line(node), ""))
        func = node.func
        if not isinstance(func, cst.Attribute):
            return
        owner = dotted(func.value) or ""
        name = func.attr.value
        if name == "receive" and any(arg.keyword is not None for arg in node.args):
            if is_test(self.path) and "recorder" in owner.lower():
                self.found.append(("suite-producer-to-role", self._line(node), ""))
            elif not is_test(self.path) or owner in self.connected:
                self.found.append(("receive-not-rewritten", self._line(node), ""))
            return
        if name not in EVERY_ACT:
            return
        last = owner.rsplit(".", 1)[-1]
        on_connection = owner in self.connected or last in ("plugin", "_plugin")
        if not on_connection:
            return
        holders = sorted(role for role in _plugin.declared if name in ACTS[role])
        said = ", ".join(holders) if holders else "no role it declares"
        self.found.append(("act-on-the-connection", self._line(node), f"{name}: {said}"))


def _is_connect(node: cst.BaseExpression, names: dict[str, str]) -> bool:
    if isinstance(node, cst.Await):
        node = node.expression
    if not isinstance(node, cst.Call):
        return False
    return _resolved(node.func, names) == "meridian.connect"


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py") or "meridian" not in text and ".receive(" not in text:
        return []
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError:
        return []
    names = _Names()
    module.visit(names)
    visitor = _Left(path, names.full)
    MetadataWrapper(module).visit(visitor)
    found = []
    for rule, line, said in visitor.found:
        shown = line_of(text, line)
        found.append(Finding(rule, path, line, f"{shown}  [{said}]" if said else shown))
    return found
