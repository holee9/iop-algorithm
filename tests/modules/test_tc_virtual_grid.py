"""XDET-TC-017 (T8/WP9): kernel virtual-grid SKS scatter-correction release gate.

Hard DoD (Scenario 1, EV-202 min): a synthetic GDS-scatter phantom (known kernel,
known injected veiling) must show a CNR improvement >= +20% after virtual_grid
correction, judged deterministically against the EXTERNALLY-injected EV-202
threshold (measurement != judgment — the module embeds no threshold). Scenario 2
(scatter estimation accuracy) and Scenario 3 (low-signal noise-boost suppression
+ non-negativity) are auxiliary deterministic gates. The EV-202 observer
non-inferiority leg and the "DL scatter deviation vs MC" leg are licensing/Gen2
deferred (PARTIAL), not development gates.

This case was converted from the pytest skeleton (skip) in tests/test_tc_skeletons.py
to a live case (REQ-VGRID-VALIDATE-5).
"""

from __future__ import annotations

import numpy as np

from modules import virtual_grid as vg
from tests.modules.phantoms.scatter_syn import (
    EV,
    KERNEL_AMP,
    KERNEL_SIGMA_DOWN,
    cnr,
    make_cnr_phantom,
    make_frame,
    make_lowsignal_phantom,
    make_smooth_scatter_phantom,
    scatter_calib,
    vgrid_params,
)

SHAPE = (96, 96)


def test_tc017_cnr_improvement_meets_ev202_min():
    """[HARD DoD] CNR improvement after correction >= EV-202 min (+20%)."""
    _, observed, _, feat_roi, bg_roi = make_cnr_phantom(SHAPE)
    out = vg.process(make_frame(observed), scatter_calib(SHAPE), vgrid_params())
    corrected = np.asarray(out.pixel, dtype=np.float64)

    cnr_before = cnr(observed, feat_roi, bg_roi)
    cnr_after = cnr(corrected, feat_roi, bg_roi)
    improvement = cnr_after / cnr_before - 1.0

    # EV-202 threshold is external-injected (not embedded in the module/engine).
    assert improvement >= EV["ev202_cnr_improvement_min"]


def test_tc017_scatter_estimation_accuracy():
    """Scenario 2: Ŝ vs injected S_inj within the external [T] tolerance."""
    _, observed, s_inj = make_smooth_scatter_phantom(SHAPE)
    s_hat = vg.estimate_scatter(observed, KERNEL_AMP, KERNEL_SIGMA_DOWN, 3, 3)
    rel_err = float(np.linalg.norm(s_hat - s_inj) / np.linalg.norm(s_inj))
    assert rel_err <= EV["scatter_rel_err_tol"]


def test_tc017_lowsignal_noise_boost_suppressed_and_nonnegative():
    """Scenario 3: low-signal noise not boosted beyond tol + output non-negative."""
    observed, lowsig = make_lowsignal_phantom(SHAPE)
    out = vg.process(make_frame(observed), scatter_calib(SHAPE), vgrid_params())
    corrected = np.asarray(out.pixel, dtype=np.float64)

    before = float(np.std(observed[lowsig]))
    after = float(np.std(corrected[lowsig]))
    assert after <= before * (1.0 + EV["lowsignal_noise_boost_tol"])
    assert float(corrected.min()) >= 0.0


def test_tc017_ev_thresholds_are_externally_injected():
    """VALIDATE-5: EV thresholds live externally (the phantom's EV dict), and the
    module's process signature accepts no threshold — judgment is separated from
    measurement (the module cannot embed a pass/fail gate)."""
    import inspect

    # The EV gate thresholds are external-injected, not module state.
    assert set(EV) >= {
        "ev202_cnr_improvement_min",
        "scatter_rel_err_tol",
        "lowsignal_noise_boost_tol",
    }
    # The module contract carries only (frame, calib, params) — no EV threshold.
    params = list(inspect.signature(vg.process).parameters)
    assert params == ["frame", "calib", "params"]
