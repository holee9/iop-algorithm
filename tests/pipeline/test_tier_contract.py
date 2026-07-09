"""Infra-layer contract: T0 surface unchanged, additive wrapper, pure layering.

Covers acceptance Scenario 1 and REQ-TIER-CONTRACT-1..5. Verifies that T10 adds no
processing stage / CalibKind, leaves the ``run_pipeline`` signature and calibration
gate intact (exercised through the wrapper), keeps ``common/equivalence.py`` pure
(common only), keeps ``pipeline/tier.py`` an orchestrator-only consumer, and keeps
tier gating free of any EV grade (measurement != judgment).
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

from common.calibset import CalibKind
from common.equivalence import EquivalenceDiff
from pipeline import tier
from pipeline.orchestrator import (
    CANONICAL_ORDER,
    CalibrationError,
    _KIND_BY_STAGE,
    run_pipeline,
)
from pipeline.tier import Tier, decide_tier, run_tier
from tests.pipeline.frame_fixtures import (
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
    params = list(inspect.signature(run_pipeline).parameters)
    assert params == [
        "frame",
        "definition",
        "registry",
        "calib_map",
        "params_map",
        "panel_id",
        "timestamp",
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


# -- CONTRACT-2: layering (import-linter mirror as an in-suite structural check) --


def _imported_top_packages(py_path: str) -> set[str]:
    tree = ast.parse(Path(py_path).read_text(encoding="utf-8"))
    tops: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                tops.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                tops.add(node.module.split(".")[0])
    return tops


def test_equivalence_module_is_pure_common():
    import common.equivalence as eq

    tops = _imported_top_packages(eq.__file__)
    assert "pipeline" not in tops
    assert "modules" not in tops
    assert "metrics" not in tops


def test_tier_module_consumes_orchestrator_only():
    tops = _imported_top_packages(tier.__file__)
    assert "modules" not in tops
    assert "metrics" not in tops
    # It DOES depend on the orchestrator surface (pipeline) + common (downward).
    assert "pipeline" in tops
    assert "common" in tops
