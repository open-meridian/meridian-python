"""open-meridian 0.33.5 to 0.34.0: contract v29.

Ruling 1001 (2026-11-01): `meridian.roles` holds only roles, so the four
topic modules there leave it for `meridian.helpers`, with no shim at the old
paths: `meridian.roles.chains`, `.packages`, `.lifecycle` and `.debt` are
`meridian.helpers.chains`, `.packages`, `.lifecycle` and `.debt`. Every
import of them is rewritten -- `import meridian.roles.chains [as c]`,
`from meridian.roles import chains [as c]`, `from meridian.roles.chains
import X`, and an import naming them beside a role's module or name
(`from meridian.roles import Latency, chains, ems`), which is split in
place, the helpers' line first -- and so is each name reaching one through
the package or `meridian.roles` (`meridian.roles.debt.factor(...)`,
`roles.chains.osi_symbol(...)` after `from meridian import roles`), and a
string that is wholly such a dotted path (a patch target). Anything else
naming an old path -- a comment, a dynamic import, a name read through
`from meridian.roles import *` -- is left by hand.

Nothing a plugin calls changed shape otherwise: the typed operations and
the SDK's dataclasses gained fields and helpers (`meridian.helpers.debt`,
the fixed-income records in `meridian.helpers.lifecycle`,
`meridian.analytics.debt`). A Dockerfile's base pinned by digest at an
older release is moved to 0.34.0 with its digest dropped, since this runs
with no network, as 0.33.0's; `meridian plugin migrate` has moved the tag
and the digest before this runs, and then there is nothing to do.

Left by hand: each suite test of a role contract v29 adds the factor's cases
to (`records-a-pools-factor` for `data`; `reads-a-pools-factors` and
`hears-a-factor-recorded` for `operations`, `portfolio`, `reporting`,
`servicing` and `signal`), which a plugin maps or names not presented, with
why; a quality assessment built by hand naming no data type, which
`RecordQualityAssessments` requires from contract v29 (628); an old path
named where no rewrite reaches it; and the digest, pinned again.
migration.toml, beside this, records the rules.
"""

from __future__ import annotations

import re
from typing import cast

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten, core_pins, version
from .._cst import dotted, imports_of, is_test, line_of

TARGET = "0.34.0"
IMAGE = "ghcr.io/open-meridian/plugin-python"
_BASE = re.compile(
    rf"(?P<head>{re.escape(IMAGE)}:)(?P<tag>[0-9][0-9.]*)(?P<digest>@sha256:[0-9a-f]{{64}})"
)
#: Every role whose suite contract v29 adds cases to: the factor's.
_ROLES = ("data", "operations", "portfolio", "reporting", "servicing", "signal")
_RUN = re.compile(rf"""\brun(?:_async)?\(\s*["'](?P<role>{"|".join(_ROLES)})["']""")
#: The SDK's data-suite not-presented sets, each naming the data case v29
#: adds (`records-a-pools-factor`), as a plugin names them.
_NAMES_THE_FACTOR = re.compile(r"\b(?:PAIRS|EVENT_CONTRACTS|RATES)_NOT_PRESENTED\b")
#: Whether the plugin names one of them anywhere (`given`, SDK 0.35.1): its
#: data suite then names the case already.
_factor_named = False


def given(files: dict[str, str]) -> None:
    """The plugin read whole, before any file: whether it names one of the
    SDK's not-presented sets naming the data suite's factor case."""
    global _factor_named
    _factor_named = any(
        path.endswith(".py") and _NAMES_THE_FACTOR.search(text) is not None
        for path, text in files.items()
    )


