SHELL := /bin/bash
PY    := python3

# A pre-push hook runs with GIT_DIR naming this repository, absolutely when
# pushed from a worktree, and fetch_schema's `git init`, `fetch` and
# `checkout` in .schema-scratch would then act on this repository instead:
# marking this clone bare and shallow, and staging meridian-schema's
# bindings here.
unexport GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR \
         GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_PREFIX

.PHONY: help ci-local ci-remote ci-local-deep ci-stage pre-push pre-push-run install-hooks ci-mirror-check contract-diff \
        build package test lint conformance fmt vendor-schema check-vendored \
        base-image check-scaffold check-migrations oracle-live oracle-regenerate

help:
	@echo "  make pre-push       the fast gate the pre-push hook runs: lint, and the stages the changed paths select"
	@echo "  make ci-local       every gate, CI's and conformance: optional, for when CI is down"
	@echo "  make ci-stage STAGE=<job>  one CI job, as it runs there ($(CI_STAGES))"
	@echo "  make build          install the package and prove it imports"
	@echo "  make package        build the wheel and prove it installs alone"
	@echo "  make base-image     the plugin base image, plugin-python, from that wheel"
	@echo "  make check-scaffold the template and each role's, built on that base, holding only themselves"
	@echo "  make check-migrations each recorded migration's plugin, migrated, passes plugin check"
	@echo "  make vendor-schema  move the bundled wire bindings to SCHEMA_REV"
	@echo "  make test           run the unit tests"
	@echo "  make conformance    check this SDK against the contract's pinned bytes"
	@echo "  make lint           ruff and mypy, warnings denied"
	@echo "  make oracle-live    the QuantLib oracle's case sets against the pinned QuantLib (scheduled)"
	@echo "  make oracle-regenerate SET=<set>  a case set's answers from the pinned QuantLib (a version bump)"
	@echo "  make fmt            apply the formatter"
	@echo "  make install-hooks  point git at hooks/ so push fires pre-push"

# Every gate: CI's (ci-remote) and conformance. CI on the pull request runs
# ci-remote, and the pull request merges on it (accepted 2026-11-07,
# superseding ruling 1075's full local gate); this is the optional full run,
# for when CI is down. Every job in .github/workflows must be reachable from
# here.
ci-local: ci-remote conformance
	@echo
	@echo "ci-local: GREEN"

# What CI can run. Conformance is not in it, because the fixtures it checks
# against live in meridian-design, that repo is private, and a public repo
# holding a credential that reads private source is a worse trade than a gate
# confirmed elsewhere.
#
# Elsewhere is real, not a euphemism: meridian-design's own CI runs this SDK's
# conformance suite against its fixtures, and it is private so it may. Here, the
# pre-push hook runs conformance whenever the package or the suite changed
# (PRE_PUSH_MAP), so it passes before any such push from a workspace. The uncovered case is a commit made through GitHub's web interface,
# which nothing in this repo can check and design's next run will.
ci-remote: contract-diff ci-mirror-check check-vendored build package check-scaffold test \
           check-migrations lint
	@echo
	@echo "ci-remote: GREEN (conformance not included; see this target's comment)"

ci-local-deep: ci-local

# One CI job, as it runs there: reproduce a failing job with this before
# pushing again, rather than rerunning CI until it is green.
CI_STAGES := ci-remote oracle-live
ci-stage:
	@case " $(CI_STAGES) " in *" $(STAGE) "*) ;; \
		*) echo "ci-stage: STAGE is one of CI's jobs: $(CI_STAGES)" >&2; exit 2;; esac
	@$(MAKE) --no-print-directory $(STAGE)

