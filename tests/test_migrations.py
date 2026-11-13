"""The migrations this SDK carries (decisions/025), over the plugins they are
recorded for.

`tests/migrations/` holds each plugin as it was written and as its migration
leaves it: desk, written against 0.5.0 and moved to this release,
meridian-snaptrade's shape at 0.6.1, and listed, written against 0.33.5 and
importing the topic modules 0.34.0 moves to `meridian.helpers`. Each is
migrated here as `meridian plugin migrate` does it -- its pins moved, every
step run in order -- and must come out as its expected tree, with the same
things left by hand, and pass its own tests against this SDK. `make
check-migrations` holds the same results to `meridian plugin check
--run-tests`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest

from meridian import migrations
from meridian.migrations import NoMigration, as_json, chain, migrate, recorded

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "migrations"
SDK = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def plugin_files(root: Path) -> dict[str, str]:
    """What `meridian plugin migrate` sends: the Python, pyproject.toml and
    the Dockerfile."""
    return {
        path.relative_to(root).as_posix(): path.read_text()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and (
            path.suffix == ".py"
            or path.relative_to(root).as_posix() in ("pyproject.toml", "Dockerfile")
        )
    }


def migrated(fixture: str, source: str, target: str, into: Path) -> migrations.Result:
    """The fixture copied into `into`, migrated, and its two pins moved, as
    `meridian plugin migrate` moves them."""
    root = FIXTURES / fixture
    for path in root.rglob("*"):
        if path.is_file():
            copied = into / path.relative_to(root)
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(path.read_bytes())
    result = migrate(plugin_files(into), source, target)
    for path, text in result.files.items():
        (into / path).write_text(text)
    for name, old, new in (
        ("pyproject.toml", f"open-meridian=={source}", f"open-meridian=={target}"),
        ("Dockerfile", f"plugin-python:{source}", f"plugin-python:{target}"),
    ):
        (into / name).write_text((into / name).read_text().replace(old, new))
    return result


def tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and ".egg-info" not in str(path)
    }


def left_by_hand(result: migrations.Result) -> list[tuple[str, str, int]]:
    return [(finding.rule, finding.file, finding.line) for _, finding in result.by_hand]


def own_tests_pass(root: Path) -> None:
    """The plugin's tests, against this SDK, with the plugin importable."""
    ran = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(root / "tests")],
        cwd=root,
        env={"PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr


# ── The record ───────────────────────────────────────────────────────────


def test_every_release_since_the_first_recorded_has_its_step() -> None:
    steps = recorded()  # each starting where the one before it ends
    assert [(m.source, m.target) for m in steps[:3]] == [
        ("0.5.0", "0.6.0"),
        ("0.6.0", "0.6.1"),
        ("0.6.1", "0.7.0"),
    ]
    assert (steps[-1].source, steps[-1].target) == ("0.36.1", "0.36.2")
    # A release that moves the version records its step, if only the pins.
    assert steps[-1].target == SDK


def test_every_rule_the_code_names_is_in_its_record() -> None:
    # migrate() refuses a rule its record lacks; each is also said in words.
    for step in recorded():
        for rule in (*step.rewrites, *step.by_hand):
            assert rule.what, (step.name, rule.rule)
        assert step.code is None or (step.directory / step.code).is_file()


def test_steps_are_chosen_in_order_and_never_backwards() -> None:
    assert [m.target for m in chain("0.5.0", "0.7.0")] == ["0.6.0", "0.6.1", "0.7.0"]
    assert chain("0.6.1", "0.6.1") == []
    with pytest.raises(NoMigration, match="never goes backwards"):
        chain("0.7.0", "0.6.0")
    with pytest.raises(NoMigration, match="no migration is recorded from 0.4.0"):
        chain("0.4.0", "0.7.0")
    with pytest.raises(NoMigration, match="0.6.5 is not a release"):
        chain("0.6.0", "0.6.5")
    with pytest.raises(NoMigration, match="not a release of the SDK"):
        chain("0.6", "latest")


# ── desk: 0.5.0 to this release ──────────────────────────────────────────


def test_desk_moves_from_tags_to_read_and_write(tmp_path: Path) -> None:
    result = migrated("desk-0.5.0", "0.5.0", "0.7.0", tmp_path)
    assert tree(tmp_path) == tree(FIXTURES / "desk-0.7.0")
    assert left_by_hand(result) == [
        ("tags-granted", "pyproject.toml", 18),
        ("identity-tags", "src/desk/__main__.py", 28),
        ("access-tag-by-tag", "src/desk/access.py", 33),
    ]
    rewrote = {
        (path, rule)
        for step in result.steps
        for path, rules in step.rewrote.items()
        for rule in rules
    }
    assert rewrote == {
        ("pyproject.toml", "tags-undeclared"),
        ("src/desk/access.py", "access-any"),
        ("src/desk/access.py", "access-union"),
        ("tests/test_desk.py", "caller-read-write"),
        ("tests/test_desk.py", "tag-access-import"),
        ("tests/test_desk.py", "not-linked-raised"),
        ("src/desk/record.py", "not-linked-isinstance"),
        ("src/desk/record.py", "not-linked-except"),
    }


def test_desk_passes_its_own_tests_once_migrated(tmp_path: Path) -> None:
    migrated("desk-0.5.0", "0.5.0", "0.7.0", tmp_path)
    own_tests_pass(tmp_path)


def test_desk_migrates_the_same_through_each_release(tmp_path: Path) -> None:
    # Step by step, each release's pins between, comes to the same place.
    files = plugin_files(FIXTURES / "desk-0.5.0")
    at = "0.5.0"
    for step in chain("0.5.0", "0.7.0"):
        files.update(migrate(files, at, step.target).files)
        at = step.target
    whole = migrate(plugin_files(FIXTURES / "desk-0.5.0"), "0.5.0", "0.7.0").files
    assert {path: files[path] for path in whole} == whole


# ── meridian-snaptrade's shape: 0.6.1 to 0.7.0 ───────────────────────────


def test_snaptrade_tells_the_unlinked_refusal_apart_by_its_code(tmp_path: Path) -> None:
    result = migrated("snaptrade-0.6.1", "0.6.1", "0.7.0", tmp_path)
    assert tree(tmp_path) == tree(FIXTURES / "snaptrade-0.7.0")
    assert left_by_hand(result) == []


def test_snaptrade_passes_its_own_tests_once_migrated(tmp_path: Path) -> None:
    migrated("snaptrade-0.6.1", "0.6.1", "0.7.0", tmp_path)
    own_tests_pass(tmp_path)


# ── listed: 0.33.5 to 0.34.0, the topic modules onto meridian.helpers ──


def test_listed_imports_the_topic_modules_from_meridian_helpers(tmp_path: Path) -> None:
    result = migrated("listed-0.33.5", "0.33.5", "0.34.0", tmp_path)
    assert tree(tmp_path) == tree(FIXTURES / "listed-0.34.0")
    # A comment naming an old path is a person's to reword.
    assert left_by_hand(result) == [("topic-module-named", "tests/test_listed.py", 32)]
    rewrote = {path: rules for step in result.steps for path, rules in step.rewrote.items()}
    assert rewrote == {
        "src/listed/chain.py": {"topic-module-to-helpers": 1},
        "src/listed/money.py": {"topic-module-to-helpers": 2},
        "src/listed/servicing.py": {"topic-module-to-helpers": 1},
        "src/listed/spread.py": {"topic-module-to-helpers": 3},
        "tests/test_listed.py": {"topic-module-to-helpers": 5},
    }


def test_listed_passes_its_own_tests_once_migrated(tmp_path: Path) -> None:
    migrated("listed-0.33.5", "0.33.5", "0.34.0", tmp_path)
    own_tests_pass(tmp_path)


def test_listed_as_migrated_is_left_as_it_is() -> None:
    result = migrate(plugin_files(FIXTURES / "listed-0.34.0"), "0.33.5", "0.34.0")
    assert result.files == {}
    assert left_by_hand(result) == [("topic-module-named", "tests/test_listed.py", 32)]


@pytest.mark.parametrize(
    ("fixture", "by_hand"),
    [
        # desk opens an empty statement naming no external account, which a
        # sidecar at v7 refuses (0.11.0 to 0.12.0). From 0.29.0 (contract
        # v25) a version's declaration carries its interface, and each must
        # name one in pyproject.toml; snaptrade's image, installing only the
        # package from a mount, holds no docs/ for its declaration to read.
        (
            "desk-0.7.0",
            [
                ("statement-external-account", "src/desk/page.py", 77),
                ("declaration-not-named", "pyproject.toml", 18),
                ("connect-names-the-declaration", "src/desk/__main__.py", 22),
                # From 0.35.0 its entry point connects by hand, and its page
                # and its recording act on the connection.
                ("connect-to-run", "src/desk/__main__.py", 22),
                ("act-on-the-connection", "src/desk/page.py", 77),
                ("act-on-the-connection", "src/desk/record.py", 20),
            ],
        ),
        (
            "snaptrade-0.7.0",
            [
                ("docs-not-in-image", "Dockerfile", 5),
                ("declaration-not-named", "pyproject.toml", 24),
                ("connect-to-run", "src/snaptrade/__main__.py", 12),
                ("act-on-the-connection", "src/snaptrade/contract.py", 42),
            ],
        ),
    ],
)
def test_the_recorded_plugins_are_as_the_later_steps_leave_them(
    fixture: str, by_hand: list[tuple[str, str, int]]
) -> None:
    # Neither reports an asset class or sends flat figures, so from 0.7.0 on
    # nothing is rewritten.
    result = migrate(plugin_files(FIXTURES / fixture), "0.7.0", SDK)
    assert result.files == {}
    assert left_by_hand(result) == by_hand


# ── 0.34.0 to 0.35.0: each role is one generated class ───────────────────

#: Each 0.34.0 plugin of a role's shape, what 0.35.0's step rewrites in it,
#: and what it leaves by hand: the data template as written (a single role,
#: wholly rewritten but for its suite test's hearing), the pricing
#: template's, a broker holding three roles in Alpaca's shape (the lake made
#: a class, the Trader's handlers dropped, its entry point, custody class and
#: page by hand), and a reading plugin hearing for its subjects (by hand).
V35 = {
    "lake": (
        {
            "src/lake/__main__.py": {"template-entry-to-run": 1},
            "src/lake/convert.py": {
                "self-plugin-act-to-self": 5,
                "receive-to-role-methods": 4,
                "template-entry-to-run": 1,
            },
            "src/lake/page.py": {"receive-to-role-methods": 1},
            "tests/test_page.py": {"receive-to-role-methods": 1},
            "tests/test_suite.py": {"receive-to-role-methods": 4},
        },
        [
            ("suite-producer-to-role", "tests/test_page.py", 36),
            ("suite-producer-to-role", "tests/test_suite.py", 102),
            ("suite-producer-to-role", "tests/test_suite.py", 135),
            ("suite-producer-to-role", "tests/test_suite.py", 144),
        ],
    ),
    "quote": (
        {
            "src/quote/__main__.py": {"template-entry-to-run": 1},
            "tests/test_page.py": {"common-logic-renamed": 1},
            "tests/test_suite.py": {"common-logic-renamed": 3},
        },
        [("suite-producer-to-role", "tests/test_suite.py", 70)],
    ),
    "broker": (
        {
            "src/broker/__main__.py": {
                "receive-to-role-methods": 4,
                "common-logic-renamed": 5,
            },
            "src/broker/lake.py": {
                "self-plugin-act-to-self": 2,
                "receive-to-role-methods": 5,
            },
            "tests/test_broker.py": {"receive-to-role-methods": 2},
        },
        [
            ("connect-to-run", "src/broker/__main__.py", 24),
            ("act-on-the-connection", "src/broker/book.py", 15),
            ("act-on-the-connection", "src/broker/page.py", 12),
            # custody's pages given no role object to act through (1014).
            ("act-on-the-connection", "src/broker/page.py", 64),
        ],
    ),
    # SDK 0.35's second part: a listings and chains plugin in Massive's shape,
    # its edge glue dropped and its copied `_changed` made the SDK's
    # SentRows; 924's helpers it adopts by hand named.
    "equities": (
        {
            "src/equities/chains.py": {"copied-bodies-to-sdk": 1, "self-plugin-act-to-self": 1},
            "src/equities/lake.py": {"listings-edge-glue-dropped": 1},
        },
        [
            ("helper-adopted", "src/equities/__main__.py", 19),
            ("helper-adopted", "src/equities/__main__.py", 28),
            ("helper-adopted", "src/equities/__main__.py", 34),
            ("connect-to-run", "src/equities/__main__.py", 50),
            ("helper-adopted", "src/equities/chains.py", 16),
            ("helper-adopted", "src/equities/chains.py", 30),
            ("helper-adopted", "src/equities/lake.py", 24),
        ],
    ),
    "reader": (
        {},
        [
            ("connect-to-run", "src/reader/__main__.py", 11),
            ("receive-not-rewritten", "src/reader/__main__.py", 14),
            ("act-on-the-connection", "src/reader/report.py", 16),
        ],
    ),
}


@pytest.mark.parametrize("name", sorted(V35))
def test_each_role_shape_migrates_to_0_35_as_recorded(tmp_path: Path, name: str) -> None:
    rewrote, by_hand = V35[name]
    result = migrated(f"{name}-0.34.0", "0.34.0", "0.35.0", tmp_path)
    assert tree(tmp_path) == tree(FIXTURES / f"{name}-0.35.0")
    assert {path: rules for step in result.steps for path, rules in step.rewrote.items()} == (
        rewrote
    )
    assert left_by_hand(result) == by_hand


@pytest.mark.parametrize("name", sorted(V35))
def test_each_role_shape_as_migrated_is_left_as_it_is(name: str) -> None:
    result = migrate(plugin_files(FIXTURES / f"{name}-0.35.0"), "0.34.0", "0.35.0")
    assert result.files == {}
    # A stand-in the step took from a class is said once, as it is taken.
    again = [
        each
        for each in V35[name][1]
        if each != ("suite-producer-to-role", "tests/test_page.py", 36)
    ]
    assert left_by_hand(result) == again


#: The by-hand work each fixture's findings name, done as a person would:
#: a suite test hearing through `recorder.receive` bound and heard instead.
BY_HAND = {
    "lake": [
        (
            "    converter = Converter(vendor or Vendor())  # type: ignore[arg-type]",
            '    converter = Recorder("reference-1").bind(Converter(vendor or Vendor()))',
        ),
        (
            "from meridian.testing import PageClient\n",
            "from meridian.suites import Recorder\nfrom meridian.testing import PageClient\n",
        ),
        (
            "await recorder.receive(observations_wanted=plugin.on_observations_wanted)",
            "await recorder.hear(plugin)",
        ),
        (
            "await recorder.receive(want_withdrawn=plugin.on_want_withdrawn)",
            "await recorder.hear(plugin)",
        ),
    ],
    "quote": [
        (
            "await recorder.receive(price_batch=recorder.bind(pricing.Pricer(MODELS)).heard)",
            "await recorder.hear(recorder.bind(pricing.Pricer(MODELS)))",
        )
    ],
}


def by_hand_done(name: str, into: Path) -> None:
    """The work a 0.35.0 fixture's findings name, done as a person would: its
    tests' recorded edits (`BY_HAND`), and the files the findings name as a
    person rewrote them (`tests/migrations/<name>-0.35.0-done/`, laid over
    the migrated tree)."""
    for old, new in BY_HAND.get(name, []):
        for path in (into / "tests").glob("*.py"):
            path.write_text(path.read_text().replace(old, new))
    done = FIXTURES / f"{name}-0.35.0-done"
    for path in plugin_files(done) if done.is_dir() else {}:
        (into / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(done / path, into / path)


@pytest.mark.parametrize("name", sorted(V35))
def test_each_role_shape_passes_its_own_tests_once_its_findings_are_done(
    tmp_path: Path, name: str
) -> None:
    """With the work the findings name done, each passes its own tests
    against this SDK: migrated on from 0.35.0 to it, as `meridian plugin
    migrate` would take it (from 0.36.0 a licence_default is its terms in
    words, ruling 1032)."""
    migrated(f"{name}-0.34.0", "0.34.0", "0.35.0", tmp_path)
    by_hand_done(name, tmp_path)
    onward = migrate(plugin_files(tmp_path), "0.35.0", SDK)
    for path, text in onward.files.items():
        (tmp_path / path).write_text(text)
    own_tests_pass(tmp_path)


@pytest.mark.parametrize("name", sorted(V35))
def test_each_role_shapes_by_hand_work_leaves_nothing_by_hand(
    tmp_path: Path, name: str
) -> None:
    """The recorded by-hand work is the whole of it: migrated again, the done
    plugin is left as it is, with nothing left by hand."""
    migrated(f"{name}-0.34.0", "0.34.0", "0.35.0", tmp_path)
    by_hand_done(name, tmp_path)
    result = migrate(plugin_files(tmp_path), "0.34.0", "0.35.0")
    assert result.files == {}
    assert left_by_hand(result) == []


def test_a_data_feeds_own_handlers_leave_its_receive_call() -> None:
    """SDK 0.35.1 (the plugin pilot's kalshi): a feed's `on_want` and
    `on_withdrawn` handed to `receive` are dropped as a Trader's are -- the
    feed is a data role class, hearing them by itself -- and the call with
    them; 0.35.0 left the call naming them by hand."""
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["data"]\n',
        "src/p/__main__.py": textwrap.dedent(
            """\
            import meridian
            from meridian.roles.data.event_contracts import ContractMap, Feed

            async def hear(plugin, feed):
                await plugin.receive(
                    observations_wanted=feed.on_want, want_withdrawn=feed.on_withdrawn
                )

            async def run(market):
                async with await meridian.connect() as plugin:
                    feed = Feed(plugin, market, ContractMap())
                    await hear(plugin, feed)
            """
        ),
    }
    result = migrate(files, "0.34.0", "0.35.0")
    written = result.files["src/p/__main__.py"]
    assert ".receive(" not in written and "feed = Feed(market, ContractMap())" in written
    rules = {r for step in result.steps for rules in step.rewrote.values() for r in rules}
    assert {"sdk-handlers-dropped", "common-logic-renamed"} <= rules
    assert [rule for rule, _, _ in left_by_hand(result)] == ["connect-to-run"]


def test_a_recorders_receive_outside_the_tests_hears_the_class() -> None:
    """SDK 0.35.1 (the plugin pilot's kalshi preview): a recorder's `receive`
    in the plugin's own code, handing it a feed's handlers, becomes the
    recorder hearing the feed, which 0.35.0 left by hand."""
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["data"]\n',
        "src/p/preview.py": textwrap.dedent(
            """\
            from meridian.roles.data.event_contracts import ContractMap, Feed
            from meridian.suites import Recorder

            async def worked(market):
                lake = Recorder("p")
                feed = Feed(lake, market, ContractMap())
                await lake.receive(observations_wanted=feed.on_want)
                return feed
            """
        ),
    }
    result = migrate(files, "0.34.0", "0.35.0")
    written = result.files["src/p/preview.py"]
    assert "feed = lake.bind(Feed(market, ContractMap()))" in written
    assert "await lake.hear(feed)" in written and ".receive(" not in written
    assert left_by_hand(result) == []


