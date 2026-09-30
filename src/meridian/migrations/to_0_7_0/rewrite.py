"""open-meridian 0.6.1 to 0.7.0: the unlinked refusal is `meridian.NotLinked`.

A row refused because its external account is not linked raises NotLinked,
chosen by the code the sidecar sends beside the refusal, never by its words.
A plugin that told the refusal apart by its words ("is not linked" in
str(err)) keeps working today and breaks the first time they are reworded,
so each such test of a meridian error becomes an isinstance, and a stand-in
refusal in a test becomes a NotLinked. Words matched anywhere else are left by
hand: this cannot tell what they were matched against. migration.toml, beside
this, records both.

Nothing else a plugin already calls changed between the two.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import Imports, add_import, dotted, imports_of, is_sdk, is_test, line_of, literal

#: What the sidecar's refusal said, and what a plugin matched it by.
PHRASE = "not linked"

#: The meridian errors the unlinked refusal can be caught as.
ERRORS = ("CallFailed", "MeridianError")


def _says_unlinked(node: cst.BaseExpression) -> bool:
    text = literal(node)
    return text is not None and PHRASE in text.lower()


def rewrite(path: str, text: str) -> Rewritten:
    if not path.endswith(".py"):
        return Rewritten(text)
    module = cst.parse_module(text)
    imports = imports_of(module)
    if not imports.modules and not imports.names:
        return Rewritten(text)  # it does not use the SDK
    errors = _Errors(imports)
    module.visit(errors)
    not_linked = _NotLinked(imports, errors.names)
    rewritten = module.visit(not_linked)
    if not_linked.import_needed:
        rewritten = add_import(rewritten, "meridian", "NotLinked")
    return Rewritten(rewritten.code, tuple(not_linked.applied))


def left(path: str, text: str) -> list[Finding]:
    # A test asserting a page says "Not linked" is reading output, not a
    # refusal; only the plugin's own code is looked at.
    if not path.endswith(".py") or is_test(path):
        return []
    module = cst.parse_module(text)
    matched = _Matched()
    MetadataWrapper(module).visit(matched)
    return [
        Finding("not-linked-by-text", path, line, line_of(text, line))
        for line in sorted(set(matched.lines))
    ]


# ── Which names hold a meridian error ────────────────────────────────────


def _is_error(node: cst.BaseExpression | None, imports: Imports) -> bool:
    if node is None:
        return False
    if isinstance(node, cst.Tuple):
        return any(_is_error(element.value, imports) for element in node.elements)
    if isinstance(node, cst.BinaryOperation):  # CallFailed | None
        return _is_error(node.left, imports) or _is_error(node.right, imports)
    return any(is_sdk(node, name, imports) for name in ERRORS)


class _Errors(cst.CSTVisitor):
    """Names a meridian error is caught as, typed as, or checked to be: only
    their words are read as the refusal's."""

    def __init__(self, imports: Imports) -> None:
        self.imports = imports
        self.names: set[str] = set()

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
        if (
            _is_error(node.type, self.imports)
            and node.name is not None
            and isinstance(node.name.name, cst.Name)
        ):
            self.names.add(node.name.name.value)

    def visit_Param(self, node: cst.Param) -> None:
        if node.annotation is not None and _is_error(node.annotation.annotation, self.imports):
            self.names.add(node.name.value)

    def visit_Call(self, node: cst.Call) -> None:
        if (
            isinstance(node.func, cst.Name)
            and node.func.value == "isinstance"
            and len(node.args) == 2
            and _is_error(node.args[1].value, self.imports)
        ):
            name = dotted(node.args[0].value)
            if name is not None:
                self.names.add(name)


def _words_of(node: cst.BaseExpression) -> cst.BaseExpression | None:
    """X, where `node` reads an error's words: X.detail, str(X), repr(X),
    X.args[0] or f"{X}"."""
    if isinstance(node, cst.Attribute) and node.attr.value == "detail":
        return node.value
    if (
        isinstance(node, cst.Call)
        and isinstance(node.func, cst.Name)
        and node.func.value in ("str", "repr")
        and len(node.args) == 1
        and node.args[0].keyword is None
        and not node.args[0].star
    ):
        return node.args[0].value
    if (
        isinstance(node, cst.Subscript)
        and isinstance(node.value, cst.Attribute)
        and node.value.attr.value == "args"
        and len(node.slice) == 1
        and isinstance(node.slice[0].slice, cst.Index)
        and isinstance(node.slice[0].slice.value, cst.Integer)
        and node.slice[0].slice.value.value == "0"
    ):
        return node.value.value
    if (
        isinstance(node, cst.FormattedString)
        and len(node.parts) == 1
        and isinstance(node.parts[0], cst.FormattedStringExpression)
        and node.parts[0].conversion is None
        and node.parts[0].format_spec is None
    ):
        return node.parts[0].expression
    return None


# ── The rewrite ──────────────────────────────────────────────────────────


