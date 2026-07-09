"""IRF fitting builder: synthetic recovery, single-exposure ban, round-trip.

Covers acceptance Scenario 6 and EC-2 for metrics.lag_irf (SWR-401,
REQ-LAG-IRF-1/2/3).
"""

from __future__ import annotations

import numpy as np
import pytest

from modules.lag import K_IRF_A, K_IRF_B, LagCorrector
from common.calibset import CalibKind
from metrics.lag_irf import (
    LagIRFCalibrationError,
    StepResponse,
    fit_lag_irf,
)
from tests.modules.phantoms.lag_seq import (
    IRF_A,
    IRF_B,
    lag_params,
    make_matched_sequence,
)


def _synthetic_residual(amplitude, a, b, n=12):
    m = np.arange(1, n + 1, dtype=np.float64)
    a_arr = np.asarray(a)[:, None]
    b_arr = np.asarray(b)[:, None]
    curve = (a_arr * b_arr ** m[None, :]).sum(axis=0)
    return amplitude * curve


def _known_step_responses(a=IRF_A, b=IRF_B):
    # Saturation 2..90% multi-point exposures.
    return [
        StepResponse(amplitude=amp, residual=_synthetic_residual(amp, a, b))
        for amp in (1000.0, 2500.0, 4000.0)
    ]


def test_scenario6_fit_recovers_known_irf():
    """REQ-LAG-IRF-1/3: multi-exposure step responses -> recovered coefficients
    that reconstruct the known afterglow curve within tolerance."""
    calib = fit_lag_irf(
        _known_step_responses(),
        m_terms=3,
        panel_id="PANEL-A",
        resolution=(8, 8),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
    )
    assert calib.kind is CalibKind.LAG
    a_fit = np.asarray(calib.data[K_IRF_A], dtype=np.float64)
    b_fit = np.asarray(calib.data[K_IRF_B], dtype=np.float64)

    # Reconstruction of the normalized curve must match the known IRF closely.
    m = np.arange(1, 13, dtype=np.float64)
    known = (np.asarray(IRF_A)[:, None] * np.asarray(IRF_B)[:, None] ** m[None, :]).sum(0)
    got = (a_fit[:, None] * b_fit[:, None] ** m[None, :]).sum(0)
    assert np.allclose(got, known, atol=1e-4)


def test_ec2_single_exposure_rejected():
    """EC-2 / REQ-LAG-IRF-2: single-exposure calibration is refused."""
    with pytest.raises(LagIRFCalibrationError, match="single-exposure"):
        fit_lag_irf(
            [StepResponse(amplitude=1000.0, residual=_synthetic_residual(1000.0, IRF_A, IRF_B))],
            m_terms=3,
            panel_id="PANEL-A",
            resolution=(8, 8),
            valid_from="2026-01-01",
            valid_until="2027-01-01",
        )


def test_fit_quality_metrics_recorded_in_provenance():
    """A successful fit embeds its fit-quality diagnostics in CalibSet
    provenance (traceability)."""
    calib = fit_lag_irf(
        _known_step_responses(),
        m_terms=3,
        panel_id="PANEL-A",
        resolution=(8, 8),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
    )
    assert calib.provenance is not None
    assert "rel_rms_residual" in calib.provenance.note


def test_unfittable_input_raises_not_bad_calibset():
    """A degenerate/noise-dominated step response the exponential-sum model
    cannot fit must raise LagIRFCalibrationError with diagnostics, never emit a
    silently bad CalibSet."""
    rng = np.random.default_rng(0)
    # Pure noise residuals (no decaying exponential structure) at several
    # exposures — the LTI premise is violated, so the fit cannot converge to an
    # acceptable relative-RMS residual.
    responses = [
        StepResponse(amplitude=amp, residual=rng.normal(0.0, 1.0, size=12))
        for amp in (1000.0, 2500.0, 4000.0)
    ]
    with pytest.raises(LagIRFCalibrationError, match="relative_rms_residual"):
        fit_lag_irf(
            responses,
            m_terms=3,
            panel_id="PANEL-A",
            resolution=(8, 8),
            valid_from="2026-01-01",
            valid_until="2027-01-01",
        )


def test_scenario6_fit_then_correct_round_trip():
    """Fitted CalibSet(LAG) drives the correction and recovers the true seq."""
    ph = make_matched_sequence(shape=(8, 8), n_frames=6, a=IRF_A, b=IRF_B)
    calib = fit_lag_irf(
        _known_step_responses(),
        m_terms=3,
        panel_id="PANEL-A",
        resolution=(8, 8),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
    )
    lag = LagCorrector()
    for measured, truth in zip(ph.measured_frames, ph.true_frames):
        out = lag.process(measured, calib, lag_params())
        assert np.allclose(out.pixel, truth.pixel, atol=2.0)
