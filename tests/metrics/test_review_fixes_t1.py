"""Regression tests for the 10 code-review defects of the T1 metrics engine
(SPEC-METRICS-001, commit bab37f5). One test (or pair) per finding.

Defects 1/3 (DQE inversion + circular test) live in test_nps_dqe.py; defect 2
(release-gate skeleton integrity) in tests/test_tc_skeletons.py; defect 9
(require_param) in test_require_param.py. The remaining engine-internal findings
are pinned here.
"""

from __future__ import annotations

import numpy as np
import pytest

from common import fft_psd
from common.xframe import new_frame
from metrics import lag, mtf, nps
from metrics.result import MetricReadError
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import TOLERANCES, make_params


# -- [4] MTF Hann window must be centred on the LSF peak, not the midpoint -----


def test_mtf_window_centred_on_lsf_peak_for_offcentre_edge():
    """An off-centre edge with a broad LSF reproduces the analytic MTF within [T].

    With a broad Gaussian (sigma 3 px) the window curvature over the LSF core
    matters: a midpoint-centred Hann applied to an edge at 8% of the ROI width
    biases the presampled MTF above the 0.02 tolerance, while a window centred on
    the LSF peak reproduces the analytic curve. Non-circular: compared against
    the phantom's analytic Gaussian MTF, not against another engine call.
    """
    phantom = gen.make_slanted_edge(
        shape=(128, 128), angle_deg=2.0, sigma_px=3.0, edge_pos_frac=0.08
    )
    result = mtf.compute_mtf(phantom.frame, make_params())
    freqs = result.get("frequencies_lpmm")
    nyq = result.get("nyquist_lpmm")
    band = freqs <= nyq
    got = result.get("mtf")[band]
    expected = phantom.analytic_mtf(freqs)[band]
    assert np.max(np.abs(got - expected)) < TOLERANCES["mtf_abs"]


# -- [5] lag: robust plateau/baseline detection, explicit precondition errors --


def _seq(levels):
    return [new_frame(np.full((16, 16), v, dtype=np.float32)) for v in levels]


def test_lag_plateau_detected_by_level_not_argmax():
    """Noisy multi-frame plateau: argmax lands mid-plateau; level detection
    picks the LAST exposed frame so the first residual is correct."""
    offset = 1000.0
    # Three exposed plateau frames (frame index 1 is the noisy argmax spike),
    # then the first residual, decay, and a settled dark tail.
    levels = [4900.0, 5050.0, 4950.0, 1300.0, 1080.0, 1010.0, 1000.0]
    #          f0       f1(max)  f2(last-exposed) f3(residual) ...   dark
    result = lag.compute_first_frame_lag(_seq(levels), make_params())
    assert result.get("last_exposed_index") == 2
    assert result.get("first_residual_index") == 3
    # lag % = (residual - dark) / (exposed - dark) * 100 = 300/3950*100.
    expected = (1300.0 - 1000.0) / (4950.0 - 1000.0) * 100.0
    assert abs(result.get("first_frame_lag_pct") - expected) < 1e-6


def test_lag_unsettled_tail_raises():
    """A sequence whose residual is still decaying at the last frame has no
    settled dark baseline -> explicit MetricReadError (no silent last-frame)."""
    levels = [5000.0, 3000.0, 2200.0, 1700.0, 1400.0]  # still falling fast
    with pytest.raises(MetricReadError, match="settled dark tail"):
        lag.compute_first_frame_lag(_seq(levels), make_params())


# -- [6] NPS: central-region tiling excludes the border ------------------------


