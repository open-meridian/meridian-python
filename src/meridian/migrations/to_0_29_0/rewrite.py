"""open-meridian 0.28.0 to 0.29.0: the SDK declares contract v25.

Ruling 118 (2026-10-16) dropped connectivity's grant of
ReadLocalRecordOrders, with the suite's case
`reads-whether-orders-may-name-local-records`: a connectivity plugin
proposes and accepts nothing on a record. In a plugin whose pyproject.toml
declares `connectivity` and no role that keeps the read (compliance, ems,
oms, portfolio), two rewrites, each only in a file that uses the SDK:

- `await <plugin>.read_local_record_orders()`, a statement of its own, is
  removed (a block it leaves empty holds `pass`);
- in a test, a mapping of the dropped case -- the key
  `"reads-whether-orders-may-name-local-records"` in a dict -- is removed.

Any other read of it in such a plugin -- its answer kept, or the call inside
another expression -- is left by hand.

For every plugin, three things the migration cannot move are left by hand:
`connect` given an interface, settings or `reads_external_accounts`, which
from v25 belong in the version's declaration, since registration is held to
the declaration uploaded; a pyproject.toml whose `[tool.meridian]` names
no declaration; and a Dockerfile that copies no documentation directory into
the image -- the one the declaration names (`documentation="..."`), `docs`
when none names one yet -- since the declaration reads its sections where it
runs, in the built image, and `meridian-declaration` and the upload fail
without them (the plugin agent's finding, 2026-10-16: an image installing
only the package from a mount holds no docs/). migration.toml, beside this,
records the rules.
"""

from __future__ import annotations

import json
import re
import tomllib

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import Imports, imports_of, is_sdk, is_test, line_of, literal

READ = "read_local_record_orders"
CASE = "reads-whether-orders-may-name-local-records"
#: The roles that keep the read (matrix/roles.tsv at contract v25).
KEEP = frozenset({"compliance", "ems", "oms", "portfolio"})
#: What connect may name that, from v25, the declaration carries.
DECLARED = ("interface", "settings", "reads_external_accounts")

#: The documentation directory a declaration names when it names none yet:
#: the templates', and the by-hand rules' instead.
DOCS = "docs"

#: Whether the plugin being migrated holds connectivity and no role keeping
#: the read, from its pyproject.toml (`given`).
_dropped = False
#: The documentation directories the plugin's declarations name (`given`),
#: DOCS when none names one.
_documented: tuple[str, ...] = (DOCS,)


def given(files: dict[str, str]) -> None:
    """The plugin's roles, read once from its pyproject.toml before any file
    is rewritten."""
    global _dropped, _documented
    roles: list[str] = []
    text = files.get("pyproject.toml")
    if text is not None:
        try:
            meridian = tomllib.loads(text).get("tool", {}).get("meridian", {})
        except tomllib.TOMLDecodeError:
            meridian = {}
        named = meridian.get("roles", [])
        roles = (
            [role for role in named if isinstance(role, str)] if isinstance(named, list) else []
        )
    _dropped = "connectivity" in roles and not KEEP.intersection(roles)
    directories: set[str] = set()
    for path, held in files.items():
        if path.endswith(".py") and "documentation" in held:
            directories.update(_documentation_named(held))
    _documented = tuple(sorted(directories)) or (DOCS,)


def _documentation_named(text: str) -> set[str]:
    """Each directory a `Declaration(documentation="...")` in `text` names,
    as a literal."""
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError:
        return set()
    imports = imports_of(module)
    found = _Documented(imports)
    module.visit(found)
    return found.named


class _Documented(cst.CSTVisitor):
    def __init__(self, imports: Imports) -> None:
        super().__init__()
        self.imports = imports
        self.named: set[str] = set()

    def visit_Call(self, node: cst.Call) -> None:
        if not is_sdk(node.func, "Declaration", self.imports):
            return
        for arg in node.args:
            if arg.keyword is not None and arg.keyword.value == "documentation":
                value = literal(arg.value)
                if value and "\0" not in value:
                    self.named.add(_bare(value))


def _bare(path: str) -> str:
    """A directory as the build context holds it: `./docs/` is `docs`."""
    while path.startswith("./"):
        path = path[2:]
    return path.rstrip("/") or "."


def _uses_sdk(module: cst.Module) -> bool:
    imports = imports_of(module)
    return bool(imports.modules or imports.names)


def _is_read(node: cst.BaseExpression) -> bool:
    """`<x>.read_local_record_orders()`, awaited or not, with no argument."""
    if isinstance(node, cst.Await):
        node = node.expression
    return (
        isinstance(node, cst.Call)
        and isinstance(node.func, cst.Attribute)
        and node.func.attr.value == READ
        and not node.args
    )


def rewrite(path: str, text: str) -> Rewritten:
    if not _dropped or not path.endswith(".py"):
        return Rewritten(text)
    module = cst.parse_module(text)
    if not _uses_sdk(module):
        return Rewritten(text)
    rewriting = _Dropped(is_test(path))
    rewritten = module.visit(rewriting)
    return Rewritten(rewritten.code, tuple(rewriting.applied))


def left(path: str, text: str) -> list[Finding]:
    if path == "pyproject.toml":
        return _undeclared(text)
    if path == "Dockerfile":
        return _docs_not_copied(text)
    if not path.endswith(".py"):
        return []
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not (imports.modules or imports.names):
        return []
    found = _Left(imports, _dropped)
    MetadataWrapper(module).visit(found)
    return [
        Finding(rule, path, line, line_of(text, line))
        for rule, line in sorted(set(found.found))
    ]


