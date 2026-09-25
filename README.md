# meridian-python

The Python SDK for building Meridian plugins.

A plugin talks only to its local sidecar. It holds no persistent state and seeds
from the kernel on start. See [CLAUDE.md](CLAUDE.md).

Plugins themselves live in their own repositories. This one stays thin.

Published to PyPI as `open-meridian`, imported as `meridian` (not yet
published; see meridian-design's plans/a-person-reaches-a-plugin, step 0):

    pip install open-meridian==0.1.0

The name `meridian-sdk` on PyPI is an unrelated company's. Do not install it.

The package carries the wire bindings it speaks to the sidecar with, as
`meridian.v1`, at the schema revision `SCHEMA_REV` in the Makefile names.
`make vendor-schema` moves them; `make check-vendored` fails when they lag.

```python
import meridian

async with await meridian.connect() as plugin:
    print(plugin.identity.role, plugin.grants.publish)
    await plugin.publish("platform.custody.acme-1.event.sync-status", event)
```

    make ci-local

Run `make install-hooks` once on a fresh clone, so that `git push` fires
`ci-local` first. Without it the gate exists and does not run.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
