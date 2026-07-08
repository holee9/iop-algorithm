"""Regression tests for the 10 defects found in the independent code review of
the SPEC-CORR-001 T2 correction modules (commit 4451875).

Findings 4/5/6/9/10 are exercised in-place by the amended TC / contract / unit
tests (test_tc_correction, test_contract_corr, test_offset, test_gain); this
module holds the RED-first regressions for the interpolation/classification
findings 1/2/3/7 that had no direct coverage before.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.mask_ops import DefectMorphology
from common.xframe import MaskFlag, new_frame
from metrics.defect_map import (
    DefectMapBuildRefused,
    build_defect_map,
    classify_morphology,
)
from modules import defect, gain
from modules.defect import DefectMapRefused
from tests.modules.phantoms.corrections import (
    corr_params,
    defect_calib,
    gain_calib,
    make_defect_stacks,
)


def _linear_bg(shape, a=1.0, b=100.0, d=1000.0):
    ny, nx = shape
    r, c = np.mgrid[0:ny, 0:nx].astype(np.float64)
    return d + a * r + b * c


# ---------------------------------------------------------------------------
# Finding 1: a solid blob must not be mislabelled LINE and bypass the C_max gate.
# ---------------------------------------------------------------------------


def test_finding1_solid_blob_refused_by_builder():
    # 10x10 = 100 px dead blob (> C_max 25). Every row-run reaches line_min=8,
    # but the blob is 10 px thick, so the THIN-run rule denies LINE and the
    # blob reaches the C_max cluster gate.
    stacks = make_defect_stacks(singles=(), clusters=((10, 10, 10, 10),))
    with pytest.raises(DefectMapBuildRefused):
        build_defect_map(
            stacks.dark_frames,
            stacks.flat_frames,
            corr_params(),
            panel_id="PANEL-A",
            resolution=stacks.planted.shape,
            valid_from="2026-01-01",
            valid_until="2027-01-01",
        )


def test_finding1_solid_blob_labelled_line_refused_by_module():
    # Hand-crafted map: a 10x10 blob mislabelled LINE must still be gated as an
    # oversize cluster at consumption time (thinness rule applied module-side).
    shape = (20, 20)
    morph = np.full(shape, DefectMorphology.NORMAL, dtype=np.int8)
    morph[5:15, 5:15] = DefectMorphology.LINE
    frame = new_frame(_linear_bg(shape).astype(np.float32))
    with pytest.raises(DefectMapRefused):
        defect.process(frame, defect_calib(morph), corr_params())


def test_finding1_genuine_thin_line_still_line():
    defect_mask = np.zeros((30, 30), dtype=bool)
    defect_mask[5, 5:25] = True  # 1x20 thin horizontal run
    morph = classify_morphology(defect_mask, line_min=8, cmax=25, line_max_width=1)
    assert np.all(morph[5, 5:25] == DefectMorphology.LINE)
    assert not np.any(morph == DefectMorphology.CLUSTER)


# ---------------------------------------------------------------------------
# Finding 2: crossing H+V lines get per-pixel orientation, not one wrong axis.
# ---------------------------------------------------------------------------


def test_finding2_crossing_lines_interpolate_along_each_arm():
    shape = (40, 40)
    bg = _linear_bg(shape, a=2.0, b=3.0, d=500.0)  # smooth linear gradient
    morph = np.full(shape, DefectMorphology.NORMAL, dtype=np.int8)
    # Horizontal arm (row 20, cols 10..30) and vertical arm (col 20, rows 10..30).
    h_cells = [(20, c) for c in range(10, 31)]
    v_cells = [(r, 20) for r in range(10, 31)]
    for r, c in h_cells + v_cells:
        morph[r, c] = DefectMorphology.LINE

    pixel = bg.copy()
    for r, c in h_cells + v_cells:
        pixel[r, c] = 0.0  # corrupt every line pixel
    frame = new_frame(pixel.astype(np.float32))

    out = defect.process(frame, defect_calib(morph), corr_params())

    # Both arms (excluding the crossing point) must recover the gradient: the
    # horizontal arm interpolates vertically, the vertical arm horizontally.
    for r, c in h_cells + v_cells:
        if (r, c) == (20, 20):
            continue
        assert out.pixel[r, c] == pytest.approx(bg[r, c], abs=1.0), (r, c)


# ---------------------------------------------------------------------------
# Finding 3: cluster one-sided fallback picks the NEAREST anchor, not first-axis.
# ---------------------------------------------------------------------------


def test_finding3_cluster_fallback_uses_nearest_anchor():
    shape = (12, 12)
    ny, nx = shape
    # Column-dominant gradient so vertical-near and horizontal-far anchors differ
    # sharply in value.
    bg = _linear_bg(shape, a=1.0, b=100.0, d=1000.0)
    morph = np.full(shape, DefectMorphology.NORMAL, dtype=np.int8)

    target = (0, nx - 1)  # top-right corner
    far_len = 8
    # Dead cluster along the top row extending left from the corner: the only
    # horizontal anchor is far; the vertical anchor one row down is adjacent.
    dead = [(0, nx - 1 - k) for k in range(far_len)]
    for r, c in dead:
        morph[r, c] = DefectMorphology.CLUSTER

    pixel = bg.copy()
    for r, c in dead:
        pixel[r, c] = 0.0
    frame = new_frame(pixel.astype(np.float32))

    out = defect.process(frame, defect_calib(morph), corr_params())

    near_vertical = bg[1, nx - 1]  # adjacent anchor one row below the corner
    far_horizontal = bg[0, nx - 1 - far_len]  # distant anchor along the row
    assert out.pixel[target] == pytest.approx(near_vertical, abs=0.5)
    # The far horizontal anchor (what the old first-axis fallback would pick) is
    # far away in value; the fix must NOT land there.
    assert abs(float(out.pixel[target]) - far_horizontal) > 50.0


# ---------------------------------------------------------------------------
# Finding 7: saturated pixels are excluded from interpolation anchors.
# ---------------------------------------------------------------------------


def test_finding7_gain_flags_clamped_pixels_saturation():
    shape = (4, 4)
    i1 = np.full(shape, 50000.0, dtype=np.float32)
    g = np.full(shape, 1.0, dtype=np.float64)
    g[:, 2:] = 2.0  # right half -> 100000 -> clamp 65535
    out = gain.process(new_frame(i1), gain_calib(g), corr_params())
    assert np.all(out.masks[:, 2:] & int(MaskFlag.SATURATION))
    assert not np.any(out.masks[:, :2] & int(MaskFlag.SATURATION))


def test_finding7_defect_ignores_saturated_anchors():
    shape = (3, 3)
    # Saturated region at 65535 everywhere except a genuine low-value column 0.
    pixel = np.full(shape, 65535.0, dtype=np.float32)
    pixel[:, 0] = 1000.0
    masks = np.zeros(shape, dtype=np.uint8)
    masks[pixel == 65535.0] = int(MaskFlag.SATURATION)

    morph = np.full(shape, DefectMorphology.NORMAL, dtype=np.int8)
    morph[1, 1] = DefectMorphology.SINGLE  # defect adjacent to the saturated region

    out = defect.process(new_frame(pixel, masks), defect_calib(morph), corr_params())

    # Only the genuine column-0 neighbours may anchor the interpolation; the
    # clipped 65535 neighbours must be ignored (else the value shoots toward
    # 65535).
    assert out.pixel[1, 1] == pytest.approx(1000.0, abs=1.0)
    assert out.masks[1, 1] & int(MaskFlag.INTERPOLATION)
