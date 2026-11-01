"""Logic shared across roles by topic (ruling 1001).

A module here holds one topic's work that plugins of several roles do the
same: a data plugin recording a chain and a reader reading it, custody and
connectivity reporting a lifecycle record and servicing proposing one. It
grants nothing: roles gate permissions and access, and their modules are
`meridian.roles`; a typed operation a helper calls is allowed or refused by
the plugin's own roles, as any other call is.

From 0.33.0 (contract v28) listed options' and futures' work
(sdk-contract/listed-options-and-futures-contract): `chains`, a chain's
series keyed by their OSI symbols, recorded and read under the underlying
with their statistics, and a series asked for before an order;
`lifecycle`, an exercise, assignment, expiry or day of variation reported
as the broker states it, `servicing`'s exercise by exception proposed and
`operations`' release of a proposal no report answered; and `packages`, a
package order's legs in lowest terms and its fill reported once for the
package and once per leg.

From 0.34.0 (contract v29) fixed income's work
(sdk-contract/fixed-income-contract): `debt`, the contract's money rules
(percent of par, a pool's cash and current face at its factor, a
paydown's principal, the cent half-even), a coupon's accrual by its day
count, an agency's factor recorded and read, a yield as its source quotes
it, a capped size and the trade characteristics, and the book's own words
on a pool's fill read (the factor taken, provisional, an open claim);
`lifecycle` the seven fixed-income records reported as the custodian
states them and `servicing`'s expected coupons, maturities, paydowns and
accretions.

From 0.35.0 (spec/each-role-is-one-generated-class, ruling 1023) a helper
defines no act of its own: one that reads or acts takes the role object
holding the act (`chains.read_chain(role, ...)`, `debt.read_factors(role,
...)`), never the connection, so the act is allowed or refused by that
role. `sessions` holds `Backoff`, the wait between a long-running work's
tries, with which `meridian.run` restarts a role's `run()`.

These four were `meridian.roles.chains`, `.packages`, `.lifecycle` and
`.debt` until 0.34.0; `meridian plugin migrate` rewrites a plugin's
imports of them.
"""

from . import chains, debt, lifecycle, packages, sessions

__all__ = ["chains", "debt", "lifecycle", "packages", "sessions"]