#: The topic modules that left `meridian.roles` for `meridian.helpers` (1001).
TOPICS = frozenset({"chains", "packages", "lifecycle", "debt"})
ROLES = "meridian.roles"
MOVED = "topic-module-to-helpers"
_TOPIC = "|".join(sorted(TOPICS))
#: A string that is wholly a dotted path into a moved module.
_PATH = re.compile(rf"meridian\.roles\.(?:{_TOPIC})(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
#: An old path, wherever it is still named.
_NAMED = re.compile(rf"\bmeridian\.roles\.(?:{_TOPIC})\b")
_STAR = re.compile(r"^[ \t]*from[ \t]+meridian\.roles[ \t]+import[ \t]*\*", re.MULTILINE)
_READ = re.compile(rf"(?<![\w.])(?:{_TOPIC})\.[A-Za-z_]")


def _alias_name(alias: cst.ImportAlias) -> str:
    return dotted(alias.name) or ""


def _bare(aliases: list[cst.ImportAlias]) -> list[cst.ImportAlias]:
    """The aliases with the commas between them libcst writes itself, for a
    statement of their own on one line."""
    return [alias.with_changes(comma=cst.MaybeSentinel.DEFAULT) for alias in aliases]


def _helpers_module() -> cst.Attribute:
    return cst.Attribute(value=cst.Name("meridian"), attr=cst.Name("helpers"))


class _RolesNames(cst.CSTVisitor):
    """The local names a file binds to `meridian.roles` itself: `roles` from
    `from meridian import roles`, `r` from `import meridian.roles as r`."""

    def __init__(self) -> None:
        super().__init__()
        self.names: set[str] = set()

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            if (
                dotted(alias.name) == ROLES
                and alias.asname is not None
                and isinstance(alias.asname.name, cst.Name)
            ):
                self.names.add(alias.asname.name.value)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.relative or node.module is None or isinstance(node.names, cst.ImportStar):
            return
        if dotted(node.module) != "meridian":
            return
        for alias in node.names:
            if _alias_name(alias) != "roles":
                continue
            local = "roles"
            if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
                local = alias.asname.name.value
            self.names.add(local)


class _Topics(cst.CSTTransformer):
    """Each import and name of a moved module, onto `meridian.helpers`."""

    def __init__(self, packages: set[str], package: str | None, roles: set[str]) -> None:
        super().__init__()
        # Local names bound to the package itself (`meridian`, or `om`).
        self.packages = packages
        self.package = package
        self.roles = roles
        self.importing = 0
        self.applied: list[str] = []
        self.needs_package = False

    # An import's own dotted names are the SDK's whatever the file binds.
    def visit_Import(self, node: cst.Import) -> None:
        self.importing += 1

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:
        self.importing -= 1
        return updated_node

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        self.importing += 1

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        self.importing -= 1
        return updated_node

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.BaseExpression:
        topic = original_node.attr.value
        if topic not in TOPICS:
            return updated_node
        base = dotted(original_node.value)
        if base is None:
            return updated_node
        head, _, last = base.rpartition(".")
        if last == "roles" and (
            (self.importing and head == "meridian")
            or (not self.importing and head in self.packages)
        ):
            # `meridian.roles.chains` (or `om.roles.chains`): roles -> helpers.
            inner = cast(cst.Attribute, updated_node.value)
            self.applied.append(MOVED)
            return updated_node.with_changes(value=inner.with_changes(attr=cst.Name("helpers")))
        if not self.importing and not head and base in self.roles:
            # `roles.chains`, `roles` bound to meridian.roles.
            package = self.package or "meridian"
            self.needs_package = self.package is None
            self.applied.append(MOVED)
            return cst.Attribute(
                value=cst.Attribute(value=cst.Name(package), attr=cst.Name("helpers")),
                attr=updated_node.attr,
            )
        return updated_node

    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.SimpleString:
        value = original_node.evaluated_value
        if not isinstance(value, str) or not _PATH.fullmatch(value):
            return updated_node
        self.applied.append(MOVED)
        return updated_node.with_changes(
            value=updated_node.value.replace("meridian.roles.", "meridian.helpers.", 1)
        )

    def _split(self, node: cst.BaseSmallStatement) -> list[cst.BaseSmallStatement] | None:
        """`from meridian.roles import ...` naming a moved module: onto
        meridian.helpers whole, or split in two, the helpers' first. None
        for any other statement."""
        if (
            not isinstance(node, cst.ImportFrom)
            or node.relative
            or node.module is None
            or dotted(node.module) != ROLES
            or isinstance(node.names, cst.ImportStar)
        ):
            return None
        aliases = list(node.names)
        moved = [alias for alias in aliases if _alias_name(alias) in TOPICS]
        if not moved:
            return None
        self.applied.extend(MOVED for _ in moved)
        if len(moved) == len(aliases):
            return [node.with_changes(module=_helpers_module())]
        kept = [alias for alias in aliases if _alias_name(alias) not in TOPICS]
        kept[-1] = kept[-1].with_changes(comma=aliases[-1].comma)
        helpers = cst.ImportFrom(module=_helpers_module(), names=_bare(moved))
        return [helpers, node.with_changes(names=kept)]

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel[cst.SimpleStatementLine]:
        body: list[cst.BaseSmallStatement] = []
        split = False
        for statement in updated_node.body:
            parts = self._split(statement)
            if parts is None:
                body.append(statement)
                continue
            split = split or len(parts) == 2
            body.extend(parts)
        if not split:
            return updated_node.with_changes(body=body)
        if len(updated_node.body) == 1:
            # One import on its line: two lines, the helpers' first, keeping
            # the line's comments before it and its trailing comment after.
            first = cst.SimpleStatementLine(
                body=[body[0]], leading_lines=updated_node.leading_lines
            )
            second = updated_node.with_changes(body=[body[1]], leading_lines=[])
            return cst.FlattenSentinel([first, second])
        # Several statements on the line: the helpers' joins them there, and
        # libcst writes the semicolon between.
        return updated_node.with_changes(body=body)


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
        node.value.visit(self)  # `roles.data` names `roles` alone
        return False

    def visit_Name(self, node: cst.Name) -> None:
        self.named.add(node.value)


class _Unbind(cst.CSTTransformer):
    """The names in `gone`, bound to meridian.roles and no longer named,
    dropped from their import, and the statement with them when nothing is
    left -- or, where the file now needs the package bound, the first such
    statement becomes `import meridian`, where the binding it replaces was."""

    def __init__(self, gone: set[str], bind_package: bool) -> None:
        super().__init__()
        self.gone = gone
        self.bind_package = bind_package
        self.bound = False

    def _emptied(self) -> cst.Import | cst.RemovalSentinel:
        if self.bind_package and not self.bound:
            self.bound = True
            return cst.Import(names=[cst.ImportAlias(name=cst.Name("meridian"))])
        return cst.RemoveFromParent()

    def _local(self, alias: cst.ImportAlias) -> str:
        if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
            return alias.asname.name.value
        return _alias_name(alias)

    def _kept(self, aliases: list[cst.ImportAlias], bound: str) -> list[cst.ImportAlias]:
        kept = [
            alias
            for alias in aliases
            if not (_alias_name(alias) == bound and self._local(alias) in self.gone)
        ]
        if kept and len(kept) != len(aliases):
            kept[-1] = kept[-1].with_changes(comma=aliases[-1].comma)
        return kept

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.Import | cst.RemovalSentinel:
        aliases = list(updated_node.names)
        kept = self._kept(aliases, ROLES)
        if not kept:
            return self._emptied()
        if len(kept) == len(aliases):
            return updated_node
        return updated_node.with_changes(names=kept)

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.Import | cst.RemovalSentinel:
        if (
            updated_node.relative
            or updated_node.module is None
            or dotted(updated_node.module) != "meridian"
            or isinstance(updated_node.names, cst.ImportStar)
        ):
            return updated_node
        aliases = list(updated_node.names)
        kept = self._kept(aliases, "roles")
        if not kept:
            return self._emptied()
        if len(kept) == len(aliases):
            return updated_node
        return updated_node.with_changes(names=kept)


def _topics(text: str) -> Rewritten:
    """`meridian.roles.{chains,packages,lifecycle,debt}` onto meridian.helpers."""
    module = cst.parse_module(text)
    imports = imports_of(module)
    roles = _RolesNames()
    module.visit(roles)
    packages = {name for name in (imports.package,) if name is not None}
    if "meridian" in imports.modules:
        packages.add("meridian")
    topics = _Topics(packages, imports.package, roles.names)
    rewritten = module.visit(topics)
    if not topics.applied:
        return Rewritten(text)
    if roles.names:
        named = _Named()
        rewritten.visit(named)
        gone = roles.names - named.named
        if gone:
            unbind = _Unbind(gone, topics.needs_package)
            rewritten = rewritten.visit(unbind)
            topics.needs_package = topics.needs_package and not unbind.bound
    if topics.needs_package:
        context = CodemodContext()
        AddImportsVisitor.add_needed_import(context, "meridian")
        rewritten = AddImportsVisitor(context).transform_module(rewritten)
    return Rewritten(rewritten.code, tuple(topics.applied))


def _dockerfile(path: str, text: str) -> Rewritten:
    rules: list[str] = []
    findings: list[Finding] = []
    out: list[str] = []
    for n, line in enumerate(text.splitlines(keepends=True), 1):
        found = _BASE.search(line)
        if found and version(found.group("tag")) < version(TARGET):  # never a later pin
            line = line[: found.start()] + found.group("head") + TARGET + line[found.end() :]
            rules.append("base-digest-dropped")
            findings.append(Finding("base-digest", path, n, line.strip()))
        out.append(line)
    return Rewritten("".join(out), tuple(rules), tuple(findings))


def rewrite(path: str, text: str) -> Rewritten:
    if path == "Dockerfile":
        return _dockerfile(path, text)
    if path.endswith(".py") and "roles" in text and "meridian" in text:
        return _topics(text)
    return Rewritten(text)


def _at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


class _Assessments(cst.CSTVisitor):
    """A `QualityAssessment(...)` built naming no `data_type`."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        name = dotted(node.func) or ""
        if name.rsplit(".", 1)[-1] != "QualityAssessment":
            return
        named = {arg.keyword.value for arg in node.args if arg.keyword is not None}
        if "data_type" not in named and not any(arg.star for arg in node.args):
            self.lines.append(self.get_metadata(PositionProvider, node).start.line)


def left(path: str, text: str) -> list[Finding]:
    if path == "Makefile":
        # Core's images an e2e runs on, pinned below contract v29 (SDK 0.35.1).
        return [
            Finding("core-images", path, line, line_of(text, line))
            for line in core_pins(path, text, 29)
        ]
    if not path.endswith(".py"):
        return []
    found: list[Finding] = []
    if is_test(path):
        for match in _RUN.finditer(text):
            if match.group("role") == "data" and _factor_named:
                continue  # the SDK's set it names names the case (SDK 0.35.1)
            line = _at(text, match.start())
            found.append(Finding("suite-cases-v29", path, line, line_of(text, line)))
    lines = {_at(text, match.start()) for match in _NAMED.finditer(text)}
    if _READ.search(text):
        lines |= {_at(text, match.start()) for match in _STAR.finditer(text)}
    for line in sorted(lines):
        found.append(Finding("topic-module-named", path, line, line_of(text, line)))
    if "QualityAssessment" not in text:
        return found
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError:
        return found
    assessments = _Assessments()
    MetadataWrapper(module).visit(assessments)
    for line in assessments.lines:
        found.append(Finding("quality-assessment-data-type", path, line, line_of(text, line)))
    return found
