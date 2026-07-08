"""Engine contract: pure consumption, metadata attachment (Scenario 1, EC-7)."""

from __future__ import annotations

import numpy as np
import pytest

from metrics import mtf, nps
from metrics.result import MetricCondition, MetricResult
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import make_params


def test_scenario1_input_frame_not_mutated():
    """Input XFrame (pixel/mask/noise/history) is unchanged (REQ-METRICS-CORE-1)."""
    phantom = gen.make_slanted_edge()
    frame = phantom.frame
    before = np.array(frame.pixel, copy=True)
    before_masks = np.array(frame.masks, copy=True)
    before_history = frame.history
    mtf.compute_mtf(frame, make_params(), calibset_id="CS-1")
    assert np.array_equal(frame.pixel, before)
    assert np.array_equal(frame.masks, before_masks)
    assert frame.history == before_history


def test_scenario1_readonly_buffer_enforced():
    """XFrame buffers are read-only (EC-7 auto-detectable side-effect guard)."""
    phantom = gen.make_slanted_edge()
    with pytest.raises(ValueError):
        phantom.frame.pixel[0, 0] = 12345.0


def test_scenario1_metadata_attached_deterministically():
    """Result carries deterministic condition metadata; no EV thresholds baked in."""
    params = make_params()
    phantom = gen.make_slanted_edge()
    result = mtf.compute_mtf(phantom.frame, params, calibset_id="CS-42")
    cond = result.condition
    assert isinstance(result, MetricResult)
    assert isinstance(cond, MetricCondition)
    assert cond.params_hash == params.hash()
    assert cond.calibset_id == "CS-42"
    assert cond.beam_quality == "RQA5"
    assert cond.added_filter == "Al 21mm"
    assert cond.temperature_c == 25.0
    # Determinism: same inputs -> identical params hash.
    again = mtf.compute_mtf(phantom.frame, params, calibset_id="CS-42")
    assert again.condition.params_hash == cond.params_hash
    # Measurement != gating: no EV min/typ/max fields present.
    for key in result.values:
        assert "ev_" not in key.lower()
        assert "pass" not in key.lower()


def test_dose_level_metadata_roundtrip():
    """Dose-level tag is attached to NPS results (Scenario 4 metadata)."""
    params = make_params()
    phantom = gen.make_white_noise_frames(n_frames=8)
    result = nps.compute_nps(phantom.frames, params, dose_level="XN/2")
    assert result.condition.dose_level == "XN/2"
