"""XDET-TC-001 .. TC-021 skeletons (REQ-INFRA-CI-1).

Every test case is registered as a pytest case now so CI tracks the full matrix
from T0. Cases beyond TC-000 are skipped with their TC id + the WP that will
implement them. They are activated as their owning work packages land (T1+).
"""

from __future__ import annotations

import numpy as np
import pytest

# XDET-TC-001..005, 018 decision-engine PRODUCE parts are realized by the T1
# metrics engine (SPEC-METRICS-001). Their synthetic-phantom reproduction lives
# in tests/metrics/; the checks below activate those TC ids at the top level so
# the CI matrix tracks them as real (no longer skipped).
from metrics import defect_stats, dqe, lag, mtf, ndt, nps
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import make_params

# (TC id, short reason / owning work package). Mirrors CLAUDE.md T1..T10 DoDs.
# Deferred cases only; T1-owned ids (001-005, 018) are realized as real tests
# below.
_SKELETONS = [
    ("XDET-TC-006", "line noise / reference-absent path (T3/WP3)"),
    ("XDET-TC-007", "line noise (T3/WP3)"),
    ("XDET-TC-008", "saturation / geometry (T3/WP4)"),
    ("XDET-TC-009", "saturation / geometry (T3/WP4)"),
    ("XDET-TC-010", "VST GAT + unbiased inverse (T5/WP5)"),
    ("XDET-TC-011", "BM3D + mask weighting (T5/WP5)"),
    ("XDET-TC-012", "MSE / DRC (T6/WP6)"),
    ("XDET-TC-013", "auto-windowing / GSDF (T6/WP7)"),
    ("XDET-TC-014", "GSDF LUT (T6/WP7)"),
    ("XDET-TC-015", "grid-line suppression, observed-peak search (T7/WP8)"),
    ("XDET-TC-016", "grid density classes (T7/WP8)"),
    ("XDET-TC-017", "kernel virtual grid / SKS (T8/WP9)"),
    ("XDET-TC-018", "NDT SNRn + IQI auto-read (T9/WP10)"),
    ("XDET-TC-019", "NDT thickness correction (T9/WP10)"),
    ("XDET-TC-020", "tier gating structure (T10)"),
    ("XDET-TC-021", "equivalence numeric gate: bit-identical / +/-1 LSB (P2)"),
]


@pytest.mark.parametrize("tc_id,reason", _SKELETONS, ids=[t[0] for t in _SKELETONS])
def test_tc_skeleton(tc_id, reason):
    pytest.skip(f"{tc_id} deferred: {reason}")


# --- T1 realized decision-engine PRODUCE parts (SPEC-METRICS-001) ----------


def test_xdet_tc_001_nps_dqe_produce():
    """XDET-TC-001: NPS/NNPS + DQE produced from synthetic uniform noise."""
    params = make_params()
    noise = gen.make_white_noise_frames()
    nps_res = nps.compute_nps(noise.frames, params)
    edge = gen.make_slanted_edge()
    mtf_res = mtf.compute_mtf(edge.frame, params)
    freqs = nps_res.get("frequencies_lpmm")
    mtf_grid = np.interp(freqs, mtf_res.get("frequencies_lpmm"), mtf_res.get("mtf"))
    dqe_res = dqe.compute_dqe(freqs, mtf_grid, nps_res.get("nps"), params)
    assert dqe_res.get("dqe") is not None


def test_xdet_tc_002_mtf_produce():
    """XDET-TC-002: MTF produced by the edge method from a synthetic edge."""
    edge = gen.make_slanted_edge()
    res = mtf.compute_mtf(edge.frame, make_params())
    assert 0.0 < res.get("mtf_at_nyquist") < 1.0


def test_xdet_tc_003_defect_produce():
    """XDET-TC-003: E2597 bad-pixel classification produced from stacks."""
    phantom = gen.make_defect_stacks()
    res = defect_stats.classify_defects(
        phantom.dark_frames, phantom.flat_frames, make_params(), truth_map=phantom.truth_map
    )
    assert res.get("miss_rate") == 0.0


def test_xdet_tc_004_first_frame_lag_produce():
    """XDET-TC-004: first-frame lag % produced from an IRF decay sequence."""
    phantom = gen.make_lag_sequence()
    res = lag.compute_first_frame_lag(phantom.frames, make_params())
    assert res.get("first_frame_lag_pct") > 0.0


def test_xdet_tc_005_ghost_cnr_produce():
    """XDET-TC-005: ghost residual CNR produced (mandatory LAG-5)."""
    phantom = gen.make_ghost_frame()
    res = lag.compute_ghost_cnr(
        phantom.frame, phantom.foreground_roi, phantom.background_roi, make_params()
    )
    assert res.get("ghost_cnr") > 0.0


def test_xdet_tc_018_snrn_produce():
    """XDET-TC-018: SNRn + duplex-wire SRb produced from synthetic IQI."""
    params = make_params()
    duplex = gen.make_duplex_profile()
    srb = ndt.read_duplex_srb(duplex.profile, duplex.pairs, params).get("srb_um")
    uniform = gen.make_uniform_snr_frame()
    res = ndt.compute_snrn(uniform.frame, uniform.roi, srb, params)
    assert res.get("snrn") > 0.0
