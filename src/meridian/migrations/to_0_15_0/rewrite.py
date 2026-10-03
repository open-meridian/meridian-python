"""open-meridian 0.14.0 to 0.15.0: the SDK declares contract v10, and a
deployment's instrument identity is its own (decisions/030).

On 0.14.0 a resolve that matched nothing answered the deployment's
placeholder, `reply.placeholder` true. On 0.15.0 it answers a record the
deployment minted, and the flag is `reply.minted`: the same field on the wire,
renamed because an LCL- ID no longer means anything is unresolved. So a name
bound to a `resolve_identifier` call's result has its `.placeholder` read
renamed, within the function that bound it.

A book position's `.placeholder` has no successor, and any other `.placeholder`
read is left by hand. migration.toml, beside this, records each rule.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import imports_of, line_of

#: The operation whose result is renamed.
RESOLVE = "resolve_identifier"


def _resolve_call(node: cst.BaseExpression) -> bool:
    if isinstance(node, cst.Await):
        node = node.expression
    return (
        isinstance(node, cst.Call)
        and isinstance(node.func, cst.Attribute)
        and node.func.attr.value == RESOLVE
    )


def _bound(body: cst.CSTNode) -> set[str]:
    """The names a function binds to a resolve's result."""
    names: set[str] = set()

    class Binding(cst.CSTVisitor):
        def visit_Assign(self, node: cst.Assign) -> None:
            if _resolve_call(node.value):
                for target in node.targets:
                    if isinstance(target.target, cst.Name):
                        names.add(target.target.value)

        def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
            if (
                node.value is not None
                and _resolve_call(node.value)
                and isinstance(node.target, cst.Name)
            ):
                names.add(node.target.value)

    body.visit(Binding())
    return names


def rewrite(path: str, text: str) -> Rewritten:
    if not path.endswith(".py"):
        return Rewritten(text)
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not imports.modules and not imports.names:
        return Rewritten(text)  # it does not use the SDK
    renaming = _Minted()
    rewritten = module.visit(renaming)
    return Rewritten(rewritten.code, tuple(renaming.applied))


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not imports.modules and not imports.names:
        return []
    found = _Left()
    MetadataWrapper(module).visit(found)
    return [
        Finding("position-placeholder", path, line, line_of(text, line))
        for line in sorted(set(found.lines))
    ]


class _Minted(cst.CSTTransformer):
    """`name.placeholder` as `name.minted`, for a name bound to a resolve's
    result in the function being left."""

    def __init__(self) -> None:
        super().__init__()
        self.applied: list[str] = []
        self.scopes: list[set[str]] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.scopes.append(_bound(node.body))

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        self.scopes.pop()
        return updated_node

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        if (
            self.scopes
            and updated_node.attr.value == "placeholder"
            and isinstance(updated_node.value, cst.Name)
            and updated_node.value.value in self.scopes[-1]
        ):
            self.applied.append("resolve-minted")
            return updated_node.with_changes(attr=cst.Name("minted"))
        return updated_node


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[int] = []

    def visit_Attribute(self, node: cst.Attribute) -> None:
        if node.attr.value == "placeholder":
            self.lines.append(self.get_metadata(PositionProvider, node).start.line)
