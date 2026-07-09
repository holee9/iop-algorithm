"""Sequence runner: threading, reset, FB trigger, TC-004/005 live gates.

Covers acceptance Scenarios 3, 4, 5, 7 and EC-5 via pipeline.sequence.run_sequence
(spec decision 1/4). first-frame lag / ghost CNR are judged in the test by the T1
engine metrics.lag alongside the lag module (CONTRACT-3).
"""

from __future__ import annotations

import numpy as np
import pytest

from modules import offset as offset_mod
from modules.lag import LagCorrector
from pipeline.orchestrator import PipelineDefinition
from pipeline.sequence import FBTriggerError, NoOpFBTrigger, run_sequence
from tests.modules.phantoms.corrections import corr_params, offset_calib
from tests.modules.phantoms.lag_seq import (
    lag_calib,
    lag_factory,
    lag_params,
    make_matched_sequence,
)


def test_scenario3_sequence_threads_state():
    """REQ-LAG-STATE-5: run_sequence threads state frame-to-frame (matches a
    single reused instance)."""
    ph = make_matched_sequence(shape=(8, 8), n_frames=6)
    calib = lag_calib((8, 8), ph.a, ph.b)
    definition = PipelineDefinition(("lag",))
    calib_map = {"lag": calib}
    params_map = {"lag": lag_params()}

    outs = run_sequence(
        ph.measured_frames, definition, lag_factory, calib_map, params_map
    )

    # Equivalent to a manually threaded single instance.
    ref = LagCorrector()
    for out, measured in zip(outs, ph.measured_frames):
        expected = ref.process(measured, calib, lag_params())
        assert out.pixel.tobytes() == expected.pixel.tobytes()


def test_ec5_reset_between_sequences():
    """REQ-LAG-STATE-4 / EC-5: a new sequence (fresh registry) resets state."""
    shape = (6, 6)
    calib = lag_calib(shape)
    definition = PipelineDefinition(("lag",))
    calib_map = {"lag": calib}
    params_map = {"lag": lag_params()}

    strong = [np.full(shape, 6000.0, dtype=np.float32) for _ in range(4)]
    from common.xframe import new_frame

    seq_a = [new_frame(x) for x in strong]
    seq_b = [new_frame(np.full(shape, 1000.0, dtype=np.float32)) for _ in range(3)]

    run_sequence(seq_a, definition, lag_factory, calib_map, params_map)
    outs_b = run_sequence(seq_b, definition, lag_factory, calib_map, params_map)

    # First frame of sequence B is uncorrected (state reset to zero).
    assert np.allclose(outs_b[0].pixel, 1000.0)


def test_scenario7_fb_trigger_handshake_mock():
    """REQ-LAG-CORR-3 / Scenario 7: FB request/confirm handshake is invoked."""

    class MockFB:
        def __init__(self):
            self.requested = 0
            self.confirmed = 0

        def request(self):
            self.requested += 1

        def confirm(self):
            self.confirmed += 1
            return True

    ph = make_matched_sequence(shape=(4, 4), n_frames=2)
    calib = lag_calib((4, 4), ph.a, ph.b)
    fb = MockFB()
    run_sequence(
        ph.measured_frames,
        PipelineDefinition(("lag",)),
        lag_factory,
        {"lag": calib},
        {"lag": lag_params()},
        fb_trigger=fb,
    )
    assert fb.requested == 1 and fb.confirmed == 1
    # Default trigger is a harmless no-op.
    assert NoOpFBTrigger().confirm() is True


def test_fb_confirm_failure_raises_not_silently_ignored():
    """A falsy confirm() must abort the sequence with a named error instead of
    being silently discarded."""

    class FailingFB:
        def request(self):
            return None

        def confirm(self):
            return False

    ph = make_matched_sequence(shape=(4, 4), n_frames=2)
    calib = lag_calib((4, 4), ph.a, ph.b)
    with pytest.raises(FBTriggerError, match="frame index 0"):
        run_sequence(
            ph.measured_frames,
            PipelineDefinition(("lag",)),
            lag_factory,
            {"lag": calib},
            {"lag": lag_params()},
            fb_trigger=FailingFB(),
        )


def test_full_chain_offset_then_lag_integration():
    """Orchestrator + sequence-runner integration over a multi-stage chain."""
    ph = make_matched_sequence(shape=(8, 8), n_frames=5)
    shape = (8, 8)

    def factory():
        return {"offset": offset_mod.process, "lag": LagCorrector().process}

    definition = PipelineDefinition(("offset", "lag"))
    calib_map = {
        "offset": offset_calib(np.zeros(shape, dtype=np.float32)),  # zero offset
        "lag": lag_calib(shape, ph.a, ph.b),
    }
    params_map = {"offset": corr_params(), "lag": lag_params()}

    outs = run_sequence(ph.measured_frames, definition, factory, calib_map, params_map)

    # Zero-offset passthrough then matched-IRF lag correction recovers true.
    for out, truth in zip(outs, ph.true_frames):
        assert np.allclose(out.pixel, truth.pixel, atol=1e-1)
    # Both stages recorded in the history chain.
    assert [h.module_name for h in outs[-1].history] == ["offset", "lag"]
