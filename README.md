# meridian-python

The Python SDK for building [Open Meridian](https://open-meridian.com) plugins:
the tools a trader has an AI agent build, and the bots and analytics a
developer writes. Python 3.11 or newer. This is release 0.16.0; its reference
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

A plugin talks only to its local sidecar. Its process holds nothing it cannot
lose and seeds from the deployment on start; a plugin at the edge (custody,
servicing, settlement and the like) may also own the storage the deployment
grants its instance, for its raw external records (decisions/028). Plugins themselves live in their own
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

The SDK sends a heartbeat for the plugin every few seconds. The health a
plugin reports, with its detail, stands on every heartbeat after, as its
figures do: `report(healthy=False, detail="...")` keeps it not healthy
until it reports `healthy=True`.

The steps a plugin's roles may take are typed methods on the same `plugin`,
generated from the contract: `report_external_accounts`, `report_sync_status`,
`record_holdings_statement`, `record_holding`, `list_custodial_positions`,
`list_statements`, `resolve_identifier`, `report_missing_instrument`,
`read_accounts_for_linking` and `link_external_account`; and `receive`, for
what its roles hear.

A deployment's instrument records are its own (contract v10): a
`resolve_identifier` that matches nothing is answered with a record the
deployment minted, `reply.minted` true, and an `LCL-` ID is a record like any
other. A custody plugin states what its source says of the security --
`stated_asset_class`, `stated_currency`, `stated_description`, only what the
source states -- which the deployment keeps as offers for its admin to accept
at the dashboard's Instruments page, never in force by itself; a record read
with `resolve_instrument` says where each value came from (`sources`) and what
is offered beside it (`offers`).

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
A person who came through a client on a delegation -- the CLI, their own
agent, an MCP client -- rather than a browser carries `caller.delegation_id`
and `caller.client_name` (`caller.through_a_client`); both are empty for a
browser. The person stays the actor, and the sidecar stamps the delegation
beside them on every command sent for them (contract v9).
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

HEAD is answered for every path that takes GET, by its GET view, with the
headers and no body. A request whose body is over `Pages(max_body=...)` bytes,
1 MiB unless said (or `pages.serve(..., max_body=...)`), is answered 413
before any view runs, so a view need not measure what it is sent. The tab row
marks the tab the request is for, or, for a form's action that answers by
rendering a page, the tab it was posted from.

`meridian.testing.PageClient` asks the pages in a plugin's tests as the
sidecar would, at each level, and as a deployment admin with
`PageClient(..., deployment_admin=True)`: `every_page()` renders each under
Manage, Open and View, and `assert_no_account_data(*held)` fails when a page
at `admin` is not served under Manage, or shows any of `held` -- the account
data the test gave the plugin: holdings, quantities, values, balances,
statement rows -- as given or escaped. An account's identity (its ID, name,
custodian, type, owner and note) is not looked for, since a Manage page may
list every account of the deployment as a link target; a string the test
names is looked for whatever it is.

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
settle-date quantity, a holding's `cost_basis` (a total), `average_cost` (per
unit, in the venue's unit), `lots`, `margin_requirement`, `available_quantity`
and `not_available_quantity` with the `available_basis` they are on, each
encumbered sub-balance (`meridian.ReportedEncumbrance`: its kind, quantity and
the source's own code verbatim, `OTHER` for one you cannot map), a statement's
`security_interest`, and every figure of a statement are optional: leave one
out where the venue reports none, which is not zero, and never compute one
from another -- available is never the quantity less what is encumbered, and
no sub-balances means none reported. Where
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

### A statement's account and figures

A statement names the external account it was read for, as its rows do, and
the institution holding it where the connector knows it; the sidecar records
it against the account that external account is linked to, and refuses it,
`meridian.NotLinked`, where there is none. Its figures are a set per margin
segment, each naming its segment as the venue does, the one with no segment
being the account's as a whole, and each carrying the collateral held under
it:

```python
await plugin.record_holdings_statement(
    source="snaptrade",
    external_statement_id=f"{account}/{read_at_ns}",
    external_account_id=account,
    institution="Interactive Brokers",
    as_of_date="2026-09-08",
    read_at_ns=read_at_ns,
    expected_rows=len(rows),
    figures=[
        meridian.StatementFigures(
            segment="",
            buying_power=meridian.Money(Decimal("25000.00"), "USD"),
            net_liquidation=meridian.Money(Decimal("93550.00"), "USD"),
        ),
    ],
)
```

A number inside a set, a `meridian.ReportedCollateral` or a holding's
`meridian.ReportedLot` is converted and refused as a call's own is, naming its
path (`figures[0].collateral[1].haircut`). Two sets naming one segment, a
collateral balance neither posted nor received, and the three flat figures a
plugin before 0.12.0 sent beside `figures` are refused before anything is
sent.

### Hearing what other plugins do

A plugin whose roles hear rows -- an `operations` plugin hears the street's
statements and positions -- gives a handler per row to `receive`, which runs
until cancelled:

```python
async def statement_recorded(heard: meridian.Heard) -> None:
    statement = heard.message  # the whole statement, as the store announced it
    ...

async def custodial_position_updated(heard: meridian.Heard) -> None:
    position = heard.message.position  # removed=True when it was removed
    ...

await plugin.receive(
    statement_recorded=statement_recorded,
    custodial_position_updated=custodial_position_updated,
)
```

It reads the store first, every row's records across the plugin's read
scope, then hands on each change heard, once and in order. Deliveries are at
most once, so where one was missed -- a gap in an account's changes, a loss
the sidecar marked, a stream that broke, an account entering the read scope
-- it reads the changes since from the store and hands them on before
anything heard after, `heard.caught_up` saying so. A handler never sees the
store's numbers. `heard.own` says the plugin's own act caused the change, and
`heard.cause` who did, where the store recorded it. `seed=False` reads the
store without handing on what it holds. The reads are typed methods too,
`list_custodial_positions` and `list_statements`, within the read scope: an
account outside it is refused, and an empty scope reads nothing.

### The book of record

The street holds what custodians say; the book of record holds what the firm
says (contract v8). An account enters it once, with an opening balance a
person answers for, and changes after that only by the book's own entries;
an `operations` plugin compares it with the street and records each
difference as a break, which a person resolves with a justified entry or
closes. `portfolio`, `reporting`, `compliance` and `oms` read and hear it.

```python
reply = await plugin.record_opening_balance(
    account_id=account,
    as_of_date="2026-09-08",
    sources=[meridian.OpeningSource(kind="custodian", name="Interactive Brokers",
                                    as_of_date="2026-09-08", basis="trade_date")],
    positions=[...],                   # each with its lots, as the custodian reports them
    reason=reason,                     # the person's own words
    idempotency_key=f"opening-balance:{account}:{statement_id}",
    acting_for=request.caller.header,  # the person confirming it
)
```

Each command answers after its entry commits, with every record it changed;
the same `idempotency_key` again is answered as the first was and applies
nothing. A break and the figures are findings, sent as the plugin itself; an
opening balance, a break's cause and handling, and its resolution are a
person's, sent `acting_for` them with a reason, as is
`close_breaks_as_cleared`, citing the statement where the differences were
gone. A message with a oneof takes one arm by keyword: a break's `position=`
or `figure=`, a resolution's `adjustment=`, `reversal=`, `entries=` or
`explanation=`, a basis adjustment's `cost_change=` or `stated_cost=`; two at
once are refused naming the oneof. A position under a record the deployment
admin merges into another is moved onto the one that stays. What of a position
cannot move is recorded from each statement with `record_encumbrances`, a
finding sent as the plugin itself, the whole set per position; the position
then carries its `encumbrances` and the `free_quantity` the book derives
from them, on its `free_basis` (settled). The book refuses with a
code, raised as `meridian.CommandRefused`; a different command under a key
already used is `REFUSAL_REASON_IDEMPOTENCY_CONFLICT`. From contract v9 the
book refuses an entry missing what tax tracking, valuation, confirmation or
settlement need -- an opening position's settled quantity, a pending
quantity's value date, its lots (but cash's), a lot's cost or acquisition
date, a named source -- with `REFUSAL_REASON_INCOMPLETE`, each missing field
in `refused.fields` by its path in the call; a lot of unknown cost and the
not-stated settlement bucket are no longer admitted. From contract v10 it
also requires each instrument's asset class and currency, naming
`positions[0].instrument.asset_class` and `.currency` when the record lacks
them, which the deployment admin completes at the dashboard's Instruments
page; and a command it could not check because the instrument store did not
answer is `REFUSAL_REASON_REFERENCE_UNAVAILABLE`, `refused.retryable`, nothing
recorded and the same command safe to send again:

