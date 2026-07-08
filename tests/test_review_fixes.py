"""Regression tests for the 10 defects found by the independent code review
of commit 64137f3 (SPEC-INFRA-001 T0 scaffold). One test (or pair) per finding.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, CalibSet
from common.contract import Params, check_process_contract
from common.xframe import XFrame, hash_params, new_frame
from pipeline.orchestrator import (
    CalibrationError,
    PipelineDefinition,
    run_pipeline,
)


def _calib(panel_id="P1", kind=CalibKind.OFFSET, res=(4, 4),
           valid_from="2026-01-01", valid_until="2027-01-01"):
    return CalibSet(
        panel_id=panel_id,
        resolution=res,
        valid_from=valid_from,
        valid_until=valid_until,
        kind=kind,
        data={"map": np.zeros(res, dtype=np.float32)},
    )


def _identity(frame, calib, params):
    return frame


# -- [1] calibration gate: panel_id / validity / kind ------------------------


def test_gate_rejects_panel_id_mismatch():
    frame = new_frame(np.zeros((4, 4), dtype=np.float32))
    calib_map = {"offset": _calib(panel_id="P1"), "gain": _calib(panel_id="P2", kind=CalibKind.GAIN)}
    definition = PipelineDefinition(stages=("offset", "gain"))
    with pytest.raises(CalibrationError, match="panel_id"):
        run_pipeline(frame, definition, {"offset": _identity, "gain": _identity}, calib_map)


def test_gate_rejects_expected_panel_id_mismatch():
    frame = new_frame(np.zeros((4, 4), dtype=np.float32))
    calib_map = {"offset": _calib(panel_id="P1")}
    definition = PipelineDefinition(stages=("offset",))
    with pytest.raises(CalibrationError, match="panel_id"):
        run_pipeline(frame, definition, {"offset": _identity}, calib_map,
                     panel_id="P2")


def test_gate_rejects_expired_calibration():
    frame = new_frame(np.zeros((4, 4), dtype=np.float32))
    calib_map = {"offset": _calib(valid_until="2026-06-01")}
    definition = PipelineDefinition(stages=("offset",))
    with pytest.raises(CalibrationError, match="validity"):
        run_pipeline(frame, definition, {"offset": _identity}, calib_map,
                     timestamp="2026-07-09")


def test_gate_rejects_kind_mismatch():
    frame = new_frame(np.zeros((4, 4), dtype=np.float32))
    calib_map = {"offset": _calib(kind=CalibKind.GAIN)}
    definition = PipelineDefinition(stages=("offset",))
    with pytest.raises(CalibrationError, match="kind"):
        run_pipeline(frame, definition, {"offset": _identity}, calib_map)


# -- [2] CalibSet save/load must not truncate dotted basenames ---------------


def test_calibset_save_load_dotted_basename(tmp_path):
    calib = _calib()
    npz_path, json_path = calib.save(tmp_path / "gain_v1.0")
    assert npz_path.name == "gain_v1.0.npz"
    assert json_path.name == "gain_v1.0.json"
    loaded = CalibSet.load(tmp_path / "gain_v1.0")
    assert loaded.panel_id == calib.panel_id
    # A sibling version must NOT collide with v1.0's files.
    with pytest.raises(FileNotFoundError):
        CalibSet.load(tmp_path / "gain_v1.1")


# -- [3] with_pixel must not silently keep a stale float64 buffer ------------


def test_with_pixel_rejects_stale_f64():
    frame = new_frame(np.ones((4, 4), dtype=np.float32), validation_mode=True)
    assert frame.pixel_f64 is not None
    with pytest.raises(ValueError, match="pixel_f64"):
        frame.with_pixel(np.zeros((4, 4), dtype=np.float32))
    # Explicit f64 update is the correct call and must succeed.
    out = frame.with_pixel(
        np.zeros((4, 4), dtype=np.float32),
        pixel_f64=np.zeros((4, 4), dtype=np.float64),
    )
    assert (out.pixel_f64 == 0).all()


# -- [4] params hash must be injective for large ndarrays --------------------


def test_hash_params_distinguishes_large_arrays():
    a = np.zeros(5000, dtype=np.float64)
    b = a.copy()
    b[2500] = 1e-9  # deep inside numpy's str() truncation region
    assert hash_params({"kernel": a}) != hash_params({"kernel": b})


# -- [5] signature contract must check names, not just count -----------------


def test_contract_rejects_wrong_param_names():
    class Renamed:
        def process(self, image, cal, cfg):
            return image

    assert check_process_contract(Renamed())


# -- [6] equals must cover validation_mode ------------------------------------


def test_equals_detects_validation_mode_drop():
    f1 = new_frame(np.ones((4, 4), dtype=np.float32), validation_mode=True)
    f2 = XFrame(
        pixel=f1.pixel, masks=f1.masks, noise=f1.noise, history=f1.history,
        pixel_f64=f1.pixel_f64, validation_mode=False,
    )
    assert not f1.equals(f2)


# -- [7] CalibSet.data must be immutable --------------------------------------


def test_calibset_data_readonly():
    calib = _calib()
    with pytest.raises((ValueError, TypeError)):
        calib.data["map"][0, 0] = 1.0


# -- [8] Params must not alias the caller's mutable dict ----------------------


def test_params_frozen_against_caller_mutation():
    src = {"a": 1}
    p = Params(values=src)
    src["a"] = 2
    assert p.get("a") == 1
    with pytest.raises(TypeError):
        p.values["a"] = 3  # type: ignore[index]


# -- [9] NaN-aware pixel equality ---------------------------------------------


def test_equals_nan_pixels_are_equal():
    pix = np.ones((4, 4), dtype=np.float32)
    pix[0, 0] = np.nan
    f1 = new_frame(pix)
    f2 = new_frame(pix.copy())
    assert f1.equals(f2)


# -- [10] metadata-only replace must not copy locked buffers ------------------


def test_record_history_shares_readonly_buffers():
    frame = new_frame(np.ones((16, 16), dtype=np.float32))
    from common.xframe import HistoryEntry

    out = frame.record_history(
        HistoryEntry("m", "1", "h", None)
    )
    assert out.pixel is frame.pixel  # already read-only: shared, not copied
    assert out.masks is frame.masks
