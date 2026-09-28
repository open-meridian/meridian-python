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
generated from the contract: `report_sync_status`, `record_holdings_statement`,
`record_holding`, `resolve_identifier` and `report_missing_instrument`. Amounts
are `Decimal`, and cross the wire as exact scaled integers, refused rather than
rounded.

## Working on it

    make ci-local

Run `make install-hooks` once on a fresh clone, so that `git push` fires
`ci-local` first. Without it the gate exists and does not run.

## Licence

Apache-2.0, so a plugin you write stays yours. See [LICENSE](LICENSE).
