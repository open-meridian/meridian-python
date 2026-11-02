"""open-meridian 0.35.1 to 0.35.2: a typed delivery of the settings keeps the
settings the SDK declares beside the class (`.values`), and `RawStore.tend`
reads a kind's window from the settings as delivered.

Nothing is rewritten. A `Declaration(settings=Config.declared())` -- the
0.35.1 way to reach the storage kinds' window settings, giving up the typed
delivery -- is found and left by hand: whether the plugin's `on_settings`
reads the untyped delivery's `missing_required` is its own to say.
migration.toml, beside this, records the rule.
"""

from __future__ import annotations

from collections.abc import Set

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import Imports, imports_of, is_sdk, line_of


def rewrite(path: str, text: str) -> Rewritten:
    return Rewritten(text)


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not imports.modules and not imports.names:
        return []  # it does not use the SDK
    aliases = _Aliases()
    module.visit(aliases)
    found = _Left(imports, aliases.names)
    MetadataWrapper(module).visit(found)
    return [
        Finding("typed-settings-declared", path, line, line_of(text, line))
        for line in sorted(found.lines)
    ]


def _declared(value: cst.BaseExpression) -> bool:
    """`<name>.declared()`: a typed class's settings, untyped."""
    return (
        isinstance(value, cst.Call)
        and not value.args
        and isinstance(value.func, cst.Attribute)
        and value.func.attr.value == "declared"
    )


class _Aliases(cst.CSTVisitor):
    """The names a file binds to a typed class's settings untyped --
    `SETTINGS = Config.declared()` -- which a declaration then names (SDK
    0.35.3: the workaround through an alias was missed)."""

    def __init__(self) -> None:
        super().__init__()
        self.names: set[str] = set()

    def visit_Assign(self, node: cst.Assign) -> None:
        if _declared(node.value):
            for target in node.targets:
                if isinstance(target.target, cst.Name):
                    self.names.add(target.target.value)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if (
            node.value is not None
            and _declared(node.value)
            and isinstance(node.target, cst.Name)
        ):
            self.names.add(node.target.value)


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, imports: Imports, aliases: Set[str] = frozenset()) -> None:
        super().__init__()
        self.imports = imports
        self.aliases = aliases
        self.lines: set[int] = set()

    def visit_Call(self, node: cst.Call) -> None:
        if not is_sdk(node.func, "Declaration", self.imports):
            return
        for arg in node.args:
            if (
                arg.keyword is not None
                and arg.keyword.value == "settings"
                and (
                    _declared(arg.value)
                    or isinstance(arg.value, cst.Name)
                    and arg.value.value in self.aliases
                )
            ):
                self.lines.add(self.get_metadata(PositionProvider, arg).start.line)
