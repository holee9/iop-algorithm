"""XDET-TC-006/007/008/009 live + Scenario 10 contract + orchestrator chain.

Converts the deferred T3/WP3+WP4 skeletons into working release-gate cases:
synthetic known-distortion injection -> processing -> judgment against externally
injected EV min thresholds (measurement != judgment). TC-008 is a T3 PARTIAL
gate (mask integration / boundary band / no-restoration mechanism); the end-to-
end boundary-artifact-invisible judgment re-runs at T5/T6 (spec decision 4).
"""

from __future__ import annotations

import numpy as np

from common.contract import check_process_contract, run_harness
from common.mask_ops import DefectMorphology, dilate_mask
from common.xframe import HistoryEntry, MaskFlag, new_frame
from dataclasses import replace
from metrics import nps
from modules import defect, gain, geometry, line_noise, offset, saturation
from pipeline.orchestrator import PipelineDefinition, run_pipeline
from tests.modules.phantoms.corrections import (
    defect_calib,
    gain_calib,
    offset_calib,
)
from tests.modules.phantoms.linesat import (
    EV_LNSG,
    dot_centroids,
    geometry_calib,
    line_noise_calib,
    lnsg_params,
    make_grid_phantom,
    make_line_noise_phantom,
    make_structure_phantom,
    max_grid_residual,
    saturation_calib,
)


# ---------------------------------------------------------------------------
# XDET-TC-006: line noise removal judged by metrics.detect_line_noise.
# ---------------------------------------------------------------------------


def test_tc006_line_noise_anomaly_peak_removed():
    ph = make_line_noise_phantom(shape=(128, 128))
    params = lnsg_params()
    before = new_frame(ph.observed)
    after = line_noise.process(before, line_noise_calib(before.shape), params)

    det_before = nps.detect_line_noise([before], params)
    det_after = nps.detect_line_noise([after], params)
    assert det_before.get("row_peak")["detected"]
    assert det_before.get("column_peak")["detected"]
    assert not det_after.get("row_peak")["detected"]
    assert not det_after.get("column_peak")["detected"]


# ---------------------------------------------------------------------------
# XDET-TC-007: structure miscorrection rate vs EV-105 min.
# ---------------------------------------------------------------------------


def test_tc007_structure_miscorrection_rate_within_ev105():
    ph = make_structure_phantom(shape=(128, 128))
    params = lnsg_params()
    tol = params.get("line_noise_miscorr_tol")
    out = line_noise.process(new_frame(ph.observed), line_noise_calib(ph.observed.shape), params)
    corrected = np.asarray(out.pixel, dtype=np.float64)
    truth = np.asarray(ph.structure_true, dtype=np.float64)
    smask = ph.structure_mask
    err = np.abs(corrected[smask] - truth[smask])
    rate = float(np.count_nonzero(err > tol)) / int(np.count_nonzero(smask))
    assert rate <= EV_LNSG["ev105_miscorr_rate_max"], rate


# ---------------------------------------------------------------------------
# XDET-TC-008 (T3 partial gate): saturation mask integration + band + no-restore.
# ---------------------------------------------------------------------------


def test_tc008_saturation_partial_gate():
    shape = (48, 48)
    s_th = 60000.0
    raw = np.full(shape, 3000.0, dtype=np.float32)
    raw[20:26, 22:28] = 64000.0
    params = lnsg_params(raw_saturation_threshold=s_th)

    after_offset = offset.process(new_frame(raw), offset_calib(np.full(shape, 40.0)), params)
    offset_sat = (np.asarray(after_offset.masks) & int(MaskFlag.SATURATION)) != 0

    out = saturation.process(after_offset, saturation_calib(shape), params)
    out_sat = (np.asarray(out.masks) & int(MaskFlag.SATURATION)) != 0
    out_interp = (np.asarray(out.masks) & int(MaskFlag.INTERPOLATION)) != 0

    # (a) offset-detected SATURATION preserved in full.
    assert np.all(out_sat[offset_sat])
    # (b) boundary band present.
    assert out.history[-1].extra["boundary_band_pixels"] > 0
    # (c) no restoration: values unchanged, no new INTERPOLATION.
    assert np.array_equal(np.asarray(out.pixel), np.asarray(after_offset.pixel))
    assert not out_interp.any()


# ---------------------------------------------------------------------------
# XDET-TC-009: geometry residual vs EV-106 min (active) + inactive passthrough.
# ---------------------------------------------------------------------------


