"""open-meridian 0.11.0 to 0.12.0: the SDK declares contract v7, and a
statement names its external account with its figures per margin segment.

On 0.11.0 a plugin sent a statement's figures flat --
`record_holdings_statement(buying_power=..., margin_requirement=...,
maintenance_excess=...)` -- and named no external account; the sidecar read the
statement's account from its rows. On 0.12.0 the figures are a set per
margin segment, `figures=[StatementFigures(segment="", ...)]`, the set with no
segment being the account's as a whole, and the statement names its external
account, which the sidecar translates through the link as it does a row's.

So the flat figures become one set with no segment, which is what the
sidecar reads them as from an older plugin: the statement keeps its meaning.
Which external account a statement was read for only the plugin knows, so a
call naming none is left by hand. migration.toml, beside this, records each
rule.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import add_import, imports_of, line_of

#: The operation whose call is rewritten.
STATEMENT = "record_holdings_statement"

#: The figures a plugin before v7 sent flat, in the order a set takes them.
FLAT = ("buying_power", "margin_requirement", "maintenance_excess")


def _statement(call: cst.Call) -> bool:
    return isinstance(call.func, cst.Attribute) and call.func.attr.value == STATEMENT


def _keywords(call: cst.Call) -> dict[str, cst.Arg]:
    return {arg.keyword.value: arg for arg in call.args if arg.keyword is not None}


def rewrite(path: str, text: str) -> Rewritten:
    if not path.endswith(".py"):
        return Rewritten(text)
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not imports.modules and not imports.names:
        return Rewritten(text)  # it does not use the SDK
    figures = _Figures()
    rewritten = module.visit(figures)
    if figures.applied:
        rewritten = add_import(rewritten, "meridian", "StatementFigures")
    return Rewritten(rewritten.code, tuple(figures.applied))


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
        Finding("statement-external-account", path, line, line_of(text, line))
        for line in sorted(found.lines)
    ]


class _Figures(cst.CSTTransformer):
    """A statement's flat figures as the one set with no segment."""

    def __init__(self) -> None:
        super().__init__()
        self.applied: list[str] = []

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        call = updated_node
        if not _statement(call):
            return call
        keywords = _keywords(call)
        flat = [keywords[name] for name in FLAT if name in keywords]
        if not flat or "figures" in keywords or any(arg.star for arg in call.args):
            return call
        self.applied.append("statement-flat-figures")
        figures = cst.Call(
            func=cst.Name("StatementFigures"),
            args=[
                cst.Arg(
                    keyword=cst.Name("segment"),
                    value=cst.SimpleString('""'),
                    equal=cst.AssignEqual(
                        whitespace_before=cst.SimpleWhitespace(""),
                        whitespace_after=cst.SimpleWhitespace(""),
                    ),
                    comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" ")),
                ),
                *[
                    arg.with_changes(
                        comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" "))
                        if i < len(flat) - 1
                        else cst.MaybeSentinel.DEFAULT,
                        whitespace_after_arg=cst.SimpleWhitespace(""),
                    )
                    for i, arg in enumerate(flat)
                ],
            ],
        )
        replacement = flat[0].with_changes(
            keyword=cst.Name("figures"),
            value=cst.List(elements=[cst.Element(value=figures)]),
        )
        args = []
        for arg in call.args:
            if arg is flat[0]:
                args.append(replacement)
            elif any(arg is other for other in flat[1:]):
                continue
            else:
                args.append(arg)
        # The last argument keeps the call's own trailing comma, or none.
        if args and call.args[-1] is not args[-1]:
            args[-1] = args[-1].with_changes(comma=call.args[-1].comma)
        return call.with_changes(args=args)


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        if not _statement(node):
            return
        keywords = _keywords(node)
        if "external_account_id" in keywords or any(arg.star for arg in node.args):
            return
        self.lines.append(self.get_metadata(PositionProvider, node).start.line)