```python
try:
    await plugin.record_opening_balance(..., acting_for=caller.header)
except meridian.CommandRefused as refused:
    if refused.reason_name == "REFUSAL_REASON_OPENING_BALANCE_RECORDED":
        ...  # already recorded: read it back and say so
    elif refused.reason_name == "REFUSAL_REASON_INCOMPLETE":
        ...  # show what is missing: ("positions[0].settled_quantity", ...)
    elif refused.retryable:
        ...  # the instrument store did not answer: send the same command again
```

The reads -- `list_positions` (by business date, at a watermark, or since
one), `list_breaks`, `list_account_figures` and `list_account_attributes`,
whose attributes carry the account's standing opening balance -- are within
the read scope, and `receive` takes `position_changed`, `break_changed`,
`account_figures_recorded` and `account_attribute_changed` handlers, each
record delivered whole.

### The edge keeps its own (contract v11)

A plugin at the edge converts its vendor's words to the contract's, and keeps
what it converted from (sdk-contract/the-edge-keeps-its-own;
spec/vendor-differences-have-a-place-in-the-contract):

```python
from decimal import Decimal

import meridian
from meridian import edge
from meridian.declaration import Declaration, NotCarried, Storage

DECLARATION = Declaration(
    settings=SETTINGS,  # its secret settings' names are declared, never a value
    not_carried=[NotCarried("custody", "myvendor:position", "open_pnl",
                            "no_contract_meaning")],
    storage=Storage(retention_days=30),
)

async with await meridian.connect(settings=SETTINGS, declaration=DECLARATION) as plugin:
    await plugin.record_holding(
        ...,
        raw_record=plugin.raw_record("ACCT-1/20261003T120000Z/positions"),
        provenance=[edge.derived("settle_date_quantity", "quantity less unsettled trades")],
        pending=[meridian.ReportedPending(value_date="2026-10-05", quantity=Decimal("5"))],
    )
    plugin.note_not_carried("myvendor:position", "open_pnl")
```

