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

PAGE = Path(__file__).resolve().parents[1] / "template" / "src" / "reference_plugin" / "page.py"


def load_page() -> ModuleType:
    spec = importlib.util.spec_from_file_location("reference_plugin_page", PAGE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ADA = meridian.Caller(
    subject="local|ada",
    display_name="Ada <Park>",
    access=(
        meridian.TagAccess(tag="brokerage", read=frozenset({"ACC-2", "ACC-1"})),
        meridian.TagAccess(tag="</script><b>x", write=frozenset({"ACC-3"})),
    ),
    header="h",
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


def test_the_page_links_the_kit_the_dashboard_serves() -> None:
    page = load_page()
    parsed = parse(page.render(ADA))
    links = [a.get("href") for t, a in parsed.tags if t == "link"]
    scripts = [a.get("src") for t, a in parsed.tags if t == "script" and a.get("src")]
    assert links == ["/.meridian/ui/0.1.0/meridian.css"]
    assert scripts == ["/.meridian/ui/0.1.0/meridian.js"]
    assert page.KIT == "/.meridian/ui/0.1.0/"


def test_the_page_is_built_from_the_kits_classes_and_components() -> None:
    text = load_page().render(ADA)
    parsed = parse(text)
    classes = {c for _, a in parsed.tags for c in (a.get("class") or "").split()}
    assert {"page", "page-head", "actions", "panel", "panel-body", "primary"} <= classes
    grids = [a for t, a in parsed.tags if t == "om-grid"]
    assert len(grids) == 1 and grids[0]["id"] == "access" and grids[0]["row-key"] == "tag"


def test_the_page_carries_no_colour_and_no_style_of_its_own() -> None:
    text = load_page().render(ADA, "Refused: no", refused=True)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", text), "a raw colour"
    assert not re.search(r"\b(rgba?|hsla?|oklch|color)\(", text), "a colour function"
    assert "<style" not in text and "style=" not in text, "the kit's classes, not its own"


def test_without_the_kit_the_table_and_the_action_are_still_there() -> None:
    parsed = parse(load_page().render(ADA))
    tags = [t for t, _ in parsed.tags]
    # The table is inside <om-grid>, shown as it is until the kit's grid takes over.
    assert tags.index("om-grid") < tags.index("table")
    forms = [a for t, a in parsed.tags if t == "form"]
    assert forms == [{"class": "inline", "method": "post", "action": "/statement"}]
    # The grid's data is read only once the kit has defined the grid.
    module = next(text for attrs, text in parsed.scripts if attrs.get("type") == "module")
    assert 'customElements.whenDefined("om-grid")' in module


def test_what_the_caller_sent_is_escaped_in_the_table_and_in_the_data() -> None:
    text = load_page().render(ADA)
    assert "Ada &lt;Park&gt;" in text
    assert "<b>x" not in text
    parsed = parse(text)
    data = next(t for a, t in parsed.scripts if a.get("id") == "access-rows")
    assert "</" not in data, "nothing in the data can close its script element"
    rows = json.loads(data)
    assert rows == [
        {"tag": "brokerage", "read": "ACC-1, ACC-2", "write": "none"},
        {"tag": "</script><b>x", "read": "none", "write": "ACC-3"},
    ]


def test_a_notice_says_which_it_is() -> None:
    page = load_page()
    assert '<div class="notice good" role="status">Opened' in page.render(ADA, "Opened it.")
    assert '<div class="notice bad" role="status">Refused' in page.render(ADA, "Refused.", True)
    assert "Nothing is granted to you here." in page.render(
        meridian.Caller(subject="s", display_name="Nobody", access=(), header="h")
    )
