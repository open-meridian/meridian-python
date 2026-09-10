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

## Review

Every pull request gets the same passes, in the same order, whether a person or
an agent wrote it. Uniformity is the point: a review that varies by author is a
review whose absence is invisible.

Mechanical checks do not belong in a review. Formatting, link targets, the
derivation chain, codegen staleness and the task ledger are enforced by
`make ci-local`. Attention spent on something a gate could catch is a missing
gate, and the fix is to write the gate.

Run the passes in order. Report at the first pass that finds an Important
finding; later passes still run, but the finding does not wait.

1. **Correctness.** Does it do what the spec says, and does it fail safely when
   it does not? State that survives a restart when it should not, or does not
   when it should. Error paths that swallow rather than surface. Concurrency
   assumptions that hold only under test timing. Arithmetic on money that is not
   exact decimal.
2. **Security.** Credentials in the diff, in a log line, in a fixture or in a
   compose file. Anything widening what an agent session may do without a human
   in the loop. New outbound network calls. Changes to `.claude/settings.json`,
   to hooks or to permissions are read line by line, every time.
3. **Contract compliance.** Does the change respect the derivation direction? A
   build-stage pull request touching a workflow, the matrix, the topic registry
   or a proto is a finding on its own, whether or not the change is a good one.
   The route is a contract-revision task, not an edit.
4. **Spec and plan alignment.** Does the diff match the plan it was approved
   against, and does that plan trace to a spec and an intent? A diff that
   quietly grew beyond its plan is a finding even when every added line is
   sound, because the scope was never reviewed.

**Important** findings are ship-blocking: data loss, a security exposure, a
wrong result, a broken contract, or scope that was never approved. State the
concrete failure, meaning the inputs, the state, and what goes wrong. A finding
without a failure scenario is a Nit wearing a costume.

**Nit** is everything else. Cap Nits at five and drop the weakest past that. A
review returning thirty Nits trains its reader to skim.

Excluded from review entirely: generated files, vendored dependencies, and
anything a CI gate already enforces.

**Always post a result, including when every pass is clean.** Say which
passes ran and that nothing was found. Silence is indistinguishable from
never having run, and a review nobody can tell apart from an absent one is
the failure the review gate in this repo exists to catch. There is no diff
small enough to be worth staying quiet about.

People decide whether a finding merges or escalates, and whether the spec solves
the problem it claims to. Those stay with a named person.

> Canonical text: `meridian-design/REVIEW.md`. This copy exists because the
> reviewer runs in this repository and cannot read a private one. Drift between
> the two is a bug, not a variation.
