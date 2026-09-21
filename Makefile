SHELL := /bin/bash
PY    := python3

.PHONY: help ci-local ci-remote ci-local-deep install-hooks ci-mirror-check contract-diff \
        build test lint conformance fmt

help:
	@echo "  make ci-local       run every gate (the pre-push gate, and what CI mirrors)"
	@echo "  make build          install the package and prove it imports"
	@echo "  make test           run the unit tests"
	@echo "  make conformance    check this SDK against the contract's pinned bytes"
	@echo "  make lint           ruff and mypy, warnings denied"
	@echo "  make fmt            apply the formatter"
	@echo "  make install-hooks  point git at hooks/ so push fires ci-local"

# Local green is the completion signal; CI is confirmation.
# Every job in .github/workflows must be reachable from here.
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
# pre-push hook runs ci-local, so conformance passes before any push from a
# workspace. The uncovered case is a commit made through GitHub's web interface,
# which nothing in this repo can check and design's next run will.
ci-remote: contract-diff ci-mirror-check build test lint
	@echo
	@echo "ci-remote: GREEN (conformance not included; see this target's comment)"

ci-local-deep: ci-local

ci-mirror-check:
	@$(PY) tools/ci_mirror_check.py --repo-root .

# ADR 005 in meridian-design. Contract-tier changes declare themselves in a
# commit trailer. Reads what changed on disk, so no tool or session root
# avoids it -- which is the whole reason it exists alongside the hook.
contract-diff:
	@$(PY) tools/check_contract_diff.py --self-test
	@$(PY) tools/check_contract_diff.py --repo-root .

PY_VERSION := 3.12
DOCKER := DOCKER_BUILDKIT=1 docker
DESIGN ?= ../meridian-design

# The domain protos the tests encode payloads with. They live in meridian-core,
# pinned here by commit as the schema is pinned in pyproject.toml. Core's own
# interop gate overrides this with its working tree, so a change to both lands
# without either waiting on the other's push.
CORE_REV   := c27a40c44b42d6e724a7d155174f7e4898822021
CORE_PROTO ?= https://github.com/open-meridian/meridian-core.git\#$(CORE_REV):proto
CONTEXTS   := --build-context core-proto=$(CORE_PROTO)

build:
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target check . >/dev/null 2>&1 \
		|| { echo "build FAILED; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build $(CONTEXTS) -f Dockerfile.python --target check --progress=plain ." >&2; exit 1; }
	@echo "build OK: the package installs and imports"

test:
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target test . >/dev/null 2>&1 \
		|| { echo "test FAILED; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build $(CONTEXTS) -f Dockerfile.python --target test --progress=plain ." >&2; exit 1; }
	@echo "test OK: the client's tests pass"

# The fixtures are not in this repo. Mounted read-only from the design repo, so
# this SDK and the Rust runtime assert against the same pinned bytes rather than
# against each other.
conformance:
	@test -d "$(DESIGN)/fixtures" \
		|| { echo "no fixtures at $(DESIGN)/fixtures; set DESIGN=<path to meridian-design>" >&2; exit 1; }
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target conformance -t meridian-python-conformance . >/dev/null 2>&1 \
		|| { echo "conformance image FAILED to build" >&2; exit 1; }
	@docker run --rm \
		-v "$(abspath $(DESIGN))/fixtures":/fixtures:ro \
		-e MERIDIAN_FIXTURES=/fixtures \
		meridian-python-conformance \
		python -m pytest -q tests/test_conformance.py >.conformance.log 2>&1 \
		|| { echo "conformance FAILED. The last 30 lines, and the whole of it in .conformance.log:" >&2; \
		     tail -30 .conformance.log >&2; exit 1; }
	@echo "conformance OK: this SDK decodes and re-encodes every pinned message"

lint:
	@$(DOCKER) build $(CONTEXTS) -f Dockerfile.python --target lint . >/dev/null 2>&1 \
		|| { echo "lint FAILED; see it with:" >&2; \
		     echo "  DOCKER_BUILDKIT=1 docker build $(CONTEXTS) -f Dockerfile.python --target lint --progress=plain ." >&2; exit 1; }
	@echo "lint OK: ruff and mypy clean"

# Applied in a container and written back, because the host has no toolchain.
fmt:
	@docker run --rm -v "$(CURDIR)":/w -w /w python:$(PY_VERSION)-slim \
		sh -c 'pip install -q ruff >/dev/null 2>&1; python -m ruff check --fix src tests >/dev/null; python -m ruff format src tests'
	@echo "fmt: applied"

install-hooks:
	@git config core.hooksPath hooks
	@echo "hooks installed: git push now runs 'make ci-local' first"
