"""open-meridian 0.35.5 to 0.36.0: contract 30.

Ruling 1032: a dataset's catalogue entry declares no licence. What a plugin
declared as `licence_default=DatasetLicence(...)` becomes
`terms_and_pricing="..."`, the same terms in words, each part as it was given
(`licence-default-described`), and `DatasetLicence` and `DataEligibility`,
gone from the SDK, leave a `from meridian import ...` where nothing else in
the file names them. A licence the rule cannot read word for word -- held in
a name, an argument that is not a literal -- is left by hand, and so is any
other naming of the two or of `.licence_default` (a test reading the
declaration's licence): `licence-default-left`.

A Dockerfile's base pinned by digest at an older release moves to 0.36.0 with
its digest dropped, as 0.34.0's did (this runs with no network).

Left by hand besides: the suites contract 30 grew (`suite-cases-v30`), an
SDK DerivedSeries or CorporateActionAnnounced given the wire's MeasureRef as
its rule (`measure-ref-sdk-form`), and core's images pinned below contract
30 (`core-images`). migration.toml, beside this, records the rules.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, cast

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten, core_pins, version
from .._cst import dotted, is_test, line_of, literal

TARGET = "0.36.0"
IMAGE = "ghcr.io/open-meridian/plugin-python"
_BASE = re.compile(
    rf"(?P<head>{re.escape(IMAGE)}:)(?P<tag>[0-9][0-9.]*)(?P<digest>@sha256:[0-9a-f]{{64}})"
)
#: The names ruling 1032 retired from the SDK.
RETIRED = ("DatasetLicence", "DataEligibility")
DESCRIBED = "licence-default-described"
LEFT = "licence-default-left"
#: The most a dataset's terms_and_pricing holds (the data dictionary's bound).
MOST = 2000

#: The roles whose suites contract 30 adds a case to.
_ROLES = ("reporting", "portfolio", "compliance", "signal", "ems", "oms", "operations",
          "servicing")  # fmt: skip
_RUN = re.compile(rf"""\brun(?:_async)?\(\s*["'](?P<role>{"|".join(_ROLES)})["']""")
#: The SDK's retired names, not the wire's DatasetLicence (`ops.DatasetLicence`,
#: a deployment admin's licence, which stays), and the field.
_NAMED = re.compile(
    rf"(?<!ops\.)(?<!_pb2\.)\b(?:{'|'.join(RETIRED)})\b|\.licence_default\b"
    r"|\blicence_default\s*="
)

# ── A licence, in words ───────────────────────────────────────────────────

#: Each word a licence's enumerated answer was given as, as a person reads it.
_WORDS = {
    "not_restricted": "not restricted",
    "internal_only": "internal only",
    "redistribution_needs_licence": "redistribution needs a licence",
    "not_allowed": "not allowed",
    "licence_required": "a licence required",
    "allowed_with_attribution": "allowed with attribution",
    "public_domain": "public domain",
    "copyright_citation_required": "citation required",
    "copyright_preapproval_required": "pre-approval required",
}


class _NotLiteral(Exception):
    """An argument the rule cannot read as written: left by hand."""


def _value(node: cst.BaseExpression) -> Any:
    """A literal argument's value: a string, a whole or decimal number, True,
    False or None, a list or tuple of them, a `Decimal("...")`, or a
    `DataEligibility(...)` of them."""
    text = literal(node)
    if text is not None and "\0" not in text:
        return text
    if isinstance(node, cst.Name) and node.value in ("True", "False", "None"):
        return {"True": True, "False": False, "None": None}[node.value]
    if isinstance(node, cst.Integer | cst.Float):
        return node.value.replace("_", "")
    if isinstance(node, cst.List | cst.Tuple):
        return [_value(element.value) for element in node.elements]
    if isinstance(node, cst.Call):
        name = (dotted(node.func) or "").rsplit(".", 1)[-1]
        if name == "Decimal" and len(node.args) == 1:
            return str(_value(node.args[0].value))
        if name == "DataEligibility":
            given = _keywords(node)
            if set(given) - _ELIGIBILITY_ARGS:
                raise _NotLiteral("an eligibility argument the rule does not word")
            return given
    raise _NotLiteral(type(node).__name__)


#: Each argument `DatasetLicence` and `DataEligibility` took, which `described`
#: words; a licence naming any other is left by hand, never part-said.
_LICENCE_ARGS = frozenset(
    {
        "kept", "retention_days", "derived_use", "derived_use_terms", "display",
        "default_fields", "personal_use", "redistribution", "attribution_required",
        "attribution_text", "copyright_class", "no_more_restrictive_terms",
        "not_affiliated_notice", "eligibility", "underlying_source",
    }
)  # fmt: skip
_ELIGIBILITY_ARGS = frozenset(
    {"uses", "buyer_revenue_below", "buyer_revenue_at_least", "buyer_revenue_currency_code"}
)


def _keywords(call: cst.Call) -> dict[str, Any]:
    if any(arg.keyword is None for arg in call.args):
        raise _NotLiteral("a positional or starred argument")
    return {arg.keyword.value: _value(arg.value) for arg in call.args if arg.keyword}


def _word(value: Any) -> str:
    said = str(value).strip().lower()
    for prefix in ("derived_use_", "redistribution_", "copyright_class_"):
        if said not in _WORDS:
            said = said.removeprefix(prefix)
    return _WORDS.get(said, said.replace("_", " "))


def _eligibility(given: dict[str, Any]) -> str:
    parts = []
    uses = [str(u).lower().removeprefix("data_use_") for u in given.get("uses") or ()]
    if uses:
        parts.append(" and ".join(uses) + " use")
    currency = str(given.get("buyer_revenue_currency_code") or "")
    for key, said in (("buyer_revenue_below", "below"), ("buyer_revenue_at_least", "at least")):
        if given.get(key) not in (None, ""):
            parts.append(f"a buyer's revenue {said} {given[key]} {currency}".rstrip())
    return "eligible: " + ", ".join(parts) if parts else ""


def described(given: dict[str, Any]) -> str:
    """A `DatasetLicence(...)`'s arguments as the vendor's terms in words,
    each part only where it was given: what `licence-default-described`
    writes as a dataset's `terms_and_pricing`."""
    parts: list[str] = []
    if "kept" in given:
        parts.append("kept by the lake" if given["kept"] else "served, not kept")
    if given.get("retention_days") not in (None, 0, "0"):
        parts.append(f"kept {given['retention_days']} days at most")
    terms = given.get("derived_use_terms")
    if terms:
        parts.append(f"derived use {_word(terms)}")
    elif "derived_use" in given and given["derived_use"] is not None:
        parts.append("derived use not restricted" if given["derived_use"] else
                     "derived use internal only")  # fmt: skip
    if "display" in given:
        parts.append("display allowed" if given["display"] else "no display")
    fields = [str(f) for f in given.get("default_fields") or ()]
    if fields:
        parts.append("fields readable by default: " + ", ".join(fields))
    if given.get("personal_use"):
        parts.append("one person's terms")
    if given.get("redistribution"):
        parts.append(f"redistribution {_word(given['redistribution'])}")
    if given.get("attribution_required") or given.get("attribution_text"):
        text = str(given.get("attribution_text") or "").strip()
        parts.append(f'attribution required: "{text}"' if text else "attribution required")
    if given.get("copyright_class"):
        parts.append(f"copyright: {_word(given['copyright_class'])}")
    if given.get("no_more_restrictive_terms"):
        parts.append("no more restrictive terms may be added downstream")
    if given.get("eligibility"):
        eligible = _eligibility(given["eligibility"])
        if eligible:
            parts.append(eligible)
    if given.get("underlying_source"):
        parts.append(f"underlying source: {str(given['underlying_source']).strip()}")
    if given.get("not_affiliated_notice"):
        parts.append(str(given["not_affiliated_notice"]).strip())
    if not parts:
        return ""
    said = "; ".join(parts)
    return said[0].upper() + said[1:] + ("" if said.endswith(".") else ".")


def _string(text: str) -> cst.SimpleString:
    """`text` as a Python string literal, double-quoted."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return cst.SimpleString(f'"{escaped}"')


def _licence_call(value: cst.BaseExpression) -> str | None:
    """A literal `DatasetLicence(...)` call's terms in words; None for any
    other expression, or a licence with an argument that is not a literal."""
    if not isinstance(value, cst.Call):
        return None
    if (dotted(value.func) or "").rsplit(".", 1)[-1] != "DatasetLicence":
        return None
    try:
        given = _keywords(value)
        if set(given) - _LICENCE_ARGS:
            return None  # an argument it does not word: never part-said
        text = described(given)
    except _NotLiteral:
        return None
    # Past the field's bound it is left for a person to shorten, never cut.
    return text if len(text) <= MOST else None


class _Held(cst.CSTVisitor):
    """The module's own names bound once, at its top level, to a literal
    `DatasetLicence(...)` -- a licence shared by its datasets -- each with its
    terms in words."""

    def __init__(self) -> None:
        super().__init__()
        self.terms: dict[str, str] = {}
        self.bound: dict[str, int] = {}

    def visit_Module(self, node: cst.Module) -> None:
        for statement in node.body:
            if not isinstance(statement, cst.SimpleStatementLine):
                continue
            for small in statement.body:
                targets = (
                    [t.target for t in small.targets] if isinstance(small, cst.Assign) else []
                )
                for target in targets:
                    if isinstance(target, cst.Name):
                        self.bound[target.value] = self.bound.get(target.value, 0) + 1
                        text = _licence_call(cast(cst.Assign, small).value)
                        if text is not None:
                            self.terms[target.value] = text

    def held(self, module: cst.Module) -> dict[str, str]:
        """Those bound once and named nowhere but as a `licence_default`: a
        name read otherwise (`LIC.retention_days`) is left by hand, since
        it then holds words."""
        uses = _Uses(set(self.terms))
        module.visit(uses)
        return {
            name: text
            for name, text in self.terms.items()
            if self.bound[name] == 1 and uses.other.get(name, 0) == 0
        }


class _Uses(cst.CSTVisitor):
    """How often each name is read other than as `licence_default=NAME` or
    as the target it is bound to."""

    def __init__(self, names: set[str]) -> None:
        super().__init__()
        self.names = names
        self.other: dict[str, int] = {}

    def visit_Arg(self, node: cst.Arg) -> bool:
        keyword = node.keyword.value if node.keyword is not None else ""
        return not (
            keyword == "licence_default"
            and isinstance(node.value, cst.Name)
            and node.value.value in self.names
        )

    def visit_AssignTarget(self, node: cst.AssignTarget) -> bool:
        return False

    def visit_Name(self, node: cst.Name) -> None:
        if node.value in self.names:
            self.other[node.value] = self.other.get(node.value, 0) + 1


class _Licences(cst.CSTTransformer):
    """Each `licence_default=DatasetLicence(...)` of a dataset's declaration,
    every argument a literal, rewritten to `terms_and_pricing="..."`; one
    naming a module-level licence bound once to a literal `DatasetLicence(...)`
    rewritten to name it, that binding then holding the words; any other
    left as it is, for `left` to name."""

    def __init__(self, held: dict[str, str]) -> None:
        super().__init__()
        self.held = held
        self.rewrote = 0

    def leave_Arg(self, original_node: cst.Arg, updated_node: cst.Arg) -> cst.Arg:
        if updated_node.keyword is None or updated_node.keyword.value != "licence_default":
            return updated_node
        value = updated_node.value
        terms = cst.Name("terms_and_pricing")
        if isinstance(value, cst.Name) and value.value == "None":
            self.rewrote += 1
            return updated_node.with_changes(keyword=terms, value=_string(""))
        if isinstance(value, cst.Name) and value.value in self.held:
            self.rewrote += 1
            return updated_node.with_changes(keyword=terms)
        text = _licence_call(value)
        if text is None:
            return updated_node
        self.rewrote += 1
        return updated_node.with_changes(keyword=terms, value=_string(text))

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        (target,) = updated_node.targets[:1] or (None,)
        if target is None or len(updated_node.targets) != 1:
            return updated_node
        name = target.target
        if isinstance(name, cst.Name) and name.value in self.held:
            text = _licence_call(updated_node.value)
            if text is not None:
                return updated_node.with_changes(value=_string(self.held[name.value]))
        return updated_node


class _Imports(cst.CSTTransformer):
    """DatasetLicence and DataEligibility dropped from a `from meridian import
    ...` where the file names them nowhere else."""

    def __init__(self, unused: frozenset[str]) -> None:
        super().__init__()
        self.unused = unused

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        if (
            updated_node.relative
            or updated_node.module is None
            or dotted(updated_node.module) not in ("meridian", "meridian.declaration")
            or isinstance(updated_node.names, cst.ImportStar)
        ):
            return updated_node
        kept = [
            alias
            for alias in updated_node.names
            if alias.asname is not None or dotted(alias.name) not in self.unused
        ]
        if len(kept) == len(updated_node.names):
            return updated_node
        if not kept:
            return cst.RemoveFromParent()
        last = updated_node.names[-1].comma
        kept[-1] = kept[-1].with_changes(comma=last)
        return updated_node.with_changes(names=kept)


def _named_elsewhere(module: cst.Module, name: str) -> bool:
    """Whether `name` is read anywhere but in an import."""
    found = False

    class _Find(cst.CSTVisitor):
        def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
            return False

        def visit_Name(self, node: cst.Name) -> None:
            nonlocal found
            if node.value == name:
                found = True

    module.visit(_Find())
    return found


def _licences(path: str, text: str) -> Rewritten:
    module = cst.parse_module(text)
    found = _Held()
    module.visit(found)
    licences = _Licences(found.held(module))
    rewritten = module.visit(licences)
    unused = frozenset(name for name in RETIRED if not _named_elsewhere(rewritten, name))
    if licences.rewrote and unused:
        rewritten = rewritten.visit(_Imports(unused))
    # What it could not read is found by `left`, in the file as it now is.
    return Rewritten(rewritten.code, (DESCRIBED,) * licences.rewrote)


def _dockerfile(path: str, text: str) -> Rewritten:
    rules: list[str] = []
    findings: list[Finding] = []
    out: list[str] = []
    for n, line in enumerate(text.splitlines(keepends=True), 1):
        found = _BASE.search(line)
        if found and version(found.group("tag")) < version(TARGET):  # never a later pin
            line = line[: found.start()] + found.group("head") + TARGET + line[found.end() :]
            rules.append("base-digest-dropped")
            findings.append(Finding("base-digest", path, n, line.strip()))
        out.append(line)
    return Rewritten("".join(out), tuple(rules), tuple(findings))


def rewrite(path: str, text: str) -> Rewritten:
    if path == "Dockerfile":
        return _dockerfile(path, text)
    if path.endswith(".py") and "licence_default" in text:
        return _licences(path, text)
    return Rewritten(text)


# ── What is left by hand ──────────────────────────────────────────────────


def _at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


class _WireRules(cst.CSTVisitor):
    """An SDK DerivedSeries or CorporateActionAnnounced given the wire's
    MeasureRef as its `rule`."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, wire: Sequence[str]) -> None:
        super().__init__()
        self.wire = tuple(wire)
        self.lines: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        name = dotted(node.func) or ""
        head, _, last = name.rpartition(".")
        if last not in ("DerivedSeries", "CorporateActionAnnounced") or head in self.wire:
            return
        for arg in node.args:
            if arg.keyword is None or arg.keyword.value != "rule":
                continue
            if not isinstance(arg.value, cst.Call):
                continue
            ref = dotted(arg.value.func) or ""
            base, _, called = ref.rpartition(".")
            if called == "MeasureRef" and base in self.wire:
                self.lines.append(self.get_metadata(PositionProvider, node).start.line)


#: The names a plugin binds the wire's bindings to, as written.
_WIRE = re.compile(
    r"^\s*from\s+meridian\.plugin\.v1\s+import\s+operations_pb2(?:\s+as\s+(?P<alias>\w+))?",
    re.MULTILINE,
)


def left(path: str, text: str) -> list[Finding]:
    if path == "Makefile":
        return [
            Finding("core-images", path, line, line_of(text, line))
            for line in core_pins(path, text, 30)
        ]
    if not path.endswith(".py"):
        return []
    found: list[Finding] = []
    if is_test(path):
        for match in _RUN.finditer(text):
            line = _at(text, match.start())
            found.append(Finding("suite-cases-v30", path, line, line_of(text, line)))
    for line in sorted({_at(text, match.start()) for match in _NAMED.finditer(text)}):
        found.append(Finding(LEFT, path, line, line_of(text, line)))
    if "MeasureRef" not in text or "rule" not in text:
        return found
    wire = ["operations_pb2", "meridian.plugin.v1.operations_pb2"]
    wire += [m.group("alias") for m in _WIRE.finditer(text) if m.group("alias")]
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError:
        return found
    rules = _WireRules(wire)
    MetadataWrapper(module).visit(rules)
    for line in rules.lines:
        found.append(Finding("measure-ref-sdk-form", path, line, line_of(text, line)))
    return found
