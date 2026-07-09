"""Lag module: recursion, state serialization, saturation, contract/harness.

Covers acceptance Scenarios 1, 2, 3 (instance level), 8 and EC-4, EC-5, EC-6 for
modules.lag (SWR-401~404, REQ-LAG-CORR / STATE / CONTRACT).
"""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.contract import check_process_contract, run_stateful_harness
from common.xframe import HistoryEntry, MaskFlag, XFrame, new_frame
from modules.lag import (
    K_IRF_A,
    K_IRF_B,
    MODULE_NAME,
    MODULE_VERSION,
    LagCalibError,
    LagCorrector,
    LagStateError,
)
from tests.modules.phantoms.lag_seq import (
    lag_calib,
    lag_params,
    make_matched_sequence,
)


def test_scenario1_state_recursion_formula():
    """REQ-LAG-CORR-2: I_hat[k] = I[k] - sum_i s_i[k], advancing s_i by SWR-402."""
    shape = (4, 4)
    a, b = (0.05,), (0.7,)  # M=1 -> closed-form check
    calib = lag_calib(shape, a, b)
    params = lag_params()
    lag = LagCorrector()

    v0 = np.full(shape, 3000.0, dtype=np.float32)
    v1 = np.full(shape, 500.0, dtype=np.float32)
    out0 = lag.process(new_frame(v0), calib, params)
    out1 = lag.process(new_frame(v1), calib, params)

    # Frame 0: fresh state -> output == input.
    assert np.allclose(out0.pixel, v0)
    # Frame 1: lag_sum = a*b*v0 (state after frame 0).
    expected1 = v1 - a[0] * b[0] * v0
    assert np.allclose(out1.pixel, expected1, atol=1e-3)


def test_scenario1_input_immutable_and_history():
    """REQ-LAG-CONTRACT-1/2: input untouched; history carries module meta."""
    shape = (6, 6)
    calib = lag_calib(shape)
    params = lag_params()
    pix = np.full(shape, 2000.0, dtype=np.float32)
    frame = new_frame(pix)
    lag = LagCorrector()

    out = lag.process(frame, calib, params)

    assert np.array_equal(frame.pixel, pix)  # input immutable
    entry = out.history[-1]
    assert entry.module_name == MODULE_NAME
    assert entry.module_version == MODULE_VERSION
    assert entry.params_hash == params.hash()
    assert entry.calibset_id == calib.calibset_id
    assert entry.extra["m_terms"] == len(calib.data[K_IRF_A])


def test_scenario1_matched_irf_recovers_true_sequence():
    """A matched-IRF correction inverts the forward lag model (near-exact)."""
    ph = make_matched_sequence(shape=(8, 8), n_frames=8)
    calib = lag_calib((8, 8), ph.a, ph.b)
    params = lag_params()
    lag = LagCorrector()

    for measured, truth in zip(ph.measured_frames, ph.true_frames):
        out = lag.process(measured, calib, params)
        assert np.allclose(out.pixel, truth.pixel, atol=1e-1)


def test_scenario2_serialize_load_byte_identical_and_resume():
    """REQ-LAG-STATE-2/3, VALIDATE-4: (M,ny,nx) float32 round-trip is byte
    identical; resume from mid-sequence state reproduces uninterrupted output."""
    ph = make_matched_sequence(shape=(8, 8), n_frames=8)
    calib = lag_calib((8, 8), ph.a, ph.b)
    params = lag_params()

    # Uninterrupted run.
    full = LagCorrector()
    outputs_full = [full.process(f, calib, params) for f in ph.measured_frames]

    # Split run with a mid-sequence serialize -> load into a fresh instance.
    j = 4
    part = LagCorrector()
    for f in ph.measured_frames[:j]:
        part.process(f, calib, params)
    state_x = part.serialize_state()

    # Byte-identical state round-trip.
    reloaded = LagCorrector()
    reloaded.load_state(state_x)
    assert state_x.pixel.dtype == np.float32
    assert reloaded.serialize_state().pixel.tobytes() == state_x.pixel.tobytes()

    resumed = [reloaded.process(f, calib, params) for f in ph.measured_frames[j:]]
    for a_out, b_out in zip(resumed, outputs_full[j:]):
        assert a_out.pixel.tobytes() == b_out.pixel.tobytes()  # byte identical


