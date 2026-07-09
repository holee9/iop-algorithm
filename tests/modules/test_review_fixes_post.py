"""Regression tests for the 10 verified code-review defects in the T6 post
modules (SPEC-POST-001, commit ec9c7c0). One test (or small group) per finding.

Defects 1 (saturation output-domain preservation) are additionally covered by the
updated assertions in tests/modules/test_mse.py and test_window.py; the remaining
findings get dedicated regressions here.
"""

from __future__ import annotations

import numpy as np
import pytest

from common import histogram_fov, pyramid
from common.xframe import MaskFlag, NoiseModel, XFrame, new_frame
from modules import mse, window
from pipeline.orchestrator import (
    CANONICAL_ORDER,
    CalibrationError,
    PipelineDefinition,
    run_pipeline,
)
from tests.modules.phantoms.post_syn import (
    ALPHA,
    SIGMA,
    full_calib_map,
    make_bone_soft_phantom,
    make_noise_frame,
    make_region_phantom,
    mse_params,
    other_calib,
    window_params,
)


# =========================== [1] saturation output-domain =====================


def test_defect1_mse_saturation_is_domain_max():
    _, noisy = make_bone_soft_phantom()
    masks = np.zeros(noisy.shape, dtype=np.uint8)
    masks[7, 7] = int(MaskFlag.SATURATION)
    sat = noisy.copy()
    sat[7, 7] = 60000.0
    out = mse.process(make_noise_frame(sat, masks), other_calib(sat.shape), mse_params())
    op = np.asarray(out.pixel, np.float64)
    assert op[7, 7] == pytest.approx(1.0)  # domain max, not 60000
    assert op.max() <= 1.0


def test_defect1_window_saturation_is_display_max():
    image, _, _ = make_region_phantom("CHEST", (3.0, 97.0))
    masks = np.zeros(image.shape, dtype=np.uint8)
    masks[2, 2] = int(MaskFlag.SATURATION)
    sat = image.copy()
    sat[2, 2] = 61000.0
    params = window_params(window_region_code="CHEST")
    out = window.process(
        new_frame(sat.astype(np.float32), masks), other_calib(sat.shape), params
    )
    _, lut_display, _ = window.build_gsdf_lut(
        params.get("window_pvalue_levels"), params.get("gsdf_lum_min"),
        params.get("gsdf_lum_max"), params.get("gsdf_jnd_grid_size"),
    )
    assert float(np.asarray(out.pixel)[2, 2]) == pytest.approx(float(lut_display[-1]))


# =========================== [2] empty anatomy fallback =======================


def test_defect2_all_direct_exposure_falls_back_to_fov_loudly():
    # A perfectly uniform bright field: collimation detect -> whole field; the
    # direct-exposure fence (median + k*MAD, MAD=0) excludes every field pixel
    # (arr < median is empty) -> anatomy empty. The VOI must fall back to the FOV
    # and RECORD it (voi_source=1.0 "fov"), never silently pool the whole image.
    image = np.full((64, 64), 50000.0, dtype=np.float32)
    out = window.process(
        new_frame(image), other_calib(image.shape),
        window_params(window_region_code="CHEST"),
    )
    extra = out.history[-1].extra
    assert extra["voi_source"] == 1.0  # fov fallback recorded (loud)
    assert np.isfinite(extra["voi_low"]) and np.isfinite(extra["voi_high"])


def test_defect2_empty_field_refused():
    # With no exposed field AND no anatomy, there is no valid signal -> explicit
    # refusal (never a whole-image fallback).
    z = np.zeros((8, 8), dtype=np.float64)
    empty = np.zeros((8, 8), dtype=bool)
    with pytest.raises(window.WindowError, match="empty exposed field"):
        window._resolve_voi(z, empty, empty, window_params())


