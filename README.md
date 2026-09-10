# meridian-python

The Python SDK for building Meridian plugins, and the reference plugins built on
it.

A plugin talks only to its local sidecar. It holds no persistent state and seeds
from the kernel on start. See [CLAUDE.md](CLAUDE.md).

    make ci-local

Run `make install-hooks` once on a fresh clone, so that `git push` fires
`ci-local` first. Without it the gate exists and does not run.