def test_tc009_geometry_residual_within_ev106_and_inactive_path():
    params = lnsg_params()
    # Active leg.
    ph = make_grid_phantom(a=6.0, degree=2)
    calib = geometry_calib(ph.observed.shape, ph.coeffs_x, ph.coeffs_y, ph.residual_px)
    out = geometry.process(new_frame(ph.observed), calib, params)
    post = max_grid_residual(dot_centroids(np.asarray(out.pixel)), ph.centers)
    assert post <= EV_LNSG["ev106_residual_px_max"], post

    # Inactive leg (residual < EV-106 min -> passthrough).
    ph2 = make_grid_phantom(a=0.4, degree=2)
    calib2 = geometry_calib(ph2.observed.shape, ph2.coeffs_x, ph2.coeffs_y, ph2.residual_px)
    frame2 = new_frame(ph2.observed)
    out2 = geometry.process(frame2, calib2, params)
    assert out2.history[-1].extra["active"] == "false"
    assert np.array_equal(np.asarray(out2.pixel), np.asarray(frame2.pixel))


# ---------------------------------------------------------------------------
# Scenario 10: common process contract for the three T3 modules + harness.
# ---------------------------------------------------------------------------


def test_scenario10_process_contract_three_modules():
    for module in (line_noise, saturation, geometry):
        assert check_process_contract(module) == ()


def test_scenario10_saturation_harness_full_xframe_match():
    """run_harness full-XFrame comparison against an independent analytic
    expected frame (saturation is deterministic: pixel unchanged, band dilated)."""
    shape = (24, 24)
    pix = np.full(shape, 3000.0, dtype=np.float32)
    masks = np.zeros(shape, dtype=np.uint8)
    masks[8:12, 8:12] = int(MaskFlag.SATURATION)
    frame = new_frame(pix, masks=masks)
    params = lnsg_params(saturation_band_width=2)
    calib = saturation_calib(shape)

    sat = (masks & int(MaskFlag.SATURATION)) != 0
    band = dilate_mask(sat, 2) & ~sat
    exp_masks = masks.copy()
    exp_masks[band] |= int(MaskFlag.SATURATION)
    n_sat = int(np.count_nonzero(sat))
    entry = HistoryEntry(
        "saturation", "1.0.0", params.hash(), calib.calibset_id,
        {
            "saturated_pixels": n_sat,
            "saturated_rate": float(n_sat) / sat.size,
            "boundary_band_pixels": int(np.count_nonzero(band)),
        },
    )
    expected = replace(frame, masks=exp_masks, history=frame.history + (entry,))
    report = run_harness(saturation, frame, calib, params, expected)
    assert report.passed, report.violations


# ---------------------------------------------------------------------------
# Orchestrator integration: full T2+T3 chain on a combined phantom.
# ---------------------------------------------------------------------------


def test_orchestrator_full_chain_offset_to_geometry():
    shape = (120, 120)
    ph = make_line_noise_phantom(shape=shape, background=3000.0)
    o_scalar = 50.0
    # raw = clean + line noise + offset; a small raw-saturated block.
    raw = np.asarray(ph.observed, dtype=np.float64) + o_scalar
    raw[60:64, 70:74] = 64000.0
    frame = new_frame(raw.astype(np.float32))

    morph = np.full(shape, DefectMorphology.NORMAL, dtype=np.int8)
    registry = {
        "offset": offset.process,
        "gain": gain.process,
        "defect": defect.process,
        "line_noise": line_noise.process,
        "saturation": saturation.process,
        "geometry": geometry.process,
    }
    cx = np.zeros((3, 3)); cy = np.zeros((3, 3))  # zero distortion, inactive
    calib_map = {
        "offset": offset_calib(np.full(shape, o_scalar)),
        "gain": gain_calib(np.full(shape, 1.0)),
        "defect": defect_calib(morph),
        "line_noise": line_noise_calib(shape),
        "saturation": saturation_calib(shape),
        "geometry": geometry_calib(shape, cx, cy, 0.1),  # residual < EV-106 min
    }
    params = lnsg_params(raw_saturation_threshold=60000.0)
    params_map = {s: params for s in registry}

    out = run_pipeline(
        frame,
        PipelineDefinition(
            ("offset", "gain", "defect", "line_noise", "saturation", "geometry")
        ),
        registry,
        calib_map,
        params_map,
        panel_id="PANEL-A",
    )

    # Six stages recorded in canonical order.
    assert [h.module_name for h in out.history[-6:]] == [
        "offset", "gain", "defect", "line_noise", "saturation", "geometry",
    ]
    # Raw-saturated block flagged and preserved through the chain.
    sat = (np.asarray(out.masks) & int(MaskFlag.SATURATION)) != 0
    assert sat[60:64, 70:74].all()
    # Geometry inactive -> passthrough recorded.
    assert out.history[-1].extra["active"] == "false"
    # Line noise removed: row/column banding variance collapses on the region
    # away from the raw-saturated block (which would otherwise dominate the
    # detector's mean profile -- the block is legitimately preserved, not line
    # noise). Compare input vs output profile variance on the clean sub-region.
    corr = np.asarray(out.pixel, dtype=np.float64)[:, :60]
    before = np.asarray(frame.pixel, dtype=np.float64)[:, :60]
    assert float(np.var(corr.mean(axis=1))) < 0.05 * float(
        np.var(before.mean(axis=1))
    )
