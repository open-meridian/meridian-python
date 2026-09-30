"""open-meridian 0.5.0 to 0.6.0: access to a plugin is read or write, and a
plugin declares no tags (decisions/026).

What changed for a plugin: `TagAccess` and `Caller.access` are gone, and
`Caller.read` and `Caller.write` hold the accounts a person may read and write
through the plugin, whole; `may_read` and `may_write` ask the same questions
they did, since 0.5.0 answered them over every tag at once. `Identity.tags` is
gone, and `[tool.meridian]` declares no `tags`.

Access read tag by tag becomes one set wherever the tags were only being
gathered, which keeps what it meant. Wherever a tag's own name decided
something, it does not, and the place is left by hand. migration.toml, beside
this, records both.
"""

from __future__ import annotations

import copy
import re
import tomllib
from typing import Any

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import RemoveImportsVisitor
from libcst.metadata import MetadataWrapper, ParentNodeProvider, PositionProvider

from .. import Finding, Rewritten
from .._cst import Imports, dotted, imports_of, is_sdk, line_of

READ_WRITE = ("read", "write")


def rewrite(path: str, text: str) -> Rewritten:
    if path == "pyproject.toml":
        return _pyproject(text)
    if path.endswith(".py"):
        return _python(text)
    return Rewritten(text)


def left(path: str, text: str) -> list[Finding]:
    if path == "pyproject.toml":
        return _tags_left(text)
    if path.endswith(".py"):
        return _python_left(path, text)
    return []


# ── pyproject.toml ───────────────────────────────────────────────────────

_HEADER = re.compile(r"^\s*\[\s*tool\s*\.\s*meridian\s*\]\s*(#.*)?$")
_TABLE = re.compile(r"^\s*\[\[?[^\[\]]+\]\]?\s*(#.*)?$")
_TAGS = re.compile(r"""^\s*(tags|"tags"|'tags')\s*=""")


