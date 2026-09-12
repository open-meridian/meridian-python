# meridian-python

The Python SDK for building Meridian plugins, and the reference plugins built on
it.

A plugin talks only to its local sidecar. It holds no persistent state and seeds
from the kernel on start. See [CLAUDE.md](CLAUDE.md).

    make ci-local

Run `make install-hooks` once on a fresh clone, so that `git push` fires
`ci-local` first. Without it the gate exists and does not run.

## Licence

Apache-2.0. Build a plugin with it, ship the plugin, keep it closed if you want
to.

That is the point rather than an oversight. Meridian's premise is best-of-breed
plugins from independent vendors, and a copyleft licence on the library they
link against would oblige every one of them to publish their plugin. Whether a
plugin is legally a derivative work is a question lawyers disagree about, and
the practical effect is that a cautious vendor assumes the worst and builds
something else instead.

`meridian-core`, the deployment runtime, is AGPL. Running that as a service and
returning nothing is what the network clause exists to prevent, and nothing here
changes it.

