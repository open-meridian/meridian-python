"""open-meridian 0.33.5 to 0.34.0: contract v29.

Nothing a plugin calls changed shape, so no call is rewritten: the typed
operations and the SDK's dataclasses gained fields and helpers
(`meridian.roles.debt`, the fixed-income records in
`meridian.roles.lifecycle`, `meridian.analytics.debt`), and nothing was
renamed or removed. A Dockerfile's base pinned by digest at an older release
is moved to 0.34.0 with its digest dropped, since this runs with no network,
as 0.33.0's; `meridian plugin migrate` has moved the tag and the digest
before this runs, and then there is nothing to do.

Left by hand: each suite test of a role contract v29 adds the factor's cases
to (`records-a-pools-factor` for `data`; `reads-a-pools-factors` and
`hears-a-factor-recorded` for `operations`, `portfolio`, `reporting`,
`servicing` and `signal`), which a plugin maps or names not presented, with
why; a quality assessment built by hand naming no data type, which
`RecordQualityAssessments` requires from contract v29 (628); and the digest,
pinned again. migration.toml, beside this, records the rules.
"""

from __future__ import annotations

import re

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import dotted, is_test, line_of

TARGET = "0.34.0"
IMAGE = "ghcr.io/open-meridian/plugin-python"
_BASE = re.compile(
    rf"(?P<head>{re.escape(IMAGE)}:)(?P<tag>[0-9][0-9.]*)(?P<digest>@sha256:[0-9a-f]{{64}})"
)
#: Every role whose suite contract v29 adds cases to: the factor's.
_ROLES = ("data", "operations", "portfolio", "reporting", "servicing", "signal")
_RUN = re.compile(rf"""\brun(?:_async)?\(\s*["'](?P<role>{"|".join(_ROLES)})["']""")


def _dockerfile(path: str, text: str) -> Rewritten:
    rules: list[str] = []
    findings: list[Finding] = []
    out: list[str] = []
    for n, line in enumerate(text.splitlines(keepends=True), 1):
        found = _BASE.search(line)
        if found and found.group("tag") != TARGET:
            line = line[: found.start()] + found.group("head") + TARGET + line[found.end() :]
            rules.append("base-digest-dropped")
            findings.append(Finding("base-digest", path, n, line.strip()))
        out.append(line)
    return Rewritten("".join(out), tuple(rules), tuple(findings))


def rewrite(path: str, text: str) -> Rewritten:
    if path == "Dockerfile":
        return _dockerfile(path, text)
    return Rewritten(text)


def _at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


class _Assessments(cst.CSTVisitor):
    """A `QualityAssessment(...)` built naming no `data_type`."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        name = dotted(node.func) or ""
        if name.rsplit(".", 1)[-1] != "QualityAssessment":
            return
        named = {arg.keyword.value for arg in node.args if arg.keyword is not None}
        if "data_type" not in named and not any(arg.star for arg in node.args):
            self.lines.append(self.get_metadata(PositionProvider, node).start.line)


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    found: list[Finding] = []
    if is_test(path):
        for match in _RUN.finditer(text):
            line = _at(text, match.start())
            found.append(Finding("suite-cases-v29", path, line, line_of(text, line)))
    if "QualityAssessment" not in text:
        return found
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError:
        return found
    assessments = _Assessments()
    MetadataWrapper(module).visit(assessments)
    for line in assessments.lines:
        found.append(Finding("quality-assessment-data-type", path, line, line_of(text, line)))
    return found
