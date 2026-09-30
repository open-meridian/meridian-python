"""`python -m meridian.migrations --from <version> --to <version>`

What `meridian plugin migrate` runs, in the SDK's image and cut off from the
network. It reads the plugin's files from stdin, as one JSON object --
`{"files": {"<path relative to the plugin>": "<text>", ...}}` -- runs each
step in order, and writes one JSON object to stdout: the steps and what each
rewrote, the new text of every file that changed, and what is left by hand
(`meridian.migrations.as_json`). It writes no file itself; the caller does.

`--list` writes the migrations this SDK carries instead, and reads nothing.

Exits 0 when it ran, whatever is left by hand; 2 when no recorded steps lead
from the one version to the other, or it was asked wrongly.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import NoMigration, as_json, migrate, recorded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m meridian.migrations")
    parser.add_argument("--from", dest="source")
    parser.add_argument("--to", dest="target")
    parser.add_argument("--list", action="store_true")
    asked = parser.parse_args(argv)

    if asked.list:
        listed = [
            {
                "from": m.source,
                "to": m.target,
                "summary": m.summary,
                "breaking": m.breaking,
                "rewrites": [{"rule": r.rule, "what": r.what} for r in m.rewrites],
                "by_hand": [
                    {"rule": r.rule, "what": r.what, "instead": r.instead} for r in m.by_hand
                ],
            }
            for m in recorded()
        ]
        json.dump(listed, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if not asked.source or not asked.target:
        print("python -m meridian.migrations: --from and --to, or --list", file=sys.stderr)
        return 2
    try:
        given = json.load(sys.stdin)
        files = given["files"]
        if not isinstance(files, dict) or not all(
            isinstance(path, str) and isinstance(text, str) for path, text in files.items()
        ):
            raise ValueError("files is not an object of paths to texts")
    except (ValueError, KeyError, TypeError) as wrong:
        print(f"python -m meridian.migrations: stdin: {wrong}", file=sys.stderr)
        return 2
    try:
        result = migrate(files, asked.source, asked.target)
    except NoMigration as none:
        print(f"python -m meridian.migrations: {none}", file=sys.stderr)
        return 2
    json.dump(as_json(result), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
