SHELL := /bin/bash
PY    := python3

.PHONY: help ci-local ci-remote ci-local-deep install-hooks ci-mirror-check contract-diff \
        build package test lint conformance fmt vendor-schema check-vendored \
        base-image check-scaffold

help:
	@echo "  make ci-local       run every gate (the pre-push gate, and what CI mirrors)"
	@echo "  make build          install the package and prove it imports"
	@echo "  make package        build the wheel and prove it installs alone"
	@echo "  make base-image     the plugin base image, plugin-python, from that wheel"
	@echo "  make check-scaffold the template, built on that base, holding only itself"
	@echo "  make vendor-schema  move the bundled wire bindings to SCHEMA_REV"
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
ci-remote: contract-diff ci-mirror-check check-vendored build package check-scaffold test lint
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

# The wire bindings this package ships as `meridian.v1`: the schema's generated
# Python at one revision, copied into src/ and committed, so the package on
# PyPI depends on nothing by URL (PyPI refuses that) and a plugin installs one
# thing. `make vendor-schema` moves the copy to SCHEMA_REV; `check-vendored`
# fails when the two disagree, as core's check-codegen does for its bindings.
SCHEMA_REV  := 77d8a9842a29f59d6d4781287c5733540d8b147a
SCHEMA_REPO := https://github.com/open-meridian/meridian-schema.git
SCRATCH     := .schema-scratch

define fetch_schema
	rm -rf $(SCRATCH) && git init -q $(SCRATCH) \
	&& git -C $(SCRATCH) fetch -q --depth 1 $(SCHEMA_REPO) $(SCHEMA_REV) \
	&& git -C $(SCRATCH) checkout -q FETCH_HEAD -- gen/python/meridian/v1 gen/python/meridian/plugin
endef

vendor-schema:
	@$(fetch_schema)
	@rm -rf src/meridian/v1 src/meridian/plugin \
		&& cp -R $(SCRATCH)/gen/python/meridian/v1 src/meridian/v1 \
		&& cp -R $(SCRATCH)/gen/python/meridian/plugin src/meridian/plugin \
		&& rm -rf $(SCRATCH)
	@echo "vendor-schema: src/meridian/v1 and src/meridian/plugin are meridian-schema at $(SCHEMA_REV)"

check-vendored:
	@$(fetch_schema) || { echo "check-vendored: could not fetch meridian-schema at $(SCHEMA_REV)" >&2; rm -rf $(SCRATCH); exit 1; }
	@if diff -r -x __pycache__ $(SCRATCH)/gen/python/meridian/v1 src/meridian/v1 >/dev/null \
		&& diff -r -x __pycache__ $(SCRATCH)/gen/python/meridian/plugin src/meridian/plugin >/dev/null; then \
		rm -rf $(SCRATCH); echo "check-vendored OK: meridian.v1 and meridian.plugin.v1 are meridian-schema at $(SCHEMA_REV)"; \
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
CORE_REV   := c9d710e0af9d68775ade5a678a8c686aec9619f4
CORE_PROTO ?= https://github.com/open-meridian/meridian-core.git\#$(CORE_REV):proto
CONTEXTS   := --build-context core-proto=$(CORE_PROTO)

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

# What a plugin author gets: the template built on the base, as its Dockerfile
# says. It must hold the base's SDK rather than a second copy -- what it adds
# on top is small, where the SDK and its gRPC are tens of megabytes -- carry
# the base's label, run as 65532, and start.
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
	@echo "check-scaffold OK: the template builds on plugin-python:$(SDK_VERSION) and adds only itself"

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
		sh -c 'pip install -q ruff >/dev/null 2>&1; python -m ruff check --fix src tests template/src >/dev/null; python -m ruff format src tests template/src'
	@echo "fmt: applied"

install-hooks:
	@git config core.hooksPath hooks
	@echo "hooks installed: git push now runs 'make ci-local' first"
