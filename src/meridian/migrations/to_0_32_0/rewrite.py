"""open-meridian 0.31.1 to 0.32.0: contract v27.

The Dockerfile's base pinned by digest at an older release is moved to
0.32.0 with its digest dropped, since this runs with no network; `meridian
plugin migrate` (CLI 0.1.47) has moved the tag and the digest before this
runs, and then there is nothing to do. Left by hand: pinning the digest
again; a role's suite test that v27's cases are new to; a data plugin's
lake query faked with no trades; a connectivity plugin's own Trading page,
and an event-contract plugin's own events loop, both the SDK's now; and an
e2e workflow's log upload missing hidden files. migration.toml, beside
this, records the rules.
"""

from __future__ import annotations

import re

from .. import Finding, Rewritten
from .._cst import is_test, line_of

TARGET = "0.32.0"
IMAGE = "ghcr.io/open-meridian/plugin-python"
_BASE = re.compile(
    rf"(?P<head>{re.escape(IMAGE)}:)(?P<tag>[0-9][0-9.]*)(?P<digest>@sha256:[0-9a-f]{{64}})"
)
#: Every role whose suite contract v27 adds cases a plugin maps itself to.
_ROLES = (
    "reporting", "portfolio", "compliance", "signal", "data", "ems", "oms", "operations",
    "connectivity",
)  # fmt: skip
_RUN = re.compile(rf"""\brun(?:_async)?\(\s*["'](?P<role>{"|".join(_ROLES)})["']""")


def rewrite(path: str, text: str) -> Rewritten:
    if path != "Dockerfile":
        return Rewritten(text)
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


def _at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def left(path: str, text: str) -> list[Finding]:
    found: list[Finding] = []
    if path.startswith(".github/workflows/") and path.endswith((".yaml", ".yml")):
        for match in re.finditer(r"uses:\s*actions/upload-artifact@\S+", text):
            step = text[match.end() :]
            following = re.search(r"\n\s*-\s", step)
            body = step[: following.start()] if following else step
            if ".e2e" in body and "include-hidden-files" not in body:
                line = _at(text, match.start())
                found.append(Finding("e2e-hidden-files", path, line, line_of(text, line)))
        return found
    if not path.endswith(".py"):
        return []
    if is_test(path):
        for match in _RUN.finditer(text):
            line = _at(text, match.start())
            found.append(Finding("suite-cases-v27", path, line, line_of(text, line)))
        lake = re.search(
            r"""["']queries-the-lake-within-bounds["']\s*:\s*\w*lake_query""", text
        )
        if (
            lake is not None
            and "meridian.v1.Trade" not in text
            and "a-trade-recorded" not in text
        ):
            line = _at(text, lake.start())
            found.append(Finding("lake-query-without-trades", path, line, line_of(text, line)))
        return found
    trading = re.search(r"""name\s*=\s*["']read_trading["']""", text)
    if trading is not None and re.search(r"""name\s*=\s*["']enable_trading["']""", text):
        line = _at(text, trading.start())
        found.append(Finding("trading-page-onto-sdk", path, line, line_of(text, line)))
    events = re.search(r"^class \w+[^\n]*:\n", text, re.M)
    while events is not None:
        start = events.end()
        following = re.search(r"^\S", text[start:], re.M)
        body = text[start : start + following.start()] if following else text[start:]
        if "report_event(" in body and re.search(
            r"\bevent\(", body.replace("report_event(", "")
        ):
            line = _at(text, events.start())
            found.append(Finding("events-onto-sdk", path, line, line_of(text, line)))
        events = re.compile(r"^class \w+[^\n]*:\n", re.M).search(text, start)
    return found
