"""open-meridian 0.35.2 to 0.35.3: a fix, with no contract change.

Nothing is rewritten: what a plugin calls kept its shape. What the plugin
step found in plugins already on 0.35, which no earlier step reached, is
named by hand, each in the plugin as it is (`given` reads it whole first,
since a role class's base may be another file's class):

- `named-calls-dataset`: a `named` override calling `dataset`, which from
  0.35 calls `named` -- endless;
- `timeliness-overridden`: a method `timeliness(...)` on a class, where a
  listings feed's `timeliness` is a property from 0.35;
- `subjects-shadowed`: a role class holding a field or attribute named
  `subjects`, which hides the role's `subjects()`;
- `old-handler-name`: a call of a 0.34 handler name (`on_want`,
  `on_withdrawn`, `on_placement`, `on_instruction`, `on_execution`, a
  feed's `seed(...)`) the plugin defines no method of;
- `receive-gone`: a `receive(<row>=...)` left, which 0.35 removed;
- `stand-in-read`: a test reading `<x>.plugin.on(...)`, the connection's
  stand-in, which holds no `on`;
- `unregistered-role-object`: a role class made outside the entry point,
  a test or a `bind(...)` -- a page's fallback -- registered with nothing;
- `base-digest`: the Dockerfile's base pinned by tag alone, in a plugin
  pinning images by digest (its Makefile's core images): a pin moved
  without its digest (the plugin step's tiingo).

migration.toml, beside this, records the rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import dotted, is_test, line_of

IMAGE = "ghcr.io/open-meridian/plugin-python"
_TAG_ONLY = re.compile(rf"{re.escape(IMAGE)}:[0-9][0-9.]*(?!@sha256:)(?=\s|$)")
#: 0.34's names of the SDK's handlers, and 0.35's.
OLD_HANDLERS = {
    "on_want": "on_observations_wanted",
    "on_withdrawn": "on_want_withdrawn",
    "on_placement": "on_placement_updated",
    "on_instruction": "on_trading_instruction_changed",
    "on_execution": "on_execution_recorded",
    "seed": "seed_symbols",
}
_MAIN = re.compile(r"^src/[A-Za-z_][A-Za-z0-9_]*/__main__\.py$")


def _rows() -> frozenset[str]:
    """The keywords `receive` took, one per row (0.35.0's surfaces)."""
    from ..to_0_35_0.rewrite import ROW_OF

    return frozenset(ROW_OF)


@dataclass
class _Plugin:
    #: Each class the plugin defines, by name: its bases as written, each
    #: resolved through its file's imports.
    bases: dict[str, list[str]] = field(default_factory=dict)
    #: Every method name the plugin's classes define.
    methods: set[str] = field(default_factory=set)
    #: The plugin's role classes: a base in `meridian.roles`, or another of
    #: its role classes.
    roles: set[str] = field(default_factory=set)
    #: Whether it pins an image by digest anywhere (its Makefile's core
    #: images): one that does pins its base so too.
    digests: bool = False


_plugin = _Plugin()


def _names(module: cst.Module) -> dict[str, str]:
    """What each name a file imports is, in full."""
    from ..to_0_35_0.rewrite import _Names

    names = _Names()
    module.visit(names)
    return names.full


def _resolved(node: cst.BaseExpression, names: dict[str, str]) -> str:
    text = dotted(node) or ""
    head, _, rest = text.partition(".")
    if head in names:
        return names[head] + (f".{rest}" if rest else "")
    return text


class _Classes(cst.CSTVisitor):
    def __init__(self, names: dict[str, str]) -> None:
        super().__init__()
        self.names = names

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        _plugin.bases[node.name.value] = [_resolved(a.value, self.names) for a in node.bases]
        for statement in node.body.body:
            if isinstance(statement, cst.FunctionDef):
                _plugin.methods.add(statement.name.value)


def given(files: dict[str, str]) -> None:
    global _plugin
    _plugin = _Plugin()
    _plugin.digests = any(
        "@sha256:" in text for path, text in files.items() if path != "Dockerfile"
    ) or "@sha256:" in files.get("Dockerfile", "")
    for path, text in sorted(files.items()):
        if not path.endswith(".py") or "class " not in text:
            continue
        try:
            module = cst.parse_module(text)
        except cst.ParserSyntaxError:
            continue
        module.visit(_Classes(_names(module)))
    changed = True
    while changed:
        changed = False
        for name, bases in _plugin.bases.items():
            if name in _plugin.roles:
                continue
            if any(
                base.startswith("meridian.roles.") or base.rsplit(".", 1)[-1] in _plugin.roles
                for base in bases
            ):
                _plugin.roles.add(name)
                changed = True


def rewrite(path: str, text: str) -> Rewritten:
    return Rewritten(text)


def _calls(node: cst.CSTNode, method: str) -> bool:
    """Whether `node` calls `.method(...)` on anything."""
    found = False

    class _Find(cst.CSTVisitor):
        def visit_Call(self, call: cst.Call) -> None:
            nonlocal found
            if isinstance(call.func, cst.Attribute) and call.func.attr.value == method:
                found = True

    node.visit(_Find())
    return found


def _is_property(method: cst.FunctionDef) -> bool:
    return any(
        (dotted(d.decorator) or "").split(".")[-1] in ("property", "setter", "getter")
        for d in method.decorators
    )


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path
        self.found: list[tuple[str, int, str]] = []
        self.classes: list[str] = []
        self.bound: set[int] = set()  # id() of each call given to `bind(...)`
        self.rows = _rows()
        self.place = not (is_test(path) or _MAIN.match(path) or "e2e/" in path)

    def _line(self, node: cst.CSTNode) -> int:
        return self.get_metadata(PositionProvider, node).start.line

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.classes.append(node.name.value)
        role = node.name.value in _plugin.roles
        for statement in node.body.body:
            if isinstance(statement, cst.FunctionDef):
                name = statement.name.value
                if name == "named" and _calls(statement, "dataset"):
                    self.found.append(("named-calls-dataset", self._line(statement), ""))
                if (
                    name == "timeliness"
                    and not _is_property(statement)
                    and len(statement.params.params) > 1
                ):
                    self.found.append(("timeliness-overridden", self._line(statement), ""))
            elif role and isinstance(statement, cst.SimpleStatementLine):
                for small in statement.body:
                    target = getattr(small, "target", None)
                    if isinstance(target, cst.Name) and target.value == "subjects":
                        self.found.append(("subjects-shadowed", self._line(statement), ""))

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        self.classes.pop()

    def visit_Assign(self, node: cst.Assign) -> None:
        if self.classes and self.classes[-1] in _plugin.roles:
            for target in node.targets:
                if dotted(target.target) == "self.subjects":
                    self.found.append(("subjects-shadowed", self._line(node), ""))

    def visit_Call(self, node: cst.Call) -> None:
        func = node.func
        if isinstance(func, cst.Attribute) and func.attr.value == "bind":
            for arg in node.args:
                self.bound.add(id(arg.value))
        if isinstance(func, cst.Attribute):
            name = func.attr.value
            if (
                name in OLD_HANDLERS
                and name not in _plugin.methods
                and not (name == "seed" and not node.args)
            ):
                self.found.append(
                    ("old-handler-name", self._line(node), f"{name}: {OLD_HANDLERS[name]}")
                )
            if name == "receive" and any(
                arg.keyword is not None and arg.keyword.value in self.rows for arg in node.args
            ):
                self.found.append(("receive-gone", self._line(node), ""))
            if (
                name == "on"
                and is_test(self.path)
                and isinstance(func.value, cst.Attribute)
                and func.value.attr.value == "plugin"
            ):
                self.found.append(("stand-in-read", self._line(node), ""))
        made = dotted(func) or ""
        if (
            self.place
            and made.rsplit(".", 1)[-1] in _plugin.roles
            and id(node) not in self.bound
            and not (self.classes and made.rsplit(".", 1)[-1] in self.classes)
        ):
            self.found.append(("unregistered-role-object", self._line(node), made))


def left(path: str, text: str) -> list[Finding]:
    if path == "Dockerfile":
        if not _plugin.digests:
            return []  # the template's way: a base by tag, nothing by digest
        return [
            Finding("base-digest", path, n, line.strip())
            for n, line in enumerate(text.splitlines(), 1)
            if _TAG_ONLY.search(line) and not line.lstrip().startswith("#")
        ]
    if not path.endswith(".py"):
        return []
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError:
        return []
    visitor = _Left(path)
    MetadataWrapper(module).visit(visitor)
    found = []
    for rule, line, said in visitor.found:
        shown = line_of(text, line)
        found.append(Finding(rule, path, line, f"{shown}  [{said}]" if said else shown))
    return found
