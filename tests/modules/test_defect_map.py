"""Defect-map builder: Scenario 9 + C_max negative (REQ-CORR-DEFECT-6, VALIDATE-7)."""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind
from common.mask_ops import DefectMorphology
from metrics.defect_map import DefectMapBuildRefused, build_defect_map
from tests.modules.phantoms.corrections import EV, corr_params, make_defect_stacks


def _build(stacks):
    return build_defect_map(
        stacks.dark_frames,
        stacks.flat_frames,
        corr_params(),
        panel_id="PANEL-A",
        resolution=stacks.planted.shape,
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        created_at="2026-07-09",
    )


def test_scenario9_builder_miss_rate_within_ev103():
    stacks = make_defect_stacks(
        singles=((5, 5), (50, 55)),
        lines=((20, 10, 8),),
        clusters=((35, 35, 2, 2),),
    )
    calib = _build(stacks)
    assert calib.kind is CalibKind.DEFECT

    morph = np.asarray(calib.data["class_map"])
    detected = morph != DefectMorphology.NORMAL
    planted = stacks.planted
    missed = int(np.count_nonzero(planted & ~detected))
    n_planted = int(np.count_nonzero(planted))
    miss_rate = missed / n_planted
    assert miss_rate <= EV["ev103_miss_rate_max"], (miss_rate, missed, n_planted)


def test_scenario9_builder_morphology_labels():
    stacks = make_defect_stacks(
        singles=((5, 5),),
        lines=((20, 10, 8),),
        clusters=((35, 35, 2, 2),),
    )
    morph = np.asarray(_build(stacks).data["class_map"])
    assert morph[5, 5] == DefectMorphology.SINGLE
    assert np.all(morph[20, 10:18] == DefectMorphology.LINE)
    assert np.all(morph[35:37, 35:37] == DefectMorphology.CLUSTER)


def test_scenario9_negative_oversize_cluster_refused():
    stacks = make_defect_stacks(singles=(), clusters=((10, 10, 6, 6),))  # 36 px
    with pytest.raises(DefectMapBuildRefused):
        _build(stacks)
