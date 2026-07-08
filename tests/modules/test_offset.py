"""Offset module: Scenarios 1, 2, 10, 12 (REQ-CORR-OFFSET-1/2/3, VALIDATE-4)."""

from __future__ import annotations

import numpy as np
import pytest

from common.xframe import MaskFlag, new_frame
from modules import offset
from tests.modules.phantoms.corrections import EV, corr_params, offset_calib


def _gradient(shape, hi):
    ny, nx = shape
    row = np.linspace(0.0, hi, nx, dtype=np.float64)
    return np.tile(row, (ny, 1))


def test_scenario1_dark_subtraction_and_history():
    shape = (32, 32)
    signal = np.full(shape, 3000.0, dtype=np.float64)
    o = _gradient(shape, 500.0)
    raw = (signal + o).astype(np.float32)
    frame = new_frame(raw)
    calib = offset_calib(o)

    out = offset.process(frame, calib, corr_params())

    assert np.allclose(out.pixel, signal, atol=0.5)
    # Input immutability: original buffer unchanged.
    assert np.array_equal(frame.pixel, raw)
    assert len(out.history) == len(frame.history) + 1
    entry = out.history[-1]
    assert entry.module_name == "offset"
    assert entry.calibset_id == calib.calibset_id
    assert entry.params_hash == corr_params().hash()


def test_scenario2_negative_clamp_rate_in_history():
    shape = (10, 10)
    raw = np.full(shape, 100.0, dtype=np.float32)
    o = np.zeros(shape, dtype=np.float64)
    o[:, 5:] = 500.0  # right half -> negative -> clamped to 0
    frame = new_frame(raw)

    out = offset.process(frame, offset_calib(o), corr_params())

    assert np.all(out.pixel[:, 5:] == 0.0)
    assert np.allclose(out.pixel[:, :5], 100.0, atol=0.5)
    expected_rate = 0.5
    # extra stores numerics natively (review finding 10), not as repr() strings.
    assert out.history[-1].extra["neg_clamp_rate"] == expected_rate
    assert isinstance(out.history[-1].extra["neg_clamp_rate"], float)


def test_scenario10_dark_residual_within_sigma_fraction():
    shape = (16, 16)
    sigma_d = np.full(shape, 10.0, dtype=np.float32)
    o = _gradient(shape, 200.0)
    # Small positive residual so no clamping bias contaminates the hook.
    residual = 0.02 * 10.0
    dark_raw = (o + residual).astype(np.float32)
    frame = new_frame(dark_raw)

    out = offset.process(frame, offset_calib(o, sigma_d=sigma_d), corr_params())

    resid_mean = float(np.mean(out.pixel))
    threshold = EV["offset_residual_frac"] * float(np.median(sigma_d))
    assert resid_mean <= threshold, (resid_mean, threshold)
    # sigma_d initialized the noise model from calibration (SWR-101).
    assert out.noise.sigma == pytest.approx(10.0)


def test_raw_saturation_flagged_before_subtraction():
    """REQ-CORR-OFFSET-4: pixels with I_raw >= S_th get the SATURATION flag,
    detected on the raw input BEFORE dark subtraction."""
    shape = (8, 8)
    s_th = 60000.0
    raw = np.full(shape, 3000.0, dtype=np.float32)
    raw[2, 3] = 65000.0  # >= S_th -> raw-saturated
    raw[5, 6] = 64000.0  # >= S_th -> raw-saturated
    o = np.full(shape, 100.0, dtype=np.float64)
    frame = new_frame(raw)

    out = offset.process(
        frame, offset_calib(o), corr_params(raw_saturation_threshold=s_th)
    )

    sat = (out.masks & int(MaskFlag.SATURATION)) != 0
    assert sat[2, 3] and sat[5, 6]
    assert np.count_nonzero(sat) == 2
    # Detection is on I_raw: the saturated pixels are still subtracted/clamped
    # normally (no restoration here), and the raw_sat_rate is on the history.
    assert out.history[-1].extra["raw_sat_rate"] == 2.0 / raw.size
    # Input immutability preserved.
    assert np.array_equal(frame.pixel, raw)


def test_raw_saturation_default_threshold_no_false_positive():
    """Sub-threshold frames raise no SATURATION flag under the [B] default."""
    shape = (8, 8)
    raw = np.full(shape, 3000.0, dtype=np.float32)
    frame = new_frame(raw)
    out = offset.process(frame, offset_calib(np.zeros(shape)), corr_params())
    assert np.count_nonzero(out.masks & int(MaskFlag.SATURATION)) == 0
    assert out.history[-1].extra["raw_sat_rate"] == 0.0


def test_scenario12_optional_dynamic_offset_applied():
    shape = (8, 8)
    o = _gradient(shape, 100.0)
    delta = np.full(shape, 20.0, dtype=np.float64)
    signal = np.full(shape, 2000.0, dtype=np.float64)
    raw = (signal + o + delta).astype(np.float32)
    frame = new_frame(raw)

    out = offset.process(frame, offset_calib(o, delta_o=delta), corr_params())

    assert np.allclose(out.pixel, signal, atol=0.5)
