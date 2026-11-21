# Contributing

Open Meridian is open source, and built by its team: we don't accept pull
requests from outside it. The best way to help is an issue.

- **Found a bug?** Open an issue with **Report a bug**: what you did, what you
  expected, and what happened instead.
- **Have an idea?** Open an issue with **Suggest an improvement**: the problem
  you have, and what would solve it for you.

Describe rather than paste code. We build every change ourselves, from your
description.

## Your suggestions

By opening an issue or making a suggestion, you give Societal Lab Inc. a
perpetual, irrevocable, worldwide, royalty-free licence to use it for any
purpose, with no obligation to you. That lets us act on what you tell us
without any question of who owns the result.

## Building on Open Meridian

Plugins are how you extend Open Meridian, and they live in your own
repositories, not ours: the Python SDK and the plugin contract are Apache-2.0,
so a plugin you write stays yours. Start with `meridian plugin new`; see
[open-meridian.dev](https://open-meridian.dev).

## For the team

`make install-hooks` makes every push run `make pre-push`, the fast gate:
lint, and the stages the changed paths select (the Makefile's
`PRE_PUSH_MAP`), conformance among them. A change goes on a branch and lands
through one pull request per version, its summary the change log. CI on the
pull request runs everything else, and it merges when green, up to date with
`main`, as a merge commit: that keeps the branch's commit SHAs, which other
repositories pin. Reproduce a failing CI job with `make ci-stage
STAGE=<job>` before pushing again; `make ci-local` runs every gate, for when
CI is down.

## Code structure

These rules are checked, not reviewed: `make check-structure` runs each in
the pre-push gate and in CI, and fails the build when one is broken. Where
today's code breaks a rule, a baseline records today's figure, and every
reduction lowers it.

- **Generated files are generated.** A file written by a generator carries
  its header and is regenerated and compared in the gate, so a hand edit
  fails. Here that is the wire bindings, bounds and the contract's JSON,
  copied from meridian-schema at one revision (`make check-vendored`), and
  the interims register (`make check-interims`).
- **Interims name their end.** A stop-gap carries a marker,
  `INTERIM(vNN): reason`, naming the version it ends in and why it exists.
  The register `tools/interims.tsv` is generated from the markers. The
  repository's roadmap version is in `tools/code-structure.toml`; a marker
  for that version or an earlier one fails the build, so the stop-gap is
  removed before the version ships. Moving a marker to a later version
  needs the product owner's word and a `Baseline-Change:` trailer naming
  the marker (`make check-baselines` fails a move without one).
- **Pins are immutable.** This repository depends on another by an
  immutable reference: a released artefact or a full commit SHA, never a
  branch name or a sibling checkout. `make check-pins` reads
  `pyproject.toml` and every workflow (`uses:`, and the `ref:` of a
  checkout of another repository). An exception is listed in
  `tools/pins-allowlist.txt` with its interim marker.
- **Licences by layer.** The SDK, its template and its role templates are
  Apache-2.0, so a plugin built on them stays its author's. No GPL or AGPL
  code enters them (`make check-licences`), and NOTICE ships beside the
  licence.
- **File size.** A new hand-written file stays under 1,500 lines. An
  existing file over that may grow only with a `Size-Exception:` trailer
  giving the reason. Generated files are exempt. `make check-size` reports
  both against `tools/size-baseline.tsv`; it warns for now and will fail.
- **Baselines change in the open.** A change to a baseline or an allowlist
  carries a `Baseline-Change:` trailer saying why, and a baseline only goes
  down (`make check-baselines`).
