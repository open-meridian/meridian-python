# meridian-python

The Python SDK for building Meridian plugins, and the reference plugins built
on it.

## Placement

The SDK exposes a domain API over generated types. It never hands plugin authors
raw wire types; that indirection is what lets a plugin survive a schema change.

Plugins here are reference implementations. Anything genuinely cross-cutting
belongs in the sidecar, in the runtime, not duplicated into each plugin.

## Rules with teeth

**Plugins are ephemeral.** No persistent state, no local database, no file it
expects to still be there. A plugin seeds from the kernel on start and can be
killed and replaced at any moment without losing anything.

**A plugin never mints reference data.** When an instrument does not resolve,
the plugin publishes the fact that a resolution missed and moves on to the next
row. It does not block, does not retry in a loop, and could not create the
instrument if it wanted to. Something with the authority to mint subscribes and
reacts.

**Quantities and money are integers scaled by 1e8.** Never a float, at any
layer, including the adapter that reads a third-party API. Convert at the
boundary, on the way in, once.

**Credentials come from the environment.** Never a literal, never a fixture,
never a committed configuration file outside sandbox placeholders.

**Resolution is dated.** Ask what an identifier meant on a date. An undated
lookup is a bug waiting for the day an identifier gets reassigned.

## Conventions

Type hints everywhere, checked. Formatting and lint are enforced by `ci-local`,
so do not argue with the formatter. Prefer a dataclass over a dict for anything
that crosses a function boundary more than once.

Async where the work is I/O bound, which for a connector is nearly all of it.

## Verification

    make ci-local

Conformance runs against the fixtures in the design repo, so this SDK and the
Rust kernel assert against the same pinned bytes rather than against each other.
Plugin tests run against the aggregator's sandbox, whose data is deterministic,
so they are real integration tests rather than mocks.
