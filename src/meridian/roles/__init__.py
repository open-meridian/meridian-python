"""Each role's common part, so a person who knows a role knows any plugin of
it (spec/plugin-pages-follow-their-role, accepted 2026-10-10).

Every plugin of a role has the same first-use path, the same pages, sections,
labels, verbs and order, the same "not set up yet" states naming the next
step, and the same Summary figures. Each module here holds its role's part:

- per common page, a record named `<Page>Read` holding the common fields,
  the page's tool's answer (`answers=`), which a plugin extends with its own;
- `figures(...)`, the role's figures in the role's order, for the plugin to
  follow with its own, within the eight the heartbeat carries;
- the role's common settings, beside `meridian.environment()` and
  `meridian.sample_data()`;
- the page templates `meridian/roles/<role>/<page>.html`, each extending
  `meridian/base.html`, drawing the common sections from the record, with
  the named extension points for the vendor's nuance: the blocks
  `vendor_notices`, `vendor_rows` (one per section, the section's title in
  `section`), `vendor_columns` (one per grid row, the row in `row`, None in
  the head) and `vendor_sections`.

    {% extends "meridian/roles/data/connection.html" %}
    {% block vendor_rows %}
    {% if section == "Key" %}<tr>…the feeds…</tr>{% endif %}
    {% endblock %}

Never at the leeway: renaming, reordering or dropping a common page,
section, row, column, label, verb, setting or figure. A vendor without a
common item says so in it ("Does not stream", "No key needed") rather than
leaving it out. The modules: `data`, `custody`, `operations`, `reporting`;
custody's, operations' and reporting's items are candidates, offered here,
until a second plugin of the role needs them (the spec's Q4).
"""

from . import custody, data, operations, reporting

__all__ = ["custody", "data", "operations", "reporting"]
