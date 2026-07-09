"""T9 engine contract (SPEC-NDT-001 Scenario 1, REQ-NDT-CONTRACT).

The NDT layer is a pure measurement/report layer: it does NOT follow the
process(XFrame, CalibSet, Params) -> XFrame contract, does NOT add a pipeline
stage / CalibKind (T0 surface unchanged), imports only downward (metrics ->
common; no modules/ or pipeline/ imports), and consumes XFrames read-only.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import numpy as np

import metrics.ndt as ndt
from common.contract import PROCESS_PARAM_NAMES
from pipeline.orchestrator import _KIND_BY_STAGE, CANONICAL_ORDER
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import make_params


def test_t0_surface_unchanged_no_ndt_stage():
    """No NDT stage is added to the fixed pipeline order or the CalibKind wiring."""
    assert "ndt" not in CANONICAL_ORDER
    assert not any("ndt" in stage.lower() for stage in CANONICAL_ORDER)
    assert "ndt" not in _KIND_BY_STAGE


def test_metrics_ndt_no_modules_or_pipeline_imports():
    """metrics.ndt imports only downward (metrics -> common); never modules/pipeline."""
    source = Path(inspect.getsourcefile(ndt)).read_text(encoding="utf-8")
    for forbidden in (
        r"import\s+modules",
        r"from\s+modules",
        r"import\s+pipeline",
        r"from\s+pipeline",
    ):
        assert re.search(forbidden, source) is None, forbidden


def test_ndt_functions_are_not_process_contract():
    """No NDT entry point matches the process(frame, calib, params) signature."""
    callables = [
        ndt.correct_thickness,
        ndt.read_single_wire_iqi,
        ndt.build_iqi_report,
        ndt.read_duplex_srb,
        ndt.compute_snrn,
        ndt.SNRnAccumulator.update,
    ]
    for fn in callables:
        params = [
            p.name
            for p in inspect.signature(fn).parameters.values()
            if p.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            and p.name != "self"
        ]
        assert tuple(params) != PROCESS_PARAM_NAMES, (fn, params)
    # And the module is not itself a process module.
    assert not hasattr(ndt, "process")


def test_ndt_measurement_consumes_xframe_read_only():
    """Thickness + accumulation consume the input XFrame without mutating it."""
    ph = gen.make_thickness_defect_phantom()
    snapshot = np.asarray(ph.frame.pixel, dtype=np.float64).copy()
    ndt.correct_thickness(ph.frame, make_params())

    seq = gen.make_snrn_sequence()
    frame0 = seq.frames[0]
    frame0_snapshot = np.asarray(frame0.pixel, dtype=np.float64).copy()
    acc = ndt.SNRnAccumulator(seq.roi, seq.srb_um, make_params())
    acc.update(frame0)

    assert np.array_equal(np.asarray(ph.frame.pixel, dtype=np.float64), snapshot)
    assert np.array_equal(np.asarray(frame0.pixel, dtype=np.float64), frame0_snapshot)


def test_report_does_not_embed_ev_gate_thresholds():
    """The report carries Class Params it consumed, never EV min/typ/max gates."""
    report = ndt.build_iqi_report(
        [ndt.IqiShot(shot_index=1, snrn=150.0, srb_um=130.0, min_visible_wire=13)],
        make_params(),
    )
    keys = set(report.values.keys())
    assert not any(k.lower().startswith("ev") for k in keys)
    assert not any("pass_threshold" in k.lower() for k in keys)
