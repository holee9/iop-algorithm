"""Regression tests for the code-review defects found in the SPEC-LNSG-001 T3
modules (commit 7ab0338): geometry mask transport, line-noise MAD==0 exclusion,
offset required saturation threshold, line-noise saturation protection, and
dilate_mask fractional-radius validation.

Saturation idempotency / band independence (findings 4/6/7) live in
test_saturation.py; phantom-quality findings (9/10) live alongside the
line-noise / geometry phantom tests.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.mask_ops import dilate_mask
from common.xframe import MaskFlag, new_frame
from modules import geometry, line_noise, offset
from tests.modules.phantoms.corrections import corr_params, offset_calib
from tests.modules.phantoms.linesat import (
    geometry_calib,
    line_noise_calib,
    lnsg_params,
    make_line_noise_phantom,
)


# -- [1] geometry: mask stack transported through the inverse warp -----------


def _const_shift_calib(shape, shift_col):
    """CalibSet(OTHER) encoding a CONSTANT forward column displacement of
    `shift_col` px (degree-1 poly, constant term only)."""
    degree = 1
    cx = np.zeros((degree + 1, degree + 1), dtype=np.float64)
    cy = np.zeros((degree + 1, degree + 1), dtype=np.float64)
    cx[0, 0] = float(shift_col)  # D_col == shift_col everywhere
    return geometry_calib(shape, cx, cy, residual=float(abs(shift_col)))


def test_geometry_transports_mask_stack_and_flags_border():
    """Finding 1: active geometry correction must resample the mask stack with
    the same inverse warp as the pixels (flags move with pixels), and border-
    filled output pixels (source outside the frame) must be flagged DEFECT."""
    shape = (32, 32)
    shift = 6
    pix = np.full(shape, 100.0, dtype=np.float32)
    masks = np.zeros(shape, dtype=np.uint8)
    pix[8:15, 8:15] = 65535.0  # saturated block
    masks[8:15, 8:15] = int(MaskFlag.SATURATION)
    frame = new_frame(pix, masks=masks)

    params = lnsg_params(
        geometry_poly_degree=1,
        geometry_activation_residual_px=1.0,
        geometry_inverse_iters=4,
    )
    out = geometry.process(frame, _const_shift_calib(shape, shift), params)

    out_sat = (np.asarray(out.masks) & int(MaskFlag.SATURATION)) != 0
    out_defect = (np.asarray(out.masks) & int(MaskFlag.DEFECT)) != 0

    # corrected[r, c] = observed[r, c - shift] -> block moves +shift in columns.
    assert out_sat[11, 17]  # flag followed the pixels to the shifted position
    assert not out_sat[11, 8]  # original edge no longer saturated (pulled bg)
    # Flags coincide with the saturated pixel VALUES (mask/pixel consistency).
    assert np.asarray(out.pixel)[11, 17] > 60000.0
    # Border columns 0..shift-1 pull from source outside the frame -> DEFECT.
    assert np.all(out_defect[:, 0:shift])
    # The saturated pixel count is preserved (block stays inside the frame).
    assert np.count_nonzero(out_sat) == 7 * 7


# -- [2] line_noise: k*MAD exclusion must still fire when MAD == 0 -----------


def test_line_noise_reference_excludes_deviant_row_when_mad_zero():
    """Finding 2: identical reference rows give MAD==0; a single deviating row
    is still contamination and must be excluded (strict |m-med|>0), not passed
    through as a bogus row correction."""
    shape = (20, 10)
    image = np.zeros(shape, dtype=np.float64)
    image[:, :4] = 50.0  # identical reference across every row -> MAD == 0
    image[:, 4:] = 1050.0  # irradiated background (== 1000 after ref removal)
    image[10, :4] = 550.0  # ONE contaminated reference row (metal spike)

    reference = np.zeros(shape, dtype=bool)
    reference[:, :4] = True
    frame = new_frame(image.astype(np.float32))
    calib = line_noise_calib(shape, reference=reference)

    out = line_noise.process(frame, calib, lnsg_params())
    corrected = np.asarray(out.pixel, dtype=np.float64)

    assert out.history[-1].extra["path"] == "reference"
    assert out.history[-1].extra["contaminated_rows"] >= 1.0
    # Row 10 was excluded + interpolated to the median (50), not subtracted as
    # 550, so its irradiated region recovers the true background (~1000).
    assert abs(float(np.mean(corrected[10, 4:])) - 1000.0) < 5.0


# -- [3] offset: raw_saturation_threshold is a REQUIRED param ----------------


def test_offset_requires_raw_saturation_threshold():
    """Finding 3: no silent hardcoded default (SWR-000-5). Missing key raises an
    explicit error naming the parameter."""
    frame = new_frame(np.full((8, 8), 3000.0, dtype=np.float32))
    params_missing = lnsg_params()
    # Strip the key to simulate a caller that forgot to inject it.
    from common.contract import Params

    stripped = {
        k: v
        for k, v in params_missing.values.items()
        if k != "raw_saturation_threshold"
    }
    with pytest.raises(ValueError, match="raw_saturation_threshold"):
        offset.process(frame, offset_calib(np.full((8, 8), 50.0)), Params(stripped))


def test_offset_uses_injected_raw_saturation_threshold():
    """The injected [B] threshold drives detection (no invented default)."""
    shape = (8, 8)
    raw = np.full(shape, 3000.0, dtype=np.float32)
    raw[1, 1] = 64000.0
    frame = new_frame(raw)
    out = offset.process(
        frame,
        offset_calib(np.full(shape, 50.0)),
        corr_params(raw_saturation_threshold=60000.0),
    )
    sat = (np.asarray(out.masks) & int(MaskFlag.SATURATION)) != 0
    assert sat[1, 1] and np.count_nonzero(sat) == 1


# -- [5] line_noise: SATURATION pixels are left UNMODIFIED -------------------


def test_line_noise_leaves_saturated_pixels_unmodified():
    """Finding 5: the line-noise subtraction must not alter SATURATION-flagged
    pixels; clamp semantics (65535) must survive to the saturation stage
    (vs SWR-602 no-restoration). DEFECT/INTERPOLATION pixels may be corrected."""
    ph = make_line_noise_phantom(shape=(64, 64))
    pix = ph.observed.copy()
    masks = np.zeros(pix.shape, dtype=np.uint8)
    pix[30, 30] = 65535.0
    masks[30, 30] = int(MaskFlag.SATURATION)
    frame = new_frame(pix, masks=masks)

    out = line_noise.process(frame, line_noise_calib(frame.shape), lnsg_params())
    # The saturated pixel value is untouched by line-noise subtraction.
    assert float(np.asarray(out.pixel)[30, 30]) == 65535.0


# -- [8] dilate_mask: fractional radius must raise, not flood -----------------


def test_dilate_mask_rejects_fractional_radius():
    """Finding 8: a radius in (0,1) truncated to iterations=0, which scipy reads
    as 'dilate until convergence' and floods the frame. It must raise instead."""
    mask = np.zeros((16, 16), dtype=bool)
    mask[8, 8] = True
    with pytest.raises(ValueError, match="radius"):
        dilate_mask(mask, 0.5)
    # A valid positive integer radius still works.
    out = dilate_mask(mask, 2)
    assert out[8, 8] and int(np.count_nonzero(out)) == 25
