# meridian-python

The Python SDK for building [Open Meridian](https://open-meridian.com) plugins:
the tools a trader has an AI agent build, and the bots and analytics a
developer writes. Python 3.11 or newer. This is release 0.32.1; its reference
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

`plugin new --role data`, `--role custody`, `--role operations` and `--role
reporting` write `templates/<role>/` instead, each built on its role's common
part (`meridian.roles`, below), so a person who knows the role knows the
plugin: a data plugin putting a stand-in vendor's prices into the lake, its
Connection and Datasets pages with their read tools, and its tests running
the data suite; a custody plugin's Connections, Account links and
Statements; an operations plugin's Breaks, Reconciliations and Opening
balances, its confirmation preparable by an agent; and a `reporting` plugin
valuing the book's positions at the close from the lake, its Closes and
Datasets pages, and its tests running the `reporting` suite. `--role
connectivity` writes a plugin placing at a stand-in venue through the SDK's
Trader, its tests running the connectivity suite; and from 0.31.0 `--role
pricing` a plugin answering the analytics component's batches, its tests
running the `pricing` suite. Each is a whole plugin, its agents' files, CI and
`Dockerfile` the reference plugin's own, and each passes `meridian plugin
check --verified` as written.

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

From contract v22 the order path's links come beside them. A connectivity
plugin is told `scope.connectivity_link`, its link to its one `ems` (whether
a deployment admin made it available, the `ems`, and who may route through
it), and in `scope.venue_account_map` the venue account codes that `ems`
mapped on it; it links no accounts of its own, and its scope is the accounts
mapped on it while it is available and linked. An `ems` is told
`scope.connectivity_links`, each connectivity plugin linked to it, and
`scope.venue_account_map`, its whole map. Both are unset, or empty, for any
other plugin, and delivered again on every change.

```python
async for scope in plugin.account_scope():
    if scope.venue_account_map is not None:
        for mapping in scope.venue_account_map.mappings:
            print(mapping.account_id, "->", mapping.venue_account_code,
                  "at", mapping.connectivity_instance_id)
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
A data plugin puts them in; the reading roles (`reporting`, `portfolio`,
`compliance`, `signal`) read and hear them. The SDK carries the typed
operations and nothing of any vendor's: no HTTP or WebSocket client, no
vendor-file parser.

**A data plugin declares its catalogue** in its declaration, from code, beside its
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
catalogue from a version not holding `data` is refused.

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

**The data suite** (`meridian.suites`, `run("data", producers)`) holds a data
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
    await recorder.receive(observations_wanted=MyDataPlugin(recorder).on_want)
```

Two plugins of one pair pass it unchanged; a candle read through a `float`, or
a forming day recorded as a new row, fails it. The reading roles have suites
of their own.

### Trades and quotes (contract v19)

The lake's 1b: a data plugin records trades and top-of-book quotes, and `signal` and
`ems` read and hear them (`reporting` reads neither). Still typed operations
only: no WebSocket client, no reconnecting stream, no bar builder.

**A data plugin records them in batches** of 1 to 500, from a live dataset declaring
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

**The suites.** The data suite gains eight cases about trades and quotes: a
trade with its attributes and aggressor, the maker's side inverted, a
condition converted and one not, a withdrawal, a quote two-sided and
one-sided, a standing want streamed. A case about one kind of data says so
(`Case.about`: closes, bars, trades, quotes, prices on a venue), and a plugin
that declares it never publishes that kind names it in `not_presented`, with
why, and is verified on the rest; every other case is still required:

```python
report = run("data", producers, not_presented={
    "a-trade-recorded": "daily closes and bars only: this source states no trades",
})
```

`signal`'s suite gains trades and quotes read, heard and caught up after a
watermark; `ems` has its first suite, the same and the datasets it may read;
and `reporting`'s, its reporting currency resolved by its ISO 4217 code
(`resolve_identifier`, read-only for `reporting` from v19).

### Prepared changes, own settings and each role's common part (contract v20)

The roles `dgm`, `ccm` and `match` are `data` ("data plugin"),
`connectivity` and `confirmation`: a plugin's metadata, its `roles=` and the
suites it runs name the new ones, and `meridian plugin migrate` rewrites
them.

**An act can be prepared.** An agent working for a person may prepare a
change for the person to make rather than make it, where the deployment's
admins set an act to "prepare only" or turn on its second pair of eyes. The
plugin's part is to make each act preparable: a route that changes something
names its check tool, a read tool taking the same record and changing
nothing, the paths in its record naming the accounts it touches, and the
page it is made on, which the SDK fills with the page the route is the form
of:

```python
@pages.route("/opening/check", levels="write", methods=["POST"], params=Confirmation,
             answers=Draft, reads=True, name="check_opening_draft")
async def check_opening_draft(request): ...

@pages.route("/opening/confirm", levels="write", methods=["POST"], params=Confirmation,
             name="confirm_opening_balance", checked_by="check_opening_draft",
             accounts=["account_id"])
async def confirm_opening_balance(request): ...
```

A page opened from a prepared change reads it for the person whose page it
is, and starts its form from its arguments, marked "prepared by" its
preparer, its reason shown as text: `prepared = await request.prepared()`
(its `tool_name`, `arguments_json`, `prepared_by_display_name`,
`prepared_through_client`, `reason`, `state`), None for a page reached from
none. The person makes it with the page's own Save or Confirm. The form
field `prepare` is the kit's Prepare button's, so no record names a field
so.

**A person's own settings.** A setting each person sets for themselves -- a
watchlist, a chart's choices -- is declared `per_person=True` (never secret,
never required). It is not on the Settings form and never in
`Settings.values`: the plugin saves a person's values for them and reads
them from each of their requests, typed:

```python
await plugin.set_own_settings({"watchlist": rows}, for_caller=request.caller)
request.own_settings["watchlist"]
```

**The accounts a plugin may link to.** A plugin linking external accounts
reads only those the deployment admin granted its instance
(`read_accounts_for_linking`); a link naming another is refused, a
`CommandRefused` with `REFUSAL_REASON_ACCOUNT_NOT_LINKABLE`.

**A data plugin's licences and its restart.** A data plugin reads its own
declared datasets' licences (`plugin.list_datasets()`, its `licences`), so
its Datasets page says "Licensed" or "Not licensed yet". On start, before
resuming its stream, it backfills a restart's gap:

```python
from meridian.roles import data

async def history(last):        # the last trade the lake holds of a subject
    return my_venue.trades_since(last.meta.subjects[0].entity_id, last.meta.valid_from_ns)

await data.backfill_restart(plugin, streamed_subjects, history)
```

The data suite gains `the-takers-side-stated` (a case about a field,
`about_field`, which a source never stating it names in `not_presented`
with why), `a-restarts-gap-backfilled` and `reads-its-datasets-licences`.

**Each role's common part** (spec/plugin-pages-follow-their-role) is
`meridian.roles`: for `data`, `custody`, `operations` and `reporting`, each
common page's record (`data.ConnectionRead`, `data.DatasetsRead`,
`custody.ConnectionsRead`, `custody.AccountLinksRead`,
`custody.StatementsRead`, `operations.BreaksRead`,
`operations.ReconciliationsRead`, `operations.OpeningBalancesRead`,
`reporting.DatasetsRead`), the role's figures in its order (`figures(...)`),
its common settings (`custody.poll_seconds()`, `operations.reconcile()`,
`reporting.reporting_currency()` and the rest), and its page templates,
`meridian/roles/<role>/<page>.html`, each drawing the common sections, their
labels and "not set up yet" states in the role's order, with the vendor's
blocks: `vendor_notices`, `vendor_rows`, `vendor_columns`, `vendor_sections`.

```jinja
{% extends "meridian/roles/data/connection.html" %}
{% block vendor_rows %}{% if section == "Key" %}<tr><th>Feeds</th>…</tr>{% endif %}{% endblock %}
```

Settings may be one typed class, declared and read alike, in the role's
order -- the environment first where the vendor has more than one, sample
data last:

```python
@meridian.settings
class Config:
    environment: str = meridian.environment()        # live or sandbox
    api_key: str = meridian.setting("API key", required=True, secret=True)
    sandbox_key: str = meridian.setting("Sandbox key", secret=True,
                                        applies_when=("environment", "sandbox"))
    sample_data: bool = meridian.sample_data()

plugin = await meridian.connect(settings=Config, interface=...)
config = await plugin.first_settings(Config)
```

A saved value this version cannot read -- no longer one of its choices, as
`practice` once the plugin says `paper`, or not of its kind -- never raises
and is never mapped to another value (0.31.1). It is delivered unset: a
required setting holds nothing, not even its default, and is in
`config.missing`; an optional one holds its default. Each is in
`config.refused` (`Settings.refused`), a `meridian.RefusedSetting` whose
`message` a page shows: "Environment was saved as 'practice', which this
version no longer offers; save it again". A person's own values refused are
in `request.own_settings_refused`. An environment so refused is empty: not
`live`, so the plugin reaches the demo host, and not demo, so `is_demo` and
the badge count it live.

Every page's loader holds the kit's patterns as macros, `meridian/kit.html`:
`status`, `action`, `notice`, `badge`, `tiles`, `when`, `grid`,
`nothing_here`, `empty` and `facts`.

### A service account runs a plugin's autonomous work (contract v21)

A plugin's autonomous work -- a scheduled sweep, a strategy, an agent inside
the plugin -- acts with an identity of its own: a **service account**, a user
of the deployment that is not a person. A deployment admin creates it, names
the person answerable for it (its owner), grants it per role and sets it to
**prepare only** (the default) or **act**; a role's admin chooses which of
the accounts granted on that role the role's work **runs as**. The plugin
holds no credential and chooses none of it. Its work calls one of its own
declared acts as that account:

```python
async with meridian.runs_as("operations") as act:
    reply = await act(
        "close_cleared_breaks",                     # one of the role's acts, by its tool's name
        {"account": "ACC-1", "reason": "The difference was gone at the statement."},
        reason="2 cleared breaks of ACC-1: the statement found no difference for them.",
    )
if reply.outcome == "made":
    answer = json.loads(reply.answer_json)          # the act's own typed answer
else:                                               # "prepared": a person makes it
    log.info("prepared %s for the people who may make it", reply.prepared_call_id)
```

The dashboard applies what it applies to a person's agent -- the account's
grants and accounts, the act's level (the strictest of the ceiling, the
plugin admin's, any access group's reaching the account, and the account's
own setting) and the act's second pair of eyes -- and makes the act or
prepares it. Nothing is declared for it: the work calls acts the plugin
already declares, each naming its check tool (`checked_by=`) so it can be
prepared; an act with none is refused to an account set to prepare only.
The arguments are the act's typed record of inputs, a mapping or its JSON;
the call is sent as the plugin itself, never for a person.

A refusal names the field (`.fields`), as the dashboard named it:
`NotGranted` for an account disabled, removed or not granted write on the
role (`role`) or an act at "may not" (`tool_name`); `CallFailed` with `kind`
"refused" for a role running as no service account (`role`), an act with no
check tool for an account set to prepare only (`tool_name`), or the check
tool's own refusal; "invalid" for a tool that is not one of the role's acts
(a read, another role's act, a core `dashboard__` tool), a role the instance
was not launched with, or a reason that is not plain text (a control,
zero-width or bidirectional override character); and "unimplemented" from a
sidecar older than contract v21. Nothing is sent, and `ValueError` is raised
here (`TypeError` for the wrong type), for an empty reason or one past 4,000
characters, a tool's name past its bound, a core tool, or arguments that are
not a JSON object or past their bound.

**The act's route acts as for a person.** Made, the dashboard sends the
arguments to the act's route with claims minted for that call alone: the
caller's `subject_kind` is `SubjectKind.SUBJECT_KIND_SERVICE_ACCOUNT`, its
`subject` the account's `SA-` ID and its `owner_subject` the person
answerable for it, with no delegation and no client. The route does what it
does for a person, handing `request.caller.header` back as `acting_for`; the
sidecar stamps the account, its kind and its owner, so the book records the
service account. Such claims open no page and are refused every
`platform.config.` command but filing a ticket and reading back what was
filed. A plugin's own test calls a tool so with
`PageClient.call_tool(name, arguments, subject="SA-...",
subject_kind=meridian.SubjectKind.SUBJECT_KIND_SERVICE_ACCOUNT,
owner_subject="local|ada")`.

### The order path and settlement calendars (contract v22)

An order reaches a venue through the book. Each role does its part through
typed operations, one per row it may send, and hears the book's records as
they change; the book holds every order, placement, execution and charge,
and alone decides what an order's state allows.

```python
# portfolio, or the oms: propose. A unit quantity or a cash quantity, never both.
await plugin.propose_order(
    account_id="ACC-1", instrument_id=aapl, side="buy", quantity=Decimal("10"),
    order_type="limit", limit_price=Money(Decimal("227.50"), "USD"),
    time_in_force="day", idempotency_key="propose:ACC-1:pm-ticket-4471",
)

# the oms: release it to be worked.
await plugin.release_order(order_id=order_id, idempotency_key=f"release:{order_id}")

# the ems: claim it, and place at a connectivity plugin linked to it, with the
# venue account code its admin mapped for the account (below).
await plugin.set_working_condition(order_id=order_id, condition="claimed", set=True)
await plugin.create_placement(
    order_id=order_id, connectivity_instance_id="snaptrade-1", venue_account_code="X12345",
    quantity=Decimal("10"), idempotency_key=f"place:{order_id}:1",
)

# a connectivity plugin: say what the venue said of the ems's placement, each
# with its raw record.
await plugin.report_placement(
    placement_id=placement_id, event="acknowledged", venue_order_id="V-881",
    raw_record=plugin.raw_record(key),
)
```

`portfolio` and the `oms` own orders, the `ems` owns placements, and a
connectivity plugin owns fills. A connectivity plugin records no order and
creates no placement: its `record_order` or `create_placement` is refused
by its sidecar, `NotGranted`. It reports what its venue says of the
placements the `ems` made at it. A fill the venue originates, on no
placement of the `ems`'s, is not supported in contract v22; its handling is
planned for a later release. `record_order` is the `oms`'s, for a telephoned
or outside order it records for a person (`origin="telephoned"`).

The `ems`'s map of book accounts to venue account codes is its admin's: it
is sent from the `ems`'s page at `admin`, acting for the admin viewing it
(W11.22), never from the `ems`'s own work. An account the deployment admin
has not granted the `ems` is refused `REFUSAL_REASON_ACCOUNT_NOT_LINKABLE`:

```python
@dataclass(frozen=True)
class Mapping:
    connectivity_instance_id: str
    venue_account_code: str
    account_id: str

@pages.route("/venue-accounts", levels="admin", methods=["POST"], params=Mapping)
async def map_account(request: meridian.Request) -> meridian.Response:
    """Map a book account to the code it trades under at a linked connectivity plugin."""
    mapping = request.params
    await request.plugin.map_venue_account(
        connectivity_instance_id=mapping.connectivity_instance_id,
        venue_account_code=mapping.venue_account_code,
        account_id=mapping.account_id,
        acting_for=request.caller.header,  # the admin viewing the page
    )
    return pages.answer("venue_accounts.html", mapping)
```

`compliance` checks and decides (`record_check`, `decide_approval`); an `ems`
works a strategy in house as child orders of a released order
(`propose_order(link=OrderLink(kind="split", parent_order_id=...))`); a
connectivity plugin reports fills, busts and charges on the `ems`'s
placements (`report_execution`, `report_charge`), records a locate
(`record_locate`), and publishes its venue's catalogue
(`report_venue_catalogue`), which an `oms` and an `ems` read
(`read_venue_catalogue`). What they hear is typed too:

```python
await plugin.receive(
    order_updated=on_order,                         # Heard[OrderUpdatedEvent]
    placement_updated=on_placement,                 # a connectivity plugin hears only its own
    execution_recorded=on_fill,
    trading_instruction_changed=on_instruction,     # a pause or stop: no account scope
)
```

A placement is delivered only to the connectivity plugin it names, and
carries its own change requests (`placement.change_requests`), each with
its `PlacementChange` and outcome: a connectivity plugin tells a cancel from
a replace by the change's `kind`, and reads a replace's new quantity, limit
and time in force from it, never from a condition's reason:

```python
async def on_placement(heard: meridian.Heard[ops.PlacementUpdatedEvent]) -> None:
    for request in heard.message.placement.change_requests:
        if request.outcome != ops.CHANGE_REQUEST_OUTCOME_PENDING:
            continue
        if request.placement_change.kind == ops.PLACEMENT_CHANGE_KIND_CANCEL:
            await venue.cancel(heard.message.placement.venue_order_id)
        elif request.placement_change.kind == ops.PLACEMENT_CHANGE_KIND_REPLACE:
            await venue.replace(heard.message.placement.venue_order_id,
                                limit=meridian.as_money(request.placement_change.limit_price))
```

The
trading instructions -- a deployment admin's or a plugin admin's pause or
stop -- reach every subscriber whatever its accounts, and are caught up
after a loss by a read naming no account (`list_trading_instructions`).

A refusal by the order's state, a claim or a link is a `CommandRefused`
with its code: `REFUSAL_REASON_ORDER_STATE`, `_CLAIMED`, `_CHECK_BLOCKS`,
`_APPROVAL_REQUIRED`, `_ALLOCATION_UNBALANCED`, `_IDENTIFIER_IN_USE`, and
`_CONNECTIVITY_NOT_ALLOWED` for a placement at a connectivity plugin not
linked to the `ems` or not made available to the user (refused and
recorded). A command naming an order or a placement by its ID alone, its
account outside the instance's write scope, is `NotGranted` with no code; an
order stating both or neither of `quantity` and `cash_quantity` is
`CallFailed` "invalid" naming both in `.fields`. The order's states and
transitions are one table, which the SDK carries as published,
`meridian/transitions.json` (read it with
`importlib.resources.files("meridian").joinpath("transitions.json")`).

**Dates are worked out in core.** A plugin never computes a settlement or
value date itself: it reads a calendar's days (`read_calendar`) or asks for
the date (`compute_date`), answered with the rule and calendar versions it
was worked out on, the same answer for every plugin:

```python
answer = await plugin.compute_date(
    settlement=meridian.SettlementDateInputs(instrument_id=aapl, trade_date="2026-10-09")
)
if answer.outcome == ops.DATE_OUTCOME_COMPUTED:
    settles = answer.date                            # "2026-10-13": Columbus Day skipped
await plugin.compute_date(spot=meridian.SpotDateInputs(pair=[eur, usd], trade_date="2027-03-24"))
await plugin.compute_date(
    tenor=meridian.TenorDateInputs(pair=[usd, jpy], tenor=meridian.Tenor(count=1, unit="month"),
                                   trade_date=date(2026, 10, 30))
)
```

A date past a calendar's coverage, or a rule the deployment does not hold,
is answered as such and never guessed. A connectivity plugin reporting a
fill states the settlement date it computed and its basis
(`computed_settlement_date`, `settlement_date_basis`).

**Algorithms.** A version declares the algorithms its autonomous work may
name, each identifier stable across versions, and the work names the one it
runs; the book records it on each entry's service account actor, where
`reporting` reads who decided and who executed:

```python
DECLARATION = Declaration(algorithms=[AlgorithmDeclaration("twap-v1", "Time-weighted slices.")])

async with meridian.runs_as("ems", algorithm_id="twap-v1") as act:
    await act("work_order", {"order_id": order_id}, reason="TWAP slice 3 of 12.")
```

One the version does not declare is refused before anything is sent. A
`Caller` carries the algorithm a service account's call named
(`algorithm_id`) and, for an `ems`, the connectivity plugins the user may
route through (`connectivity_instance_ids`), for showing which may be
chosen; the sidecar
checks a placement against them whatever is drawn. `meridian.testing`'s
`caller_header` takes both, `PageClient.call_tool` the algorithm.

The role suites hold the order path's roles (`connectivity`, `oms`, and its
cases of `portfolio`, `ems`, `compliance`, `operations` and `reporting`) and
every role's calendar reads; a field a case names `<same>` is one value on
every message sent on its row, at least two sent.

### Booking, and one ID for every instrument (contract v24)

An execution is booked to its accounts. The `oms` books an explicit list of
executions on one order, each account's part an `Allocation` tied out
exactly in quantity, gross and each fee kind; hands the booking off to
`operations`, or cancels or replaces it before then; and records a cross
between two sleeves of one account:

```python
usd = lambda amount: Money(Decimal(amount), "USD")
await plugin.book_order(
    order_id=order_id, execution_ids=[execution_id],
    allocations=[
        meridian.Allocation(account_id="ACC-FUND-A", quantity=Decimal("60"),
                            average_price=usd("227.50"), gross_amount=usd("13650.00"),
                            net_amount=usd("13650.00"), intended_settlement_date="2026-10-16"),
        meridian.Allocation(account_id="ACC-FUND-B", quantity=Decimal("40"),
                            average_price=usd("227.50"), gross_amount=usd("9100.00"),
                            net_amount=usd("9100.00"), intended_settlement_date="2026-10-16"),
    ],
)
await plugin.hand_off_booking(booking_id=booking_id)
await plugin.correct_booking(booking_id=booking_id, kind="cancel", reason="Wrong fund")
```

A block's allocations share one average price (`average_priced=True`); an
overfill goes to the account the deployment admin marked its error account,
with its reason and `ErrorCause`, and raises an alert. `operations` and
`portfolio` amend an order's allocation instruction
(`set_allocation_instruction`); `connectivity` and `confirmation` report a
prime's answer to a give-up (`report_give_up`). The readers hear and read
bookings (`receive(booking_updated=...)`, `list_bookings`) and alerts
(`receive(alert_changed=...)`, `list_alerts`), and `compliance` raises its
own and acknowledges one for a person (`raise_alert`, `acknowledge_alert`). A
booking's states are a table beside the order's, in `meridian/transitions.json`.
Cash follows option (c): the account's base currency is a balance, every
other currency opens lots with base-currency cost, and every currency does
until a base currency is set.

Every instrument is named by the platform master's ID. A record the
deployment keeps locally while the platform has none is provisional
(`InstrumentRecord.provisional`, and a resolve's `provisional`), held to the
template it names; read the mark, never an ID's prefix. When it resolves to
the platform's `INS-` record, or two records merge, every role hears the
replacement and catches up on what it missed by sequence. A plugin that keeps
instrument IDs follows each to the record it became:

```python
ids = meridian.CurrentIdMap()
await ids.catch_up(plugin)                                    # on start
await plugin.receive(replace_merged_instrument=ids.heard, order_updated=on_order)
if ids.same(held.instrument_id, order.instrument_id): ...      # never by the IDs' text
```

The templates the store holds are read with `meridian.TemplateCatalogue`
(`list_templates`, `read_template`), and a `reference` plugin offers a
record's template fields with their provenance (`offer_template_fields`), its
suite in preview. Whether orders may name a provisional record is the
deployment admin's setting, read with `read_local_record_orders` by the roles
that propose, place or check orders (not `connectivity`, from contract v25).

Every role's suite holds `hears-and-reads-a-replacement` and
`reads-the-template-catalogue`, which the SDK answers itself for a plugin
that maps neither (`Report.answered_by_sdk`). The suites' resolves answer the
platform's `INS-suite-n`; `run(..., provisional=True)` runs every case on
the deployment's provisional records instead, which a plugin passes alike.

A data plugin's dataset names the settlement calendar its business dates
follow (`DatasetDeclaration(calendar_id="CAL-...")`), the field contract v22
added and the SDK carries from 0.28.0, so the lake can flag a daily value
dated on a closed day.

`meridian.environment()` now defaults to `sandbox`: a plugin is Live only
where a person chose Live, or where its own code says
`meridian.environment(default="live")`.

### The whole declaration and its documentation (contract v25)

A version's declaration is the whole of what it says about itself
(plans/a-plugin-carries-its-own-documentation): beside its settings, its
interface -- its pages and the tools their typed routes make -- whether it
reads external accounts, and the vendor's documentation, each section of the
plugin's `docs/` named by its digest and size:

```python
INTERFACE = meridian.Interface(port=8000, title=TITLE, pages=pages)  # a fixed port

DECLARATION = meridian.Declaration(
    settings=Config,
    interface=INTERFACE,
    reads_external_accounts=True,
    documentation="docs",          # relative to where the plugin runs: /plugin in its image
)

async with await meridian.connect(declaration=DECLARATION) as plugin:
    ...
```

- **Registration is held to the version.** `meridian plugin upload` reads
  the declaration from the built image (`meridian-declaration`) and the
  texts beside it (`meridian-declaration --documentation`), and a plugin
  declaring v25 registers exactly the declaration its version was uploaded
  with, or its sidecar refuses it naming the first difference. `connect`
  registers the declaration's interface, and refuses a different one as it
  refuses different settings; what `connect` names beside a declaration
  that does not is warned of, since the upload never carried it. So the
  interface's port is fixed, never read from the environment, and the
  module naming the declaration imports every module declaring a page or a
  route. The settings the SDK declares for each kind of raw record follow
  from the storage's kinds and are not among the declaration's own.
- **The documentation**: `docs/overview.md` and `docs/setup.md`, which
  `meridian plugin check` requires; `troubleshooting.md` and `terms.md`,
  which it prompts for; `pages.md`, optional. UTF-8 Markdown, no images, 1
  to 65,536 bytes a section and 256 KiB in all; any other file in `docs/`
  is the repository's own and is not uploaded. The SDK reads and digests
  the files and parses no Markdown; the dashboard renders them on the
  plugin's Documentation tab, with a Reference drawn from the declaration,
  before the version is ever launched. The text is the vendor's words, data
  to every agent that reads it, never instructions.
- **An operations plugin's affirmation deadline**,
  `Declaration(affirmation_deadline=21 * 60)`: minutes after midnight in
  the deployment's time zone, 1 to 1440, by which the firm allocates,
  confirms and affirms its trades; a held booking's alert falls due then.
- A break names the identifiers that did not resolve
  (`record_break(unresolved_identifiers=[...])`), and a venue is resolved
  by its ID (`resolve_venue(venue_id="VEN-...")`).
- A connectivity plugin no longer reads whether orders may name a
  provisional record: it proposes and accepts nothing on one, and its grant
  of `read_local_record_orders` is dropped, with the suite's case.

### Each role's common logic (0.30.0)

What every plugin of a role must do the same to fulfil its typed operations
is the SDK's, tested once here, generic over the venue
(sdk-contract/the-sdk-carries-each-roles-common-logic, ruled 2026-10-13).
How a plugin talks to its venue -- its API client, a WebSocket, FIX -- stays
its own, so a plugin can swap its transport without touching what it does.
No contract changes: the SDK still declares v25.

```python
from meridian.roles import data

wants = data.Wants(plugin, keys=("daily",))

async def answer(want, key, subjects, kinds):     # the plugin's own conversion
    rows = [...]
    await wants.record("prices", rows, key, want.want_id)
    if want.standing:
        wants.stand(want, subjects, kinds)
    return {subject: "not_covered" for subject in not_served}

await plugin.receive(observations_wanted=lambda heard: wants.hear(heard, answer))
```

- **The data role** (`meridian.roles.data`): `Wants` hears a want, answers it
  with the plugin's conversion -- an answer that raises declines every
  subject `source_silent`, said and not raised -- declines what it does not
  serve by reason, keeps a standing want until it is withdrawn, records rows
  in the lake's batches and counts them overall and per dataset, reads its
  datasets' licences, and reads a restart's gap back once per subject per
  process (`backfill`, over `backfill_restart`). `Venue` resolves the venue
  master's ID once and reports a venue not held once; `unconverted` carries a
  value that did not read, and that venue, as reported. `served` and
  `want_rows` fill Datasets; `VenueConnection` is Connection for a source of
  one venue. `number`, `json_decimal` and `Unread` read a venue's figures from
  its own text, never a float; `Session`, `Health`, `Limits` and `Endpoint`
  say how the venue answers.
- **A venue's whole work, by what it lists**: `meridian.roles.data.pairs`
  for a venue listing pairs, a base asset priced in a quote asset (daily
  closes and bars, live prices, trades and quotes, the stream kept current
  and its gaps read back), and `meridian.roles.data.event_contracts` for a
  venue of binary event contracts (live prices and quotes, and each
  contract's outcome). The plugin hands its `Feed` a `Market` -- its client's
  answers read into the module's values -- and, for a stream, its own
  session as the stream factory (`Feed(..., stream_factory=Stream)`, a
  `Streamer`). Each draws its pages from the kind's templates
  (`meridian/roles/data/pairs/connection.html` and `datasets.html`), filled
  by `connection_read`, `datasets_read` and `figures_read`.
- **The checks a plugin runs unchanged** (`meridian.roles.data.testing`):
  the lake as a test stands it in (`Lake`), the data suite's producers for
  each kind, and `PairsChecks` and `EventContractsChecks`, run as one test
  class against the plugin's own conversion, its `venue_cases` naming its
  synthetic exchanges:

  ```python
  class TestPairs(PairsChecks):
      venue = venue_cases
  ```

- **Raw records as files** (`meridian.edge.RawStore`): a vendor's answers
  kept before anything is read from them, a unit a UTC day, a live answer a
  line added only when it changed, and the units past the kind's window
  archived, kept or deleted (`store.tend(plugin, window_days, past, today)`).
- **Connectivity** (`meridian.roles.connectivity`): the role's whole work
  over a venue's adapter. `Trader` hears each placement naming its instance
  and places it in the account its `ems` mapped, noted in storage before it
  is sent and never sent twice (`Sent`, `place_once`); reports what the venue
  did -- a refusal rejected, a send never answered outcome unknown and
  resolved from the venue's orders by the tag it was sent with
  (`resolve_unanswered`), a status not mapped said as reported
  (`report_status_not_mapped`); reports each fill into the book as the venue
  stated it or inferred from two averages (`fill_price`, `execution_id`,
  `filled_in_book`), and a bust (`bust_id`); works cancels and replaces;
  keeps the firm's pauses and stops; publishes the venue's catalogue; and
  reports fills of orders placed outside the platform (`Watched`). The
  plugin hands it a `Venue` -- its client's answers read into `VenueOrder`,
  a send raising `VenueRefused` or `VenueUnanswered`, each exchange kept as
  a raw record -- and the listing market's zone (`market_zone=`; price
  places and the default currency where they differ). Its Trading page is
  `trading_read`, drawn by `meridian/roles/connectivity/trading.html`, with
  `TradingAsked` and `TradingEnabled` for "Enable trading".
  `meridian.roles.connectivity.testing.Rig` runs a plugin's own adapter over
  its fake broker against the suites' recorder: fakes only, never a real
  broker or a token.

  ```python
  trader = connectivity.Trader(
      plugin, lambda: venue, now=lambda: datetime.now(UTC),
      sent=connectivity.Sent(sent), enabled=connectivity.Sent(enabled),
      watched=connectivity.Watched(originated),
      market_zone=ZoneInfo("America/New_York"),
  )
  await trader.run(poll_seconds=lambda: 5.0)
  ```

- A role template for connectivity (`templates/connectivity`) joins the
  others: the Trader over a stand-in venue held in memory.
- The role's Datasets template pages its Wants with the kit's `om-pager`.

### The analytics component, event groups and the agents' guard (contract v26)

0.31.0 declares contract v26 (`meridian.SCHEMA_VERSION`).

- **Asking the analytics component** (`meridian.analytics`; a `reporting`,
  `portfolio`, `compliance` or `signal` plugin): a job built with typed
  builders, checked as it is built, answered inline or later; every figure
  read with how it was computed (`exact` now, `model` from v28) and the
  scenario it is under, a weight compared by cross-multiplication, and what
  was not evaluated listed with why, never as a zero.

  ```python
  from meridian import analytics

  job = analytics.job(
      analytics.measure("exposure", by=["asset_class"]),
      analytics.measure("historical_var"),
      accounts=["ACC-12"],
  )
  answer = await analytics.Jobs().run(plugin, job)   # waits for one answered later
  for figure in answer.figures("exposure"):
      print(figure.breakdown, figure.value)
  ```

  `exposure` answers each bucket gross and net, each a `component`
  breakdown; `pnl` version 1 is Unrealized P&L, one `unrealized` component
  per bucket (realized P&L since the account opened is `pnl` version 2,
  served from 0.32.0, below). A job answered later is heard on
  `job_finished` (`plugin.receive(job_finished=jobs.heard)`) and caught up by
  sequence (`jobs.catch_up`).
- **The reference computations** (`meridian.analytics.reference`): v26's
  models (`cash`, `quoted_price`, `binary_event`) and its eight measure
  definitions in `decimal` and exact fractions, which the engine equals
  exactly, the answer's hash included: SHA-256 over the RFC 8785 canonical
  JSON of a case's inputs. The pinned cases are `tests/reference_cases/`,
  written by `tools/write_reference_cases.py`.
- **A pricing plugin** (`meridian.roles.pricing.Pricer`): each batch the
  component routes to it answered whole, from exactly the market objects
  each unit carries, with no sensitivity until v28; the batches still
  waiting read after a restart, from the last sequence answered, kept in
  memory, since `pricing` holds no storage. `reference_model` is the built-in models'
  own computation, so an implementation of a v26 model equals them.
- **Event groups**: `meridian.EventGroups` keeps every version read
  (`list_event_groups`) and heard (`event_group_changed`), and answers the
  one in force at a moment; a venue's data plugin reports its venue's
  grouping with `event_contracts.Feed.report_event`, a flag the venue does
  not state reported not stated, never false. Every role's suite's
  `hears-and-reads-an-event-group` is answered by the SDK.
- **The agents' demo-only guard**: `meridian.environment(demo="paper")`
  offers paper beside sandbox; a connectivity adapter says which environment
  its session reached (`environment`, read with
  `meridian.reached_environment`), which the Trader publishes on its
  catalogue; `meridian.connection_badge` draws Demo, Live or "Live
  (environment not confirmed)"; `Caller.agent_refused` says before sending
  what the book would refuse an agent.
- **The agent tools**: `plugin.query_lake`, one bounded query of the lake,
  and `plugin.count_model_tokens`, a model's tokens on every heartbeat.
- **The QuantLib oracle** (`tests/oracle`): QuantLib pinned in the
  `oracle` extra alone, never a dependency of the SDK or an image; committed
  case sets, regenerated only on a version bump (`make oracle-regenerate`),
  and a scheduled live run (`make oracle-live`); its calendars built from
  core's settlement calendars.

### More of each role's common logic (0.31.0; ruling 213)

- **Custody's pages** (`custody.account_pages` over a plugin's
  `CustodySource`): Account links, Statements and History, each the same
  answer as its tool, from Alpaca's and Tradier's plugins.
- **A broker's US equity listings** (`meridian.roles.data.listings`): the
  lake layer Alpaca's and Tradier's plugins kept, a plugin subclassing
  `listings.Feed` and converting only its broker's trade conditions.
- **The Trader** reports the charges a venue states apart from its orders
  (`VenueCharge`) and a fill's settlement date it states, awaits an async
  adapter, and dates a fill in its order's own zone: SnapTrade's trading,
  onto the SDK.

### The placement type, TCA, rates, latency and liveness (contract v27; 0.32.0 and 0.32.1)

0.32.0 declares contract v27 (`meridian.SCHEMA_VERSION`).

- **The analytics component** serves `pnl` version 2, realized P&L since
  the account opened beside unrealized (`analytics.measure("pnl", 2)`;
  rulings 320 and 396), and `execution_cost` version 1, each execution
  against the mid at its decision, arrival, placement arrival and fill, in
  bps, side-adjusted, positive a cost, a quote past its 5-second bound never
  imputed. A job takes a `business_date` and a `reporting_currency`, and is
  refused with no account, as the component refuses it. The reference
  computations round a quoted price once per unit to 18 places (rulings 453
  and 486), invert a fiat leg the lake holds only the other way and cross one
  it holds neither way through the deployment's pivots, USD's then EUR's
  (rulings 462 and 483), never a token's; each answer names the business
  date, each position's input price and each conversion leg; a lot's cost
  the book does not record is `NOT_EVALUATED_REASON_COST_MISSING`, never
  zero. Twelve pinned cases, four new.
- **The rates slice** (`meridian.roles.data.rates`; ruling 345): a
  publisher's fixings, averages, index levels and curves' points as `Rate`
  rows -- a 3.87 per cent fixing is 3.87 `percent`, never a Money -- each
  subject a referential record resolved by the identifiers it states, a
  same-day revision the next version of its row key, a tenor not published
  no row; a reader's curve for a date in tenor order (`read_curve`).

  ```python
  from meridian.roles.data import rates

  feed = rates.Feed(plugin, "ust", wants=wants)
  curve = await feed.subject(("symbol", "PAR_NOMINAL", "ust"), instrument_type="rate_curve")
  rows = feed.curve(curve, "ust_par", "par_yield", {"1 Mo": "4.12", "10 Yr": "4.21"},
                    business_date=day, published_ns=at, convention=rates.BOND_EQUIVALENT)
  await feed.record("ust_par", rows)
  ```
- **Latency, data age and liveness** (`meridian.roles.Latency`; rulings 415
  to 427): a histogram per session and metric and per dataset and hop,
  HdrHistogram's layout at 2 significant digits, taken every 10 seconds as
  `ReportLatency`'s snapshots with their counters, clock skew, liveness and
  the ceilings in force (`meridian.session_ceilings()`, `ceilings_from`).
  **Recorded, not yet reported**: core receives `ReportLatency` from
  contract v28 (rulings 515 and 516), so 0.32.0 records every session and
  hop locally, shows it in "Sessions", and sends nothing; the liveness
  below is sent. The suites' three latency reports are about `latency`, and
  a v27 plugin names them not presented: "core receives ReportLatency from
  contract v28, ruling 515" (ruling 518). A data plugin's
  `Wants.latency` records each row's age at the edge, its feed delay, and
  `Wants.liveness` a stream's heartbeat, which confirms the values in force
  (`RecordLiveness`); a dataset declares its delay
  (`DatasetDeclaration.declared_delay_ns`) and its admin its staleness
  (`meridian.dataset_thresholds()`). A reader keeps the latest liveness heard
  (`roles.Liveness`) for a value's confirmed time (`confirmed_ns`), and
  `roles.in_session` reads a venue's trading sessions. Connection and
  Trading show each session's latency in "Sessions" (`SessionLatency`).
- **The placement type and RFQ quotes**: the Trader takes the placement
  types its venue takes (an adapter's `placement_types`, on its catalogue;
  any other rejected unsupported), records each dealer's quote on an RFQ
  placement and each later outcome once (`VenueQuote`; an adapter's
  `request_quotes`, `quotes`, `accept_quote`), accepts the quote its `ems`
  picked once, and records its session's round trip, order acknowledgement
  and fill delay. An `ems` checks its reference price's age before a
  placement (`roles.ems.ReferenceCheck`): past the tighter of the dataset's
  ceiling and its admin's own (`meridian.stale_reference_after()`), in
  session, it holds the order with `HOLD_CAUSE_REFERENCE_PRICE_STALE` or
  places it marked, as its admin chose (`meridian.stale_reference_action()`);
  `roles.ems.open_quotes` offers an RFQ placement's quotes best first.
- **Connectivity's pages** (`connectivity.trading_pages`,
  `raw_records_page`): Trading with "Enable trading", the connection's badge
  and Sessions, and Raw records, from Alpaca's and Tradier's; for a plugin
  holding the data role too, one Connection for both roles
  (`connection_pages`, 457).
- **Event contracts**: a range member's floor, cap and unit reported with
  its group (ruling 464); the events of the contracts served kept reported
  (`Feed.keep_events`).
- **The data suite**: seven rates cases (about `rates`), a stream's
  liveness (about `streams`), every data plugin's feed delay (about
  `latency`, not presented until v28: ruling 518); the lake's
  bounded query is about trades, so a plugin recording none marks it not
  presented. `data.testing` carries `rates_producers` and each kind's cases
  never presented (`PAIRS_NOT_PRESENTED`, `EVENT_CONTRACTS_NOT_PRESENTED`).
  From 0.32.1 (ruling 537) `an-exact-price` and `a-want-recorded-against`
  are about `closes`, so a plugin recording rates and no prices names them
  not presented, "it records rates, never prices";
  `RATES_NOT_PRESENTED` names every case a rates-only plugin never
  presents.
- **Smaller**: a licence writes both `derived_use` and `derived_use_terms`
  (ruling 479); a venue-originated order is resolved by every identifier its
  venue states (`VenueOrder.identifiers`, `.currency`); a rejected replace's
  raw record names its venue account; a good-till-date order is asked with
  its expiry (`Asked.expire_date`, `.expire_time_ns`).

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
| 0.21.0 to 0.22.0: the SDK declares contract v18, the lake's 1a: a data plugin's catalogue (`Declaration(catalogue=[DatasetDeclaration(...)])`, `DatasetLicence`, `ObservationMode`), prices and bars recorded in batches of 1 to 500 (`plugin.record_prices`, `plugin.record_bars`, `Price`, `Bar`, `ObservationMeta`, `SourceTime`, `Source`, `SubjectRef`), wants heard and declined (`receive(observations_wanted=, want_withdrawn=)`, `want_id=`, `plugin.decline_want`), the lake's reads by business date, as of and side by side (`list_prices`, `list_bars`, `list_datasets`, `SourceChoice`), prices and bars heard latest value first for the subjects named with their dataset (`receive(prices_recorded=, bars_recorded=, subjects=)`, `Heard.dataset`), venues resolved (`resolve_venue`, `report_missing_venue`), the data suite and the reading roles' (a heard row delivered by `answer`); a Money names its cash instrument (`Money.instrument_id`; `Money(amount, "USD")` resolved by core, dated); every date field takes a `datetime.date`, and refuses text that is no date. `Money(amount, code)` keeps its shape, so `meridian plugin migrate` needs no change in the command line | only the pins move | a test comparing a Money read back (`as_money`) with one it made, which now carries `instrument_id`: compare `amount` and `currency_code`; a date sent as text that is no date, refused |
| 0.23.0 to 0.24.0: the SDK declares contract v20. Breaking: the roles `dgm`, `ccm` and `match` are `data`, `connectivity` and `confirmation`. An act names its check tool, its accounts and its page (`checked_by=`, `accounts=`, `made_on=`), a page reads the prepared change it was opened from (`request.prepared()`), a route's record names no field `prepare`; a person's own settings (`Setting(per_person=True)`, `plugin.set_own_settings`, `request.own_settings`); a link to an account not granted refused (`REFUSAL_REASON_ACCOUNT_NOT_LINKABLE`); a data plugin's licences (`list_datasets`) and its restart backfilled (`list_trades(latest_recorded=True)`, `meridian.roles.data.backfill_restart`); the data suite's v20 cases and `about_field`; each role's common part (`meridian.roles`), `meridian.environment()`, `@meridian.settings`, `meridian.sample_data()` and `meridian/kit.html` | a role named `dgm`, `ccm` or `match` in `pyproject.toml`'s `[tool.meridian]` roles, a `roles=` argument, or the role a suite is run or an access read for, into `data`, `connectivity` or `confirmation` | a role's old name anywhere else, in words or a variable; a developer setting named `synthetic`, which `meridian.sample_data()` replaces at the plugin's next push; an act to be preparable: name its check tool |
| 0.22.0 to 0.23.0: the SDK declares contract v19, the lake's 1b: trades and quotes recorded in batches of 1 to 500 (`plugin.record_trades`, `plugin.record_quotes`, `Trade`, `TradeAttributes`, `Eligibility`, `Quote`), read (`list_trades` over a range or `after_watermark=`, `list_quotes`) and heard (`receive(trades_recorded=, quotes_recorded=, subjects=)`: every trade, caught up after the watermark last seen; the latest quote per asset); a price heard is conflated per its asset too; `reporting` resolves an identifier; the data suite's eight 1b cases, a case about a kind of data the plugin never publishes not presented with why (`Case.about`), `signal`'s 1b cases, the `ems` suite, `reporting`'s `resolves-its-reporting-currency` | only the pins move | a data plugin's suite test meeting the eight new cases: map each, or name those about trades or quotes in `not_presented` with why where it publishes neither |
| 0.24.0 to 0.25.0: the SDK declares contract v21, a service account runs a plugin's autonomous work: an act called as the role's service account (`meridian.runs_as(role)`), answered made or prepared, a refusal naming its field (`NotGranted.fields`, `CallFailed.fields`); a caller who is a service account (`Caller.subject_kind`, `Caller.owner_subject`, `meridian.SubjectKind`), and a tool's call as one in a plugin's own test (`PageClient.call_tool(subject_kind=, owner_subject=)`) | only the pins move | |
| 0.25.0 to 0.26.0: the SDK declares contract v22, the order path's slice A and settlement calendars: the order path's typed operations (`propose_order`, `release_order`, `record_check`, `decide_approval`, `set_working_condition`, `create_placement`, `request_order_change`, `request_placement_change`, `report_placement`, `report_execution`, `report_charge`, `record_order`, `acknowledge_flag`, `list_orders`, `read_order_history`, `list_trading_instructions`, the locate's and the venue catalogue's, `map_venue_account`) and deliveries (`receive(order_updated=, placement_updated=, execution_recorded=, unplaced_fact_recorded=, trading_instruction_changed=, locate_updated=, report_venue_catalogue=)`), the order path's refusal codes, the transition table (`meridian/transitions.json`); the calendars (`read_calendar`, `compute_date`); a version's algorithms (`Declaration(algorithms=)`, `AlgorithmDeclaration`, `runs_as(role, algorithm_id=)`, `Caller.algorithm_id`); the connectivity plugins a caller may route through (`Caller.connectivity_instance_ids`); a sleeve on positions, lots and movement lines; the suites' v22 cases | only the pins move | a suite test meeting the calendar reads every role now holds (`reads-a-calendar`, `asks-for-a-settlement-date`): map each |
| 0.26.0 to 0.27.0: the SDK declares contract v23, venue-originated fills and the lake's outcomes: a connectivity plugin's fill on no placement (`report_execution`'s `instrument_id`, `side`, `venue_order_id`, `venue_client_order_id`), waiting unmatched (`Execution.state`, `ExecutionState`); the ems's accept and DK (`accept_execution`, `NewOrderFromExecutions`, `dont_know_execution`, `DkReason`) and their refusal codes; a connectivity plugin hearing the executions it reported (`receive(execution_recorded=)`); `VenueCatalogue.execution_acknowledgement`; `list_orders(execution_state=)`; an event contract's outcomes (`record_outcomes`, `Outcome`, `receive(outcomes_recorded=)`, `list_outcomes`); the closed-day flag (`ObservationMeta.closed_day`) and a dataset's closed-day counts; the suites' v23 cases | only the pins move | none |
| 0.27.0 to 0.28.0: the SDK declares contract v24, an execution booked to its accounts and one ID for every instrument: booking (`book_order`, `Allocation`, `hand_off_booking`, `correct_booking`, `BookingCorrectionKind`, `list_bookings`, `receive(booking_updated=)`, `BookingState`, `ErrorCause`), the allocation instruction amended (`set_allocation_instruction`), the give-up (`report_give_up`, `GiveUpAnswer`), the sleeve cross (`record_sleeve_cross`, `SleeveCross`), the alert (`raise_alert`, `acknowledge_alert`, `list_alerts`, `receive(alert_changed=)`, `AlertKind`, `AlertState`); cash under option (c); a provisional record (`InstrumentRecord.provisional`, `ResolveIdentifierResult.provisional`, `template_id`, `template_version`), the replacement heard by every role and caught up by sequence (`receive(replace_merged_instrument=)`, `list_replacements`, `ReplacementCause`) and followed by `meridian.CurrentIdMap`; the template catalogue (`list_templates`, `read_template`, `meridian.TemplateCatalogue`); `offer_template_fields` and the `reference` suite, in preview; `read_local_record_orders`; every suite's two cases the SDK answers; the suites' resolves answering `INS-suite-n`, and `LCL-suite-n` on `Recorder(provisional=True)`; `DatasetDeclaration.calendar_id`; `meridian.environment()` defaulting to `sandbox` | a record's `instrument_id.startswith("LCL-")` into its `provisional`; the platform's ID read from the `open_meridian` identifier into the record's `instrument_id` (the read's default where the record is provisional); a test's `LCL-suite-n` into `INS-suite-n` | an ID tested for the prefix `LCL-` with no record at hand: read the record's `provisional`; `open_meridian` read or written any other way; a plugin whose environment was Live by default: say `environment(default="live")` only where Live is meant, otherwise its admin chooses |
| 0.28.0 to 0.29.0: the SDK declares contract v25, plugins shared through registries and carrying their own documentation: the whole declaration (`Declaration(interface=, reads_external_accounts=, documentation=, affirmation_deadline=)`, its settings, interface, tools and documentation by digest), `meridian-declaration --documentation`, registration held to the version uploaded, `connect` refusing an interface its declaration does not name; `record_break(unresolved_identifiers=)`, `resolve_venue(venue_id=)`; the give-up cases marked `about: give-ups`. Breaking: a plugin whose declaration does not carry its interface is refused at registration until it does | a connectivity plugin's `await plugin.read_local_record_orders()` removed, and its test's mapping of `reads-whether-orders-may-name-local-records` | `connect` given an interface, settings or `reads_external_accounts`: declare them in the `Declaration`, the port fixed, and pass `connect(declaration=DECLARATION)`; a `[tool.meridian]` naming no `declaration`: name one, and write `docs/overview.md` and `docs/setup.md`; a Dockerfile whose last stage copies no documentation directory (one installing only the package from a mount): `COPY docs/ docs/`, or the whole context as the templates do (`COPY . .`), since the declaration reads its sections in the built image; a connectivity plugin's read of the escape hatch whose answer it uses: remove it and what depends on it |
| 0.29.0 to 0.30.0: each role's common logic in the SDK, contract v25 unchanged: `meridian.roles.data` a package -- `Wants` (wants heard and declined by reason, standing wants, rows recorded in the lake's batches and counted, licences, a restart's gap read back once), `Venue`, `unconverted`, `asked`, the venue's reading (`number`, `json_decimal`, `Unread`, `Session`, `Health`, `Limits`, `Endpoint`), `served`, `want_rows`, `WantHeard`, `VenueConnection`; `meridian.roles.data.pairs` and `.event_contracts`, a venue's whole work by what it lists (`Feed`, `ProductMap`, `ContractMap`, their pages and templates); `meridian.roles.data.testing` (`Lake`, the suite's producers, `PairsChecks`, `EventContractsChecks`); `meridian.edge.RawStore`; `meridian.roles.connectivity` (`Sent`, `place_once`, `resolve_unanswered`, `report_status_not_mapped`, `execution_id`, `bust_id`, `fill_price`, `filled_in_book`, and the role's work: `Trader` over a `Venue`, `Watched`, `trading_read` and its template, `testing.Rig`); a connectivity role template; the role's Wants paged | a module copied from a sibling plugin (`market.py`, `products.py`, `contracts.py`, `raw.py`, `dgm.py`, saying "The same module in ... and ...") into a re-export of the SDK's names; a trading layer in SnapTrade 0.16.0's shape (`trading.py` defining `Trader`, `Noted`, `Venue`, `Watched`, `trading_files`) into a re-export of `meridian.roles.connectivity`, its `Trader` in the module's market zone | import from the SDK and delete the re-exports, constructing `Trader` with `market_zone=` and `Sent` for `Noted`; the Trading page: `trading_read` and the SDK's template; the trading test rig: a subclass of `testing.Rig`; the copied `page.py` and templates: the kind's builders and templates; the copied tests: one class of the SDK's checks; a copied `stream.py`: the plugin's own transport, handed to the feed; an assignment of a stream's `connect`: `retarget` it; the Makefile's suite-same: removed |
| 0.30.0 to 0.31.0: the SDK declares contract v26: `meridian.analytics` (typed builders for a job, `Answer`, `Jobs`) and its reference computations, the `pricing` role (`roles.pricing.Pricer`) and template, event groups (`EventGroups`, `event_contracts.Feed.report_event`), the agents' guard (`environment(demo="paper")`, `reached_environment`, `connection_badge`, `Caller.agent_refused`), `query_lake` and `count_model_tokens`; custody's pages (`custody.account_pages`), a broker's listings (`roles.data.listings`) and the Trader's charges and stated settlement dates (ruling 213) | a base pinned by digest at an older release moved to 0.31.0, its digest dropped (offline) | pin the base's digest again; map each role suite's v26 cases; give a connectivity adapter its `environment`; move custody pages, a listings layer or a SnapTrade-shaped trader onto the SDK |
| 0.31.0 to 0.31.1: a saved setting value that is no longer one of its choices, or not of its kind, is delivered unset rather than raised (`Settings.refused`, a typed class's `.refused`, `meridian.RefusedSetting`, `request.own_settings_refused`), a required one named missing and an environment so refused counted live by the guard; an event-contract venue's contract map keeps a range market's bounds; `event_contracts.Feed.stated_identifiers`, by which `EventContractsChecks` holds a record complete, and a record holding the venue's ticker alone named by it; the pricing template declares no storage; the templates' AGENTS.md on publishing to a registry and their pre-push hook's tag-push message | only the pins move | |
| 0.31.1 to 0.32.0: the SDK declares contract v27: `pnl` version 2 and `execution_cost`, a job's business date and reporting currency, a job refused with no account; the reference rounding a quoted price per unit and inverting and crossing fiat legs; the rates slice (`roles.data.rates`); latency and data age recorded, not yet reported (ReportLatency from contract v28), and liveness recorded (`roles.Latency`, `SessionLatency`, `Liveness`, `in_session`, `Wants.latency`, `Wants.liveness`, `declared_delay_ns`, and the settings `session_ceilings`, `dataset_thresholds`, `stale_reference_action`, `stale_reference_after`); the Trader's placement types and RFQ quotes, the `ems`'s reference check (`roles.ems`); connectivity's pages (`trading_pages`, `raw_records_page`, `connection_pages`); a range member's bounds and `Feed.keep_events`; `derived_use_terms`; the suites' v27 cases. Breaking | a base pinned by digest at an older release moved to 0.32.0, its digest dropped (offline) | pin the base's digest again; map each role suite's v27 cases; mark a data plugin's lake query not presented where it records no trades; move a plugin's own Trading page or events loop onto the SDK; add `include-hidden-files: true` to an e2e log upload |
| 0.32.0 to 0.32.1: the data suite's `an-exact-price` and `a-want-recorded-against` are about `closes` (ruling 537), so a plugin recording rates and no prices names them not presented, "it records rates, never prices"; `meridian.roles.data.testing.RATES_NOT_PRESENTED` names every case a rates-only plugin never presents | only the pins move | |

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
