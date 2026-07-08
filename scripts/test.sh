#!/usr/bin/env sh
# Platform-agnostic CI entrypoint (POSIX shell).
# Runs the dependency-direction static check + XDET-TC-000 gate.
set -e

echo "== import-linter (dependency direction) =="
uv run lint-imports

echo "== pytest (XDET-TC-000 + skeletons) =="
uv run pytest -q
