"""NPS/NNPS, DQE reproduction and edge cases (Scenario 3, 4, 10; EC-2, EC-3)."""

from __future__ import annotations

import numpy as np
import pytest

from metrics import dqe, mtf, nps
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


def test_scenario3_dqe_reproduces_formula():
    """DQE = MTF^2 q Ka / NPS reproduces the analytic composition."""
    params = make_params()
    edge = gen.make_slanted_edge()
    mtf_res = mtf.compute_mtf(edge.frame, params)
    noise = gen.make_white_noise_frames()
    nps_res = nps.compute_nps(noise.frames, params)

    freqs = nps_res.get("frequencies_lpmm")
    mtf_on_grid = np.interp(freqs, mtf_res.get("frequencies_lpmm"), mtf_res.get("mtf"))
    nps_vals = nps_res.get("nps")

    result = dqe.compute_dqe(freqs, mtf_on_grid, nps_vals, params)
    q = params.get("dqe_q")
    ka = params.get("dqe_ka")
    expected = mtf_on_grid**2 * q * ka / nps_vals
    got = result.get("dqe")
    good = ~np.isnan(got)
    assert np.allclose(got[good], expected[good], rtol=TOLERANCES["dqe_rel"])


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
