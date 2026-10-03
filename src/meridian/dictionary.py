"""The data dictionary a refusal's paths resolve to (contract v12;
spec/every-store-publishes-a-versioned-data-dictionary, requirements 9 to
11; spec/a-deployment-serves-its-mcp, requirement 15).

`fields.json` is meridian-schema's `boundaries/fields.json` at the revision
this SDK vendors, so what an entry says is what the contract this SDK is
built against says. A path in the dictionary's grammar -- `field`, `[n]`,
and `x` stepping through `x_id` into the record the identifier names --
resolves from an operation (the matrix row a plugin's command is, such as
`RecordOpeningBalance`) to the entry it lands on:

    entry("RecordOpeningBalance", "positions[2].instrument.asset_class")
    # {"name": "meridian.v1.InstrumentRecord.asset_class", "meaning": ..., ...}

so a refusal can say which field it is about and what that field means,
for an agent to read without parsing a sentence.
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Any

__all__ = ["entry", "resolve"]

_STEP = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]")


@functools.cache
def _fields() -> dict[str, Any]:
    with (Path(__file__).parent / "fields.json").open(encoding="utf-8") as read:
        data: dict[str, Any] = json.load(read)
    return data


@functools.cache
def _by_name() -> dict[str, dict[str, Any]]:
    return {each["name"]: each for each in _fields()["entries"]}


def _steps(path: str) -> list[str]:
    """The names a path steps through, its indices dropped."""
    names: list[str] = []
    at = 0
    while at < len(path):
        m = _STEP.match(path, at)
        if m is None:
            return []
        if m.group(1) is not None:
            names.append(m.group(1))
        at = m.end()
        if at < len(path) and path[at] == ".":
            at += 1
    return names


def _message_of(type_text: str, package: str) -> str | None:
    """The message an entry's type names (`repeated message OpeningPosition`),
    in the entry's own package where it gives none."""
    words = type_text.split()
    if "message" not in words:
        return None
    name = words[words.index("message") + 1]
    return name if "." in name else f"{package}.{name}"


def resolve(message: str, path: str) -> str | None:
    """The entry's name `path` lands on from `message` (a full name such as
    `meridian.v1.RecordOpeningBalanceRequest`), or None where it lands on
    no entry."""
    entries = _by_name()
    identifiers: dict[str, str] = _fields().get("identifiers", {})
    names = _steps(path)
    if not names:
        return None
    current = message
    for depth, name in enumerate(names):
        package = current.rsplit(".", 1)[0]
        found = entries.get(f"{current}.{name}")
        if found is None:
            # `x` stepping through `x_id` into the record its kind names.
            through = entries.get(f"{current}.{name}_id")
            if through is None:
                return None
            kind = str(through.get("type", "")).removeprefix("repeated ").split()
            if len(kind) != 2 or kind[0] != "identifier" or kind[1] not in identifiers:
                return None
            current = identifiers[kind[1]]
            if depth == len(names) - 1:
                return str(through["name"])
            continue
        if depth == len(names) - 1:
            return str(found["name"])
        nested = _message_of(str(found.get("type", "")), package)
        if nested is None:
            return None
        current = nested
    return None


def entry(operation: str, path: str) -> dict[str, Any] | None:
    """The entry `path` lands on in `operation`'s command (a matrix row's
    canonical name), or None."""
    message = _fields().get("operations", {}).get(operation)
    if message is None:
        return None
    name = resolve(message, path)
    return None if name is None else _by_name().get(name)
