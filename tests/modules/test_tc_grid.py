"""XDET-TC-015 / TC-016 live release gates for T7 grid suppression
(SPEC-GRID-001).

TC-015 (hard DoD): observed-spectrum detection across the three density classes
+ residual grid-line invisibility after the 1D notch + grid-orthogonal
MTF@Nyquist retention guardrail (EV-102 min). Includes the aliased-class
negative control proving the observed-spectrum search is load-bearing (SWR-1001).

TC-016 (PARTIAL): standard-class moire 0-count, low-frequency-fold attenuation
cap + grid-replacement warning, and GLS-failure numerically-identical passthrough
(FR-M007). Perceptual "invisibility" (EV-204 observer study) is licensing-deferred.

Thresholds (D_th, residual, EV-102, moire cutoff/cap) are external-injected.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.contract import Params
from metrics import mtf as mtf_engine
from modules import grid
from tests.modules.phantoms.grid_syn import (
    EV,
    F_GRID_ALIASED,
    F_GRID_BELOW,
    F_GRID_MOIRE,
    F_GRID_NEAR,
    PITCH_MM,
    fold_frequency,
    grid_params,
    make_frame,
    make_grid_phantom,
    make_slanted_edge_with_grid,
    other_calib,
)

_CLASSES = [
    ("below", F_GRID_BELOW),
    ("near", F_GRID_NEAR),
    ("aliased", F_GRID_ALIASED),
]


def _mtf_params():
    return Params(
        values={
            "pixel_pitch_mm": PITCH_MM,
            "mtf_oversample": 4,
            "mtf_angle_min_deg": 1.0,
            "mtf_angle_max_deg": 10.0,
            "mtf_angle_margin_deg": 0.5,
        }
    )


# -- TC-015 (a): observed-spectrum detection across 3 density classes -----------


@pytest.mark.parametrize("name,f_grid", _CLASSES, ids=[c[0] for c in _CLASSES])
def test_tc015_detects_correct_observed_peak(name, f_grid):
    _, img = make_grid_phantom((128, 128), f_grid, direction="vertical")
    analysis = grid.analyze(img, grid_params())
    assert analysis.detected, f"{name}: grid not detected"
    observed = analysis.peaks[0].freq_lpmm
    expected = fold_frequency(f_grid)  # aliased fold for f_grid > f_N
    assert observed == pytest.approx(expected, abs=0.12), (
        f"{name}: observed {observed} != expected fold {expected}"
    )


# -- TC-015 (b): residual grid-line invisibility after the notch ----------------


@pytest.mark.parametrize("name,f_grid", _CLASSES, ids=[c[0] for c in _CLASSES])
def test_tc015_residual_peak_below_significance(name, f_grid):
    _, img = make_grid_phantom((128, 128), f_grid, direction="vertical")
    frame = make_frame(img)
    out = grid.process(frame, other_calib((128, 128)), grid_params())
    after = grid.analyze(np.asarray(out.pixel), grid_params())
    # Hard-DoD (unconditional): the suppressed frequency must not carry a
    # significant residual peak in EITHER outcome. If analyze() reports
    # detected=False the peaks tuple is empty and `residual` is empty, so the
    # targeted grid line is invisible (DoD met). If detected=True (partial
    # suppression), any residual peak at the suppressed frequency must still clear
    # the significance bar. `all([])` is True, so the success case passes and a
    # broken notch (peak persists) fails -- the assertion is never a silent no-op.
    expected = fold_frequency(f_grid)
    residual = [p for p in after.peaks if abs(p.freq_lpmm - expected) < 0.15]
    assert all(p.significance_db < EV["residual_db"] for p in residual), (
        f"{name}: residual grid line still visible"
    )


# -- TC-015 (c): grid-orthogonal MTF@Nyquist retention guardrail (EV-102) -------


@pytest.mark.parametrize("name,f_grid", _CLASSES, ids=[c[0] for c in _CLASSES])
def test_tc015_mtf_nyquist_retention_guardrail(name, f_grid):
    # Baseline MTF@Nyquist is measured with the real metrics engine on a clean
    # slanted edge (grid-orthogonal / notched axis). The post-suppression
    # retention is MTF_before(Nyq) * |H_notch(Nyq)| / MTF_before(Nyq) =
    # |H_notch(Nyq)| -- the notch transfer gain at Nyquist. This is the exact,
    # deterministic retention of a linear notch and avoids the Gibbs-ringing
    # artifact that re-estimating an ESF from a notched hard edge would inject
    # (see report deviation note). EV-102 min is external-injected.
    edge_clean = make_slanted_edge_with_grid((128, 128), with_grid=False)
    base = mtf_engine.compute_mtf(
        make_frame(edge_clean), _mtf_params(), direction="vertical"
    )
    m_base = base.get("mtf_at_nyquist")
    nyquist = base.get("nyquist_lpmm")
    assert m_base > 0.0

    # The grid the module actually detects (observed-spectrum peaks) drives the
    # notch; use a uniform+grid phantom so detection is clean.
    _, img = make_grid_phantom((128, 128), f_grid, direction="vertical")
    analysis = grid.analyze(img, grid_params())
    assert analysis.detected
    gain_nyquist = float(grid.notch_gain_1d([nyquist], analysis.peaks, grid_params())[0])
    retention = gain_nyquist  # = MTF_after(Nyq) / MTF_before(Nyq)
    assert retention >= EV["ev102_mtf_retention_min"], (
        f"{name}: MTF@Nyquist retention {retention:.3f} < EV-102 min"
    )


# -- TC-015 negative control: nominal-frequency search fails, observed succeeds --


def test_tc015_aliased_negative_control():
    # f_grid = 5.0 lp/mm > f_N; nominal is not representable, observed folds to f_a.
    _, img = make_grid_phantom((128, 128), F_GRID_ALIASED, direction="vertical")
    analysis = grid.analyze(img, grid_params())
    f_a = fold_frequency(F_GRID_ALIASED)
    observed = analysis.peaks[0].freq_lpmm
    assert observed == pytest.approx(f_a, abs=0.12)
    assert abs(observed - F_GRID_ALIASED) > 1.0  # observed != nominal

    # Test-local control: probe the observed PSD at the NOMINAL location. It is
    # above Nyquist (unrepresentable) so a nominal-frequency search finds nothing.
    from common import fft_psd

    freq, psd = fft_psd.axial_welch_psd(img, axis=1, pitch_mm=PITCH_MM)
    assert F_GRID_ALIASED > freq[-1]  # nominal beyond the representable axis
    bg = np.median(psd[freq >= 0.3])
    peak_at_fa = psd[np.argmin(np.abs(freq - f_a))]
    assert 10.0 * np.log10(peak_at_fa / bg) >= EV["d_th_db"]


# -- TC-016 (a): standard-class moire 0-count ----------------------------------


def test_tc016_standard_class_no_residual_moire():
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    out = grid.process(make_frame(img), other_calib((128, 128)), grid_params())
    after = grid.analyze(np.asarray(out.pixel), grid_params())
    # No significant peak anywhere in the search band after suppression.
    assert (not after.detected) or all(
        p.significance_db < EV["residual_db"] for p in after.peaks
    )


# -- TC-016 (b): low-frequency fold -> attenuation cap + replacement warning -----


def test_tc016_lowfreq_fold_caps_attenuation_and_warns():
    # f_grid = 7.0 lp/mm folds to f_a = 0.143/mm (< 0.5 moire cutoff).
    _, img = make_grid_phantom((128, 128), F_GRID_MOIRE, direction="vertical")
    frame = make_frame(img)
    out = grid.process(frame, other_calib((128, 128)), grid_params())
    extra = dict(out.history[-1].extra)
    assert extra["grid_detected"] == "true"
    assert extra["moire_atten_capped"] == "true"
    assert "moire_warning" in extra
    # Under the cap the peak is only partially attenuated (residual characterized,
    # PARTIAL): the frame changed but was not fully nulled.
    assert not np.array_equal(np.asarray(out.pixel), np.asarray(frame.pixel))


# -- TC-016 (c): GLS-failure numerically-identical passthrough ------------------


def test_tc016_no_detection_numerically_identical_passthrough():
    clean, _ = make_grid_phantom((96, 96), F_GRID_BELOW, anatomy=True)
    frame = make_frame(clean)
    out = grid.process(frame, other_calib((96, 96)), grid_params())
    extra = dict(out.history[-1].extra)
    assert extra["grid_detected"] == "false"
    assert extra["grid_undetected"] == "true"
    assert np.array_equal(np.asarray(out.pixel), np.asarray(frame.pixel))
    assert np.array_equal(np.asarray(out.masks), np.asarray(frame.masks))


# -- Scenario 8 (Optional): metadata mismatch warning --------------------------


def test_metadata_mismatch_records_warning():
    # Grid mounted per metadata, but the observed frequency disagrees with the
    # (folded) nominal -> a comparison-only warning, never a search input.
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    params = grid_params(grid_meta_mounted=True, grid_meta_nominal_lpmm=3.4)
    out = grid.process(make_frame(img), other_calib((128, 128)), params)
    extra = dict(out.history[-1].extra)
    assert "metadata_mismatch_warning" in extra


def test_metadata_absent_no_warning():
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    out = grid.process(make_frame(img), other_calib((128, 128)), grid_params())
    assert "metadata_mismatch_warning" not in dict(out.history[-1].extra)
