"""Tier-decision fixtures for SPEC-TIER-001 (tests/ only).

Every tier threshold here is a PLACEHOLDER P2 value (SWR-1301 "임계 TBD: P2
벤치마크") injected via ``Params`` — the production tree (``pipeline/tier.py``)
carries none (REQ-TIER-CONTRACT-3). Builds synthetic capability descriptors, an
injected tier policy, and per-tier pipeline variants (Tier 1 = deterministic
integer path — P1's only real execution path; Tier 2 = float variant, taxonomy
only, GPU-accelerated kernel is P2).
"""

from __future__ import annotations

from common.contract import Params
from pipeline.tier import NO_GPU, TIER_POLICY_KEY, Capability, Tier, TierRule
from tests.pipeline.frame_fixtures import FLOAT_DEF, INT_DEF


def tier_policy_params() -> Params:
    """Injected P2-placeholder policy: Tier 2 demands more than Tier 1."""
    policy = (
        TierRule(
            tier=Tier.TIER1,
            min_cpu_cores=1,
            requires_avx=False,
            requires_gpu=False,
            min_vram_gb=0.0,
        ),
        TierRule(
            tier=Tier.TIER2,
            min_cpu_cores=4,
            requires_avx=True,
            requires_gpu=True,
            min_vram_gb=4.0,
        ),
    )
    return Params(values={TIER_POLICY_KEY: policy})


def cap_tier2() -> Capability:
    """A descriptor meeting the Tier 2 placeholder rule."""
    return Capability(cpu_cores=8, avx=True, gpu_model="SYN-GPU-X", vram_gb=8.0)


def cap_tier1() -> Capability:
    """A descriptor meeting only the Tier 1 rule (no AVX, no GPU)."""
    return Capability(cpu_cores=2, avx=False, gpu_model=NO_GPU, vram_gb=0.0)


def tier_variants() -> dict[Tier, "PipelineDefinition"]:  # noqa: F821
    """Per-tier execution-path variants (Tier 1 integer, Tier 2 float)."""
    return {Tier.TIER1: INT_DEF, Tier.TIER2: FLOAT_DEF}
