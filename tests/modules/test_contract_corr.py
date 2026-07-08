"""Scenario 11 + EC-1: process contract, harness, calibration gate refusal."""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind
from common.contract import check_process_contract, run_harness
from common.xframe import MaskFlag, new_frame
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


@pytest.mark.parametrize(
    "module,stage",
    [(offset, "offset"), (gain, "gain"), (defect, "defect")],
)
def test_scenario11_signature_and_harness(module, stage):
    assert check_process_contract(module) == ()
    frame, params = _frame(), corr_params()
    calib = _calibs()[stage]
    expected = module.process(frame, calib, params)
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
