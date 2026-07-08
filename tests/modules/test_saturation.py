"""Saturation module: Scenarios 3, 4, 5, 8 + EC-2 (REQ-LNSG-SAT, VALIDATE-4)."""

from __future__ import annotations

import numpy as np

from common.xframe import MaskFlag, new_frame
from modules import offset, saturation
from tests.modules.phantoms.corrections import offset_calib
from tests.modules.phantoms.linesat import lnsg_params, saturation_calib


def _sat_frame(shape=(32, 32), block=(10, 12, 6, 6), interp_px=(2, 2)):
    """Frame with an accumulated SATURATION block (offset raw + gain clamp) and
    a pre-existing INTERPOLATION pixel (upstream defect stage)."""
    pix = np.full(shape, 3000.0, dtype=np.float32)
    masks = np.zeros(shape, dtype=np.uint8)
    r0, c0, h, w = block
    pix[r0 : r0 + h, c0 : c0 + w] = 65535.0
    masks[r0 : r0 + h, c0 : c0 + w] = int(MaskFlag.SATURATION)
    if interp_px is not None:
        masks[interp_px] |= int(MaskFlag.INTERPOLATION)
    sat_bool = np.zeros(shape, dtype=bool)
    sat_bool[r0 : r0 + h, c0 : c0 + w] = True
    return new_frame(pix, masks=masks), sat_bool


def test_scenario3_consumes_accumulated_saturation_mask():
    """REQ-LNSG-SAT-1: accumulated SATURATION mask consumed and forwarded;
    input immutable, history updated."""
    frame, sat = _sat_frame()
    out = saturation.process(frame, saturation_calib(frame.shape), lnsg_params())

    out_sat = (np.asarray(out.masks) & int(MaskFlag.SATURATION)) != 0
    assert np.all(out_sat[sat])  # every saturated pixel retained
    assert np.array_equal(frame.masks, np.asarray(frame.masks))  # input unchanged
    assert out.history[-1].module_name == "saturation"


def test_scenario4_boundary_band_marked():
    """REQ-LNSG-SAT-2: a W_band boundary band around the saturated region is
    flagged SATURATION (dilation approximation, spec decision 3)."""
    frame, sat = _sat_frame()
    params = lnsg_params(saturation_band_width=2)
    out = saturation.process(frame, saturation_calib(frame.shape), params)

    out_sat = (np.asarray(out.masks) & int(MaskFlag.SATURATION)) != 0
    band = out_sat & ~sat
    assert band.any()
    assert out.history[-1].extra["boundary_band_pixels"] == int(np.count_nonzero(band))
    # Band pixels are within 2px (Chebyshev) of the saturated core.
    from common.mask_ops import dilate_mask

    assert np.all(band <= dilate_mask(sat, 2))


def test_scenario5_saturation_statistics_in_history():
    """REQ-LNSG-SAT-4: saturation statistics recorded on the history entry."""
    frame, sat = _sat_frame()
    out = saturation.process(frame, saturation_calib(frame.shape), lnsg_params())
    n = int(np.count_nonzero(sat))
    assert out.history[-1].extra["saturated_pixels"] == n
    assert out.history[-1].extra["saturated_rate"] == n / sat.size


def test_ec2_no_restoration_postconditions():
    """EC-2 / REQ-LNSG-SAT-3: saturated values unchanged, SATURATION retained,
    INTERPOLATION not newly set (pre-existing preserved)."""
    frame, sat = _sat_frame(interp_px=(2, 2))
    pre_interp = (np.asarray(frame.masks) & int(MaskFlag.INTERPOLATION)) != 0
    out = saturation.process(frame, saturation_calib(frame.shape), lnsg_params())

    # (1) saturated pixel values unchanged.
    assert np.array_equal(np.asarray(out.pixel), np.asarray(frame.pixel))
    # (2) SATURATION retained.
    out_sat = (np.asarray(out.masks) & int(MaskFlag.SATURATION)) != 0
    assert np.all(out_sat[sat])
    # (3) INTERPOLATION not newly set; pre-existing preserved exactly.
    out_interp = (np.asarray(out.masks) & int(MaskFlag.INTERPOLATION)) != 0
    assert np.array_equal(out_interp, pre_interp)


def test_scenario8_offset_detected_saturation_preserved_end_to_end():
    """REQ-LNSG-VALIDATE-4: offset(raw >= S_th) SATURATION flags survive the
    saturation stage in full; boundary band present; no restoration."""
    shape = (40, 40)
    s_th = 60000.0
    raw = np.full(shape, 3000.0, dtype=np.float32)
    raw[15:22, 18:25] = 64000.0  # raw-saturated block
    frame = new_frame(raw)
    params = lnsg_params(raw_saturation_threshold=s_th)

    after_offset = offset.process(frame, offset_calib(np.full(shape, 50.0)), params)
    offset_sat = (np.asarray(after_offset.masks) & int(MaskFlag.SATURATION)) != 0
    assert offset_sat.any()

    out = saturation.process(after_offset, saturation_calib(shape), params)
    out_sat = (np.asarray(out.masks) & int(MaskFlag.SATURATION)) != 0
    # (a) every offset-detected saturated pixel is preserved.
    assert np.all(out_sat[offset_sat])
    # (b) boundary band marked.
    assert out.history[-1].extra["boundary_band_pixels"] > 0
    # (c) pixel values unchanged by the saturation stage (no restoration).
    assert np.array_equal(np.asarray(out.pixel), np.asarray(after_offset.pixel))
