"""Pipeline orchestrator: the sole authority over module order and composition.

@MX:ANCHOR: [AUTO] `run_pipeline` is the single composition entry point
(SWR-000-8/-2, REQ-INFRA-ORCH-1/3). It enforces the fixed stage order and the
CalibSet entry gate; modules are invoked only via the registry, never by each
other.
@MX:REASON: Every end-to-end run flows through here; the fixed ordering and the
calibration-refusal gate are safety-critical invariants (SWR-000-5).

Order (REQ-INFRA-ORCH-3):
    offset -> gain -> defect -> lag -> line_noise -> saturation -> geometry
        -> denoise -> post

Entry gate (REQ-INFRA-ORCH-4): a missing or mismatched CalibSet (resolution /
panel_id) causes refusal with an explicit error. Defaults are NEVER substituted
(SWR-000-5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import XFrame

# Fixed canonical pipeline order (REQ-INFRA-ORCH-3). The saturation/geometry
# pair corresponds to CLAUDE.md's "(포화/기하)".
CANONICAL_ORDER: tuple[str, ...] = (
    "offset",
    "gain",
    "defect",
    "lag",
    "line_noise",
    "saturation",
    "geometry",
    # Dedicated VST+BM3D denoise stage between geometry and post
    # (SPEC-DENOISE-001 decision 1). Registered stages are a subsequence of
    # CANONICAL_ORDER, so inserting a stage is backward-compatible with pipelines
    # that do not register it.
    "denoise",
    "post",
)

# A processing callable follows the module contract: process(frame, calib, params).
ProcessCallable = Callable[[XFrame, CalibSet, Params], XFrame]


class CalibrationError(RuntimeError):
    """Raised when the CalibSet entry gate refuses to proceed (ORCH-4)."""


class PipelineOrderError(ValueError):
    """Raised when a pipeline definition violates the canonical stage order."""


@dataclass(frozen=True)
class PipelineDefinition:
    """Declarative pipeline: the ordered subset of stages to execute.

    @MX:NOTE: [AUTO] This object is the ONLY place order/composition is decided
    (ORCH-1). Stages must be a subsequence of CANONICAL_ORDER — reordering is
    rejected (ORCH-3). Absent stages are simply skipped; present stages keep
    their canonical relative order.
    """

    stages: tuple[str, ...]

    def __post_init__(self) -> None:
        unknown = [s for s in self.stages if s not in CANONICAL_ORDER]
        if unknown:
            raise PipelineOrderError(f"unknown stage(s): {unknown}")
        # Enforce canonical relative order (must be a subsequence).
        rank = {name: i for i, name in enumerate(CANONICAL_ORDER)}
        ranks = [rank[s] for s in self.stages]
        if ranks != sorted(ranks):
            raise PipelineOrderError(
                f"stages violate canonical order {CANONICAL_ORDER}: {self.stages}"
            )
        if len(set(self.stages)) != len(self.stages):
            raise PipelineOrderError(f"duplicate stage(s) in {self.stages}")

    @classmethod
    def full(cls) -> "PipelineDefinition":
        """Definition running every canonical stage in order."""
        return cls(stages=CANONICAL_ORDER)


# Stage names that directly correspond to a CalibKind category; for these the
# CalibSet.kind must match the stage it is wired to.
_KIND_BY_STAGE: dict[str, str] = {
    "offset": "offset",
    "gain": "gain",
    "defect": "defect",
    "lag": "lag",
    "line_noise": "line_noise",
    # denoise stage consumes CalibSet(NOISE) — the (alpha, sigma) noise model
    # (SPEC-DENOISE-001 decision 2/5). Kind-vs-stage enforcement blocks default
    # substitution of the noise model at the entry gate.
    "denoise": "noise",
}


def _calibration_gate(
    frame: XFrame,
    calib_map: Mapping[str, CalibSet],
    stages: tuple[str, ...],
    panel_id: str | None = None,
    timestamp: str | None = None,
) -> None:
    """Refuse processing on missing/mismatched calibration (ORCH-4, EC-1/EC-2).

    Checks per stage: presence, schema, resolution, kind-vs-stage wiring, and
    (when given) expected panel_id and ISO-8601 validity window at `timestamp`.
    All wired CalibSets must additionally agree on panel_id with each other.

    @MX:NOTE: [AUTO] No default substitution — an unmet requirement raises
    CalibrationError naming the offending stage/field (SWR-000-5).
    """
    seen_panel: tuple[str, str] | None = None  # (stage, panel_id)
    for stage in stages:
        calib = calib_map.get(stage)
        if calib is None:
            raise CalibrationError(
                f"stage '{stage}': CalibSet missing; refusing to substitute defaults"
            )
        calib.validate()
        if not calib.matches_resolution(frame.shape):
            raise CalibrationError(
                f"stage '{stage}': CalibSet resolution {calib.resolution} "
                f"!= frame {frame.shape}"
            )
        expected_kind = _KIND_BY_STAGE.get(stage)
        if expected_kind is not None and calib.kind.value != expected_kind:
            raise CalibrationError(
                f"stage '{stage}': CalibSet kind '{calib.kind.value}' does not "
                f"match the stage (expected '{expected_kind}')"
            )
        if panel_id is not None and calib.panel_id != panel_id:
            raise CalibrationError(
                f"stage '{stage}': CalibSet panel_id '{calib.panel_id}' "
                f"!= expected panel_id '{panel_id}'"
            )
        if seen_panel is not None and calib.panel_id != seen_panel[1]:
            raise CalibrationError(
                f"stage '{stage}': CalibSet panel_id '{calib.panel_id}' "
                f"!= panel_id '{seen_panel[1]}' of stage '{seen_panel[0]}'"
            )
        seen_panel = (stage, calib.panel_id)
        if timestamp is not None and not (
            calib.valid_from <= timestamp <= calib.valid_until
        ):
            # ISO-8601 strings order lexicographically == chronologically.
            raise CalibrationError(
                f"stage '{stage}': timestamp {timestamp} outside validity "
                f"window [{calib.valid_from}, {calib.valid_until}]"
            )


def run_pipeline(
    frame: XFrame,
    definition: PipelineDefinition,
    registry: Mapping[str, ProcessCallable],
    calib_map: Mapping[str, CalibSet],
    params_map: Mapping[str, Params] | None = None,
    *,
    panel_id: str | None = None,
    timestamp: str | None = None,
) -> XFrame:
    """Execute the pipeline in fixed canonical order (ORCH-1/3/4).

    Args:
        frame:      input XFrame (treated as immutable, DATA-6).
        definition: the ordered stage subset (sole order authority).
        registry:   stage-name -> process callable. Modules are invoked ONLY
                    through this registry; they never call each other (ORCH-2,
                    structurally enforced by import-linter).
        calib_map:  stage-name -> CalibSet (entry gate input).
        params_map: stage-name -> Params (externalized; defaults to empty).

    Returns:
        the final XFrame. When validation_mode is active, per-stage intermediate
        frames are preserved on the result (DATA-5).
    """
    params_map = params_map or {}

    # Entry gate before any processing (ORCH-4).
    _calibration_gate(
        frame, calib_map, definition.stages, panel_id=panel_id, timestamp=timestamp
    )

    current = frame
    preserved: tuple[XFrame, ...] = ()
    for stage in definition.stages:
        process = registry.get(stage)
        if process is None:
            raise CalibrationError(
                f"stage '{stage}': no processing callable registered"
            )
        calib = calib_map[stage]
        params = params_map.get(stage, Params())
        current = process(current, calib, params)
        if frame.validation_mode:
            preserved = preserved + (current,)

    if frame.validation_mode and preserved:
        # Attach preserved intermediates to the final frame (DATA-5).
        from dataclasses import replace

        current = replace(current, intermediates=preserved)
    return current
