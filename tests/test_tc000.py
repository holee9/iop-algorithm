"""XDET-TC-000 — the T0 framework self-test (DoD).

Three decision engines (plan.md section 7):
- A (harness):   passthrough fixture output matches expected XFrame.
- B (static):    import-linter dependency-direction check passes on the tree.
- C (contract):  signature / return-contract violations are detected.

DoD: all three pass with zero contract violations -> XDET-TC-000 PASS.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from common.contract import Params, check_process_contract, run_harness
from tests.fixtures import passthrough
from tests.fixtures.violations import ExtraReturnModule, WrongSignatureModule

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# @MX:NOTE: [AUTO] `python -m importlinter.cli` has no __main__ guard and exits 0
# without running any check — the console script is the only reliable entrypoint.
LINT_IMPORTS = str(Path(sys.executable).parent / "lint-imports")


def _run_lint_imports(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [LINT_IMPORTS, *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    # Guard against the vacuous-pass failure mode: the tool must produce output.
    assert result.stdout.strip() or result.stderr.strip(), (
        "lint-imports produced no output — the check did not actually run"
    )
    return result


# --- Decision engine A: harness fixture comparison ------------------------


def test_tc000_A_passthrough_harness_passes(synthetic_frame, calib, params):
    """Scenario 1: identity module output equals expected XFrame (all fields)."""
    expected = passthrough.expected_output(synthetic_frame, calib, params)
    report = run_harness(passthrough, synthetic_frame, calib, params, expected)
    assert report.passed, report.violations
    # History chain gained a deterministic entry with module/version/hash/calib.
    result = passthrough.process(synthetic_frame, calib, params)
    assert len(result.history) == 1
    entry = result.history[0]
    assert entry.module_name == "reference_passthrough"
    assert entry.params_hash == params.hash()
    assert entry.calibset_id == calib.calibset_id


def test_tc000_A_input_frame_unchanged(synthetic_frame, calib, params):
    """DATA-6: the input frame is not mutated by processing."""
    before_pixel = synthetic_frame.pixel.copy()
    before_history = synthetic_frame.history
    passthrough.process(synthetic_frame, calib, params)
    assert (synthetic_frame.pixel == before_pixel).all()
    assert synthetic_frame.history == before_history  # still empty tuple


# --- Decision engine B: import-linter static check ------------------------


def test_tc000_B_import_linter_passes():
    """Scenario 3: the real project satisfies the layering contract."""
    result = _run_lint_imports()
    assert result.returncode == 0, (
        f"lint-imports failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_tc000_B_import_linter_detects_violation():
    """EC-5: an upward import is DETECTED and fails the check."""
    ini = textwrap.dedent(
        """
        [importlinter]
        root_package = tests

        [importlinter:contract:1]
        name = badlayers must be downward-only
        type = layers
        layers =
            tests.fixtures.badlayers.high
            tests.fixtures.badlayers.low
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
            "import-linter should have detected the upward import violation:\n"
            f"{result.stdout}\n{result.stderr}"
        )
    finally:
        cfg_path.unlink(missing_ok=True)


# --- Decision engine C: contract signature / return check -----------------


def test_tc000_C_wrong_signature_detected(synthetic_frame, calib, params):
    """EC-3: a wrong-signature module is flagged as a contract violation."""
    violations = check_process_contract(WrongSignatureModule())
    assert violations, "wrong signature must be detected"


def test_tc000_C_extra_return_value_detected(synthetic_frame, calib, params):
    """EC-4: an extra return value is detected as a FAIL by the harness."""
    module = ExtraReturnModule()
    expected = passthrough.expected_output(synthetic_frame, calib, params)
    report = run_harness(module, synthetic_frame, calib, params, expected)
    assert not report.passed
    assert any("must return XFrame" in v for v in report.violations)
