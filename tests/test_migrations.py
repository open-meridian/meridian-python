"""The migrations this SDK carries (decisions/025), over the plugins they are
recorded for.

`tests/migrations/` holds each plugin as it was written and as its migration
leaves it: desk, written against 0.5.0 and moved to this release, and
meridian-snaptrade's shape at 0.6.1. Each is migrated here as `meridian
plugin migrate` does it -- its pins moved, every step run in order -- and must
come out as its expected tree, with the same things left by hand, and pass
its own tests against this SDK. `make check-migrations` holds the same
results to `meridian plugin check --run-tests`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest

from meridian import migrations
from meridian.migrations import NoMigration, chain, migrate, recorded

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "migrations"
SDK = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def plugin_files(root: Path) -> dict[str, str]:
    """What `meridian plugin migrate` sends: the Python and pyproject.toml."""
    return {
        path.relative_to(root).as_posix(): path.read_text()
        for path in sorted(root.rglob("*"))
        if path.is_file() and (path.suffix == ".py" or path.name == "pyproject.toml")
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
    assert (steps[-1].source, steps[-1].target) == ("0.10.1", "0.11.0")
    # A release that moves the version records its step, if only the pins. The
    # step to the release being prepared is recorded before the release moves
    # the version, and is then the one step past it.
    after = [m for m in steps if migrations.version(m.target) > migrations.version(SDK)]
    assert steps[-1].target == SDK or (after == [steps[-1]] and steps[-2].target == SDK)


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


@pytest.mark.parametrize("fixture", ["desk-0.7.0", "snaptrade-0.7.0"])
def test_the_recorded_plugins_are_as_the_later_steps_leave_them(fixture: str) -> None:
    # Neither reports an asset class, so from 0.7.0 on only their pins move.
    result = migrate(plugin_files(FIXTURES / fixture), "0.7.0", SDK)
    assert result.files == {}
    assert left_by_hand(result) == []


# ── Held to the framework's rules ────────────────────────────────────────


@pytest.mark.parametrize(
    ("fixture", "source", "target"),
    [("desk-0.5.0", "0.5.0", "0.7.0"), ("snaptrade-0.6.1", "0.6.1", "0.7.0")],
)
def test_each_migrated_plugin_passes_plugin_check(
    tmp_path: Path, fixture: str, source: str, target: str
) -> None:
    """`meridian plugin check --run-tests` over each, as `meridian plugin
    migrate` runs it after the steps. `make check-migrations` installs the
    command line and requires this; elsewhere it is skipped without it."""
    meridian = shutil.which("meridian")
    if meridian is None:
        if os.environ.get("MERIDIAN_PLUGIN_CHECK") == "required":
            pytest.fail("meridian is not installed, and make check-migrations requires it")
        pytest.skip("meridian is not installed; make check-migrations runs this")
    migrated(fixture, source, target, tmp_path)
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
