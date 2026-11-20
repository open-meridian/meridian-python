"""open-meridian 0.36.3 to 0.37.0: step 3d, with no contract change.

An instance running as shards, or with a standby, writes only in its
shard's folder, known once the plugin registered; on a storage its copy
step converted (`.meridian/copied-from-<claim>`), `edge.storage_dir()` read
before Register raises. So a plugin reads its storage from its class's
`on_start`:

- `trading-files-on-start` (rewritten): the connectivity template's trading
  files from 0.34.0 to 0.36.3 -- `sent, enabled, originated =
  connectivity.trading_files(edge.storage_dir())` in a function, and the
  Trader built there given `sent=connectivity.Sent(sent)`,
  `enabled=connectivity.Sent(enabled)` and
  `watched=connectivity.Watched(originated)` -- become the Trader given
  none, which reads them on start; the assignment goes, and `edge`'s import
  where nothing else names it. Anything else made of those names is left.
- `noted-file-read-whole` (by hand): a `Sent`'s file (`sent.json`,
  `enabled.json`, `charged.json`) read whole, a test's most often: from
  0.37.0 each name is a file of its own beside it, and the file is only read.
- `storage-read-before-register` (by hand): `edge.storage_dir()` read where
  a plugin's code runs before it registers -- a module's top level, a class
  body, `main()` or an `__init__` -- such as `option_chains.SeriesTimes(
  edge.storage_dir() / "series.json")` built with the class.

migration.toml, beside this, records both rules.
"""

from __future__ import annotations

import re

import libcst as cst
from libcst.metadata import MetadataWrapper, ParentNodeProvider, PositionProvider

from .. import Finding, Rewritten
from .._cst import Imports, dotted, imports_of, is_test, line_of

REWRITTEN = "trading-files-on-start"
LEFT = "storage-read-before-register"
READ_WHOLE = "noted-file-read-whole"
#: A `Sent`'s file read as the JSON list an earlier release wrote whole.
_READ_WHOLE = re.compile(
    r"""(?:sent|enabled|charged)\.json["']\s*\)*\s*\.read_(?:text|bytes)\("""
)
#: Where a plugin's code runs before it registers.
BEFORE_REGISTER = frozenset({"main", "__init__"})
#: The Trader's arguments the files went to, and what built each.
GIVEN = {"sent": "Sent", "enabled": "Sent", "watched": "Watched"}
COMMENT = (
    "# What it sent, enabled and watched is read from its storage on start,",
    "# once registered: a shard's own folder is known only then.",
)


def _sdk(node: cst.BaseExpression, name: str, imports: Imports) -> bool:
    """Whether `node` names the SDK's `name`: imported from it, or an
    attribute of a module imported from it (`connectivity.Sent`, `edge.storage_dir`)."""
    if isinstance(node, cst.Name):
        return imports.names.get(node.value) == name
    if isinstance(node, cst.Attribute) and node.attr.value == name:
        base = dotted(node.value)
        if base is None:
            return False
        first = base.split(".")[0]
        return first in imports.modules or first in imports.names
    return False


def _reads_storage(node: cst.BaseExpression, imports: Imports) -> bool:
    return (
        isinstance(node, cst.Call) and not node.args and _sdk(node.func, "storage_dir", imports)
    )


def _files_of(statement: cst.BaseStatement, imports: Imports) -> tuple[str, ...] | None:
    """The names bound by `a, b, c = <sdk>.trading_files(<sdk>.storage_dir())`."""
    if not isinstance(statement, cst.SimpleStatementLine) or len(statement.body) != 1:
        return None
    assign = statement.body[0]
    if not isinstance(assign, cst.Assign) or len(assign.targets) != 1:
        return None
    call = assign.value
    if not (
        isinstance(call, cst.Call)
        and _sdk(call.func, "trading_files", imports)
        and len(call.args) == 1
        and _reads_storage(call.args[0].value, imports)
    ):
        return None
    target = assign.targets[0].target
    if not isinstance(target, cst.Tuple) or len(target.elements) != 3:
        return None
    names = tuple(
        e.value.value if isinstance(e.value, cst.Name) else "" for e in target.elements
    )
    return names if all(names) else None


class _Uses(cst.CSTVisitor):
    def __init__(self) -> None:
        self.names: list[str] = []

    def visit_Name(self, node: cst.Name) -> None:
        self.names.append(node.value)


def _uses(node: cst.CSTNode) -> list[str]:
    uses = _Uses()
    node.visit(uses)
    return uses.names


