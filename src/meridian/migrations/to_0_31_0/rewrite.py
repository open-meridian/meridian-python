"""open-meridian 0.30.0 to 0.31.0: contract v26.

The Dockerfile's base pinned by digest at an older release (`ARG
BASE=ghcr.io/open-meridian/plugin-python:<v>@sha256:<hex>`) is moved to
0.31.0 with its digest dropped, since this runs with no network and cannot
read the new release's digest; `meridian plugin migrate` (CLI 0.1.47) has
moved the tag and the digest before this runs, and then there is nothing to
do. Left by hand: pinning the digest again; a role's suite test that v26's
cases are new to; and a connectivity adapter saying no environment its
session reached; and custody's pages and a broker's listings layer a plugin
keeps itself, which are the SDK's (ruling 213). migration.toml, beside this, records the rules.
"""

from __future__ import annotations

import re

from .. import Finding, Rewritten
from .._cst import is_test, line_of

TARGET = "0.31.0"
IMAGE = "ghcr.io/open-meridian/plugin-python"
_BASE = re.compile(
    rf"(?P<head>{re.escape(IMAGE)}:)(?P<tag>[0-9][0-9.]*)(?P<digest>@sha256:[0-9a-f]{{64}})"
)
#: The roles whose suites contract v26 adds cases a plugin maps itself to.
_ROLES = ("reporting", "portfolio", "compliance", "signal", "data", "ems", "oms", "operations")
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


def _defines(body: str, *names: str) -> bool:
    return all(re.search(rf"^[ \t]+def {name}\(", body, re.M) for name in names)


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    found: list[Finding] = []
    if (
        not is_test(path)
        and 'name="read_account_links"' in text
        and 'name="read_account_activities"' in text
        and re.search(r"^async def link_account\(", text, re.M)
    ):
        found.append(Finding("custody-pages-onto-sdk", path, 1, line_of(text, 1)))
    lake = re.search(r"^class Lake\b", text, re.M)
    if (
        not is_test(path)
        and lake is not None
        and re.search(r"^class Products\b", text, re.M)
        and re.search(r"^    async def trade_row\(", text, re.M)
        and re.search(r"^    async def quote_row\(", text, re.M)
    ):
        line = text[: lake.start()].count("\n") + 1
        found.append(Finding("lake-onto-sdk", path, line, line_of(text, line)))
    if is_test(path):
        for match in _RUN.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            found.append(Finding("suite-cases-v26", path, line, line_of(text, line)))
        return found
    for match in re.finditer(r"^class \w+[^\n]*:\n", text, re.M):
        start = match.end()
        following = re.search(r"^\S", text[start:], re.M)
        body = text[start : start + following.start()] if following else text[start:]
        if _defines(body, "catalogue", "place", "orders") and not re.search(
            r"^[ \t]+(environment\b|self\.environment\b)|def environment\(", body, re.M
        ):
            line = text.count("\n", 0, match.start()) + 1
            found.append(
                Finding("venue-reports-no-environment", path, line, line_of(text, line))
            )
    return found