- **The declaration** (`meridian.Declaration`) goes with registration, and
  `meridian plugin upload` reads the same one from the built image when
  pyproject.toml's `[tool.meridian]` names it (`declaration =
  "my_plugin.declaration:DECLARATION"`; `meridian-declaration` prints it as
  JSON). Without one, a plugin declares its secret settings' names alone.
  Storage is for a plugin holding an edge role only.
- **The raw record**: every row and statement names the record in the
  plugin's own storage it was converted from, by the plugin's own key;
  `plugin.raw_record(key)` names this instance, and the sidecar refuses
  another's. The storage is the deployment's grant to the instance,
  `edge.storage_dir()`, None where none is granted.
- **Provenance**: a value the vendor did not send, and the plugin closed,
  says how: `edge.derived(field, rule)`, `edge.supplied(field, person)`,
  `edge.second_source(field, source)`, or `edge.reported(field, raw_record)`.
- **As reported**: a value that does not convert travels as the field's
  not-known value with the vendor's beside it, `edge.as_reported(scheme,
  code, text)`: an account's kind (`account_kind`,
  `account_kind_as_reported`; the venue's own type is deprecated), and a
  miss's asset class (`asset_class_as_reported`).
- **Each asset once**: a custody plugin sends the cash of a currency net of
  any holding the custodian also counts as cash, with that provenance, and
  withholds a statement it cannot serve clean; `also_counted_in_cash` and
  `currency_assumed` are deprecated. The settled quantity and the pending by
  value date (`meridian.ReportedPending`) are the custody role's.
- **A backfill**: a row sent again under its statement with a field a
  revision added, `backfill=edge.backfill("v11", "raw_record")`, is journaled
  beside the row as first recorded.
- **The role's suite**: `meridian.suites.run("custody", producers)` runs each
  case of the role's suite (vendored with the bindings, `suites.json`)
  against the plugin's own conversion, recorded by a `Recorder` rather than
  sent; a plugin is verified for its role by passing every case. A resolve
  may state a money market fund (`stated_instrument_type`).

### Figures on Summary

Manage opens on the plugin's Summary, which core draws: its own status first
(health and why, the versions, restart), then a few figures the plugin
reports about its own work, each a tile. A plugin gives them on its heartbeat
and builds no summary page of its own:

```python
from datetime import datetime, timezone
import meridian

