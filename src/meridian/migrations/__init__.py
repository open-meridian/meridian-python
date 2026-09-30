"""What moves a plugin from one release of this SDK to the next (decisions/025).

Every release that changes what a plugin calls carries a migration from the
release before it, and every other release carries one that only moves the
pins, so the steps from any recorded release to this one exist and run in
order. `meridian plugin migrate` moves a plugin's pins and runs these.

A migration is a directory here holding `migration.toml`, the record of it --
from, to, what it rewrites and what it leaves for a person or an agent -- and
the rewrite code the record names beside it, if it has any. The record is
data, not Python, so another SDK carries its own in the same shape, with
rewrite code in its own language.

The rewrite code is a module with two functions, each given a file's path
relative to the plugin and its text:

- `rewrite(path, text) -> Rewritten`: the file rewritten, the rules that
  rewrote it, once for each place, and anything the rewriting found left
  to do there;
- `left(path, text) -> list[Finding]`: what is still to do by hand in the
  file after every step has run.

Every rule either names must be in its record: what a migration does is what
its record says, and nothing else.

Run as `python -m meridian.migrations --from <version> --to <version>`, with
the plugin's files on stdin; see `__main__`. The rewrites read Python with
libcst, the SDK's `migrate` extra, which a plugin's own runtime never needs.
"""

from __future__ import annotations

import importlib
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, cast

HERE = Path(__file__).parent

#: The record in each migration's directory.
RECORD = "migration.toml"


class NoMigration(Exception):
    """No recorded steps lead from the one version to the other."""


def version(text: str) -> tuple[int, ...]:
    """`0.6.1` as numbers to compare. Anything else is refused, not guessed."""
    parts = text.strip().split(".")
    if not parts or not all(part.isdigit() for part in parts):
        raise NoMigration(f"{text!r} is not a release of the SDK: numbers, dot by dot")
    return tuple(int(part) for part in parts)


@dataclass(frozen=True)
class Rule:
    """One thing a migration rewrites, or leaves by hand, as its record says."""

    rule: str
    what: str
    # For a rule left by hand: what to write instead.
    instead: str = ""


@dataclass(frozen=True)
class Finding:
    """A place left by hand: the rule, the file and the line (from 1; 0 for
    the file as a whole), and what is there."""

    rule: str
    file: str
    line: int
    found: str


@dataclass(frozen=True)
class Rewritten:
    text: str
    # A rule's id once for each place it rewrote.
    rules: tuple[str, ...] = ()
    findings: tuple[Finding, ...] = ()


#: What any migration with rewrite code may leave: a file it could not read.
UNREADABLE = Rule(
    "unreadable",
    "a file the migration could not read as Python, which it therefore left as it was",
    "make it parse, and migrate again from the same version, or apply this step's rewrites "
    "to it by hand",
)


@dataclass(frozen=True)
class Migration:
    source: str
    target: str
    summary: str
    # Whether a plugin that is not migrated breaks on the new release, rather
    # than keeping a form the release no longer promises.
    breaking: bool
    rewrites: tuple[Rule, ...]
    by_hand: tuple[Rule, ...]
    directory: Path
    # The rewrite code's file, beside the record; none when only the pins move.
    code: str | None = None

    @property
    def name(self) -> str:
        return f"{self.source} to {self.target}"

    def rule(self, rule: str) -> Rule:
        for each in (*self.rewrites, *self.by_hand, UNREADABLE):
            if each.rule == rule:
                return each
        raise AssertionError(f"migration {self.name}: rule {rule!r} is not in its record")

    def module(self) -> ModuleType | None:
        if self.code is None:
            return None
        return importlib.import_module(
            f"{__name__}.{self.directory.name}.{Path(self.code).stem}"
        )


def _rules(table: dict[str, Any], key: str, by_hand: bool) -> tuple[Rule, ...]:
    rules = []
    for entry in table.get(key, []):
        rule = Rule(str(entry["rule"]), str(entry["what"]), str(entry.get("instead", "")))
        if by_hand and not rule.instead:
            raise AssertionError(f"{key} {rule.rule!r} says nothing to do instead")
        rules.append(rule)
    return tuple(rules)


def read(directory: Path) -> Migration:
    """One migration, from its record."""
    table = tomllib.loads((directory / RECORD).read_text(encoding="utf-8"))
    code = table.get("rewrite")
    migration = Migration(
        source=str(table["from"]),
        target=str(table["to"]),
        summary=str(table["summary"]).strip(),
        breaking=bool(table["breaking"]),
        rewrites=_rules(table, "rewrites", by_hand=False),
        by_hand=_rules(table, "by_hand", by_hand=True),
        directory=directory,
        code=str(code) if code else None,
    )
    if version(migration.source) >= version(migration.target):
        raise AssertionError(f"{directory.name}: from {migration.source} is not before its to")
    if migration.code is not None and not (directory / migration.code).is_file():
        raise AssertionError(f"{directory.name}: names {migration.code}, which is not there")
    ids = [rule.rule for rule in (*migration.rewrites, *migration.by_hand)]
    if len(ids) != len(set(ids)):
        raise AssertionError(f"{directory.name}: a rule is recorded twice")
    return migration


