"""open-meridian 0.32.3 to 0.33.0: contract v28.

Ruling 599 (2026-10-24): SubjectRef gained its role, so the typed
operations take the SDK's dataclass, `meridian.SubjectRef`, and refuse the
wire's. In a file that uses the SDK, every `SubjectRef(...)` built from the
wire bindings -- `ops.SubjectRef(...)` with `ops` naming
`meridian.plugin.v1.operations_pb2`, `operations_pb2.SubjectRef(...)`, or a
`SubjectRef` imported from it -- becomes `meridian.SubjectRef(...)`, with
`import meridian` added where the file has none, unless it is built inside
another wire message (`ops.ObservationMeta(subjects=[ops.SubjectRef(...)])`,
a test's fake event) or added to a wire message's field (`.extend`,
`.append`), where the wire's stays. A `SubjectRef` imported from the wire
bindings and no longer named is dropped from its import.

Left by hand: a typed operation given subjects read from a heard message
(`subjects=want.subjects`), which are the wire's; each role's suite test,
since contract v28 adds cases a plugin maps; the three latency cases a
plugin named not presented under v27, required from v28 (ruling 518); and
a Dockerfile's base pinned by digest, as 0.32.0's. migration.toml, beside
this, records the rules.
"""

from __future__ import annotations

import dataclasses
import inspect
import re

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor
from libcst.metadata import MetadataWrapper, PositionProvider

from ... import operations
from .. import Finding, Rewritten
from .._cst import dotted, imports_of, is_test, line_of

TARGET = "0.33.0"
IMAGE = "ghcr.io/open-meridian/plugin-python"
WIRE = "meridian.plugin.v1.operations_pb2"
NAME = "SubjectRef"
#: A wire message's repeated field takes elements by these.
_ADDS = frozenset({"extend", "append", "add", "insert", "CopyFrom", "MergeFrom"})
_BASE = re.compile(
    rf"(?P<head>{re.escape(IMAGE)}:)(?P<tag>[0-9][0-9.]*)(?P<digest>@sha256:[0-9a-f]{{64}})"
)
#: Every role whose suite contract v28 adds cases a plugin maps itself to.
_ROLES = (
    "reporting", "portfolio", "compliance", "signal", "data", "ems", "oms", "operations",
    "connectivity", "custody", "servicing",
)  # fmt: skip
_RUN = re.compile(rf"""\brun(?:_async)?\(\s*["'](?P<role>{"|".join(_ROLES)})["']""")
#: The three cases about `latency` a v27 plugin named not presented (518).
_LATENCY = re.compile(
    r"""["'](?:reports-its-feed-delay|reports-a-sessions-round-trip|"""
    r"""reports-its-pre-trade-checks-data-age)["']\s*:\s*["'][^"']*(?:v28|515|ReportLatency)"""
)


class _Wire(cst.CSTVisitor):
    """How a file names the wire bindings: the modules (`ops`,
    `operations_pb2`, the dotted path) and the names imported from them."""

    def __init__(self) -> None:
        super().__init__()
        self.modules: set[str] = set()
        self.names: dict[str, str] = {}

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            if dotted(alias.name) != WIRE:
                continue
            if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
                self.modules.add(alias.asname.name.value)
            else:
                self.modules.add(WIRE)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.relative or node.module is None or isinstance(node.names, cst.ImportStar):
            return
        module = dotted(node.module)
        for alias in node.names:
            name = dotted(alias.name)
            local = name
            if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
                local = alias.asname.name.value
            if local is None or name is None:
                continue
            if module == "meridian.plugin.v1" and name == "operations_pb2":
                self.modules.add(local)
            elif module == WIRE:
                self.names[local] = name


def _of_wire(node: cst.BaseExpression, wire: _Wire) -> str | None:
    """The wire's name `node` names (`ops.Trade` is "Trade"), or None."""
    if isinstance(node, cst.Name):
        return wire.names.get(node.value)
    if isinstance(node, cst.Attribute):
        base = dotted(node.value)
        if base is not None and base in wire.modules:
            return node.attr.value
    return None


def _builds_wire(call: cst.Call, wire: _Wire) -> bool:
    """Whether `call` builds a wire message, or adds to one's field."""
    if _of_wire(call.func, wire) is not None:
        return True
    return isinstance(call.func, cst.Attribute) and call.func.attr.value in _ADDS


class _Subjects(cst.CSTTransformer):
    def __init__(self, wire: _Wire, package: str) -> None:
        super().__init__()
        self.wire = wire
        self.package = package
        self.calls: list[cst.Call] = []
        self.applied: list[str] = []

    def visit_Call(self, node: cst.Call) -> None:
        self.calls.append(node)

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        self.calls.pop()
        if _of_wire(original_node.func, self.wire) != NAME:
            return updated_node
        if self.calls and _builds_wire(self.calls[-1], self.wire):
            return updated_node  # an element of a wire message: the wire's stays
        self.applied.append("subject-ref-from-the-sdk")
        return updated_node.with_changes(
            func=cst.Attribute(value=cst.Name(self.package), attr=cst.Name(NAME))
        )


