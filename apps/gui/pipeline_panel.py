"""Pipeline comparison viewer (REQ-VIEW-RUN-2, C-16): partial/full CANONICAL_ORDER runs.

@MX:ANCHOR: [AUTO] `run_partial_pipeline` is the sole producer of the
stage-by-stage before/after XFrame pairs that REQ-VIEW-COMPARE layers
(C-05/06/07, `apps.gui.layers`) display for the Phase 2 pipeline view.
@MX:REASON: REQ-VIEW-CORE-4 forbids adding a new core hook for per-stage
capture; this function derives before/after pairs entirely from
`run_pipeline`'s existing `validation_mode` intermediate-preservation path
(`pipeline/orchestrator.py`) rather than modifying the orchestrator.

Registry adapter note: `modules.registry.default_registry()` returns stage ->
ProcessModule (module OBJECTS, e.g. the `modules.offset` module itself) --
suited for direct `.process(...)` calls (Phase 1's `module_panel.py`) and
`run_harness(module, ...)`. `run_pipeline` instead calls `registry[stage](frame,
calib, params)` DIRECTLY, so a module object (not callable) would raise
`TypeError`. `build_pipeline_registry()` is the adapter that extracts each
module's bound `.process` callable.
"""

from __future__ import annotations

from dataclasses import dataclass

from common.calibset import CalibKind, CalibSet
from common.contract import Params
from common.synth_calibset import make_synthetic_calibset
from common.xframe import XFrame, new_frame
from modules.registry import default_registry
from pipeline.orchestrator import (
    CANONICAL_ORDER,
    ProcessCallable,
    PipelineDefinition,
    _KIND_BY_STAGE,
    run_pipeline,
)

# "post" is a reserved CANONICAL_ORDER tail with no registered module
# (modules/registry.py excludes it) -- the pipeline viewer can only select
# stages that have a real ProcessCallable behind them.
SELECTABLE_STAGES: tuple[str, ...] = tuple(
    s for s in CANONICAL_ORDER if s in default_registry()
)


def build_pipeline_registry() -> dict[str, ProcessCallable]:
    """Adapt `default_registry()` (module objects) to a bare stage->callable map."""
    return {name: module.process for name, module in default_registry().items()}


def build_synthetic_calib_map(
    definition: PipelineDefinition, resolution: tuple[int, int]
) -> dict[str, CalibSet]:
    """Synthetic CalibSet per stage (REQ-VIEW-CORE-3), kind-matched via `_KIND_BY_STAGE`.

    Mirrors `tests/pipeline/frame_fixtures.py::calib_map_for` -- stages absent
    from `_KIND_BY_STAGE` (no detector calibration) get `CalibKind.OTHER`.
    """
    return {
        stage: make_synthetic_calibset(
            resolution, CalibKind(_KIND_BY_STAGE.get(stage, "other"))
        )
        for stage in definition.stages
    }


@dataclass(frozen=True)
class StageComparison:
    """One stage's before/after XFrame pair (REQ-VIEW-RUN-2 display unit)."""

    stage: str
    before: XFrame
    after: XFrame


@dataclass(frozen=True)
class PipelineRunResult:
    """Full pipeline execution result: final frame + per-stage before/after pairs."""

    final_frame: XFrame
    stage_comparisons: tuple[StageComparison, ...]


def _as_validation_mode(frame: XFrame) -> XFrame:
    """Return `frame` guaranteed to carry the validation-mode float64 buffer.

    `run_pipeline` only appends each stage's output to `XFrame.intermediates`
    when the INPUT frame has `validation_mode=True` (`pipeline/orchestrator.py`
    "if frame.validation_mode: preserved = preserved + (current,)"); this is the
    sole mechanism REQ-VIEW-RUN-2's stage-by-stage before/after view relies on
    -- no new core hook is added (REQ-VIEW-CORE-4 additive-only constraint).
    """
    if frame.validation_mode:
        return frame
    return new_frame(frame.pixel, frame.masks, frame.noise, validation_mode=True)


def run_partial_pipeline(
    input_frame: XFrame,
    stages: tuple[str, ...],
    params_map: dict[str, Params] | None = None,
    *,
    registry: dict[str, ProcessCallable] | None = None,
    calib_map: dict[str, CalibSet] | None = None,
) -> PipelineRunResult:
    """Execute `stages` (a `CANONICAL_ORDER` subsequence, partial or full) via
    `run_pipeline` and derive stage-by-stage before/after pairs (REQ-VIEW-RUN-2).

    `registry`/`calib_map` default to the GUI's own synthetic substitutes
    (`build_pipeline_registry`/`build_synthetic_calib_map`) but may be
    overridden by a caller with real calibration (REQ-VIEW-CORE-3 substitution
    is "when absent", not "always").
    """
    definition = PipelineDefinition(tuple(stages))
    reg = registry if registry is not None else build_pipeline_registry()
    calibs = (
        calib_map
        if calib_map is not None
        else build_synthetic_calib_map(definition, input_frame.shape)
    )
    vframe = _as_validation_mode(input_frame)
    result = run_pipeline(vframe, definition, reg, calibs, params_map)

    comparisons: list[StageComparison] = []
    prior = vframe
    for stage, after in zip(definition.stages, result.intermediates):
        comparisons.append(StageComparison(stage=stage, before=prior, after=after))
        prior = after
    return PipelineRunResult(final_frame=result, stage_comparisons=tuple(comparisons))