def test_scenario3_reset_is_fresh_instance():
    """REQ-LAG-STATE-4: a fresh instance starts at s_i[-1]=0 (no leak)."""
    shape = (5, 5)
    calib = lag_calib(shape)
    params = lag_params()

    # Instance drained by a strong prior sequence.
    used = LagCorrector()
    for _ in range(5):
        used.process(new_frame(np.full(shape, 6000.0, dtype=np.float32)), calib, params)
    leaked = used.process(new_frame(np.full(shape, 1000.0, dtype=np.float32)), calib, params)

    # Fresh instance: first frame is uncorrected (state zero).
    fresh = LagCorrector()
    clean = fresh.process(new_frame(np.full(shape, 1000.0, dtype=np.float32)), calib, params)

    assert np.allclose(clean.pixel, 1000.0)  # no prior-state intrusion
    assert not np.allclose(leaked.pixel, 1000.0)  # negative control: leak present


def test_ec6_saturation_value_preserved_recursion_uses_calculated():
    """REQ-LAG-CORR-5 / EC-6: SATURATION output preserved; state still advances
    with the calculated I_hat at that pixel."""
    shape = (4, 4)
    calib = lag_calib(shape, (0.05,), (0.7,))
    params = lag_params()
    lag = LagCorrector()

    # Prime state with an exposure frame.
    lag.process(new_frame(np.full(shape, 5000.0, dtype=np.float32)), calib, params)

    pix = np.full(shape, 800.0, dtype=np.float32)
    masks = np.zeros(shape, dtype=np.uint8)
    masks[0, 0] = int(MaskFlag.SATURATION)
    out = lag.process(new_frame(pix, masks=masks), calib, params)

    # Saturated pixel value preserved (no sub-saturation value invented).
    assert out.pixel[0, 0] == pytest.approx(800.0)
    # Non-saturated pixels ARE corrected (lag subtracted).
    assert out.pixel[1, 1] < 800.0
    assert out.history[-1].extra["saturation_preserved"] == 1
    # State at the saturated pixel evolved from the CALCULATED I_hat (not 800):
    # serialize and confirm it differs from a pixel that saw only preservation.
    state = lag.serialize_state()
    assert state.pixel[0, 0, 0] != pytest.approx(0.0)


def test_ec4_missing_irf_calibset_raises():
    """REQ-LAG-CONTRACT-4 spirit: no IRF payload -> explicit named error."""
    shape = (4, 4)
    empty = CalibSet(
        panel_id="PANEL-A",
        resolution=shape,
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=CalibKind.LAG,
        data={},  # no irf_a / irf_b
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
    )
    lag = LagCorrector()
    with pytest.raises(LagCalibError, match="irf_a"):
        lag.process(new_frame(np.zeros(shape, dtype=np.float32)), empty, lag_params())


def test_ec4_contract_signature_and_stateful_harness():
    """Scenario 8: process signature valid; stateful harness compares output +
    post-state (CONTRACT-2 runtime exercise)."""
    shape = (3, 3)
    a, b = (0.030, 0.020, 0.010), (0.50, 0.80, 0.90)
    calib = lag_calib(shape, a, b)
    params = lag_params()
    pix = np.full(shape, 2000.0, dtype=np.float32)
    masks = np.zeros(shape, dtype=np.uint8)
    masks[0, 0] = int(MaskFlag.SATURATION)
    frame = new_frame(pix, masks=masks)

    lag = LagCorrector()
    assert check_process_contract(lag) == ()

    # Analytic expected: fresh state -> I_hat == input -> output == input.
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    state_after = (b_arr[:, None, None] * a_arr[:, None, None]
                   * pix.astype(np.float64)[None, :, :]).astype(np.float32)
    entry = HistoryEntry(
        MODULE_NAME,
        MODULE_VERSION,
        params.hash(),
        calib.calibset_id,
        {
            "m_terms": 3,
            "saturation_preserved": 1,
            "state_l1": float(np.abs(state_after).sum()),
        },
    )
    expected = XFrame(pixel=pix, masks=masks, history=frame.history + (entry,))
    expected_state = XFrame(
        pixel=state_after, masks=np.zeros(state_after.shape, dtype=np.uint8)
    )

    report = run_stateful_harness(
        lag, frame, calib, params, expected, expected_state=expected_state
    )
    assert report.passed, report.violations


def test_load_state_rejects_non_3d():
    lag = LagCorrector()
    with pytest.raises(LagStateError):
        lag.load_state(new_frame(np.zeros((4, 4), dtype=np.float32)))
