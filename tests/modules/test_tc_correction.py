"""XDET-TC-001/002/003 live: before/after judgment via the T1 metrics engine.

These convert the deferred skeletons into working release-gate cases: synthetic
known-distortion injection -> correction -> metrics-engine before/after judgment
against externally injected EV min thresholds (measurement != judgment).
"""

from __future__ import annotations

import numpy as np

from common.mask_ops import DefectMorphology
from common.xframe import new_frame
from metrics import dqe, mtf, nps
from metrics.defect_stats import DefectClass, classify_defects
from modules import defect, gain, offset
from pipeline.orchestrator import PipelineDefinition, run_pipeline
from tests.metrics.phantoms import generators as gen
from tests.modules.phantoms.corrections import (
    EV,
    corr_params,
    defect_calib,
    gain_calib,
    make_defect_stacks,
    offset_calib,
)
from metrics.defect_map import build_defect_map


def _correct(frame, o_scalar, g_scalar):
    """Apply offset -> gain correction with uniform scalar maps."""
    shape = frame.shape
    p = corr_params()
    f1 = offset.process(frame, offset_calib(np.full(shape, o_scalar)), p)
    return gain.process(f1, gain_calib(np.full(shape, g_scalar)), p)


def _midband(freqs, values, nyq):
    band = (freqs > 0.2 * nyq) & (freqs < 0.8 * nyq)
    return float(np.mean(np.asarray(values)[band]))


# ---------------------------------------------------------------------------
# Orchestrator integration: offset -> gain -> defect via the registry.
# ---------------------------------------------------------------------------


def test_orchestrator_offset_gain_defect_recovers_scene():
    shape = (48, 48)
    r, c = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float64)
    bg = 1000.0 + 5.0 * r + 3.0 * c
    g_scalar, o_scalar = 1.25, 200.0

    morph = np.full(shape, DefectMorphology.NORMAL, dtype=np.int8)
    morph[10, 10] = DefectMorphology.SINGLE
    morph[20, 10:18] = DefectMorphology.LINE
    morph[30:32, 30:32] = DefectMorphology.CLUSTER

    raw = bg / g_scalar + o_scalar
    for (rr, cc) in [(10, 10)] + [(20, cc) for cc in range(10, 18)] + [
        (30, 30), (30, 31), (31, 30), (31, 31)
    ]:
        raw[rr, cc] = 0.0
    frame = new_frame(raw.astype(np.float32))

    registry = {"offset": offset.process, "gain": gain.process, "defect": defect.process}
    calib_map = {
        "offset": offset_calib(np.full(shape, o_scalar)),
        "gain": gain_calib(np.full(shape, g_scalar)),
        "defect": defect_calib(morph),
    }
    params_map = {s: corr_params() for s in ("offset", "gain", "defect")}

    out = run_pipeline(
        frame,
        PipelineDefinition(("offset", "gain", "defect")),
        registry,
        calib_map,
        params_map,
        panel_id="PANEL-A",
    )
    assert np.allclose(out.pixel, bg, atol=2.0)


# ---------------------------------------------------------------------------
# XDET-TC-002: MTF@Nyquist retention after correction.
# ---------------------------------------------------------------------------


def test_tc002_mtf_nyquist_retention():
    edge = gen.make_slanted_edge(shape=(160, 160), angle_deg=2.0, sigma_px=0.6)
    true_frame = edge.frame
    g_scalar, o_scalar = 1.25, 200.0

    distorted = new_frame(
        (np.asarray(true_frame.pixel, dtype=np.float64) / g_scalar + o_scalar).astype(
            np.float32
        )
    )
    corrected = _correct(distorted, o_scalar, g_scalar)

    params = corr_params()
    mtf_true = mtf.compute_mtf(true_frame, params)
    mtf_after = mtf.compute_mtf(corrected, params)
    retention = mtf_after.get("mtf_at_nyquist") / mtf_true.get("mtf_at_nyquist")
    assert retention >= EV["ev102_mtf_retention_min"], retention


# ---------------------------------------------------------------------------
# XDET-TC-001: DQE 3-dose degradation after correction.
# ---------------------------------------------------------------------------


def test_tc001_dqe_three_dose_no_degradation():
    params = corr_params()
    pitch = params.get("pixel_pitch_mm")
    nyq = 1.0 / (2.0 * pitch)
    g_scalar, o_scalar = 1.25, 150.0

    for dose, sigma in (("XN/2", 70.0), ("XN", 50.0), ("2XN", 35.0)):
        true = gen.make_white_noise_frames(
            shape=(512, 512), n_frames=12, sigma=sigma, seed=hash(dose) % 100
        )
        distorted = [
            new_frame(
                (np.asarray(f.pixel, dtype=np.float64) / g_scalar + o_scalar).astype(
                    np.float32
                )
            )
            for f in true.frames
        ]
        corrected = [_correct(f, o_scalar, g_scalar) for f in distorted]

        nnps_true = nps.compute_nps(true.frames, params).get("nnps")
        res_after = nps.compute_nps(corrected, params)
        freqs = res_after.get("frequencies_lpmm")
        nnps_after = res_after.get("nnps")

        ones = np.ones_like(freqs)
        dqe_true = dqe.compute_dqe(freqs, ones, nnps_true, params).get("dqe")
        dqe_after = dqe.compute_dqe(freqs, ones, nnps_after, params).get("dqe")

        mid_true = _midband(freqs, dqe_true, nyq)
        mid_after = _midband(freqs, dqe_after, nyq)
        degrade = abs(mid_after - mid_true) / mid_true
        assert degrade <= EV["ev101_dqe_degrade_max"], (dose, degrade)


# ---------------------------------------------------------------------------
# XDET-TC-003: residual cluster (module) + builder miss-rate (both EV-103 legs).
# ---------------------------------------------------------------------------


def test_tc003_residual_cluster_and_builder_miss_rate():
    stacks = make_defect_stacks(
        singles=((5, 5), (50, 55)),
        lines=((20, 10, 8),),
        clusters=((35, 35, 2, 2),),
    )
    params = corr_params()

    # Builder leg (miss-rate vs ground truth).
    calib = build_defect_map(
        stacks.dark_frames,
        stacks.flat_frames,
        params,
        panel_id="PANEL-A",
        resolution=stacks.planted.shape,
        valid_from="2026-01-01",
        valid_until="2027-01-01",
    )
    morph = np.asarray(calib.data["class_map"])
    detected = morph != DefectMorphology.NORMAL
    missed = int(np.count_nonzero(stacks.planted & ~detected))
    miss_rate = missed / int(np.count_nonzero(stacks.planted))
    assert miss_rate <= EV["ev103_miss_rate_max"], miss_rate

    # Residual-cluster leg: correct the flat stack, re-classify, expect no
    # residual defect at the planted positions.
    corrected_flats = [defect.process(f, calib, params) for f in stacks.flat_frames]
    residual = classify_defects(stacks.dark_frames, corrected_flats, params)
    residual_map = np.asarray(residual.get("class_map"))
    residual_at_planted = int(
        np.count_nonzero((residual_map != DefectClass.GOOD) & stacks.planted)
    )
    assert residual_at_planted <= EV["ev103_residual_cluster_max"], residual_at_planted
