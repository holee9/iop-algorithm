"""XDET-TC-001 .. TC-021 release-gate registry (REQ-INFRA-CI-1) — P1 COMPLETE.

Every test case is registered as a pytest case so CI tracks the full matrix from
T0. Cases were skipped with their TC id + owning WP until that WP landed, then
converted to live gates in the WP's own test module. As of T10 (SPEC-TIER-001, the
P1 final SPEC) ALL Gen 1 cases XDET-TC-000..021 are LIVE; `_SKELETONS` is empty and
`test_all_gen1_tc_skeletons_are_live` asserts the P1 golden-model shape-freeze
capstone. Gen 2 items (DL path SWR-1303, ADR) are intentionally out of P1 scope.

Release-gate integrity (code-review finding #2): the TC-0xx cases are the CI
release gates defined in docs/XDET_TestSpec_v1.0.md. They gate PROCESSING /
execution work packages (correction / lag / NDT / tier gates) — they are NOT
existence checks for the T1 metrics engine, whose own reproduction coverage lives
under tests/metrics/* (synthetic phantoms + analytic known values), independent of
these gates. The comments below record where each converted TC now lives.
"""

from __future__ import annotations

from pathlib import Path

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
#   read accuracy against EV-301 min, and TC-019 gates the T9 thickness correction
#   (SRb protection EV-102 + CSa EV-303). Both are now LIVE in
#   tests/metrics/test_tc_ndt.py (T9/WP10 landed) and therefore removed from the
#   deferred skeleton list below. They gate the NEW T9 processing (streaming SNRn
#   accumulation, single-wire IQI report, thickness correction) on synthetic
#   phantoms, not the pre-existing T1 read functions (whose reproduction coverage
#   lives in tests/metrics/test_ndt*.py).
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
    # TC-015 (grid detection accuracy + residual grid-line invisibility, hard DoD)
    # and TC-016 (moire / low-freq fold + GLS-failure passthrough) are the T7/WP8
    # release gates; they are now LIVE in tests/modules/test_tc_grid.py and
    # therefore removed from this deferred list. TC-016 is a T7 PARTIAL gate (the
    # low-frequency-fold residual under the attenuation cap and the observer
    # "invisible" study are licensing-deferred, spec decision 3).
    # TC-017 (kernel virtual grid / SKS scatter correction CNR improvement, hard
    # DoD) is the T8/WP9 release gate; it is now LIVE in
    # tests/modules/test_tc_virtual_grid.py and therefore removed from this
    # deferred list.
    # TC-020 (tier gating structure) and TC-021 (equivalence diff frame structure)
    # are the T10/WP12 release gates; they are now LIVE in
    # tests/pipeline/test_tc_tier.py and therefore removed from this deferred list.
    # Their STRUCTURE pass (numeric gates — tier thresholds, integer bit-identical /
    # float +/-1 LSB, absolute processing time — remain P2) completes Gen 1
    # XDET-TC-000..021 and marks the P1 golden-model shape-freeze milestone
    # (SPEC-TIER-001 VALIDATE-4; P1 final SPEC).
]


# Full Gen 1 release-gate range: XDET-TC-000 .. XDET-TC-021 (inclusive).
_GEN1_TC_RANGE = range(0, 22)

# TC ids inside the Gen 1 range that are intentionally NOT live-tested in P1, each
# mapped to a documented reason. Empty at T10: every XDET-TC-000..021 is live (P1
# golden-model shape-freeze). Gen 2 items (DL path SWR-1303, ADR) fall OUTSIDE this
# range and are not tracked here. Adding an entry here is the ONLY sanctioned way to
# drop a TC from live coverage — a bare removal makes the capstone fail loudly.
_DEFERRED_GEN1_TC: dict[str, str] = {}

# This registry file references TC ids in its own bookkeeping docstring/comments;
# those references must NOT count as a live test, so the scan excludes this file.
_REGISTRY_FILE = Path(__file__).resolve()


def _live_tc_ids() -> set[str]:
    """Zero-padded TC ids (e.g. '016') referenced in any test source EXCEPT this
    registry file.

    Accepts the id forms actually used across the suite (case-insensitive):
    'XDET-TC-016' and 'TC-016' (docstrings / comments / section headers) and the
    'tc_016' function-name style. A TC is 'live' when it is named anywhere outside
    this registry — proving a real converted test carries it.
    """
    tests_root = _REGISTRY_FILE.parent
    chunks: list[str] = []
    for py in sorted(tests_root.rglob("*.py")):
        if py.resolve() == _REGISTRY_FILE:
            continue
        chunks.append(py.read_text(encoding="utf-8").lower())
    corpus = "\n".join(chunks)
    live: set[str] = set()
    for n in _GEN1_TC_RANGE:
        tc = f"{n:03d}"
        if f"tc-{tc}" in corpus or f"tc_{tc}" in corpus:
            live.add(tc)
    return live


def test_all_gen1_tc_skeletons_are_live():
    """P1 capstone (SPEC-TIER-001 VALIDATE-4): no deferred Gen 1 TC skeleton
    remains AND every XDET-TC-000..021 id is backed by a real live test somewhere in
    the suite (or is explicitly deferred-with-reason).

    Strengthened per code-review finding #3: `_SKELETONS == []` alone could pass even
    if a TC were silently dropped (converted to nothing), because it never checked
    that each removed id actually has a corresponding live test elsewhere. The scan
    below closes that gap — hiding/renaming a TC's only reference makes this fail.
    Gen 2 items (DL path SWR-1303, ADR) are intentionally out of P1 scope."""
    assert _SKELETONS == []

    # Deferred entries must each carry a non-empty reason (no silent deferral).
    assert all(reason.strip() for reason in _DEFERRED_GEN1_TC.values()), (
        "every _DEFERRED_GEN1_TC entry must document a reason"
    )

    live = _live_tc_ids()
    missing = {
        f"{n:03d}"
        for n in _GEN1_TC_RANGE
        if f"{n:03d}" not in live and f"{n:03d}" not in _DEFERRED_GEN1_TC
    }
    assert not missing, (
        "Gen 1 TC id(s) neither live-tested nor deferred-with-reason "
        f"(a TC was dropped without conversion): {sorted(missing)}"
    )