def test_an_e2e_stand_ins_act_on_the_connection_is_judged_by_its_own_roles() -> None:
    """SDK 0.35.1 (the plugin pilot's kalshi): an e2e reader beside a data
    plugin is a plugin of its own, reading as `reporting`; its acts were
    judged by the data plugin's [tool.meridian] roles ("no role it
    declares"). The plugin's own files still are."""
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["data"]\n',
        "e2e/reader.py": textwrap.dedent(
            """\
            import meridian
            from meridian import Page

            PAGES = [Page("/", "Rows", levels=["read"], roles=["reporting"])]

            class Reader:
                async def read(self):
                    await self.plugin.list_prices(subjects=[])
                    await self.plugin.list_quotes(subjects=[])
            """
        ),
        "src/p/work.py": textwrap.dedent(
            """\
            import meridian

            class Work:
                async def read(self, plugin: meridian.Plugin):
                    await plugin.list_prices(subjects=[])
            """
        ),
    }
    result = migrate(files, "0.34.0", "0.35.0")
    said = {
        (path, line): text
        for _, f in result.by_hand
        for path, line, text in [(f.file, f.line, f.found)]
    }
    assert "[list_prices: reporting; an e2e stand-in" in said[("e2e/reader.py", 8)]
    assert "[list_quotes: no role it names; an e2e stand-in" in said[("e2e/reader.py", 9)]
    assert said[("src/p/work.py", 5)].endswith("[list_prices: no role it declares]")


def test_a_class_given_two_roles_events_or_a_lambda_is_left_by_hand() -> None:
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["data", "signal"]\n',
        "src/p/__main__.py": textwrap.dedent(
            """\
            import meridian
            from .work import Work

            async def run():
                async with await meridian.connect() as plugin:
                    work = Work(plugin)
                    await plugin.receive(want_withdrawn=work.gone, trades_recorded=work.trade)
                    await plugin.receive(observations_wanted=lambda heard: None)
            """
        ),
        "src/p/work.py": textwrap.dedent(
            """\
            class Work:
                def __init__(self, plugin):
                    self.plugin = plugin

                async def gone(self, heard): ...

                async def trade(self, heard): ...
            """
        ),
    }
    result = migrate(files, "0.34.0", "0.35.0")
    assert result.files == {}
    assert left_by_hand(result) == [
        ("connect-to-run", "src/p/__main__.py", 5),
        ("receive-not-rewritten", "src/p/__main__.py", 7),
        ("receive-not-rewritten", "src/p/__main__.py", 8),
    ]


def test_a_role_class_missing_a_required_event_is_named() -> None:
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["connectivity"]\n',
        "src/p/desk.py": textwrap.dedent(
            """\
            from meridian.roles import connectivity

            class Desk(connectivity.Role):
                async def on_placement_updated(self, heard): ...
            """
        ),
    }
    result = migrate(files, "0.34.0", "0.35.0")
    assert left_by_hand(result) == [("required-event-missing", "src/p/desk.py", 3)]


def test_the_steps_role_surfaces_are_0_35s() -> None:
    """The step's record of each role's surface is the generated bases' as
    0.35.0 carries them."""
    if not SDK.startswith("0.35."):
        pytest.skip("the step's surfaces are 0.35.0's; later releases may add rows")
    import importlib

    from meridian.migrations.to_0_35_0.rewrite import SURFACES
    from meridian.roles._generated import ROLES

    for role in ROLES:
        base = importlib.import_module(f"meridian.roles._generated.{role}").Role
        assert SURFACES[role]["events"] == dict(base.EVENTS)
        assert SURFACES[role]["required"] == sorted(base.REQUIRED)
        assert SURFACES[role]["acts"] == list(base.ACTS)


# ── Held to the framework's rules ────────────────────────────────────────


