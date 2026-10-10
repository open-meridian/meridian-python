# meridian-python

The Python SDK for building [Open Meridian](https://open-meridian.com) plugins:
the tools a trader has an AI agent build, and the bots and analytics a
developer writes. Python 3.11 or newer. This is release 0.23.0; its reference
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

`plugin new --role dgm` and `--role reporting` write `templates/dgm/` and
`templates/reporting/` instead: a `dgm` putting a stand-in vendor's prices
into the lake, its catalogue declared, its Connection and Datasets pages
with their read tools, and its tests running the `dgm` suite; and a
`reporting` plugin valuing the book's positions at the close from the lake,
its Closes page with its read tool, `read_report`, and its tests running the
`reporting` suite. Each is a whole plugin, its agents'
files, CI and `Dockerfile` the reference plugin's own.

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

### Access per role (contract v15)

A person's level is granted on each role of a plugin (decisions/033): write on
its `operations` and read on its `custody`, or admin on its `custody` alone.
The home offers the same three buttons, and a session carries the person's
entry for each role within its button: `caller.roles`, each role's level, and
`caller.level_for(role)`, `caller.read_for(role)` and `caller.write_for(role)`
-- under Open a role held at write is at write and one held at read at read,
under View each at read, under Manage each role administered at admin with no
account. `caller.level`, `read` and `write` stay the session's button and the
union over its roles. The sidecar admits a command sent for the person only
when they hold write on the role whose grants include it, the account among
that role's write accounts, and otherwise refuses it naming the role
("RecordHoldingsStatement is custody's, and Ada Park holds read on custody").

```python
@pages.page("/statements", "Statements", roles=["custody"], levels=["write", "read"])
async def statements(request: meridian.Request) -> str:
    caller = request.caller
    rows = [...]  # cut to caller.read_for("custody")
    return pages.render("statements.html", rows=rows,
                        may_record=bool(caller.write_for("custody")))

@pages.page("/blotter", "Blotter", roles=["custody", "operations"], levels=["write", "read"])
async def blotter(request: meridian.Request) -> str: ...  # each role's rows by read_for(role)

settings = [meridian.Setting("api_key", secret=True, roles=["custody", "operations"])]
```

A page, route, tool and setting names the roles it serves with `roles=`, from
those the plugin was launched with: a page is served, and its tab shown, when
the person's level on one of its roles within the button is one of its
levels, and `Pages` answers 403 before the view otherwise, naming the roles
and what the session holds on each; a derived tool takes its route's roles
(`@pages.tool(..., roles=)` to name others); a setting is shown to an admin of
any of its roles and set only by one holding admin on every one. **A plugin
holding one role, or none, names none, and nothing changes**: the sidecar
serves its declarations that role. A plugin holding several names roles on
every declaration, and the sidecar refuses its registration for one naming
none, or a role it was not launched with, naming it. A declaration's roles
decide what is shown, never what is admitted. Claims carrying no per-role
entry -- a plugin holding no role, or a dashboard before v15 -- read every
role as the session's level and accounts.

`PageClient(pages, roles=["custody", "operations"])` holds a two-role plugin
to it in its tests: its person holds every level on each role,
`caller(level, roles=...)`, `request`, `post` and `call_tool` take `roles=`
to narrow a session (`{"operations": "write", "custody": "read"}` gives each
role its own level within Open), and `every_page()` renders each page under
each level for each role alone and for all of them together, which
`assert_no_account_data` holds to under Manage. `caller_header(level,
roles=...)` builds the header itself.

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
marks the tab the request is for, or the one its path is under
(`/raw/archive` marks `/raw`), or, for a form's action that answers by
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

### Tools for agents, from typed routes (contract v12)

A deployment serves one MCP surface at its dashboard's `/mcp`, where an agent a
person delegated to works on their behalf. A plugin's tools are derived from
its routes: a route that declares its inputs as one typed record is a tool,
an act for a method that changes something, a read for GET or `reads=True`.

```python
@dataclass(frozen=True)
class Lot:
    quantity: Decimal
    cost: Decimal | None = None
    acquired: date | None = None

@dataclass(frozen=True)
class Confirmation:
    account: str
    reason: str = ""
    lots: list[Lot] = field(default_factory=list)

@pages.route("/confirm", levels="write", methods=["POST"], params=Confirmation,
             name="confirm_lots")
async def confirm(request: meridian.Request) -> meridian.Response:
    """Record the account's lots, as read."""
    record = request.params            # from the form, or from the tool's JSON
    if not record.reason:
        pages.refuse("Give a reason.", ("reason", "required to confirm"))
    ...
    return pages.answer("done.html", Recorded(...))
```

The record (`meridian.params`) is read from a browser's form whose inputs are
named by the data dictionary's paths -- `lots[0].cost`, as the kit's
`om-entry-grid` names its cells -- and from an agent's JSON, by the same
paths, so one refusal names one cell and one argument. A decimal is a string
in JSON, never a number; a date `YYYY-MM-DD`. For a tool's call a field that
does not read, or an argument the record has not, is refused by path before
the view runs; for a browser each is in `request.param_errors` beside the
record, for the page to show on its cell. `pages.answer(template, data)`
renders `data` for a browser and returns it as JSON, with its outcome (`made`
for an act, `unchanged` for a read or a repeat), for a tool; `pages.refuse`
refuses by path (`Field.of(path, operation="RecordOpeningBalance")` resolves
a book's path to its dictionary entry). A call whose claims name its tool
(`request.tool_name`) carries no form token, since only the dashboard's
`/mcp` sets one and the sidecar holds it to the tool's route. `tool=False`
with `why=` declares a route not offered to agents, which `meridian plugin
check` reports; `@pages.tool(replaces=path)` stands in for a derived tool.
`PageClient.call_tool(name, arguments)` calls a tool in a plugin's tests as
the surface would. From contract v15 a tool serves its route's roles, and is
listed to a person holding one of its levels on one of them.

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

### A table setting (contract v14)

A setting may be rows of typed columns, such as a plan's own fund code per
account linked to the instrument it is. An admin of the plugin enters the
rows in the dashboard's Settings form, an editable table checked cell by
cell; the plugin only reads them, as any setting arrives. A plugin sets none
of its settings itself.

```python
PLAN_CODES = meridian.Setting(
    "plan_code_links",
    list,
    label="Plan-code links",
    columns=(
        meridian.Column("account", "external_account", label="Account", required=True),
        meridian.Column("code", label="Plan code", required=True),
        meridian.Column("instrument", "instrument", label="Instrument", required=True),
    ),
)

async for settings in plugin.settings():
    for row in settings.values.get("plan_code_links", []):
        row["code"], row["instrument"], row["changed_by"], row["changed_at"]
```

A column's kind is "text", "integer", "decimal", "date", "choice" (with
`choices`), "external_account" (one this plugin reported) or "instrument" (a
deployment instrument record's ID, picked by search, never a symbol). Each
row arrives as a dict of text by column name, with `changed_by` and
`changed_at`, which the conductor stamps when a row is added or changed.
`most_rows` bounds the table (at most 500). `preview` in v14.

### Quantities and money

A quantity is a Python `Decimal` (or an `int`), and an amount of currency is a
`meridian.Money`, a `Decimal` and the asset it is in:

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

**A Money names its cash instrument** (contract v18; decisions/023 as amended).
`Money(Decimal("12.50"), "USD")` still works: core resolves the ISO 4217 code,
dated, to the currency's cash instrument, and what it keeps and answers names
the instrument, so a Money read back (`as_money`) carries `instrument_id`
beside the code. An asset with no ISO 4217 code -- USDC, USDT, a network's gas
token -- is named by its instrument alone, as `resolve_identifier` resolved it:
`Money(Decimal("2410.5"), instrument_id=usdc)`. Its code in `currency_code` is
refused, a code and an instrument naming two assets are refused, and a USDT
amount is never a USD amount. A Money naming neither is refused before
anything is sent.

**A date is a date** (contract v18). Every field the data dictionary types
`date` -- a business date, an as-of date, a trade date, a value date -- takes a
`datetime.date`, or its ISO 8601 text as before, and crosses as the text
(`2026-10-09`). Text that is no date (`2026-02-30`, `20261009`) and a
`datetime`, which is a moment, are refused naming the field before anything is
sent. What comes back is the text: `date.fromisoformat(price.meta.business_date)`.

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

### The archive (contract v16)

A plugin at the edge declares the kinds of raw record it keeps, and past each
kind's window its records are archived, kept or deleted, as its admin chose
(sdk-contract/an-edge-plugins-older-records-move-to-the-archive;
spec/an-edge-plugins-older-records-move-to-the-archive):

```python
import meridian
from meridian.declaration import Declaration, RecordKind, Storage

DECLARATION = Declaration(
    settings=SETTINGS,
    storage=Storage(kinds=[
        RecordKind("activity", "Reported activity", window_days=2555),
        RecordKind("responses", "Raw responses", window_days=30),
        RecordKind("session", "Session state", window_days=7, archivable=False),
    ]),
)

async with await meridian.connect(declaration=DECLARATION, interface=INTERFACE) as plugin:
    async for settings in plugin.settings():
        window = settings.values["activity_window_days"]   # days, the admin's
        past = settings.values["activity_past_window"]     # archived, kept or deleted
        for unit, count, first, last in units_past(window):  # the plugin's own units
            if past == "archived":
                await plugin.archive_unit("activity", unit, record_count=count,
                                          first_received_ns=first, last_received_ns=last)
            elif past == "deleted":
                await plugin.delete_unit("activity", unit, record_count=count,
                                         first_received_ns=first, last_received_ns=last)
        plugin.stored = [meridian.StoredSpan(record_kind="activity", record_count=...,
                                             first_received_ns=..., last_received_ns=...)]
```

- **The kinds** go on the declaration (`Storage(kinds=...)`; at most 16, each
  name lowercase letters, digits and underscores, a label up to 40
  characters, a window of 1 to 36,500 days, and whether a unit of it can be
  archived). `retention_days` is the longest window unless given; a plugin
  declaring no kinds keeps one retention, as before.
- **The window settings** are the SDK's, two per kind for every edge plugin
  alike: `<kind>_window_days`, defaulting to the kind's window, and
  `<kind>_past_window`, `archived`, `kept` or `deleted`, defaulting to
  `archived` where the instance has an archive and `kept` otherwise. A
  plugin declaring a setting of either name is refused. The deployment
  refuses a window below its hold.
- **The archive** is the instance's own, where a deployment admin allowed it
  one: `edge.archive_dir()` where it is mounted (`MERIDIAN_ARCHIVE_DIR`), or
  in a cloud the bucket `MERIDIAN_ARCHIVE_BUCKET` names (an `s3://` URL, read
  through boto3, which a plugin deployed with one installs), behind the same
  interface. With neither, records past their window are kept.
- **A unit** is a file or directory in the plugin's storage, named by its
  path there; the records it holds are the paths within it, which rows name
  as their `record_key`. `archive_unit` writes it to the archive, checks
  each file landed (size and SHA-256), reports the move through the sidecar
  with its rule (`activity_window_days 2555`), and only then removes it;
  the move is refused before anything moves where the kind's
  `<kind>_past_window` is not `archived`, or the settings have not arrived.
  An index in the storage keeps what moved.
- **Restoring** is a person's: `restore_unit(kind, unit, for_caller=)`
  copies the unit back to a restore area in storage and answers its path,
  readable there for seven days, after which it is removed and its return
  reported. Every edge plugin with pages offers `POST /archive/restore`,
  taking `record_kind` and `unit`, for a person at `write`; the deployment
  derives it as the `restore_unit` tool, and the person is the claims'.
- **Deleting** reports first and deletes after, so a refusal keeps the unit:
  inside the deployment's hold, `CommandRefused` with
  `REFUSAL_REASON_WITHIN_HOLD`. Deleting an archived unit is an admin's act,
  `for_caller=` the person.
- **Finding a record**: `plugin.find_record(key)` answers the last move of
  the unit holding it, `outcome` archived (restorable), restored or deleted,
  or None for a record never moved. A row's `record_key` on the plugin's own
  page resolves through it, never to nothing.
- **What is stored** is the plugin's to say, as its figures are:
  `plugin.stored`, one `StoredSpan` per kind, on every heartbeat. The bytes
  each kind uses of the archive (`StoredSpan.bytes`) are the SDK's: it sums
  them from its index on every heartbeat, in place of any the plugin set,
  and adds a kind the plugin left out that the archive holds some of. The
  deployment's Summary draws them against the archive's bound.

**The archive's bound**, a deployment admin's, reaches the plugin as
`MERIDIAN_ARCHIVE_MOST_BYTES`, in bytes, unset where there is none.
`archive_unit` refuses a unit that would take the archive past it, with a
`RuntimeError` saying how much the archive holds, its bound and the unit's
size, before anything is written or reported: the unit stays in storage and
no move is recorded, so the plugin keeps it and tries again on a later pass.

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

### Filing a ticket for a person (contract v13)

When a person meets a problem the plugin cannot handle -- a refusal it cannot
explain, a figure that looks wrong -- the plugin may file a ticket for them,
which reaches whoever in the deployment can act: the plugin's people, its
admin, the deployment admin, or Open Meridian. Only for a person whose
request it is serving, at whatever level their session holds, and never as
itself: what a plugin notices on its own is its health, figures on its
Summary, from which a person may choose to file.

```python
import meridian

reply = await plugin.file_ticket(
    title="Break on the growth account still open after its cause was confirmed",
    seen=request.form.get("seen", ""),   # the person's words, plain text
    kind="defect",                       # discrepancy, request or question
    idempotency_key=f"break-still-open-{break_id}",
    for_caller=request.caller,
    references=[meridian.TicketReference("break", break_id, account_id="ACC-GROWTH")],
)
reply.ticket_id, reply.outcome, reply.seen_count   # "TKT-...", "made", 1
```

`for_caller` is the person: the `Caller` of the request being served, or the
`Meridian-Caller` header it was read from, sent as the call's
`meridian-caller` metadata. `concerns` is this plugin unless it names a part
of core or the platform (`meridian.TicketSubject.SDK`, `"platform"`); never
another plugin, which the sidecar refuses naming it. The plugin names no
instance or version: its sidecar sets the instance, and the deployment the
version at filing. `step`, `operation`, `reason` and `paths` name the
workflow step, the operation, the refusal and the fields by their paths,
where known; `references`, at most 50, name the records it is about by value,
a break, an entry or a street record with its account, and an account only
one the person may read.

`idempotency_key` is required: the plugin's own key for the problem, so a
plugin restarted mid-run files nothing twice. Filed again while its ticket is
open, the ticket is brought up to date and answered `unchanged`, its
`seen_count` counting the filing; after it was resolved or closed, a new
ticket is filed. `plugin.filed_tickets(for_caller=..., idempotency_keys=[...])`
(or `ticket_ids=`, or every one after a `cursor=`) reads back what became of
them: each `FiledTicket`'s `TicketState`, `TicketResolution` and seen counts,
never people's notes, so a plugin sees one answered and stops filing it.

A title is 1 to 120 characters and what was seen at most 8,000, plain text;
past a bound the call is refused here, naming the field, and nothing is sent.
The sidecar refuses a filing as the plugin itself (`NotGranted`), for a person
it cannot vouch for, about another plugin, naming an account the person may
not read, and past 20 filings an hour from one instance, a repeat not counted.
Every text filed is data to whoever reads it, never instructions.

### The custodian's activity, and each sync status (contract v14)

A custody plugin reports each activity on an account -- a purchase, a sale, a
reinvested dividend, a split, a fee, a transfer -- as the custodian states it.
It is evidence that explains a break, never a source: the street keeps it as
reported and derives no position, lot or figure from it, and nothing moves the
book until a person confirms.

```python
import meridian
from decimal import Decimal

reply = await plugin.record_activity(
    external_account_id="SNAP-ACC-1",
    source="snaptrade",
    activity=meridian.CustodialActivity(
        external_activity_id=venue_activity["id"],
        kind=meridian.ActivityKind.ACTIVITY_KIND_REINVESTMENT,
        instrument_id="INS-...",              # resolved at the edge, as a holding's is
        trade_date="2026-09-30",
        settlement_date="2026-09-30",
        units=Decimal("3.27"),                # signed by what it did to the account
        price=meridian.Money(Decimal("1.00"), "USD"),
        amount=meridian.Money(Decimal("-3.27"), "USD"),   # by what it did to the cash
        description=venue_activity["description"],
        raw_record=plugin.raw_record(f"activities/SNAP-ACC-1/{venue_activity['id']}"),
    ),
)
reply.activity_id, reply.already_recorded   # "ACT-...", False
```

The sidecar sets the account from the external account's link and refuses an
unlinked one (`NotLinked`). Sent again under the same `external_activity_id`,
it is answered `already_recorded` and recorded once; a custodian restating an
activity under a new identifier is a new one, reported, never merged. A value
the custodian did not state is left unset, never zero (a split moves no cash).
A type that converts to no `ActivityKind` is sent as not known with
`kind_as_reported`; a code that did not resolve, with `instrument_as_reported`.
Report past activity on first connection back to the `history_from` the sync
status names (a backfill), then each sync's new activity.

Operations reads it, `plugin.list_activities(account_id=, trade_date_from=,
trade_date_to=, page_size=, cursor=)` (inclusive, by trade date, or
`since=` a watermark in the order recorded), the reply carrying the source's
`history_from`, so an opening balance older than the history says so. It hears
it with `receive(activity_recorded=...)`, and links a break's cause to the
activity that explains it: `meridian.BreakCause(category=
"BREAK_CAUSE_CATEGORY_INCOME_REINVESTED", activity=meridian.ActivityRef(...))`.

Each sync status a custody plugin reports is kept by the street:
`plugin.list_sync_statuses()` reads the latest of each connection in the
reader's scope (or every one `since=` a watermark), and
`receive(sync_status_recorded=...)` hears each, so "needs sign-in" is told
apart from merely old. One for an unlinked external account is kept with its
account empty and reaches no plugin.

The three rows are `preview` in v14.

**An activity recorded before its instrument resolved is re-resolved**
(contract v15) -- a plan's own code linked to an instrument later, a symbol
the security master completes later -- never sent again, since a redelivery
is answered as already recorded and changes nothing:

```python
reply = await plugin.re_resolve_activity(
    external_account_id="SNAP-ACC-401K",
    source="snaptrade",
    external_activity_id=activity_id,          # as first reported
    instrument_id="INS-...",                   # empty where the link was removed
    provenance=meridian.Provenance(field="instrument_id",
                                   kind="PROVENANCE_KIND_SUPPLIED",
                                   person="Ada Park, in the plan-code links"),
    resolved_at_ns=link_set_at_ns,             # when the link was set or the rule ran
)
reply.activity_id, reply.already_recorded
```

The street keeps the activity as first recorded and each re-resolution beside
it, its own record; one naming what the latest resolution names is answered
`already_recorded`, and one of an activity never recorded is refused naming
it. Operations reads them beside the activities, `list_activities(...)`'s
`re_resolutions` (the activity's instrument is the latest's), and hears each
with `receive(activity_re_resolved=...)`, caught up from that read after a
gap. A custody plugin re-resolves an account's activities whenever what
resolves them changes. Both rows are `preview` in v15.

### The lake (contract v18)

The lake keeps what sources say about prices, append-only and point in time.
A `dgm` plugin puts them in; the reading roles (`reporting`, `portfolio`,
`compliance`, `signal`) read and hear them. The SDK carries the typed
operations and nothing of any vendor's: no HTTP or WebSocket client, no
vendor-file parser.

**A dgm declares its catalogue** in its declaration, from code, beside its
storage: each dataset it serves, by a key its rows name as the instance, a
colon and the key (`coinbase-1:daily`):

```python
from meridian import DatasetDeclaration, DatasetLicence, Declaration

DECLARATION = Declaration(
    settings=SETTINGS,
    storage=Storage(kinds=[RecordKind("responses", "Raw responses", window_days=30)]),
    catalogue=[
        DatasetDeclaration(
            key="daily",
            vendor="Coinbase",
            data_types=["meridian.v1.Price", "meridian.v1.Bar", "meridian.v1.Bar.trade_count"],
            modes=["pull", "push"],          # how its rows can arrive
            cadence=86_400,                  # seconds between updates; 0, only when asked
            history=3650,                    # days it reaches back; 0, none stated
            licence_default=DatasetLicence(kept=True, personal_use=True),
            day_time_zone="Etc/UTC",         # the day a business date is in
            day_end_minute=0,                # minutes after local midnight it ends
            venue_id="VEN-...",              # the venue it is; empty for consolidated
        ),
    ],
)
```

A data type is named by its message and an optional field it fills by its
dictionary entry; the licence is what the vendor's standard terms say, which
the deployment's licence confirms or replaces, never whether a deployment meets
them. Each is refused here past the dictionary's bounds (a key, a zone that is
no IANA zone, a mode twice, a venue that is no venue master ID), and a
catalogue from a version not holding `dgm` is refused.

**It records prices and bars in batches** of 1 to 500, refused outside the
bound before anything is sent, recorded whole or refused naming the item and
field. Each row names its dataset, the deployment's own entities it is about,
its times and the raw record it was converted from; resolve every subject first
(`resolve_identifier`, a miss reported with `report_missing_instrument`) and
every venue (`resolve_venue`, a MIC as `iso10383`, a miss reported with
`report_missing_venue`):

```python
from datetime import date
from meridian import Money, ObservationMeta, Price, Source, SourceTime, SubjectRef

done = await plugin.record_prices(
    prices=[
        Price(
            meta=ObservationMeta(
                row_key="BTC-USD:1d:1791331200",      # from the raw record: a repeat changes nothing
                subjects=[SubjectRef(entity_id=btc)],
                source=Source(dataset=f"{plugin.identity.instance_id}:daily", venue_id=venue),
                valid_from_ns=day_start_ns,
                valid_until_ns=day_end_ns,            # a day still forming says so
                business_date=date(2026, 10, 8),
                source_times=[SourceTime(kind="published", at_ns=day_end_ns)],
                raw=plugin.raw_record("candles/BTC-USD/86400/1791331200"),
            ),
            kind="close",
            price=Money(Decimal("62431.27"), "USD"),
            basis="per_unit",
        )
    ]
)
done.recorded, done.restated, done.unchanged
```

The same row key with the same values (by decimal value: 764.2 is 764.20) is
answered unchanged; a changed value, the day still forming, is the next
version, the first kept. A price in a stablecoin names the token's own cash
instrument, never a fiat code. `record_bars` takes `Bar`s alike: one asset for
open, high, low, close and a vwap, which is left unset where the source gives
none, as is a trade count.

**It hears what the lake wants of it** and records against the want or
declines it per subject:

```python
async def wanted(heard: meridian.Heard[meridian.plugin.v1.operations_pb2.ObservationsWantedEvent]) -> None:
    want = heard.message           # dataset, data_type, subjects, kinds, business_date or a range
    await plugin.record_prices(prices=fetched(want), want_id=want.want_id)
    await plugin.decline_want(want_id=want.want_id, subjects=uncovered, reason="not_covered")

await plugin.receive(observations_wanted=wanted, want_withdrawn=stop_keeping_current)
```

A standing want asks the subjects kept current until it is withdrawn.

**A reader reads** by business date, at a valid time (the latest in force) or
over a range, as of a recorded time, from the deployment's default sources,
named datasets or every dataset side by side -- the generated reads'
parameters:

```python
closes = await plugin.list_prices(subjects=held, kinds=["close"], business_date=date(2026, 10, 8))
then = await plugin.list_prices(subjects=held, business_date=date(2026, 10, 8), as_of_ns=cut)
both = await plugin.list_prices(subjects=held, sources=meridian.SourceChoice(side_by_side=True))
bars = await plugin.list_bars(subjects=held, interval_ns=86_400 * 10**9,
                              valid_from_ns=start, valid_until_ns=end)
closes.datasets      # each dataset the answer includes, once: vendor, aggregator, instance
closes.unanswered    # each subject or dataset not served, and why
listed = await plugin.list_datasets()   # what it may read, with each catalogue entry
```

and hears what is recorded after for the subjects it names, at most 500,
latest value first per key (a price's dataset, subjects, venue and kind; a
bar's interval start), read again by the same query, latest first, when it
starts, after a loss and after a broken stream:

```python
await plugin.receive(prices_recorded=on_price, bars_recorded=on_bar, subjects=held_ids)
```

Each is handed on with its dataset as the catalogue declares it
(`Heard.dataset`: vendor, aggregator, instance and its entry), which the
lake's answers name once rather than on every row. The lake's rows are
`preview` in v18.

**The dgm suite** (`meridian.suites`, `run("dgm", producers)`) holds a data
plugin to its role: a daily close with its business date, kind, dataset, source
times and raw record; the forming day restated under one row key; a price
exact past a float; a bar with no vwap; an FX rate; a stablecoin quote on the
token's instrument; an asset that does not resolve and a venue not held,
reported; a venue resolved; a want recorded against, a subject declined, a
standing want withdrawn. A case naming a row the plugin hears gives it what
`answer` delivers through its own `receive`, called on the recorder:

```python
async def a_want_recorded_against(recorder):
    recorder.answer("ObservationsWanted", lambda _: synthetic_want())
    await recorder.receive(observations_wanted=MyDgm(recorder).on_want)
```

Two plugins of one pair pass it unchanged; a candle read through a `float`, or
a forming day recorded as a new row, fails it. The reading roles have suites
of their own.

### Trades and quotes (contract v19)

The lake's 1b: a `dgm` records trades and top-of-book quotes, and `signal` and
`ems` read and hear them (`reporting` reads neither). Still typed operations
only: no WebSocket client, no reconnecting stream, no bar builder.

**A dgm records them in batches** of 1 to 500, from a live dataset declaring
`data_types=["meridian.v1.Trade", "meridian.v1.Quote"]` and `modes=["stream"]`.
Each is keyed by UTC instants and names no business date; a trade's venue is
the venue it printed on, and its price a `Money` naming its cash instrument:

```python
from meridian import Eligibility, Quote, Trade, TradeAttributes

every = Eligibility(high_low="eligible", open="eligible", close="eligible", volume="eligible")
await plugin.record_trades(
    trades=[
        Trade(
            meta=ObservationMeta(row_key="BTC-USD:t:812345678", subjects=[SubjectRef(entity_id=btc)],
                                 source=Source(dataset=live, venue_id=venue), valid_from_ns=at_ns,
                                 raw=plugin.raw_record("matches/BTC-USD/812345678")),
            price=Money(Decimal("62510.01"), "USD"),
            quantity=Decimal("0.0125"),
            attributes=TradeAttributes(consolidated=every, market_centre=every),
            aggressor="buy",            # the side that took liquidity; unset when not said
            source_sequence=812345678,
        )
    ]
)
await plugin.record_quotes(quotes=[Quote(meta=meta, bid=Money(Decimal("62510.00"), "USD"),
                                         bid_quantity=Decimal("0.84"))])   # no offer: ask unset
```

A source's condition codes are converted at the edge into the trade's
attributes (`characteristics=["odd_lot"]`, and what it may set of a bar); a
code with no conversion stays in `meta.unconverted`, its eligibilities
unspecified. A source naming the resting order's side records the other as
the aggressor. A withdrawn trade is the next version under its row key, with
`cancelled=True`.

**A reader reads** trades over a range within one day of the dataset, or the
trades recorded after a watermark, whatever their valid time; and quotes at the
latest in force, per subject, dataset, venue and asset, or over a range:

```python
day = await plugin.list_trades(subjects=held, valid_from_ns=start, valid_until_ns=end)
late = await plugin.list_trades(subjects=held, after_watermark=day.watermark)
quotes = await plugin.list_quotes(subjects=held)          # BTC in USD and in USDC: both
```

and hears them for the subjects it names:

```python
await plugin.receive(trades_recorded=on_trade, quotes_recorded=on_quote, subjects=held_ids)
```

Every trade is handed on, never dropped for a later one. After a loss, or a
broken stream, the SDK reads the trades recorded after the watermark it last
saw -- per dataset, the last trade handed on -- and hands them on marked
`caught_up`, a late print among them, before anything heard after; on start
it reads none, so a plugin wanting the day's trades reads them by range.
Quotes, like prices, are handed on latest value first, and read again at the
latest after a loss. The 1b's rows are `preview` in v19. From v19 a price's key and a quote's hold the asset they
are in, so BTC priced in USD and in USDC on one venue are two values.

**The suites.** The dgm suite gains eight cases about trades and quotes: a
trade with its attributes and aggressor, the maker's side inverted, a
condition converted and one not, a withdrawal, a quote two-sided and
one-sided, a standing want streamed. A case about one kind of data says so
(`Case.about`: closes, bars, trades, quotes, prices on a venue), and a plugin
that declares it never publishes that kind names it in `not_presented`, with
why, and is verified on the rest; every other case is still required:

```python
report = run("dgm", producers, not_presented={
    "a-trade-recorded": "daily closes and bars only: this source states no trades",
})
```

`signal`'s suite gains trades and quotes read, heard and caught up after a
watermark; `ems` has its first suite, the same and the datasets it may read;
and `reporting`'s, its reporting currency resolved by its ISO 4217 code
(`resolve_identifier`, read-only for `reporting` from v19).

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
| 0.16.0 to 0.17.0: the SDK declares contract v12, the deployment serves its MCP: a route's one typed record of inputs (`params=`, `request.params`, `request.param_errors`), read alike from a form named by the dictionary's paths and from an agent's JSON (`meridian.params`); tools derived from typed routes (`name=`, `description=`, `reads=`, `answers=`, `tool=False` with `why=`, `@pages.tool(replaces=...)`), sent at registration; `pages.answer`, `pages.refuse`, `request.tool_name`; a refusal's path resolved to its dictionary entry (`meridian.dictionary`, `Field.of`); `PageClient.call_tool`; the base template on kit 0.9.0 | nothing | a page or route that changes something and declares no `params=`: give it its record, or `tool=False` with `why=` |
| 0.17.0 to 0.18.0: the SDK declares contract v13; a plugin files a ticket for a person and reads what it filed (`plugin.file_ticket`, `plugin.filed_tickets`, `TicketKind`, `TicketSubject`, `TicketReference`, `TicketState`, `TicketResolution`) | only the pins move | |
| 0.18.0 to 0.19.0: the SDK declares contract v14; a custody plugin reports the custodian's activity and operations reads, hears and links it (`plugin.record_activity`, `plugin.list_activities`, `CustodialActivity`, `ActivityKind`, `ActivityRef`, `receive(activity_recorded=)`); each sync status the street keeps (`plugin.list_sync_statuses`, `receive(sync_status_recorded=)`); a table setting (`meridian.Setting(name, list, columns=...)`, `meridian.Column`) | only the pins move | |
| 0.19.0 to 0.20.0: the SDK declares contract v15, a person's access granted per role: `roles=` on `@pages.page`, `@pages.route`, `@pages.tool`, `meridian.Setting` and `meridian.Page`; `Caller.roles`, `Caller.level_for`, `Caller.read_for`, `Caller.write_for`; `PageClient(..., roles=)` and `roles=` on its sessions; an activity re-resolved (`plugin.re_resolve_activity`, `re_resolutions`, `receive(activity_re_resolved=)`); a plugin holding one role or none names no role, and one coming to hold a second names `roles=` on every page, route, tool and setting, which `meridian plugin check` reports | only the pins move | |
| 0.20.0 to 0.21.0: the SDK declares contract v16, an edge plugin's older records move to the archive: the kinds of raw record (`Storage(kinds=[RecordKind(...)])`) and the two settings the SDK declares per kind (`<kind>_window_days`, `<kind>_past_window`), reserved; the archive (`edge.archive_dir()`, `MERIDIAN_ARCHIVE_BUCKET`); the moves with their index (`plugin.archive_unit`, `plugin.restore_unit`, `plugin.delete_unit`, `plugin.find_record`), a deletion inside the hold a `CommandRefused` with `REFUSAL_REASON_WITHIN_HOLD`; what each kind holds in storage on the heartbeat (`plugin.stored`, `StoredSpan`), with the bytes each uses of the archive (`StoredSpan.bytes`), which the SDK fills in; the archive's bound (`MERIDIAN_ARCHIVE_MOST_BYTES`), past which `archive_unit` refuses; `POST /archive/restore` on every edge plugin's host, derived as the `restore_unit` tool. A plugin declaring no kinds keeps `retention_days` as before, so `meridian plugin migrate` needs no change in the command line | only the pins move | a setting of the plugin's own that held a window, dropped, its release notes naming the kind's window it maps to for the admin to set once at upgrade (SnapTrade's two); a setting it declared as `<kind>_window_days` or `<kind>_past_window`, renamed |
| 0.21.0 to 0.22.0: the SDK declares contract v18, the lake's 1a: a dgm's catalogue (`Declaration(catalogue=[DatasetDeclaration(...)])`, `DatasetLicence`, `ObservationMode`), prices and bars recorded in batches of 1 to 500 (`plugin.record_prices`, `plugin.record_bars`, `Price`, `Bar`, `ObservationMeta`, `SourceTime`, `Source`, `SubjectRef`), wants heard and declined (`receive(observations_wanted=, want_withdrawn=)`, `want_id=`, `plugin.decline_want`), the lake's reads by business date, as of and side by side (`list_prices`, `list_bars`, `list_datasets`, `SourceChoice`), prices and bars heard latest value first for the subjects named with their dataset (`receive(prices_recorded=, bars_recorded=, subjects=)`, `Heard.dataset`), venues resolved (`resolve_venue`, `report_missing_venue`), the dgm suite and the reading roles' (a heard row delivered by `answer`); a Money names its cash instrument (`Money.instrument_id`; `Money(amount, "USD")` resolved by core, dated); every date field takes a `datetime.date`, and refuses text that is no date. `Money(amount, code)` keeps its shape, so `meridian plugin migrate` needs no change in the command line | only the pins move | a test comparing a Money read back (`as_money`) with one it made, which now carries `instrument_id`: compare `amount` and `currency_code`; a date sent as text that is no date, refused |
| 0.22.0 to 0.23.0: the SDK declares contract v19, the lake's 1b: trades and quotes recorded in batches of 1 to 500 (`plugin.record_trades`, `plugin.record_quotes`, `Trade`, `TradeAttributes`, `Eligibility`, `Quote`), read (`list_trades` over a range or `after_watermark=`, `list_quotes`) and heard (`receive(trades_recorded=, quotes_recorded=, subjects=)`: every trade, caught up after the watermark last seen; the latest quote per asset); a price heard is conflated per its asset too; `reporting` resolves an identifier; the dgm suite's eight 1b cases, a case about a kind of data the plugin never publishes not presented with why (`Case.about`), `signal`'s 1b cases, the `ems` suite, `reporting`'s `resolves-its-reporting-currency` | only the pins move | a dgm's suite test meeting the eight new cases: map each, or name those about trades or quotes in `not_presented` with why where it publishes neither |

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
