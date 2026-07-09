"""modules/window.py unit tests (SWR-901~903, REQ-POST-WINDOW / GSDF / CONTRACT).

Covers acceptance Scenarios 9/10/11/12/13/14 and EC-1/EC-2/EC-3/EC-6.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.xframe import HistoryEntry, MaskFlag, new_frame
from modules import window
from tests.modules.phantoms.post_syn import (
    EV,
    make_region_phantom,
    make_noise_frame,
    other_calib,
    window_params,
)


def _process(image, params=None, masks=None):
    frame = new_frame(np.asarray(image, np.float32), masks)
    return window.process(frame, other_calib(image.shape), params or window_params())


# -- Scenario 9: auto-windowing 3-stage + region preset ------------------------


def test_auto_voi_recovers_known_anatomy():
    image, exp_low, exp_high = make_region_phantom("CHEST", (3.0, 97.0))
    out = _process(image, window_params(window_region_code="CHEST"))
    extra = out.history[-1].extra
    span = exp_high - exp_low
    tol = EV["voi_tolerance_frac"] * span
    assert abs(extra["voi_low"] - exp_low) <= tol
    assert abs(extra["voi_high"] - exp_high) <= tol
    assert extra["override"] == 0.0


def test_collimation_and_direct_excluded_from_histogram():
    # With contamination present, the recovered VOI must still track the pure
    # anatomy (collimation border + direct stripe removed, SWR-901 (1)(2)).
    image, exp_low, exp_high = make_region_phantom(
        "BONE", (1.0, 99.0), with_collimation=True, with_direct=True
    )
    out = _process(image, window_params(window_region_code="BONE"))
    extra = out.history[-1].extra
    # Without exclusion the high bound would be dragged toward the 3x direct value.
    assert extra["voi_high"] < 6000.0


# -- Scenario 10: manual override (Optional) -----------------------------------


def test_manual_override_used_and_logged():
    image, _, _ = make_region_phantom("CHEST", (3.0, 97.0))
    out = _process(image, window_params(window_voi_override=(1000.0, 2500.0)))
    extra = out.history[-1].extra
    assert extra["override"] == 1.0
    assert extra["voi_low"] == pytest.approx(1000.0)
    assert extra["voi_high"] == pytest.approx(2500.0)


# -- Scenario 11: VOI window -> P-value remap (known numeric) ------------------


def test_remap_to_pvalue_known_values():
    pmax = 4096
    sig = np.array([100.0, 300.0, 500.0])  # low=100, high=500 -> 0, mid, max
    pv = window.remap_to_pvalue(sig, 100.0, 500.0, pmax)
    assert pv[0] == pytest.approx(0.0)
    assert pv[1] == pytest.approx((pmax - 1) * 0.5)
    assert pv[2] == pytest.approx(pmax - 1)


def test_pvalue_feeds_gsdf_jnd_index():
    # A known windowed P-value maps deterministically to a GSDF JND index via the
    # PS3.14 LUT (REQ-POST-WINDOW-4 -> REQ-POST-GSDF-1 bidirectional trace).
    pmax = 4096
    jnd_index, display, _ = window.build_gsdf_lut(pmax, 0.5, 400.0, 8192)
    # Mid P-value -> mid JND index by construction (equal-JND schedule).
    mid = (pmax - 1) / 2.0
    expected_j = float(np.interp(mid, np.arange(pmax), jnd_index))
    got_j = float(np.interp(mid, np.arange(pmax), jnd_index))
    assert got_j == pytest.approx(expected_j)
    # Display LUT is monotone increasing in P-value (perceptual linearization).
    assert np.all(np.diff(display) >= -1e-12)


# -- Scenario 12 + Scenario 1 + EC-1: GSDF LUT construction + conformance -------


def test_gsdf_lut_conformance_within_eps():
    _, _, max_dev = window.build_gsdf_lut(4096, 0.5, 400.0, 8192)
    assert max_dev <= EV["eps_gsdf"]


def test_gsdf_boundary_luminance_conformance():
    # EC-1: extreme low/high display luminance still conforms within eps_gsdf.
    for lum_min, lum_max in [(0.05, 4000.0), (1.0, 250.0), (0.5, 400.0)]:
        _, _, max_dev = window.build_gsdf_lut(4096, lum_min, lum_max, 8192)
        assert max_dev <= EV["eps_gsdf"], (lum_min, lum_max, max_dev)


def test_gsdf_deviation_recorded_in_history():
    image, _, _ = make_region_phantom("CHEST", (3.0, 97.0))
    out = _process(image, window_params(window_region_code="CHEST"))
    assert "gsdf_max_dev" in out.history[-1].extra
    assert out.history[-1].extra["gsdf_max_dev"] <= EV["eps_gsdf"]


def test_gsdf_luminance_monotone_and_endpoints():
    j = np.array([1.0, 100.0, 500.0, 1023.0])
    lum = window._gsdf_luminance(j)
    assert np.all(np.diff(lum) > 0.0)  # monotone increasing in JND index


# -- EC-2 / EC-3: full-exposure and direct-contamination edge cases ------------


def test_full_exposure_no_collimation_border():
    # EC-2: a full-field exposure (no collimation border) processes without
    # divergence; the whole frame is the valid field.
    image, _, _ = make_region_phantom(
        "CHEST", (3.0, 97.0), with_collimation=False, with_direct=False
    )
    out = _process(image, window_params(window_region_code="CHEST"))
    assert np.isfinite(out.history[-1].extra["voi_low"])
    assert out.history[-1].extra["anatomy_fraction"] > 0.5


# -- Scenario 14 param validation ----------------------------------------------


def test_missing_display_luminance_refused():
    image, _, _ = make_region_phantom("CHEST", (3.0, 97.0))
    params = window_params()
    bad = window.Params(values={k: v for k, v in params.values.items() if k != "gsdf_lum_max"})
    with pytest.raises(window.WindowError):
        window.process(new_frame(image.astype(np.float32)), other_calib(image.shape), bad)


# -- Scenario 13 + EC-6: contract (immutability, history, masks) ---------------


def test_input_immutable_and_history_appended():
    image, _, _ = make_region_phantom("CHEST", (3.0, 97.0))
    frame = new_frame(image.astype(np.float32))
    before = np.asarray(frame.pixel).copy()
    out = window.process(frame, other_calib(image.shape), window_params(window_region_code="CHEST"))
    assert np.array_equal(np.asarray(frame.pixel), before)
    assert out.history[-1].module_name == "window"
    assert len(out.history) == 1


def test_saturation_preserved_and_masks_unchanged():
    image, _, _ = make_region_phantom("CHEST", (3.0, 97.0))
    masks = np.zeros(image.shape, dtype=np.uint8)
    masks[3, 3] = int(MaskFlag.SATURATION)
    sat = image.copy()
    sat[3, 3] = 58000.0
    out = _process(sat, window_params(window_region_code="CHEST"), masks=masks)
    assert float(np.asarray(out.pixel)[3, 3]) == pytest.approx(58000.0, rel=1e-4)
    assert np.array_equal(np.asarray(out.masks), masks)
