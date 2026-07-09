"""Orchestrator integration for the dedicated `grid` stage (SPEC-GRID-001).

Covers acceptance Scenario 10 (decision 1): the grid stage sits between geometry
and denoise in CANONICAL_ORDER, registered stages are a subsequence
(backward-compatible insertion), and CalibSet(OTHER) satisfies the entry gate
(grid has no detector calibration; not wired in _KIND_BY_STAGE).
"""

from __future__ import annotations

import numpy as np
import pytest

from modules import grid
from pipeline.orchestrator import (
    CANONICAL_ORDER,
    CalibrationError,
    PipelineDefinition,
    PipelineOrderError,
    run_pipeline,
)
from tests.modules.phantoms.grid_syn import (
    F_GRID_BELOW,
    grid_params,
    make_frame,
    make_grid_phantom,
    other_calib,
)


def test_canonical_order_places_grid_between_geometry_and_denoise():
    order = list(CANONICAL_ORDER)
    assert order.index("geometry") < order.index("grid") < order.index("denoise")


def test_grid_is_registrable_subsequence():
    definition = PipelineDefinition(("geometry", "grid", "denoise"))
    assert definition.stages == ("geometry", "grid", "denoise")


def test_reordered_grid_before_geometry_rejected():
    with pytest.raises(PipelineOrderError):
        PipelineDefinition(("grid", "geometry"))


def test_grid_stage_runs_in_pipeline():
    _, img = make_grid_phantom((96, 96), F_GRID_BELOW, direction="vertical")
    frame = make_frame(img)
    definition = PipelineDefinition(("grid",))
    registry = {"grid": grid.process}
    calib_map = {"grid": other_calib((96, 96))}
    params_map = {"grid": grid_params()}
    out = run_pipeline(frame, definition, registry, calib_map, params_map)
    assert out.history[-1].module_name == "grid"
    assert np.all(np.isfinite(np.asarray(out.pixel)))


def test_entry_gate_refuses_missing_calibset_for_grid():
    _, img = make_grid_phantom((96, 96), F_GRID_BELOW)
    frame = make_frame(img)
    definition = PipelineDefinition(("grid",))
    registry = {"grid": grid.process}
    with pytest.raises(CalibrationError):
        run_pipeline(frame, definition, registry, {}, {"grid": grid_params()})


def test_entry_gate_refuses_resolution_mismatch():
    _, img = make_grid_phantom((96, 96), F_GRID_BELOW)
    frame = make_frame(img)
    definition = PipelineDefinition(("grid",))
    registry = {"grid": grid.process}
    calib_map = {"grid": other_calib((32, 32))}
    with pytest.raises(CalibrationError):
        run_pipeline(frame, definition, registry, calib_map, {"grid": grid_params()})
