"""Equivalence diff frame: CI-4 hook reuse, path classification, +/- controls.

Covers acceptance Scenario 4 (positive equivalence + path classification), Scenario
5 / EC-2 (perturbation negative control) and REQ-TIER-EQUIV-1..4 / CONTRACT-5. The
frame REUSES the T0 ``common/equivalence.diff_frames`` hook (SWR-000-9) — it does
not reimplement a frame diff. Numeric tolerances (bit-identical / +/-1 LSB) are NOT
asserted here (P2, EV-402); only the structural judgment is.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.equivalence import (
    INTEGER_PATH_STAGES,
    EquivalenceDiff,
    PathClass,
    PathEquivalence,
    classify_path,
    compare_paths,
    diff_frames,
)
from common.xframe import new_frame
from pipeline.orchestrator import run_pipeline
from tests.pipeline.frame_fixtures import (
    FLOAT_DEF,
    INT_DEF,
    calib_map_for,
    passthrough_registry,
    perturb,
    std_frame,
)


def _run_twice(definition):
    """Produce two outputs of the same golden model over the same input."""
    frame = std_frame()
    registry = passthrough_registry(definition)
    calib = calib_map_for(definition)
    a = run_pipeline(frame, definition, registry, calib)
    b = run_pipeline(frame, definition, registry, calib)
    return a, b


# -- Scenario 4: positive equivalence + diff_frames reuse + path classification --


def test_scenario4_identical_outputs_structurally_equal():
    a, b = _run_twice(INT_DEF)
    diff = diff_frames(a, b)
    assert diff.structurally_equal is True
    assert diff.max_pixel_abs_diff == 0.0


def test_scenario4_compare_paths_reuses_diff_frames_and_classifies():
    a, b = _run_twice(INT_DEF)
    result = compare_paths(a, b, INT_DEF.stages)
    assert isinstance(result, PathEquivalence)
    # Reuse (not reimplementation): identical to the T0 hook (CONTRACT-5 / EQUIV-1).
    assert result.diff == diff_frames(a, b)
    assert isinstance(result.diff, EquivalenceDiff)
    assert result.structurally_equal is True
    assert result.max_pixel_abs_diff == 0.0
    # Integer path -> bit-identical target label (P2 gate-type marker).
    assert result.path is PathClass.INTEGER


# -- REQ-TIER-EQUIV-2: integer / float path classification --------------------


def test_integer_and_float_paths_classified():
    assert classify_path(INT_DEF.stages) is PathClass.INTEGER
    assert classify_path(FLOAT_DEF.stages) is PathClass.FLOAT
    # A single non-integer-path stage taints the comparison to the +/-1 LSB path.
    assert classify_path(("geometry",)) is PathClass.FLOAT
    assert classify_path(("offset",)) is PathClass.INTEGER
    assert classify_path(("offset", "gain", "defect", "line_noise")) is PathClass.INTEGER


def test_integer_path_stage_set_matches_swr_1302():
    assert INTEGER_PATH_STAGES == frozenset(
        {"offset", "gain", "defect", "line_noise"}
    )


def test_classify_path_empty_is_error():
    with pytest.raises(ValueError):
        classify_path(())


# -- Scenario 5 / EC-2: perturbation negative control (not vacuously equal) ----


def test_scenario5_perturbation_detected_negative_control():
    frame = std_frame()
    registry = passthrough_registry(INT_DEF)
    calib = calib_map_for(INT_DEF)
    a = run_pipeline(frame, INT_DEF, registry, calib)
    b = run_pipeline(perturb(frame, delta=5.0), INT_DEF, registry, calib)
    diff = diff_frames(a, b)
    assert diff.structurally_equal is False
    assert diff.max_pixel_abs_diff > 0.0


def test_ec2_perturbation_via_compare_paths_not_vacuous():
    frame = std_frame()
    registry = passthrough_registry(INT_DEF)
    calib = calib_map_for(INT_DEF)
    a = run_pipeline(frame, INT_DEF, registry, calib)
    b = run_pipeline(perturb(frame), INT_DEF, registry, calib)
    result = compare_paths(a, b, INT_DEF.stages)
    assert result.structurally_equal is False
    assert result.max_pixel_abs_diff > 0.0
    # Classification is a structural property, independent of the equality outcome.
    assert result.path is PathClass.INTEGER


def test_mask_perturbation_detected():
    frame = std_frame()
    masks = np.array(frame.masks, copy=True)
    masks[0, 0] = 1
    b = new_frame(np.array(frame.pixel, copy=True), masks, frame.noise)
    diff = diff_frames(frame, b)
    assert diff.masks_equal is False
    assert diff.structurally_equal is False
