# meridian-python

The Python SDK for building Meridian plugins.

A plugin talks only to its local sidecar. It holds no persistent state and seeds
from the kernel on start. See [CLAUDE.md](CLAUDE.md).

Plugins themselves live in their own repositories. This one stays thin.

```python
import meridian_sdk

async with await meridian_sdk.connect() as plugin:
    print(plugin.identity.role, plugin.grants.publish)
    await plugin.publish("platform.custody.acme-1.event.sync-status", event)
```

    make ci-local

Run `make install-hooks` once on a fresh clone, so that `git push` fires
`ci-local` first. Without it the gate exists and does not run.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
