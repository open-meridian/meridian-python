"""open-meridian 0.23.0 to 0.24.0: the SDK declares contract v20, and the
roles dgm, ccm and match are data, connectivity and confirmation.

Two rewrites, both of a role's name where a plugin names a role: in Python, a
string literal in a `roles=` argument or given as the role to the suites'
`run`, `run_async`, `suite` and `names` or to `Caller.level_for`,
`read_for` and `write_for`; and in pyproject.toml, the `roles` of
[tool.meridian]. A literal anywhere else is left as it is: "match" is also an
English word. migration.toml, beside this, records the rules.
"""

from __future__ import annotations

import re

import libcst as cst

from .. import Finding, Rewritten
from .._cst import imports_of

#: The renames, ruled by the product owner on 2026-10-10.
RENAMED = {"dgm": "data", "ccm": "connectivity", "match": "confirmation"}
#: What takes a role as its first argument.
ASKED = frozenset({"run", "run_async", "suite", "names", "level_for", "read_for", "write_for"})
#: [tool.meridian]'s roles line in pyproject.toml.
_ROLES_LINE = re.compile(r"^(roles\s*=\s*\[)([^\]]*)(\])", re.M)


def rewrite(path: str, text: str) -> Rewritten:
    if path.endswith("pyproject.toml"):
        return _metadata(text)
    if not path.endswith(".py"):
        return Rewritten(text)
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not imports.modules and not imports.names:
        return Rewritten(text)  # it does not use the SDK
    renamer = _Renamer()
    rewritten = module.visit(renamer)
    return Rewritten(rewritten.code, tuple(renamer.rules))


def left(path: str, text: str) -> list[Finding]:
    return []


def _metadata(text: str) -> Rewritten:
    if "[tool.meridian]" not in text:
        return Rewritten(text)
    head, _, tail = text.partition("[tool.meridian]")
    section, nxt, rest = tail.partition("\n[")
    rules: list[str] = []

    def renamed(match: re.Match[str]) -> str:
        def one(role: re.Match[str]) -> str:
            rules.append("metadata-role-renamed")
            return f"{role.group(1)}{RENAMED[role.group(2)]}{role.group(1)}"

        inner = re.sub(r"""(["'])(dgm|ccm|match)\1""", one, match.group(2))
        return f"{match.group(1)}{inner}{match.group(3)}"

    section = _ROLES_LINE.sub(renamed, section)
    return Rewritten(head + "[tool.meridian]" + section + nxt + rest, tuple(rules))


def _named(node: cst.BaseExpression) -> str:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return node.attr.value
    return ""


class _Renamer(cst.CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self.rules: list[str] = []

    def _role(self, node: cst.BaseExpression) -> cst.BaseExpression:
        if isinstance(node, cst.SimpleString) and node.evaluated_value in RENAMED:
            quote = node.value[0]
            self.rules.append("role-renamed")
            return node.with_changes(
                value=f"{quote}{RENAMED[str(node.evaluated_value)]}{quote}"
            )
        if isinstance(node, (cst.List, cst.Tuple, cst.Set)):
            return node.with_changes(
                elements=[e.with_changes(value=self._role(e.value)) for e in node.elements]
            )
        return node

    def leave_Call(self, original: cst.Call, updated: cst.Call) -> cst.Call:
        args = list(updated.args)
        changed = False
        for n, arg in enumerate(args):
            if arg.keyword is not None and arg.keyword.value == "roles":
                args[n] = arg.with_changes(value=self._role(arg.value))
                changed = True
        if _named(updated.func) in ASKED and args and args[0].keyword is None:
            args[0] = args[0].with_changes(value=self._role(args[0].value))
            changed = True
        return updated.with_changes(args=args) if changed else updated