def _flatten(
    node: cst.BaseExpression,
) -> tuple[list[cst.BaseExpression], list[cst.BaseBooleanOp]]:
    """`a and b and c`, unparenthesised, as its operands and operators."""
    if (
        isinstance(node, cst.BooleanOperation)
        and isinstance(node.operator, cst.And)
        and not node.lpar
    ):
        left, left_ops = _flatten(node.left)
        right, right_ops = _flatten(node.right)
        return left + right, [*left_ops, node.operator, *right_ops]
    return [node], []


def _exits(block: cst.BaseSuite) -> bool:
    """Whether a block always leaves: its last statement returns, raises,
    continues or breaks."""
    if not isinstance(block, cst.IndentedBlock) or not block.body:
        return False
    last = block.body[-1]
    return isinstance(last, cst.SimpleStatementLine) and isinstance(
        last.body[-1], (cst.Return, cst.Raise, cst.Continue, cst.Break)
    )


def _is_reraise(statement: cst.BaseStatement) -> bool:
    return (
        isinstance(statement, cst.SimpleStatementLine)
        and len(statement.body) == 1
        and isinstance(statement.body[0], cst.Raise)
        and statement.body[0].exc is None
    )


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


class _NotLinked(cst.CSTTransformer):
    def __init__(self, imports: Imports, errors: set[str]) -> None:
        super().__init__()
        self.imports = imports
        self.errors = errors
        self.applied: list[str] = []
        self.import_needed = False
        # The isinstance tests this wrote, by identity, so only those decide
        # what is simplified around them.
        self.written: list[cst.Call] = []

    def _not_linked(self, beside: cst.BaseExpression | None = None) -> cst.BaseExpression:
        """How this file names NotLinked: beside the module a CallFailed was
        named from, or as `meridian.NotLinked`, or imported by name."""
        if isinstance(beside, cst.Attribute):
            return beside.with_changes(attr=cst.Name("NotLinked"))
        if self.imports.package is not None:
            return cst.Attribute(
                value=cst.Name(self.imports.package), attr=cst.Name("NotLinked")
            )
        self.import_needed = True
        return cst.Name("NotLinked")

    def _is_written(self, node: cst.BaseExpression) -> bool:
        return any(node is written for written in self.written)

    def leave_Comparison(
        self, original_node: cst.Comparison, updated_node: cst.Comparison
    ) -> cst.BaseExpression:
        """`"is not linked" in str(err)` is `isinstance(err, meridian.NotLinked)`."""
        if len(updated_node.comparisons) != 1:
            return updated_node
        target = updated_node.comparisons[0]
        if not isinstance(target.operator, (cst.In, cst.NotIn)) or not _says_unlinked(
            updated_node.left
        ):
            return updated_node
        error = _words_of(target.comparator)
        if error is None or dotted(error) not in self.errors:
            return updated_node
        test = cst.Call(
            cst.Name("isinstance"),
            [
                cst.Arg(error, comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" "))),
                cst.Arg(self._not_linked()),
            ],
        )
        self.applied.append("not-linked-isinstance")
        if isinstance(target.operator, cst.NotIn):
            self.written.append(test)
            return cst.UnaryOperation(
                cst.Not(), test, lpar=updated_node.lpar, rpar=updated_node.rpar
            )
        test = test.with_changes(lpar=updated_node.lpar, rpar=updated_node.rpar)
        self.written.append(test)
        return test

    def _implied(self, node: cst.BaseExpression, error: cst.BaseExpression) -> bool:
        """`isinstance(err, CallFailed)` or `err.kind == "refused"`, which
        NotLinked implies for the same err."""
        if (
            isinstance(node, cst.Call)
            and isinstance(node.func, cst.Name)
            and node.func.value == "isinstance"
            and len(node.args) == 2
            and node.args[0].value.deep_equals(error)
            and _is_error(node.args[1].value, self.imports)
        ):
            return True
        if isinstance(node, cst.Comparison) and len(node.comparisons) == 1:
            target = node.comparisons[0]
            if not isinstance(target.operator, cst.Equal):
                return False
            sides = (node.left, target.comparator)
            for kind, refused in (sides, sides[::-1]):
                if (
                    isinstance(kind, cst.Attribute)
                    and kind.attr.value == "kind"
                    and kind.value.deep_equals(error)
                    and literal(refused) == "refused"
                ):
                    return True
        return False

    def leave_BooleanOperation(
        self, original_node: cst.BooleanOperation, updated_node: cst.BooleanOperation
    ) -> cst.BaseExpression:
        if not isinstance(updated_node.operator, cst.And):
            return updated_node
        left, left_ops = _flatten(updated_node.left)
        right, right_ops = _flatten(updated_node.right)
        operands = left + right
        operators = [*left_ops, updated_node.operator, *right_ops]
        written = [
            operand
            for operand in operands
            if isinstance(operand, cst.Call) and self._is_written(operand)
        ]
        if not written:
            return updated_node
        errors = [call.args[0].value for call in written]
        kept = [
            index
            for index, operand in enumerate(operands)
            if not any(self._implied(operand, error) for error in errors)
        ]
        if len(kept) == len(operands):
            return updated_node
        if len(kept) == 1:
            only = operands[kept[0]]
            if isinstance(only, cst.Call):
                return only  # binds tightest: its parentheses are nobody's
            return only.with_changes(lpar=updated_node.lpar, rpar=updated_node.rpar)
        joined = operands[kept[0]]
        for index in kept[1:]:
            joined = cst.BooleanOperation(
                left=joined, operator=operators[index - 1], right=operands[index]
            )
        return joined.with_changes(lpar=updated_node.lpar, rpar=updated_node.rpar)

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        """`CallFailed(topic, "refused", "... is not linked ...")` is
        `NotLinked(topic, "...")`: a test's stand-in for the refusal."""
        if not is_sdk(updated_node.func, "CallFailed", self.imports):
            return updated_node
        args = list(updated_node.args)
        if any(arg.star for arg in args):
            return updated_node
        names = ("topic", "kind", "detail")
        by_name: dict[str, int] = {}
        for index, arg in enumerate(args):
            name = names[index] if arg.keyword is None and index < 3 else None
            if arg.keyword is not None:
                name = arg.keyword.value
            if name not in names:
                return updated_node
            by_name[name] = index
        if set(by_name) != set(names):
            return updated_node
        if literal(args[by_name["kind"]].value) != "refused" or not _says_unlinked(
            args[by_name["detail"]].value
        ):
            return updated_node
        dropped = by_name["kind"]
        kept = args[:dropped] + args[dropped + 1 :]
        if dropped == len(args) - 1:
            kept[-1] = kept[-1].with_changes(comma=args[dropped].comma)
        self.applied.append("not-linked-raised")
        return updated_node.with_changes(func=self._not_linked(updated_node.func), args=kept)

    def leave_Try(self, original_node: cst.Try, updated_node: cst.Try) -> cst.Try:
        """`except CallFailed as err: if isinstance(err, NotLinked): ...
        else: raise` is `except NotLinked: ...`, in a try's last handler,
        where no later handler could have caught what it re-raised."""
        if not updated_node.handlers:
            return updated_node
        handler = updated_node.handlers[-1]
        if (
            handler.type is None
            or isinstance(handler.type, cst.Tuple)
            or not _is_error(handler.type, self.imports)
            or handler.name is None
            or not isinstance(handler.name.name, cst.Name)
            or not isinstance(handler.body, cst.IndentedBlock)
        ):
            return updated_node
        name = handler.name.name.value
        body = list(handler.body.body)
        test = body[0] if body else None
        if not isinstance(test, cst.If) or not isinstance(test.test, cst.Call):
            return updated_node
        call = test.test
        if not (
            self._is_written(call)
            and isinstance(call.args[0].value, cst.Name)
            and call.args[0].value.value == name
        ):
            return updated_node
        otherwise = test.orelse
        narrowed = (
            len(body) == 1
            and isinstance(otherwise, cst.Else)
            and isinstance(otherwise.body, cst.IndentedBlock)
            and len(otherwise.body.body) == 1
            and _is_reraise(otherwise.body.body[0])
        ) or (
            len(body) == 2 and otherwise is None and _is_reraise(body[1]) and _exits(test.body)
        )
        if not narrowed or not isinstance(test.body, cst.IndentedBlock):
            return updated_node
        block = test.body
        statements = list(block.body)
        first = statements[0]
        # A comment above the `if` now sits above what it guarded.
        if isinstance(first, (cst.SimpleStatementLine, cst.BaseCompoundStatement)):
            statements[0] = first.with_changes(
                leading_lines=[*test.leading_lines, *first.leading_lines]
            )
        header = handler.body.header
        if header.comment is None and block.header.comment is not None:
            header = block.header
        self.applied.append("not-linked-except")
        narrow = handler.with_changes(
            type=call.args[1].value,
            name=handler.name if _mentions(block, name) else None,
            body=block.with_changes(body=statements, header=header),
        )
        return updated_node.with_changes(handlers=[*updated_node.handlers[:-1], narrow])


# ── What is left ─────────────────────────────────────────────────────────

_MATCHING = frozenset({"startswith", "endswith", "find", "rfind", "index", "rindex", "count"})
_PATTERNS = frozenset({"search", "match", "fullmatch", "findall", "finditer", "sub", "split"})


class _Matched(cst.CSTVisitor):
    """The words matched: compared, searched for, or given to a pattern."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[int] = []

    def _at(self, node: cst.CSTNode) -> None:
        self.lines.append(self.get_metadata(PositionProvider, node).start.line)

    def visit_Comparison(self, node: cst.Comparison) -> None:
        sides = [node.left, *(target.comparator for target in node.comparisons)]
        if any(_says_unlinked(side) for side in sides):
            self._at(node)

    def visit_Call(self, node: cst.Call) -> None:
        func = node.func
        name = dotted(func)
        matching = isinstance(func, cst.Attribute) and func.attr.value in _MATCHING
        pattern = name is not None and name.startswith("re.") and name[3:] in _PATTERNS
        if (matching or pattern or name == "re.compile") and any(
            _says_unlinked(arg.value) for arg in node.args
        ):
            self._at(node)