plugin.figures = [
    meridian.Figure("Connections", 3, state="warn",
                    why="1 connection needs attention: the brokerage asked to reconnect"),
    meridian.Figure("Accounts reached", 7),
    meridian.Figure("Last read", datetime.now(timezone.utc)),
]
```

A value is an `int` (a count), a `Decimal`, a `str` (a text) or a
timezone-aware `datetime` (a time). `as_of` says when it was true, where
that is not now; `state` is `"ok"`, `"warn"` or `"error"`, the tile's mark,
and `why` the note beside it. The list goes on every heartbeat from the next
on, in its order, each replacing the last, and an empty list clears it;
`await plugin.report(healthy=True, figures=[...])` sends it at once. A figure
names no account and carries none of an account's data: Manage shows none.

At most 8; a label of 1 to 40 characters, given once; a text of at most 40;
a why of at most 200; a decimal within what the wire carries. The bounds are
`meridian.bounds`', generated from the data dictionary
(`HEARTBEAT_REQUEST_FIGURES_COUNT`, `PLUGIN_FIGURE_LABEL_LENGTH`,
`PLUGIN_FIGURE_TEXT_LENGTH`, `PLUGIN_FIGURE_WHY_LENGTH`); 0.16.0 moved
`meridian.figures.MOST_FIGURES` and its `LONGEST_*` there. Anything past
a bound is refused at the line that sets it, in the words the sidecar would
refuse it with, and nothing is sent. In a plugin's tests,
`meridian.testing.heartbeat(figures=[...])` is the heartbeat its sidecar
receives, or the refusal.

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
| 0.10.0 to 0.10.1: pages answer HEAD and refuse a large body; `assert_no_account_data` looks for account data, not identities | only the pins move | |
| 0.10.1 to 0.11.0: the SDK declares contract v6; a plugin may report figures on its Summary (`plugin.figures`, `meridian.Figure`); a reported health stands until reported again | only the pins move | |
| 0.11.0 to 0.12.0: the SDK declares contract v7; `receive`, the street's reads, a statement's external account and figures per segment, a holding's cost and lots. Breaking | a statement's flat `buying_power`, `margin_requirement` and `maintenance_excess` into `figures=[StatementFigures(segment="", ...)]` | a statement naming no `external_account_id`, which a sidecar at v7 refuses: pass the external account it was read for, and its `institution` |
| 0.12.0 to 0.13.0: the SDK declares contract v8; the book of record's operations, reads and deliveries, a oneof taken by keyword, `CommandRefused` with the book's codes, what of a holding cannot move, and the book's encumbrances with their free quantity | only the pins move | |
| 0.13.0 to 0.14.0: the SDK declares contract v9; `CommandRefused.fields` names what an incomplete entry left out (`REFUSAL_REASON_INCOMPLETE`); `Caller.delegation_id` and `Caller.client_name` | only the pins move | |
| 0.14.0 to 0.15.0: the SDK declares contract v10; a deployment's instrument identity is its own: `ResolveIdentifierResult.minted`, a resolve's `stated_*` values, a record's `sources` and `offers`, the book's refusal of an incomplete instrument record and `CommandRefused.retryable`, the book's actor naming the delegation and client. Breaking | a resolve result's `.placeholder` into `.minted` | a book position's `.placeholder`, which is gone: drop it, and link the person to the dashboard's Instruments page where the book refuses an incomplete record |
| 0.15.0 to 0.16.0: the SDK declares contract v11, the edge keeps its own: the version's declaration (`meridian.Declaration`, `connect(declaration=...)`, `meridian-declaration`), a row's raw record and provenance (`plugin.raw_record`, `meridian.edge`), the account kind and values as reported, each asset counted once, pending by value date (`meridian.ReportedPending`), a backfill, the stated instrument type, the custody suite (`meridian.suites`), names not carried counted on the heartbeat (`plugin.note_not_carried`); `meridian.ExternalAccount` is the SDK's form; `meridian.figures.MOST_FIGURES` and `LONGEST_*` moved to `meridian.bounds` | nothing | an ExternalAccount's `venue_account_type=`, a holding's `also_counted_in_cash=`, `currency_assumed=`, each replaced by the plugin's own conversion; a read of `meridian.figures`' moved bounds |

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
