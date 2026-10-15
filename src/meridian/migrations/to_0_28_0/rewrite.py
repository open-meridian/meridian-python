"""open-meridian 0.27.0 to 0.28.0: the SDK declares contract v24, and every
instrument is named by the platform master's ID.

The one-ID spec's requirement 20, three rewrites, each only in a file that
uses the SDK:

- a record's ID tested for the prefix `LCL-` -- `<record>.instrument_id
  .startswith("LCL-")` -- reads the record's mark, `<record>.provisional`
  (InstrumentRecord and ResolveIdentifierResult both carry it);
- the platform's ID read from a record's `open_meridian` identifier --
  `next(i.value for i in <record>.identifiers if i.scheme == "open_meridian")`,
  with or without a default -- reads the record's own `instrument_id`, or
  the default where the record is provisional, since the platform's record
  is keyed by its `INS-` ID;
- in a test, the suite runner's `LCL-suite-n` is `INS-suite-n`, what its
  resolve answers from 0.28.0 (a provisional record's is still
  `LCL-suite-n`, from a `Recorder(provisional=True)`).

A prefix test on anything else -- an ID held alone, a slice compared, `"LCL-"
in` it -- and any other `open_meridian` left in the file are left by hand: the
record to read is not at hand. migration.toml, beside this, records the rules.
"""

from __future__ import annotations

import re

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import imports_of, is_test, line_of, literal

LCL = "LCL-"
OPEN_MERIDIAN = "open_meridian"
#: The suite runner's resolve answer before 0.28.0.
_SUITE_ID = re.compile(r"LCL-suite-")


def _uses_sdk(module: cst.Module) -> bool:
    imports = imports_of(module)
    return bool(imports.modules or imports.names)


def rewrite(path: str, text: str) -> Rewritten:
    if not path.endswith(".py"):
        return Rewritten(text)
    module = cst.parse_module(text)
    if not _uses_sdk(module):
        return Rewritten(text)
    rewriting = _OneId(is_test(path))
    rewritten = module.visit(rewriting)
    return Rewritten(rewritten.code, tuple(rewriting.applied))


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    module = cst.parse_module(text)
    if not _uses_sdk(module):
        return []
    found = _Left()
    MetadataWrapper(module).visit(found)
    return [
        Finding(rule, path, line, line_of(text, line))
        for rule, line in sorted(set(found.found))
    ]


def _is_lcl(node: cst.BaseExpression) -> bool:
    """The literal "LCL-", alone or in a tuple of prefixes."""
    if literal(node) == LCL:
        return True
    if isinstance(node, cst.Tuple):
        return any(literal(element.value) == LCL for element in node.elements)
    return False


def _prefix_test(node: cst.Call) -> cst.BaseExpression | None:
    """The receiver of `<x>.startswith("LCL-")`, or None."""
    if (
        isinstance(node.func, cst.Attribute)
        and node.func.attr.value == "startswith"
        and len(node.args) == 1
        and node.args[0].keyword is None
        and literal(node.args[0].value) == LCL
    ):
        return node.func.value
    return None


def _scheme_test(test: cst.BaseExpression, name: str) -> bool:
    """`<name>.scheme == "open_meridian"`, either way round."""
    if not isinstance(test, cst.Comparison) or len(test.comparisons) != 1:
        return False
    target = test.comparisons[0]
    if not isinstance(target.operator, cst.Equal):
        return False

    def scheme_of(node: cst.BaseExpression) -> bool:
        return (
            isinstance(node, cst.Attribute)
            and node.attr.value == "scheme"
            and isinstance(node.value, cst.Name)
            and node.value.value == name
        )

    left_side, right_side = test.left, target.comparator
    return (scheme_of(left_side) and literal(right_side) == OPEN_MERIDIAN) or (
        scheme_of(right_side) and literal(left_side) == OPEN_MERIDIAN
    )