def _undeclared(text: str) -> list[Finding]:
    """pyproject.toml's `[tool.meridian]`, where it names no declaration."""
    try:
        meridian = tomllib.loads(text).get("tool", {}).get("meridian")
    except tomllib.TOMLDecodeError:
        return []
    if not isinstance(meridian, dict) or "declaration" in meridian:
        return []
    line = next(
        (n for n, held in enumerate(text.splitlines(), 1) if held.strip() == "[tool.meridian]"),
        0,
    )
    return [
        Finding(
            "declaration-not-named", "pyproject.toml", line, line_of(text, line) if line else ""
        )
    ]


def _instructions(text: str) -> list[tuple[int, str, str]]:
    """The Dockerfile's instructions: the line each starts on, its keyword in
    upper case and the rest, continuation lines joined and comments dropped."""
    out: list[tuple[int, str, str]] = []
    held: list[str] = []
    start = 0
    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not held and (not stripped or stripped.startswith("#")):
            continue
        if held and stripped.startswith("#"):
            continue
        if not held:
            start = n
        if stripped.endswith("\\"):
            held.append(stripped[:-1])
            continue
        held.append(stripped)
        keyword, _, rest = " ".join(held).partition(" ")
        out.append((start, keyword.upper(), rest.strip()))
        held = []
    return out


#: A COPY's or an ADD's flags (`--chown=...`, `--from=...`, `--link`).
FLAG = re.compile(r"^--[a-z-]+(?:=\S*)?$")


def _sources(rest: str) -> tuple[list[str], bool] | None:
    """A COPY's or an ADD's sources, as the build context names them, and
    whether it copies from another stage or image (`--from`); None when it is
    not one that can be read."""
    words = rest.split()
    flags = [word for word in words if FLAG.match(word)]
    rest = " ".join(word for word in words if not FLAG.match(word))
    if rest.startswith("["):
        try:
            named = json.loads(rest)
        except json.JSONDecodeError:
            return None
        if not isinstance(named, list) or not all(isinstance(word, str) for word in named):
            return None
    else:
        named = rest.split()
    if len(named) < 2:
        return None
    return [_bare(source) for source in named[:-1]], any(
        flag.startswith("--from") for flag in flags
    )


def _docs_not_copied(text: str) -> list[Finding]:
    """The Dockerfile, where its last stage copies none of the documentation
    directories the declaration names -- the whole context (`COPY . .`), the
    directory, or what holds it. A copy from another stage is taken to carry
    it, since what that stage holds is not read here."""
    instructions = _instructions(text)
    stages = [n for n, (_, keyword, _) in enumerate(instructions) if keyword == "FROM"]
    if not stages:
        return []
    begun = stages[-1]
    copied: list[str] = []
    for _, keyword, rest in instructions[begun:]:
        if keyword not in ("COPY", "ADD"):
            continue
        read = _sources(rest)
        if read is None:
            return []
        sources, staged = read
        if staged:
            return []
        copied += sources
    missing = [
        directory
        for directory in _documented
        if not any(
            source in (".", "*") or directory == source or directory.startswith(source + "/")
            for source in copied
        )
    ]
    if not missing:
        return []
    line = instructions[begun][0]
    return [Finding("docs-not-in-image", "Dockerfile", line, line_of(text, line))]


class _Dropped(cst.CSTTransformer):
    def __init__(self, test: bool) -> None:
        super().__init__()
        self.test = test
        self.applied: list[str] = []

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.RemovalSentinel:
        body = updated_node.body
        if len(body) == 1 and isinstance(body[0], cst.Expr) and _is_read(body[0].value):
            self.applied.append("escape-hatch-read-dropped")
            return cst.RemoveFromParent()
        return updated_node

    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.IndentedBlock:
        if original_node.body and not updated_node.body:
            return updated_node.with_changes(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
        return updated_node

    def leave_Dict(self, original_node: cst.Dict, updated_node: cst.Dict) -> cst.Dict:
        if not self.test:
            return updated_node
        kept = [
            element
            for element in updated_node.elements
            if not (isinstance(element, cst.DictElement) and literal(element.key) == CASE)
        ]
        if len(kept) == len(updated_node.elements):
            return updated_node
        self.applied.extend(
            ["escape-hatch-case-dropped"] * (len(updated_node.elements) - len(kept))
        )
        if kept and not isinstance(updated_node.elements[-1].comma, cst.Comma):
            kept[-1] = kept[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
        return updated_node.with_changes(elements=kept)


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, imports: Imports, dropped: bool) -> None:
        super().__init__()
        self.imports = imports
        self.dropped = dropped
        self.found: list[tuple[str, int]] = []

    def _at(self, rule: str, node: cst.CSTNode) -> None:
        self.found.append((rule, self.get_metadata(PositionProvider, node).start.line))

    def visit_Call(self, node: cst.Call) -> None:
        if is_sdk(node.func, "connect", self.imports):
            named = {arg.keyword.value for arg in node.args if arg.keyword is not None}
            if named.intersection(DECLARED):
                self._at("connect-names-the-declaration", node)
        if (
            self.dropped
            and isinstance(node.func, cst.Attribute)
            and node.func.attr.value == READ
        ):
            self._at("escape-hatch-read-kept", node)
