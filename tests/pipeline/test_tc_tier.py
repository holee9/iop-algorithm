"""XDET-TC-020 / TC-021 — LIVE structure cases (SPEC-TIER-001, P1 capstone).

Converts the two remaining pytest skeletons (tests/test_tc_skeletons.py) into live
STRUCTURE gates. Numeric gates stay P2: TC-020 asserts the tier-gating + timing
STRUCTURE (no absolute-time gate, EV-401); TC-021 asserts the equivalence
diff-frame STRUCTURE — positive (identical -> structurally_equal) and negative
control (perturbation -> difference) with integer/float path classification — but
asserts NO bit-identical / +/-1 LSB tolerance (EV-402). Their structural pass
completes Gen 1 XDET-TC-000..021 = P1 golden-model shape-freeze (VALIDATE-4).
"""

from __future__ import annotations

import numpy as np
import pytest

from common.equivalence import PathClass, compare_paths, diff_frames
from pipeline.orchestrator import run_pipeline
from pipeline.tier import (
    Tier,
    TierDecision,
    TierDecisionError,
    TimingRecord,
    decide_tier,
    run_tier,
    time_tier,
)
from tests.pipeline.frame_fixtures import (
    FLOAT_DEF,
    INT_DEF,
    calib_map_for,
    passthrough_registry,
    perturb,
    std_frame,
)
from tests.pipeline.tier_fixtures import (
    cap_tier1,
    cap_tier2,
    tier_policy_params,
    tier_variants,
)


def test_xdet_tc_020_tier_gating_structure():
    """TC-020: capability -> tier + rationale, forced downgrade accepted / forced
    upgrade rejected, path selection + cold/warm timing record. Structure only —
    absolute processing time (EV-401 <=3s/<=5s) is NOT asserted (P2)."""
    policy = tier_policy_params()

    # (a) decision + rationale log.
    d = decide_tier(cap_tier2(), policy)
    assert isinstance(d, TierDecision)
    assert d.tier is Tier.TIER2
    assert d.rationale

    # (b) forced downgrade accepted.
    down = decide_tier(cap_tier2(), policy, forced_tier=Tier.TIER1)
    assert down.tier is Tier.TIER1
    assert down.forced is True

    # (c) forced upgrade rejected (single deterministic path).
    with pytest.raises(TierDecisionError):
        decide_tier(cap_tier1(), policy, forced_tier=Tier.TIER2)

    # (d) path selection delegates to run_pipeline; timing record structure.
    frame = std_frame()
    variants = tier_variants()
    definition = variants[d.tier]
    registry = passthrough_registry(definition)
    calib = calib_map_for(definition)
    out = run_tier(frame, d.tier, variants, registry, calib)
    assert np.all(np.isfinite(np.asarray(out.pixel)))

    rec = time_tier(frame, d.tier, variants, registry, calib, warm_runs=2)
    assert isinstance(rec, TimingRecord)
    assert rec.runs == 2
    assert len(rec.warm_seconds) == 2


def test_xdet_tc_021_equivalence_diff_frame_structure():
    """TC-021: diff_frames-reuse equivalence frame — identical pair structurally
    equal (positive), perturbed pair differs (negative control), integer/float path
    classified. NO numeric tolerance asserted (bit-identical / +/-1 LSB = P2)."""
    frame = std_frame()

    # Positive: same golden model twice -> structurally equal, max diff 0.
    reg_i = passthrough_registry(INT_DEF)
    cal_i = calib_map_for(INT_DEF)
    a = run_pipeline(frame, INT_DEF, reg_i, cal_i)
    b = run_pipeline(frame, INT_DEF, reg_i, cal_i)
    pos = compare_paths(a, b, INT_DEF.stages)
    assert pos.structurally_equal is True
    assert pos.max_pixel_abs_diff == 0.0
    assert pos.path is PathClass.INTEGER  # bit-identical target (P2 gate marker)
    # Reuse contract: identical to the T0 CI-4 hook (no reimplementation).
    assert pos.diff == diff_frames(a, b)

    # Negative control: perturbation is detected (frame is not vacuously equal).
    c = run_pipeline(perturb(frame, delta=7.0), INT_DEF, reg_i, cal_i)
    neg = compare_paths(a, c, INT_DEF.stages)
    assert neg.structurally_equal is False
    assert neg.max_pixel_abs_diff > 0.0

    # Float-path classification marker (+/-1 LSB target).
    reg_f = passthrough_registry(FLOAT_DEF)
    cal_f = calib_map_for(FLOAT_DEF)
    fa = run_pipeline(frame, FLOAT_DEF, reg_f, cal_f)
    fb = run_pipeline(frame, FLOAT_DEF, reg_f, cal_f)
    fpos = compare_paths(fa, fb, FLOAT_DEF.stages)
    assert fpos.path is PathClass.FLOAT
    assert fpos.structurally_equal is True