@pytest.mark.parametrize(
    ("fixture", "source", "target"),
    [
        ("desk-0.5.0", "0.5.0", "0.7.0"),
        ("snaptrade-0.6.1", "0.6.1", "0.7.0"),
        ("listed-0.33.5", "0.33.5", "0.34.0"),
        # From meridian 0.1.55, whose check takes `meridian.run(` and fails a
        # declared role with no class registered (ruling 1015).
        ("lake-0.34.0", "0.34.0", "0.35.0"),
        ("quote-0.34.0", "0.34.0", "0.35.0"),
        ("broker-0.34.0", "0.34.0", "0.35.0"),
        ("reader-0.34.0", "0.34.0", "0.35.0"),
        ("equities-0.34.0", "0.34.0", "0.35.0"),
    ],
)
def test_each_migrated_plugin_passes_plugin_check(
    tmp_path: Path, fixture: str, source: str, target: str
) -> None:
    """`meridian plugin check --run-tests` over each, migrated and with the
    work its findings name done (`by_hand_done`): a plugin `meridian plugin
    migrate` moved and a person finished passes the framework's check. `make
    check-migrations` installs the command line and requires this; elsewhere
    it is skipped without it."""
    meridian = shutil.which("meridian")
    if meridian is None:
        if os.environ.get("MERIDIAN_PLUGIN_CHECK") == "required":
            pytest.fail("meridian is not installed, and make check-migrations requires it")
        pytest.skip("meridian is not installed; make check-migrations runs this")
    migrated(fixture, source, target, tmp_path)
    if target == "0.35.0":
        by_hand_done(fixture.rsplit("-", 1)[0], tmp_path)
        # On to this SDK, as `meridian plugin migrate` takes it: its tests
        # run against this SDK (from 0.36.0 a licence_default is words).
        onward = migrate(plugin_files(tmp_path), "0.35.0", SDK)
        for path, text in onward.files.items():
            (tmp_path / path).write_text(text)
    ran = subprocess.run(
        [meridian, "plugin", "check", "--run-tests", "--dir", str(tmp_path)],
        env={**os.environ, "PYTHONPATH": str(tmp_path / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr


# ── The rewrites, one form at a time ─────────────────────────────────────


def one(text: str, frm: str, to: str, path: str = "src/p/x.py") -> migrations.Result:
    return migrate({path: textwrap.dedent(text)}, frm, to)


def test_a_file_that_does_not_parse_is_left_and_said() -> None:
    result = one("import meridian\ndef broken(:\n", "0.5.0", "0.6.0")
    assert result.files == {}
    assert left_by_hand(result) == [("unreadable", "src/p/x.py", 2)]


def test_a_comparison_keeps_its_meaning_where_it_lands() -> None:
    result = one(
        """\
        import meridian

        def same(caller: meridian.Caller, a: str, b: bool) -> bool:
            return b == any(a in held.read for held in caller.access)
        """,
        "0.5.0",
        "0.6.0",
    )
    assert "return b == (a in caller.read)" in result.files["src/p/x.py"]


def test_a_file_that_does_not_use_the_sdk_is_not_touched() -> None:
    text = "def f(x):\n    return any(a in h.read for h in x.access)\n"
    assert one(text, "0.5.0", "0.7.0").files == {}


def test_words_of_an_error_that_is_not_meridians_are_left_by_hand() -> None:
    result = one(
        """\
        import meridian

        def unlinked(err: Exception) -> bool:
            return "is not linked" in str(err)
        """,
        "0.6.1",
        "0.7.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [("not-linked-by-text", "src/p/x.py", 4)]


def test_a_handler_before_another_is_not_narrowed() -> None:
    # A CallFailed it re-raised went past the handler after it; narrowed, the
    # handler after it would catch it.
    result = one(
        """\
        from meridian import CallFailed

        async def f(plugin):
            try:
                await plugin.record_holding()
            except CallFailed as err:
                if "is not linked" in err.detail:
                    return "unlinked"
                raise
            except Exception:
                return "failed"
        """,
        "0.6.1",
        "0.7.0",
    )
    text = result.files["src/p/x.py"]
    assert "from meridian import CallFailed, NotLinked" in text
    assert "except CallFailed as err:" in text
    assert "if isinstance(err, NotLinked):" in text


def test_a_tag_still_named_is_left_by_hand() -> None:
    result = one(
        """\
        from meridian import Caller, TagAccess

        def build(held: tuple[TagAccess, ...]) -> Caller:
            return Caller(subject="u", display_name="U", access=held, header="h")
        """,
        "0.5.0",
        "0.6.0",
    )
    assert result.files == {}
    assert {rule for rule, _, _ in left_by_hand(result)} == {"tag-access"}


def test_an_asset_class_in_another_case_becomes_its_ruled_spelling() -> None:
    result = one(
        """\
        import meridian

        async def miss(plugin: meridian.Plugin) -> None:
            await plugin.report_missing_instrument(source="s", asset_class="EQUITY")
            await plugin.report_missing_instrument(source="s", asset_class='Crypto_Asset')
            await plugin.report_missing_instrument(source="s", asset_class="asset_class_fund")
            await plugin.report_missing_instrument(source="s", asset_class="equity")
            await plugin.report_missing_instrument(source="s", asset_class="ASSET_CLASS_CASH")
        """,
        "0.8.0",
        "0.9.0",
    )
    text = result.files["src/p/x.py"]
    assert 'asset_class="equity")' in text
    assert "asset_class='crypto_asset')" in text
    assert 'asset_class="fund")' in text
    assert 'asset_class="ASSET_CLASS_CASH")' in text  # already the enum's name
    (step,) = result.steps
    assert step.rewrote == {"src/p/x.py": {"asset-class-spelling": 3}}
    assert left_by_hand(result) == []


def test_no_asset_class_is_left_as_it_is() -> None:
    result = one(
        """\
        import meridian

        async def miss(plugin: meridian.Plugin) -> None:
            await plugin.report_missing_instrument(source="s", asset_class="")
            await plugin.report_missing_instrument(source="s", asset_class=None)
            await plugin.report_missing_instrument(
                source="s", asset_class=meridian.AssetClass.ASSET_CLASS_FUND
            )
        """,
        "0.8.0",
        "0.9.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == []


def test_an_asset_class_that_names_no_class_is_left_by_hand() -> None:
    # An ETF is a type within fund, and which class a vendor's kind is in is
    # the person's to say: nothing is guessed.
    result = one(
        """\
        import meridian

        async def miss(plugin: meridian.Plugin) -> None:
            await plugin.report_missing_instrument(source="s", asset_class="etf")
            await plugin.report_missing_instrument(
                source="s",
                asset_class="Bond",
            )
        """,
        "0.8.0",
        "0.9.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [
        ("asset-class-unknown", "src/p/x.py", 4),
        ("asset-class-unknown", "src/p/x.py", 7),
    ]
    assert result.by_hand[0][1].found == (
        'await plugin.report_missing_instrument(source="s", asset_class="etf")'
    )


def test_an_asset_class_the_migration_cannot_read_is_left_by_hand() -> None:
    result = one(
        """\
        import meridian

        KINDS = {"ETF": "fund"}

        async def miss(plugin: meridian.Plugin, kind: str) -> None:
            await plugin.report_missing_instrument(source="s", asset_class=kind)
            await plugin.report_missing_instrument(source="s", asset_class=KINDS[kind])
        """,
        "0.8.0",
        "0.9.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [
        ("asset-class-computed", "src/p/x.py", 6),
        ("asset-class-computed", "src/p/x.py", 7),
    ]


def test_an_asset_class_outside_a_report_or_the_sdk_is_not_touched() -> None:
    # Another call's asset_class is somebody else's field.
    elsewhere = one(
        """\
        import meridian

        def record(book, kind: str) -> None:
            book.define(asset_class="EQUITY")
            book.define(asset_class="etf")
            book.define(asset_class=kind)
        """,
        "0.8.0",
        "0.9.0",
    )
    assert elsewhere.files == {} and left_by_hand(elsewhere) == []
    # A file that does not use the SDK is not read.
    unused = one(
        """\
        async def miss(plugin, kind: str) -> None:
            await plugin.report_missing_instrument(asset_class="EQUITY")
            await plugin.report_missing_instrument(asset_class=kind)
        """,
        "0.8.0",
        "0.9.0",
    )
    assert unused.files == {} and left_by_hand(unused) == []


def test_admin_pages_become_pages_at_admin() -> None:
    result = one(
        """\
        import meridian
        from meridian import Interface, Page

        TABS = (
            meridian.Page("/admin/connections", "Connections"),
            Page(
                '/admin/accounts',
                'Account links',
            ),
            Page("/admin/x", "X", levels=["admin", "write"]),
        )

        def interface(port: int) -> Interface:
            return meridian.Interface(port=port, title="SnapTrade", admin_pages=TABS)
        """,
        "0.9.0",
        "0.10.0",
    )
    text = result.files["src/p/x.py"]
    assert 'meridian.Page("/admin/connections", "Connections", levels=["admin"]),' in text
    assert (
        "    Page(\n"
        "        '/admin/accounts',\n"
        "        'Account links',\n"
        "        levels=['admin'],\n"
        "    ),\n"
    ) in text
    assert 'Page("/admin/x", "X", levels=["admin", "write"])' in text, "already levelled"
    assert 'meridian.Interface(port=port, title="SnapTrade", pages=TABS)' in text
    (step,) = result.steps
    assert step.rewrote == {"src/p/x.py": {"page-at-admin": 2, "admin-pages-keyword": 1}}
    assert left_by_hand(result) == []


def test_who_was_served_the_admin_pages_is_left_by_hand() -> None:
    # SnapTrade's shape at 0.9.0: its pages served to a deployment admin, and
    # a test reading the declaration's admin pages.
    result = migrate(
        {
            "src/p/page.py": textwrap.dedent(
                """\
                import meridian

                PAGES = (meridian.Page("/admin", "Setup"),)

                def is_administrator(caller: meridian.Caller) -> bool:
                    return caller.deployment_admin is True
                """
            ),
            "src/p/__main__.py": textwrap.dedent(
                """\
                import meridian
                from .page import PAGES

                def interface() -> meridian.Interface:
                    return meridian.Interface(8000, "P", PAGES)
                """
            ),
            "tests/test_page.py": textwrap.dedent(
                """\
                import meridian
                from p.page import PAGES

                def test_declared() -> None:
                    declared = meridian.Interface(8000, "P", admin_pages=PAGES)._declared()
                    assert len(declared.admin_pages) == 1
                    assert meridian.Caller("s", "d", "h", deployment_admin=True)
                """
            ),
        },
        "0.9.0",
        "0.10.0",
    )
    assert left_by_hand(result) == [
        ("admin-pages-positional", "src/p/__main__.py", 5),
        ("deployment-admin-gate", "src/p/page.py", 6),
        ("admin-pages-read", "tests/test_page.py", 6),
    ]
    assert 'meridian.Page("/admin", "Setup", levels=["admin"])' in result.files["src/p/page.py"]
    assert "pages=PAGES" in result.files["tests/test_page.py"]


def test_a_page_outside_the_sdk_is_not_touched() -> None:
    result = one(
        """\
        import meridian
        from http.server import BaseHTTPRequestHandler

        class Page(BaseHTTPRequestHandler):
            pass

        def make(path: str, title: str) -> Page:
            return Page(path, title)
        """,
        "0.9.0",
        "0.10.0",
    )
    assert result.files == {} and left_by_hand(result) == []


def test_a_statements_flat_figures_become_one_set_with_no_segment() -> None:
    result = one(
        """\
        from decimal import Decimal

        from meridian import Money

        async def opened(plugin, account):
            await plugin.record_holdings_statement(
                source="snaptrade",
                external_account_id=account,
                buying_power=Money(Decimal("25000.00"), "USD"),
                maintenance_excess=None,
                expected_rows=4,
            )
        """,
        "0.11.0",
        "0.12.0",
    )
    text = result.files["src/p/x.py"]
    assert "from meridian import Money, StatementFigures" in text
    assert (
        '        figures=[StatementFigures(segment="", '
        'buying_power=Money(Decimal("25000.00"), "USD"), maintenance_excess=None)],\n'
    ) in text
    assert "expected_rows=4,\n" in text
    (step,) = result.steps
    assert step.rewrote == {"src/p/x.py": {"statement-flat-figures": 1}}
    assert left_by_hand(result) == []


def test_a_statement_naming_no_external_account_is_left_by_hand() -> None:
    result = one(
        """\
        import meridian

        async def opened(plugin: meridian.Plugin) -> None:
            await plugin.record_holdings_statement(source="snaptrade", expected_rows=0)
        """,
        "0.11.0",
        "0.12.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [("statement-external-account", "src/p/x.py", 4)]


def test_the_runner_reads_stdin_and_writes_what_changed() -> None:
    given = {"files": plugin_files(FIXTURES / "snaptrade-0.6.1")}
    ran = subprocess.run(
        [sys.executable, "-m", "meridian.migrations", "--from", "0.6.1", "--to", "0.7.0"],
        input=json.dumps(given),
        capture_output=True,
        text=True,
        check=True,
    )
    said = json.loads(ran.stdout)
    assert said["from"] == "0.6.1" and said["to"] == "0.7.0"
    assert sorted(said["files"]) == [
        "src/snaptrade/contract.py",
        "tests/test_contract.py",
    ]
    assert said["by_hand"] == []
    assert [step["to"] for step in said["steps"]] == ["0.7.0"]


def test_the_runner_refuses_versions_it_has_no_steps_between() -> None:
    ran = subprocess.run(
        [sys.executable, "-m", "meridian.migrations", "--from", "0.3.0", "--to", "0.7.0"],
        input='{"files": {}}',
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == 2 and "no migration is recorded from 0.3.0" in ran.stderr


def test_a_resolve_results_placeholder_becomes_minted() -> None:
    result = one(
        """\
        import meridian

        async def resolved(plugin: meridian.Plugin, identifiers, counted) -> str:
            answer = await plugin.resolve_identifier(identifiers=identifiers, as_of_ns=0)
            counted.placeholders += 1 if answer.placeholder else 0
            return answer.instrument_id
        """,
        "0.14.0",
        "0.15.0",
    )
    text = result.files["src/p/x.py"]
    assert "1 if answer.minted else 0" in text
    assert "counted.placeholders" in text, "a name not bound to a resolve is left alone"
    (step,) = result.steps
    assert step.rewrote == {"src/p/x.py": {"resolve-minted": 1}}
    assert left_by_hand(result) == []


def test_a_book_positions_placeholder_is_left_by_hand() -> None:
    result = one(
        """\
        import meridian

        def flagged(position: meridian.BookPosition) -> bool:
            return position.placeholder
        """,
        "0.14.0",
        "0.15.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [("position-placeholder", "src/p/x.py", 4)]


def test_what_contract_v11_deprecates_is_found_and_left_by_hand() -> None:
    # 0.16.0: the venue's type, "also counted in cash" and the currency flag
    # are each replaced by the plugin's own conversion, so each is found.
    result = one(
        """\
        import meridian

        async def report(plugin: meridian.Plugin) -> None:
            await plugin.report_external_accounts(accounts=[meridian.ExternalAccount(
                external_account_id="A", venue_account_type="MARGIN")])
            await plugin.record_holding(statement_id="S", instrument_id="I", quantity=1,
                                        also_counted_in_cash=True, currency_assumed=True)
        """,
        "0.15.0",
        "0.16.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [
        ("account-kind", "src/p/x.py", 5),
        ("counted-once", "src/p/x.py", 7),
        ("currency-provenance", "src/p/x.py", 7),
    ]


def test_a_read_of_meridian_figures_moved_bounds_is_found_and_left_by_hand() -> None:
    # 0.16.0: MOST_FIGURES and LONGEST_* are meridian.bounds' now.
    result = one(
        """\
        import meridian
        from meridian import figures
        from meridian.figures import LONGEST_WHY

        def short(why: str) -> str:
            return why[: LONGEST_WHY - 1] if len(why) > figures.MOST_FIGURES else why
        """,
        "0.15.0",
        "0.16.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [
        ("figures-bounds", "src/p/x.py", 3),
        ("figures-bounds", "src/p/x.py", 6),
    ]


def test_a_changing_route_with_no_typed_record_is_found_and_left_by_hand() -> None:
    # 0.17.0: a route that changes something is derived as a tool only from
    # its record (params=), which is the plugin's to write.
    result = one(
        """\
        import meridian

        pages = meridian.Pages("Desk")

        @pages.route("/sync", levels="write", methods=["POST"])
        async def sync(request: meridian.Request) -> str: ...

        @pages.route("/typed", levels="write", methods=["POST"], params=object)
        async def typed(request: meridian.Request) -> str: ...

        @pages.route("/file", levels="write", methods=["POST"], tool=False, why="a file")
        async def upload(request: meridian.Request) -> str: ...

        @pages.page("/", "Home", levels=["read"])
        async def home(request: meridian.Request) -> str: ...
        """,
        "0.16.0",
        "0.17.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [("typed-route", "src/p/x.py", 5)]


def test_the_renamed_roles_are_rewritten_where_a_plugin_names_a_role() -> None:
    # Contract v20 (the product owner, 2026-10-10): dgm is data, ccm is
    # connectivity and match is confirmation, wherever a plugin names a role;
    # "match" anywhere else is an English word and stays.
    result = one(
        """\
        import meridian
        from meridian.suites import run

        pages = meridian.Pages("Prices")

        @pages.page("/", "Connection", levels="admin", roles=["dgm"])
        async def connection(request):
            mode = "match" if request.caller.level_for("ccm") else ""
            return mode

        def test_suite():
            assert run("dgm", {}).passed
        """,
        "0.23.0",
        "0.24.0",
    )
    text = result.files["src/p/x.py"]
    assert 'roles=["data"]' in text
    assert 'level_for("connectivity")' in text
    assert 'run("data", {})' in text
    assert 'mode = "match"' in text
    (step,) = result.steps
    assert step.rewrote == {"src/p/x.py": {"role-renamed": 3}}
    assert left_by_hand(result) == []


def test_the_renamed_roles_are_rewritten_in_the_plugins_metadata() -> None:
    files = {
        "pyproject.toml": '[project]\nname = "p"\n\n[tool.meridian]\nroles = ["dgm"]\n'
        'interface = true\n\n[tool.other]\nroles = ["dgm"]\n'
    }
    result = migrations.migrate(files, "0.23.0", "0.24.0")
    text = result.files["pyproject.toml"]
    assert '[tool.meridian]\nroles = ["data"]' in text
    assert '[tool.other]\nroles = ["dgm"]' in text


# ── 0.27.0 to 0.28.0: one ID (contract v24, the one-ID spec's requirement 20) ─


def test_a_records_lcl_prefix_test_becomes_its_provisional_mark() -> None:
    result = one(
        """\
        import meridian

        async def local(plugin: meridian.Plugin, instrument_id: str) -> bool:
            answer = await plugin.resolve_instrument(instrument_id=instrument_id)
            found = await plugin.resolve_identifier(identifiers=[])
            if not answer.instrument.instrument_id.startswith("LCL-"):
                return False
            return found.instrument_id.startswith("LCL-") or "INS-" in instrument_id
        """,
        "0.27.0",
        "0.28.0",
    )
    text = result.files["src/p/x.py"]
    assert "if not answer.instrument.provisional:" in text
    assert "return found.provisional or" in text
    assert "startswith" not in text
    (step,) = result.steps
    assert step.rewrote == {"src/p/x.py": {"lcl-prefix-provisional": 2}}
    assert left_by_hand(result) == []


def test_an_ids_prefix_tested_with_no_record_at_hand_is_left_by_hand() -> None:
    # sample-operations' stand-in store, as it was at 0.12.0.
    result = one(
        """\
        import meridian

        def resolve(self, instrument_id: str) -> object:
            if instrument_id.startswith("LCL-"):
                return self.minted.get(instrument_id)
            if instrument_id[:4] == "LCL-" or "LCL-" in instrument_id:
                return None
            return RECORDS.get(instrument_id, "LCL-0001")
        """,
        "0.27.0",
        "0.28.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [
        ("lcl-prefix-tested", "src/p/x.py", 4),
        ("lcl-prefix-tested", "src/p/x.py", 6),
    ]


def test_the_platforms_id_read_from_open_meridian_becomes_the_instrument_id() -> None:
    result = one(
        """\
        import meridian

        def platform_id(record: meridian.InstrumentRecord) -> str:
            return next(
                (i.value for i in record.identifiers if i.scheme == "open_meridian"), ""
            )

        def must(answer) -> str:
            held = answer.instrument
            return next(x.value for x in held.identifiers if "open_meridian" == x.scheme)
        """,
        "0.27.0",
        "0.28.0",
    )
    text = result.files["src/p/x.py"]
    assert '("" if record.provisional else record.instrument_id)' in text
    assert "return held.instrument_id" in text
    (step,) = result.steps
    assert step.rewrote == {"src/p/x.py": {"open-meridian-instrument-id": 2}}
    assert left_by_hand(result) == []


def test_open_meridian_written_or_read_another_way_is_left_by_hand() -> None:
    result = one(
        """\
        import meridian

        KEY = meridian.Identifier(scheme="open_meridian", value="INS-1")

        def ids(record) -> list[str]:
            return [i.value for i in record.identifiers if i.scheme == "open_meridian"]
        """,
        "0.27.0",
        "0.28.0",
    )
    assert result.files == {}
    assert left_by_hand(result) == [
        ("open-meridian-read", "src/p/x.py", 3),
        ("open-meridian-read", "src/p/x.py", 6),
    ]


def test_a_tests_lcl_suite_id_becomes_the_platforms() -> None:
    files = {
        "tests/test_suite.py": textwrap.dedent(
            """\
            from meridian.suites import Recorder, run

            def test_held() -> None:
                assert held == "LCL-suite-3"
                assert [f"LCL-suite-{n}" for n in range(2)] == ids
                assert other == "LCL-0001"
            """
        ),
        # Not a test: the plugin's own code is not the suite's fixtures.
        "src/p/x.py": 'import meridian\nKEEP = "LCL-suite-3"\n',
    }
    result = migrations.migrate(files, "0.27.0", "0.28.0")
    text = result.files["tests/test_suite.py"]
    assert 'held == "INS-suite-3"' in text
    assert 'f"INS-suite-{n}"' in text
    assert 'other == "LCL-0001"' in text
    assert "src/p/x.py" not in result.files
    (step,) = result.steps
    assert step.rewrote == {"tests/test_suite.py": {"suite-fixture-ins": 2}}


def test_a_file_not_using_the_sdk_keeps_its_prefix_tests() -> None:
    text = 'def f(x):\n    return x.instrument_id.startswith("LCL-")\n'
    result = one(text, "0.27.0", "0.28.0")
    assert result.files == {}
    assert left_by_hand(result) == []


# ── 0.28.0 to 0.29.0: the whole declaration; connectivity's read dropped ──

CONNECTIVITY = """\
[project]
name = "venue"
dependencies = ["open-meridian==0.28.0"]

[tool.meridian]
roles = ["connectivity"]
interface = true
declaration = "venue.declaration:DECLARATION"
"""


def test_a_connectivity_plugins_escape_hatch_read_and_case_are_removed() -> None:
    files = {
        "pyproject.toml": CONNECTIVITY,
        "src/venue/route.py": textwrap.dedent(
            """\
            import meridian

            async def before_placing(plugin: meridian.Plugin) -> None:
                await plugin.read_local_record_orders()

            async def on_start(plugin: meridian.Plugin) -> None:
                await plugin.read_local_record_orders()
                await plugin.report(healthy=True, detail="started")
            """
        ),
        "tests/test_suite.py": textwrap.dedent(
            """\
            from meridian.suites import run

            async def reads(recorder):
                await recorder.read_local_record_orders()

            def test_suite():
                assert run(
                    "connectivity",
                    {
                        "acknowledges-a-placement-naming-it": reads,
                        "reads-whether-orders-may-name-local-records": reads,
                    },
                ).passed
            """
        ),
    }
    result = migrate(files, "0.28.0", "0.29.0")
    route = result.files["src/venue/route.py"]
    assert "read_local_record_orders" not in route
    assert "async def before_placing(plugin: meridian.Plugin) -> None:\n    pass\n" in route
    assert 'await plugin.report(healthy=True, detail="started")' in route
    test = result.files["tests/test_suite.py"]
    assert "reads-whether-orders-may-name-local-records" not in test
    assert '"acknowledges-a-placement-naming-it": reads,' in test
    (step,) = result.steps
    assert step.rewrote == {
        "src/venue/route.py": {"escape-hatch-read-dropped": 2},
        "tests/test_suite.py": {"escape-hatch-read-dropped": 1, "escape-hatch-case-dropped": 1},
    }
    assert left_by_hand(result) == []
    compile(route, "route.py", "exec")
    compile(test, "test_suite.py", "exec")


def test_a_read_whose_answer_is_used_is_left_by_hand() -> None:
    files = {
        "pyproject.toml": CONNECTIVITY,
        "src/venue/route.py": textwrap.dedent(
            """\
            import meridian

            async def allowed(plugin: meridian.Plugin) -> bool:
                held = await plugin.read_local_record_orders()
                return held.allowed
            """
        ),
    }
    result = migrate(files, "0.28.0", "0.29.0")
    assert result.files == {}
    assert left_by_hand(result) == [("escape-hatch-read-kept", "src/venue/route.py", 4)]


def test_a_role_that_keeps_the_read_keeps_it() -> None:
    for roles in ('["oms"]', '["connectivity", "ems"]', "[]"):
        files = {
            "pyproject.toml": CONNECTIVITY.replace('["connectivity"]', roles),
            "src/venue/route.py": "import meridian\n\n\nasync def f(plugin):\n"
            "    await plugin.read_local_record_orders()\n",
        }
        result = migrate(files, "0.28.0", "0.29.0")
        assert result.files == {}, roles
        assert left_by_hand(result) == [], roles


def test_what_connect_names_beside_the_declaration_is_left_by_hand() -> None:
    files = {
        "pyproject.toml": CONNECTIVITY.replace(
            'declaration = "venue.declaration:DECLARATION"\n', ""
        ),
        "src/venue/__main__.py": textwrap.dedent(
            """\
            import meridian

            async def run() -> None:
                async with await meridian.connect(
                    interface=meridian.Interface(port=8000, title="Venue"),
                    reads_external_accounts=True,
                ) as plugin:
                    pass

            async def again() -> None:
                async with await meridian.connect(declaration=None) as plugin:
                    pass
            """
        ),
    }
    result = migrate(files, "0.28.0", "0.29.0")
    assert result.files == {}
    assert left_by_hand(result) == [
        ("declaration-not-named", "pyproject.toml", 5),
        ("connect-names-the-declaration", "src/venue/__main__.py", 4),
    ]
    (step,) = result.steps
    assert step.migration.breaking


MOUNTED = """\
ARG BASE=ghcr.io/open-meridian/plugin-python:0.29.0
FROM ${BASE}
WORKDIR /plugin
# Installed from a mount rather than copied.
RUN --mount=type=bind,target=/tmp/src,rw pip install --no-cache-dir /tmp/src
USER 65532
CMD ["venue"]
"""


def _declared(documentation: str | None) -> str:
    named = f", documentation={documentation!r}" if documentation is not None else ""
    return f"import meridian\n\nDECLARATION = meridian.Declaration(settings=None{named})\n"


@pytest.mark.parametrize(
    ("dockerfile", "documentation", "left"),
    [
        # The plugin agent's finding (2026-10-16): all 13 first-party plugins
        # installed only the package, so their images held no docs/.
        (MOUNTED, "docs", True),
        (MOUNTED, None, True),
        (MOUNTED.replace("USER", "COPY docs/ docs/\nUSER"), "docs", False),
        (MOUNTED.replace("USER", "COPY ./docs ./docs\nUSER"), "./docs/", False),
        (MOUNTED.replace("USER", 'COPY ["docs", "docs/"]\nUSER'), None, False),
        (MOUNTED.replace("USER", "COPY --chown=65532 . .\nUSER"), "docs", False),
        (MOUNTED.replace("USER", "COPY src \\\n     docs/ ./\nUSER"), "docs", False),
        (MOUNTED.replace("USER", "COPY docs/ docs/\nUSER"), "manual", True),
        (MOUNTED.replace("USER", "COPY manual/ manual/\nUSER"), "manual", False),
        (MOUNTED.replace("USER", "COPY share/ share/\nUSER"), "share/docs", False),
        # A copy in an earlier stage is not the image's.
        ("FROM python AS build\nCOPY . .\n" + MOUNTED, "docs", True),
        # A copy from another stage may carry it; what that stage holds is
        # not read here.
        (MOUNTED.replace("USER", "COPY --from=build /plugin /plugin\nUSER"), "docs", False),
    ],
)
def test_a_dockerfile_copying_no_documentation_is_left_by_hand(
    dockerfile: str, documentation: str | None, left: bool
) -> None:
    files = {
        "pyproject.toml": CONNECTIVITY,
        "Dockerfile": dockerfile,
        "src/venue/declaration.py": _declared(documentation),
    }
    result = migrate(files, "0.28.0", "0.29.0")
    assert result.files == {}
    stage = dockerfile.splitlines().index("FROM ${BASE}") + 1
    assert left_by_hand(result) == (
        [("docs-not-in-image", "Dockerfile", stage)] if left else []
    )


def test_a_plugin_sending_no_dockerfile_is_not_held_to_one() -> None:
    # A meridian before 0.1.46 sends the Python and pyproject.toml alone.
    files = {"pyproject.toml": CONNECTIVITY, "src/venue/declaration.py": _declared("docs")}
    assert left_by_hand(migrate(files, "0.28.0", "0.29.0")) == []


# ── 0.29.0 to 0.30.0: the copied middle layer onto the SDK's helpers ─────

PAIRS = "The same module in plugin-one and plugin-two.\n"
CONTRACTS_PAIR = "The same module in plugin-ka and plugin-pm.\n"


def _copied_pairs() -> dict[str, str]:
    """A pairs plugin's copied layer, in the few lines that make each what it
    is: its marker and its own definitions."""
    return {
        "pyproject.toml": '[project]\nname = "one"\ndependencies = ["open-meridian==0.29.0"]\n',
        "src/one/__init__.py": "",
        "src/one/market.py": f'"""Values. {PAIRS}"""\nclass Listed: ...\nclass Candle: ...\n',
        "src/one/products.py": f'"""The map. {PAIRS}"""\nclass ProductMap: ...\n',
        "src/one/raw.py": (
            f'"""Raw. {PAIRS}"""\nKIND = "answers"\nLABEL = "Raw answers"\nWINDOW_DAYS = 9\n'
            "class RawStore: ...\n"
        ),
        "src/one/dgm.py": (
            f'"""Work. {PAIRS}"""\nfrom .products import ProductMap\n'
            "from .stream import Stream\nclass Dgm: ...\n"
        ),
        "src/one/page.py": f'"""Pages. {PAIRS}"""\n',
        "src/one/stream.py": (
            f'"""A stream. {PAIRS}"""\nfrom fake_venues import Keeper as Stream  # noqa: F401\n'
        ),
        "src/one/preview.py": "def go(feed):\n    feed.stream.connect = None\n",
        "src/one/convert.py": '"""Its own: The same words, not a copy."""\nclass Listed: ...\n',
        "tests/test_suite.py": '"""The same file in plugin-one and plugin-two (held)."""\n',
    }


def test_a_pairs_plugins_copied_modules_become_re_exports_of_the_sdk() -> None:
    files = _copied_pairs()
    result = migrate(files, "0.29.0", "0.30.0")
    assert set(result.files) == {
        "src/one/market.py", "src/one/products.py", "src/one/raw.py", "src/one/dgm.py",
    }  # fmt: skip
    assert all(t.startswith('"""Moved into the SDK (open-meridian 0.30.0)') for t in
               result.files.values())  # fmt: skip
    assert "WINDOW_DAYS = 9" in result.files["src/one/raw.py"]
    assert 'KIND = "answers"' in result.files["src/one/raw.py"]
    assert "stream_factory: StreamFactory | None = Stream" in result.files["src/one/dgm.py"]
    assert left_by_hand(result) == [
        ("suite-same-retired", "pyproject.toml", 0),
        ("re-export-left", "src/one/dgm.py", 1),
        ("re-export-left", "src/one/market.py", 1),
        ("copied-page", "src/one/page.py", 1),
        ("stream-connect-assigned", "src/one/preview.py", 2),
        ("re-export-left", "src/one/products.py", 1),
        ("re-export-left", "src/one/raw.py", 1),
        ("stream-is-the-plugins", "src/one/stream.py", 1),
        ("copied-tests", "tests/test_suite.py", 1),
    ]
    for text in result.files.values():
        compile(text, "<re-export>", "exec")


def test_the_re_exports_run_as_the_modules_they_replace(tmp_path: Path) -> None:
    files = _copied_pairs()
    files.update(migrate(files, "0.29.0", "0.30.0").files)
    for path, text in files.items():
        if path.startswith("src/"):
            (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / path).write_text(text)
    sys.path.insert(0, str(tmp_path / "src"))
    try:
        import importlib

        dgm = importlib.import_module("one.dgm")
        raw = importlib.import_module("one.raw")
        products = importlib.import_module("one.products")
        from fake_venues import pairs_venue
        from meridian.roles.data import pairs
        from meridian.suites import Recorder

        # From 0.35 the feed is a data role class, bound to its connection.
        work = Recorder("one").bind(dgm.Dgm(pairs_venue.market(), products.ProductMap()))
        assert isinstance(work, pairs.Feed) and work.stream_factory is not None
        store = raw.RawStore(tmp_path / "storage")
        assert store.kind == "answers" and raw.WINDOW_DAYS == 9
    finally:
        sys.path.remove(str(tmp_path / "src"))
        for name in [m for m in sys.modules if m == "one" or m.startswith("one.")]:
            del sys.modules[name]


def test_an_event_contract_plugins_copied_modules_become_re_exports() -> None:
    files = {
        "src/ka/market.py": f'"""{CONTRACTS_PAIR}"""\nclass Contract: ...\nclass Cash: ...\n',
        "src/ka/contracts.py": f'"""{CONTRACTS_PAIR}"""\nclass ContractMap: ...\n',
        "src/ka/dgm.py": (
            f'"""{CONTRACTS_PAIR}"""\nfrom .contracts import ContractMap\nclass Dgm: ...\n'
        ),
    }
    result = migrate(files, "0.29.0", "0.30.0")
    assert set(result.files) == set(files)
    assert "Dgm = Feed" in result.files["src/ka/dgm.py"]
    assert (
        "event_contracts import ContractMap as ContractMap"
        in result.files["src/ka/contracts.py"]
    )
    assert "event_contracts import Cash as Cash" in result.files["src/ka/market.py"]


def test_a_plugins_own_modules_of_the_same_names_are_left_alone() -> None:
    files = {
        "pyproject.toml": '[project]\nname = "own"\n',
        "src/own/market.py": '"""Its own market."""\nclass Listed: ...\nclass Candle: ...\n',
        "src/own/raw.py": "class RawStore: ...\n",
        "src/own/dgm.py": "from .products import ProductMap\nclass Dgm: ...\n",
        "src/own/preview.py": "def go(feed):\n    feed.stream.connect = None\n",
    }
    result = migrate(files, "0.29.0", "0.30.0")
    assert result.files == {} and left_by_hand(result) == []


# ── 0.29.0 to 0.30.0: a trading layer onto meridian.roles.connectivity ───

_TRADING = '''"""The connectivity role, in SnapTrade 0.16.0's shape."""
from typing import Protocol
from zoneinfo import ZoneInfo

PRICE_PLACES = 6
MARKET_ZONE = ZoneInfo("Asia/Tokyo")


class Venue(Protocol):
    def accounts(self): ...


class Noted: ...


class Watched: ...


class Trader: ...


def trading_files(base): ...
'''


def _traded() -> dict[str, str]:
    return {
        "pyproject.toml": '[project]\nname = "br"\n',
        "src/br/trading.py": _TRADING,
        "src/br/records.py": "class TradingRead: ...\nclass AccountTrading: ...\n",
        "tests/trading_cases.py": "class Rig:\n    def make(self):\n        return Trader(1)\n",
    }


def test_a_trading_layer_becomes_a_re_export_of_the_sdks_connectivity(tmp_path: Path) -> None:
    files = _traded()
    result = migrate(files, "0.29.0", "0.30.0")
    assert set(result.files) == {"src/br/trading.py"}
    files.update(result.files)
    (tmp_path / "br").mkdir()
    (tmp_path / "br" / "trading.py").write_text(files["src/br/trading.py"])
    sys.path.insert(0, str(tmp_path))
    try:
        import importlib
        from datetime import UTC, datetime
        from decimal import Decimal

        from meridian.roles import connectivity
        from meridian.suites import Recorder

        trading = importlib.import_module("br.trading")
        assert trading.Noted is connectivity.Sent and trading.PRICE_PLACES == 6
        # From 0.35 the Trader is the connectivity role class, bound to its connection.
        trader = Recorder("br").bind(
            trading.Trader(lambda: None, now=lambda: datetime.now(UTC))
        )
        assert isinstance(trader, connectivity.Trader)
        assert str(trader.market_zone) == "Asia/Tokyo" and trader.price_places == 6
        assert trading.fill_price(Decimal(0), None, Decimal(3), Decimal(1)) == (
            Decimal(1),
            False,
        )
        at = datetime(2026, 9, 29, 16, tzinfo=UTC)
        assert str(trading.trade_date_of(at)) == "2026-09-30"
    finally:
        sys.path.remove(str(tmp_path))
        for name in [m for m in sys.modules if m == "br" or m.startswith("br.")]:
            del sys.modules[name]
    assert [(rule, file) for rule, file, _ in left_by_hand(result)] == [
        ("trading-page-onto-sdk", "src/br/records.py"),
        ("trader-re-export-left", "src/br/trading.py"),
        ("trading-rig-onto-sdk", "tests/trading_cases.py"),
    ]


def test_a_trading_layer_whose_zone_is_not_a_constant_is_left_by_hand() -> None:
    files = _traded()
    files["src/br/trading.py"] = _TRADING.replace(
        'MARKET_ZONE = ZoneInfo("Asia/Tokyo")', "MARKET_ZONE = zone_of_the_venue()"
    )
    result = migrate(files, "0.29.0", "0.30.0")
    assert result.files == {}
    assert ("trader-by-hand", "src/br/trading.py", 1) in left_by_hand(result)


def test_a_plugins_own_trader_is_left_alone() -> None:
    files = {
        "src/own/trading.py": "class Trader: ...\nclass Noted: ...\n",
        "src/own/records.py": "class TradingRead: ...\n",
        "tests/cases.py": "class Rig:\n    t = Trader(1)\n",
    }
    result = migrate(files, "0.29.0", "0.30.0")
    assert result.files == {} and left_by_hand(result) == []


# ── 0.30.0 to 0.31.0: contract v26 ───────────────────────────────────────

_DIGEST = "sha256:" + "ab" * 32


def test_a_base_pinned_by_digest_at_an_older_release_drops_its_digest() -> None:
    """Run without `meridian plugin migrate`'s pin move (CLI 0.1.47), the step
    moves the tag offline and drops the digest it cannot read: an old digest
    is never kept under a new tag."""
    dockerfile = (
        f"ARG BASE=ghcr.io/open-meridian/plugin-python:0.30.0@{_DIGEST}\nFROM ${{BASE}}\n"
    )
    result = migrate({"Dockerfile": dockerfile}, "0.30.0", "0.31.0")
    assert result.files["Dockerfile"].splitlines()[0] == (
        "ARG BASE=ghcr.io/open-meridian/plugin-python:0.31.0"
    )
    assert ("base-digest", "Dockerfile", 1) in left_by_hand(result)
    rewrote = {r for step in result.steps for rules in step.rewrote.values() for r in rules}
    assert rewrote == {"base-digest-dropped"}


def test_a_base_the_command_line_moved_with_its_digest_is_left_alone() -> None:
    dockerfile = (
        f"ARG BASE=ghcr.io/open-meridian/plugin-python:0.31.0@{_DIGEST}\nFROM ${{BASE}}\n"
    )
    result = migrate({"Dockerfile": dockerfile}, "0.30.0", "0.31.0")
    assert result.files == {}
    assert [rule for rule, _, _ in left_by_hand(result)] == []


def test_a_role_suite_v26_adds_cases_to_is_left_to_map() -> None:
    files = {
        "tests/test_suite.py": 'report = run("reporting", PRODUCERS, not_presented=NP)\n',
        "tests/test_other.py": "asyncio.run(main())\n",
    }
    result = migrate(files, "0.30.0", "0.31.0")
    assert result.files == {}
    assert left_by_hand(result) == [("suite-cases-v26", "tests/test_suite.py", 1)]


def test_a_venue_adapter_saying_no_environment_is_left_to_report_one() -> None:
    adapter = textwrap.dedent(
        """\
        class BrokerVenue:
            source = "broker"

            def catalogue(self, code): ...
            def place(self, code, asked): ...
            def orders(self, code): ...


        class Reaching(BrokerVenue):
            environment = "paper"

            def catalogue(self, code): ...
            def place(self, code, asked): ...
            def orders(self, code): ...
        """
    )
    result = migrate({"src/br/venue.py": adapter}, "0.30.0", "0.31.0")
    assert left_by_hand(result) == [("venue-reports-no-environment", "src/br/venue.py", 1)]


def test_custody_pages_a_plugin_declares_itself_are_left_to_move_onto_the_sdk() -> None:
    copied = (
        '"""Custody\'s pages."""\n'
        '@pages.page(LINKS, "Account links", name="read_account_links")\n'
        "async def account_links(request): ...\n"
        "async def link_account(request): ...\n"
        '@pages.page(HISTORY, "History", name="read_account_activities")\n'
        "async def history(request): ...\n"
    )
    result = migrate({"src/br/custody_pages.py": copied}, "0.30.0", "0.31.0")
    assert left_by_hand(result) == [("custody-pages-onto-sdk", "src/br/custody_pages.py", 1)]


def test_a_listings_layer_a_plugin_keeps_itself_is_left_to_move_onto_the_sdk() -> None:
    copied = (
        "class Products:\n    pass\n\n\nclass Lake:\n"
        "    async def trade_row(self, stated, subject): ...\n"
        "    async def quote_row(self, stated, subject): ...\n"
    )
    result = migrate({"src/br/lake.py": copied}, "0.30.0", "0.31.0")
    assert left_by_hand(result) == [("lake-onto-sdk", "src/br/lake.py", 5)]


def test_a_trader_in_snaptrades_shape_is_left_to_move_onto_the_sdk() -> None:
    copied = (
        "class Charged:\n    pass\n\n\nclass Worked:\n    pass\n\n\nclass Trader:\n"
        "    async def _charges(self, venue): ...\n"
    )
    result = migrate({"src/st/trading.py": copied}, "0.30.0", "0.31.0")
    assert left_by_hand(result) == [("trading-onto-sdk", "src/st/trading.py", 9)]


# ── 0.31.1 to 0.32.0: contract v27 ───────────────────────────────────────


def test_v27s_base_pinned_by_digest_drops_its_digest() -> None:
    dockerfile = (
        f"ARG BASE=ghcr.io/open-meridian/plugin-python:0.31.1@{_DIGEST}\nFROM ${{BASE}}\n"
    )
    result = migrate({"Dockerfile": dockerfile}, "0.31.1", "0.32.0")
    assert result.files["Dockerfile"].splitlines()[0] == (
        "ARG BASE=ghcr.io/open-meridian/plugin-python:0.32.0"
    )
    assert ("base-digest", "Dockerfile", 1) in left_by_hand(result)


def test_a_role_suite_v27_adds_cases_to_and_a_faked_lake_query_are_left() -> None:
    files = {
        "tests/test_suite.py": (
            'report = run("data", PRODUCERS, not_presented=NP)\n'
            'PRODUCERS = {"queries-the-lake-within-bounds": lake_query("INS-1")}\n'
        ),
        "tests/test_desk.py": 'report = run("connectivity", PRODUCERS)\n',
    }
    result = migrate(files, "0.31.1", "0.32.0")
    assert result.files == {}
    assert sorted(left_by_hand(result)) == [
        ("lake-query-without-trades", "tests/test_suite.py", 2),
        ("suite-cases-v27", "tests/test_desk.py", 1),
        ("suite-cases-v27", "tests/test_suite.py", 1),
    ]


def test_a_trading_page_and_an_events_loop_a_plugin_keeps_are_left_to_the_sdk() -> None:
    page = (
        '@pages.page(TRADING, "Trading", name="read_trading")\n'
        "async def trading(request): ...\n"
        '@pages.route(ENABLE, name="enable_trading")\n'
        "async def enable(request): ...\n"
    )
    loop = (
        "class Events:\n"
        "    async def now(self, feed):\n"
        "        event = feed.market.event(ref)\n"
        "        await feed.report_event(event)\n"
    )
    result = migrate(
        {"src/br/trading_page.py": page, "src/k/__main__.py": loop}, "0.31.1", "0.32.0"
    )
    assert sorted(left_by_hand(result)) == [
        ("events-onto-sdk", "src/k/__main__.py", 1),
        ("trading-page-onto-sdk", "src/br/trading_page.py", 1),
    ]


def test_an_e2e_log_upload_missing_hidden_files_is_left_to_add_them() -> None:
    missing = (
        "jobs:\n  e2e:\n    steps:\n      - uses: actions/upload-artifact@v4\n"
        "        with:\n          path: .e2e/*.log\n      - run: echo done\n"
    )
    kept = missing.replace(
        "path: .e2e/*.log", "path: .e2e/*.log\n          include-hidden-files: true"
    )
    result = migrate(
        {".github/workflows/e2e.yaml": missing, ".github/workflows/other.yaml": kept},
        "0.31.1",
        "0.32.0",
    )
    assert left_by_hand(result) == [("e2e-hidden-files", ".github/workflows/e2e.yaml", 4)]


# ── 0.32.3 to 0.33.0: contract v28 ───────────────────────────────────────

# A v27 plugin's data feed, as plugin-kalshi and plugin-alpaca wrote theirs:
# subjects built from the wire bindings, handed to the SDK's typed rows and
# operations, and a test's fake want built of the wire's own messages.
_V27_FEED = textwrap.dedent(
    """\
    import meridian
    from meridian.plugin.v1 import operations_pb2 as ops


    def meta(subject: str) -> meridian.ObservationMeta:
        return meridian.ObservationMeta(
            row_key="k",
            subjects=[ops.SubjectRef(entity_id=subject)],
            source=ops.Source(dataset="d"),
        )


    async def decline(plugin, want_id, subjects):
        await plugin.decline_want(
            want_id=want_id,
            subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
            reason="not_covered",
        )


    def fake_want(subjects):
        return ops.ObservationsWantedEvent(
            want_id="WNT-1", subjects=[ops.SubjectRef(entity_id=s) for s in subjects]
        )


    def add(want, subject):
        want.subjects.append(ops.SubjectRef(entity_id=subject))
    """
)


def test_a_wire_subject_ref_handed_to_the_sdk_becomes_meridians() -> None:
    result = migrate({"src/feed.py": _V27_FEED}, "0.32.3", "0.33.0")
    text = result.files["src/feed.py"]
    assert "subjects=[meridian.SubjectRef(entity_id=subject)]" in text
    assert "subjects=[meridian.SubjectRef(entity_id=s) for s in subjects],\n" in text
    # Inside a wire message, or added to one's field, the wire's stays.
    assert 'want_id="WNT-1", subjects=[ops.SubjectRef(entity_id=s) for s in subjects]' in text
    assert "want.subjects.append(ops.SubjectRef(entity_id=subject))" in text
    assert result.steps[-1].rewrote == {"src/feed.py": {"subject-ref-from-the-sdk": 2}}
    assert left_by_hand(result) == []


def test_the_rewritten_subject_ref_is_what_the_typed_operations_take(tmp_path: Path) -> None:
    import importlib.util

    import meridian

    text = migrate({"src/feed.py": _V27_FEED}, "0.32.3", "0.33.0").files["src/feed.py"]
    (tmp_path / "feed.py").write_text(text)
    spec = importlib.util.spec_from_file_location("v27_feed_migrated", tmp_path / "feed.py")
    assert spec is not None and spec.loader is not None
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    meta = feed.meta("INS-1")
    assert isinstance(meta.subjects[0], meridian.SubjectRef)
    assert feed.fake_want(["INS-1"]).subjects[0].entity_id == "INS-1"


def test_a_file_naming_the_package_another_way_gets_it_imported() -> None:
    aliased = (
        "import meridian as om\n"
        "from meridian.plugin.v1 import operations_pb2\n"
        "ROW = om.ObservationMeta(subjects=[operations_pb2.SubjectRef(entity_id='X')])\n"
    )
    bare = (
        "from meridian import ObservationMeta\n"
        "from meridian.plugin.v1.operations_pb2 import Source, SubjectRef\n"
        "ROW = ObservationMeta(subjects=[SubjectRef(entity_id='X')], source=Source())\n"
    )
    result = migrate({"src/a.py": aliased, "src/b.py": bare}, "0.32.3", "0.33.0")
    assert "subjects=[om.SubjectRef(entity_id='X')]" in result.files["src/a.py"]
    b = result.files["src/b.py"]
    assert "\nimport meridian\n" in b
    assert "from meridian.plugin.v1.operations_pb2 import Source\n" in b
    assert "subjects=[meridian.SubjectRef(entity_id='X')]" in b


def test_a_file_not_using_the_sdk_keeps_its_subject_refs() -> None:
    other = "from vendor import ops\nROW = ops.SubjectRef(entity_id='X')\n"
    assert migrate({"src/v.py": other}, "0.32.3", "0.33.0").files == {}


def test_subjects_read_from_a_heard_message_are_left_by_hand() -> None:
    echo = (
        "import meridian\n"
        "async def on_want(plugin, heard):\n"
        "    await plugin.decline_want(\n"
        "        want_id=heard.message.want_id,\n"
        "        subjects=heard.message.subjects,\n"
        "        reason='not_covered',\n"
        "    )\n"
        "    return meridian.roles.WantHeard(subjects=heard.subjects)\n"
    )
    result = migrate({"src/w.py": echo}, "0.32.3", "0.33.0")
    assert left_by_hand(result) == [("subjects-from-the-wire", "src/w.py", 5)]


def test_v28s_suite_cases_and_the_latency_cases_named_not_presented_are_left() -> None:
    files = {
        "tests/test_suite.py": (
            'report = run("data", PRODUCERS, not_presented=NP)\n'
            'NP = {"reports-its-feed-delay": "core receives ReportLatency from contract v28, '
            'ruling 515"}\n'
        ),
        "tests/test_custody.py": 'report = run("custody", PRODUCERS)\n',
    }
    result = migrate(files, "0.32.3", "0.33.0")
    assert result.files == {}
    assert sorted(left_by_hand(result)) == [
        ("latency-cases-required", "tests/test_suite.py", 2),
        ("suite-cases-v28", "tests/test_custody.py", 1),
        ("suite-cases-v28", "tests/test_suite.py", 1),
    ]


def test_v28s_base_pinned_by_digest_drops_its_digest() -> None:
    dockerfile = (
        f"ARG BASE=ghcr.io/open-meridian/plugin-python:0.32.3@{_DIGEST}\nFROM ${{BASE}}\n"
    )
    result = migrate({"Dockerfile": dockerfile}, "0.32.3", "0.33.0")
    assert result.files["Dockerfile"].splitlines()[0] == (
        "ARG BASE=ghcr.io/open-meridian/plugin-python:0.33.0"
    )
    assert ("base-digest", "Dockerfile", 1) in left_by_hand(result)


# ── 0.33.5 to 0.34.0: contract v29 ───────────────────────────────────────


_RUNTIME = "ghcr.io/open-meridian/meridian-runtime:8def82a@sha256:" + "cd" * 32
_HARNESS = "ghcr.io/open-meridian/meridian-harness:8def82a@sha256:" + "ef" * 32


@pytest.mark.parametrize(
    ("comment", "left"),
    [
        ("# Core 8def82a, contract v28, as published with chart 0.1.313.", [3, 4]),
        ("# Core's images for the e2e.", [3, 4]),
        ("# Core 1ae36f0, contract v29, as published with chart 0.1.339.", []),
    ],
)
def test_core_images_pinned_below_v29_are_named(comment: str, left: list[int]) -> None:
    """SDK 0.35.1 (the plugin pilot): the step to contract v29 moved no
    e2e's core pins and named none; it names each one pinned to a core below
    v29, or naming no contract, for a person to pin by digest."""
    makefile = (
        f"E2E := 1\n{comment}\nRUNTIME_IMAGE ?= {_RUNTIME}\nHARNESS_IMAGE ?= {_HARNESS}\n"
    )
    result = migrate({"Makefile": makefile}, "0.33.5", "0.34.0")
    assert result.files == {}
    assert left_by_hand(result) == [("core-images", "Makefile", line) for line in left]


def test_v29s_suite_cases_and_a_quality_assessment_naming_no_data_type_are_left() -> None:
    files = {
        "tests/test_suite.py": 'report = run("data", PRODUCERS, not_presented=NP)\n',
        "tests/test_board.py": 'report = run("reporting", PRODUCERS)\n',
        "tests/test_custody.py": 'report = run("custody", PRODUCERS)\n',
        "src/judge.py": (
            "from meridian import QualityAssessment\n"
            "kept = QualityAssessment(dataset=d, row_key=k, version=1)\n"
            'named = QualityAssessment(dataset=d, data_type="meridian.v1.Price")\n'
        ),
    }
    result = migrate(files, "0.33.5", "0.34.0")
    assert result.files == {}
    assert sorted(left_by_hand(result)) == [
        ("quality-assessment-data-type", "src/judge.py", 2),
        ("suite-cases-v29", "tests/test_board.py", 1),
        ("suite-cases-v29", "tests/test_suite.py", 1),
    ]


@pytest.mark.parametrize("named", ["PAIRS", "EVENT_CONTRACTS", "RATES"])
def test_a_data_suite_naming_the_sdks_not_presented_set_is_not_left(named: str) -> None:
    """SDK 0.35.1 (the plugin pilot's kalshi): a plugin spreading the SDK's
    not-presented set into its own, in another file, names v29's factor case
    already; another role's suite run is still left."""
    files = {
        "tests/venue_cases.py": (
            f"from meridian.roles.data.testing import {named}_NOT_PRESENTED\n"
            f"NOT_PRESENTED = {{**{named}_NOT_PRESENTED}}\n"
        ),
        "tests/test_data_role.py": (
            "import venue_cases as v\n"
            'report = run(\n    "data", PRODUCERS, not_presented=v.NOT_PRESENTED\n)\n'
        ),
        "tests/test_board.py": 'report = run("reporting", PRODUCERS)\n',
    }
    result = migrate(files, "0.33.5", "0.34.0")
    assert left_by_hand(result) == [("suite-cases-v29", "tests/test_board.py", 1)]


def test_v29s_base_pinned_by_digest_drops_its_digest() -> None:
    dockerfile = (
        f"ARG BASE=ghcr.io/open-meridian/plugin-python:0.33.5@{_DIGEST}\nFROM ${{BASE}}\n"
    )
    result = migrate({"Dockerfile": dockerfile}, "0.33.5", "0.34.0")
    assert result.files["Dockerfile"].splitlines()[0] == (
        "ARG BASE=ghcr.io/open-meridian/plugin-python:0.34.0"
    )
    assert ("base-digest", "Dockerfile", 1) in left_by_hand(result)


@pytest.mark.parametrize("source", ["0.30.0", "0.31.1", "0.32.3", "0.33.4"])
def test_a_step_never_moves_back_a_base_pinned_at_a_later_release(source: str) -> None:
    """SDK 0.35.1 (the plugin pilot's migrate from 0.33.4): `meridian plugin
    migrate` pins the base to the release it migrates to, by digest, before
    the steps run; a step moving the base to its own, earlier release
    overwrote that pin, and the run ended on 0.34.0 with no digest."""
    dockerfile = (
        f"ARG BASE=ghcr.io/open-meridian/plugin-python:0.35.0@{_DIGEST}\nFROM ${{BASE}}\n"
    )
    result = migrate({"Dockerfile": dockerfile}, source, "0.35.0")
    assert "Dockerfile" not in result.files
    assert [r for r, path, _ in left_by_hand(result) if path == "Dockerfile"] == []


@pytest.mark.parametrize(
    "declaring",
    [
        "from meridian.declaration import Declaration\nD = Declaration(\n"
        "    settings=Config.declared(),\n)\n",
        "import meridian\nD = meridian.Declaration(\n    settings=Config.declared(),\n)\n",
        # Through an alias (SDK 0.35.3, the plugin step's tiingo).
        "import meridian\nSETTINGS = Config.declared()\n"
        "D = meridian.Declaration(settings=SETTINGS)\n",
    ],
)
def test_a_declaration_of_a_typed_class_untyped_is_left_by_hand(declaring: str) -> None:
    """SDK 0.35.2 (the plugin pilot's fred): `settings=Config.declared()`
    reached the storage kinds' window settings on 0.35.1, which a typed
    delivery dropped; from 0.35.2 the typed delivery holds them, so the
    declaration names its class again, by hand."""
    result = migrate({"src/p/declaration.py": declaring}, "0.35.1", "0.35.2")
    assert result.files == {}
    assert left_by_hand(result) == [("typed-settings-declared", "src/p/declaration.py", 3)]


def test_a_declaration_naming_its_class_or_a_list_is_not_left() -> None:
    files = {
        "src/p/a.py": "import meridian\nD = meridian.Declaration(settings=Config)\n",
        "src/p/b.py": "import meridian\nD = meridian.Declaration(settings=[KEY])\n",
        "src/p/c.py": "import meridian\nconfig = await plugin.first_settings(Config)\n",
        "src/p/d.py": "D = Declaration(settings=Config.declared())\n",  # not the SDK's
    }
    result = migrate(files, "0.35.1", "0.35.2")
    assert result.files == {} and left_by_hand(result) == []


# ── 0.34.0: the topic modules leave meridian.roles (ruling 1001) ────────


def _helpers(text: str, path: str = "src/p/x.py") -> migrations.Result:
    return migrate({path: textwrap.dedent(text)}, "0.33.5", "0.34.0")


def test_every_import_form_of_a_topic_module_moves_to_meridian_helpers() -> None:
    result = _helpers(
        """\
        import meridian.roles.chains
        import meridian.roles.debt as rules
        from meridian.roles import lifecycle as events
        from meridian.roles.packages import legs, propose as offer
        """
    )
    assert result.files["src/p/x.py"] == textwrap.dedent(
        """\
        import meridian.helpers.chains
        import meridian.helpers.debt as rules
        from meridian.helpers import lifecycle as events
        from meridian.helpers.packages import legs, propose as offer
        """
    )
    assert left_by_hand(result) == []


def test_an_import_beside_a_roles_module_is_split_the_helpers_first() -> None:
    result = _helpers(
        """\
        # The desk's imports.
        from meridian.roles import Latency, chains, data, debt as rules  # kept here
        from meridian.roles import (
            ems,
            packages,
            signal,
        )
        """
    )
    assert result.files["src/p/x.py"] == textwrap.dedent(
        """\
        # The desk's imports.
        from meridian.helpers import chains, debt as rules
        from meridian.roles import Latency, data  # kept here
        from meridian.helpers import packages
        from meridian.roles import (
            ems,
            signal,
        )
        """
    )


def test_a_split_import_on_a_line_of_several_statements_stays_on_it() -> None:
    result = _helpers("import os; from meridian.roles import chains, ems\n")
    assert result.files["src/p/x.py"] == (
        "import os; from meridian.helpers import chains; from meridian.roles import ems\n"
    )


def test_a_name_reached_through_the_package_moves_with_it() -> None:
    result = _helpers(
        """\
        import meridian as om
        import meridian.roles

        FACE = om.roles.debt.current_face(100, "0.5")
        ITM = meridian.roles.lifecycle.in_the_money("call", 1, 2)
        WANTS = meridian.roles.data.Wants
        """
    )
    assert result.files["src/p/x.py"] == textwrap.dedent(
        """\
        import meridian as om
        import meridian.roles

        FACE = om.helpers.debt.current_face(100, "0.5")
        ITM = meridian.helpers.lifecycle.in_the_money("call", 1, 2)
        WANTS = meridian.roles.data.Wants
        """
    )


def test_roles_bound_by_name_is_kept_while_a_role_is_still_read_through_it() -> None:
    result = _helpers(
        """\
        from meridian import roles

        SYMBOL = roles.chains.osi_symbol("A", "2026-01-16", "call", "1")
        WANTS = roles.data.Wants
        """
    )
    text = result.files["src/p/x.py"]
    assert "from meridian import roles\n" in text
    assert "import meridian\n" in text
    assert 'SYMBOL = meridian.helpers.chains.osi_symbol("A", "2026-01-16", "call", "1")' in text
    assert "WANTS = roles.data.Wants" in text


def test_roles_bound_by_an_alias_is_dropped_once_nothing_reads_through_it() -> None:
    result = _helpers(
        """\
        import meridian
        import meridian.roles as r

        RULES = r.debt
        """
    )
    assert result.files["src/p/x.py"] == textwrap.dedent(
        """\
        import meridian

        RULES = meridian.helpers.debt
        """
    )


def test_a_patch_targets_path_moves_and_other_strings_are_left_by_hand() -> None:
    result = _helpers(
        """\
        import pytest

        def test_patched(monkeypatch: pytest.MonkeyPatch) -> None:
            monkeypatch.setattr("meridian.roles.debt.to_cent", round)
            note = "uses meridian.roles.packages for its legs"
        """,
        path="tests/test_patch.py",
    )
    text = result.files["tests/test_patch.py"]
    assert 'monkeypatch.setattr("meridian.helpers.debt.to_cent", round)' in text
    assert '"uses meridian.roles.packages for its legs"' in text
    assert left_by_hand(result) == [("topic-module-named", "tests/test_patch.py", 5)]


def test_a_moved_module_read_through_a_star_import_is_left_by_hand() -> None:
    result = _helpers(
        """\
        from meridian.roles import *

        SYMBOL = chains.osi_symbol("A", "2026-01-16", "call", "1")
        """
    )
    assert result.files == {}
    assert left_by_hand(result) == [("topic-module-named", "src/p/x.py", 1)]
    # A star import reading no moved module leaves nothing to do.
    assert left_by_hand(_helpers("from meridian.roles import *\nW = data.Wants\n")) == []


def test_the_roles_and_other_packages_named_the_same_are_left_alone() -> None:
    untouched = {
        "src/a.py": (
            "from meridian.roles import Latency, data, ems\nimport meridian.roles.data\n"
        ),
        "src/b.py": "from vendor.roles import chains\nimport vendor.roles.debt\n",
        "src/c.py": (
            "import meridian\n\nclass R:\n    chains = 1\n\nroles = R()\nN = roles.chains\n"
        ),
        "src/d.py": "import meridian.helpers.chains\nfrom meridian.helpers import debt\n",
    }
    result = migrate(untouched, "0.33.5", "0.34.0")
    assert result.files == {}
    assert left_by_hand(result) == []


def test_the_old_paths_are_gone_and_the_new_ones_are_the_same_modules() -> None:
    import importlib

    from meridian import helpers, roles

    for topic in ("chains", "packages", "lifecycle", "debt"):
        moved = importlib.import_module(f"meridian.helpers.{topic}")
        assert getattr(helpers, topic) is moved
        assert not hasattr(roles, topic), topic
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(f"meridian.roles.{topic}")


# ── SDK 0.35.3: what the plugin step found 0.35.0's step missing ─────────


def _step(files: dict[str, str]) -> tuple[dict[str, str], list[tuple[str, str, int]]]:
    result = migrate(files, "0.34.0", "0.35.0")
    return result.files, left_by_hand(result)


DATA = '[tool.meridian]\nroles = ["data"]\n'


def test_renames_reach_super_and_an_object_named_another_way() -> None:
    """The plugin step's crypto brokers: `super().on_want(...)`,
    `state.lake.seed(...)` and `rig.trader.on_execution(...)` were missed."""
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["data", "connectivity"]\n',
        "src/p/lake.py": textwrap.dedent(
            """\
            from meridian.roles.connectivity import Trader
            from meridian.roles.data import listings

            class Lake(listings.Feed):
                async def on_want(self, heard):
                    await super().on_want(heard)

            class Rig:
                def __init__(self, plugin):
                    self.lake = Lake(plugin, None)
                    self.trader = Trader(plugin, None)

            async def go(state, rig, heard):
                await state.lake.seed(["SPY"])
                await rig.trader.on_execution(heard)
            """
        ),
    }
    written, _ = _step(files)
    lake = written["src/p/lake.py"]
    assert "await super().on_observations_wanted(heard)" in lake
    assert "await state.lake.seed_symbols([" in lake
    assert "await rig.trader.on_execution_recorded(heard)" in lake


def test_a_helper_given_the_dropped_plugin_is_given_self_and_other_reads_named() -> None:
    """fx-rates: `data.Wants(plugin, ...)`, `Latency(plugin)` and
    `rates.Feed(plugin, ...)` were left naming the removed parameter -- the
    last dropped, as the plugin's own `Feed` was planned; `self.me =
    plugin.identity` is named."""
    files = {
        "pyproject.toml": DATA,
        "src/p/__main__.py": textwrap.dedent(
            """\
            import meridian
            from .work import Feed

            async def run():
                async with await meridian.connect() as plugin:
                    feed = Feed(plugin)
                    await plugin.receive(observations_wanted=feed.wanted)
            """
        ),
        "src/p/work.py": textwrap.dedent(
            """\
            from meridian.roles import Latency, data
            from meridian.roles.data import rates

            class Feed:
                def __init__(self, plugin):
                    self.plugin = plugin
                    self.wants = data.Wants(plugin, "fx")
                    self.latency = Latency(plugin)
                    self.rates = rates.Feed(plugin, "fx")
                    self.me = plugin.identity

                async def wanted(self, heard): ...
            """
        ),
    }
    written, by_hand = _step(files)
    work = written["src/p/work.py"]
    assert "def __init__(self):" in work and "self.plugin = plugin" not in work
    assert "data.Wants(self, " in work and "Latency(self)" in work
    assert 'rates.Feed(self, "fx")' in work
    assert ("plugin-param-removed", "src/p/work.py", 10) in by_hand


def test_a_plugins_own_trader_no_longer_takes_the_connection() -> None:
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["connectivity"]\n',
        "src/p/desk.py": textwrap.dedent(
            """\
            from meridian.roles.connectivity import Trader

            class Desk(Trader):
                def __init__(self, plugin, venue):
                    super().__init__(plugin, venue)
                    self.plugin = plugin

            def made(plugin, venue):
                return Desk(plugin, venue)
            """
        ),
    }
    written, _ = _step(files)
    desk = written["src/p/desk.py"]
    assert "def __init__(self, venue):" in desk and "super().__init__(venue)" in desk
    assert "self.plugin = plugin" not in desk and "return Desk(venue)" in desk


def test_a_stand_in_is_bound_to_and_one_not_plainly_the_connection_is_named() -> None:
    """newer-data: a preview's `Lake(stand_in, ...)` lost its binding, and
    `Work(plugin if live else stand_in)` its argument, silently."""
    files = {
        "pyproject.toml": DATA,
        "src/p/__main__.py": textwrap.dedent(
            """\
            import meridian
            from .work import Work

            async def run():
                async with await meridian.connect() as plugin:
                    work = Work(plugin)
                    await plugin.receive(observations_wanted=work.wanted)
            """
        ),
        "src/p/work.py": textwrap.dedent(
            """\
            class Work:
                def __init__(self, plugin):
                    self.plugin = plugin

                async def wanted(self, heard): ...
            """
        ),
        "src/p/preview.py": textwrap.dedent(
            """\
            from .work import Work

            def shown(stand_in, live, plugin):
                lake = Work(stand_in)
                other = Work(plugin if live else stand_in)
                return lake, other
            """
        ),
    }
    written, by_hand = _step(files)
    preview = written["src/p/preview.py"]
    assert "lake = stand_in.bind(Work())" in preview
    assert ("suite-producer-to-role", "src/p/preview.py", 5) in by_hand


def test_an_import_dropped_while_all_names_it_is_kept_and_new_ones_placed() -> None:
    """massive: PRICE and TRADE imports dropped while `__all__` named them;
    `from meridian.roles.data import SentRows` placed after the local
    imports."""
    files = {
        "pyproject.toml": DATA,
        "src/p/lake.py": textwrap.dedent(
            """\
            from meridian.roles.data import listings
            from meridian.roles.data.listings import PRICE, at_the_edge

            from .convert import convert

            __all__ = ["PRICE", "Lake"]

            class Lake(listings.Feed):
                def at_the_edge(self, rows):
                    return at_the_edge(self, rows)
            """
        ),
    }
    written, _ = _step(files)
    lake = written["src/p/lake.py"]
    assert "import PRICE\n" in lake and "at_the_edge" not in lake
    files["src/p/chains.py"] = (FIXTURES / "equities-0.34.0/src/equities/chains.py").read_text()
    files["src/p/chains.py"] = files["src/p/chains.py"].replace(
        "from meridian", "from .convert import convert\nfrom meridian", 1
    )
    chains = _step(files)[0]["src/p/chains.py"]
    assert chains.index("import SentRows") < chains.index("from .convert import")


def test_a_temporary_record_override_and_a_dataclass_memory_are_the_sdks() -> None:
    """alpaca's 0.33 `_record` that aged and judged its rows by hand; unusual
    whales' memory a dataclass field."""
    chains = (FIXTURES / "equities-0.34.0/src/equities/chains.py").read_text()
    copied = re.search(r"\n    def _changed\(.*?(?=\n    (?:async )?def |\Z)", chains, re.S)
    assert copied is not None
    files = {
        "pyproject.toml": DATA,
        "src/p/lake.py": textwrap.dedent(
            """\
            from meridian.roles.data import listings

            class Lake(listings.Feed):
                async def _record(self, key, data_type, rows, want_id):
                    \"\"\"TEMPORARY until the SDK's listings feed does it.\"\"\"
                    if self.latency is not None:
                        for row in rows:
                            self.latency.aged(self.dataset(key), "AGE_HOP_EDGE", row)
                    rows = self.quality.judged(key, rows)
                    await super()._record(key, data_type, rows, want_id)
            """
        ),
        "src/p/work.py": "from collections import OrderedDict\n"
        "from dataclasses import dataclass, field\n\nREMEMBERED = 10\n\n\n@dataclass\n"
        "class Work:\n"
        "    sent: OrderedDict[tuple[str, str, str], str] = field(\n"
        "        default_factory=OrderedDict\n"
        "    )\n" + copied.group(0) + "\n",
    }
    written, _ = _step(files)
    assert "_record" not in written["src/p/lake.py"]
    work = written["src/p/work.py"]
    assert "sent: SentRows = field(default_factory=lambda: SentRows(REMEMBERED))" in work


def test_a_role_objects_act_on_its_connection_and_tests_shapes() -> None:
    """massive: `self.lake.plugin.read_calendar(...)`; a test's
    `lake.receive(...)`, `type(work)(recorder, ...)`, a `getattr` act and a
    rewritten `# fmt: skip` statement named."""
    files = {
        "pyproject.toml": DATA,
        "src/p/chains.py": textwrap.dedent(
            """\
            from meridian.roles.data import listings

            class Lake(listings.Feed):
                pass

            class Chains:
                def __init__(self, lake):
                    self.lake = lake

                async def day(self):
                    await self.lake.plugin.read_calendar(calendar_id="CAL-1")
                    await getattr(self.lake.plugin, f"record_{self.kind}")([])

            def made(plugin):
                lake = Lake(plugin, None)
                return Chains(lake)
            """
        ),
        "tests/test_p.py": textwrap.dedent(
            """\
            from p.chains import Lake

            async def test_it(lake, work, recorder):
                await lake.receive(observations_wanted=work.on_observations_wanted)
                again = type(work)(recorder, 1)
                held = Lake(recorder,
                            None)  # fmt: skip
            """
        ),
    }
    written, by_hand = _step(files)
    assert 'await self.lake.read_calendar(calendar_id="CAL-1")' in written["src/p/chains.py"]
    assert ("act-on-the-connection", "src/p/chains.py", 12) in by_hand
    assert ("suite-producer-to-role", "tests/test_p.py", 4) in by_hand
    assert ("suite-producer-to-role", "tests/test_p.py", 5) in by_hand
    assert ("fmt-skip-rewritten", "tests/test_p.py", 6) in by_hand


def test_a_class_making_another_roles_acts_is_named_not_made_a_role_class() -> None:
    """The samples' options `Chains`: hearing portfolio's rows, listing
    signal's quotes, it was made a portfolio class and lost them."""
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["portfolio", "signal"]\n',
        "src/p/chains.py": textwrap.dedent(
            """\
            class Chains:
                def __init__(self, plugin):
                    self.plugin = plugin

                async def position(self, heard):
                    await self.plugin.list_quotes(subjects=[])

                async def hear(self):
                    await self.plugin.receive(position_changed=self.position)
            """
        ),
    }
    written, by_hand = _step(files)
    assert written == {}
    assert ("role-class-two-roles", "src/p/chains.py", 1) in by_hand
    assert ("receive-not-rewritten", "src/p/chains.py", 9) in by_hand


def test_a_class_with_its_own_run_is_named_and_an_emptied_hear_removed() -> None:
    """The samples' operations `Follower`: its `run(account_id)` would be
    the role's; and once a class is made one, a method only calling
    `receive` is removed and its calls named."""
    clash = textwrap.dedent(
        """\
        class Follower:
            async def activity(self, heard): ...

            async def run(self, account_id):
                return account_id

            async def hear(self, through):
                await through.receive(activity_recorded=self.activity)
        """
    )
    files = {"pyproject.toml": '[tool.meridian]\nroles = ["operations"]\n', "src/p/f.py": clash}
    written, by_hand = _step(files)
    assert written == {} and ("role-method-clash", "src/p/f.py", 1) in by_hand
    files["src/p/f.py"] = clash.replace("def run(", "def run_account(")
    files["src/p/__main__.py"] = textwrap.dedent(
        """\
        import meridian
        from .f import Follower

        async def go(plugin: meridian.Plugin):
            follower = Follower()
            await follower.hear(plugin)
        """
    )
    written, by_hand = _step(files)
    assert "class Follower(operations.Role):" in written["src/p/f.py"]
    assert "def hear" not in written["src/p/f.py"]
    assert ("emptied-method-called", "src/p/__main__.py", 6) in by_hand


def test_an_init_only_keeping_the_connection_goes_and_again_is_judged_by_its_body() -> None:
    files = {
        "pyproject.toml": DATA,
        "src/p/__main__.py": textwrap.dedent(
            """\
            import meridian
            from .work import Work

            def again(text):
                return text * 2

            async def run():
                async with await meridian.connect() as plugin:
                    work = Work(plugin)
                    await plugin.receive(observations_wanted=work.wanted)
            """
        ),
        "src/p/work.py": textwrap.dedent(
            """\
            class Work:
                def __init__(self, plugin):
                    self.plugin = plugin

                async def wanted(self, heard): ...
            """
        ),
    }
    written, by_hand = _step(files)
    assert "__init__" not in written["src/p/work.py"]
    assert [r for r, _, _ in by_hand if r == "helper-adopted"] == []


def test_an_annotation_of_the_wires_subject_ref_becomes_the_sdks() -> None:
    """The samples' operations closes.py: `list[ops.SubjectRef]` was left
    over a list the step made the SDK's, which strict mypy refused."""
    text = textwrap.dedent(
        """\
        import meridian
        from meridian.plugin.v1 import operations_pb2 as ops

        def subjects(ids: list[str]) -> list[ops.SubjectRef]:
            made: list[ops.SubjectRef] = [ops.SubjectRef(entity_id=each) for each in ids]
            return made

        def kept(meta: ops.ObservationMeta) -> ops.ObservationMeta:
            return meta
        """
    )
    result = migrate({"src/closes.py": text}, "0.32.3", "0.33.0")
    written = result.files["src/closes.py"]
    assert "-> list[meridian.SubjectRef]:" in written
    assert "made: list[meridian.SubjectRef] = [meridian.SubjectRef(" in written
    assert "def kept(meta: ops.ObservationMeta) -> ops.ObservationMeta:" in written


# ── 0.35.2 to 0.35.3: what the plugin step found, left by hand ───────────


def _left_0353(files: dict[str, str]) -> list[tuple[str, str, int]]:
    result = migrate(files, "0.35.2", "0.35.3")
    assert result.files == {}
    return left_by_hand(result)


def test_0353_names_a_feeds_overrides_that_0_35_breaks() -> None:
    """massive: `named` calling `dataset` (endless from 0.35), its own
    `timeliness(asset_class)` hiding the feed's property; fx-rates: a field
    `subjects` hiding the role's `subjects()`."""
    files = {
        "src/p/lake.py": textwrap.dedent(
            """\
            from meridian.roles import data
            from meridian.roles.data import listings

            class Lake(listings.Feed):
                def named(self, key):
                    return super().dataset(key)

                def timeliness(self, asset_class):
                    return "delayed"

                @property
                def plan(self):
                    return 1

            class Work(data.Role):
                subjects: tuple[str, ...] = ()

            class Again(Work):
                def __init__(self):
                    self.subjects = ["SPY"]
            """
        )
    }
    assert _left_0353(files) == [
        ("named-calls-dataset", "src/p/lake.py", 5),
        ("timeliness-overridden", "src/p/lake.py", 8),
        ("subjects-shadowed", "src/p/lake.py", 16),
        ("subjects-shadowed", "src/p/lake.py", 20),
    ]


def test_0353_names_old_handler_names_a_receive_and_a_stand_ins_read() -> None:
    """crypto-brokers: `held.on_want(...)` and `rig.trader.on_execution(...)`
    through names 0.35.0's step could not follow; a test's `lake.receive`;
    and `work.plugin.on(...)` reading the connection's stand-in."""
    files = {
        "src/p/work.py": textwrap.dedent(
            """\
            import meridian

            class Lake:
                async def seed(self, symbols): ...
            """
        ),
        "tests/test_p.py": textwrap.dedent(
            """\
            import meridian

            async def test_it(held, rig, lake, work, heard):
                await held.on_want(heard)
                await rig.trader.on_execution(heard)
                await lake.seed(["SPY"])
                await lake.receive(observations_wanted=work.on_observations_wanted)
                assert work.plugin.on("RecordPrices") == []
            """
        ),
    }
    assert _left_0353(files) == [
        ("old-handler-name", "tests/test_p.py", 4),
        ("old-handler-name", "tests/test_p.py", 5),
        ("receive-gone", "tests/test_p.py", 7),
        ("stand-in-read", "tests/test_p.py", 8),
    ]


def test_0353_names_a_role_object_registered_with_nothing() -> None:
    """pyth: the pages' fallback built a `Work` no `meridian.run` or
    `bind` registered; the entry point's, a test's and a bound one are not
    named."""
    work = "from meridian.roles import data\n\nclass Work(data.Role):\n    pass\n"
    files = {
        "src/p/work.py": work,
        "src/p/page.py": "from .work import Work\n\ndef pages(work=None):\n"
        "    work = work or Work()\n    return work\n",
        "src/p/preview.py": "from .work import Work\n\ndef shown(recorder):\n"
        "    return recorder.bind(Work())\n",
        "src/p/__main__.py": "import meridian\nfrom .work import Work\n\n"
        "meridian.run(roles=[Work()])\n",
        "tests/test_p.py": "from p.work import Work\n\ndef test_it():\n    Work()\n",
    }
    assert _left_0353(files) == [("unregistered-role-object", "src/p/page.py", 4)]


def test_0353_names_a_base_by_tag_where_the_plugin_pins_by_digest() -> None:
    base = "ARG BASE=ghcr.io/open-meridian/plugin-python:0.35.3\nFROM ${BASE}\n"
    pinned = f"RUNTIME_IMAGE ?= ghcr.io/open-meridian/meridian-runtime:abc@{_DIGEST}\n"
    assert _left_0353({"Dockerfile": base, "Makefile": pinned}) == [
        ("base-digest", "Dockerfile", 1)
    ]
    # The template's way, nothing by digest: not named.
    assert _left_0353({"Dockerfile": base}) == []
    by_digest = base.replace("0.35.3", f"0.35.3@{_DIGEST}")
    assert _left_0353({"Dockerfile": by_digest, "Makefile": pinned}) == []


# ── 0.35.5 to 0.36.0: contract 30 ────────────────────────────────────────


def test_a_licence_default_is_written_as_its_terms_in_words() -> None:
    """Ruling 1032: `licence-default-described` turns each literal
    `licence_default=DatasetLicence(...)` into `terms_and_pricing="..."`,
    drops the retired names from the import where nothing else names them,
    and leaves by hand a licence it cannot read word for word, a test
    reading `.licence_default`, a suite contract 30 grew and an SDK
    DerivedSeries given the wire's MeasureRef."""
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["data"]\n',
        "src/p/declared.py": textwrap.dedent(
            """\
            from meridian import DatasetDeclaration, DatasetLicence

            HELD = DatasetLicence(kept=True)

            def licence_for(key):
                return DatasetLicence(kept=key == "daily")

            DAILY = DatasetDeclaration(
                key="daily",
                vendor="Coinbase",
                data_types=["meridian.v1.Price"],
                modes=["pull"],
                licence_default=DatasetLicence(kept=True, retention_days=2, display=True),
            )
            LIVE = DatasetDeclaration(
                key="live", vendor="Coinbase", data_types=["meridian.v1.Price"],
                modes=["stream"], licence_default=HELD,
            )
            BARS = DatasetDeclaration(
                key="bars", vendor="Coinbase", data_types=["meridian.v1.Bar"],
                modes=["pull"], licence_default=licence_for("bars"),
            )
            ODD = DatasetDeclaration(
                key="odd", vendor="Coinbase", data_types=["meridian.v1.Bar"],
                modes=["pull"], licence_default=DatasetLicence(kept=True, meters="display"),
            )
            LONG = DatasetDeclaration(
                key="long", vendor="Coinbase", data_types=["meridian.v1.Bar"],
                modes=["pull"], licence_default=DatasetLicence(attribution_text=LONGTEXT),
            )
            """
        ),
        "src/p/plain.py": textwrap.dedent(
            """\
            import meridian
            from meridian import DataEligibility, DatasetDeclaration, DatasetLicence

            DAILY = DatasetDeclaration(
                key="daily",
                vendor="ECB",
                data_types=["meridian.v1.Rate"],
                modes=["pull"],
                licence_default=meridian.DatasetLicence(
                    kept=True,
                    derived_use_terms="not_restricted",
                    attribution_text="Source: ECB",
                    eligibility=DataEligibility(uses=["personal", "commercial"]),
                ),
            )
            """
        ),
        "src/p/shared.py": textwrap.dedent(
            """\
            from meridian import DatasetDeclaration, DatasetLicence

            LIC = DatasetLicence(kept=True, retention_days=2)
            DAYS = LIC.retention_days
            D = DatasetDeclaration(
                key="d", vendor="v", data_types=["meridian.v1.Bar"], modes=["pull"],
                licence_default=LIC,
            )
            """
        ),
        "src/p/derived.py": textwrap.dedent(
            """\
            import meridian
            from meridian.plugin.v1 import operations_pb2 as ops

            VIX = meridian.DerivedSeries(series="level", rule=ops.MeasureRef(definition="v"))
            WIRE = ops.DerivedSeries(series="level", rule=ops.MeasureRef(definition="v"))
            """
        ),
        "tests/test_suite.py": textwrap.dedent(
            """\
            from meridian.suites import run

            def test_suite():
                assert run("signal", {}).passed
            """
        ),
        "tests/test_declared.py": textwrap.dedent(
            """\
            from p.declared import DAILY

            def test_kept():
                assert DAILY._wire().licence_default.kept
            """
        ),
    }
    # Terms past the field's 2,000 characters, in words: left, never cut.
    files["src/p/declared.py"] = files["src/p/declared.py"].replace(
        "LONGTEXT", '"' + "x" * 2001 + '"'
    )
    result = migrate(files, "0.35.5", "0.36.0")
    declared = result.files["src/p/declared.py"]
    # An argument the rule does not word, and terms too long: by hand.
    assert 'licence_default=DatasetLicence(kept=True, meters="display")' in declared
    assert "licence_default=DatasetLicence(attribution_text=" in declared
    assert 'terms_and_pricing="Kept by the lake; kept 2 days at most; display allowed."' in (
        declared
    )
    # A licence shared through a module-level name bound once: the name
    # holds the words, and each dataset names it.
    assert 'HELD = "Kept by the lake."' in declared
    assert 'modes=["stream"], terms_and_pricing=HELD,' in declared
    # One made by a function is left by hand, and so its import stays.
    assert 'licence_default=licence_for("bars")' in declared
    assert "from meridian import DatasetDeclaration, DatasetLicence" in declared
    plain = result.files["src/p/plain.py"]
    assert "from meridian import DatasetDeclaration\n" in plain
    assert (
        'terms_and_pricing="Kept by the lake; derived use not restricted; attribution '
        'required: \\"Source: ECB\\"; eligible: personal and commercial use."'
    ) in plain
    left = {(each["rule"], each["file"], each["line"]) for each in as_json(result)["by_hand"]}
    assert ("licence-default-left", "src/p/declared.py", 21) in left
    assert ("licence-default-left", "src/p/declared.py", 25) in left
    assert ("licence-default-left", "src/p/declared.py", 29) in left
    assert ("licence-default-left", "tests/test_declared.py", 4) in left
    assert ("suite-cases-v30", "tests/test_suite.py", 4) in left
    assert ("measure-ref-sdk-form", "src/p/derived.py", 4) in left
    assert not any(f == "src/p/derived.py" and n == 5 for _, f, n in left)
    # A shared licence read otherwise too keeps its licence: by hand.
    assert "src/p/shared.py" not in result.files
    assert ("licence-default-left", "src/p/shared.py", 7) in left
    rewrote = {
        (each["file"], each["rule"], each["places"])
        for step in as_json(result)["steps"]
        for each in step["rewrote"]
    }
    assert ("src/p/declared.py", "licence-default-described", 2) in rewrote
    assert ("src/p/plain.py", "licence-default-described", 1) in rewrote


def test_a_hand_built_jobs_wire_measures_are_left_by_hand() -> None:
    """0.36.1: `measure-ref-sdk-form` also names an SDK Job built by hand
    whose `measures` are not each a `meridian.MeasureRef` as written -- the
    wire's, `analytics.measure`'s answer, or a list built elsewhere -- which
    0.36.0's Job refuses (a TypeError; sample-options' 74 tests). A Job of
    the wire's, `analytics.job`, and a Job of SDK refs are not named."""
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["signal"]\n',
        "src/p/jobs.py": textwrap.dedent(
            """\
            import meridian
            from meridian import Job, analytics
            from meridian.plugin.v1 import operations_pb2 as ops

            A = meridian.Job(account_ids=["ACC-1"], measures=[ops.MeasureRef(definition="v")])
            B = Job(measures=[analytics.measure("exposure", 1)])
            def c(measures):
                return meridian.Job(measures=list(measures))
            D = meridian.Job(measures=[meridian.MeasureRef(definition="v", version=1)])
            E = ops.Job(measures=[ops.MeasureRef(definition="v")])
            F = analytics.job(measures=[analytics.measure("exposure", 1)])
            G = meridian.Job(account_ids=["ACC-1"])
            """
        ),
    }
    result = migrate(files, "0.35.5", "0.36.0")
    left = {
        (each["file"], each["line"])
        for each in as_json(result)["by_hand"]
        if each["rule"] == "measure-ref-sdk-form"
    }
    assert left == {("src/p/jobs.py", 5), ("src/p/jobs.py", 6), ("src/p/jobs.py", 8)}


def test_a_receive_stand_in_with_no_read_is_left_by_hand() -> None:
    """0.36.1: `receive-stand-in-read` names a test's stand-in for a Receive
    call iterated with `async for` and no `read()`, which 0.36.0's hearing
    loop and views call (sample-fx, -options and -reporting's
    tests/sidecar_stream.py: an AttributeError). One with `read`, or an
    async iterator in a file handing the SDK no Receive call, is not named."""
    files = {
        "pyproject.toml": '[tool.meridian]\nroles = ["reporting"]\n',
        "tests/sidecar_stream.py": textwrap.dedent(
            """\
            import asyncio
            import grpc

            class _Call:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            class _Read:
                def __aiter__(self):
                    return self

                async def read(self):
                    return grpc.aio.EOF

            class _Stub:
                def Receive(self, request):
                    return _Call()
            """
        ),
        "tests/other.py": textwrap.dedent(
            """\
            class Ticks:
                def __aiter__(self):
                    return self
            """
        ),
    }
    result = migrate(files, "0.35.5", "0.36.0")
    left = {
        (each["file"], each["line"])
        for each in as_json(result)["by_hand"]
        if each["rule"] == "receive-stand-in-read"
    }
    assert left == {("tests/sidecar_stream.py", 4)}


# ── 0.36.1 to 0.36.2: a row's valid time from the clock, left by hand ────


def test_0362_names_a_rows_valid_time_taken_from_the_clock() -> None:
    """The plugin step's chains plugins (databento, massive, tradier,
    unusual-whales): a series' terms and a statistic given the read's time
    as their valid time, under a key recorded again (the-lake rule 5). A
    source's own time, a key naming its moment's own value, and a test, are
    not named."""
    files = {
        "src/p/chains.py": textwrap.dedent(
            """\
            import time
            from meridian import helpers

            def rows(self, held, contract, now, at):
                series = helpers.option_series(
                    held, contract.osi, template_id="T", template_version="1",
                    dataset="d", currency="USD", exercise_style="E",
                    settlement_method="S", valid_from_ns=self.now(),
                )
                stat = helpers.statistic(held, [], "volume", 1, "2026-11-11",
                                         dataset="d", valid_from_ns=now)
                quote = Quote(meta=meta(row_key=f"{contract.osi}:q:{at}", valid_from_ns=at))
                published = helpers.statistic(held, [], "volume", 1, "2026-11-11",
                                              dataset="d", valid_from_ns=contract.published_ns)
                return series, stat, quote, published, meta(valid_from_ns=time.time_ns())
            """
        ),
        "tests/test_chains.py": "row = meta(valid_from_ns=self.now())\n",
    }
    result = migrate(files, "0.36.1", "0.36.2")
    assert result.files == {}, "nothing rewritten: only the pins move"
    assert left_by_hand(result) == [
        ("valid-time-from-the-clock", "src/p/chains.py", 8),
        ("valid-time-from-the-clock", "src/p/chains.py", 11),
        ("valid-time-from-the-clock", "src/p/chains.py", 15),
    ]
    (step,) = result.steps
    assert not step.migration.breaking
