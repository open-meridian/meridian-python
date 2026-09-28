# meridian-python

The Python SDK for building [Open Meridian](https://open-meridian.com) plugins:
the tools a trader has an AI agent build, and the bots and analytics a
developer writes. Python 3.11 or newer.

## Start here

Start a plugin with the command line, not from this repository:

    meridian plugin new my-plugin
    meridian plugin dev --instance my-plugin   # on a deployment installed with --development

`plugin new` writes this repository's `template/`, the reference plugin: its
code and page, a `Dockerfile`, and `AGENTS.md`, which teaches any coding agent
the live loop (`CLAUDE.md` and a Claude Code skill lead to it). See
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
`record_holdings_statement`, `record_holding`, `resolve_identifier` and
`report_missing_instrument`.

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
