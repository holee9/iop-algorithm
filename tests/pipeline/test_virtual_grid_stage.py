"""Orchestrator integration for the dedicated `virtual_grid` stage (SPEC-VGRID-001).

Covers acceptance Scenario 7/10 (decisions 1 & 2): the virtual_grid stage sits
between grid and denoise in CANONICAL_ORDER, registered stages are a subsequence
(backward-compatible insertion), and the entry gate enforces
_KIND_BY_STAGE["virtual_grid"] == "scatter" (CalibSet(SCATTER) required; the T7
grid CalibSet(OTHER) is refused).
"""

from __future__ import annotations

import numpy as np
import pytest

from modules import virtual_grid
from pipeline.orchestrator import (
    CANONICAL_ORDER,
    CalibrationError,
    PipelineDefinition,
    PipelineOrderError,
    run_pipeline,
)
from tests.modules.phantoms.scatter_syn import (
    make_frame,
    make_smooth_scatter_phantom,
    other_calib,
    scatter_calib,
    vgrid_params,
)

SHAPE = (96, 96)


def test_canonical_order_places_virtual_grid_between_grid_and_denoise():
    order = list(CANONICAL_ORDER)
    assert order.index("grid") < order.index("virtual_grid") < order.index("denoise")


def test_virtual_grid_is_registrable_subsequence():
    definition = PipelineDefinition(("grid", "virtual_grid", "denoise"))
    assert definition.stages == ("grid", "virtual_grid", "denoise")


def test_reordered_virtual_grid_before_grid_rejected():
    with pytest.raises(PipelineOrderError):
        PipelineDefinition(("virtual_grid", "grid"))


def test_virtual_grid_stage_runs_in_pipeline():
    frame = make_frame(make_smooth_scatter_phantom(SHAPE)[1])
    definition = PipelineDefinition(("virtual_grid",))
    registry = {"virtual_grid": virtual_grid.process}
    calib_map = {"virtual_grid": scatter_calib(SHAPE)}
    params_map = {"virtual_grid": vgrid_params()}
    out = run_pipeline(frame, definition, registry, calib_map, params_map)
    assert out.history[-1].module_name == "virtual_grid"
    assert np.all(np.isfinite(np.asarray(out.pixel)))


def test_entry_gate_refuses_missing_calibset():
    frame = make_frame(make_smooth_scatter_phantom(SHAPE)[1])
    definition = PipelineDefinition(("virtual_grid",))
    registry = {"virtual_grid": virtual_grid.process}
    with pytest.raises(CalibrationError):
        run_pipeline(frame, definition, registry, {}, {"virtual_grid": vgrid_params()})


def test_entry_gate_refuses_wrong_kind_other_not_scatter():
    """Scenario 7: CalibSet(OTHER) (the T7 grid placeholder) is refused — the gate
    enforces kind == scatter for virtual_grid."""
    frame = make_frame(make_smooth_scatter_phantom(SHAPE)[1])
    definition = PipelineDefinition(("virtual_grid",))
    registry = {"virtual_grid": virtual_grid.process}
    calib_map = {"virtual_grid": other_calib(SHAPE)}
    with pytest.raises(CalibrationError, match="kind"):
        run_pipeline(frame, definition, registry, calib_map, {"virtual_grid": vgrid_params()})


def test_entry_gate_refuses_resolution_mismatch():
    frame = make_frame(make_smooth_scatter_phantom(SHAPE)[1])
    definition = PipelineDefinition(("virtual_grid",))
    registry = {"virtual_grid": virtual_grid.process}
    calib_map = {"virtual_grid": scatter_calib((32, 32))}
    with pytest.raises(CalibrationError):
        run_pipeline(frame, definition, registry, calib_map, {"virtual_grid": vgrid_params()})
