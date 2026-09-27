"""`meridian-dev run`: the live shape's process (spec/live-plugin-development).

A real subprocess each time, against a plugin written into a temporary live
folder: what is checked is what the runner does to a process, not a mock of it.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from meridian import dev

PYPROJECT = """
[project]
name = "sample-plugin"
version = "0.1.0"
[project.scripts]
sample-plugin = "sample_plugin.__main__:main"
"""

WORKS = """
import time
from meridian.dev import report_ready

def main():
    print("serving revision", flush=True)
    report_ready()
    while True:
        time.sleep(0.1)
"""

BREAKS = """
def main():
    raise RuntimeError("the page module is broken")
"""


def plugin(root: Path, body: str) -> None:
    (root / "src" / "sample_plugin").mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(PYPROJECT)
    (root / "src" / "sample_plugin" / "__init__.py").write_text("")
    (root / "src" / "sample_plugin" / "__main__.py").write_text(body)


def events(live: Path) -> list[dict]:
    path = live / ".meridian" / "runner-events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def until(check, seconds: float = 15.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        found = check()
        if found:
            return found
        time.sleep(0.1)
    raise AssertionError("never happened")


def send(live: Path, body: str, rev: int) -> None:
    """As the sidecar does: the files, then the revision last."""
    plugin(live, body)
    (live / ".meridian").mkdir(exist_ok=True)
    (live / ".meridian" / "revision").write_text(str(rev))


@pytest.fixture
def running(tmp_path, monkeypatch):
    monkeypatch.setattr(dev, "POLL", 0.05)
    monkeypatch.setattr(dev, "STOP_GRACE", 2.0)
    seed, live = tmp_path / "image", tmp_path / "live"
    plugin(seed, WORKS)
    runner = dev.Runner(live, seed)
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    yield runner, live
    runner.stopping = True
    thread.join(10)


def test_a_new_live_folder_is_seeded_from_the_image_and_never_again(tmp_path):
    seed, live = tmp_path / "image", tmp_path / "live"
    plugin(seed, WORKS)
    assert dev.seed(live, seed)
    assert (live / "src" / "sample_plugin" / "__main__.py").read_text() == WORKS
    (live / "src" / "sample_plugin" / "__main__.py").write_text(BREAKS)
    assert not dev.seed(live, seed), "what the sidecar was sent is never overwritten"
    assert (live / "src" / "sample_plugin" / "__main__.py").read_text() == BREAKS


def test_the_entry_point_is_the_one_the_project_names(tmp_path):
    plugin(tmp_path, WORKS)
    assert dev.entry_point(tmp_path) == ("sample_plugin.__main__", "main")


def test_a_revision_restarts_the_process_and_the_sdk_says_when_it_is_ready(running):
    runner, live = running
    until(lambda: any(e["event"] == "ready" and e["revision"] == 0 for e in events(live)))
    first = runner.process.pid
    send(live, WORKS.replace("serving revision", "serving the change"), 1)
    until(lambda: any(e["event"] == "ready" and e["revision"] == 1 for e in events(live)))
    assert runner.process.pid != first, "a new process"
    lines = [
        json.loads(line)
        for line in (live / ".meridian" / "output.jsonl").read_text().splitlines()
    ]
    assert {"revision": 1, "line": "serving the change"} in lines
    assert {"revision": 0, "line": "serving revision"} in lines


def test_a_plugin_that_cannot_start_is_reported_with_why_and_not_restarted(running):
    runner, live = running
    until(lambda: any(e["event"] == "ready" for e in events(live)))
    send(live, BREAKS, 2)
    crashed = until(
        lambda: [e for e in events(live) if e["event"] == "crashed" and e["revision"] == 2]
    )
    assert "the page module is broken" in crashed[0]["traceback"]
    time.sleep(0.5)
    restarts = [e for e in events(live) if e["event"] == "restarted" and e["revision"] == 2]
    assert len(restarts) == 1, "not restarted until the next revision"
    send(live, WORKS, 3)
    until(lambda: any(e["event"] == "ready" and e["revision"] == 3 for e in events(live)))


def test_ready_is_said_only_under_the_runner(monkeypatch, tmp_path):
    monkeypatch.delenv(dev.EVENTS_ENV, raising=False)
    dev.report_ready()  # nothing, and no error
    monkeypatch.setenv(dev.EVENTS_ENV, str(tmp_path / "events.jsonl"))
    monkeypatch.setenv(dev.REVISION_ENV, "7")
    dev.report_ready()
    said = json.loads((tmp_path / "events.jsonl").read_text())
    assert said["revision"] == 7 and said["event"] == "ready"
