"""Architecture / install / license gates -- Phase 2 (REQ-VIEW-ARCH-1~4, XDET-TC-036).

Headless, logic-level only (C-15). `pytest.importorskip("qtpy")` guards this
module from collection in the `core-no-gui` job's `[gui]`-less base install
(C-12) even though none of these tests actually import `apps.gui` at the
Python level (import-linter and pip-licenses are both external subprocesses;
this guard is kept for convention parity with the sibling Phase 1/2 test
modules).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

pytest.importorskip("qtpy")

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py<3.11 fallback, unused here
    import tomli as tomllib  # type: ignore[no-redef]

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# @MX:NOTE: [AUTO] `python -m importlinter.cli` has no __main__ guard and exits
# 0 without running any check -- the console script is the only reliable
# entrypoint (lesson #1, mirrors tests/test_tc000.py::LINT_IMPORTS).
LINT_IMPORTS = str(Path(sys.executable).parent / "lint-imports")
PIP_LICENSES = str(Path(sys.executable).parent / "pip-licenses")


def _run_lint_imports(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [LINT_IMPORTS, *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.stdout.strip() or result.stderr.strip(), (
        "lint-imports produced no output -- the check did not actually run"
    )
    return result


# -- REQ-VIEW-ARCH-1 (C-11): production forbidden contract -------------------


def test_production_gui_forbidden_contract_is_kept():
    """The real tree's core -> apps.gui forbidden contract passes (Scenario 8a)."""
    result = _run_lint_imports()
    assert result.returncode == 0, (
        f"lint-imports failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "GUI is a one-way consumer: core must never import apps.gui" in result.stdout
    assert "KEPT" in result.stdout


# -- REQ-VIEW-ARCH-2 (C-11 canary, EC-2): vacuous-pass guard (lesson #1) -----


def test_badgui_canary_detects_core_to_apps_gui_violation():
    """A seeded core->apps.gui violation, in an isolated fixture package
    OUTSIDE `root_packages`, is actually caught by a narrowly-scoped temp
    import-linter config (proves the production contract is not a vacuous
    pass -- tests/fixtures/badlayers negative-control precedent)."""
    ini = textwrap.dedent(
        """
        [importlinter]
        root_packages=
            tests
            apps

        [importlinter:contract:1]
        name = badgui core->apps.gui forbidden canary
        type = forbidden
        source_modules =
            tests.fixtures.badgui.core_analog
        forbidden_modules =
            apps.gui
        """
    ).strip()
    with tempfile.NamedTemporaryFile(
        "w", suffix=".ini", delete=False, dir=PROJECT_ROOT
    ) as fh:
        fh.write(ini)
        cfg_path = Path(fh.name)
    try:
        result = _run_lint_imports("--config", str(cfg_path))
        assert result.returncode != 0, (
            "import-linter should have detected the seeded core -> apps.gui "
            f"violation:\n{result.stdout}\n{result.stderr}"
        )
        assert "core_analog" in result.stdout
    finally:
        cfg_path.unlink(missing_ok=True)


# -- REQ-VIEW-ARCH-3 (C-12): extras isolation (structural) --------------------


def test_gui_dependencies_isolated_in_optional_extras():
    """Base `[project.dependencies]` carries no Qt/GUI package; `[gui]` extras does."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    base_deps = " ".join(pyproject["project"]["dependencies"]).lower()
    gui_extra = " ".join(pyproject["project"]["optional-dependencies"]["gui"]).lower()

    for pkg in ("pyqtgraph", "pyside6", "qtpy", "pytest-qt"):
        assert pkg not in base_deps, f"{pkg} must not leak into base dependencies (C-12)"
        assert pkg in gui_extra, f"{pkg} must be declared in the [gui] extra"


# -- REQ-VIEW-ARCH-4 (C-13): license gate ------------------------------------


def _is_gpl_only(license_str: str) -> bool:
    """True when `license_str` denotes GPL licensing with NO LGPL alternative.

    Qt/PySide6 publishes a disjunctive SPDX expression
    ("LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only") -- the licensee is free
    to choose LGPL, which is exactly this project's choice (spec.md, C-13).
    Substring-matching "GPL" alone would wrongly flag that expression; a
    license is only "GPL-only" (rejected) when it mentions GPL WITHOUT also
    offering an LGPL option.
    """
    upper = license_str.upper()
    is_lgpl = "LGPL" in upper or "LESSER GENERAL PUBLIC LICENSE" in upper
    is_gpl = "GPL" in upper or "GENERAL PUBLIC LICENSE" in upper
    return is_gpl and not is_lgpl


def test_license_gate_no_gpl_only_dependencies_pyqt6_excluded():
    """`pip-licenses` reports zero GPL-only packages; PyQt6 is not installed (C-13)."""
    result = subprocess.run(
        [PIP_LICENSES, "--format=json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, f"pip-licenses failed:\n{result.stderr}"
    packages = json.loads(result.stdout)
    assert packages, "pip-licenses produced no package data -- the check did not actually run"

    names = {pkg["Name"].lower() for pkg in packages}
    assert "pyqt6" not in names, "PyQt6 must be explicitly excluded (GPL/commercial, C-13)"

    gpl_only = [
        f"{pkg['Name']} ({pkg['License']})"
        for pkg in packages
        if _is_gpl_only(pkg["License"])
    ]
    assert not gpl_only, f"GPL-only dependency(ies) detected: {gpl_only}"


def test_is_gpl_only_classifier_distinguishes_lgpl_choice_from_pure_gpl():
    """Unit check of the classifier itself (guards against a silently-wrong gate)."""
    assert not _is_gpl_only("LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only")
    assert not _is_gpl_only("MIT")
    assert not _is_gpl_only("BSD-3-Clause")
    assert _is_gpl_only("GPL-3.0-only")
    assert _is_gpl_only("GNU General Public License v3")
