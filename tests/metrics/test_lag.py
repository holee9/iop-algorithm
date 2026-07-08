"""First-frame lag and ghost CNR (Scenario 5, 8; EC-6)."""

from __future__ import annotations

import pytest

from metrics import lag
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import TOLERANCES, make_params


def test_scenario5_first_frame_lag_reproduced():
    """Exponential-sum IRF sequence -> known first-frame lag % within [T]."""
    phantom = gen.make_lag_sequence()
    result = lag.compute_first_frame_lag(phantom.frames, make_params())
    got = result.get("first_frame_lag_pct")
    rel = abs(got - phantom.known_lag_pct) / phantom.known_lag_pct
    assert rel < TOLERANCES["lag_rel"], (got, phantom.known_lag_pct)


def test_ec6_saturation_premise_violation_warns():
    """EC-6: exposed signal below premise floor -> warning (still computed)."""
    # exposed_amp 200 < lag_min_exposed_signal (500).
    phantom = gen.make_lag_sequence(exposed_amp=200.0)
    result = lag.compute_first_frame_lag(phantom.frames, make_params())
    assert result.warnings


def test_scenario8_ghost_cnr_reproduced():
    """Ghost residual -> known CNR within [T] (mandatory LAG-5)."""
    phantom = gen.make_ghost_frame()
    result = lag.compute_ghost_cnr(
        phantom.frame, phantom.foreground_roi, phantom.background_roi, make_params()
    )
    got = result.get("ghost_cnr")
    rel = abs(got - phantom.known_cnr) / phantom.known_cnr
    assert rel < TOLERANCES["ghost_cnr_rel"], (got, phantom.known_cnr)
