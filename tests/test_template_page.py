"""The scaffold's page: built on the plugin UI kit, and working without it.

`meridian plugin new` copies template/, so this page is the first one anybody
builds. It must link the kit the dashboard serves on the plugin's own host,
use its classes and components, carry no colour of its own, and still show
its table and its action when the kit is not there. What it does with a real
sidecar is test_interop's.
"""

from __future__ import annotations

import html.parser
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

import meridian
from meridian.testing import PageClient

PAGE = Path(__file__).resolve().parents[1] / "template" / "src" / "reference_plugin" / "page.py"


def load_page() -> ModuleType:
    spec = importlib.util.spec_from_file_location("reference_plugin_page", PAGE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Stand:
    """What the pages reach of the plugin: who it was launched as, and a
    statement opened, which this sidecar refuses."""

    identity = meridian.Identity("reference-1", roles=("custody",))
    grants = meridian.Grants()

    async def record_holdings_statement(self, **_: object) -> None:
        raise meridian.NotGranted("RecordHoldingsStatement", "no sidecar here")


def ada(display_name: str = "Ada <Park>") -> PageClient:
    return PageClient(
        load_page().pages,
        Stand(),
        read={"ACC-2", "ACC-1", "</script><b>x"},
        write={"</script><b>x"},
        display_name=display_name,
    )


class Parsed(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.scripts: list[tuple[dict[str, str | None], str]] = []
        self._in: dict[str, str | None] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))
        if tag == "script":
            self._in = dict(attrs)
            self.scripts.append((self._in, ""))

    def handle_data(self, data: str) -> None:
        if self._in is not None:
            attrs, text = self.scripts[-1]
            self.scripts[-1] = (attrs, text + data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in = None


def parse(text: str) -> Parsed:
    parsed = Parsed()
    parsed.feed(text)
    return parsed


def test_every_page_links_the_kit_the_dashboard_serves() -> None:
    for rendered in ada().every_page():
        if rendered.response.status != 200:
            continue
        parsed = parse(rendered.response.text)
        links = [a.get("href") for t, a in parsed.tags if t == "link"]
        scripts = [a.get("src") for t, a in parsed.tags if t == "script" and a.get("src")]
        assert links == ["/.meridian/ui/0.9.0/meridian.css"], rendered.page.path
        assert scripts == ["/.meridian/ui/0.9.0/meridian.js"], rendered.page.path


def test_the_scaffold_has_one_manage_page_and_one_open_and_view_page() -> None:
    page = load_page()
    assert [(p.path, p.title, p.levels) for p in page.pages.declared] == [
        ("/setup", "Setup", (meridian.AccessLevel.ACCESS_LEVEL_ADMIN,)),
        (
            "/",
            "Accounts",
            (meridian.AccessLevel.ACCESS_LEVEL_WRITE, meridian.AccessLevel.ACCESS_LEVEL_READ),
        ),
    ]
    ada().assert_no_account_data("ACC-1", "ACC-2")


def test_the_page_is_built_from_the_kits_classes_and_components() -> None:
    parsed = parse(ada().get("/", "write").text)
    classes = {c for _, a in parsed.tags for c in (a.get("class") or "").split()}
    assert {"page", "page-head", "panel", "panel-body", "primary"} <= classes
    grids = [a for t, a in parsed.tags if t == "om-grid"]
    assert len(grids) == 1 and grids[0]["id"] == "access" and grids[0]["row-key"] == "account"


def test_the_pages_carry_no_colour_and_no_style_of_their_own() -> None:
    texts = [r.response.text for r in ada().every_page()]
    texts.append(ada().post("/statement", "write").text)  # a notice, refused
    for text in texts:
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", text), "a raw colour"
        assert not re.search(r"\b(rgba?|hsla?|oklch|color)\(", text), "a colour function"
        assert "<style" not in text and "style=" not in text, "the kit's classes, not its own"


def test_without_the_kit_the_table_and_the_action_are_still_there() -> None:
    parsed = parse(ada().get("/", "write").text)
    tags = [t for t, _ in parsed.tags]
    # The table is inside <om-grid>, shown as it is until the kit's grid takes over.
    assert tags.index("om-grid") < tags.index("table")
    forms = [a for t, a in parsed.tags if t == "form"]
    assert forms == [{"class": "inline", "method": "post", "action": "/statement"}]
    # The grid's data is in the page, read by the kit's grid: no script of its own.
    assert not [a for t, a in parsed.tags if t == "script" and a.get("type") == "module"]


def test_what_the_caller_sent_is_escaped_in_the_table_and_in_the_data() -> None:
    text = ada().get("/", "write").text
    assert "Ada &lt;Park&gt;" in text
    assert "<b>x" not in text
    parsed = parse(text)
    data = next(t for a, t in parsed.scripts if a.get("type") == "application/json")
    assert "</" not in data, "nothing in the data can close its script element"
    assert json.loads(data)["rows"] == [
        {"account": "</script><b>x", "may": "read and write"},
        {"account": "ACC-1", "may": "read"},
        {"account": "ACC-2", "may": "read"},
    ]


def test_a_notice_says_which_it_is() -> None:
    said = ada().post("/statement", "write").text
    assert '<div class="notice bad" role="status">Refused' in said
    nobody = PageClient(load_page().pages, Stand()).get("/", "read").text
    assert 'empty="Nothing is granted to you here."' in nobody
