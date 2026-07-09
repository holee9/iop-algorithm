"""Unit tests for modules.virtual_grid (SKS scatter correction, SPEC-VGRID-001).

Covers the estimation (REQ-VGRID-ESTIMATE), subtraction (REQ-VGRID-SUBTRACT),
kernel-source (REQ-VGRID-CALIB), and module-contract (REQ-VGRID-CONTRACT)
requirements at the module level. The CNR hard DoD (XDET-TC-017) and orchestrator
integration live in test_tc_virtual_grid.py and tests/pipeline respectively.
"""

from __future__ import annotations

import numpy as np
import pytest

from common import pyramid
from common.calibset import CalibKind, K_SCATTER_AMP, K_SCATTER_SIGMA
from common.contract import Params
from common.xframe import MaskFlag, new_frame
from modules import virtual_grid as vg
from tests.modules.phantoms.scatter_syn import (
    EV,
    KERNEL_AMP,
    KERNEL_SIGMA_DOWN,
    make_frame,
    make_lowsignal_phantom,
    make_smooth_scatter_phantom,
    scatter_calib,
    vgrid_params,
)

SHAPE = (96, 96)


# -- REQ-VGRID-ESTIMATE --------------------------------------------------------


def test_scatter_estimate_matches_injected_within_tolerance():
    """Scenario 2: Ŝ recovers the injected S_inj within the external [T] tol."""
    _, observed, s_inj = make_smooth_scatter_phantom(SHAPE)
    s_hat = vg.estimate_scatter(observed, KERNEL_AMP, KERNEL_SIGMA_DOWN, 3, 3)
    rel_err = float(np.linalg.norm(s_hat - s_inj) / np.linalg.norm(s_inj))
    assert rel_err <= EV["scatter_rel_err_tol"]


def test_downsample_reuses_pyramid_reduce_once():
    """Scenario 4: the x8 downsample reuses common.pyramid.reduce_once (SWR-000-9),
    not a module-internal downsampler."""
    img = np.asarray(make_smooth_scatter_phantom(SHAPE)[1], dtype=np.float64)
    expected = img
    for _ in range(3):
        expected = pyramid.reduce_once(expected)
    assert vg._downsample(img, 3).shape == expected.shape
    np.testing.assert_allclose(vg._downsample(img, 3), expected)


def test_iterations_param_is_honored():
    """The SKS iteration count comes from Params (2..3), not a hardcoded value."""
    _, observed, _ = make_smooth_scatter_phantom(SHAPE)
    s2 = vg.estimate_scatter(observed, KERNEL_AMP, KERNEL_SIGMA_DOWN, 2, 3)
    s3 = vg.estimate_scatter(observed, KERNEL_AMP, KERNEL_SIGMA_DOWN, 3, 3)
    # Different iteration counts produce different (converging) estimates.
    assert not np.allclose(s2, s3)


def test_high_spr_iteration_is_stable():
    """EC-1: a high-SPR (0.6) kernel converges without divergence/over-subtraction."""
    _, observed, _ = make_smooth_scatter_phantom(SHAPE)
    s_hat = vg.estimate_scatter(observed, KERNEL_AMP, KERNEL_SIGMA_DOWN, 3, 3)
    assert np.all(np.isfinite(s_hat))
    # Scatter estimate stays a modest fraction of the signal (no runaway growth).
    assert float(np.max(np.abs(s_hat))) < float(np.max(np.abs(observed)))


# -- REQ-VGRID-SUBTRACT --------------------------------------------------------


def test_output_is_non_negative():
    """Scenario 3 / SUBTRACT-3: no output pixel is a negative X-ray signal."""
    observed, _ = make_lowsignal_phantom(SHAPE)
    out = vg.process(make_frame(observed), scatter_calib(SHAPE), vgrid_params())
    assert float(np.asarray(out.pixel).min()) >= 0.0


def test_lowsignal_weight_attenuates_toward_zero_signal():
    """SUBTRACT-2: the effective weight ramps down in low-signal regions and is
    continuous across the threshold (EC-3)."""
    signal = np.linspace(0.0, 200.0, 201)
    w_eff = vg._lowsignal_weight(signal, w=1.0, threshold=50.0, softness=30.0)
    assert w_eff[0] < 0.1  # near-zero signal -> attenuated
    assert w_eff[-1] > 0.9  # bright signal -> ~full weight
    assert np.all(np.diff(w_eff) >= 0.0)  # monotone, no discontinuity
    assert np.all(np.abs(np.diff(w_eff)) < 0.05)  # smooth (no jump)


def test_lowsignal_region_noise_not_boosted():
    """Scenario 3 / VALIDATE-4: low-signal region noise does not grow beyond the
    external tolerance after correction (w auto-attenuation)."""
    observed, lowsig = make_lowsignal_phantom(SHAPE)
    out = vg.process(make_frame(observed), scatter_calib(SHAPE), vgrid_params())
    before = float(np.std(observed[lowsig]))
    after = float(np.std(np.asarray(out.pixel, dtype=np.float64)[lowsig]))
    assert after <= before * (1.0 + EV["lowsignal_noise_boost_tol"])


def test_bilinear_upsample_matches_target_shape():
    """SUBTRACT-1: bilinear upsample restores the exact input resolution."""
    small = np.arange(12 * 12, dtype=np.float64).reshape(12, 12)
    up = vg._bilinear_upsample(small, (96, 96))
    assert up.shape == (96, 96)
    assert np.all(np.isfinite(up))


