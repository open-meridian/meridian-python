"""open-meridian 0.9.0 to 0.10.0: the SDK declares contract v5, and a plugin's
pages are one list, each with the levels it serves.

On 0.9.0 a plugin declared its admin pages, `Interface(admin_pages=(Page(path,
title), ...))`, and served them to a caller whose `deployment_admin` was true.
On 0.10.0 it declares `Interface(pages=...)`, each page with its levels, and
serves each in a session opened at one of them; a Manage session is at
`admin`. `admin_pages=` is still taken, as pages at admin, for this release.

So `admin_pages=` becomes `pages=`, and a `Page(path, title)` naming no levels,
which on 0.9.0 could only be an admin page, gains `levels=["admin"]`: what the
plugin declared keeps its meaning. What decides who is served stays by hand:
`deployment_admin` read to gate a page, since a plugin admin need not be a
deployment admin, and which of the plugin's other checks become a page's
levels is the person's to say. migration.toml, beside this, records each rule.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import Imports, imports_of, is_sdk, is_test, line_of

#: What a page that was an admin page serves.
ADMIN = "admin"


def _uses_sdk(imports: Imports) -> bool:
    return bool(imports.modules or imports.names)


def _keyword(call: cst.Call, name: str) -> cst.Arg | None:
    return next(
        (arg for arg in call.args if arg.keyword is not None and arg.keyword.value == name),
        None,
    )


def _positional(call: cst.Call) -> list[cst.Arg]:
    return [arg for arg in call.args if arg.keyword is None and not arg.star]


def rewrite(path: str, text: str) -> Rewritten:
    if not path.endswith(".py"):
        return Rewritten(text)
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not _uses_sdk(imports):
        return Rewritten(text)
    pages = _Pages(imports)
    rewritten = module.visit(pages)
    return Rewritten(rewritten.code, tuple(pages.applied))


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not _uses_sdk(imports):
        return []
    found = _Left(imports, gates=not is_test(path))
    MetadataWrapper(module).visit(found)
    return [
        Finding(rule, path, line, line_of(text, line)) for line, rule in sorted(found.places)
    ]


# ── The rewrite ──────────────────────────────────────────────────────────


def _quote(call: cst.Call) -> str:
    """The quote the call's own strings are in, for the level it gains."""
    for arg in call.args:
        if isinstance(arg.value, cst.SimpleString):
            return arg.value.quote[0]
    return '"'


def _appended(call: cst.Call, arg: cst.Arg) -> cst.Call:
    """`arg` after the call's last, in the call's own layout: on a line of its
    own where each is, with the trailing comma the call has or has not."""
    args = list(call.args)
    last = args[-1]
    if isinstance(last.comma, cst.Comma):
        between = args[-2].comma if len(args) > 1 else last.comma
        args[-1] = last.with_changes(comma=between)
        args.append(arg.with_changes(comma=last.comma))
    else:
        args[-1] = last.with_changes(
            comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" ")),
            whitespace_after_arg=cst.SimpleWhitespace(""),
        )
        args.append(arg.with_changes(whitespace_after_arg=last.whitespace_after_arg))
    return call.with_changes(args=args)


class _Pages(cst.CSTTransformer):
    def __init__(self, imports: Imports) -> None:
        super().__init__()
        self.imports = imports
        self.applied: list[str] = []

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        call = updated_node
        if is_sdk(call.func, "Interface", self.imports):
            retired = _keyword(call, "admin_pages")
            if retired is None or _keyword(call, "pages") is not None:
                return call
            self.applied.append("admin-pages-keyword")
            renamed = retired.with_changes(keyword=cst.Name("pages"))
            return call.with_changes(
                args=[renamed if arg is retired else arg for arg in call.args]
            )
        if is_sdk(call.func, "Page", self.imports):
            if (
                _keyword(call, "levels") is not None
                or any(arg.star for arg in call.args)
                or len(_positional(call)) > 2
                or not call.args
            ):
                return call
            quote = _quote(call)
            level = cst.Arg(
                keyword=cst.Name("levels"),
                equal=cst.AssignEqual(
                    whitespace_before=cst.SimpleWhitespace(""),
                    whitespace_after=cst.SimpleWhitespace(""),
                ),
                value=cst.List([cst.Element(cst.SimpleString(f"{quote}{ADMIN}{quote}"))]),
            )
            self.applied.append("page-at-admin")
            return _appended(call, level)
        return call


# ── What is left ─────────────────────────────────────────────────────────


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, imports: Imports, *, gates: bool) -> None:
        super().__init__()
        self.imports = imports
        # Whether a deployment_admin read here may decide who is served: not
        # in a test, which builds callers rather than serving them.
        self.gates = gates
        self.places: list[tuple[int, str]] = []

    def _at(self, node: cst.CSTNode, rule: str) -> None:
        self.places.append((self.get_metadata(PositionProvider, node).start.line, rule))

    def visit_Attribute(self, node: cst.Attribute) -> None:
        if node.attr.value == "admin_pages":
            self._at(node, "admin-pages-read")
        elif node.attr.value == "deployment_admin" and self.gates:
            self._at(node, "deployment-admin-gate")

    def visit_Call(self, node: cst.Call) -> None:
        if is_sdk(node.func, "Interface", self.imports) and len(_positional(node)) > 2:
            self._at(node, "admin-pages-positional")
