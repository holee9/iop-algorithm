"""Synthetic CalibSet factory (#18, additive, SPEC-VIEWER-001).

@MX:NOTE: [AUTO] Deploy-time promotion of the synthetic-CalibSet pattern
already used ad hoc by tests (e.g. `tests/pipeline/frame_fixtures.py::_calib`)
so the verification GUI's raw-input path can substitute a schema-valid
CalibSet when no measured one is available (REQ-VIEW-CORE-3). Placed in
`common/` -- not `apps/gui/` -- because `pyproject.toml`
`[tool.setuptools] packages` only ships `common`, `modules`, `pipeline`,
`metrics`; an apps/gui-local factory would not be deployable (plan.md SS3,
REQ-VIEW-CORE-3 "deployable" requirement forces a single answer). additive
only -- does not alter `common/calibset.py`'s schema or any existing
module-specific calib builder.
"""

from __future__ import annotations

from common.calibset import CalibKind, CalibProvenance, CalibSet

_DEFAULT_PANEL_ID = "SYNTH-PANEL"
_DEFAULT_VALID_FROM = "2026-01-01"
_DEFAULT_VALID_UNTIL = "2099-01-01"


def make_synthetic_calibset(
    resolution: tuple[int, int],
    kind: CalibKind,
    *,
    panel_id: str = _DEFAULT_PANEL_ID,
    valid_from: str = _DEFAULT_VALID_FROM,
    valid_until: str = _DEFAULT_VALID_UNTIL,
) -> CalibSet:
    """Build a schema-valid synthetic CalibSet for any (resolution, kind).

    Substitutes for a measured CalibSet when none is available on disk
    (REQ-VIEW-CORE-3, e.g. a raw-input GUI path with no real calibration).
    The data payload is empty -- callers that need a populated payload (e.g.
    the offset stage's `O_map`) must supply their own module-specific
    builder; this factory only guarantees the common schema
    (`common/calibset.py` `CalibSet.validate()`) passes so the orchestrator's
    entry gate does not refuse the run.
    """
    calib = CalibSet(
        panel_id=panel_id,
        resolution=tuple(resolution),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=kind,
        data={},
        provenance=CalibProvenance(created_at=valid_from, source="synthetic"),
    )
    calib.validate()
    return calib
