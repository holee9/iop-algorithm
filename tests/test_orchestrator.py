"""Orchestrator tests: fixed order + CalibSet entry gate (REQ-INFRA-ORCH)."""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, CalibSet
from common.contract import Params
from common.xframe import HistoryEntry, new_frame
from pipeline.orchestrator import (
    CANONICAL_ORDER,
    CalibrationError,
    PipelineDefinition,
    PipelineOrderError,
    run_pipeline,
)
from tests.fixtures import passthrough

FRAME_SHAPE = (4, 4)


def _calib_for(stage: str) -> CalibSet:
    return CalibSet(
        panel_id="PANEL-A",
        resolution=FRAME_SHAPE,
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=CalibKind.OTHER,
        data={},
    )


def _stage_module(tag: str):
    """Build a passthrough-style callable that tags the history with `tag`."""

    def process(frame, calib, params):
        return frame.record_history(
            HistoryEntry(tag, "1.0.0", params.hash(), calib.calibset_id)
        )

    return process


@pytest.fixture
def frame():
    return new_frame(np.arange(16, dtype=np.float32).reshape(FRAME_SHAPE))


def test_definition_enforces_canonical_order():
    with pytest.raises(PipelineOrderError):
        PipelineDefinition(stages=("gain", "offset"))  # reversed -> reject


def test_definition_rejects_unknown_stage():
    with pytest.raises(PipelineOrderError):
        PipelineDefinition(stages=("offset", "sharpen"))


def test_pipeline_runs_in_fixed_order(frame):
    """Scenario 2: modules run in canonical order via the orchestrator only."""
    definition = PipelineDefinition.full()
    registry = {s: _stage_module(s) for s in CANONICAL_ORDER}
    calib_map = {s: _calib_for(s) for s in CANONICAL_ORDER}
    out = run_pipeline(frame, definition, registry, calib_map)
    executed = [e.module_name for e in out.history]
    assert executed == list(CANONICAL_ORDER)


def test_input_frame_preserved_across_pipeline(frame):
    definition = PipelineDefinition(stages=("offset", "gain"))
    registry = {"offset": passthrough.process, "gain": passthrough.process}
    calib_map = {"offset": _calib_for("offset"), "gain": _calib_for("gain")}
    run_pipeline(frame, definition, registry, calib_map)
    assert frame.history == ()  # original untouched (DATA-6)


def test_missing_calibset_refused(frame):
    """EC-1: missing CalibSet -> explicit refusal, no default substitution."""
    definition = PipelineDefinition(stages=("offset",))
    registry = {"offset": passthrough.process}
    with pytest.raises(CalibrationError, match="missing"):
        run_pipeline(frame, definition, registry, calib_map={})


def test_mismatched_resolution_refused(frame):
    """EC-2: resolution mismatch -> explicit refusal naming the mismatch."""
    definition = PipelineDefinition(stages=("offset",))
    registry = {"offset": passthrough.process}
    bad = CalibSet(
        panel_id="PANEL-A",
        resolution=(8, 8),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=CalibKind.OTHER,
        data={},
    )
    with pytest.raises(CalibrationError, match="resolution"):
        run_pipeline(frame, definition, registry, {"offset": bad})


def test_validation_mode_preserves_intermediates():
    """DATA-5: validation mode preserves per-stage intermediate frames."""
    vframe = new_frame(
        np.arange(16, dtype=np.float32).reshape(FRAME_SHAPE), validation_mode=True
    )
    definition = PipelineDefinition(stages=("offset", "gain", "defect"))
    registry = {s: _stage_module(s) for s in ("offset", "gain", "defect")}
    calib_map = {s: _calib_for(s) for s in ("offset", "gain", "defect")}
    out = run_pipeline(vframe, definition, registry, calib_map)
    assert len(out.intermediates) == 3