def test_defect2_anatomy_present_records_anatomy_source():
    image, _, _ = make_region_phantom("CHEST", (3.0, 97.0))
    out = window.process(
        new_frame(image.astype(np.float32)), other_calib(image.shape),
        window_params(window_region_code="CHEST"),
    )
    assert out.history[-1].extra["voi_source"] == 0.0  # anatomy


# =========================== [3] correlated-noise propagation =================


def test_defect3_band_noise_gains_match_measured_std():
    # White noise -> the propagated per-level Laplacian-band variance must match the
    # empirically measured band variance within a few % at ALL levels; the old
    # independent-noise model (sum(k^2)^k) diverges badly at coarse levels.
    shape = (384, 384)
    levels = 6
    gains = pyramid.laplacian_band_noise_gains(shape, levels)

    acc = np.zeros(levels)
    trials = 4
    for s in range(trials):
        rng = np.random.default_rng(100 + s)
        x = rng.normal(size=shape)
        pyr = pyramid.build_pyramid(x, levels)
        for k, band in enumerate(pyr[:-1]):
            ny, nx = band.shape
            interior = band[ny // 4 : 3 * ny // 4, nx // 4 : 3 * nx // 4]
            acc[k] += float(np.var(interior))
    measured = acc / trials

    ratio = np.array(gains) / measured
    assert np.all(np.abs(ratio - 1.0) < 0.10), (gains, measured.tolist())

    # The naive model is materially worse at the coarsest level (regression guard).
    k1d = np.array([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0
    naive = (float(np.sum(k1d**2)) ** 2) ** (levels - 1)
    assert abs(gains[-1] / measured[-1] - 1.0) < abs(naive / measured[-1] - 1.0)


# =========================== [4] multi-level DRC ==============================


def _coarse_fine_ratio(image: np.ndarray) -> float:
    a = (image - image.mean()) / (image.std() + 1e-12)
    bands = pyramid.build_pyramid(a, 4)
    fine = float(np.std(bands[0]))
    coarse = float(np.std(bands[-2])) + float(np.std(bands[-1]))
    return coarse / (fine + 1e-12)


def test_defect4_drc_compresses_multilevel_gradient():
    # A large-scale gradient lives in the COARSE detail levels, not only the
    # residual. Residual-only DRC would leave it uncompressed; the multi-level base
    # must compress it -> the coarse/fine energy ratio drops under compression and
    # drops further as more top levels are folded into B.
    ny, nx = 96, 96
    ys, xs = np.mgrid[0:ny, 0:nx]
    grad = 500.0 + 2500.0 * (xs / (nx - 1))
    rng = np.random.default_rng(7)
    noisy = (grad + rng.normal(0.0, 5.0, size=(ny, nx))).astype(np.float32)

    def ratio(**ov):
        out = mse.process(
            make_noise_frame(noisy), other_calib(noisy.shape), mse_params(**ov)
        )
        return _coarse_fine_ratio(np.asarray(out.pixel, np.float64))

    no_compress = ratio(mse_drc_gamma=1.0, mse_drc_low_levels=2)
    k1 = ratio(mse_drc_gamma=0.3, mse_drc_low_levels=1)
    k3 = ratio(mse_drc_gamma=0.3, mse_drc_low_levels=3)
    assert k1 < no_compress            # compression reduces coarse contribution
    assert k3 < k1                     # folding more top levels compresses more


def test_defect4_drc_low_levels_recorded():
    _, noisy = make_bone_soft_phantom()
    out = mse.process(
        make_noise_frame(noisy), other_calib(noisy.shape),
        mse_params(mse_drc_low_levels=3),
    )
    assert out.history[-1].extra["drc_low_levels"] == 3.0


# =========================== [5] bimodal collimation threshold ================


def test_defect5_border_dominant_frame_excludes_border():
    # 60%-area collimated border: a median anchor falls INTO the border and fails;
    # the Otsu bright-anchor must still exclude the border and keep the anatomy.
    n = 100
    img = np.full((n, n), 2000.0)
    b = int(n * 0.6 / 2)
    img[:b, :] = img[-b:, :] = img[:, :b] = img[:, -b:] = 80.0
    border = img < 200.0
    field = histogram_fov.detect_collimation_field(img, rel_threshold=0.2)
    assert not field[border].any()      # border fully excluded
    assert field[~border].all()         # anatomy fully retained


def test_defect5_full_exposure_stays_all_field():
    ys, xs = np.mgrid[0:96, 0:96]
    grad = 500.0 + 2500.0 * (xs / 95.0)
    field = histogram_fov.detect_collimation_field(grad, rel_threshold=0.2)
    assert field.mean() > 0.99          # unimodal full exposure -> ~all True


# =========================== [6] pyramid level infeasibility ==================


def test_defect6_build_pyramid_rejects_infeasible_levels():
    img = np.zeros((64, 64))
    assert pyramid.max_feasible_levels((64, 64)) == 6
    with pytest.raises(ValueError, match="at most 6"):
        pyramid.build_pyramid(img, levels=7)


def test_defect6_mse_surfaces_infeasible_levels():
    _, noisy = make_bone_soft_phantom(shape=(64, 64))
    with pytest.raises(mse.MseError, match="supports at most"):
        mse.process(
            make_noise_frame(noisy), other_calib(noisy.shape),
            mse_params(mse_levels=7),
        )


# =========================== [7] independent GSDF reference ===================

# DICOM PS3.14 GSDF is DEFINED so that the JND index j runs from 1 to 1023 across
# the luminance range 0.05 .. 4000 cd/m^2 (the tabulated GSDF endpoints). These
# defining anchors are EXTERNAL ground truth independent of the polynomial
# coefficients: a wrong forward map would not reproduce them. This breaks the
# circularity of the module's own inversion-residual self-check (defect 7).
_PS314_ANCHORS = [
    (0.05, 1.0),      # standard minimum: j = 1 at L_min = 0.05 cd/m^2
    (4000.0, 1023.0),  # standard maximum: j = 1023 at L_max = 4000 cd/m^2
]


def test_defect7_forward_polynomial_matches_ps314_anchors():
    # The module's forward GSDF polynomial must reproduce the standard's defining
    # (L, j) endpoints within ~1 JND (independent of its own inverse).
    for lum, j in _PS314_ANCHORS:
        got = float(window._gsdf_jnd_index(lum))
        assert abs(got - j) <= 1.0, (lum, j, got)
    # The full-range JND span must be the standard's 1022 (=1023-1) within tolerance.
    span = float(window._gsdf_jnd_index(4000.0)) - float(window._gsdf_jnd_index(0.05))
    assert abs(span - 1022.0) <= 2.0, span


def test_defect7_lut_roundtrip_monotone_and_inverts():
    jnd, display, _ = window.build_gsdf_lut(4096, 0.5, 400.0, 8192)
    assert np.all(np.diff(jnd) > 0.0)
    assert np.all(np.diff(display) >= -1e-12)
    # Round-trip: L(j) then j(L) recovers the JND index (inverse consistency).
    j_targets = np.array([10.0, 200.0, 800.0])
    lum = window._gsdf_luminance(j_targets)
    assert np.allclose(window._gsdf_jnd_index(lum), j_targets, atol=0.5)


# =========================== [8] full() calib map =============================


def test_defect8_full_run_with_complete_calib_map():
    _, noisy = make_bone_soft_phantom(shape=(64, 64), detail_amp=200.0)
    frame = make_noise_frame(noisy)
    definition = PipelineDefinition.full()
    # Real mse/window; passthrough for the rest (kept minimal, focus on the T6 gate).
    def _passthrough(f, c, p):
        return f
    registry = {s: _passthrough for s in CANONICAL_ORDER}
    registry["mse"] = mse.process
    registry["window"] = window.process
    calib_map = full_calib_map((64, 64))
    params_map = {
        "mse": mse_params(),
        "window": window_params(window_region_code="CHEST"),
    }
    out = run_pipeline(frame, definition, registry, calib_map, params_map)
    names = [h.module_name for h in out.history]
    assert "mse" in names and "window" in names


def test_defect8_full_run_missing_post_calib_refused():
    _, noisy = make_bone_soft_phantom(shape=(64, 64))
    frame = make_noise_frame(noisy)
    definition = PipelineDefinition.full()
    def _passthrough(f, c, p):
        return f
    registry = {s: _passthrough for s in CANONICAL_ORDER}
    registry["mse"] = mse.process
    registry["window"] = window.process
    calib_map = full_calib_map((64, 64))
    del calib_map["window"]  # missing post-stage CalibSet -> refuse at the gate
    with pytest.raises(CalibrationError, match="window"):
        run_pipeline(frame, definition, registry, calib_map,
                     {"mse": mse_params(), "window": window_params()})


# =========================== [9] f32/f64 classification unity =================


def _dual_frame(f32: np.ndarray, f64: np.ndarray, noise=None) -> XFrame:
    base = new_frame(f32.astype(np.float32), noise=noise, validation_mode=True)
    return XFrame(
        pixel=base.pixel, masks=base.masks, noise=base.noise, history=base.history,
        pixel_f64=np.asarray(f64, dtype=np.float64), validation_mode=True,
    )


def test_defect9_window_f64_uses_f32_decision():
    image, _, _ = make_region_phantom("CHEST", (3.0, 97.0))
    perturbed = image.astype(np.float64) * 1.05 + 30.0  # decisions would diverge
    frame = _dual_frame(image, perturbed)
    params = window_params(window_region_code="CHEST")
    out = window.process(frame, other_calib(image.shape), params)
    extra = out.history[-1].extra
    low, high = extra["voi_low"], extra["voi_high"]
    _, lut_display, _ = window.build_gsdf_lut(
        params.get("window_pvalue_levels"), params.get("gsdf_lum_min"),
        params.get("gsdf_lum_max"), params.get("gsdf_jnd_grid_size"),
    )
    # f64 buffer must be the f32 window bounds applied to the f64 pixels.
    pv = window.remap_to_pvalue(perturbed, low, high, params.get("window_pvalue_levels"))
    expected = np.interp(pv, np.arange(len(lut_display)), lut_display)
    assert np.allclose(np.asarray(out.pixel_f64), expected, atol=1e-9)


def test_defect9_mse_f64_uses_f32_decision():
    _, noisy = make_bone_soft_phantom(shape=(64, 64), detail_amp=200.0)
    perturbed = noisy.astype(np.float64) * 1.03 + 20.0
    frame = _dual_frame(noisy, perturbed, noise=NoiseModel(alpha=ALPHA, sigma=SIGMA))
    out = mse.process(frame, other_calib(noisy.shape), mse_params())
    extra = out.history[-1].extra
    # Recompute the f64 output using the AUTHORITATIVE f32 decisions (b_mid, lo, hi).
    decisions = {
        "b_mid": extra["b_mid"],
        "norm_low": extra["norm_low"],
        "norm_high": extra["norm_high"],
    }
    masks_u8 = np.asarray(frame.masks, dtype=np.uint8)
    expected, _ = mse._run(
        perturbed, masks_u8, ALPHA, SIGMA, mse_params(), "power_law", decisions
    )
    assert np.allclose(np.asarray(out.pixel_f64), expected, atol=1e-9)


# =========================== [10] public reduce API ==========================


def test_defect10_reduce_once_is_public_and_used():
    img = np.arange(64, dtype=np.float64).reshape(8, 8)
    assert np.array_equal(pyramid.reduce_once(img), pyramid._reduce(img))
    src = __import__("pathlib").Path(mse.__file__).read_text(encoding="utf-8")
    assert "pyramid._reduce" not in src        # no coupling to the private helper
    assert "pyramid.reduce_once" in src         # uses the public API
