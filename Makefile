# XDET T0 framework — platform-agnostic CI entrypoints (REQ-INFRA-CI-2).
# CI runtime is TBD (Gitea Actions likely); these targets are the neutral
# interface CI wraps.

.PHONY: install lint test ci

install:
	uv pip install -e ".[dev]"

lint:
	uv run lint-imports

test:
	uv run pytest -q

# Full module-level gate (XDET-TC-000): static dependency check + tests.
ci: lint test
