"""open-meridian 0.36.2 to 0.36.3: fixes, with no contract change.

Nothing is rewritten: what a plugin calls kept its shape. A plugin that
builds a chain's series itself (`helpers.chains.option_series` in its code,
not its tests) in a module holding no `option_chains.SeriesTimes` is named
by hand, `series-without-a-holder`: the holder keeps each series' first
valid time and first subject across restarts (spec/the-lake rule 5), which
core enforces from stage H. migration.toml, beside this, records the rule.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import dotted, is_test, line_of

RULE = "series-without-a-holder"
#: What a module that holds its series names.
HOLDER = "SeriesTimes"


class _Built(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        self.lines: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        called = dotted(node.func)
        if called is not None and called.rsplit(".", 1)[-1] == "option_series":
            self.lines.append(self.get_metadata(PositionProvider, node).start.line)


def rewrite(path: str, text: str) -> Rewritten:
    return Rewritten(text)


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py") or is_test(path):
        return []
    if "option_series" not in text or HOLDER in text:
        return []
    try:
        wrapper = MetadataWrapper(cst.parse_module(text))
    except cst.ParserSyntaxError:
        return []
    built = _Built()
    wrapper.visit(built)
    return [Finding(RULE, path, line, line_of(text, line)) for line in sorted(set(built.lines))]
