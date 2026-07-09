"""Regression tests for verified code-review defects in modules.grid
(SPEC-GRID-001, T7 grid line suppression).

Each test targets one defect and is written to FAIL on the pre-fix code and pass
after the corresponding fix. Defect 5 (a conditional hard-DoD assertion) lives in
test_tc_grid.py where the affected assertion is.
"""

from __future__ import annotations

import numpy as np
import pytest

from modules import grid
from tests.modules.phantoms.grid_syn import (
    EV,
    F_NYQUIST,
    PITCH_MM,
    grid_params,
    make_grid_phantom,
)


# -- DEFECT 1: a peakless (but noisy) axis must never outrank a real peak --------


def test_defect1_peakless_noise_axis_does_not_outrank_real_peak(monkeypatch):
    """Direction selection must compare only axes where a peak was actually found.

    Pre-fix `analyze` compares the raw significance scalars, and a peakless axis
    reports its in-band noise-floor maximum as its "significance". Here the x-axis
    has NO peak but a high noise-floor value (20 dB) while the y-axis carries a
    genuine peak at a LOWER significance (8 dB). The correct grid axis is the
    y-axis (horizontal), and it must be selected regardless of the noise floor.
    """
    real_peak = grid.Peak(freq_lpmm=2.5, significance_db=8.0, fwhm_lpmm=0.1)
    calls: list[int] = []

    def fake_find_peaks(freq, psd, lo, f_nyq, d_th, max_peaks, bg_window):
        calls.append(1)
        # analyze() scans the x-axis (axis=1) first, then the y-axis (axis=0).
        if len(calls) == 1:
            return [], 20.0  # x-axis: no peak, high noise-floor value
        return [real_peak], 8.0  # y-axis: genuine peak, lower significance

    monkeypatch.setattr(grid, "_find_peaks", fake_find_peaks)
    _, img = make_grid_phantom((128, 128), 2.5, direction="horizontal")
    analysis = grid.analyze(img, grid_params())

    assert analysis.detected, "genuine peak on the peaked axis must be detected"
    assert analysis.direction == "horizontal", "must select the axis with the real peak"
    assert analysis.peaks and analysis.peaks[0].freq_lpmm == pytest.approx(2.5)


# -- DEFECT 2: a peak landing exactly on the Nyquist (last) PSD bin --------------


def test_defect2_peak_at_nyquist_bin_detected():
    """A grid peak at exactly the Nyquist bin must not be dropped by the search.

    Pre-fix `_find_peaks` skips the last PSD bin (no right neighbor), so a grid at
    f == f_N is never detected.
    """
    _, img = make_grid_phantom((128, 128), F_NYQUIST, direction="vertical", noise_sigma=0.0)
    analysis = grid.analyze(img, grid_params())
    assert analysis.detected, "Nyquist-bin grid peak must be detected"
    assert analysis.peaks[0].freq_lpmm == pytest.approx(F_NYQUIST, abs=0.12)


# -- DEFECT 3: an explicit folded-harmonic candidate on a shoulder ---------------


def test_defect3_folded_harmonic_on_shoulder_added_directly():
    """A folded harmonic that is NOT a strict local maximum must still be added.

    The 2nd harmonic of the fundamental folds onto the rising shoulder of a
    stronger neighbouring feature: it is elevated well above the local background
    (clears D_th) but its right neighbour is higher, so the local-maximum search
    misses it. The documented direct-significance check must add it.
    """
    f_nyq = 1.0 / (2.0 * PITCH_MM)
    n = 51
    freq = np.linspace(0.0, f_nyq, n)
    psd = np.ones(n)
    # Fundamental: a clean local maximum at bin 38 (freq ~2.714 lp/mm).
    psd[36], psd[37], psd[38], psd[39], psd[40] = 100.0, 800.0, 5000.0, 800.0, 100.0
    # A stronger neighbouring feature (local max at bin 27). fold(2*f0) lands on
    # bin 24, which sits on this feature's rising shoulder: elevated but NOT a
    # strict local maximum (its right neighbour bin 25 is higher).
    psd[23], psd[24], psd[25], psd[26], psd[27], psd[28] = 5.0, 30.0, 40.0, 90.0, 150.0, 30.0

    peaks, _ = grid._find_peaks(freq, psd, 0.3, f_nyq, 6.0, 3, 11)
    f0 = float(freq[38])
    f_harm = grid._fold(2.0 * f0, 2.0 * f_nyq, f_nyq)  # -> freq[24]
    got = [p.freq_lpmm for p in peaks]
    assert any(abs(f - f_harm) < 1e-6 for f in got), (
        f"folded harmonic on shoulder at {f_harm:.4f} not added; got {got}"
    )


# -- DEFECT 4: notch_gain_1d must match the two-term applied notch ---------------


def test_defect4_notch_gain_1d_matches_applied_notch_at_nyquist():
    """notch_gain_1d must equal the gain the real notch imposes at Nyquist.

    Pre-fix notch_gain_1d sums a single Gaussian term while the applied notch sums
    two (at +/-f_peak). For a low-frequency, wide-bandwidth peak the mirror term's
    tail reaches +Nyquist, so the single-term proxy UNDER-reports attenuation.
    """
    f_nyq = 1.0 / (2.0 * PITCH_MM)
    # Low-frequency (above the moire cutoff), wide-bandwidth peak: the -f_peak
    # mirror term's tail is non-negligible at +Nyquist.
    peaks = (grid.Peak(freq_lpmm=0.6, significance_db=20.0, fwhm_lpmm=3.0),)
    params = grid_params()
    fwhm_mult = EV["notch_fwhm_mult"]
    moire_cutoff = EV["moire_cutoff_lpmm"]
    atten_cap = EV["moire_atten_cap"]

    n = 128
    xs = np.arange(n)
    col = np.cos(np.pi * xs)  # pure Nyquist grid along columns (vertical grid)
    img = np.tile(col, (n, 1))
    gain, _ = grid._notch_axis_gain(n, PITCH_MM, peaks, fwhm_mult, moire_cutoff, atten_cap)
    out = grid._apply_notch(img, "vertical", gain)
    measured = float(np.max(np.abs(out[0])) / np.max(np.abs(img[0])))

    predicted = float(grid.notch_gain_1d([f_nyq], peaks, params)[0])
    assert predicted == pytest.approx(measured, abs=1e-6), (
        f"notch_gain_1d {predicted:.6f} != applied-notch gain {measured:.6f}"
    )
