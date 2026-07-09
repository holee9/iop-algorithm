"""Frame / calib / registry helpers for SPEC-TIER-001 structure tests (tests/ only).

No dependency on ``pipeline.tier`` so the equivalence-frame tests stay decoupled
from the tier gating module. Builds a standard synthetic frame, a passthrough
registry, and a kind-matched calib map for a ``PipelineDefinition`` so the
equivalence / timing FRAME machinery can be exercised structurally without
asserting any numeric gate.

Integer-path vs float-path definitions mirror SWR-1302's split
(offset/gain/defect/line_noise = bit-identical target; every other stage = +/-1
LSB target). The numeric tolerance itself is P2 (Exclusions); only the structural
classification is exercised here.
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.xframe import XFrame, new_frame
from pipeline.orchestrator import PipelineDefinition
from tests.fixtures import passthrough

STD_SHAPE = (16, 16)

# SWR-1302 integer path (bit-identical target). Everything else = float path.
INT_STAGES: tuple[str, ...] = ("offset", "gain", "defect", "line_noise")
INT_DEF = PipelineDefinition(INT_STAGES)
# Float-inclusive variant: geometry is a non-integer-path stage (+/-1 LSB target).
FLOAT_DEF = PipelineDefinition(INT_STAGES + ("geometry",))

# Test-side mirror of the orchestrator kind-vs-stage wiring, used only to build a
# calib map that satisfies the (unchanged) entry gate for the passthrough runs.
_CALIB_KIND: dict[str, CalibKind] = {
    "offset": CalibKind.OFFSET,
    "gain": CalibKind.GAIN,
    "defect": CalibKind.DEFECT,
    "line_noise": CalibKind.LINE_NOISE,
    "denoise": CalibKind.NOISE,
    "virtual_grid": CalibKind.SCATTER,
}


def std_frame(shape: tuple[int, int] = STD_SHAPE) -> XFrame:
    """A deterministic synthetic input frame (the 'standard frame')."""
    n = shape[0] * shape[1]
    pixel = np.linspace(0.0, 1000.0, num=n, dtype=np.float32).reshape(shape)
    return new_frame(pixel)


def _calib(kind: CalibKind, shape: tuple[int, int]) -> CalibSet:
    return CalibSet(
        panel_id="PANEL-A",
        resolution=tuple(shape),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=kind,
        data={},
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
    )


def calib_map_for(
    definition: PipelineDefinition, shape: tuple[int, int] = STD_SHAPE
) -> dict[str, CalibSet]:
    """A kind-matched CalibSet per stage (empty data; passes the entry gate)."""
    return {
        s: _calib(_CALIB_KIND.get(s, CalibKind.OTHER), shape)
        for s in definition.stages
    }


def passthrough_registry(definition: PipelineDefinition):
    """Registry mapping every stage of ``definition`` to the identity module."""
    return {s: passthrough.process for s in definition.stages}


def perturb(frame: XFrame, delta: float = 1.0) -> XFrame:
    """A one-pixel-different copy of ``frame`` (equivalence negative control)."""
    pixel = np.array(frame.pixel, dtype=np.float32, copy=True)
    pixel[0, 0] = pixel[0, 0] + delta
    return new_frame(pixel, np.array(frame.masks, copy=True), frame.noise)
