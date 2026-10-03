"""open-meridian 0.15.0 to 0.16.0: the SDK declares contract v11, and the edge
keeps its own.

Nothing is rewritten. Three arguments contract v11 deprecates are found and
left by hand, since what replaces each is the plugin's own conversion: an
ExternalAccount's `venue_account_type=` (the account kind, converted, and the
type as reported only where it does not convert); a `record_holding` call's
`also_counted_in_cash=` (the cash netted at the edge, with its provenance);
and `currency_assumed=` anywhere (the currency's provenance, derived by a
named rule). And `meridian.figures`' bounds, MOST_FIGURES and LONGEST_*,
which moved to `meridian.bounds` under the data dictionary's names, are
found where they are imported or read. migration.toml, beside this, records
each rule.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import imports_of, line_of

#: Each deprecated keyword, and the rule that finds it.
DEPRECATED = {
    "venue_account_type": "account-kind",
    "also_counted_in_cash": "counted-once",
    "currency_assumed": "currency-provenance",
}

#: meridian.figures' bounds, gone from it: each is meridian.bounds' now.
FIGURE_BOUNDS = frozenset({"MOST_FIGURES", "LONGEST_LABEL", "LONGEST_TEXT", "LONGEST_WHY"})


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


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.places: set[tuple[int, str]] = set()

    def _at(self, node: cst.CSTNode, rule: str) -> None:
        self.places.add((self.get_metadata(PositionProvider, node).start.line, rule))

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        module = node.module
        named = cst.Module([]).code_for_node(module) if module is not None else ""
        if named not in ("meridian.figures", "figures") or isinstance(
            node.names, cst.ImportStar
        ):
            return
        if any(
            isinstance(alias.name, cst.Name) and alias.name.value in FIGURE_BOUNDS
            for alias in node.names
        ):
            self._at(node, "figures-bounds")

    def visit_Attribute(self, node: cst.Attribute) -> None:
        if node.attr.value in FIGURE_BOUNDS and cst.Module([]).code_for_node(
            node.value
        ).endswith("figures"):
            self._at(node, "figures-bounds")

    def visit_Arg(self, node: cst.Arg) -> None:
        if node.keyword is None:
            return
        rule = DEPRECATED.get(node.keyword.value)
        if rule is not None:
            self._at(node, rule)