def recorded() -> list[Migration]:
    """Every migration this SDK carries, oldest first. Each starts where the
    one before it ends, so the steps from any of them to the last exist."""
    migrations = sorted(
        (read(path.parent) for path in HERE.glob(f"*/{RECORD}")),
        key=lambda migration: version(migration.target),
    )
    for before, after in zip(migrations, migrations[1:], strict=False):
        if before.target != after.source:
            raise AssertionError(
                f"no migration from {before.target}: {before.name} is followed by {after.name}"
            )
    return migrations


def chain(source: str, target: str) -> list[Migration]:
    """The steps from `source` to `target`, in order."""
    if version(source) > version(target):
        raise NoMigration(f"{source} is after {target}: a migration never goes backwards")
    migrations = recorded()
    starting = {migration.source: migration for migration in migrations}
    steps: list[Migration] = []
    at = source
    while at != target:
        step = starting.get(at)
        if step is None:
            first, last = migrations[0].source, migrations[-1].target
            raise NoMigration(
                f"no migration is recorded from {at}: they run from {first} to {last}, "
                "each from one release to the next"
            )
        if version(step.target) > version(target):
            raise NoMigration(
                f"{target} is not a release: the step from {at} goes to {step.target}"
            )
        steps.append(step)
        at = step.target
    return steps


@dataclass
class Step:
    migration: Migration
    # By file, each rule that rewrote it and how many places it did.
    rewrote: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass
class Result:
    source: str
    target: str
    steps: list[Step]
    # The final text of each file that changed.
    files: dict[str, str]
    by_hand: list[tuple[Migration, Finding]]


def migrate(files: dict[str, str], source: str, target: str) -> Result:
    """Each step from `source` to `target` over the plugin's files, in order,
    each on what the one before it wrote. Nothing is written anywhere: the
    files that changed come back, and the caller writes them."""
    steps = chain(source, target)
    # What a rewrite raises for a file it cannot read; nothing is read when
    # only the pins move.
    unparsed: type[Exception] = SyntaxError
    if any(migration.code for migration in steps):
        import libcst

        unparsed = libcst.ParserSyntaxError
    now = dict(files)
    result = Result(source=source, target=target, steps=[], files={}, by_hand=[])
    unreadable: set[tuple[str, str]] = set()
    for migration in steps:
        step = Step(migration)
        result.steps.append(step)
        code = migration.module()
        if code is None:
            continue
        rewrite = cast(Any, code).rewrite
        for path in sorted(now):
            try:
                rewritten: Rewritten = rewrite(path, now[path])
            except unparsed as failed:
                line = int(getattr(failed, "raw_line", 0) or 0)
                result.by_hand.append(
                    (
                        migration,
                        Finding(UNREADABLE.rule, path, line, str(failed).splitlines()[0]),
                    )
                )
                unreadable.add((migration.directory.name, path))
                continue
            for rule in rewritten.rules:
                migration.rule(rule)
                counted = step.rewrote.setdefault(path, {})
                counted[rule] = counted.get(rule, 0) + 1
            for finding in rewritten.findings:
                migration.rule(finding.rule)
                result.by_hand.append((migration, finding))
            now[path] = rewritten.text
    # What is left, found in the files as they now are, so each line is the
    # line a person opens.
    for migration in steps:
        code = migration.module()
        if code is None:
            continue
        left = cast(Any, code).left
        for path in sorted(now):
            if (migration.directory.name, path) in unreadable:
                continue
            for finding in left(path, now[path]):
                migration.rule(finding.rule)
                result.by_hand.append((migration, finding))
    result.files = {path: text for path, text in now.items() if files.get(path) != text}
    return result


def as_json(result: Result) -> dict[str, Any]:
    """What `python -m meridian.migrations` writes, and `meridian plugin
    migrate` reads."""
    return {
        "from": result.source,
        "to": result.target,
        "steps": [
            {
                "from": step.migration.source,
                "to": step.migration.target,
                "summary": step.migration.summary,
                "breaking": step.migration.breaking,
                "rewrote": [
                    {
                        "file": path,
                        "rule": rule,
                        "what": step.migration.rule(rule).what,
                        "places": places,
                    }
                    for path, rules in sorted(step.rewrote.items())
                    for rule, places in sorted(rules.items())
                ],
            }
            for step in result.steps
        ],
        "files": result.files,
        "by_hand": [
            {
                "from": migration.source,
                "to": migration.target,
                "rule": finding.rule,
                "file": finding.file,
                "line": finding.line or None,
                "found": finding.found,
                "what": migration.rule(finding.rule).what,
                "instead": migration.rule(finding.rule).instead,
            }
            for migration, finding in result.by_hand
        ],
    }
