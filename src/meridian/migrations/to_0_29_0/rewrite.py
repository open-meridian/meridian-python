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

For every plugin, two things the migration cannot move are left by hand:
`connect` given an interface, settings or `reads_external_accounts`, which
from v25 belong in the version's declaration, since registration is held to
the declaration uploaded; and a pyproject.toml whose `[tool.meridian]` names
no declaration. migration.toml, beside this, records the rules.
"""

from __future__ import annotations

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

#: Whether the plugin being migrated holds connectivity and no role keeping
#: the read, from its pyproject.toml (`given`).
_dropped = False


def given(files: dict[str, str]) -> None:
    """The plugin's roles, read once from its pyproject.toml before any file
    is rewritten."""
    global _dropped
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
