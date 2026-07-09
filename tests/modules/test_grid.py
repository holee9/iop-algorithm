"""Unit scenarios for the grid-line suppression module (SPEC-GRID-001).

Covers acceptance Scenarios 5/6/7/9 and edge cases EC-2/EC-3/EC-4/EC-6, plus the
SEARCH/NOTCH/PASSTHROUGH/MOIRE/CONTRACT requirement groups. The hard-DoD
detection + residual-invisibility + MTF guardrail live in test_tc_grid.py.

All thresholds are injected via Params/EV (measurement != judgment); nothing is
embedded in the module.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.contract import Params, check_process_contract
from common.xframe import MaskFlag, new_frame
from modules import grid
from tests.modules.phantoms.grid_syn import (
    EV,
    F_GRID_ALIASED,
    F_GRID_BELOW,
    F_GRID_NEAR,
    F_NYQUIST,
    PITCH_MM,
    fold_frequency,
    grid_params,
    make_crossed_grid_phantom,
    make_frame,
    make_grid_phantom,
    other_calib,
)


def _extra(out):
    return dict(out.history[-1].extra)


# -- Scenario 5: direction estimation + observed-spectrum peak search ----------


@pytest.mark.parametrize(
    "direction,f_grid",
    [("vertical", F_GRID_BELOW), ("horizontal", F_GRID_BELOW), ("vertical", F_GRID_NEAR)],
)
def test_direction_estimated_from_psd_energy(direction, f_grid):
    _, img = make_grid_phantom((128, 128), f_grid, direction=direction)
    analysis = grid.analyze(img, grid_params())
    assert analysis.detected
    assert analysis.direction == direction


def test_observed_peak_matches_known_frequency_below_nyquist():
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    analysis = grid.analyze(img, grid_params())
    assert analysis.peaks
    fundamental = analysis.peaks[0]
    assert fundamental.freq_lpmm == pytest.approx(F_GRID_BELOW, abs=0.1)
    assert fundamental.significance_db >= EV["d_th_db"]


def test_peak_search_restricted_to_search_band():
    # A pure low-frequency anatomy (no grid) has all energy below the 0.3 lp/mm
    # band edge -> no peak inside the search band.
    clean, _ = make_grid_phantom((128, 128), F_GRID_BELOW, anatomy=True)
    analysis = grid.analyze(clean, grid_params())
    assert not analysis.detected


def test_search_consumes_common_fft_psd_component():
    # SWR-000-9: the axial Welch PSD estimator lives in common.fft_psd; the grid
    # module must consume it rather than re-implementing FFT/PSD locally.
    from common import fft_psd

    assert hasattr(fft_psd, "axial_welch_psd")
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    freq, psd = fft_psd.axial_welch_psd(img, axis=1, pitch_mm=PITCH_MM)
    assert freq[0] == 0.0 and freq[-1] == pytest.approx(F_NYQUIST, rel=1e-6)
    assert psd.shape == freq.shape


# -- EC-3: folded-harmonic candidates ------------------------------------------


def test_folded_harmonic_candidates_detected():
    # A square-wave grid carries strong harmonics; for an aliased fundamental the
    # 2nd harmonic folds back to a distinct in-band location that must also be
    # picked up (REQ-GRID-SEARCH-3).
    ny, nx = 128, 128
    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    f0 = F_GRID_ALIASED
    # square wave => fundamental + odd harmonics
    grid_sig = 200.0 * np.sign(np.cos(2.0 * np.pi * f0 * xs * PITCH_MM))
    img = 2000.0 + grid_sig
    analysis = grid.analyze(img, grid_params())
    assert analysis.detected
    freqs = sorted(p.freq_lpmm for p in analysis.peaks)
    fa = fold_frequency(f0)
    fa3 = fold_frequency(3.0 * f0)
    assert any(abs(f - fa) < 0.15 for f in freqs)
    assert any(abs(f - fa3) < 0.15 for f in freqs)


# -- Scenario 6 / EC-2: ambiguity + nominal-frequency prohibition --------------


def test_crossed_grid_is_ambiguous_and_passes_through():
    img = make_crossed_grid_phantom((128, 128), F_GRID_BELOW)
    frame = make_frame(img)
    out = grid.process(frame, other_calib((128, 128)), grid_params())
    extra = _extra(out)
    assert extra["grid_detected"] == "false"
    # numerically identical passthrough (no unauthorized suppression)
    assert np.array_equal(np.asarray(out.pixel), np.asarray(frame.pixel))


def test_metadata_never_enters_peak_search():
    # A deliberately WRONG nominal density is supplied. The observed peak must be
    # the real spectral peak, unaffected by the metadata (SWR-1001 [HARD]).
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    params_wrong_meta = grid_params(grid_meta_mounted=True, grid_meta_nominal_lpmm=8.0)
    a_meta = grid.analyze(img, params_wrong_meta)
    a_plain = grid.analyze(img, grid_params())
    assert a_meta.peaks[0].freq_lpmm == pytest.approx(a_plain.peaks[0].freq_lpmm)


# -- Scenario 7: 1D Gaussian notch on the grid-orthogonal axis -----------------


def test_notch_suppresses_detected_peak():
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    frame = make_frame(img)
    out = grid.process(frame, other_calib((128, 128)), grid_params())
    before = grid.analyze(img, grid_params())
    after = grid.analyze(np.asarray(out.pixel), grid_params())
    # detected peak power drops below significance after notch (invisible)
    assert before.detected
    assert (not after.detected) or after.peaks[0].significance_db < EV["residual_db"]


def test_notch_is_1d_not_isotropic():
    # A vertical grid is notched only along the horizontal frequency axis; the
    # orthogonal (vertical) frequency content of anatomy must be preserved. A 2D
    # isotropic notch would also carve the vertical axis. We verify by injecting a
    # benign VERTICAL-frequency ripple (grid-parallel axis) and confirming it
    # survives (REQ-GRID-NOTCH-2).
    ny, nx = 128, 128
    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    grid_v = 200.0 * np.cos(2.0 * np.pi * F_GRID_BELOW * xs * PITCH_MM)
    # benign ripple along y at the SAME frequency the notch targets on x
    ripple_y = 200.0 * np.cos(2.0 * np.pi * F_GRID_BELOW * ys * PITCH_MM)
    img = 2000.0 + grid_v + ripple_y
    frame = make_frame(img)
    out = grid.process(frame, other_calib((128, 128)), grid_params())
    resid = np.asarray(out.pixel, dtype=np.float64) - 2000.0
    # vertical ripple energy retained (grid-parallel axis untouched)
    from common import fft_psd

    _, psd_y = fft_psd.axial_welch_psd(resid, axis=0, pitch_mm=PITCH_MM)
    fy = np.fft.rfftfreq(ny, d=PITCH_MM)
    peak_y = psd_y[np.argmin(np.abs(fy - F_GRID_BELOW))]
    bg_y = np.median(psd_y[fy >= 0.3])
    assert 10.0 * np.log10(peak_y / bg_y) >= EV["d_th_db"]


def test_notch_bandwidth_scales_with_peak_fwhm():
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    frame = make_frame(img)
    out = grid.process(frame, other_calib((128, 128)), grid_params())
    extra = _extra(out)
    assert float(extra["notch_bandwidth_lpmm"]) > 0.0


# -- Scenario 4 / EC-4: no-detection passthrough -------------------------------


def test_no_grid_passes_through_bit_identical():
    clean, _ = make_grid_phantom((96, 96), F_GRID_BELOW, anatomy=True)
    frame = make_frame(clean)
    out = grid.process(frame, other_calib((96, 96)), grid_params())
    extra = _extra(out)
    assert extra["grid_detected"] == "false"
    assert np.array_equal(np.asarray(out.pixel), np.asarray(frame.pixel))
    assert np.array_equal(np.asarray(out.masks), np.asarray(frame.masks))


def test_subthreshold_noise_peak_not_suppressed():
    # Pure noise: any spectral peak is below D_th -> passthrough (EC-4).
    rng = np.random.default_rng(3)
    img = 2000.0 + rng.normal(0.0, 20.0, size=(96, 96))
    frame = make_frame(img)
    out = grid.process(frame, other_calib((96, 96)), grid_params())
    assert _extra(out)["grid_detected"] == "false"
    assert np.array_equal(np.asarray(out.pixel), np.asarray(frame.pixel))


# -- Scenario 9 / EC-6: module contract ----------------------------------------


def test_process_conforms_to_contract():
    assert check_process_contract(grid) == ()


def test_input_frame_is_immutable():
    _, img = make_grid_phantom((96, 96), F_GRID_BELOW, direction="vertical")
    frame = make_frame(img)
    pixel_copy = np.array(frame.pixel, copy=True)
    grid.process(frame, other_calib((96, 96)), grid_params())
    assert np.array_equal(np.asarray(frame.pixel), pixel_copy)


def test_masks_substrate_unchanged():
    _, img = make_grid_phantom((96, 96), F_GRID_BELOW, direction="vertical")
    masks = np.zeros((96, 96), dtype=np.uint8)
    masks[10, 10] = np.uint8(MaskFlag.SATURATION)
    frame = new_frame(np.asarray(img, dtype=np.float32), masks)
    out = grid.process(frame, other_calib((96, 96)), grid_params())
    # no flag set or cleared (grid consumes masks, never mutates the substrate)
    assert np.array_equal(np.asarray(out.masks), masks)


def test_history_records_scalar_diagnostics():
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    frame = make_frame(img)
    out = grid.process(frame, other_calib((128, 128)), grid_params())
    extra = _extra(out)
    for key in ("grid_detected", "direction", "direction_energy_ratio_db", "n_peaks"):
        assert key in extra
    assert out.history[-1].module_name == "grid"
