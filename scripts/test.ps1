# Platform-agnostic CI entrypoint (Windows PowerShell).
# Runs the dependency-direction static check + XDET-TC-000 gate.
# Usage:  pwsh scripts/test.ps1   (or)   powershell -File scripts/test.ps1
$ErrorActionPreference = "Stop"

Write-Host "== import-linter (dependency direction) =="
uv run lint-imports
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== pytest (XDET-TC-000 + skeletons) =="
uv run pytest -q
exit $LASTEXITCODE
