# Platform-agnostic CI entrypoint (Windows PowerShell).
# Reproduces the 4 CI jobs from .github/workflows/gui.yml + the core gate:
#   import-linter, core-no-gui, gui-offscreen, license-gate.
# Usage:  pwsh scripts/test.ps1   (or)   powershell -File scripts/test.ps1
$ErrorActionPreference = "Stop"

Write-Host "== import-linter (dependency direction, core 4 layers + apps.gui forbidden) =="
uv run lint-imports
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== core-no-gui: full core TC suite, GUI tests excluded from collection (C-12) =="
uv run pytest --ignore=tests/apps -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== gui-offscreen: headless GUI suite (C-14/C-15) =="
uv sync --extra gui --extra dev
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$env:QT_QPA_PLATFORM = "offscreen"
uv run pytest tests/apps/gui -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== license-gate: GPL-only dependency gate, PyQt6 excluded (C-13) =="
uv run pytest tests/apps/gui/test_tc_viewer_arch.py -k license -q
exit $LASTEXITCODE