# The fast gate (accepted 2026-11-07; the pre-push hook runs it): CI on the
# pull request runs ci-remote whole, so a push runs only what its changes
# reach. Every push runs the contract diff, the mirror and lint (ruff, its
# formatting and mypy); the rest only when a path the branch changed against
# PRE_PUSH_BASE maps to them here (<glob>=<stage>,...; tools/pre_push.py
# prints which ran and why):
#
#   python       build and test: the package imports, and its unit tests and
#                the templates' pass
#   vendored     check-vendored: the wire bindings are the schema's
#   package      package: the wheel installs alone
#   scaffold     check-scaffold: the base image and each role's template
#   migrations   check-migrations: each recorded migration passes plugin check
#   conformance  conformance, against design's fixtures at its origin/main;
#                not in CI (the fixtures are private), so here whenever the
#                package or the suite changes
PRE_PUSH_BASE ?= origin/main
PRE_PUSH_ALWAYS := checks
PRE_PUSH_ORDER := checks python vendored package scaffold migrations conformance
PRE_PUSH_MAP := \
	src/*=python,package,conformance \
	tests/*=python \
	tests/migrations/*=migrations \
	tests/test_migrations.py=migrations \
	src/meridian/migrations/*=migrations \
	tests/test_conformance.py=conformance \
	template/*=python,scaffold \
	templates/*=python,scaffold \
	src/meridian/v1/*=vendored \
	src/meridian/plugin/*=vendored \
	src/meridian/bounds.py=vendored \
	src/meridian/suites.json=vendored \
	src/meridian/fields.json=vendored \
	src/meridian/transitions.json=vendored \
	src/meridian/behaviours.json=vendored \
	pyproject.toml=python,package,scaffold,conformance \
	Dockerfile.python=python,package,scaffold,migrations,conformance \
	README.md=package LICENSE=package NOTICE=package \
	Makefile=python,vendored,conformance

pre-push:
	@$(PY) tools/pre_push.py --self-test >/dev/null
	@mkdir -p build
	@$(PY) tools/pre_push.py plan --base "$(PRE_PUSH_BASE)" --always "$(PRE_PUSH_ALWAYS)" \
		--order "$(PRE_PUSH_ORDER)" --map "$(PRE_PUSH_MAP)" --out build/pre-push.plan
	@began=$$(date +%s); \
	eval "$(MAKE) --no-print-directory pre-push-run $$(cat build/pre-push.plan)" \
		|| { echo "pre-push: FAILED after $$(( $$(date +%s) - began ))s" >&2; exit 1; }; \
	took=$$(( $$(date +%s) - began )); \
	echo; echo "pre-push: GREEN in $$((took / 60))m$$(printf %02d $$((took % 60)))s; CI runs everything else"

pre-push-run: $(addprefix pre-push-,$(PRE_PUSH_STAGES))

pre-push-checks: contract-diff ci-mirror-check lint
pre-push-python: build test
pre-push-vendored: check-vendored
pre-push-package: package
pre-push-scaffold: check-scaffold
pre-push-migrations: check-migrations
pre-push-conformance: conformance

ci-mirror-check:
	@$(PY) tools/ci_mirror_check.py --repo-root .

# ADR 005 in meridian-design. Contract-tier changes declare themselves in a
# commit trailer. Reads what changed on disk, so no tool or session root
# avoids it -- which is the whole reason it exists alongside the hook.
contract-diff:
	@$(PY) tools/check_contract_diff.py --self-test
	@$(PY) tools/check_contract_diff.py --repo-root .

# The wire bindings this package ships as `meridian.v1`: the schema's generated
# Python at one revision, copied into src/ and committed, so the package on
# PyPI depends on nothing by URL (PyPI refuses that) and a plugin installs one
# thing. `make vendor-schema` moves the copy to SCHEMA_REV; `check-vendored`
# fails when the two disagree, as core's check-codegen does for its bindings.
# meridian-schema c30 at 7bf0e73 (contract 30, DESIGN30 at c30 a47167e: core's
# stage M -- the refusals for load and Refusal.retry_after_seconds -- and the
# `load` behaviour cases; its PR open, before it lands), its gen/ and
# boundaries/ vendored here byte for byte.
SCHEMA_REV := 7bf0e732fdd3e772fd9e408a94a1afe2b7e1f806
SCHEMA_REPO := https://github.com/open-meridian/meridian-schema.git
SCRATCH     := .schema-scratch

define fetch_schema
	rm -rf $(SCRATCH) && git init -q $(SCRATCH) \
	&& git -C $(SCRATCH) fetch -q --depth 1 $(SCHEMA_REPO) $(SCHEMA_REV) \
	&& git -C $(SCRATCH) checkout -q FETCH_HEAD -- gen/python/meridian/v1 gen/python/meridian/plugin \
		gen/python/meridian/bounds.py boundaries/suites.json boundaries/fields.json \
		boundaries/transitions.json boundaries/behaviours.json
endef

vendor-schema:
	@$(fetch_schema)
	@rm -rf src/meridian/v1 src/meridian/plugin \
		&& cp -R $(SCRATCH)/gen/python/meridian/v1 src/meridian/v1 \
		&& cp -R $(SCRATCH)/gen/python/meridian/plugin src/meridian/plugin \
		&& cp $(SCRATCH)/gen/python/meridian/bounds.py src/meridian/bounds.py \
		&& cp $(SCRATCH)/boundaries/suites.json src/meridian/suites.json \
		&& cp $(SCRATCH)/boundaries/fields.json src/meridian/fields.json \
		&& cp $(SCRATCH)/boundaries/transitions.json src/meridian/transitions.json \
		&& cp $(SCRATCH)/boundaries/behaviours.json src/meridian/behaviours.json \
		&& rm -rf $(SCRATCH)
	@echo "vendor-schema: src/meridian/v1, src/meridian/plugin, src/meridian/bounds.py, the role suites, the data dictionary, the order's transitions and the behaviour cases are meridian-schema at $(SCHEMA_REV)"

check-vendored:
	@$(fetch_schema) || { echo "check-vendored: could not fetch meridian-schema at $(SCHEMA_REV)" >&2; rm -rf $(SCRATCH); exit 1; }
	@if diff -r -x __pycache__ $(SCRATCH)/gen/python/meridian/v1 src/meridian/v1 >/dev/null \
		&& diff -r -x __pycache__ $(SCRATCH)/gen/python/meridian/plugin src/meridian/plugin >/dev/null \
		&& diff $(SCRATCH)/gen/python/meridian/bounds.py src/meridian/bounds.py >/dev/null \
		&& diff $(SCRATCH)/boundaries/suites.json src/meridian/suites.json >/dev/null \
		&& diff $(SCRATCH)/boundaries/fields.json src/meridian/fields.json >/dev/null \
		&& diff $(SCRATCH)/boundaries/transitions.json src/meridian/transitions.json >/dev/null \
		&& diff $(SCRATCH)/boundaries/behaviours.json src/meridian/behaviours.json >/dev/null; then \
		rm -rf $(SCRATCH); echo "check-vendored OK: meridian.v1, meridian.plugin.v1, meridian.bounds, the role suites, the data dictionary, the order's transitions and the behaviour cases are meridian-schema at $(SCHEMA_REV)"; \
	else \
		rm -rf $(SCRATCH); echo "check-vendored FAILED: src/meridian/v1 is not meridian-schema at $(SCHEMA_REV). Run 'make vendor-schema'." >&2; exit 1; \
	fi

PY_VERSION := 3.12
DOCKER := DOCKER_BUILDKIT=1 docker
DESIGN ?= ../meridian-design

# The domain protos the tests encode payloads with. They live in meridian-core,
# pinned here by commit as the schema is pinned in pyproject.toml. Core's own
# interop gate overrides this with its working tree, so a change to both lands
# without either waiting on the other's push.
# Core's contract 30 protos (DESIGN30 at 7fd2bf0), its c30 branch the core
# stages build on, before it lands; journal.proto moved from there into
# meridian-schema.
CORE_REV   := 793bd22798caebe51581f8c6b5c9d09e1900ace1
CORE_PROTO ?= https://github.com/open-meridian/meridian-core.git\#$(CORE_REV):proto
# And meridian-schema's, which core's import, at the revision vendored here.
SCHEMA_PROTO ?= https://github.com/open-meridian/meridian-schema.git\#$(SCHEMA_REV):proto
# The analytics engine's oracle cases (contract v29; requirement 36): the
# platform's packages' cases and QuantLib's answers core holds its debt
# models to, which the SDK's reference computations are held to as well
# (tests/test_v29_reference.py), read at the same revision, never copied.
CORE_ORACLE ?= https://github.com/open-meridian/meridian-core.git\#$(CORE_REV):crates/analytics-engine/oracle_cases
CONTEXTS   := --build-context core-proto=$(CORE_PROTO) --build-context schema-proto=$(SCHEMA_PROTO) \
              --build-context core-oracle=$(CORE_ORACLE)

build:
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target check . >/dev/null 2>&1 \
		|| { echo "build FAILED; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build $(CONTEXTS) -f Dockerfile.python --target check --progress=plain ." >&2; exit 1; }
	@echo "build OK: the package installs and imports"

# The package as a plugin author gets it: built from the source alone,
# installed where there is no git, and checked for what it must and must not
# carry (see the `installed` stage).
package:
	@$(DOCKER) build -f Dockerfile.python --target installed . >/dev/null 2>&1 \
		|| { echo "package FAILED; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build -f Dockerfile.python --target installed --progress=plain ." >&2; exit 1; }
	@echo "package OK: open-meridian installs from its wheel alone, with the wire bindings and nothing by URL"

# The plugin base image and the scaffold on it (spec/the-local-plugin-registry).
# The version is pyproject.toml's, and the template's pin and its FROM line
# must name the same one: a scaffold built on one SDK and pinning another
# would install the second over the first, and send it with every upload.
SDK_VERSION := $(shell sed -n 's/^version = "\(.*\)"$$/\1/p' pyproject.toml)
BASE_IMAGE  ?= plugin-python:local

base-image:
	@$(DOCKER) build -f Dockerfile.python --target plugin-base --build-arg SDK_VERSION=$(SDK_VERSION) \
		-t $(BASE_IMAGE) . >/dev/null 2>&1 \
		|| { echo "base-image FAILED; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build -f Dockerfile.python --target plugin-base --build-arg SDK_VERSION=$(SDK_VERSION) --progress=plain ." >&2; exit 1; }
	@echo "base-image OK: $(BASE_IMAGE), Python and open-meridian $(SDK_VERSION)"

# The roles' templates, which `meridian plugin new --role <role>` writes:
# each a whole plugin holding that role, sharing these files with template/
# byte for byte, so the agents' instructions, the CI and the image are one.
ROLE_TEMPLATES := data reporting custody operations connectivity pricing
SHARED := AGENTS.md CLAUDE.md Dockerfile .dockerignore .gitignore \
          .claude/skills/develop-live/SKILL.md .github/workflows/check.yaml \
          hooks/pre-push docs/overview.md docs/setup.md docs/troubleshooting.md \
          docs/terms.md docs/pages.md

# What a plugin author gets: the template built on the base, as its Dockerfile
# says. It must hold the base's SDK rather than a second copy -- what it adds
# on top is small, where the SDK and its gRPC are tens of megabytes -- carry
# the base's label, run as 65532, and start. Each role's template shares its
# files, declares its role, builds on the base and starts; the data plugin's
# declaration prints from its image, as `meridian plugin upload` reads it.
check-scaffold: base-image
	@grep -q '^dependencies = \["open-meridian==$(SDK_VERSION)"\]' template/pyproject.toml \
		|| { echo "check-scaffold FAILED: the template does not pin open-meridian==$(SDK_VERSION)" >&2; exit 1; }
	@grep -q '^ARG BASE=ghcr.io/open-meridian/plugin-python:$(SDK_VERSION)$$' template/Dockerfile \
		|| { echo "check-scaffold FAILED: the template's Dockerfile is not FROM plugin-python:$(SDK_VERSION)" >&2; exit 1; }
	@$(DOCKER) build --build-arg BASE=$(BASE_IMAGE) -t reference-plugin:check template >/dev/null 2>&1 \
		|| { echo "check-scaffold FAILED: the template does not build on the base; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build --build-arg BASE=$(BASE_IMAGE) --progress=plain template" >&2; exit 1; }
	@label="$$(docker inspect -f '{{index .Config.Labels "dev.meridian.sdk-version"}}' reference-plugin:check)"; \
	[ "$$label" = "$(SDK_VERSION)" ] \
		|| { echo "check-scaffold FAILED: the plugin's image says SDK $$label, not $(SDK_VERSION)" >&2; exit 1; }
	@added=$$(( $$(docker inspect -f '{{.Size}}' reference-plugin:check) - $$(docker inspect -f '{{.Size}}' $(BASE_IMAGE)) )); \
	[ "$$added" -lt 5000000 ] \
		|| { echo "check-scaffold FAILED: the plugin adds $$added bytes over its base; it reinstalled the SDK rather than using the base's" >&2; exit 1; }
	@[ "$$(docker inspect -f '{{.Config.User}}' reference-plugin:check)" = "65532" ] \
		|| { echo "check-scaffold FAILED: the plugin does not run as 65532" >&2; exit 1; }
	@docker run --rm --entrypoint python reference-plugin:check -c "import meridian, reference_plugin.__main__" \
		|| { echo "check-scaffold FAILED: the plugin's image does not import the SDK and itself" >&2; exit 1; }
	@docker run --rm --entrypoint sh reference-plugin:check -c "test ! -e /plugin/AGENTS.md && test ! -e /plugin/CLAUDE.md && test ! -e /plugin/.claude" \
		|| { echo "check-scaffold FAILED: the plugin's image holds the agents' files, which .dockerignore keeps out" >&2; exit 1; }
	@for role in $(ROLE_TEMPLATES); do \
		for shared in $(SHARED); do \
			cmp -s template/$$shared templates/$$role/$$shared \
				|| { echo "check-scaffold FAILED: templates/$$role/$$shared is not template/$$shared; the role's templates share the reference plugin's" >&2; exit 1; }; \
		done; \
		grep -q "^roles = \[\"$$role\"\]$$" templates/$$role/pyproject.toml \
			|| { echo "check-scaffold FAILED: templates/$$role does not declare roles = [\"$$role\"]" >&2; exit 1; }; \
		$(DOCKER) build --build-arg BASE=$(BASE_IMAGE) -t reference-$$role:check templates/$$role >/dev/null 2>&1 \
			|| { echo "check-scaffold FAILED: templates/$$role does not build on the base; see it with:" >&2; \
			     echo "  DOCKER_BUILDKIT=1 docker build --build-arg BASE=$(BASE_IMAGE) --progress=plain templates/$$role" >&2; exit 1; }; \
		docker run --rm --entrypoint python reference-$$role:check -c "import meridian, reference_plugin.__main__" \
			|| { echo "check-scaffold FAILED: templates/$$role's image does not import the SDK and itself" >&2; exit 1; }; \
	done
	@for image in reference-plugin $(addprefix reference-,$(ROLE_TEMPLATES)); do \
		docker run --rm --entrypoint meridian-declaration $$image:check reference_plugin.declaration:DECLARATION >/dev/null \
			&& docker run --rm --entrypoint meridian-declaration $$image:check --documentation reference_plugin.declaration:DECLARATION >/dev/null \
			|| { echo "check-scaffold FAILED: $$image's declaration, or its documentation from /plugin/docs, does not print from its image" >&2; exit 1; }; \
	done
	@echo "check-scaffold OK: the template and each role's ($(ROLE_TEMPLATES)) build on plugin-python:$(SDK_VERSION); the template adds only itself, without the agents' files; each declaration and its documentation print from its image"

test:
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target test . >/dev/null 2>&1 \
		|| { echo "test FAILED; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build $(CONTEXTS) -f Dockerfile.python --target test --progress=plain ." >&2; exit 1; }
	@echo "test OK: the client's tests pass, and the template's own"

# The plugins the migrations are recorded for (tests/migrations), migrated as
# `meridian plugin migrate` does it and held to what it runs next: `meridian
# plugin check --run-tests`, from the released command line named here, as a
# plugin's own CI installs it. `make test` checks what each migration writes
# and runs each plugin's own tests; this adds the framework's rules.
MERIDIAN_CLI := 0.1.55

check-migrations:
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target migrations \
		--build-arg MERIDIAN_CLI_VERSION=$(MERIDIAN_CLI) . >/dev/null 2>&1 \
		|| { echo "check-migrations FAILED; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build $(CONTEXTS) -f Dockerfile.python --target migrations --build-arg MERIDIAN_CLI_VERSION=$(MERIDIAN_CLI) --progress=plain ." >&2; exit 1; }
	@echo "check-migrations OK: every recorded migration's plugin passes meridian $(MERIDIAN_CLI)'s plugin check --run-tests"

# The fixtures are not in this repo. Read from the design repo, so this SDK and
# the Rust runtime assert against the same pinned bytes rather than against
# each other: at design's origin/main (accepted 2026-11-07, as design's own
# gate reads its siblings), fetched into a bare cache under build/ through
# the checkout at DESIGN, never its working tree, and written to build/ for
# the run (tools/sibling-at-main.sh). DESIGN_AT=worktree reads DESIGN's
# working tree instead, for fixtures not yet on design's main.
DESIGN_AT ?= main
DESIGN_CACHE := build/siblings/meridian-design.git
DESIGN_MAIN := build/siblings/meridian-design

conformance:
	@if [ "$(DESIGN_AT)" = worktree ]; then \
		test -d "$(DESIGN)/fixtures" \
			|| { echo "no fixtures at $(DESIGN)/fixtures; set DESIGN=<path to meridian-design>" >&2; exit 1; }; \
		fixtures="$(abspath $(DESIGN))/fixtures"; at="$(DESIGN)'s working tree"; \
	else \
		rev=$$(tools/sibling-at-main.sh files "$(DESIGN)" $(DESIGN_CACHE) $(DESIGN_MAIN) fixtures) \
			|| { echo "conformance FAILED: design's fixtures at its main could not be read (DESIGN=$(DESIGN))" >&2; exit 1; }; \
		fixtures="$(CURDIR)/$(DESIGN_MAIN)/fixtures"; at="design's main at $$rev"; \
	fi; \
	$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target conformance -t meridian-python-conformance . >/dev/null 2>&1 \
		|| { echo "conformance image FAILED to build" >&2; tools/sibling-at-main.sh remove $(DESIGN_CACHE) $(DESIGN_MAIN); exit 1; }; \
	docker run --rm \
		-v "$$fixtures":/fixtures:ro \
		-e MERIDIAN_FIXTURES=/fixtures \
		meridian-python-conformance \
		python -m pytest -q tests/test_conformance.py >.conformance.log 2>&1; \
	status=$$?; tools/sibling-at-main.sh remove $(DESIGN_CACHE) $(DESIGN_MAIN); \
	if [ $$status -ne 0 ]; then \
		echo "conformance FAILED against $$at. The last 30 lines, and the whole of it in .conformance.log:" >&2; \
		tail -30 .conformance.log >&2; exit 1; \
	fi; \
	echo "conformance OK: this SDK decodes and re-encodes every pinned message, $$at"

# The QuantLib oracle (spec/the-analytics-engines-first-release, Q12):
# committed answers from the pinned QuantLib, which `make test` holds the
# case sets to offline, and this scheduled live run (the oracle-live
# workflow), every case recomputed by the pinned QuantLib and held to its
# tolerance. Out of ci-local by that ruling, so the gate stays offline and
# deterministic; reproducible here.
oracle-live:
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target oracle -t meridian-python-oracle . >/dev/null 2>&1 \
		|| { echo "oracle-live FAILED to build the oracle image" >&2; exit 1; }
	@docker run --rm --network none meridian-python-oracle python -m oracle --live

# A case set regenerated by the pinned QuantLib, printed and written here,
# never copied back from the container: only on a deliberate version bump,
# its diff reviewed (Q12). SET names one, as tests/oracle/cases/<SET>.json.
oracle-regenerate:
	@test -n "$(SET)" || { echo "oracle-regenerate: SET=<case set>" >&2; exit 1; }
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target oracle -t meridian-python-oracle . >/dev/null 2>&1 \
		|| { echo "oracle-regenerate FAILED to build the oracle image" >&2; exit 1; }
	@docker run --rm --network none meridian-python-oracle python -m oracle --write oracle/cases/$(SET).json \
		> .oracle-$(SET).json && mv .oracle-$(SET).json tests/oracle/cases/$(SET).json \
		&& echo "oracle-regenerate: tests/oracle/cases/$(SET).json from QuantLib; review its diff"

lint:
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target lint . >/dev/null 2>&1 \
		|| { echo "lint FAILED; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build $(CONTEXTS) -f Dockerfile.python --target lint --progress=plain ." >&2; exit 1; }
	@echo "lint OK: ruff and mypy clean"

# Applied in a container and written back, because the host has no toolchain.
fmt:
	@docker run --rm -v "$(CURDIR)":/w -w /w python:$(PY_VERSION)-slim \
		sh -c 'pip install -q ruff >/dev/null 2>&1; python -m ruff check --fix src tests template/src template/tests templates >/dev/null; python -m ruff format src tests template/src template/tests templates'
	@echo "fmt: applied"

install-hooks:
	@git config core.hooksPath hooks
	@echo "hooks installed: git push now runs 'make pre-push' first"
