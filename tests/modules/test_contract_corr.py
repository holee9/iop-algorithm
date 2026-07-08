"""Scenario 11 + EC-1: process contract, harness, calibration gate refusal."""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind
from common.contract import check_process_contract, run_harness
from common.xframe import HistoryEntry, MaskFlag, XFrame, new_frame
from modules import defect, gain, offset
from pipeline.orchestrator import (
    CalibrationError,
    PipelineDefinition,
    run_pipeline,
)
from tests.modules.phantoms.corrections import (
    corr_params,
    defect_calib,
    gain_calib,
    offset_calib,
)

_SHAPE = (16, 16)


def _frame():
    return new_frame(np.full(_SHAPE, 2000.0, dtype=np.float32))


def _calibs():
    return {
        "offset": offset_calib(np.full(_SHAPE, 100.0)),
        "gain": gain_calib(np.full(_SHAPE, 1.25)),
        "defect": defect_calib(np.zeros(_SHAPE, dtype=np.int8)),
    }


def _expected(stage, frame, calib, params):
    """Independent analytic expected XFrame (review finding 9).

    Pixel/mask/history are derived from first principles with plain numpy, NOT
    by calling module.process, so the harness comparison is non-circular. The
    input fixture is uniform 2000.0 with an all-NORMAL defect map, so offset
    subtracts 100 (no clamp), gain multiplies by 1.25 (no clamp / no hand-off),
    and defect leaves the frame untouched.
    """
    base = np.full(_SHAPE, 2000.0, dtype=np.float64)
    masks = frame.masks  # no stage flags any pixel for this fixture
    if stage == "offset":
        pix = base - 100.0
        entry = HistoryEntry(
            "offset", "1.0.0", params.hash(), calib.calibset_id,
            {"neg_clamp_rate": 0.0},
        )
    elif stage == "gain":
        pix = base * 1.25
        entry = HistoryEntry(
            "gain", "1.0.0", params.hash(), calib.calibset_id,
            {"upper_clamp_rate": 0.0, "invalid_gain_rate": 0.0},
        )
    else:  # defect: all-NORMAL map, nothing corrected
        pix = base
        entry = HistoryEntry(
            "defect", "1.0.0", params.hash(), calib.calibset_id,
            {"defect_pixels": 0, "interpolated_pixels": 0, "uncorrected_pixels": 0},
        )
    return XFrame(
        pixel=pix.astype(np.float32),
        masks=masks,
        noise=frame.noise,
        history=frame.history + (entry,),
    )


@pytest.mark.parametrize(
    "module,stage",
    [(offset, "offset"), (gain, "gain"), (defect, "defect")],
)
def test_scenario11_signature_and_harness(module, stage):
    assert check_process_contract(module) == ()
    frame, params = _frame(), corr_params()
    calib = _calibs()[stage]
    expected = _expected(stage, frame, calib, params)
    report = run_harness(module, frame, calib, params, expected)
    assert report.passed, report.violations
    # Deterministic reproduction: input frame unchanged (immutability).
    assert np.array_equal(frame.pixel, np.full(_SHAPE, 2000.0, dtype=np.float32))


def test_scenario11_fixed_order_subsequence():
    # offset -> gain -> defect is a valid canonical subsequence.
    definition = PipelineDefinition(("offset", "gain", "defect"))
    assert definition.stages == ("offset", "gain", "defect")


def test_ec1_kind_stage_miswire_refused():
    frame = _frame()
    registry = {"offset": offset.process, "gain": gain.process}
    calib_map = _calibs()
    # Wire a GAIN CalibSet into the offset stage -> gate refuses.
    calib_map["offset"] = gain_calib(np.full(_SHAPE, 1.25))
    with pytest.raises(CalibrationError):
        run_pipeline(
            frame,
            PipelineDefinition(("offset", "gain")),
            registry,
            calib_map,
            {"offset": corr_params(), "gain": corr_params()},
        )


def test_ec1_missing_calib_refused():
    frame = _frame()
    registry = {"offset": offset.process}
    with pytest.raises(CalibrationError):
        run_pipeline(
            frame,
            PipelineDefinition(("offset",)),
            registry,
            {},  # no CalibSet for offset
            {"offset": corr_params()},
        )
