"""Tier gating: an additive wrapper selecting an execution path (SWR-1301).

@MX:ANCHOR: [AUTO] `decide_tier` is the single tier-judgment entry point
(SWR-1301, REQ-TIER-GATE-1/3/4). It consumes a hardware compute-capability
descriptor, returns the supported execution tier plus a rationale log, accepts a
user forced DOWNGRADE and rejects a forced UPGRADE with an explicit error.
@MX:REASON: fan_in spans the XDET-TC-020 live gate and the Scenario 2/3 + EC-1/EC-3
tests; the forced-downgrade-only rule and the "never guess a tier" invariant
(missing/invalid descriptor / policy -> explicit error, no silent default or
promotion) are what those consumers rely on.

Placement (spec decision 1): T10 is execution infrastructure, NOT a processing
stage. This module is an ADDITIVE wrapper around `pipeline.orchestrator.run_pipeline`
(the `pipeline/sequence.py` precedent) — it does not add a stage to
`CANONICAL_ORDER`, does not introduce a new `CalibKind` / `_KIND_BY_STAGE` wiring,
and does not change the `run_pipeline` signature or its calibration gate. It imports
only the orchestrator (its own layer) + `common`; the per-tier execution variants
and their registries are INJECTED by the caller (registry pattern), so pipeline
never imports `modules`.

Numeric policy (P2, REQ-TIER-CONTRACT-3): the capability -> tier thresholds are NOT
hardcoded here. They arrive as an injected `TierRule` policy in `Params` (SWR-1301
"임계 TBD: P2 벤치마크"). P1 establishes the judgment structure, the rationale log,
the forced downgrade/upgrade rule and the path selection only. Absolute processing
time (EV-401) and the integer bit-identical / float +/-1 LSB gates (EV-402) are P2.

DL path (SWR-1303: ONNX Runtime, model-hash verification, fallback auto-switch) is
a Gen 2 reserved item and is intentionally NOT implemented here (CLAUDE.md).

Tier is a HARDWARE compute-capability tier (which execution path runs), not an EV
image-quality grade — it carries no MTF/DQE pass/fail (measurement != judgment,
REQ-TIER-CONTRACT-4).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from statistics import median
from time import perf_counter
from typing import Mapping

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import XFrame
from pipeline.orchestrator import PipelineDefinition, ProcessCallable, run_pipeline

# Sentinel gpu_model value for a machine with no discrete GPU (a valid Tier 1
# descriptor). Distinct from a MISSING field (None), which is an EC-3 error.
NO_GPU = "none"

# Params key carrying the injected tuple[TierRule, ...] (thresholds are P2).
TIER_POLICY_KEY = "tier_policy"


class Tier(IntEnum):
    """Hardware compute-capability execution tiers (SWR-1301, EV-401).

    Ordinal ordering is what makes the forced downgrade/upgrade rule a pure
    structural comparison (independent of the P2 capability thresholds). TIER1 is
    the deterministic CPU float golden-model path (P1's only real implementation);
    TIER2 is the full / accelerated path (taxonomy present, GPU kernel is P2).
    """

    TIER1 = 1
    TIER2 = 2


class TierDecisionError(RuntimeError):
    """The single explicit error type raised by every guarded path in this module.

    Raise sites (all deterministic — never a silent threshold guess, a quiet
    substitution of the lowest tier, or an unauthorized promotion; SWR-1301
    강제 상향 금지, EC-3):
      - an invalid/missing capability descriptor (`decide_tier` via
        `_validate_capability`);
      - an invalid `params` container — None or not a `Params` — so the injected
        capability->tier policy is unreachable (`decide_tier`);
      - a missing / empty / unsatisfiable tier policy (`decide_tier` /
        `_detect_tier`);
      - an invalid `forced_tier` type or a forced UPGRADE request (`decide_tier`);
      - no pipeline variant registered for the requested tier (`select_pipeline`);
      - `warm_runs` < 1 for the timing harness (`time_tier`).
    """


@dataclass(frozen=True)
class Capability:
    """Hardware compute-capability descriptor (SWR-1301).

    Fields default to None so a MISSING field is representable; `decide_tier`
    validates completeness and rejects an incomplete/invalid descriptor (EC-3)
    rather than guessing. A machine with no discrete GPU sets gpu_model=NO_GPU and
    vram_gb=0.0 (a valid Tier 1 descriptor), distinct from a missing field.
    """

    cpu_cores: int | None = None
    avx: bool | None = None
    gpu_model: str | None = None
    vram_gb: float | None = None


@dataclass(frozen=True)
class TierRule:
    """One injected capability->tier threshold rule (thresholds are P2 values).

    The numeric fields are supplied by the caller (P2 benchmark register); this
    module hardcodes no threshold literal (REQ-TIER-CONTRACT-3).
    """

    tier: Tier
    min_cpu_cores: int
    requires_avx: bool
    requires_gpu: bool
    min_vram_gb: float


@dataclass(frozen=True)
class TierDecision:
    """The tier judgment: chosen tier, auto-detected ceiling, forced flag, log.

    Carries execution-path classification ONLY — no EV grade (measurement !=
    judgment, REQ-TIER-CONTRACT-4).
    """

    tier: Tier
    detected_tier: Tier
    forced: bool
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class TimingRecord:
    """A cold + warm timing record for one tier's pipeline (XDET-TC-020).

    Structure only: no absolute-time threshold is asserted anywhere (EV-401 is P2;
    the P1 golden model is intentionally slow — accuracy is the single goal).
    """

    tier: Tier
    cold_seconds: float
    warm_seconds: tuple[float, ...]
    warm_median: float
    runs: int


def _validate_capability(capability: Capability | None) -> None:
    """Refuse an incomplete/invalid descriptor with an explicit error (EC-3)."""
    if capability is None:
        raise TierDecisionError(
            "capability descriptor is None; refusing to guess a tier (EC-3)"
        )
    if not isinstance(capability, Capability):
        raise TierDecisionError(
            f"capability must be a Capability, got {type(capability)!r}"
        )
    if (
        isinstance(capability.cpu_cores, bool)
        or not isinstance(capability.cpu_cores, int)
        or capability.cpu_cores < 1
    ):
        raise TierDecisionError(
            f"capability.cpu_cores invalid/missing: {capability.cpu_cores!r} "
            "(must be int >= 1)"
        )
    if not isinstance(capability.avx, bool):
        raise TierDecisionError(
            f"capability.avx invalid/missing: {capability.avx!r} (must be bool)"
        )
    if not isinstance(capability.gpu_model, str) or not capability.gpu_model:
        raise TierDecisionError(
            f"capability.gpu_model invalid/missing: {capability.gpu_model!r} "
            f"(non-empty str; '{NO_GPU}' when no discrete GPU)"
        )
    if (
        isinstance(capability.vram_gb, bool)
        or not isinstance(capability.vram_gb, (int, float))
        or capability.vram_gb < 0
    ):
        raise TierDecisionError(
            f"capability.vram_gb invalid/missing: {capability.vram_gb!r} "
            "(must be a number >= 0)"
        )


def _rule_satisfied(rule: TierRule, cap: Capability) -> tuple[bool, list[str]]:
    """Evaluate one rule against a (validated) capability; return (ok, reasons)."""
    reasons: list[str] = []
    ok = True
    if cap.cpu_cores >= rule.min_cpu_cores:
        reasons.append(f"cpu_cores {cap.cpu_cores}>={rule.min_cpu_cores}")
    else:
        ok = False
        reasons.append(f"cpu_cores {cap.cpu_cores}<{rule.min_cpu_cores}")
    if rule.requires_avx and not cap.avx:
        ok = False
        reasons.append("avx required, absent")
    elif rule.requires_avx:
        reasons.append("avx present")
    if rule.requires_gpu:
        if cap.gpu_model != NO_GPU:
            reasons.append(f"gpu '{cap.gpu_model}' present")
        else:
            ok = False
            reasons.append("gpu required, none present")
    if cap.vram_gb >= rule.min_vram_gb:
        reasons.append(f"vram {cap.vram_gb}>={rule.min_vram_gb}")
    else:
        ok = False
        reasons.append(f"vram {cap.vram_gb}<{rule.min_vram_gb}")
    return ok, reasons


def _detect_tier(
    cap: Capability, policy: tuple[TierRule, ...]
) -> tuple[Tier, tuple[str, ...]]:
    """Select the highest tier the capability satisfies + a rationale log.

    Raises TierDecisionError if NO rule is satisfied — no silent fallback to the
    lowest tier (SWR-1301, EC-3 spirit).
    """
    rationale: list[str] = [
        f"capability cpu_cores={cap.cpu_cores} avx={cap.avx} "
        f"gpu={cap.gpu_model} vram_gb={cap.vram_gb}"
    ]
    satisfied: list[Tier] = []
    for rule in sorted(policy, key=lambda r: int(r.tier)):
        ok, reasons = _rule_satisfied(rule, cap)
        rationale.append(
            f"{rule.tier.name}: {'satisfied' if ok else 'unsatisfied'} "
            f"({'; '.join(reasons)})"
        )
        if ok:
            satisfied.append(rule.tier)
    if not satisfied:
        raise TierDecisionError(
            "no tier rule satisfied by the capability; refusing to substitute a "
            "fallback tier (SWR-1301)"
        )
    tier = max(satisfied, key=lambda t: int(t))
    rationale.append(f"detected tier = {tier.name} (highest satisfied by capability)")
    return tier, tuple(rationale)


def decide_tier(
    capability: Capability | None,
    params: Params,
    *,
    forced_tier: Tier | None = None,
) -> TierDecision:
    """Judge the execution tier from a capability descriptor + injected policy.

    The capability -> tier thresholds live in `params[TIER_POLICY_KEY]` (a tuple of
    TierRule); they are P2 and never hardcoded here. A user may FORCE a downgrade
    (<= detected tier), which is accepted; a forced UPGRADE (> detected tier) is
    rejected with an explicit error (SWR-1301). A missing/invalid descriptor or a
    missing/unsatisfiable policy raises TierDecisionError — never a silent default.
    """
    _validate_capability(capability)
    assert capability is not None  # narrowed by _validate_capability
    if not isinstance(params, Params):
        raise TierDecisionError(
            f"params must be a Params container, got {type(params)!r}; the "
            "capability->tier policy is injected through it and cannot be read "
            "(SWR-1301, REQ-TIER-CONTRACT-3)"
        )
    policy = params.get(TIER_POLICY_KEY)
    if not policy:
        raise TierDecisionError(
            f"tier policy missing from Params[{TIER_POLICY_KEY!r}]; capability->tier "
            "thresholds are P2-externalized and must be injected "
            "(SWR-1301, REQ-TIER-CONTRACT-3)"
        )
    detected, rationale = _detect_tier(capability, tuple(policy))

    if forced_tier is None:
        return TierDecision(
            tier=detected, detected_tier=detected, forced=False, rationale=rationale
        )
    if not isinstance(forced_tier, Tier):
        raise TierDecisionError(
            f"forced_tier must be a Tier, got {type(forced_tier)!r}"
        )
    if int(forced_tier) > int(detected):
        raise TierDecisionError(
            f"forced upgrade rejected: requested {forced_tier.name} exceeds detected "
            f"{detected.name} (SWR-1301 강제 상향 금지 — no silent promotion)"
        )
    note = (
        f"forced downgrade to {forced_tier.name} accepted (<= detected {detected.name})"
        if forced_tier != detected
        else f"forced {forced_tier.name} equals detected; accepted"
    )
    return TierDecision(
        tier=forced_tier,
        detected_tier=detected,
        forced=True,
        rationale=rationale + (note,),
    )


def select_pipeline(
    tier: Tier, variants: Mapping[Tier, PipelineDefinition]
) -> PipelineDefinition:
    """Select the execution-path variant (PipelineDefinition) for a tier.

    @MX:NOTE: [AUTO] The variant map is injected by the caller (registry pattern)
    so this module never imports `modules`. A missing variant is an explicit
    error, not a silent fallback.
    """
    definition = variants.get(tier)
    if definition is None:
        raise TierDecisionError(
            f"no pipeline variant registered for {tier.name}; cannot select an "
            "execution path"
        )
    return definition


def run_tier(
    frame: XFrame,
    tier: Tier,
    variants: Mapping[Tier, PipelineDefinition],
    registry: Mapping[str, ProcessCallable],
    calib_map: Mapping[str, CalibSet],
    params_map: Mapping[str, Params] | None = None,
    *,
    panel_id: str | None = None,
    timestamp: str | None = None,
) -> XFrame:
    """Run the tier's execution-path variant via the UNCHANGED run_pipeline.

    @MX:NOTE: [AUTO] Additive wrapper (sequence.py precedent): it selects the
    variant then delegates to run_pipeline verbatim, so the run_pipeline
    signature, CANONICAL_ORDER and the calibration entry gate are untouched.
    """
    definition = select_pipeline(tier, variants)
    return run_pipeline(
        frame,
        definition,
        registry,
        calib_map,
        params_map,
        panel_id=panel_id,
        timestamp=timestamp,
    )


def time_tier(
    frame: XFrame,
    tier: Tier,
    variants: Mapping[Tier, PipelineDefinition],
    registry: Mapping[str, ProcessCallable],
    calib_map: Mapping[str, CalibSet],
    params_map: Mapping[str, Params] | None = None,
    *,
    warm_runs: int = 3,
    panel_id: str | None = None,
    timestamp: str | None = None,
) -> TimingRecord:
    """Run one cold + `warm_runs` warm executions and record their timing.

    Structure only (XDET-TC-020): produces a cold/warm/median timing record and
    asserts NO absolute-time threshold (EV-401 is P2; the P1 golden model is
    intentionally slow). The production 100-run count is a P2 concern; the caller
    supplies `warm_runs`.
    """
    if warm_runs < 1:
        raise TierDecisionError("warm_runs must be >= 1 to form a warm median")

    def _once() -> None:
        run_tier(
            frame,
            tier,
            variants,
            registry,
            calib_map,
            params_map,
            panel_id=panel_id,
            timestamp=timestamp,
        )

    cold_start = perf_counter()
    _once()
    cold_seconds = perf_counter() - cold_start

    warm: list[float] = []
    for _ in range(warm_runs):
        start = perf_counter()
        _once()
        warm.append(perf_counter() - start)

    return TimingRecord(
        tier=tier,
        cold_seconds=cold_seconds,
        warm_seconds=tuple(warm),
        warm_median=float(median(warm)),
        runs=warm_runs,
    )
