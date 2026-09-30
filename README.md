# meridian-python

The Python SDK for building [Open Meridian](https://open-meridian.com) plugins:
the tools a trader has an AI agent build, and the bots and analytics a
developer writes. Python 3.11 or newer.

## Start here

Start a plugin with the command line, not from this repository:

    meridian plugin new my-plugin
    meridian plugin dev --instance my-plugin   # on a deployment installed with --development

`plugin new` writes this repository's `template/`, the reference plugin: its
code and its page, built on the plugin UI kit (open-meridian/meridian-ui), a
`Dockerfile`, and `AGENTS.md`, which teaches any coding agent to build pages
with the kit and the live loop (`CLAUDE.md` and a Claude Code skill lead to
it). See
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
the person is, whether they are a deployment admin, and their access on this
plugin, as two sets of accounts. A person's access to a plugin is `read` or
`write`, the same for every plugin, and a plugin declares no parts of itself
for access (decisions/026): `read` is what the plugin may show them, and
`write`, which includes it, is what the plugin may do for them.

```python
caller = meridian.Caller.from_header(header)
shown = sorted(caller.read)  # every account the page may show them
if caller.may_write("ACC-1"):
    await plugin.record_holdings_statement(..., acting_for=caller.header)
```

`caller.read` and `caller.write` are the sets themselves. The sidecar checks
every command sent for the person again, whatever the plugin believes.
`meridian.TagAccess` and `Caller.access`, the same access tag by tag, are
gone, and say so when reached for.

### Linking external accounts

A custody plugin links the external accounts it reported on its own admin
page, for the deployment admin viewing it: pass the `Meridian-Caller` header
the page request carried as `acting_for`. The sidecar refuses both without an
assertion saying the person is a deployment admin, and a link for an account
the plugin did not report.

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

## Working on it

    make ci-local

Run `make install-hooks` once on a fresh clone, so that `git push` fires
`ci-local` first. Without it the gate exists and does not run.

## Licence

Apache-2.0, so a plugin you write stays yours. See [LICENSE](LICENSE).
