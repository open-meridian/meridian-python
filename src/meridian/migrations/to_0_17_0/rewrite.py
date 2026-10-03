"""open-meridian 0.16.0 to 0.17.0: the SDK declares contract v12, and the
deployment serves its MCP.

Nothing is rewritten. A page or route that takes a method other than GET and
declares no typed record of inputs (`params=`), and does not say it is not
offered to agents (`tool=False`), is found and left by hand: no tool is
derived from it, and its record is the plugin's to write. migration.toml,
beside this, records the rule.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import imports_of, line_of

#: The declarations a route is made by.
DECLARING = frozenset({"page", "route"})
#: The methods that change nothing.
SAFE = frozenset({"GET", "HEAD"})


def rewrite(path: str, text: str) -> Rewritten:
    return Rewritten(text)


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not imports.modules and not imports.names:
        return []  # it does not use the SDK
    found = _Left()
    MetadataWrapper(module).visit(found)
    return [
        Finding(rule, path, line, line_of(text, line)) for line, rule in sorted(found.places)
    ]


def _methods(call: cst.Call) -> set[str]:
    for arg in call.args:
        if arg.keyword is not None and arg.keyword.value == "methods":
            value = arg.value
            if isinstance(value, (cst.List, cst.Tuple)):
                return {
                    element.value.evaluated_value.upper()
                    for element in value.elements
                    if isinstance(element.value, cst.SimpleString)
                    and isinstance(element.value.evaluated_value, str)
                }
            return {"POST"}  # named some other way: assume it changes something
    return {"GET"}


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.places: set[tuple[int, str]] = set()

    def visit_Decorator(self, node: cst.Decorator) -> None:
        call = node.decorator
        if not isinstance(call, cst.Call) or not isinstance(call.func, cst.Attribute):
            return
        if call.func.attr.value not in DECLARING:
            return
        keywords = {arg.keyword.value for arg in call.args if arg.keyword is not None}
        if "params" in keywords or "tool" in keywords:
            return
        if _methods(call) - SAFE:
            line = self.get_metadata(PositionProvider, node).start.line
            self.places.add((line, "typed-route"))
