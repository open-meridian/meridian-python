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

From 0.30.0 a role's module also carries the logic every plugin of the role
must do the same to fulfil its typed operations (sdk-contract/the-sdk-carries-
each-roles-common-logic, ruled 2026-10-13): `data`'s wants, standing wants,
recording, restart backfill and pages, with a venue's whole work by what it
lists (`data.pairs`, `data.event_contracts`); and `connectivity`, the
role's whole work over a venue's adapter (`Trader`) -- a placement sent at
most once, an unknown outcome resolved from the venue's orders, fills into
the book, cancels and replaces, pauses and stops -- and its Trading page.
How a plugin talks to its venue -- its client, its conversion, FIX, a
stream's transport -- is never here.

From 0.31.0 (contract v26) `pricing` holds a pricing plugin's work
(`Pricer`): each batch the analytics component routes to it answered whole,
the built-in models' own computation for a v26 model id (`reference_model`),
and the batches still waiting read after a restart.
"""

from . import connectivity, custody, data, operations, pricing, reporting

__all__ = ["connectivity", "custody", "data", "operations", "pricing", "reporting"]
