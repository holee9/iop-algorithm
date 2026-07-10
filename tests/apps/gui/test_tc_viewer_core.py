"""XDET-TC-031 -- Phase 0.5 preceding core gaps + contract preservation.

SPEC-VIEWER-001 REQ-VIEW-CORE-1~4. Verifies the additive Phase 0.5 core-gap
modules (#16 common/io.py, #15 modules/registry.py, #18
common/synth_calibset.py) without depending on any GUI-stack package
(napari/Qt) -- this file is collectible even without the `[gui]` extras
installed.

Per SPEC-VIEWER-001 v0.1.1 decision D9, GUI test sources must not contain the
Gen 1 TC id string range ("000"-"021") so the capstone scan
(tests/test_tc_skeletons.py `_GEN1_TC_RANGE`) never mis-registers a deleted
Gen 1 test as alive.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from common.calibset import CalibKind
from common.contract import ProcessModule, check_process_contract
from common.io import load_raw_frame
from common.synth_calibset import make_synthetic_calibset
from common.xframe import XFrame
from modules.registry import default_registry
from pipeline.orchestrator import CANONICAL_ORDER
from tests.fixtures.violations import WrongSignatureModule

PROJECT_ROOT = Path(__file__).resolve().parents[3]
# @MX:NOTE: [AUTO] `python -m importlinter.cli` has no __main__ guard and exits
# 0 without running any check (lesson: import-linter vacuous-pass) -- the
# console script is the only reliable entrypoint (tests/test_tc000.py precedent).
LINT_IMPORTS = str(Path(sys.executable).parent / "lint-imports")


# --- (a) common/io.py: raw + JSON -> float32 XFrame ------------------------


def test_core_raw_json_loader_produces_float32_xframe(tmp_path):
    """REQ-VIEW-CORE-1: raw 16-bit + metadata JSON yields a float32 XFrame."""
    rows, cols = 4, 5
    raw = np.arange(rows * cols, dtype=np.uint16).reshape(rows, cols)
    raw_path = tmp_path / "frame_0001.raw"
    raw_path.write_bytes(raw.tobytes())
    meta_path = tmp_path / "frame_0001.json"
    meta_path.write_text(json.dumps({"resolution": [rows, cols]}), encoding="utf-8")

    frame = load_raw_frame(raw_path)

    assert isinstance(frame, XFrame)
    assert frame.pixel.dtype == np.float32
    assert frame.shape == (rows, cols)
    # C-04 lossless: every uint16 value is exactly representable as float32.
    assert np.array_equal(frame.pixel, raw.astype(np.float32))


def test_core_raw_json_loader_accepts_explicit_meta_path(tmp_path):
    """An explicit meta_path overrides the default `<name>.json` sidecar lookup."""
    rows, cols = 2, 3
    raw = np.arange(rows * cols, dtype=np.uint16).reshape(rows, cols)
    raw_path = tmp_path / "odd_name.dat"
    raw_path.write_bytes(raw.tobytes())
    meta_path = tmp_path / "sidecar.json"
    meta_path.write_text(json.dumps({"resolution": [rows, cols]}), encoding="utf-8")

    frame = load_raw_frame(raw_path, meta_path)

    assert frame.shape == (rows, cols)


def test_core_raw_json_loader_rejects_resolution_mismatch(tmp_path):
    """A raw payload whose element count disagrees with metadata is an explicit error."""
    raw_path = tmp_path / "bad.raw"
    raw_path.write_bytes(np.zeros(6, dtype=np.uint16).tobytes())
    meta_path = tmp_path / "bad.json"
    meta_path.write_text(json.dumps({"resolution": [4, 4]}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_raw_frame(raw_path)


# --- (b) modules/registry.py: default_registry() ---------------------------


def test_core_default_registry_returns_nonempty_module_set():
    """REQ-VIEW-CORE-2: the registry returns a non-empty name -> ProcessModule set."""
    registry = default_registry()

    assert registry, "default_registry() must not be empty"
    for name, module in registry.items():
        assert isinstance(name, str) and name
        assert isinstance(module, ProcessModule), f"{name}: not a ProcessModule"


def test_core_default_registry_stage_names_are_canonical():
    """Every registered stage name is a real CANONICAL_ORDER stage (no invented stages)."""
    registry = default_registry()

    assert set(registry).issubset(set(CANONICAL_ORDER))


# --- (c) common/synth_calibset.py: synthetic CalibSet factory --------------


def test_core_synthetic_calibset_factory_produces_valid_calibset():
    """REQ-VIEW-CORE-3: the synthetic factory substitutes for a missing measured CalibSet."""
    calib = make_synthetic_calibset((32, 32), CalibKind.OFFSET)

    calib.validate()  # raises CalibSchemaError on any violation
    assert calib.matches_resolution((32, 32))
    assert calib.kind is CalibKind.OFFSET


@pytest.mark.parametrize("kind", list(CalibKind))
def test_core_synthetic_calibset_factory_covers_every_kind(kind):
    """The factory is generic over CalibKind, not hardcoded to one stage."""
    calib = make_synthetic_calibset((8, 8), kind)
    calib.validate()


# --- (d) REQ-VIEW-CORE-4: additive-only, core contracts unchanged ---------


def test_core_process_contract_check_still_functions():
    """check_process_contract still passes real modules and flags wrong signatures.

    Ties the #15 registry values directly to the still-live contract checker:
    a real registered module produces zero violations, while the existing
    negative-control fixture is still detected -- proving the SWR-000-7
    `process(frame, calib, params) -> XFrame` contract enforcement is
    unmodified by the additive Phase 0.5 changes.
    """
    registry = default_registry()
    assert check_process_contract(registry["offset"]) == ()
    assert check_process_contract(WrongSignatureModule())


def test_core_canonical_order_unchanged():
    """pipeline.orchestrator.CANONICAL_ORDER is untouched by the Phase 0.5 additions."""
    assert CANONICAL_ORDER == (
        "offset",
        "gain",
        "defect",
        "lag",
        "line_noise",
        "saturation",
        "geometry",
        "grid",
        "virtual_grid",
        "denoise",
        "mse",
        "window",
        "post",
    )


def test_core_import_linter_contract_still_passes():
    """The existing import-linter contract (KEPT) still passes after the additive changes."""
    result = subprocess.run(
        [LINT_IMPORTS],
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    # Guard against the vacuous-pass failure mode: the tool must produce output.
    assert result.stdout.strip() or result.stderr.strip(), (
        "lint-imports produced no output -- the check did not actually run"
    )
    assert result.returncode == 0, (
        f"lint-imports failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