def _open_meridian_read(node: cst.BaseExpression) -> cst.BaseExpression | None:
    """The record of `<x>.value for <x> in <record>.identifiers if <x>.scheme
    == "open_meridian"`, or None."""
    if not isinstance(node, cst.GeneratorExp) or len(node.for_in.ifs) != 1:
        return None
    for_in = node.for_in
    if for_in.inner_for_in is not None or for_in.asynchronous is not None:
        return None
    if not isinstance(for_in.target, cst.Name):
        return None
    name = for_in.target.value
    element = node.elt
    if not (
        isinstance(element, cst.Attribute)
        and element.attr.value == "value"
        and isinstance(element.value, cst.Name)
        and element.value.value == name
    ):
        return None
    source = for_in.iter
    if not (isinstance(source, cst.Attribute) and source.attr.value == "identifiers"):
        return None
    if not _scheme_test(for_in.ifs[0].test, name):
        return None
    return source.value


class _OneId(cst.CSTTransformer):
    def __init__(self, test: bool) -> None:
        super().__init__()
        self.test = test
        self.applied: list[str] = []

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        receiver = _prefix_test(updated_node)
        if (
            receiver is not None
            and isinstance(receiver, cst.Attribute)
            and receiver.attr.value == "instrument_id"
        ):
            self.applied.append("lcl-prefix-provisional")
            return cst.Attribute(value=receiver.value, attr=cst.Name("provisional"))
        if (
            isinstance(updated_node.func, cst.Name)
            and updated_node.func.value == "next"
            and 1 <= len(updated_node.args) <= 2
            and all(arg.keyword is None for arg in updated_node.args)
        ):
            record = _open_meridian_read(updated_node.args[0].value)
            if record is not None:
                self.applied.append("open-meridian-instrument-id")
                instrument_id = cst.Attribute(value=record, attr=cst.Name("instrument_id"))
                if len(updated_node.args) == 1:
                    return instrument_id
                default = updated_node.args[1].value
                return cst.IfExp(
                    test=cst.Attribute(value=record, attr=cst.Name("provisional")),
                    body=default,
                    orelse=instrument_id,
                    lpar=[cst.LeftParen()],
                    rpar=[cst.RightParen()],
                )
        return updated_node

    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.SimpleString:
        if not self.test:
            return updated_node
        value = updated_node.evaluated_value
        if isinstance(value, str) and re.fullmatch(r"LCL-suite-\d+", value):
            self.applied.append("suite-fixture-ins")
            return updated_node.with_changes(
                value=_SUITE_ID.sub("INS-suite-", updated_node.value, count=1)
            )
        return updated_node

    def leave_FormattedStringText(
        self, original_node: cst.FormattedStringText, updated_node: cst.FormattedStringText
    ) -> cst.FormattedStringText:
        if self.test and updated_node.value.endswith("LCL-suite-"):
            self.applied.append("suite-fixture-ins")
            return updated_node.with_changes(
                value=updated_node.value[: -len("LCL-suite-")] + "INS-suite-"
            )
        return updated_node


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.found: list[tuple[str, int]] = []

    def _at(self, rule: str, node: cst.CSTNode) -> None:
        self.found.append((rule, self.get_metadata(PositionProvider, node).start.line))

    def visit_Call(self, node: cst.Call) -> None:
        if (
            isinstance(node.func, cst.Attribute)
            and node.func.attr.value == "startswith"
            and node.args
            and _is_lcl(node.args[0].value)
        ):
            self._at("lcl-prefix-tested", node)

    def visit_Comparison(self, node: cst.Comparison) -> None:
        # `x[:4] == "LCL-"`, `"LCL-" in x`, either way round.
        sides = [node.left, *(target.comparator for target in node.comparisons)]
        if any(literal(side) == LCL for side in sides):
            self._at("lcl-prefix-tested", node)

    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        if node.evaluated_value == OPEN_MERIDIAN:
            self._at("open-meridian-read", node)