def test_nps_central_tiling_ignores_bright_border():
    """A bright border step must not bias NPS: central tiling excludes it."""
    params = make_params()
    clean = gen.make_white_noise_frames(shape=(512, 512), n_frames=12, seed=7)
    clean_res = nps.compute_nps(clean.frames, params)

    # Same noise, with a high-variance noisy band painted on the outer 10%
    # border (broadband corruption, unlike a smooth step which is low-frequency).
    # Central tiling must exclude it; border tiling would inflate the mid-band.
    rng = np.random.default_rng(99)
    bordered = []
    for f in clean.frames:
        img = np.asarray(f.pixel, dtype=np.float64).copy()
        b = int(0.1 * img.shape[0])
        corruption = rng.normal(0.0, 1500.0, size=img.shape)
        mask = np.zeros(img.shape, dtype=bool)
        mask[:b, :] = mask[-b:, :] = mask[:, :b] = mask[:, -b:] = True
        img[mask] += corruption[mask]
        bordered.append(new_frame(img.astype(np.float32)))
    bordered_res = nps.compute_nps(bordered, params)

    freqs = clean_res.get("frequencies_lpmm")
    nyq = 1.0 / (2.0 * 0.14)
    band = (freqs > 0.2 * nyq) & (freqs < 0.8 * nyq)
    lvl_clean = float(np.mean(clean_res.get("nps")[band]))
    lvl_border = float(np.mean(bordered_res.get("nps")[band]))
    assert abs(lvl_border - lvl_clean) / lvl_clean < TOLERANCES["nps_rel"]


# -- [7] line-noise detection requires a significance test ---------------------


def test_line_noise_pure_white_noise_no_detection():
    """Pure white noise has no line noise: argmax alone would report a bin, the
    significance test must return not-detected."""
    rng = np.random.default_rng(11)
    frames = [
        new_frame((2000.0 + rng.normal(0.0, 20.0, size=(256, 256))).astype(np.float32))
        for _ in range(8)
    ]
    result = nps.detect_line_noise(frames, make_params())
    assert result.get("column_peak")["detected"] is False
    assert result.get("column_peak")["peak_freq_lpmm"] is None
    assert result.get("row_peak")["detected"] is False


def test_line_noise_injected_pattern_detected_at_frequency():
    """An injected periodic column pattern is detected at the correct freq."""
    frames, expected_freq = gen.make_line_noise_frames()
    result = nps.detect_line_noise(frames, make_params())
    col = result.get("column_peak")
    assert col["detected"] is True
    assert abs(col["peak_freq_lpmm"] - expected_freq) < 0.5


# -- [8] finite-difference derivative attenuation correction -------------------


def test_mtf_derivative_correction_tightens_reproduction():
    """Analytic Gaussian-edge MTF reproduced within the tightened 0.02 abs
    tolerance thanks to the derivative-sinc correction."""
    phantom = gen.make_slanted_edge(angle_deg=2.0, sigma_px=0.6)
    result = mtf.compute_mtf(phantom.frame, make_params())
    freqs = result.get("frequencies_lpmm")
    nyq = result.get("nyquist_lpmm")
    band = freqs <= nyq
    got = result.get("mtf")[band]
    expected = phantom.analytic_mtf(freqs)[band]
    assert np.max(np.abs(got - expected)) < 0.02


# -- [10] axial_1d_nps common frequency range for non-square inputs ------------


def test_axial_nps_nonsquare_axis_within_common_range():
    """Non-square (ny=64, nx=96) white-noise NPS: the returned frequency axis
    must not extend past the common Nyquist min(fx.max, fy.max).

    The horizontal axis (nx=96) reaches a higher Nyquist than the vertical
    (ny=64); the old code returned fx[fx>=0], whose top bins lie beyond the
    vertical axis and are fabricated by np.interp clamping the vertical estimate.
    """
    rng = np.random.default_rng(13)
    sigma = 30.0
    pitch = 0.14
    rois = rng.normal(0.0, sigma, size=(40, 64, 96))  # nx=96 > ny=64
    nps2d = fft_psd.nps_2d(rois, pitch * pitch)
    freq, nps1d = fft_psd.axial_1d_nps(
        nps2d, pitch, exclude_axis_bins=1, n_average_lines=7
    )
    fx_max = float(np.fft.fftshift(np.fft.fftfreq(96, d=pitch)).max())
    fy_max = float(np.fft.fftshift(np.fft.fftfreq(64, d=pitch)).max())
    common = min(fx_max, fy_max)
    assert freq.max() <= common + 1e-12, (freq.max(), common)
    # White-noise flat level is preserved within the common range (no clamp bias).
    expected = sigma**2 * pitch * pitch
    top = freq > 0.7 * freq.max()
    assert abs(float(np.mean(nps1d[top])) - expected) / expected < 0.15
