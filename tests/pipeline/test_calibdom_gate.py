"""XDET-TC-063..065: cross-domain entry-gate firewall (SPEC-CALDOM-001).

Exercises the descriptor checks the orchestrator entry gate layers on top of the
existing five checks (existence/resolution/kind/panel_id/validity):

  - TC-063: a specified-domain CalibSet in a mismatched pipeline-domain context
    is REJECTED (real CalibrationError), and the same CalibSet in a matching
    context PASSES (positive control, real pipeline execution evidence).
  - TC-064: two stages with mutually inconsistent specified domains — or
    mutually inconsistent specified beam_quality — are REJECTED.
  - TC-065: unspecified descriptors / a None pipeline context skip the descriptor
    checks entirely (no regression); the pre-existing gate behavior is unchanged.

Evidence is REAL (lesson L#1): rejections assert an actual raised
CalibrationError naming the offending field, and the positive control inspects
the history of the actually-executed pipeline — never a vacuous "did not raise".
"""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibDomain, CalibKind, CalibSet
from common.xframe import new_frame
from pipeline.orchestrator import (
    CalibrationError,
    PipelineDefinition,
    _calibration_gate,
    run_pipeline,
)
from tests.fixtures import passthrough

FRAME_SHAPE = (4, 4)


def _calib(
    kind: CalibKind,
    *,
    domain: CalibDomain = CalibDomain.UNSPECIFIED,
    beam_quality: str | None = None,
    panel_id: str = "PANEL-A",
) -> CalibSet:
    return CalibSet(
        panel_id=panel_id,
        resolution=FRAME_SHAPE,
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=kind,
        data={},
        domain=domain,
        beam_quality=beam_quality,
    )


@pytest.fixture
def frame():
    return new_frame(np.arange(16, dtype=np.float32).reshape(FRAME_SHAPE))


# --- TC-063: cross-context domain rejection + positive control ----------------


def test_tc063_medical_gain_map_rejected_in_ndt_pipeline(frame):
    """A medical RQA5 gain map fed to an NDT-domain pipeline is refused, and the
    error names the offending stage / CalibSet domain / expected domain."""
    definition = PipelineDefinition(stages=("gain",))
    registry = {"gain": passthrough.process}
    calib_map = {
        "gain": _calib(CalibKind.GAIN, domain=CalibDomain.MEDICAL, beam_quality="RQA5")
    }
    with pytest.raises(CalibrationError) as excinfo:
        run_pipeline(frame, definition, registry, calib_map, domain=CalibDomain.NDT)
    msg = str(excinfo.value)
    assert "gain" in msg
    assert "medical" in msg and "ndt" in msg


def test_tc063_matching_domain_context_passes_with_execution_evidence(frame):
    """Positive control: the SAME medical CalibSet in a medical-domain context is
    accepted and the pipeline actually runs the stage (history evidence)."""
    definition = PipelineDefinition(stages=("gain",))
    registry = {"gain": passthrough.process}
    calib = _calib(CalibKind.GAIN, domain=CalibDomain.MEDICAL, beam_quality="RQA5")
    out = run_pipeline(
        frame, definition, registry, {"gain": calib}, domain=CalibDomain.MEDICAL
    )
    # Real execution evidence: the passthrough stage ran and recorded history
    # tying the output to the medical CalibSet's id.
    assert len(out.history) == 1
    assert out.history[-1].calibset_id == calib.calibset_id
    assert frame.history == ()  # input untouched (DATA-6)


def test_tc063_unspecified_calibset_passes_any_domain_context(frame):
    """GATE-5: an UNSPECIFIED-domain CalibSet is domain-agnostic — a domain
    context never rejects it."""
    definition = PipelineDefinition(stages=("gain",))
    registry = {"gain": passthrough.process}
    calib_map = {"gain": _calib(CalibKind.GAIN)}  # UNSPECIFIED / None
    out = run_pipeline(frame, definition, registry, calib_map, domain=CalibDomain.NDT)
    assert len(out.history) == 1


# --- TC-064: cross-stage mutual domain / beam_quality rejection ---------------


def test_tc064_cross_stage_domain_mismatch_rejected(frame):
    calib_map = {
        "offset": _calib(CalibKind.OFFSET, domain=CalibDomain.MEDICAL),
        "gain": _calib(CalibKind.GAIN, domain=CalibDomain.NDT),
    }
    with pytest.raises(CalibrationError) as excinfo:
        _calibration_gate(frame, calib_map, stages=("offset", "gain"))
    msg = str(excinfo.value)
    assert "domain" in msg
    assert "offset" in msg and "gain" in msg


def test_tc064_cross_stage_beam_quality_mismatch_rejected(frame):
    calib_map = {
        "offset": _calib(CalibKind.OFFSET, beam_quality="RQA5"),
        "gain": _calib(CalibKind.GAIN, beam_quality="E2597-classA"),
    }
    with pytest.raises(CalibrationError) as excinfo:
        _calibration_gate(frame, calib_map, stages=("offset", "gain"))
    msg = str(excinfo.value)
    assert "beam_quality" in msg
    assert "RQA5" in msg and "E2597-classA" in msg


def test_tc064_matching_cross_stage_domain_and_beam_pass(frame):
    calib_map = {
        "offset": _calib(CalibKind.OFFSET, domain=CalibDomain.MEDICAL, beam_quality="RQA5"),
        "gain": _calib(CalibKind.GAIN, domain=CalibDomain.MEDICAL, beam_quality="RQA5"),
    }
    _calibration_gate(frame, calib_map, stages=("offset", "gain"))  # must not raise


# --- TC-065: no-regression (unspecified descriptors / None context) -----------


def test_tc065_all_unspecified_descriptors_pass_gate(frame):
    calib_map = {
        "offset": _calib(CalibKind.OFFSET),
        "gain": _calib(CalibKind.GAIN),
    }
    _calibration_gate(frame, calib_map, stages=("offset", "gain"))  # no raise


def test_tc065_none_context_skips_check_even_with_specified_domain(frame):
    """A specified-domain CalibSet with NO pipeline context is not rejected."""
    calib_map = {"gain": _calib(CalibKind.GAIN, domain=CalibDomain.MEDICAL)}
    _calibration_gate(frame, calib_map, stages=("gain",), domain=None)  # no raise


def test_tc065_unspecified_stage_does_not_conflict_with_specified(frame):
    """A mix of one UNSPECIFIED stage and one specified stage does not trip the
    mutual-consistency check (the unspecified stage is skipped)."""
    calib_map = {
        "offset": _calib(CalibKind.OFFSET),  # UNSPECIFIED
        "gain": _calib(CalibKind.GAIN, domain=CalibDomain.MEDICAL, beam_quality="RQA5"),
    }
    _calibration_gate(frame, calib_map, stages=("offset", "gain"))  # no raise


def test_tc065_existing_gate_checks_unchanged_by_descriptors(frame):
    """EC-3: the pre-existing checks (missing / resolution) still fire exactly as
    before, independent of the descriptor layer."""
    # Missing CalibSet -> existing refusal.
    with pytest.raises(CalibrationError, match="missing"):
        _calibration_gate(frame, {}, stages=("offset",))
    # Resolution mismatch -> existing refusal (descriptors default, irrelevant).
    bad = CalibSet(
        panel_id="PANEL-A",
        resolution=(8, 8),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=CalibKind.OFFSET,
        data={},
    )
    with pytest.raises(CalibrationError, match="resolution"):
        _calibration_gate(frame, {"offset": bad}, stages=("offset",))
