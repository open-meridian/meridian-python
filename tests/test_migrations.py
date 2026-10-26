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
    assert (steps[-1].source, steps[-1].target) == ("0.32.3", "0.33.0")
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
            ],
        ),
        (
            "snaptrade-0.7.0",
            [
                ("docs-not-in-image", "Dockerfile", 5),
                ("declaration-not-named", "pyproject.toml", 24),
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

        work = dgm.Dgm(Recorder("one"), pairs_venue.market(), products.ProductMap())
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
        trader = trading.Trader(Recorder("br"), lambda: None, now=lambda: datetime.now(UTC))
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
