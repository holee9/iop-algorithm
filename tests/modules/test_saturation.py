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
    masks_before = np.asarray(frame.masks).copy()  # snapshot BEFORE process
    out = saturation.process(frame, saturation_calib(frame.shape), lnsg_params())

    out_sat = (np.asarray(out.masks) & int(MaskFlag.SATURATION)) != 0
    assert np.all(out_sat[sat])  # every saturated pixel retained
    # Input mask stack unchanged vs the pre-process snapshot (DATA-6).
    assert np.array_equal(np.asarray(frame.masks), masks_before)
    assert out.history[-1].module_name == "saturation"


def test_saturation_stage_is_idempotent():
    """Re-running the saturation stage yields identical output: the band is
    flagged SATURATION_BAND (not SATURATION), so the second run dilates only the
    original SATURATION core and produces the same band (no 2px-per-run growth,
    review finding 4)."""
    frame, _ = _sat_frame()
    calib = saturation_calib(frame.shape)
    params = lnsg_params(saturation_band_width=2)

    once = saturation.process(frame, calib, params)
    twice = saturation.process(once, calib, params)

    assert np.array_equal(np.asarray(once.masks), np.asarray(twice.masks))
    assert (
        once.history[-1].extra["boundary_band_pixels"]
        == twice.history[-1].extra["boundary_band_pixels"]
    )


def _expected_band(sat: np.ndarray, width: int) -> np.ndarray:
    """Independent brute-force boundary band: pixels within Chebyshev distance
    `width` of a saturated core pixel, excluding the core itself. Computed here
    without dilate_mask so the test does not validate the module against its own
    dilation implementation (review finding 7)."""
    ny, nx = sat.shape
    core = np.argwhere(sat)
    expected = np.zeros(sat.shape, dtype=bool)
    for r in range(ny):
        for c in range(nx):
            if sat[r, c]:
                continue
            # Chebyshev distance to nearest core pixel.
            if core.size == 0:
                continue
            cheb = np.maximum(np.abs(core[:, 0] - r), np.abs(core[:, 1] - c)).min()
            if cheb <= width:
                expected[r, c] = True
    return expected


def test_scenario4_boundary_band_marked():
    """REQ-LNSG-SAT-2: a W_band boundary band around the saturated region is
    flagged SATURATION_BAND (dilation approximation, spec decision 3)."""
    frame, sat = _sat_frame()
    params = lnsg_params(saturation_band_width=2)
    out = saturation.process(frame, saturation_calib(frame.shape), params)

    band = (np.asarray(out.masks) & int(MaskFlag.SATURATION_BAND)) != 0
    assert band.any()
    assert out.history[-1].extra["boundary_band_pixels"] == int(np.count_nonzero(band))
    # Band == independent brute-force Chebyshev band (not the module's own
    # dilate_mask), and never overlaps the saturated core.
    expected = _expected_band(sat, 2)
    assert np.array_equal(band, expected)
    assert not np.any(band & sat)


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
