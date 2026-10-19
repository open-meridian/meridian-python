"""Contract v25 (sdk-contract/plugins-are-shared-and-documented-contract):
the whole declaration and the vendor's documentation.

What this SDK decides (plans/a-plugin-carries-its-own-documentation): the
declaration carries what registration sends -- its settings, interface,
tools and whether it reads external accounts -- and names each section of
the plugin's `docs/` by its digest and size, read from the files and never
parsed; `meridian-declaration --documentation` prints the texts the upload
sends; `connect` registers the declaration's interface, refusing a different
one as it refuses different settings. Holding a registration to the version
uploaded is the sidecar's, stood in for here as core's sidecar holds it.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import meridian
from meridian.declaration import (
    _DOCUMENTATION_BUNDLE_BYTES,
    _SECTIONS,
    Declaration,
    RecordKind,
    Storage,
    _read_documentation,
    main,
)
from meridian.v1 import sidecar_pb2

SETTINGS = (meridian.Setting(name="api_key", label="API key", secret=True, required=True),)


@dataclasses.dataclass(frozen=True)
class Connections:
    connections: list[str]


def _pages() -> meridian.Pages:
    pages = meridian.Pages("Desk")

    @pages.page("/", "Desk", levels=["write", "read"])
    async def home(request: meridian.Request) -> str:
        return ""

    @pages.page(
        "/connections",
        "Connections",
        levels=["admin"],
        answers=Connections,
        name="read_connections",
    )
    async def connections(request: meridian.Request) -> meridian.Response:
        """Each connection and when it last read."""
        return pages.answer("", {"connections": []})

    return pages


def _docs(root: Path, **texts: str | bytes) -> Path:
    folder = root / "docs"
    folder.mkdir()
    for name, text in texts.items():
        data = text if isinstance(text, bytes) else text.encode()
        (folder / f"{name}.md").write_bytes(data)
    return folder


def test_the_schema_is_contract_v25_or_later() -> None:
    assert int(meridian.SCHEMA_VERSION.removeprefix("v")) >= 25
    assert "documentation" in sidecar_pb2.PluginDeclaration.DESCRIPTOR.fields_by_name
    assert "affirmation_deadline" in sidecar_pb2.PluginDeclaration.DESCRIPTOR.fields_by_name


# ── The documentation ───────────────────────────────────────────────────────


def test_each_section_is_named_by_its_digest_and_size_in_the_fixed_order(
    tmp_path: Path,
) -> None:
    folder = _docs(
        tmp_path,
        terms="# Terms\n\nThe vendor's terms.\n",
        overview="# Overview\n\nWhat it does — in a sentence.\n",
        setup="# Setup\r\n\r\nWindows line endings, kept as written.\r\n",
    )
    (folder / "README.md").write_text("The repository's own index, never uploaded.")
    found = _read_documentation(folder)
    assert [section.name for section in found] == ["overview", "setup", "terms"]
    for section in found:
        data = (folder / f"{section.name}.md").read_bytes()
        assert section.markdown.encode() == data
        assert section.bytes == len(data)
        assert section.digest == f"sha256:{hashlib.sha256(data).hexdigest()}"
    assert _SECTIONS == ("overview", "setup", "troubleshooting", "terms", "pages")


@pytest.mark.parametrize(
    ("text", "says"),
    [
        (b"", "1 to 65,536 bytes"),
        (b"x" * 65_537, "1 to 65,536 bytes"),
        (b"\xff\xfe not text", "not UTF-8"),
    ],
)
def test_a_section_out_of_bounds_or_not_text_is_refused_naming_its_file(
    tmp_path: Path, text: bytes, says: str
) -> None:
    folder = _docs(tmp_path, overview=text)
    with pytest.raises(ValueError, match=says) as refused:
        _read_documentation(folder)
    assert "overview.md" in str(refused.value)


def test_the_sections_together_are_held_to_the_bundles_bound(tmp_path: Path) -> None:
    each = b"x" * 60_000
    folder = _docs(tmp_path, **{name: each for name in _SECTIONS})
    assert 5 * len(each) > _DOCUMENTATION_BUNDLE_BYTES
    with pytest.raises(ValueError, match="262,144"):
        _read_documentation(folder)


def test_a_folder_that_is_not_there_is_refused_saying_where_it_was_looked_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    declared = Declaration(documentation="docs")
    with pytest.raises(ValueError, match="relative to where the plugin runs"):
        declared.to_wire()


def test_the_declaration_reads_its_folder_where_the_plugin_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _docs(tmp_path, overview="# Overview\n", setup="# Setup\n")
    monkeypatch.chdir(tmp_path)
    wire = Declaration(documentation="docs").to_wire()
    assert [(held.name, held.bytes) for held in wire.documentation] == [
        ("overview", 11),
        ("setup", 8),
    ]
    assert Declaration().to_wire().documentation == []


# ── The whole declaration ───────────────────────────────────────────────────


def test_the_declaration_carries_what_registration_sends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _docs(tmp_path, overview="# Overview\n", setup="# Setup\n")
    monkeypatch.chdir(tmp_path)
    interface = meridian.Interface(port=8000, title="Desk", pages=_pages())
    declared = Declaration(
        settings=SETTINGS,
        interface=interface,
        reads_external_accounts=True,
        documentation="docs",
    )
    wire = declared.to_wire()
    assert [held.name for held in wire.settings] == ["api_key"]
    assert wire.settings[0] == SETTINGS[0]._declared()
    assert wire.interface == interface._declared()
    assert [tool.name for tool in wire.tools] == ["read_connections"]
    assert wire.reads_external_accounts is True
    assert list(wire.secret_settings) == ["api_key"]

    printed = declared.to_json()
    assert printed["interface"]["loopback_port"] == 8000
    assert printed["interface"]["pages"][1]["levels"] == ["ACCESS_LEVEL_ADMIN"]
    assert [tool["name"] for tool in printed["tools"]] == ["read_connections"]
    assert printed["reads_external_accounts"] is True
    assert [held["name"] for held in printed["documentation"]] == ["overview", "setup"]
    assert printed["settings"][0]["secret"] is True
    assert "affirmation_deadline" not in printed


def test_an_affirmation_deadline_is_an_operations_plugins_minutes_after_midnight() -> None:
    declared = Declaration(affirmation_deadline=21 * 60)
    assert declared.to_wire().affirmation_deadline == 1260
    assert declared.to_json()["affirmation_deadline"] == 1260
    assert declared.refused_for(["operations"]) is None
    assert "not holding operations" in (declared.refused_for(["custody"]) or "")
    for wrong in (-1, 1441, True, "21:00"):
        with pytest.raises(ValueError, match="minutes after midnight"):
            Declaration(affirmation_deadline=wrong)  # type: ignore[arg-type]


def test_the_restore_route_is_in_the_declarations_tools_before_any_connect() -> None:
    pages = _pages()
    declared = Declaration(
        settings=SETTINGS,
        storage=Storage(kinds=[RecordKind("activity", "Activity", window_days=30)]),
        interface=meridian.Interface(port=8000, title="Desk", pages=pages),
    )
    tools = [tool.name for tool in declared.to_wire().tools]
    assert "restore_unit" in tools
    # The SDK's window settings follow from the kinds and the deployment's
    # archive, and are not the declaration's own.
    assert [held.name for held in declared.to_wire().settings] == ["api_key"]
    assert tools == [tool.name for tool in declared.to_wire().tools], "declared once"


# Read where `meridian-declaration` runs, as in the image.
DOCUMENTED = Declaration(settings=SETTINGS, documentation="docs")


def test_meridian_declaration_prints_the_texts_the_upload_sends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _docs(tmp_path, overview="# Overview\n\nSee [setup](setup.md).\n", setup="# Setup\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent))

    assert main(["--documentation", "tests.test_v25:DOCUMENTED"]) == 0
    texts = json.loads(capsys.readouterr().out)
    assert [text["section"] for text in texts] == ["overview", "setup"]

    assert main(["tests.test_v25:DOCUMENTED"]) == 0
    declared = json.loads(capsys.readouterr().out)
    for text, named in zip(texts, declared["documentation"], strict=True):
        data = text["markdown"].encode()
        assert named["name"] == text["section"]
        assert named["digest"] == f"sha256:{hashlib.sha256(data).hexdigest()}"
        assert named["bytes"] == len(data)

    assert main(["--documentation"]) == 2
    assert main(["--documentation", "a:b", "c:d"]) == 2


# ── connect ─────────────────────────────────────────────────────────────────


async def test_connect_registers_the_declarations_interface(sidecar: Any) -> None:
    service, address = sidecar
    interface = meridian.Interface(port=8000, title="Desk", pages=_pages())
    declared = Declaration(settings=SETTINGS, interface=interface, reads_external_accounts=True)
    service.uploaded = declared.to_wire()
    plugin = await meridian.connect(address, heartbeat=False, declaration=declared)
    await plugin.leave()
    sent = service.registered[0]
    assert sent.interface == interface._declared()
    assert [tool.name for tool in sent.tools] == ["read_connections"]
    assert sent.reads_external_accounts is True
    assert sent.declaration == service.uploaded


async def test_connect_refuses_an_interface_its_declaration_does_not_name(sidecar: Any) -> None:
    service, address = sidecar
    declared = Declaration(
        settings=SETTINGS, interface=meridian.Interface(port=8000, title="Desk", pages=_pages())
    )
    other = meridian.Interface(port=8001, title="Desk", pages=_pages())
    with pytest.raises(ValueError, match="interface and its declaration's interface differ"):
        await meridian.connect(address, heartbeat=False, declaration=declared, interface=other)
    assert service.registered == []
    # The same interface, made twice, is the same.
    same = meridian.Interface(port=8000, title="Desk", pages=_pages())
    plugin = await meridian.connect(
        address, heartbeat=False, declaration=declared, interface=same
    )
    await plugin.leave()


async def test_connect_warns_of_what_it_names_and_the_declaration_does_not(
    sidecar: Any,
) -> None:
    service, address = sidecar
    interface = meridian.Interface(port=8000, title="Desk", pages=_pages())
    with pytest.warns(UserWarning, match="connect names interface, reads_external_accounts"):
        plugin = await meridian.connect(
            address,
            heartbeat=False,
            declaration=Declaration(settings=SETTINGS),
            interface=interface,
            reads_external_accounts=True,
        )
    await plugin.leave()
    sent = service.registered[0]
    assert sent.declaration.interface == sent.interface
    assert sent.declaration.reads_external_accounts is True


# ── Registration held to the version (the sidecar's, stood in for) ──────────


async def test_a_registration_differing_from_its_upload_is_refused_naming_the_difference(
    sidecar: Any,
) -> None:
    service, address = sidecar
    pages = _pages()
    uploaded = Declaration(
        settings=SETTINGS, interface=meridian.Interface(port=8000, title="Desk", pages=pages)
    )
    service.uploaded = uploaded.to_wire()

    @pages.page("/later", "Later", levels=["admin"], answers=Connections, name="read_later")
    async def later(request: meridian.Request) -> meridian.Response:
        """A tool its upload did not declare."""
        return pages.answer("", {})

    with pytest.raises(meridian.Refused) as refused:
        await meridian.connect(address, heartbeat=False, declaration=uploaded)
    assert refused.value.reason.startswith(
        "declaration.interface.pages: 2 declared, 3 registered"
    )


async def test_a_declaration_differing_from_the_request_is_refused(sidecar: Any) -> None:
    service, address = sidecar
    declared = Declaration(settings=SETTINGS)
    wire = declared.to_wire()
    request = sidecar_pb2.RegisterRequest(
        schema_version="v25",
        settings=[setting._declared() for setting in SETTINGS],
        declaration=wire,
        reads_external_accounts=True,
    )
    assert service._declaration_refused(request).startswith(
        "declaration.reads_external_accounts: False declared, True registered"
    )
    request.schema_version = "v24"
    assert service._declaration_refused(request) == "", "a v24 plugin is admitted unchecked"


async def test_the_window_settings_are_left_out_of_the_comparison(sidecar: Any) -> None:
    service, address = sidecar
    declared = Declaration(
        settings=SETTINGS,
        storage=Storage(kinds=[RecordKind("activity", "Activity", window_days=30)]),
    )
    service.uploaded = declared.to_wire()
    plugin = await meridian.connect(address, heartbeat=False, declaration=declared)
    await plugin.leave()
    sent = service.registered[0]
    assert {held.name for held in sent.settings} == {
        "api_key",
        "activity_window_days",
        "activity_past_window",
    }
    assert [held.name for held in sent.declaration.settings] == ["api_key"]


def test_a_declaration_replaced_keeps_nothing_read_from_another_folder(tmp_path: Path) -> None:
    first = _docs(tmp_path, overview="# One\n")
    declared = Declaration(documentation=first)
    assert declared._sections()[0].markdown == "# One\n"
    second = tmp_path / "other"
    second.mkdir()
    (second / "overview.md").write_text("# Two\n")
    assert (
        dataclasses.replace(declared, documentation=second)._sections()[0].markdown == "# Two\n"
    )


# ── The templates ───────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = "import sys; from meridian.declaration import main; sys.exit(main(sys.argv[1:]))"
TEMPLATES = [ROOT / "template", *sorted((ROOT / "templates").iterdir())]


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda path: path.name)
def test_each_template_declares_its_interface_and_documentation(template: Path) -> None:
    """As `meridian plugin upload` reads it from the built image: from the
    plugin's root, the declaration pyproject.toml names, printed with its
    documentation's digests, and the texts beside it."""
    import subprocess
    import sys
    import tomllib

    named = tomllib.loads((template / "pyproject.toml").read_text())["tool"]["meridian"][
        "declaration"
    ]
    sdk = Path(meridian.__file__).resolve().parents[1]
    env = {"PYTHONPATH": f"{template / 'src'}:{sdk}", "PYTHONDONTWRITEBYTECODE": "1"}

    def printed(*args: str) -> Any:
        ran = subprocess.run(
            # As the `meridian-declaration` script runs it.
            [sys.executable, "-c", _SCRIPT, *args, named],
            cwd=template,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert ran.returncode == 0, ran.stderr
        return json.loads(ran.stdout)

    declared = printed()
    texts = printed("--documentation")
    assert [held["name"] for held in declared["documentation"]] == list(_SECTIONS)
    for text, held in zip(texts, declared["documentation"], strict=True):
        data = text["markdown"].encode()
        assert held["digest"] == f"sha256:{hashlib.sha256(data).hexdigest()}"
    assert declared["interface"]["loopback_port"] == 8000
    main_py = (template / "src" / "reference_plugin" / "__main__.py").read_text()
    assert "PAGE_PORT" not in main_py, "the port is the declaration's, never the environment's"
    assert "connect(declaration=DECLARATION)" in main_py