def _section(text: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """The whole document and its [tool.meridian], when it reads."""
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None  # `meridian plugin check` says where it does not read
    section = document.get("tool", {}).get("meridian")
    return (document, section) if isinstance(section, dict) else None


def _span(lines: list[str], value: object) -> tuple[int, int, int] | None:
    """Where `tags` is in [tool.meridian]: the header's index, the first line
    to remove (the comment directly above it, if any), and the line after
    its value. Each is checked by reading it as TOML, not assumed."""
    header = next((i for i, line in enumerate(lines) if _HEADER.match(line)), None)
    if header is None:
        return None
    stop = next(
        (i for i in range(header + 1, len(lines)) if _TABLE.match(lines[i])), len(lines)
    )
    start = next((i for i in range(header + 1, stop) if _TAGS.match(lines[i])), None)
    if start is None:
        return None
    for end in range(start + 1, stop + 1):
        try:
            if tomllib.loads("".join(lines[start:end])) == {"tags": value}:
                break
        except tomllib.TOMLDecodeError:
            continue
    else:
        return None
    first = start
    while first - 1 > header and lines[first - 1].lstrip().startswith("#"):
        first -= 1
    return header, first, end


def _pyproject(text: str) -> Rewritten:
    read = _section(text)
    if read is None or "tags" not in read[1]:
        return Rewritten(text)
    document, section = read
    lines = text.splitlines(keepends=True)
    span = _span(lines, section["tags"])
    if span is None:
        return Rewritten(text)  # left() reports it
    header, first, end = span
    removed = "".join(lines[:first] + lines[end:])
    expected = copy.deepcopy(document)
    del expected["tool"]["meridian"]["tags"]
    try:
        kept = tomllib.loads(removed) == expected
    except tomllib.TOMLDecodeError:
        kept = False
    if not kept:
        return Rewritten(text)
    findings: tuple[Finding, ...] = ()
    tags = section["tags"]
    if tags:
        named = ", ".join(str(tag) for tag in tags) if isinstance(tags, list) else str(tags)
        findings = (
            Finding(
                "tags-granted",
                "pyproject.toml",
                header + 1,
                f"[tool.meridian] declared the tags {named}; the declaration is removed",
            ),
        )
    return Rewritten(removed, ("tags-undeclared",), findings)


def _tags_left(text: str) -> list[Finding]:
    read = _section(text)
    if read is None or "tags" not in read[1]:
        return []
    lines = text.splitlines()
    line = next((i + 1 for i, each in enumerate(lines) if _TAGS.match(each)), 0)
    return [Finding("tags-declared", "pyproject.toml", line, line_of(text, line))]


# ── Python ───────────────────────────────────────────────────────────────


def _python(text: str) -> Rewritten:
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not imports.modules and not imports.names:
        return Rewritten(text)  # it does not use the SDK
    access = _Access(imports)
    rewritten = MetadataWrapper(module).visit(access)
    rules = list(access.applied)
    # An import of TagAccess fails on 0.6.0, so one nothing uses goes, and
    # one something still uses stays for left() to report.
    context = CodemodContext()
    for source in ("meridian", "meridian.client"):
        RemoveImportsVisitor.remove_unused_import(context, source, "TagAccess")
    pruned = RemoveImportsVisitor(context).transform_module(rewritten)
    if pruned.code != rewritten.code:
        rules.append("tag-access-import")
    return Rewritten(pruned.code, tuple(rules))


_EQUAL = cst.AssignEqual(
    whitespace_before=cst.SimpleWhitespace(""), whitespace_after=cst.SimpleWhitespace("")
)


def _over_access(for_in: cst.CompFor) -> tuple[str, cst.BaseExpression] | None:
    """`for held in X.access` and nothing more: the name and X."""
    it = for_in.iter
    if (
        for_in.ifs
        or for_in.asynchronous is not None
        or not isinstance(for_in.target, cst.Name)
        or not isinstance(it, cst.Attribute)
        or it.attr.value != "access"
        or it.lpar
    ):
        return None
    return for_in.target.value, it.value


def _held(node: cst.BaseExpression, name: str) -> str | None:
    """`held.read` or `held.write`, for the loop's name: which of the two."""
    if (
        isinstance(node, cst.Attribute)
        and isinstance(node.value, cst.Name)
        and node.value.value == name
        and node.attr.value in READ_WRITE
        and not node.lpar
    ):
        return node.attr.value
    return None


class _Mentions(cst.CSTVisitor):
    def __init__(self, name: str) -> None:
        self.name = name
        self.found = False

    def visit_Name(self, node: cst.Name) -> None:
        self.found = self.found or node.value == self.name


def _mentions(node: cst.CSTNode, name: str) -> bool:
    visitor = _Mentions(name)
    node.visit(visitor)
    return visitor.found


def _gathered(
    elt: cst.BaseExpression, for_in: cst.CompFor
) -> tuple[cst.BaseExpression, str] | None:
    """`a for held in X.access for a in held.read`: X, and read or write."""
    inner = for_in.inner_for_in
    over = _over_access(for_in.with_changes(inner_for_in=None))
    if (
        over is None
        or inner is None
        or inner.inner_for_in is not None
        or inner.ifs
        or inner.asynchronous is not None
        or not isinstance(inner.target, cst.Name)
        or not isinstance(elt, cst.Name)
        or elt.value != inner.target.value
    ):
        return None
    attribute = _held(inner.iter, over[0])
    return (over[1], attribute) if attribute else None


def _attribute(receiver: cst.BaseExpression, name: str) -> cst.Attribute:
    return cst.Attribute(value=receiver, attr=cst.Name(name))


def _union_of(parts: list[cst.BaseExpression]) -> cst.BaseExpression:
    """One set from each tag's, joined with `|`."""
    atoms = (cst.Name, cst.Attribute, cst.Call, cst.Subscript, cst.Set, cst.SetComp)

    def atom(part: cst.BaseExpression) -> cst.BaseExpression:
        if isinstance(part, atoms) or part.lpar:
            return part
        return part.with_changes(lpar=[cst.LeftParen()], rpar=[cst.RightParen()])

    joined = atom(parts[0])
    for part in parts[1:]:
        joined = cst.BinaryOperation(left=joined, operator=cst.BitOr(), right=atom(part))
    return joined


def _fields(call: cst.Call, names: tuple[str, ...]) -> dict[str, cst.BaseExpression] | None:
    """A call's arguments by name, positional ones included; None where any
    is unpacked or unknown."""
    fields: dict[str, cst.BaseExpression] = {}
    for index, arg in enumerate(call.args):
        if arg.star:
            return None
        if arg.keyword is None:
            if index >= len(names):
                return None
            fields[names[index]] = arg.value
        elif arg.keyword.value in names:
            fields[arg.keyword.value] = arg.value
        else:
            return None
    return fields


def _commas(args: list[cst.Arg], original: list[cst.Arg]) -> list[cst.Arg]:
    """Each argument but the last followed by the call's own separator, and
    the last by whatever followed the original last, so the call keeps its
    layout, one line or many."""
    first = original[0].comma if len(original) > 1 else None
    separator = (
        first
        if isinstance(first, cst.Comma)
        else cst.Comma(whitespace_after=cst.SimpleWhitespace(" "))
    )
    last = original[-1].comma
    return [
        arg.with_changes(comma=separator if index < len(args) - 1 else last)
        for index, arg in enumerate(args)
    ]


class _Access(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self, imports: Imports) -> None:
        super().__init__()
        self.imports = imports
        self.applied: list[str] = []

    def _needs_parentheses(self, original: cst.CSTNode) -> bool:
        """Whether a comparison put where `original` was would bind wrongly."""
        parent = self.get_metadata(ParentNodeProvider, original, None)
        if isinstance(parent, cst.UnaryOperation):
            return not isinstance(parent.operator, cst.Not)
        return isinstance(
            parent,
            (
                cst.Comparison,
                cst.ComparisonTarget,
                cst.BinaryOperation,
                cst.Attribute,
                cst.Subscript,
                cst.Await,
                cst.Call,
            ),
        )

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        for replace in (self._any, self._union, self._caller):
            replaced = replace(original_node, updated_node)
            if replaced is not None:
                return replaced
        return updated_node

    def leave_SetComp(
        self, original_node: cst.SetComp, updated_node: cst.SetComp
    ) -> cst.BaseExpression:
        found = _gathered(updated_node.elt, updated_node.for_in)
        if found is None:
            return updated_node
        self.applied.append("access-union")
        return cst.Call(
            cst.Name("set"),
            [cst.Arg(_attribute(*found))],
            lpar=updated_node.lpar,
            rpar=updated_node.rpar,
        )

    def _any(self, original: cst.Call, updated: cst.Call) -> cst.BaseExpression | None:
        """`any(a in held.read for held in X.access)` is `a in X.read`."""
        if not (
            isinstance(updated.func, cst.Name)
            and updated.func.value == "any"
            and len(updated.args) == 1
            and updated.args[0].keyword is None
            and not updated.args[0].star
            and isinstance(updated.args[0].value, cst.GeneratorExp)
        ):
            return None
        generator = updated.args[0].value
        if generator.for_in.inner_for_in is not None:
            return None
        over = _over_access(generator.for_in)
        if over is None:
            return None
        held, receiver = over
        element = generator.elt
        whole = _held(element, held)
        if whole:
            self.applied.append("access-any")
            return cst.Call(
                cst.Name("bool"),
                [cst.Arg(_attribute(receiver, whole))],
                lpar=updated.lpar,
                rpar=updated.rpar,
            )
        if not (isinstance(element, cst.Comparison) and len(element.comparisons) == 1):
            return None
        target = element.comparisons[0]
        attribute = _held(target.comparator, held)
        if (
            not attribute
            or not isinstance(target.operator, cst.In)
            or element.lpar
            or _mentions(element.left, held)
        ):
            return None
        self.applied.append("access-any")
        compared = element.with_changes(
            comparisons=[target.with_changes(comparator=_attribute(receiver, attribute))]
        )
        if updated.lpar:
            return compared.with_changes(lpar=updated.lpar, rpar=updated.rpar)
        if self._needs_parentheses(original):
            return compared.with_changes(lpar=[cst.LeftParen()], rpar=[cst.RightParen()])
        return compared

    def _union(self, original: cst.Call, updated: cst.Call) -> cst.BaseExpression | None:
        """Every account gathered from the tags into one set is that set."""
        func = updated.func
        args = updated.args
        # set(a for held in X.access for a in held.read), and frozenset(...)
        if (
            isinstance(func, cst.Name)
            and func.value in ("set", "frozenset")
            and len(args) == 1
            and args[0].keyword is None
            and not args[0].star
            and isinstance(args[0].value, cst.GeneratorExp)
        ):
            found = _gathered(args[0].value.elt, args[0].value.for_in)
            if found:
                return self._as(func.value, *found, updated)
        # frozenset().union(*(held.read for held in X.access)), and set()'s
        if (
            isinstance(func, cst.Attribute)
            and func.attr.value == "union"
            and isinstance(func.value, cst.Call)
            and isinstance(func.value.func, cst.Name)
            and func.value.func.value in ("set", "frozenset")
            and not func.value.args
            and len(args) == 1
            and args[0].star == "*"
            and isinstance(args[0].value, cst.GeneratorExp)
            and args[0].value.for_in.inner_for_in is None
        ):
            over = _over_access(args[0].value.for_in)
            attribute = _held(args[0].value.elt, over[0]) if over else None
            if over and attribute:
                return self._as(func.value.func.value, over[1], attribute, updated)
        return None

    def _as(
        self, kind: str, receiver: cst.BaseExpression, attribute: str, updated: cst.Call
    ) -> cst.BaseExpression:
        self.applied.append("access-union")
        # Caller's sets are frozensets already; a set is asked for by name.
        whole: cst.BaseExpression = _attribute(receiver, attribute)
        if kind == "set":
            whole = cst.Call(cst.Name("set"), [cst.Arg(whole)])
        return whole.with_changes(lpar=updated.lpar, rpar=updated.rpar)

    def _caller(self, original: cst.Call, updated: cst.Call) -> cst.BaseExpression | None:
        """`Caller(..., access=(TagAccess(...), ...))` is `Caller(..., read=, write=)`."""
        if not is_sdk(updated.func, "Caller", self.imports):
            return None
        args = list(updated.args)
        if any(arg.star for arg in args):
            return None
        positional = [arg for arg in args if arg.keyword is None]
        index = next(
            (i for i, arg in enumerate(args) if arg.keyword and arg.keyword.value == "access"),
            None,
        )
        # 0.5.0's order: subject, display_name, access, header, deployment_admin.
        by_position = index is None and 3 <= len(positional) <= 5
        if by_position:
            index = 2
        if index is None:
            return None
        value = args[index].value
        if not isinstance(value, (cst.Tuple, cst.List)):
            return None
        reads: list[cst.BaseExpression] = []
        writes: list[cst.BaseExpression] = []
        for element in value.elements:
            if not isinstance(element, cst.Element):
                return None
            held = element.value
            if not (
                isinstance(held, cst.Call) and is_sdk(held.func, "TagAccess", self.imports)
            ):
                return None
            fields = _fields(held, ("tag", "read", "write"))
            if fields is None:
                return None
            if "read" in fields:
                reads.append(fields["read"])
            if "write" in fields:
                writes.append(fields["write"])
        replacement = [
            cst.Arg(value=_union_of(parts), keyword=cst.Name(name), equal=_EQUAL)
            for name, parts in (("read", reads), ("write", writes))
            if parts
        ]
        if by_position:
            named = [
                arg.with_changes(keyword=cst.Name(name), equal=_EQUAL)
                for name, arg in zip(
                    ("header", "deployment_admin"), args[3 : len(positional)], strict=False
                )
            ]
            rearranged = args[:2] + named + replacement + args[len(positional) :]
        else:
            rearranged = args[:index] + replacement + args[index + 1 :]
        self.applied.append("caller-read-write")
        return updated.with_changes(args=_commas(rearranged, args))


# ── What is left ─────────────────────────────────────────────────────────


class _Callers(cst.CSTVisitor):
    """Names that hold a Caller: assigned one, or a parameter typed as one."""

    def __init__(self, imports: Imports) -> None:
        self.imports = imports
        self.names: set[str] = set()

    def _is_caller(self, node: cst.BaseExpression) -> bool:
        if isinstance(node, cst.BinaryOperation):  # Caller | None
            return self._is_caller(node.left) or self._is_caller(node.right)
        if isinstance(node, cst.SimpleString):  # "meridian.Caller"
            return node.evaluated_value in ("Caller", "meridian.Caller")
        return is_sdk(node, "Caller", self.imports)

    def visit_Param(self, node: cst.Param) -> None:
        if node.annotation is not None and self._is_caller(node.annotation.annotation):
            self.names.add(node.name.value)

    def visit_Assign(self, node: cst.Assign) -> None:
        value = node.value
        if not isinstance(value, cst.Call):
            return
        func = value.func
        made = self._is_caller(func) or (
            isinstance(func, cst.Attribute)
            and func.attr.value == "from_header"
            and self._is_caller(func.value)
        )
        if made:
            for target in node.targets:
                if isinstance(target.target, cst.Name):
                    self.names.add(target.target.value)


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider, ParentNodeProvider)

    def __init__(self, imports: Imports, callers: set[str]) -> None:
        super().__init__()
        self.imports = imports
        self.callers = callers
        self.found: list[tuple[str, int]] = []

    def _at(self, rule: str, node: cst.CSTNode) -> None:
        self.found.append((rule, self.get_metadata(PositionProvider, node).start.line))

    def _is_caller(self, node: cst.BaseExpression) -> bool:
        name = dotted(node)
        return name is not None and (
            name in self.callers or "caller" in name.rsplit(".", 1)[-1].lower()
        )

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        return False  # an import still there is for a use, which is reported

    def visit_Attribute(self, node: cst.Attribute) -> None:
        parent = self.get_metadata(ParentNodeProvider, node, None)
        attr = node.attr.value
        if attr == "access":
            if isinstance(parent, cst.Call) and parent.func is node:
                return  # Plugin.access(), the plugin's own grants, is not this
            iterated = isinstance(parent, (cst.For, cst.CompFor)) and parent.iter is node
            if iterated or self._is_caller(node.value):
                self._at("access-tag-by-tag", node)
        elif attr == "tags":
            base = dotted(node.value)
            if base is not None and base.rsplit(".", 1)[-1] == "identity":
                self._at("identity-tags", node)
        elif attr == "TagAccess" and is_sdk(node, "TagAccess", self.imports):
            self._at("tag-access", node)

    def visit_Name(self, node: cst.Name) -> None:
        if self.imports.names.get(node.value) == "TagAccess":
            parent = self.get_metadata(ParentNodeProvider, node, None)
            if not (isinstance(parent, cst.Attribute) and parent.attr is node):
                self._at("tag-access", node)

    def visit_Call(self, node: cst.Call) -> None:
        if is_sdk(node.func, "Caller", self.imports) and any(
            arg.keyword is not None and arg.keyword.value == "access" for arg in node.args
        ):
            self._at("tag-access", node)


def _python_left(path: str, text: str) -> list[Finding]:
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not imports.modules and not imports.names:
        return []
    callers = _Callers(imports)
    module.visit(callers)
    left = _Left(imports, callers.names)
    MetadataWrapper(module).visit(left)
    seen = sorted(set(left.found), key=lambda found: (found[1], found[0]))
    return [Finding(rule, path, line, line_of(text, line)) for rule, line in seen]
