"""Orchestrator integration for the mse/window post-processing stages.

Covers acceptance Scenario 14 (dedicated stages between denoise and post,
CalibSet(OTHER) entry gate) and the full-chain composition through the new
stages (REQ-POST-CONTRACT-5, decision 1/2).
"""

from __future__ import annotations

import numpy as np
import pytest

from common.contract import Params
from modules import mse, window
from pipeline.orchestrator import (
    CANONICAL_ORDER,
    CalibrationError,
    PipelineDefinition,
    PipelineOrderError,
    run_pipeline,
)
from tests.modules.phantoms.post_syn import (
    make_bone_soft_phantom,
    make_noise_frame,
    mse_params,
    other_calib,
    window_params,
)


def test_canonical_order_places_mse_window_between_denoise_and_post():
    order = list(CANONICAL_ORDER)
    assert order.index("denoise") < order.index("mse") < order.index("window")
    assert order.index("window") < order.index("post")


def test_mse_window_are_registrable_subsequence():
    # A subsequence of CANONICAL_ORDER is accepted (backward-compatible insertion).
    definition = PipelineDefinition(("mse", "window"))
    assert definition.stages == ("mse", "window")


def test_reordered_window_before_mse_rejected():
    with pytest.raises(PipelineOrderError):
        PipelineDefinition(("window", "mse"))


def test_full_chain_runs_through_mse_and_window():
    _, noisy = make_bone_soft_phantom(shape=(64, 64), detail_amp=200.0)
    frame = make_noise_frame(noisy)
    definition = PipelineDefinition(("mse", "window"))
    registry = {"mse": mse.process, "window": window.process}
    calib_map = {"mse": other_calib((64, 64)), "window": other_calib((64, 64))}
    params_map = {"mse": mse_params(), "window": window_params(window_region_code="CHEST")}

    out = run_pipeline(frame, definition, registry, calib_map, params_map)

    # Two history entries appended in canonical order (mse then window).
    names = [h.module_name for h in out.history]
    assert names[-2:] == ["mse", "window"]
    assert np.all(np.isfinite(np.asarray(out.pixel)))


def test_entry_gate_refuses_missing_calibset_for_post_stage():
    _, noisy = make_bone_soft_phantom(shape=(64, 64))
    frame = make_noise_frame(noisy)
    definition = PipelineDefinition(("mse", "window"))
    registry = {"mse": mse.process, "window": window.process}
    # window CalibSet omitted -> entry gate refuses before any processing.
    calib_map = {"mse": other_calib((64, 64))}
    with pytest.raises(CalibrationError):
        run_pipeline(frame, definition, registry, calib_map, {"mse": mse_params()})


def test_entry_gate_refuses_resolution_mismatch():
    _, noisy = make_bone_soft_phantom(shape=(64, 64))
    frame = make_noise_frame(noisy)
    definition = PipelineDefinition(("mse",))
    registry = {"mse": mse.process}
    calib_map = {"mse": other_calib((32, 32))}  # wrong resolution
    with pytest.raises(CalibrationError):
        run_pipeline(frame, definition, registry, calib_map, {"mse": mse_params()})
