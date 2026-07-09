"""XDET-TC-012/013/014 live release gates for T6/WP6+WP7 (SPEC-POST-001).

Converts the deferred T6 skeletons into working gate cases (measurement !=
judgment: EV / eps_gsdf thresholds are external-injected; computed values come
from the module + the T1 MTF engine + PS3.14 known-value comparison).

- XDET-TC-014 (hard DoD): GSDF LUT PS3.14 conformance — per-JND contrast-response
  deviation <= eps_gsdf, deterministic binary gate across display characteristics.
- XDET-TC-013 (PARTIAL): auto-window fit rate on known-VOI region phantoms >=
  EV-205 min (unattended-acceptance surrogate; real observer acceptance deferred).
- XDET-TC-012 (PARTIAL): MSE/DRC IQA surrogate non-degradation vs a committed
  baseline snapshot (absolute IQA thresholds + EV-102 MTF guardrail pre-passed
  before the snapshot was committed) + MTF@Nyquist retention >= EV-102 min.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from common import pyramid
from common.xframe import new_frame
from metrics import mtf
from modules import mse, window
from tests.metrics.phantoms.params import make_params
from tests.modules.phantoms.post_syn import (
    EV,
    make_bone_soft_phantom,
    make_noise_frame,
    make_region_phantom,
    make_slanted_edge,
    mse_params,
    other_calib,
    window_params,
)

_SNAPSHOT = Path(__file__).resolve().parents[1] / "fixtures" / "post_tc012_baseline.json"


# ===================== XDET-TC-014: GSDF PS3.14 (hard DoD) =====================


def test_tc014_gsdf_conformance_within_eps():
    """Hard DoD: per-JND contrast-response deviation <= eps_gsdf (PS3.14)."""
    _, _, max_dev = window.build_gsdf_lut(4096, 0.5, 400.0, 8192)
    assert max_dev <= EV["eps_gsdf"], max_dev


def test_tc014_gsdf_conformance_over_display_range():
    """EC-1: conformance holds across extreme display luminance characteristics."""
    for lum_min, lum_max in [(0.05, 4000.0), (1.0, 500.0), (0.2, 250.0)]:
        _, _, max_dev = window.build_gsdf_lut(4096, lum_min, lum_max, 8192)
        assert max_dev <= EV["eps_gsdf"], (lum_min, lum_max, max_dev)


def test_tc014_eps_gsdf_is_external():
    """eps_gsdf is injected by the test harness, never embedded in the module."""
    src = (Path(window.__file__)).read_text(encoding="utf-8")
    assert "eps_gsdf" not in src


# ===================== XDET-TC-013: auto-window fit rate =======================

# A set of known-VOI region phantoms across regions, seeds, and contamination.
_REGION_CASES = [
    ("CHEST", (3.0, 97.0), True, True, 20),
    ("CHEST", (3.0, 97.0), True, False, 21),
    ("BONE", (1.0, 99.0), True, True, 22),
    ("BONE", (1.0, 99.0), False, True, 23),
    ("CHEST", (3.0, 97.0), False, False, 24),
    ("BONE", (1.0, 99.0), True, True, 25),
]


def _window_fit(region, voi_pct, collim, direct, seed):
    image, exp_low, exp_high = make_region_phantom(
        region, voi_pct, with_collimation=collim, with_direct=direct, seed=seed
    )
    out = window.process(
        new_frame(image.astype(np.float32)),
        other_calib(image.shape),
        window_params(window_region_code=region),
    )
    extra = out.history[-1].extra
    span = exp_high - exp_low
    tol = EV["voi_tolerance_frac"] * span
    return (
        abs(extra["voi_low"] - exp_low) <= tol
        and abs(extra["voi_high"] - exp_high) <= tol
    )


def test_tc013_window_fit_rate_meets_ev205():
    """PARTIAL: fraction of phantoms whose auto VOI lands within tolerance of the
    known VOI (unattended-acceptance surrogate) >= EV-205 min."""
    hits = [_window_fit(*case) for case in _REGION_CASES]
    fit_rate = float(np.mean(hits))
    assert fit_rate >= EV["ev205_window_fit_min"], (fit_rate, hits)


# ===================== XDET-TC-012: MSE/DRC IQA non-degradation ================


def _iqa_metrics():
    """Objective IQA surrogates for the MSE/DRC output on a fixed phantom."""
    clean, noisy = make_bone_soft_phantom(shape=(96, 96), detail_amp=400.0, seed=11)
    out = mse.process(make_noise_frame(noisy), other_calib(noisy.shape), mse_params())
    op = np.asarray(out.pixel, np.float64)

    # Local contrast gain: RMS of the Laplacian (detail) of the scale-normalized
    # output vs the scale-normalized noisy input.
    def _detail_rms(a):
        a = (a - a.mean()) / a.std()
        bands = pyramid.build_pyramid(a, 3)[:-1]
        return float(np.sqrt(np.mean([np.mean(b**2) for b in bands])))

    local_contrast_gain = _detail_rms(op) / _detail_rms(np.asarray(noisy, np.float64))

    # Structural detail-energy retention (above-noise, measured on clean output).
    out_clean = mse.process(
        make_noise_frame(clean), other_calib(clean.shape), mse_params()
    )
    oc = np.asarray(out_clean.pixel, np.float64)
    oc = (oc - oc.mean()) / oc.std()
    cn = (clean - clean.mean()) / clean.std()
    e_in = sum(float(np.sum(b**2)) for b in pyramid.build_pyramid(cn, 3)[:-1])
    e_out = sum(float(np.sum(b**2)) for b in pyramid.build_pyramid(oc, 3)[:-1])
    detail_energy_retention = e_out / e_in

    clip_fraction = float(np.mean((op <= 0.0) | (op >= 1.0)))
    return {
        "local_contrast_gain": local_contrast_gain,
        "detail_energy_retention": detail_energy_retention,
        "clip_fraction": clip_fraction,
    }


def _mtf_retention():
    clean, noisy = make_slanted_edge((128, 128), slope=0.05, seed=12)
    out = mse.process(make_noise_frame(noisy), other_calib(noisy.shape), mse_params())
    band = (slice(16, 112), slice(52, 76))
    mp = make_params()
    out_band = np.asarray(out.pixel, np.float64)[band]
    clean_band = clean[band]
    m_out = mtf.compute_mtf(new_frame(out_band.astype(np.float32)), mp).get("mtf_at_nyquist")
    m_clean = mtf.compute_mtf(new_frame(clean_band.astype(np.float32)), mp).get("mtf_at_nyquist")
    return float(m_out / m_clean)


def test_tc012_iqa_absolute_thresholds():
    """PARTIAL leg (a): objective IQA surrogates meet the injected ABSOLUTE
    thresholds (the pre-condition that gated the baseline-snapshot commit)."""
    iqa = _iqa_metrics()
    assert iqa["local_contrast_gain"] >= EV["local_contrast_min_gain"], iqa
    assert iqa["detail_energy_retention"] >= EV["detail_energy_retention_min"], iqa
    assert iqa["clip_fraction"] <= EV["clip_fraction_max"], iqa


def test_tc012_mtf_guardrail_meets_ev102():
    """PARTIAL leg (b): MTF@Nyquist retention through MSE >= EV-102 min guardrail."""
    retention = _mtf_retention()
    assert retention >= EV["ev102_mtf_retention_min"], retention


def test_tc012_no_regression_vs_baseline_snapshot():
    """PARTIAL: IQA surrogates are non-degraded vs the committed baseline snapshot
    (regression-only after the absolute-threshold + MTF-guardrail pre-pass)."""
    assert _SNAPSHOT.exists(), (
        f"missing baseline snapshot {_SNAPSHOT}; generate it once after the "
        f"absolute IQA thresholds + EV-102 guardrail pass (decision 6)"
    )
    baseline = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    iqa = _iqa_metrics()
    margin = 1e-6  # deterministic; only true degradation should trip this
    assert iqa["local_contrast_gain"] >= baseline["local_contrast_gain"] - margin
    assert (
        iqa["detail_energy_retention"]
        >= baseline["detail_energy_retention"] - margin
    )
    assert iqa["clip_fraction"] <= baseline["clip_fraction"] + margin
