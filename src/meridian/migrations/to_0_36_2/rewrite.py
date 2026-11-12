"""open-meridian 0.36.1 to 0.36.2: fixes, with no contract change.

Nothing is rewritten: what a plugin calls kept its shape. The row-key rule
(spec/the-lake rule 5, ruled 2026-11-12) the SDK's helpers now keep is named
where a plugin builds rows itself: `valid-time-from-the-clock`, a row's
`valid_from_ns` given the plugin's clock (`now`, `self.now()`,
`time.time_ns()` ...) in its code, not its tests, so a key recorded again is
restated under a new valid time, which core refuses from stage H.
migration.toml, beside this, records the rule.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import dotted, is_test, line_of

RULE = "valid-time-from-the-clock"
#: A name holding the clock's time, and the clocks called.
_NOW = frozenset({"now", "now_ns"})
_CLOCKS = frozenset({"now", "_now", "now_ns", "clock_ns", "time_ns"})


def _clock(value: cst.BaseExpression) -> bool:
    """Whether a value is the plugin's clock: a name holding it, or a call
    of one (`self.now()`, `time.time_ns()`)."""
    if isinstance(value, cst.Name):
        return value.value in _NOW
    if isinstance(value, cst.Call) and not value.args:
        called = dotted(value.func)
        return called is not None and called.rsplit(".", 1)[-1] in _CLOCKS
    return False


class _Clocked(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        self.lines: list[int] = []

    def visit_Arg(self, node: cst.Arg) -> None:
        named = node.keyword is not None and node.keyword.value == "valid_from_ns"
        if named and _clock(node.value):
            self.lines.append(self.get_metadata(PositionProvider, node).start.line)


def rewrite(path: str, text: str) -> Rewritten:
    return Rewritten(text)


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py") or is_test(path) or "valid_from_ns" not in text:
        return []
    try:
        wrapper = MetadataWrapper(cst.parse_module(text))
    except cst.ParserSyntaxError:
        return []
    clocked = _Clocked()
    wrapper.visit(clocked)
    lines = sorted(set(clocked.lines))
    return [Finding(RULE, path, line, line_of(text, line)) for line in lines]
