# meridian-python

The Python SDK for building [Open Meridian](https://open-meridian.com) plugins:
the tools a trader has an AI agent build, and the bots and analytics a
developer writes. Python 3.11 or newer. This is release 0.9.0; its reference
is at [open-meridian.dev](https://open-meridian.dev/api/python-sdk/).

## Start here

Start a plugin with the command line, not from this repository:

    meridian plugin new my-plugin
    meridian plugin dev --instance my-plugin   # on a deployment installed with --development

`plugin new` writes this repository's `template/`, the reference plugin: its
code and its page, built on the plugin UI kit (open-meridian/meridian-ui), its
tests, a CI workflow running `meridian plugin check --run-tests`, a
`Dockerfile`, and `AGENTS.md`, which teaches any coding agent to build pages
with the kit, hold the plugin to `meridian plugin check`, and the live loop
(`CLAUDE.md` and a Claude Code skill lead to it). meridian-cli vendors the
template at a pinned commit, so a CLI release carries it. See
[meridian-cli](https://github.com/open-meridian/meridian-cli).

## The SDK

A plugin talks only to its local sidecar. It holds no persistent state and seeds
from the deployment on start. Plugins themselves live in their own
repositories; this one stays thin.

Published to PyPI as `open-meridian`, imported as `meridian`:

    pip install open-meridian

The name `meridian-sdk` on PyPI is an unrelated company's. Do not install it.

The package carries the wire bindings it speaks to the sidecar with, as
`meridian.v1`, at the schema revision `SCHEMA_REV` in the Makefile names.
`make vendor-schema` moves them; `make check-vendored` fails when they lag.

```python
import meridian

async with await meridian.connect() as plugin:
    print(plugin.identity.instance_id, plugin.identity.roles, plugin.grants.publish)
    await plugin.report(healthy=True, detail="started")
```

The steps a plugin's roles may take are typed methods on the same `plugin`,
generated from the contract: `report_external_accounts`, `report_sync_status`,
`record_holdings_statement`, `record_holding`, `resolve_identifier`,
`report_missing_instrument`, `read_accounts_for_linking` and
`link_external_account`.

### Who is asking, and what they may do

A request for the plugin's page arrives with one `Meridian-Caller` header,
which its sidecar verified before forwarding. `meridian.Caller` reads it: who
the person is, the level their session was opened at, and the accounts that
level reaches through this plugin. A person may hold `admin` on a plugin and,
beside it, `read` or `write`, the same three for every plugin (decisions/026,
027), and opens it from the dashboard's home by a button per level held:
**Manage** at `admin`, **Open** at `write`, **View** at `read`. A session
carries only the level chosen, `caller.level`, a `meridian.AccessLevel`, and
its accounts are cut to it: under Open, `read`, what the plugin may show
them, and `write`, which it includes, what the plugin may do for them; under
View, `read` alone; under Manage (`caller.admin`), neither, since admin
configures a plugin and sees no account's data.

```python
caller = meridian.Caller.from_header(header)
shown = sorted(caller.read)  # every account the page may show them
if caller.may_write("ACC-1"):
    await plugin.record_holdings_statement(..., acting_for=caller.header)
```

`caller.read` and `caller.write` are the sets themselves. The sidecar checks
every command sent for the person again, whatever the plugin believes: it
admits one only in a session at `write`. `caller.deployment_admin` opens no
page; it says only that the person may name a new account when linking.
`meridian.TagAccess` and `Caller.access`, the same access tag by tag, are
gone, and say so when reached for.

### Pages, declared and enforced in one place

A plugin's pages are one list, each a path, a title and the levels it
serves; the dashboard shows under each button the pages whose levels include
its level, and one path may serve several, adapting by the session's level.
`meridian.Pages` declares a page where its view function is, sends the list
at registration, and answers 403 to a session at any other level before the
view runs:

```python
pages = meridian.Pages("Statements", templates=Path(__file__).parent / "templates")

@pages.page("/connections", "Connections", levels=["admin"])
async def connections(request: meridian.Request) -> str:
    return pages.render("connections.html", linked=...)  # no account's data

@pages.page("/", "Statements", levels=["write", "read"])
async def statements(request: meridian.Request) -> str:
    rows = [...]  # cut to request.caller.read
    return pages.render("statements.html", rows=rows)

@pages.route("/sync", levels=["write"], methods=["POST"])  # not a tab
async def sync(request: meridian.Request) -> str: ...

async with await meridian.connect(
    interface=meridian.Interface(port=8000, title="Statements", pages=pages)
) as plugin:
    pages.serve(plugin, 8000)  # the standard library's server; or pages.app(plugin), ASGI
```

`pages.render` renders a [Jinja2](https://jinja.palletsprojects.com)
template, autoescaped, with `caller` and `level` (admin, write or read)
always in its context. A page's template extends the kit's base template,
which links the kit the dashboard serves and draws the page's heading and the
tab row of the session's level (the kit drops both when the dashboard frames
the page):

```html+jinja
{% extends "meridian/base.html" %}
{% block status %}<om-status data-om-header state="ok" label="Synced"></om-status>{% endblock %}
{% block head_actions %}{% if level == "write" %}
  <form class="inline" method="post" action="/sync"><button data-om-action="sync">Sync</button></form>
{% endif %}{% endblock %}
{% block content %}
  <om-grid row-key="id"><script type="application/json">{{ grid | tojson }}</script></om-grid>
{% endblock %}
```

`status` and `head_actions` hand the frame the page's status dot and its
buttons, which the dashboard draws in its own header; `tojson` writes a kit
component's data safely inside its `<script>`; `{% include %}` and macros
compose a page from pieces.
`Page(path, title, levels=[...])` in `Interface(pages=...)` declares a page
served some other way, and `page.serves(caller)` checks it there.

**A request that changes something carries this plugin's CSRF token.** The
plugin's host keeps the person's session in a cookie, and every plugin's host
is the same site as the dashboard, so SameSite does not stop another plugin's
page from posting here as the person, and the plugin never sees the host it is
reached at to check an `Origin` against. So `Pages` refuses every request but
GET and HEAD, with 403 before the view runs, unless it carries back the token
only this plugin's page could have read: `{{ csrf_input }}` inside a form, or
the `X-CSRF-Token` header from a script (`request.csrf_token`). It is an HMAC
of the person and the session's level under a secret the process makes at
start, so a restart makes an open page's form stale until it is reloaded. A
GET changes nothing.

`meridian.testing.PageClient` asks the pages in a plugin's tests as the
sidecar would, at each level: `every_page()` renders each under Manage, Open
and View, and `assert_no_account_data(...)` fails when a page at `admin`
shows anything the plugin holds for an account.

`Interface(admin_pages=...)`, retired by contract v5, is still taken in this
release, as pages at `admin`, with a DeprecationWarning.

### Linking external accounts

A custody plugin links the external accounts it reported on one of its pages
at `admin`, for the admin of the plugin viewing it under Manage: pass the
`Meridian-Caller` header the page request carried as `acting_for`. The sidecar
refuses both outside a session at `admin`, answers every account's identity
and never its holdings, and refuses a link for an account the plugin did not
report; only a deployment admin may name a new account.

```python
accounts = await plugin.read_accounts_for_linking(acting_for=header)
await plugin.link_external_account(
    external_account_id="acct-1", account_id="ACC-1", acting_for=header
)
# Or a new account, created and linked in one step; or neither, to unlink.
await plugin.link_external_account(
    external_account_id="acct-2",
    new_account_name="Fidelity Roth",
    # Optional, free text, and ignored when linking to an existing account:
    # pre-fill what the venue reported, for the admin to change.
    new_account_custodian="Fidelity",
    new_account_type="Roth IRA",
    new_account_owner="Fund I",
    new_account_note="Linked from the Accounts tab.",
    acting_for=header,
)
```

Each account read carries its `custodian`, `account_type`, `owner` and `note`
beside its name and state, any of them empty, so a page can tell two accounts
of the same name apart. The conductor refuses more than 200 characters in the
first three, or 2,000 in the note, naming the field.

Which of its external accounts are linked, and to what, the plugin reads
beside its account scope, acting for nobody: the first delivery comes at once,
so a plugin just started has every link, and another comes whenever one is
made or removed or a linked account is renamed or closed. Hold the latest; a
plugin keeps nothing of its own across a restart.

```python
async for scope in plugin.account_scope():
    for link in scope.links:
        print(link.external_account_id, "->", link.account_id, link.account_name)
    scope.link_of("acct-3")  # None: not linked
```

A holding for an external account nothing links is refused, and raises
`meridian.NotLinked`, chosen by the code the sidecar sends beside the
refusal, never by its words. It is a `CallFailed` whose `kind` is
`"refused"`; the next statement after the account is linked records it.

```python
try:
    await plugin.record_holding(..., external_account_id="acct-3")
except meridian.NotLinked:
    ...  # offer it for linking; stop this statement
```

### Quantities and money

A quantity is a Python `Decimal` (or an `int`), and an amount of currency is a
`meridian.Money`, a `Decimal` and its ISO 4217 code:

```python
from decimal import Decimal
import meridian

await plugin.record_holding(
    statement_id=opened.statement_id,
    instrument_id=instrument_id,
    side=meridian.HoldingSide.HOLDING_SIDE_LONG,
    quantity=Decimal("12.5"),
    market_value=meridian.Money(Decimal("2812.50"), "USD"),
    external_account_id="acct-1",
)
```

Each crosses the wire as an integer and the scale it was stated with, so
`Decimal("2812.50")` is sent as 281250 at two places and reads back as
`Decimal("2812.50")` (`meridian.as_decimal`, `meridian.as_money`). Nothing is
rounded: a `float`, more than 18 decimal places, or more than 38 digits is
refused before anything is sent, naming the parameter.

**Say only what the venue said.** A holding states its side, and its quantity
is signed to match, negative short; a venue reporting an account's long and
short of one instrument apart is two calls, one on each side. A market value, a
settle-date quantity, and a statement's buying power and margin figures are
optional: leave one out where the venue reports none, which is not zero. Where
the venue states no currency and you assume one, pass `currency_assumed=True`.
Cash is a holding of the currency's cash instrument, which the security master
names by `iso4217` (`meridian.Identifier(scheme="iso4217", value="USD")`).

**The plugin that speaks to a venue converts; nothing after it does.** Keep
what the venue, broker or data vendor sent, as it sent it, in your own logs.
Put only the platform's convention on the bus: amounts in the currency's major
unit (dollars, not cents), quantities in the instrument's own units (shares,
not lots), at the instrument's precision. Whoever reads your messages next
cannot know which venue's convention they were in. A value the venue sent as a
float becomes `Decimal(repr(value))`, its shortest round-trip form, and never
`Decimal(value)`, which is its binary expansion: `Decimal(0.1)` is
0.1000000000000000055511151231257827021181583404541015625.

## Moving a plugin to a new release

    meridian plugin migrate            # to the latest release
    meridian plugin migrate --to 0.7.0

Every release that changes what a plugin calls carries a migration from the
release before it, and every other release one that only moves the pins, so
the steps from any recorded release to the newest exist and run in order
(decisions/025). `meridian plugin migrate` moves the plugin's two pins
(`open-meridian==<version>` in `pyproject.toml`, and the Dockerfile's
`plugin-python:<version>`), runs each step over its code, runs `meridian
plugin check`, and says what is left for a person or an agent to do, with the
file and line. The first recorded step is from 0.5.0.

The migrations live in this package, in `src/meridian/migrations/`, one
directory per step, released with the version they lead to:

- `migration.toml`, the record: `from` and `to`, a `summary`, whether a plugin
  that is not migrated `breaking`ly fails on the new release, what it
  `rewrites` and what it leaves `by_hand`, each a `rule` with `what` it covers
  and, for one left by hand, what to write `instead`. The record is data, so
  another SDK carries its own in the same shape.
- the rewrite code it names in `rewrite`, beside it, and none where only the
  pins move: a module with `rewrite(path, text)`, which returns the file
  rewritten and the rules that rewrote it, and `left(path, text)`, which
  returns what is still to do in the file once every step has run. It reads
  Python with [libcst](https://libcst.readthedocs.io), keeping the file's
  formatting and comments wherever it rewrites nothing, and names only rules
  its record has.

`python -m meridian.migrations --from 0.5.0 --to 0.7.0` runs the steps between
over the files it is given on stdin, as `{"files": {"<path>": "<text>"}}`,
and writes the steps, the new text of each file that changed, and what is
left by hand, as one JSON object; it writes no file. `--list` writes the
records. It needs the `migrate` extra (`pip install "open-meridian[migrate]"`),
which only the migration's own image installs: a plugin's runtime never
carries libcst.

| Step | Rewrites | Leaves by hand |
|---|---|---|
| 0.5.0 to 0.6.0: access is read or write, and a plugin declares no tags (decisions/026) | `tags` in `[tool.meridian]`; access gathered over the tags into `caller.read` or `caller.write`, `any(a in held.read for held in caller.access)` into `a in caller.read`; `Caller(access=(TagAccess(...), ...))` into `Caller(read=..., write=...)`; an unused import of `TagAccess` | access read by a tag's own name; `TagAccess` still named; `plugin.identity.tags`; declared tags, whose holders a deployment admin gives read or write |
| 0.6.0 to 0.6.1 | only the pins move | |
| 0.6.1 to 0.7.0: the unlinked refusal is `meridian.NotLinked` | a meridian error's words tested for "not linked" into `isinstance(err, meridian.NotLinked)`, and such a handler into `except meridian.NotLinked`; a test's `CallFailed(topic, "refused", "... is not linked ...")` into `NotLinked(topic, "...")` | the words matched anywhere else |
| 0.7.0 to 0.7.1: the SDK carries its migrations | only the pins move | |
| 0.7.1 to 0.8.0: the SDK declares contract v3 | only the pins move | |
| 0.8.0 to 0.9.0: the SDK declares contract v4; `asset_class` is an enum | `report_missing_instrument`'s `asset_class`, a string naming one of the seven classes in another case or with its prefix (`"EQUITY"`, `"asset_class_fund"`), into the class's spelling (`"equity"`, `"fund"`) | an `asset_class` string naming no class (`"etf"`, `"stock"`); one the migration cannot read, such as a variable, which must come to a class, an `AssetClass`, or `None` |
| 0.9.0 to 0.10.0: the SDK declares contract v5; pages carry their levels | `Interface(admin_pages=...)` into `pages=`, and a `Page(path, title)` naming no levels into `Page(path, title, levels=["admin"])` | `caller.deployment_admin` read to decide who is served, which opens no page since v5: declare the page at `admin` or ask `caller.admin`; `admin_pages` read as an attribute; admin pages passed as `Interface`'s third argument |

`tests/migrations/` holds the plugins the migrations are recorded for, as
written and as their migration leaves them, and `make check-migrations` holds
each result to `meridian plugin check --run-tests`.

## Working on it

    make ci-local

Run `make install-hooks` once on a fresh clone, so that `git push` fires
`ci-local` first. Without it the gate exists and does not run.

## Releasing

By hand, from the `publish` workflow: TestPyPI by default, PyPI when chosen,
with no token (trusted publishing). A real release then publishes the plugin
base image, `ghcr.io/open-meridian/plugin-python:<version>`, which a plugin's
`Dockerfile` builds on; a tag already published is never overwritten. A
release that changes what a plugin calls carries its migration from the
release before, and every other release one that only moves the pins.

## Licence

Apache-2.0, so a plugin you write stays yours. See [LICENSE](LICENSE).
