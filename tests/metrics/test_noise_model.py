"""Offline (alpha, sigma) noise-model builder tests (REQ-DENOISE-VST-3).

Scenario 10: a known synthetic (alpha, sigma) injected into dose-step flat fields
must be recovered by the variance-vs-mean linear regression within a [T]
tolerance, and a CalibSet(NOISE) emitted. The builder lives in metrics (layering
metrics -> common); modules.denoise never imports it.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, K_NOISE_ALPHA, K_NOISE_SIGMA
from metrics.noise_model import DoseLevel, NoiseModelCalibrationError, fit_noise_model
from tests.modules.phantoms.denoise_syn import ALPHA, SIGMA, sample_pg

# External-injected recovery tolerances ([T]).
ALPHA_REL_TOL = 0.10
SIGMA_REL_TOL = 0.15


def _dose_levels(levels, shape=(96, 96), seed=1, n_frames=8):
    rng = np.random.default_rng(seed)
    out = []
    for lvl in levels:
        frames = np.stack(
            [sample_pg(np.full(shape, lvl), ALPHA, SIGMA, rng) for _ in range(n_frames)]
        )
        out.append(DoseLevel(frames=frames))
    return out


def test_scenario10_recovers_known_alpha_sigma():
    # Low dose levels keep the read-noise intercept sigma**2 identifiable (it is
    # otherwise negligible against alpha*mean at high dose).
    calib = fit_noise_model(
        _dose_levels([20.0, 50.0, 100.0, 200.0, 400.0]),
        panel_id="PANEL-A",
        resolution=(96, 96),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
    )
    assert calib.kind is CalibKind.NOISE
    alpha = float(np.asarray(calib.data[K_NOISE_ALPHA]))
    sigma = float(np.asarray(calib.data[K_NOISE_SIGMA]))
    assert abs(alpha - ALPHA) / ALPHA <= ALPHA_REL_TOL, alpha
    assert abs(sigma - SIGMA) / SIGMA <= SIGMA_REL_TOL, sigma


def test_single_dose_rejected():
    with pytest.raises(NoiseModelCalibrationError, match="2 dose"):
        fit_noise_model(
            _dose_levels([500.0]),
            panel_id="PANEL-A",
            resolution=(64, 64),
            valid_from="2026-01-01",
            valid_until="2027-01-01",
        )


def test_singular_design_rejected():
    """All dose means equal -> slope unidentifiable -> explicit refusal."""
    with pytest.raises(NoiseModelCalibrationError, match="singular"):
        fit_noise_model(
            _dose_levels([500.0, 500.0, 500.0]),
            panel_id="PANEL-A",
            resolution=(64, 64),
            valid_from="2026-01-01",
            valid_until="2027-01-01",
        )
