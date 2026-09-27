"""`meridian-dev run`: a live plugin's process, restarted on each change.

The plugin container's command in the chart's live shape, on a development
deployment (spec/live-plugin-development, requirement 7). The pod, the
sidecar and its broker credential stay as they are; this restarts only the
plugin's process, on the files the sidecar was sent.

The live folder, shared with the sidecar:

- the plugin's files, copied from the image's `/plugin` when the folder is
  new, and written by the sidecar after that;
- `.meridian/revision`, which the sidecar writes last, after the files: a
  new revision is what starts a restart, so a change half-written is never
  run;
- `.meridian/output.jsonl`, the plugin's output, one line each, with the
  revision it came from -- bounded, and written by this alone;
- `.meridian/runner-events.jsonl`, `restarted`, `crashed` with the traceback,
  `exited`; and the SDK writes `ready` there itself once it has registered
  with its sidecar, so `ready` means running, not started.

The sidecar's own events -- `synced`, and what the instance published,
received and was refused -- are its own file; the sidecar reads both back.

The standard library alone: the base image gains nothing it did not have.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import tomllib
from collections import deque
from pathlib import Path

LIVE = Path(os.environ.get("MERIDIAN_LIVE_DIR", "/plugin/live"))
SEED = Path(os.environ.get("MERIDIAN_LIVE_SEED", "/plugin"))
BOOKS = ".meridian"
OUTPUT_LIMIT = 1 << 20  # bytes of output kept
EVENTS_LIMIT = 2000  # lines of events kept
CRASH_LINES = 40  # of output, carried by `crashed`
POLL = 0.25  # seconds between looks at the revision
STOP_GRACE = 5.0  # seconds a process is given to stop before it is killed
# Read by the SDK, which writes `ready` when it registers.
EVENTS_ENV = "MERIDIAN_DEV_EVENTS"
REVISION_ENV = "MERIDIAN_DEV_REVISION"


def books(live: Path) -> Path:
    return live / BOOKS


def revision(live: Path) -> int:
    try:
        return int((books(live) / "revision").read_text().strip() or 0)
    except (FileNotFoundError, ValueError):
        return 0


def seed(live: Path, source: Path) -> bool:
    """Copy the image's plugin into a new live folder. False when it was not
    new: what the sidecar was sent is never overwritten by the image."""
    if (live / "pyproject.toml").exists():
        return False
    live.mkdir(parents=True, exist_ok=True)
    for entry in source.iterdir():
        if entry.name in (live.name, BOOKS, "__pycache__") or entry.resolve() == live.resolve():
            continue
        target = live / entry.name
        if entry.is_dir():
            shutil.copytree(
                entry,
                target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", BOOKS),
            )
        else:
            shutil.copy2(entry, target)
    return True


def entry_point(live: Path) -> tuple[str, str]:
    """The module and function `[project.scripts]` names: what the image's
    own command runs, found the same way."""
    project = tomllib.loads((live / "pyproject.toml").read_text())
    scripts = project.get("project", {}).get("scripts", {})
    if not scripts:
        raise SystemExit(
            f"{live / 'pyproject.toml'} names no [project.scripts] entry point to run"
        )
    target = next(iter(scripts.values()))
    module, _, function = target.partition(":")
    if not module or not function:
        raise SystemExit(f"the entry point {target!r} is not `module:function`")
    return module.strip(), function.strip()


def append(path: Path, record: dict[str, object], keep: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(record) + "\n")
    if keep is not None:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        if len(lines) > keep:
            path.write_text("".join(lines[-keep:]), encoding="utf-8")


def report_ready() -> None:
    """Called by the SDK once the plugin has registered with its sidecar: the
    revision it runs is ready. Nothing when not run by this."""
    events = os.environ.get(EVENTS_ENV)
    if not events:
        return
    append(
        Path(events),
        {
            "revision": int(os.environ.get(REVISION_ENV, "0") or 0),
            "event": "ready",
            "at": time.time(),
        },
    )


class Runner:
    def __init__(self, live: Path, source: Path) -> None:
        self.live = live
        self.source = source
        self.events = books(live) / "runner-events.jsonl"
        self.output = books(live) / "output.jsonl"
        self.process: subprocess.Popen[str] | None = None
        self.running = 0
        self.tail: deque[str] = deque(maxlen=CRASH_LINES)
        self.lock = threading.Lock()
        self.stopping = False

    def event(self, name: str, **more: object) -> None:
        append(
            self.events,
            {"revision": self.running, "event": name, "at": time.time(), **more},
            keep=EVENTS_LIMIT,
        )

    def start(self) -> None:
        self.running = revision(self.live)
        self.tail.clear()
        try:
            module, function = entry_point(self.live)
        except SystemExit as refused:
            self.event("crashed", traceback=str(refused), exit=None)
            self.process = None
            return
        code = f"import sys\nfrom {module} import {function} as main\nsys.exit(main())\n"
        env = dict(os.environ)
        paths = [str(self.live / "src"), str(self.live)]
        env["PYTHONPATH"] = os.pathsep.join(
            paths + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
        )
        env[EVENTS_ENV] = str(self.events)
        env[REVISION_ENV] = str(self.running)
        env["PYTHONUNBUFFERED"] = "1"
        self.process = subprocess.Popen(
            [sys.executable, "-c", code],
            cwd=self.live,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.event("restarted", pid=self.process.pid)
        threading.Thread(
            target=self.read, args=(self.process, self.running), daemon=True
        ).start()

    def read(self, process: subprocess.Popen[str], at: int) -> None:
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip("\n")
            print(line, flush=True)  # the pod's own log, as a plugin's always is
            with self.lock:
                if at == self.running:
                    self.tail.append(line)
                append(self.output, {"revision": at, "line": line})
                if self.output.stat().st_size > OUTPUT_LIMIT:
                    kept = self.output.read_text(encoding="utf-8").splitlines(keepends=True)
                    self.output.write_text("".join(kept[len(kept) // 2 :]), encoding="utf-8")

    def stop(self) -> None:
        process, self.process = self.process, None
        if process is None or process.poll() is not None:
            return
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(STOP_GRACE)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def ended(self) -> None:
        """A process that ended by itself: said once, with what it printed
        last, and not started again until the next revision -- a plugin that
        cannot start would otherwise restart as fast as it fails."""
        assert self.process is not None
        code = self.process.returncode
        time.sleep(0.2)  # the reader's last lines
        with self.lock:
            tail = "\n".join(self.tail)
        if code == 0:
            self.event("exited", exit=0)
        else:
            self.event("crashed", exit=code, traceback=tail)
        self.process = None

    def run(self) -> int:
        if seed(self.live, self.source):
            self.event("seeded")
        self.start()
        while not self.stopping:
            time.sleep(POLL)
            if revision(self.live) != self.running:
                self.stop()
                self.start()
            elif self.process is not None and self.process.poll() is not None:
                self.ended()
        self.stop()
        return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] != ["run"]:
        print("usage: meridian-dev run", file=sys.stderr)
        return 2
    # Group-writable, with the pod's shared group: the sidecar replaces the
    # files this seeded, and writes the revision into the folder this made.
    os.umask(0o002)
    runner = Runner(LIVE, SEED)

    def stop(*_: object) -> None:
        runner.stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
