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
from modules.lag import LagCorrector
from pipeline.orchestrator import PipelineDefinition
from pipeline.sequence import run_sequence
from tests.metrics.phantoms.params import make_params
from tests.modules.phantoms.lag_seq import (
    EV,
    lag_calib,
    lag_params,
    make_first_frame_lag_sequence,
    make_ghost_sequence,
)


def _lag_factory():
    return {"lag": LagCorrector().process}


def test_tc004_first_frame_lag_within_ev104_min():
    ph = make_first_frame_lag_sequence(shape=(16, 16))
    calib = lag_calib((16, 16))
    corrected = run_sequence(
        ph.measured_frames,
        PipelineDefinition(("lag",)),
        _lag_factory,
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


def test_tc005_ghost_cnr_reduced_partial_gate():
    ph = make_ghost_sequence(shape=(64, 64))
    calib = lag_calib((64, 64))
    corrected = run_sequence(
        ph.measured_frames,
        PipelineDefinition(("lag",)),
        _lag_factory,
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
    assert after < before
