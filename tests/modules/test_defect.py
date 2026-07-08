"""Defect module: Scenario 6, 8, EC-2, EC-3, DEFECT-8 (REQ-CORR-DEFECT-*)."""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.mask_ops import DefectMorphology, label_components
from common.xframe import MaskFlag, new_frame
from modules import defect
from modules.defect import DefectMapRefused, DefectMapSchemaError
from tests.modules.phantoms.corrections import EV, corr_params, defect_calib


def _linear_bg(shape):
    ny, nx = shape
    r, c = np.mgrid[0:ny, 0:nx].astype(np.float64)
    return 1000.0 + 5.0 * r + 3.0 * c


def _scene():
    shape = (64, 64)
    bg = _linear_bg(shape)
    morph = np.full(shape, DefectMorphology.NORMAL, dtype=np.int8)
    morph[10, 10] = DefectMorphology.SINGLE
    morph[20, 10:18] = DefectMorphology.LINE
    morph[30:32, 30:32] = DefectMorphology.CLUSTER

    pixel = bg.copy()
    defect_coords = [(10, 10)] + [(20, c) for c in range(10, 18)]
    defect_coords += [(30, 30), (30, 31), (31, 30), (31, 31)]
    handoff = (40, 40)
    for (r, c) in defect_coords + [handoff]:
        pixel[r, c] = 0.0  # corrupt the defective pixels

    masks = np.zeros(shape, dtype=np.uint8)
    masks[handoff] = int(MaskFlag.DEFECT)  # gain hand-off, no map classification

    frame = new_frame(pixel.astype(np.float32), masks)
    return frame, defect_calib(morph), bg, defect_coords, handoff


def test_scenario6_map_interpolation_and_flags():
    frame, calib, bg, coords, handoff = _scene()
    out = defect.process(frame, calib, corr_params())

    for (r, c) in coords:
        assert out.pixel[r, c] == pytest.approx(bg[r, c], abs=1.5)
        assert out.masks[r, c] & int(MaskFlag.INTERPOLATION)
        assert out.masks[r, c] & int(MaskFlag.DEFECT)


def test_defect8_gain_handoff_pixel_single_interpolated():
    frame, calib, bg, coords, handoff = _scene()
    out = defect.process(frame, calib, corr_params())

    r, c = handoff
    assert out.pixel[r, c] == pytest.approx(bg[r, c], abs=1.5)
    assert out.masks[r, c] & int(MaskFlag.INTERPOLATION)


def test_scenario8_no_residual_visible_cluster():
    frame, calib, bg, coords, handoff = _scene()
    out = defect.process(frame, calib, corr_params())

    deviation = np.abs(np.asarray(out.pixel, dtype=np.float64) - bg)
    residual = deviation > 5.0
    _, n_clusters = label_components(residual, connectivity=8)
    assert n_clusters <= EV["ev103_residual_cluster_max"]


def test_ec2a_oversize_cluster_refused():
    shape = (16, 16)
    morph = np.full(shape, DefectMorphology.NORMAL, dtype=np.int8)
    morph[2:8, 2:8] = DefectMorphology.CLUSTER  # 36 px > C_max 25
    frame = new_frame(_linear_bg(shape).astype(np.float32))

    with pytest.raises(DefectMapRefused):
        defect.process(frame, defect_calib(morph), corr_params())


def test_ec2b_schema_violation_missing_key_refused():
    shape = (8, 8)
    frame = new_frame(_linear_bg(shape).astype(np.float32))
    bad = CalibSet(
        panel_id="PANEL-A",
        resolution=shape,
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=CalibKind.DEFECT,
        data={"wrong_key": np.zeros(shape, dtype=np.int8)},
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
    )
    with pytest.raises(DefectMapSchemaError):
        defect.process(frame, bad, corr_params())


def test_ec2b_schema_violation_invalid_label_refused():
    shape = (8, 8)
    morph = np.zeros(shape, dtype=np.int8)
    morph[0, 0] = 9  # not a valid morphology label
    frame = new_frame(_linear_bg(shape).astype(np.float32))
    with pytest.raises(DefectMapSchemaError):
        defect.process(frame, defect_calib(morph), corr_params())


def test_ec3_all_defect_no_fabrication():
    shape = (3, 3)
    morph = np.full(shape, DefectMorphology.CLUSTER, dtype=np.int8)
    pixel = np.full(shape, 1234.0, dtype=np.float32)
    frame = new_frame(pixel)

    out = defect.process(frame, defect_calib(morph), corr_params())

    # No valid normal neighbour anywhere: values preserved, DEFECT kept,
    # INTERPOLATION never set (EC-3 post-conditions).
    assert np.array_equal(out.pixel, pixel)
    assert np.all(out.masks & int(MaskFlag.DEFECT))
    assert not np.any(out.masks & int(MaskFlag.INTERPOLATION))
