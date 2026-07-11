"""Infra-layer contract: T0 surface unchanged, additive wrapper, pure layering.

Covers acceptance Scenario 1 and REQ-TIER-CONTRACT-1..5. Verifies that T10 adds no
processing stage / CalibKind, leaves the ``run_pipeline`` signature and calibration
gate intact (exercised through the wrapper), keeps ``common/equivalence.py`` pure
(common only), keeps ``pipeline/tier.py`` an orchestrator-only consumer, and keeps
tier gating free of any EV grade (measurement != judgment).
"""

from __future__ import annotations

import dataclasses
import inspect
import typing

import pytest

from common.calibset import CalibKind
from common.equivalence import INTEGER_PATH_STAGES, EquivalenceDiff
from pipeline.orchestrator import (
    CANONICAL_ORDER,
    CalibrationError,
    PipelineDefinition,
    _KIND_BY_STAGE,
    run_pipeline,
)
from pipeline.tier import Tier, decide_tier, run_tier
from tests.pipeline import tier_fixtures
from tests.pipeline.frame_fixtures import (
    _CALIB_KIND,
    passthrough_registry,
    std_frame,
)
from tests.pipeline.tier_fixtures import cap_tier2, tier_policy_params, tier_variants


# -- Scenario 1: T0 orchestrator surface unchanged ----------------------------


def test_canonical_order_has_no_tier_stage():
    assert "tier" not in CANONICAL_ORDER
    assert "equivalence" not in CANONICAL_ORDER


def test_no_tier_calibkind_or_kind_wiring():
    kinds = {k.value for k in CalibKind}
    assert "tier" not in kinds
    assert not any("tier" in stage for stage in _KIND_BY_STAGE)


def test_run_pipeline_signature_unchanged():
    # `domain` is the SPEC-CALDOM-001 additive context arg: keyword-only with a
    # default of None (isomorphic to panel_id/timestamp), so every existing caller
    # is unaffected. The guard is updated to acknowledge the authorized additive
    # surface — the positional core (frame/definition/registry/calib_map) is fixed.
    params = list(inspect.signature(run_pipeline).parameters)
    assert params == [
        "frame",
        "definition",
        "registry",
        "calib_map",
        "params_map",
        "panel_id",
        "timestamp",
        "domain",
    ]


def test_run_tier_preserves_calibration_gate():
    # The additive wrapper still flows through the entry gate: a missing CalibSet
    # is refused (SWR-000-5), proving the gate is not bypassed.
    frame = std_frame()
    variants = tier_variants()
    definition = variants[Tier.TIER1]
    registry = passthrough_registry(definition)
    with pytest.raises(CalibrationError):
        run_tier(frame, Tier.TIER1, variants, registry, {})


# -- CONTRACT-4: measurement != judgment (no EV grade in tier gating) ---------


def test_tier_decision_has_no_ev_grade_fields():
    d = decide_tier(cap_tier2(), tier_policy_params())
    fields = set(vars(d).keys())
    forbidden = {"ev", "mtf", "dqe", "quality", "grade", "score"}
    assert not (fields & forbidden)
    # Fields are execution-path classification only.
    assert fields == {"tier", "detected_tier", "forced", "rationale"}


# -- CONTRACT-5: CI-4 diff shape reused, not reimplemented --------------------


def test_equivalence_diff_shape_contract_unchanged():
    names = {f.name for f in dataclasses.fields(EquivalenceDiff)}
    assert names == {"pixel_equal", "masks_equal", "noise_equal", "max_pixel_abs_diff"}
    assert hasattr(EquivalenceDiff, "structurally_equal")


# -- CONTRACT-2: layering is enforced by import-linter (single source of truth) --
#
# The pipeline/tier.py "orchestrator + common only, never modules/metrics" ban and
# the common/equivalence.py "pure common" ban are enforced declaratively by the
# import-linter contracts in pyproject.toml (run via `uv run lint-imports`, part of
# XDET-TC-000 decision engine B). A previous hand-rolled AST import scanner here
# duplicated that enforcement and could drift from the linter config, so it was
# removed in favour of the linter as the single source of truth (code-review
# defect #6). The gap the AST test covered that the default "common is foundational"
# contract did NOT — pipeline.tier must not import modules/metrics, whereas the
# layers contract otherwise permits pipeline -> modules — is now closed by a
# dedicated forbidden contract for pipeline.tier in pyproject.toml.


# -- CONTRACT-5 (drift guard): INTEGER_PATH_STAGES must track the orchestrator ----

# The SWR-1302 float-path calibrated stages: detector-calibrated (present in
# _KIND_BY_STAGE) but NOT bit-exact integer arithmetic — lag is an exponential-sum
# recursive FLOAT state, denoise is VST/BM3D FLOAT, virtual_grid is SKS scatter
# FLOAT. Every other _KIND_BY_STAGE entry is the integer (bit-identical) path.
_FLOAT_PATH_CALIBRATED_STAGES = {"lag", "denoise", "virtual_grid"}


def test_integer_path_stages_track_orchestrator_wiring():
    # common/equivalence.py keeps INTEGER_PATH_STAGES as literal strings because it
    # is the foundational layer and must not import pipeline.orchestrator
    # (import-linter forbidden edge). This tests/ module is allowed to import BOTH,
    # so it is the place that guarantees the two never silently drift — a drift
    # would otherwise downgrade a stage's equivalence check from bit-exact INTEGER
    # to lenient FLOAT with no test failure (code-review defect #2).
    derived = set(_KIND_BY_STAGE) - _FLOAT_PATH_CALIBRATED_STAGES
    assert INTEGER_PATH_STAGES == derived
    # Every integer-path stage must be a real canonical stage (catches a rename in
    # orchestrator that equivalence.py failed to mirror).
    assert INTEGER_PATH_STAGES <= set(CANONICAL_ORDER)
    # And it must be exactly the SWR-1302 documented integer path.
    assert INTEGER_PATH_STAGES == {"offset", "gain", "defect", "line_noise"}


# -- Fixture derives its calib-kind wiring from the orchestrator (no drift) --------


def test_calib_kind_fixture_derived_from_orchestrator():
    # frame_fixtures._CALIB_KIND must be derived from the orchestrator's
    # _KIND_BY_STAGE (mapped to CalibKind), not a separate hand-written dict that
    # can drift or omit a stage — it previously omitted 'lag' (code-review defect
    # #4). Every wired stage is present and maps to the matching CalibKind.
    assert set(_CALIB_KIND) == set(_KIND_BY_STAGE)
    assert "lag" in _CALIB_KIND
    for stage, kind_value in _KIND_BY_STAGE.items():
        assert _CALIB_KIND[stage] == CalibKind(kind_value)


# -- Fixture return annotation is a real, resolvable type (no suppressed noqa) -----


def test_tier_variants_annotation_is_resolvable():
    # tier_fixtures.tier_variants() previously annotated its return with an
    # unresolvable quoted forward reference suppressed by `# noqa: F821`. The
    # annotation must resolve to the real PipelineDefinition type (code-review
    # defect #7) so get_type_hints does not raise NameError.
    hints = typing.get_type_hints(tier_fixtures.tier_variants)
    assert hints["return"] == dict[Tier, PipelineDefinition]
