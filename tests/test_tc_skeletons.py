"""XDET-TC-001 .. TC-021 skeletons (REQ-INFRA-CI-1).

Every test case is registered as a pytest case now so CI tracks the full matrix
from T0. Cases beyond TC-000 are skipped with their TC id + the WP that will
implement them. They are activated as their owning work packages land (T1+).
"""

from __future__ import annotations

import pytest

# (TC id, short reason / owning work package). Mirrors CLAUDE.md T1..T10 DoDs.
_SKELETONS = [
    ("XDET-TC-001", "offset/gain/defect on synthetic+real (T2/WP1)"),
    ("XDET-TC-002", "offset/gain/defect (T2/WP1)"),
    ("XDET-TC-003", "offset/gain/defect (T2/WP1)"),
    ("XDET-TC-004", "lag exponential-sum recursion (T4/WP2)"),
    ("XDET-TC-005", "lag IRF fitting (T4/WP2)"),
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
