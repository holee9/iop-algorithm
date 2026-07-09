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
    # The gate requires kind to match the stage it is wired to; stages with no
    # dedicated CalibKind (saturation/geometry/post) use OTHER. The denoise stage
    # is wired to CalibKind.NOISE (value "noise"), whose value differs from the
    # stage name, so it is mapped explicitly (SPEC-DENOISE-001 decision 2/5).
    if stage == "denoise":
        kind = CalibKind.NOISE
    elif stage == "virtual_grid":
        # virtual_grid is wired to CalibKind.SCATTER (value "scatter"), whose
        # value differs from the stage name (SPEC-VGRID-001 decision 2).
        kind = CalibKind.SCATTER
    else:
        try:
            kind = CalibKind(stage)
        except ValueError:
            kind = CalibKind.OTHER
    return CalibSet(
        panel_id="PANEL-A",
        resolution=FRAME_SHAPE,
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=kind,
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


def test_full_definition_covers_all_canonical_stages():
    """Defect 2: full() means 'full' — it returns ALL canonical stages in order,
    including the denoise stage. Callers must supply complete calib/params."""
    assert PipelineDefinition.full().stages == CANONICAL_ORDER


def test_full_run_missing_denoise_calib_errors_at_gate(frame):
    """Defect 2: a full() run with the real denoise module but no CalibSet(NOISE)
    fails LOUDLY at the entry gate BEFORE any frame is processed."""
    from modules import denoise

    definition = PipelineDefinition.full()
    registry = {s: _stage_module(s) for s in CANONICAL_ORDER}
    registry["denoise"] = denoise.process
    calib_map = {s: _calib_for(s) for s in CANONICAL_ORDER}
    del calib_map["denoise"]  # missing noise calibration
    with pytest.raises(CalibrationError, match="denoise"):
        run_pipeline(frame, definition, registry, calib_map)


def test_full_run_missing_denoise_params_errors_before_processing(frame):
    """Defect 2: with calib present but the denoise Params bundle absent, the
    denoise stage raises an explicit named DenoiseError at entry (fail fast)."""
    from modules import denoise
    from tests.modules.phantoms.denoise_syn import noise_calib

    definition = PipelineDefinition.full()
    registry = {s: _stage_module(s) for s in CANONICAL_ORDER}
    registry["denoise"] = denoise.process
    calib_map = {s: _calib_for(s) for s in CANONICAL_ORDER}
    calib_map["denoise"] = noise_calib(FRAME_SHAPE)  # valid (alpha,sigma) payload
    # No params_map -> denoise stage gets empty Params -> named missing-param error.
    with pytest.raises(denoise.DenoiseError, match="missing required parameter"):
        run_pipeline(frame, definition, registry, calib_map)


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