class _Named(cst.CSTVisitor):
    """Each local name still named outside an import."""

    def __init__(self) -> None:
        super().__init__()
        self.named: set[str] = set()

    def visit_Import(self, node: cst.Import) -> bool:
        return False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        return False

    def visit_Attribute(self, node: cst.Attribute) -> bool:
        node.value.visit(self)  # `meridian.SubjectRef` names `meridian` alone
        return False

    def visit_Name(self, node: cst.Name) -> None:
        self.named.add(node.value)


class _Unimport(cst.CSTTransformer):
    """`gone` dropped from `from meridian.plugin.v1.operations_pb2 import ...`,
    and the statement with it when nothing is left."""

    def __init__(self, gone: set[str]) -> None:
        super().__init__()
        self.gone = gone

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        names = updated_node.names
        if (
            updated_node.module is None
            or dotted(updated_node.module) != WIRE
            or isinstance(names, cst.ImportStar)
        ):
            return updated_node
        kept = [
            alias
            for alias in names
            if (
                alias.asname.name.value
                if alias.asname is not None and isinstance(alias.asname.name, cst.Name)
                else dotted(alias.name)
            )
            not in self.gone
        ]
        if not kept:
            return cst.RemoveFromParent()
        if len(kept) == len(names):
            return updated_node
        kept[-1] = kept[-1].with_changes(comma=names[-1].comma)
        return updated_node.with_changes(names=kept)


def rewrite(path: str, text: str) -> Rewritten:
    if path == "Dockerfile":
        return _dockerfile(path, text)
    if not path.endswith(".py") or NAME not in text:
        return Rewritten(text)
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not (imports.modules or imports.names):
        return Rewritten(text)
    wire = _Wire()
    module.visit(wire)
    if not wire.modules and NAME not in wire.names.values():
        return Rewritten(text)
    package = imports.package or "meridian"
    subjects = _Subjects(wire, package)
    rewritten = module.visit(subjects)
    if not subjects.applied:
        return Rewritten(text)
    if imports.package is None:
        context = CodemodContext()
        AddImportsVisitor.add_needed_import(context, "meridian")
        rewritten = AddImportsVisitor(context).transform_module(rewritten)
    named = _Named()
    rewritten.visit(named)
    gone = {local for local, name in wire.names.items() if name == NAME} - named.named
    if gone:
        rewritten = rewritten.visit(_Unimport(gone))
    return Rewritten(rewritten.code, tuple(subjects.applied))


def _dockerfile(path: str, text: str) -> Rewritten:
    rules: list[str] = []
    findings: list[Finding] = []
    out: list[str] = []
    for n, line in enumerate(text.splitlines(keepends=True), 1):
        found = _BASE.search(line)
        if found and found.group("tag") != TARGET:
            line = line[: found.start()] + found.group("head") + TARGET + line[found.end() :]
            rules.append("base-digest-dropped")
            findings.append(Finding("base-digest", path, n, line.strip()))
        out.append(line)
    return Rewritten("".join(out), tuple(rules), tuple(findings))


def _at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


#: What takes the SDK's SubjectRef as `subjects`: each typed operation with
#: that parameter, and each of the SDK's dataclasses with that field.
_TAKES_SUBJECTS = frozenset(
    {
        name
        for name, method in vars(operations.Operations).items()
        if inspect.isfunction(method) and "subjects" in inspect.signature(method).parameters
    }
    | {
        name
        for name, value in vars(operations).items()
        if inspect.isclass(value)
        and dataclasses.is_dataclass(value)
        and "subjects" in {f.name for f in dataclasses.fields(value)}
    }
)


class _FromHeard(cst.CSTVisitor):
    """`subjects=<x>.subjects` (or `list(<x>.subjects)`) given to a call that
    builds no wire message: the wire's SubjectRef handed to a typed
    operation, which refuses it from 0.33.0."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, wire: _Wire) -> None:
        super().__init__()
        self.wire = wire
        self.lines: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        func = node.func
        called = func.attr.value if isinstance(func, cst.Attribute) else dotted(func)
        if called not in _TAKES_SUBJECTS or _builds_wire(node, self.wire):
            return
        for arg in node.args:
            if arg.keyword is None or arg.keyword.value != "subjects":
                continue
            value = arg.value
            if (
                isinstance(value, cst.Call)
                and dotted(value.func) == "list"
                and len(value.args) == 1
            ):
                value = value.args[0].value
            if isinstance(value, cst.Attribute) and value.attr.value == "subjects":
                self.lines.append(self.get_metadata(PositionProvider, arg).start.line)


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    found: list[Finding] = []
    if is_test(path):
        for match in _RUN.finditer(text):
            line = _at(text, match.start())
            found.append(Finding("suite-cases-v28", path, line, line_of(text, line)))
        for match in _LATENCY.finditer(text):
            line = _at(text, match.start())
            found.append(Finding("latency-cases-required", path, line, line_of(text, line)))
    if "subjects" not in text:
        return found
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError:
        return found
    imports = imports_of(module)
    if not (imports.modules or imports.names):
        return found
    wire = _Wire()
    module.visit(wire)
    heard = _FromHeard(wire)
    MetadataWrapper(module).visit(heard)
    for line in heard.lines:
        found.append(Finding("subjects-from-the-wire", path, line, line_of(text, line)))
    return found