def test_weight_sourced_from_params_scales_subtraction():
    """SUBTRACT-1: a larger grid-ratio weight w removes more scatter (w is Params)."""
    _, observed, _ = make_smooth_scatter_phantom(SHAPE)
    frame = make_frame(observed)
    calib = scatter_calib(SHAPE)
    low = vg.process(frame, calib, vgrid_params(vgrid_grid_ratio_w=0.5))
    high = vg.process(frame, calib, vgrid_params(vgrid_grid_ratio_w=1.5))
    # Stronger weight subtracts more -> lower mean output.
    assert float(np.asarray(high.pixel).mean()) < float(np.asarray(low.pixel).mean())


# -- REQ-VGRID-CALIB (no-silent-default REJECT) --------------------------------


def test_missing_kernel_payload_rejected():
    """Scenario 6 / CALIB-2: absent kernel payload is refused, no default kernel."""
    bad = scatter_calib(SHAPE, data={})
    with pytest.raises(vg.VirtualGridError, match="missing"):
        vg.process(make_frame(make_smooth_scatter_phantom(SHAPE)[1]), bad, vgrid_params())


def test_degenerate_kernel_nonfinite_rejected():
    """EC-2: a non-finite kernel coefficient is refused (no substitution)."""
    bad = scatter_calib(
        SHAPE,
        data={
            K_SCATTER_AMP: np.array([np.nan, 0.3]),
            K_SCATTER_SIGMA: np.array([1.0, 3.0]),
        },
    )
    with pytest.raises(vg.VirtualGridError, match="degenerate"):
        vg.process(make_frame(make_smooth_scatter_phantom(SHAPE)[1]), bad, vgrid_params())


def test_diverging_spr_kernel_rejected():
    """EC-2: an SPR >= 1 kernel (would diverge the SKS iteration) is refused."""
    bad = scatter_calib(
        SHAPE,
        data={
            K_SCATTER_AMP: np.array([0.6, 0.6]),  # SPR 1.2 >= 1
            K_SCATTER_SIGMA: np.array([1.0, 3.0]),
        },
    )
    with pytest.raises(vg.VirtualGridError, match="SPR"):
        vg.process(make_frame(make_smooth_scatter_phantom(SHAPE)[1]), bad, vgrid_params())


def test_empty_sigma_arity_rejected():
    """EC-2: a wrong-arity kernel (not exactly 2 Gaussians) is refused."""
    bad = scatter_calib(
        SHAPE,
        data={
            K_SCATTER_AMP: np.array([0.3, 0.3, 0.3]),
            K_SCATTER_SIGMA: np.array([1.0, 3.0, 5.0]),
        },
    )
    with pytest.raises(vg.VirtualGridError, match="degenerate"):
        vg.process(make_frame(make_smooth_scatter_phantom(SHAPE)[1]), bad, vgrid_params())


# -- REQ-VGRID-CONTRACT --------------------------------------------------------


def test_input_frame_is_immutable():
    """CONTRACT-1: the input XFrame pixel buffer is not mutated."""
    observed = make_smooth_scatter_phantom(SHAPE)[1]
    frame = make_frame(observed)
    before = np.asarray(frame.pixel).copy()
    vg.process(frame, scatter_calib(SHAPE), vgrid_params())
    np.testing.assert_array_equal(np.asarray(frame.pixel), before)


def test_history_records_diagnostics():
    """CONTRACT-2: history carries meta + scalar diagnostics incl. ⚠P provenance."""
    out = vg.process(
        make_frame(make_smooth_scatter_phantom(SHAPE)[1]), scatter_calib(SHAPE), vgrid_params()
    )
    entry = out.history[-1]
    assert entry.module_name == "virtual_grid"
    extra = entry.extra
    for key in (
        "iterations",
        "grid_ratio_w",
        "scatter_fraction",
        "lowsignal_attenuated_fraction",
        "nonneg_clamp_count",
        "sks_patent_flag",
        "kernel_provenance",
    ):
        assert key in extra
    assert "US11911202" in str(extra["sks_patent_flag"])  # patent flag preserved


def test_mask_substrate_unchanged_and_no_restoration():
    """EC-6 / CONTRACT-6: no mask flag is set or cleared; saturated pixels are not
    restored (their value is not reconstructed upward)."""
    observed = np.full(SHAPE, 1500.0, dtype=np.float32)
    masks = np.zeros(SHAPE, dtype=np.uint8)
    masks[10:14, 10:14] = np.uint8(MaskFlag.SATURATION)
    frame = new_frame(observed, masks)
    out = vg.process(frame, scatter_calib(SHAPE), vgrid_params())
    np.testing.assert_array_equal(np.asarray(out.masks), np.asarray(frame.masks))
    # Subtraction is monotone-down (never restores clipped-away signal upward).
    assert float(np.asarray(out.pixel).max()) <= float(np.asarray(frame.pixel).max()) + 1e-3


def test_masked_pixels_do_not_contaminate_estimate():
    """EC-5: masked (defect) pixel values are filled before estimation so an
    extreme value does not pollute the low-frequency scatter estimate."""
    observed = np.full(SHAPE, 1000.0, dtype=np.float64)
    valid = np.ones(SHAPE, dtype=bool)
    valid[48, 48] = False
    contaminated = observed.copy()
    contaminated[48, 48] = 1e6  # extreme defect value
    filled = vg._fill_masked(contaminated, valid)
    assert filled[48, 48] == pytest.approx(1000.0)


def test_validation_mode_float64_buffer_processed():
    """CONTRACT-1: the validation-mode float64 parallel buffer is also corrected."""
    observed = make_smooth_scatter_phantom(SHAPE)[1]
    frame = new_frame(np.asarray(observed, dtype=np.float32), validation_mode=True)
    out = vg.process(frame, scatter_calib(SHAPE), vgrid_params())
    assert out.pixel_f64 is not None
    assert np.all(np.isfinite(np.asarray(out.pixel_f64)))
