#!/usr/bin/env sh
# Platform-agnostic CI entrypoint (POSIX shell).
# Reproduces the 4 CI jobs from .github/workflows/gui.yml + the core gate:
#   import-linter, core-no-gui, gui-offscreen, license-gate.
set -e

echo "== import-linter (dependency direction, core 4 layers + apps.gui forbidden) =="
uv run lint-imports

echo "== core-no-gui: full core TC suite, GUI tests excluded from collection (C-12) =="
uv run pytest --ignore=tests/apps -q

echo "== gui-offscreen: headless GUI suite (C-14/C-15) =="
uv sync --extra gui --extra dev
QT_QPA_PLATFORM=offscreen uv run pytest tests/apps/gui -q

echo "== license-gate: GPL-only dependency gate, PyQt6 excluded (C-13) =="
uv run pytest tests/apps/gui/test_tc_viewer_arch.py -k license -q
