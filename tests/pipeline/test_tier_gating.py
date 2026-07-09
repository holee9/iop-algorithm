"""Tier judgment, forced downgrade/upgrade, path selection, timing harness.

Covers acceptance Scenario 2 (tier + rationale + path selection), Scenario 3 +
EC-1 (forced downgrade accepted / upgrade rejected), Scenario 6 (cold/warm timing
record structure) and EC-3 (missing/invalid capability). Numeric tier thresholds
are injected via Params (P2); no absolute-time gate is asserted (EV-401 P2).
"""

from __future__ import annotations

import numpy as np
import pytest

from common.contract import Params
from pipeline.orchestrator import PipelineDefinition
from pipeline.tier import (
    NO_GPU,
    TIER_POLICY_KEY,
    Capability,
    Tier,
    TierDecision,
    TierDecisionError,
    TierRule,
    TimingRecord,
    decide_tier,
    run_tier,
    select_pipeline,
    time_tier,
)
from tests.pipeline.frame_fixtures import (
    INT_DEF,
    calib_map_for,
    passthrough_registry,
    std_frame,
)
from tests.pipeline.tier_fixtures import (
    cap_tier1,
    cap_tier2,
    tier_policy_params,
    tier_variants,
)


# -- Scenario 2: tier decision + rationale log --------------------------------


def test_scenario2_decide_tier_produces_tier_and_rationale():
    d = decide_tier(cap_tier2(), tier_policy_params())
    assert isinstance(d, TierDecision)
    assert d.tier is Tier.TIER2
    assert d.detected_tier is Tier.TIER2
    assert d.forced is False
    assert d.rationale  # non-empty rationale log
    joined = "\n".join(d.rationale)
    # Which capability decided which tier is recorded.
    assert "TIER2" in joined
    assert "capability" in joined


def test_scenario2_decide_tier_is_deterministic():
    p = tier_policy_params()
    assert decide_tier(cap_tier2(), p) == decide_tier(cap_tier2(), p)


def test_scenario2_tier1_capability_detects_tier1():
    d = decide_tier(cap_tier1(), tier_policy_params())
    assert d.tier is Tier.TIER1
    assert d.detected_tier is Tier.TIER1


# -- Scenario 2 (b): path selection delegates to run_pipeline -----------------


def test_scenario2_select_pipeline_returns_variant_definition():
    variants = tier_variants()
    selected = select_pipeline(Tier.TIER1, variants)
    assert isinstance(selected, PipelineDefinition)
    assert selected is INT_DEF


def test_scenario2_run_tier_delegates_to_run_pipeline():
    frame = std_frame()
    variants = tier_variants()
    definition = variants[Tier.TIER1]
    registry = passthrough_registry(definition)
    calib = calib_map_for(definition)
    out = run_tier(frame, Tier.TIER1, variants, registry, calib)
    assert len(out.history) == len(definition.stages)
    assert np.all(np.isfinite(np.asarray(out.pixel)))


# -- Scenario 3 / EC-1: forced downgrade accepted, forced upgrade rejected ----


def test_scenario3_forced_downgrade_accepted():
    d = decide_tier(cap_tier2(), tier_policy_params(), forced_tier=Tier.TIER1)
    assert d.tier is Tier.TIER1
    assert d.detected_tier is Tier.TIER2
    assert d.forced is True
    assert any("downgrade" in r for r in d.rationale)


def test_scenario3_forced_equal_tier_accepted():
    d = decide_tier(cap_tier2(), tier_policy_params(), forced_tier=Tier.TIER2)
    assert d.tier is Tier.TIER2
    assert d.forced is True


def test_ec1_forced_upgrade_rejected():
    with pytest.raises(TierDecisionError, match="upgrade"):
        decide_tier(cap_tier1(), tier_policy_params(), forced_tier=Tier.TIER2)


# -- EC-3: missing / invalid capability -> explicit error, no silent default --


@pytest.mark.parametrize(
    "bad",
    [
        None,
        Capability(cpu_cores=None, avx=True, gpu_model=NO_GPU, vram_gb=0.0),
        Capability(cpu_cores=4, avx=None, gpu_model=NO_GPU, vram_gb=0.0),
        Capability(cpu_cores=4, avx=True, gpu_model=None, vram_gb=0.0),
        Capability(cpu_cores=4, avx=True, gpu_model=NO_GPU, vram_gb=None),
        Capability(cpu_cores=0, avx=True, gpu_model=NO_GPU, vram_gb=0.0),
        Capability(cpu_cores=-1, avx=True, gpu_model=NO_GPU, vram_gb=0.0),
        Capability(cpu_cores=4, avx=True, gpu_model="", vram_gb=0.0),
        Capability(cpu_cores=4, avx=True, gpu_model=NO_GPU, vram_gb=-1.0),
    ],
)
def test_ec3_invalid_capability_raises(bad):
    with pytest.raises(TierDecisionError):
        decide_tier(bad, tier_policy_params())


# -- REQ-TIER-CONTRACT-3 / GATE-1: thresholds injected, never guessed ---------


def test_missing_policy_raises_no_hardcoded_fallback():
    with pytest.raises(TierDecisionError):
        decide_tier(cap_tier2(), Params(values={}))


def test_empty_policy_no_silent_lowest_tier():
    p = Params(values={TIER_POLICY_KEY: ()})
    with pytest.raises(TierDecisionError):
        decide_tier(cap_tier2(), p)


def test_unsatisfiable_policy_raises_not_silent_lowest():
    policy = (
        TierRule(
            tier=Tier.TIER1,
            min_cpu_cores=999,
            requires_avx=False,
            requires_gpu=False,
            min_vram_gb=0.0,
        ),
    )
    p = Params(values={TIER_POLICY_KEY: policy})
    with pytest.raises(TierDecisionError):
        decide_tier(cap_tier1(), p)


def test_select_pipeline_missing_variant_raises():
    with pytest.raises(TierDecisionError):
        select_pipeline(Tier.TIER2, {Tier.TIER1: INT_DEF})


# -- Scenario 6: timing harness structure, no absolute-time gate --------------


def test_scenario6_timing_harness_structure():
    frame = std_frame()
    variants = tier_variants()
    definition = variants[Tier.TIER1]
    registry = passthrough_registry(definition)
    calib = calib_map_for(definition)
    rec = time_tier(frame, Tier.TIER1, variants, registry, calib, warm_runs=3)
    assert isinstance(rec, TimingRecord)
    assert rec.tier is Tier.TIER1
    assert rec.runs == 3
    assert len(rec.warm_seconds) == 3
    assert rec.cold_seconds >= 0.0
    assert rec.warm_median >= 0.0
    # Structure only: NO absolute-time threshold is asserted (EV-401 is P2).


def test_timing_harness_rejects_zero_warm_runs():
    frame = std_frame()
    variants = tier_variants()
    definition = variants[Tier.TIER1]
    with pytest.raises(TierDecisionError):
        time_tier(
            frame,
            Tier.TIER1,
            variants,
            passthrough_registry(definition),
            calib_map_for(definition),
            warm_runs=0,
        )
