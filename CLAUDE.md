# meridian-go

The Go SDK, and the reference plugins built on it. Public.

## Placement

The SDK exposes a domain API over generated types. It never exposes raw wire
types to plugin authors; that is what makes a plugin survive a schema change.

Plugins here are reference implementations. Anything a plugin needs that is
genuinely cross-cutting belongs in the sidecar, in `meridian-core`, not
duplicated into each plugin.

## Rules with teeth

**Plugins are ephemeral.** No persistent state. A plugin seeds from the kernel
on start and can be killed and replaced at any moment without losing anything.

**A plugin never mints reference data.** When an instrument does not resolve, the
plugin reports that a miss happened and moves on. It does not block, does not
retry in a loop, and does not create the instrument. The administrator's console
subscribes and reacts. This is a fact on the wire, not a request.

**Quantities and cash are scaled integers.** Never a float, at any layer,
including the adapter that reads a third-party API.

**Credentials come from the environment.** Never a literal, never a fixture,
never a compose file outside sandbox placeholders.

## Verification

    make ci-local

Conformance runs against the fixtures in `meridian-design`, so this SDK and the
Rust kernel assert against the same pinned bytes rather than against each other.
