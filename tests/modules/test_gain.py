"""Gain module: Scenarios 3, 4, 5, 13 (REQ-CORR-GAIN-1/2/3/4)."""

from __future__ import annotations

import numpy as np
import pytest

from common.xframe import MaskFlag, new_frame
from modules import gain
from tests.modules.phantoms.corrections import corr_params, gain_calib


def test_scenario3_flatfield_normalization_and_history():
    shape = (16, 16)
    i1 = np.full(shape, 2000.0, dtype=np.float32)
    g = np.full(shape, 1.2, dtype=np.float64)
    frame = new_frame(i1)
    calib = gain_calib(g)

    out = gain.process(frame, calib, corr_params())

    assert np.allclose(out.pixel, 2400.0, atol=1.0)
    assert np.array_equal(frame.pixel, i1)  # immutable input
    assert out.history[-1].module_name == "gain"
    assert out.history[-1].calibset_id == calib.calibset_id


def test_scenario4_upper_clamp_rate_in_history():
    shape = (10, 10)
    i1 = np.full(shape, 50000.0, dtype=np.float32)
    g = np.full(shape, 1.0, dtype=np.float64)
    g[:, 5:] = 2.0  # right half -> 100000 -> clamp to 65535
    frame = new_frame(i1)

    out = gain.process(frame, gain_calib(g), corr_params())

    assert np.all(out.pixel[:, 5:] == 65535.0)
    assert np.allclose(out.pixel[:, :5], 50000.0, atol=1.0)
    assert out.history[-1].extra["upper_clamp_rate"] == repr(0.5)


def test_scenario5_out_of_range_gain_handed_off_as_defect():
    shape = (8, 8)
    i1 = np.full(shape, 1000.0, dtype=np.float32)
    g = np.full(shape, 1.5, dtype=np.float64)
    g[0, 0] = 3.0  # above gain_max 2.0
    g[1, 1] = 0.2  # below gain_min 0.5
    frame = new_frame(i1)

    out = gain.process(frame, gain_calib(g), corr_params())

    # Out-of-range pixels keep I1 (no gain applied) + DEFECT flag.
    assert out.pixel[0, 0] == pytest.approx(1000.0, abs=1.0)
    assert out.pixel[1, 1] == pytest.approx(1000.0, abs=1.0)
    assert out.masks[0, 0] & int(MaskFlag.DEFECT)
    assert out.masks[1, 1] & int(MaskFlag.DEFECT)
    # In-range pixel gained normally, no DEFECT flag.
    assert out.pixel[2, 2] == pytest.approx(1500.0, abs=1.0)
    assert not (out.masks[2, 2] & int(MaskFlag.DEFECT))


def test_scenario13_optional_multipoint_gain_deferred():
    shape = (4, 4)
    frame = new_frame(np.full(shape, 1000.0, dtype=np.float32))
    calib = gain_calib(np.ones(shape), anchor_gains=np.ones((3,) + shape))

    with pytest.raises(NotImplementedError):
        gain.process(frame, calib, corr_params())
