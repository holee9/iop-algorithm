"""XDET-TC-004/005 live release gates for the T4/WP2 lag correction.

Converts the deferred T4/WP2 skeletons into working gate cases: known-IRF
synthetic sequence injection -> lag correction (via the sequence runner) ->
judgment by the T1 engine metrics.lag against externally injected EV-104
thresholds (measurement != judgment).

- XDET-TC-004: first-frame lag % after correction <= EV-104 min AND improved.
- XDET-TC-005: PARTIAL gate — ghost residual CNR reduced after correction
  (SWR-402 by-product). EV-104 ghost "invisible" end-judgment depends on FB /
  real-panel integration and is deferred (spec decision 6).
"""

from __future__ import annotations

from metrics import lag as lag_metric
from metrics.lag import P_BASELINE, P_EXPOSURE_END, P_MIN_EXPOSED
from pipeline.orchestrator import PipelineDefinition
from pipeline.sequence import run_sequence
from tests.metrics.phantoms.params import make_params
from tests.modules.phantoms.lag_seq import (
    EV,
    IRF_B,
    lag_calib,
    lag_factory,
    lag_params,
    make_first_frame_lag_sequence,
    make_ghost_sequence,
)


def test_tc004_first_frame_lag_within_ev104_min():
    ph = make_first_frame_lag_sequence(shape=(16, 16))
    calib = lag_calib((16, 16))
    corrected = run_sequence(
        ph.measured_frames,
        PipelineDefinition(("lag",)),
        lag_factory,
        {"lag": calib},
        {"lag": lag_params()},
    )
    judge = make_params(
        **{
            P_BASELINE: ph.offset,
            P_EXPOSURE_END: ph.exposure_end_index,
            P_MIN_EXPOSED: 100.0,
        }
    )
    before = lag_metric.compute_first_frame_lag(ph.measured_frames, judge).get(
        "first_frame_lag_pct"
    )
    after = lag_metric.compute_first_frame_lag(corrected, judge).get(
        "first_frame_lag_pct"
    )
    assert after <= EV["ev104_first_frame_lag_min_pct"], after
    assert after < before


def _ghost_before_after(calib):
    """Run the ghost sequence through a lag correction and return (before, after)
    corrected ghost residual CNR judged by the T1 engine."""
    ph = make_ghost_sequence(shape=(64, 64))
    corrected = run_sequence(
        ph.measured_frames,
        PipelineDefinition(("lag",)),
        lag_factory,
        {"lag": calib},
        {"lag": lag_params()},
    )
    params = make_params()
    before = lag_metric.compute_ghost_cnr(
        ph.measured_frames[ph.ghost_index], ph.foreground_roi, ph.background_roi, params
    ).get("ghost_cnr")
    after = lag_metric.compute_ghost_cnr(
        corrected[ph.ghost_index], ph.foreground_roi, ph.background_roi, params
    ).get("ghost_cnr")
    return before, after


def test_tc005_ghost_cnr_reduced_partial_gate():
    """PARTIAL gate — EV-104 ghost "invisible" end-judgment depends on FB /
    real-panel integration and stays deferred (spec decision 6). The synthetic
    gate here asserts BOTH the SWR-402 relative reduction AND an externally
    injected ABSOLUTE ceiling on the corrected ghost residual CNR, so a token
    (relative-only) reduction cannot pass."""
    calib = lag_calib((64, 64))
    before, after = _ghost_before_after(calib)
    # Relative leg: correction must reduce the ghost residual.
    assert after < before
    # Absolute leg: corrected ghost CNR must fall below the injected EV ceiling.
    assert after <= EV["ev104_ghost_cnr_max"], after


def test_tc005_crippled_correction_fails_absolute_gate():
    """RED demonstration: a deliberately crippled correction (epsilon IRF that
    barely subtracts anything) still shows a microscopic relative reduction but
    MUST fail the absolute ghost-CNR gate — proving the gate is not relative-only."""
    crippled = lag_calib((64, 64), a=(1e-6, 1e-6, 1e-6), b=IRF_B)
    before, after = _ghost_before_after(crippled)
    # A token reduction still passes a relative-only check ...
    assert after < before
    # ... but the absolute EV ceiling rejects it (the correction is not real).
    assert after > EV["ev104_ghost_cnr_max"]
