"""XDET-TC-053 — metric_view return-type normalization adapter (additive).

SPEC-ERGO-001 (REQ-ERGO-METRIC-1/2/3, REQ-ERGO-VALIDATE-5a).

Consumer-ergonomics gap #4: `metrics.result.metric_view(obj) -> MetricResult`
lets a generic name->run->render dispatch treat any metric-like return
uniformly. `MetricResult` passes through as identity; `ThicknessResult` is
projected to a MetricResult-shaped summary (scalar fields method/scale_px/changed).
This is an ADDITIVE adapter — `correct_thickness` still returns `ThicknessResult`
and its native array fields (flattened/low_freq) stay accessible (no substitution).
"""

from __future__ import annotations

import numpy as np

from metrics.ndt import ThicknessResult, correct_thickness
from metrics.result import MetricCondition, MetricResult, metric_view
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import make_params


def test_tc_053_metric_view_is_identity_for_metric_result():
    mr = MetricResult(
        name="MTF",
        values={"mtf": np.array([1.0, 0.5]), "frequencies_lpmm": np.array([0.0, 1.0])},
        condition=MetricCondition(beam_quality="RQA5"),
    )
    assert metric_view(mr) is mr


def test_tc_053_metric_view_projects_thickness_result_scalars():
    tr = ThicknessResult(
        flattened=np.ones((4, 4)),
        low_freq=np.zeros((4, 4)),
        method="gaussian",
        scale_px=20.0,
        changed=True,
        warnings=("advice",),
    )
    view = metric_view(tr)
    assert isinstance(view, MetricResult)
    assert view.get("method") == "gaussian"
    assert view.get("scale_px") == 20.0
    assert view.get("changed") is True
    # Non-fatal advisories carry through.
    assert view.warnings == ("advice",)
    # Summary view is scalar-only: the large arrays are not smuggled into values.
    assert "flattened" not in view.values


def test_tc_053_correct_thickness_still_returns_thickness_result_native_fields():
    ph = gen.make_thickness_defect_phantom()
    params = make_params(ndt_thickness_method="gaussian", ndt_thickness_scale_px=20)
    res = correct_thickness(ph.frame, params)

    # The return type is unchanged (no MetricResult substitution) and the native
    # array fields remain directly accessible (behavior-preserving).
    assert isinstance(res, ThicknessResult)
    assert isinstance(res.flattened, np.ndarray)
    assert isinstance(res.low_freq, np.ndarray)
    assert isinstance(res.changed, bool)

    # And the adapter projects that very result into a uniform MetricResult view.
    view = metric_view(res)
    assert isinstance(view, MetricResult)
    assert view.get("changed") == res.changed
    assert view.get("method") == res.method


def test_tc_053_existing_metric_result_consumers_unaffected():
    # Regression stand-in for apps/gui/metrics_panel.plot_mtf's MetricResult use.
    mr = MetricResult(
        name="MTF",
        values={"mtf": np.array([1.0, 0.7]), "frequencies_lpmm": np.array([0.0, 2.0])},
    )
    assert metric_view(mr).get("mtf") is mr.get("mtf")
    assert np.allclose(mr.get("frequencies_lpmm"), [0.0, 2.0])