class _Dropped(cst.CSTTransformer):
    """The Trader's `sent=`, `enabled=` and `watched=` made of `files`."""

    def __init__(self, files: tuple[str, ...], imports: Imports) -> None:
        super().__init__()
        self.files = dict(zip(("sent", "enabled", "watched"), files, strict=True))
        self.imports = imports
        self.dropped = 0

    def _given(self, arg: cst.Arg) -> bool:
        keyword = arg.keyword.value if arg.keyword is not None else ""
        if keyword not in GIVEN:
            return False
        made = arg.value
        return (
            isinstance(made, cst.Call)
            and _sdk(made.func, GIVEN[keyword], self.imports)
            and len(made.args) == 1
            and made.args[0].keyword is None
            and isinstance(made.args[0].value, cst.Name)
            and made.args[0].value.value == self.files[keyword]
        )

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if not _sdk(updated_node.func, "Trader", self.imports):
            return updated_node
        kept = [arg for arg in updated_node.args if not self._given(arg)]
        if len(kept) == len(updated_node.args):
            return updated_node
        self.dropped += len(updated_node.args) - len(kept)
        return updated_node.with_changes(args=kept)


class _OnStart(cst.CSTTransformer):
    def __init__(self, imports: Imports) -> None:
        super().__init__()
        self.imports = imports
        self.rewrote = 0

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        body = updated_node.body
        if not isinstance(body, cst.IndentedBlock):
            return updated_node
        statements = list(body.body)
        for at, statement in enumerate(statements):
            files = _files_of(statement, self.imports)
            if files is None or at + 1 == len(statements):
                continue
            rest = cst.IndentedBlock(body=statements[at + 1 :])
            dropping = _Dropped(files, self.imports)
            after = rest.visit(dropping)
            if (
                not isinstance(after, cst.IndentedBlock)
                or not isinstance(statement, cst.SimpleStatementLine)
                or dropping.dropped != 3
                or set(files) & set(_uses(after))
            ):
                continue  # the files are given elsewhere too: left by hand
            following = list(after.body)
            first = following[0]
            if not isinstance(first, cst.SimpleStatementLine | cst.BaseCompoundStatement):
                continue
            comment = [
                cst.EmptyLine(indent=True, comment=cst.Comment(line)) for line in COMMENT
            ]
            following[0] = first.with_changes(
                leading_lines=[*statement.leading_lines, *comment, *first.leading_lines]
            )
            self.rewrote += 1
            return updated_node.with_changes(
                body=body.with_changes(body=[*statements[:at], *following])
            )
        return updated_node


class _NoEdge(cst.CSTTransformer):
    """`from meridian import edge` without `edge`, which nothing names now."""

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        if updated_node.relative or dotted(updated_node.module or cst.Name("")) != "meridian":
            return updated_node
        names = updated_node.names
        if isinstance(names, cst.ImportStar):
            return updated_node
        kept = [
            alias
            for alias in names
            if not (dotted(alias.name) == "edge" and alias.asname is None)
        ]
        if len(kept) == len(names):
            return updated_node
        if not kept:
            return cst.RemoveFromParent()
        kept[-1] = kept[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
        return updated_node.with_changes(names=kept)


def rewrite(path: str, text: str) -> Rewritten:
    if not path.endswith(".py") or is_test(path) or "trading_files" not in text:
        return Rewritten(text)
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError:
        return Rewritten(text)
    imports = imports_of(module)
    moving = _OnStart(imports)
    moved = module.visit(moving)
    if not moving.rewrote:
        return Rewritten(text)
    if imports.names.get("edge") == "edge" and "edge" not in _uses(_without_imports(moved)):
        moved = moved.visit(_NoEdge())
    return Rewritten(moved.code, (REWRITTEN,) * moving.rewrote)


def _without_imports(module: cst.Module) -> cst.Module:
    return module.with_changes(
        body=[
            s
            for s in module.body
            if not (
                isinstance(s, cst.SimpleStatementLine)
                and all(isinstance(b, cst.Import | cst.ImportFrom) for b in s.body)
            )
        ]
    )


class _Early(cst.CSTVisitor):
    """Each `storage_dir()` read where code runs before Register."""

    METADATA_DEPENDENCIES = (PositionProvider, ParentNodeProvider)

    def __init__(self, imports: Imports) -> None:
        self.imports = imports
        self.lines: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        if not _reads_storage(node, self.imports):
            return
        at: cst.CSTNode = node
        while True:
            parent = self.get_metadata(ParentNodeProvider, at, None)
            if parent is None or isinstance(parent, cst.ClassDef):
                break  # a module's top level or a class body
            if isinstance(parent, cst.FunctionDef):
                if parent.name.value not in BEFORE_REGISTER:
                    return
                break
            if isinstance(parent, cst.Lambda):
                return  # called later, not where it is written
            at = parent
        self.lines.append(self.get_metadata(PositionProvider, node).start.line)


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    whole = [
        Finding(READ_WHOLE, path, n, line.strip())
        for n, line in enumerate(text.splitlines(), start=1)
        if _READ_WHOLE.search(line)
    ]
    return whole + _early(path, text)


def _early(path: str, text: str) -> list[Finding]:
    if is_test(path) or "storage_dir" not in text:
        return []
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError:
        return []
    early = _Early(imports_of(module))
    MetadataWrapper(module).visit(early)
    return [Finding(LEFT, path, line, line_of(text, line)) for line in sorted(set(early.lines))]
