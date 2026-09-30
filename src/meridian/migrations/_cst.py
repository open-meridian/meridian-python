"""What the rewrites share: which names in a file are this SDK's, and the text
of a string literal. Read with libcst, which keeps a file's formatting and
comments as they were wherever nothing is rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor

#: The SDK's modules a plugin may import by name, rather than names in them.
SUBMODULES = frozenset({"asgi", "client", "errors", "operations"})


def dotted(node: cst.BaseExpression) -> str | None:
    """`meridian.errors.CallFailed` as that text; None for anything but names."""
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        base = dotted(node.value)
        return None if base is None else f"{base}.{node.attr.value}"
    return None


def literal(node: cst.BaseExpression) -> str | None:
    """A string literal's text: plain or implicitly joined, and an f-string's
    literal parts, with NUL where each value goes. None for anything else."""
    if isinstance(node, cst.SimpleString):
        value = node.evaluated_value
        return value if isinstance(value, str) else None
    if isinstance(node, cst.ConcatenatedString):
        left, right = literal(node.left), literal(node.right)
        return None if left is None or right is None else left + right
    if isinstance(node, cst.FormattedString):
        return "".join(
            part.value if isinstance(part, cst.FormattedStringText) else "\0"
            for part in node.parts
        )
    return None


@dataclass
class Imports:
    """How one file names the SDK."""

    # Local names bound to the package or one of its modules: `meridian`,
    # `om` for `import meridian as om`, `errors` for `from meridian import
    # errors`.
    modules: set[str] = field(default_factory=set)
    # Local names for things in the SDK, from `from meridian import X as Y`.
    names: dict[str, str] = field(default_factory=dict)
    # What `import meridian [as om]` binds, for writing `meridian.X`.
    package: str | None = None


class _Imports(cst.CSTVisitor):
    def __init__(self) -> None:
        self.found = Imports()

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            name = dotted(alias.name)
            if name is None or not (name == "meridian" or name.startswith("meridian.")):
                continue
            if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
                local = alias.asname.name.value
                self.found.modules.add(local)
                if name == "meridian":
                    self.found.package = local
            else:
                self.found.modules.add("meridian")
                if name == "meridian":
                    self.found.package = "meridian"

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.relative or node.module is None or isinstance(node.names, cst.ImportStar):
            return
        module = dotted(node.module)
        if module is None or not (module == "meridian" or module.startswith("meridian.")):
            return
        for alias in node.names:
            if not isinstance(alias.name, cst.Name):
                continue
            name = alias.name.value
            local = name
            if alias.asname is not None and isinstance(alias.asname.name, cst.Name):
                local = alias.asname.name.value
            if module == "meridian" and name in SUBMODULES:
                self.found.modules.add(local)
            else:
                self.found.names[local] = name


def imports_of(module: cst.Module) -> Imports:
    visitor = _Imports()
    module.visit(visitor)
    return visitor.found


def is_sdk(node: cst.BaseExpression, name: str, imports: Imports) -> bool:
    """Whether `node` names the SDK's `name`: as imported from it, or as an
    attribute of the package or one of its modules."""
    if isinstance(node, cst.Name):
        return imports.names.get(node.value) == name
    if isinstance(node, cst.Attribute) and node.attr.value == name:
        base = dotted(node.value)
        return base is not None and base.split(".")[0] in imports.modules
    return False


def is_test(path: str) -> bool:
    """A test, as `meridian plugin check` tells one: not the plugin's code."""
    name = path.rsplit("/", 1)[-1]
    return (
        path.startswith(("tests/", "test/"))
        or "/tests/" in path
        or "/test/" in path
        or (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def line_of(text: str, line: int) -> str:
    """The line `line` (from 1) of `text`, as it reads, for a finding."""
    lines = text.splitlines()
    return lines[line - 1].strip() if 0 < line <= len(lines) else ""


def _isort_key(name: str) -> tuple[int, str]:
    """Where isort, and ruff's, puts a name in `from x import ...`: constants,
    then classes, then the rest, each alphabetically."""
    if name.isupper() and len(name) > 1:
        return 0, name
    if name[:1].isupper():
        return 1, name
    return 2, name


class _AddName(cst.CSTTransformer):
    """`name` added to the first `from <module> import ...` whose names are
    in isort's order, where that order puts it."""

    def __init__(self, module: str, name: str) -> None:
        super().__init__()
        self.module = module
        self.name = name
        self.added = False

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        names = updated_node.names
        if (
            self.added
            or updated_node.relative
            or updated_node.module is None
            or dotted(updated_node.module) != self.module
            or isinstance(names, cst.ImportStar)
        ):
            return updated_node
        aliases = list(names)
        held = [dotted(alias.name) or "" for alias in aliases]
        if self.name in held:
            self.added = True
            return updated_node
        keys = [_isort_key(name) for name in held]
        if keys != sorted(keys):
            return updated_node  # somebody else's order, not guessed at
        at = next(
            (i for i, key in enumerate(keys) if key > _isort_key(self.name)), len(aliases)
        )
        separator = next(
            (alias.comma for alias in aliases[:-1] if isinstance(alias.comma, cst.Comma)),
            cst.Comma(whitespace_after=cst.SimpleWhitespace(" ")),
        )
        new = cst.ImportAlias(name=cst.Name(self.name), comma=separator)
        if at == len(aliases):
            # After the last, which gives it its comma, trailing or none.
            new = new.with_changes(comma=aliases[-1].comma)
            aliases[-1] = aliases[-1].with_changes(comma=separator)
        aliases.insert(at, new)
        self.added = True
        return updated_node.with_changes(names=aliases)


def add_import(module: cst.Module, source: str, name: str) -> cst.Module:
    """`from source import name`, beside the names already imported from
    there in their order, or on a line of its own."""
    adding = _AddName(source, name)
    added = module.visit(adding)
    if adding.added:
        return added
    context = CodemodContext()
    AddImportsVisitor.add_needed_import(context, source, name)
    return AddImportsVisitor(context).transform_module(module)
