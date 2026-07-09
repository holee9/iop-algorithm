"""XDET-TC-001 .. TC-021 skeletons (REQ-INFRA-CI-1).

Every test case is registered as a pytest case now so CI tracks the full matrix
from T0. Cases beyond TC-000 are skipped with their TC id + the WP that will
implement them. They are activated as their owning work packages land (T1+).

Release-gate integrity (code-review finding #2): the TC-0xx cases here are the
CI release gates defined in docs/XDET_TestSpec_v1.0.md. They gate PROCESSING
work packages (correction / lag / NDT modules) against EV min thresholds — they
are NOT existence checks for the T1 metrics engine. TC ids owned by later WPs
therefore stay SKIPPED here until their processing module lands. The T1 metrics
engine's own reproduction coverage lives under tests/metrics/* (its synthetic
phantoms and analytic known values), independent of these gates.
"""

from __future__ import annotations

import pytest

# (TC id, short reason / owning work package). Mirrors CLAUDE.md T1..T10 DoDs and
# the VV -> WP mapping in docs/XDET_TestSpec_v1.0.md.
#
# TC-001/002/003 (VV-001) gate the T2/WP1 offset/gain/defect CORRECTION modules
#   ("보정 전/후 DQE·MTF 유지율", "Defect 보정 잔존 cluster") against EV-101/102/
#   103 min. These are now LIVE in tests/modules/test_tc_correction.py (T2/WP1
#   landed) and therefore removed from the deferred skeleton list below.
# TC-004/005 (VV-002) gate the T4/WP2 lag CORRECTION processing (first-frame lag
#   %, ghost CNR reduced below EV-104 min). These are now LIVE in
#   tests/modules/test_tc_lag.py (T4/WP2 landed) and therefore removed from the
#   deferred skeleton list below. TC-005 is a T4 PARTIAL gate (ghost CNR
#   reduction; the end-to-end ghost-invisible judgment depends on FB / real-panel
#   integration, spec decision 6). The metrics-engine lag/ghost readout is
#   exercised independently in tests/metrics/test_lag.py.
# TC-018 (VV-011) gates the T9/WP10 NDT module: SNRn/SRb auto-read PLUS IQI auto-
#   read accuracy on GDS-NDT weld specimens against EV-301 min. It is not purely
#   the metric readout (which lives in tests/metrics/test_ndt.py). Deferred to T9.
_SKELETONS = [
    # TC-006/007 (line noise) and TC-008/009 (saturation/geometry) are the
    # T3/WP3+WP4 release gates; they are now LIVE in
    # tests/modules/test_tc_lnsg.py and therefore removed from this deferred
    # list. TC-008 is a T3 PARTIAL gate (mask integration / boundary band /
    # no-restoration mechanism); the end-to-end boundary-artifact-invisible
    # judgment re-runs at T5/T6 (spec decision 4).
    # TC-010 (denoising performance: SNR improvement + MTF/SRb retention) and
    # TC-011 (VST round-trip unbiasedness) are the T5/WP5 release gates; they are
    # now LIVE in tests/modules/test_tc_denoise.py and therefore removed from this
    # deferred list.
    # TC-012 (MSE/DRC IQA non-degradation), TC-013 (auto-window fit rate) and
    # TC-014 (GSDF LUT PS3.14 conformance, hard DoD) are the T6/WP6+WP7 release
    # gates; they are now LIVE in tests/modules/test_tc_post.py and therefore
    # removed from this deferred list.
    ("XDET-TC-015", "grid-line suppression, observed-peak search (T7/WP8)"),
    ("XDET-TC-016", "grid density classes (T7/WP8)"),
    ("XDET-TC-017", "kernel virtual grid / SKS (T8/WP9)"),
    ("XDET-TC-018", "NDT SNRn + IQI auto-read on weld specimens vs EV-301 (T9/WP10)"),
    ("XDET-TC-019", "NDT thickness correction (T9/WP10)"),
    ("XDET-TC-020", "tier gating structure (T10)"),
    ("XDET-TC-021", "equivalence numeric gate: bit-identical / +/-1 LSB (P2)"),
]


@pytest.mark.parametrize("tc_id,reason", _SKELETONS, ids=[t[0] for t in _SKELETONS])
def test_tc_skeleton(tc_id, reason):
    pytest.skip(f"{tc_id} deferred: {reason}")
