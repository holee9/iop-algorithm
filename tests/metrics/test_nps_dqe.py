"""NPS/NNPS, DQE reproduction and edge cases (Scenario 3, 4, 10; EC-2, EC-3)."""

from __future__ import annotations

import numpy as np
import pytest

from metrics import dqe, nps
from metrics.result import MetricReadError
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import TOLERANCES, make_params


def _midband(freqs, values, nyq):
    band = (freqs > 0.2 * nyq) & (freqs < 0.8 * nyq)
    return float(np.mean(values[band]))


def test_scenario3_white_noise_flat_nps():
    """White noise -> flat NPS at var*pixel_area within [T]."""
    phantom = gen.make_white_noise_frames()
    params = make_params()
    result = nps.compute_nps(phantom.frames, params)
    freqs = result.get("frequencies_lpmm")
    nyq = 1.0 / (2.0 * 0.14)
    level = _midband(freqs, result.get("nps"), nyq)
    rel = abs(level - phantom.flat_nps_level) / phantom.flat_nps_level
    assert rel < TOLERANCES["nps_rel"], (level, phantom.flat_nps_level)


def test_scenario3_nnps_normalization():
    """NNPS = NPS / mean_signal^2 within [T]."""
    phantom = gen.make_white_noise_frames()
    result = nps.compute_nps(phantom.frames, make_params())
    freqs = result.get("frequencies_lpmm")
    nyq = 1.0 / (2.0 * 0.14)
    level = _midband(freqs, result.get("nnps"), nyq)
    rel = abs(level - phantom.flat_nnps_level) / phantom.flat_nnps_level
    assert rel < TOLERANCES["nnps_rel"]


def test_colored_noise_is_lowpass_shaped():
    """Correlated noise -> NPS higher at low freq than near Nyquist."""
    phantom = gen.make_colored_noise_frames()
    result = nps.compute_nps(phantom.frames, make_params())
    freqs = result.get("frequencies_lpmm")
    nps1d = result.get("nps")
    low = float(np.mean(nps1d[(freqs > 0) & (freqs < 0.5)]))
    high = float(np.mean(nps1d[freqs > 2.5]))
    assert low > high


def _ideal_quantum_frames(fluence_per_mm2, pitch_mm, shape, n_frames, seed):
    """Poisson-limited ideal detector: each pixel counts N = fluence * area.

    For an ideal quantum-limited detector the output SNR equals the input SNR,
    so DQE = 1 at every frequency by construction.
    """
    from common.xframe import new_frame

    rng = np.random.default_rng(seed)
    n_mean = fluence_per_mm2 * (pitch_mm * pitch_mm)  # photons per pixel
    frames = [
        new_frame(rng.poisson(n_mean, size=shape).astype(np.float32))
        for _ in range(n_frames)
    ]
    return frames


def _ideal_dqe_midband(params, pitch_mm, shape=(512, 512), n_frames=24, seed=0):
    """Compute the mid-band DQE of an ideal quantum-limited synthetic detector.

    Non-circular: the expected value (~1) is the analytic DQE of an ideal
    Poisson detector, NOT a recomputation of the implementation expression. The
    engine ingests NNPS and q*Ka independently and must return ~1.
    """
    q = params.get("dqe_q")
    ka = params.get("dqe_ka")
    fluence = q * ka  # photons / mm^2
    frames = _ideal_quantum_frames(fluence, pitch_mm, shape, n_frames, seed)
    nps_res = nps.compute_nps(frames, params)
    freqs = nps_res.get("frequencies_lpmm")
    nnps = nps_res.get("nnps")
    mtf_ideal = np.ones_like(freqs)  # ideal detector: MTF = 1
    result = dqe.compute_dqe(freqs, mtf_ideal, nnps, params)
    got = result.get("dqe")
    nyq = 1.0 / (2.0 * pitch_mm)
    band = (freqs > 0.2 * nyq) & (freqs < 0.8 * nyq)
    return float(np.mean(got[band]))


def test_scenario3_dqe_ideal_detector_is_unity():
    """Ideal quantum-limited detector -> DQE ~ 1 and dimensionless (IEC form).

    Catches the dimensionally-inverted protocol §1.4 expression: with the wrong
    (MTF^2 q Ka / NPS) form the value is enormous, not ~1.
    """
    params = make_params()
    pitch = params.get("pixel_pitch_mm")
    dqe_mid = _ideal_dqe_midband(params, pitch, seed=0)
    assert abs(dqe_mid - 1.0) < TOLERANCES["dqe_ideal_abs"], dqe_mid


def test_scenario3_dqe_is_dose_invariant():
    """DQE at 2x dose ~= DQE at nominal dose (dose invariance of the IEC form).

    The inverted protocol expression is NOT dose invariant; this pins the fix.
    """
    pitch = make_params().get("pixel_pitch_mm")
    dqe_1x = _ideal_dqe_midband(make_params(), pitch, seed=1)
    # 2x dose: double the air kerma (fluence) and the delivered photon counts.
    params_2x = make_params(dqe_ka=make_params().get("dqe_ka") * 2.0)
    dqe_2x = _ideal_dqe_midband(params_2x, pitch, seed=2)
    assert abs(dqe_1x - dqe_2x) < TOLERANCES["dqe_ideal_abs"], (dqe_1x, dqe_2x)
    assert abs(dqe_2x - 1.0) < TOLERANCES["dqe_ideal_abs"], dqe_2x


def test_scenario4_three_dose_levels():
    """Per-dose NPS/DQE each produced with dose metadata (Scenario 4)."""
    params = make_params()
    for dose, sigma in (("XN/2", 70.0), ("XN", 50.0), ("2XN", 35.0)):
        noise = gen.make_white_noise_frames(sigma=sigma, seed=hash(dose) % 100)
        res = nps.compute_nps(noise.frames, params, dose_level=dose)
        assert res.condition.dose_level == dose
        assert res.get("nps") is not None


def test_ec2_roi_exceeds_frame_rejected():
    """EC-2: 256 ROI cannot fit a small frame -> reject with error."""
    small = gen.make_white_noise_frames(shape=(128, 128), n_frames=4)
    with pytest.raises(MetricReadError):
        nps.compute_nps(small.frames, make_params())  # roi_size 256 > 128


def test_ec3_dqe_zero_nps_marked_invalid():
    """EC-3: NPS at/below floor -> DQE invalid (NaN), no zero-division."""
    params = make_params()
    freqs = np.array([0.0, 1.0, 2.0, 3.0])
    mtf_vals = np.array([1.0, 0.8, 0.5, 0.2])
    nps_vals = np.array([1.0, 0.0, 0.5, 0.2])  # zero at index 1
    result = dqe.compute_dqe(freqs, mtf_vals, nps_vals, params)
    got = result.get("dqe")
    assert np.isnan(got[1])
    assert not np.isnan(got[0])
    assert 1 in result.get("invalid_indices")
    assert result.warnings


def test_scenario10_line_noise_peak_detected():
    """NPS-8 Optional: injected periodic column pattern -> column peak found."""
    frames, expected_freq = gen.make_line_noise_frames()
    result = nps.detect_line_noise(frames, make_params())
    peak = result.get("column_peak")["peak_freq_lpmm"]
    assert abs(peak - expected_freq) < 0.5
