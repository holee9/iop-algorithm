"""XDET-TC-044..049: headless GUI sample (plumbing-only) 6-suite (REQ-REALDATA-GUI).

Drives the SPEC-VIEWER-001 GUI surface with sample acquisition-set pixels under
QT_QPA_PLATFORM=offscreen. [HARD] QUARANTINE: assertions are SANITY ONLY — shape
/ dtype / finiteness / non-degeneracy / write-refusal / engine-execution. The
vendor `_result` frame is used ONLY as a diff target layer (zero numeric
authority); no bit-identity / tolerance assertion is made (REQ-REALDATA-CONTRACT-3).

Suite map:
  044 (a) real-frame load shape/dtype + hover probe          [realdata]
  045 (b) diff / blink vs `_result` target layer             [realdata]
  046 (c) module panel offset -> gain runs + finite output   [always-on, real crops]
  047 (d) metrics panel/engine runs + finite output          [always-on, real crops]
  048 (e) guard_output_path refuses data/ write              [always-on]
  049 (f) 3072^2 downsample smoke: reduced shape + finite     [slow + realdata]

This source deliberately uses only XDET-TC-044..049 ids (no earlier-block id
strings) so the Gen-1 capstone scan is unaffected (D9 precedent).
"""

from __future__ import annotations

import json

import numpy as np
import pytest

pytest.importorskip("qtpy")
pytest.importorskip("pyqtgraph")

import pyqtgraph as pg  # noqa: E402

from apps.gui.io_panel import DataWriteRejectedError, guard_output_path  # noqa: E402
from apps.gui.layers import CompareView, make_diff_layer, make_image_layer  # noqa: E402
from apps.gui.metrics_panel import plot_mtf  # noqa: E402
from apps.gui.module_panel import run_module  # noqa: E402
from apps.gui.probe import probe_at  # noqa: E402
from common.contract import Params  # noqa: E402
from common.io import load_raw_frame  # noqa: E402
from common.pyramid import reduce_once  # noqa: E402
from common.xframe import new_frame  # noqa: E402
from metrics import nps  # noqa: E402
from metrics.ndt import compute_snr  # noqa: E402
from metrics.result import MetricReadError  # noqa: E402
from modules import gain, offset  # noqa: E402
from scripts import ingest_edrogi as ing  # noqa: E402
from tests.metrics.phantoms.params import _DEFAULTS  # noqa: E402
from tests.modules.phantoms.corrections import corr_params  # noqa: E402

_FIXTURE = ing.FIXTURE_DIR


def _load_crop(base: str):
    return load_raw_frame(_FIXTURE / f"{base}.raw", _FIXTURE / f"{base}.json")


def _first_capture_and_result(folder: str):
    """Return (capture_raw, result_raw) for the first capture with a vendor result."""
    root = ing.require_edrogi()
    for raw in sorted((root / folder).glob("*.raw")):
        if raw.name.endswith("_result.raw"):
            continue
        result = raw.with_name(raw.stem + "_result.raw")
        if result.exists():
            return raw, result
    pytest.skip(f"no capture/_result pair under {folder}")


def _load_full_with_sidecar(raw_path, tmp_path):
    """Load a full-res raw via the loader by writing a transient sidecar."""
    sidecar = tmp_path / (raw_path.stem + ".json")
    sidecar.write_text(
        json.dumps({"resolution": [3072, 3072], "dtype": "uint16"}), encoding="utf-8"
    )
    return load_raw_frame(raw_path, sidecar)


# -- 044 (a): real-frame load shape/dtype + hover probe -----------------------


@pytest.mark.realdata
def test_tc_044_real_frame_load_and_probe(qtbot, tmp_path):
    raw, _ = _first_capture_and_result("nps")
    frame = _load_full_with_sidecar(raw, tmp_path)
    assert frame.shape == (3072, 3072)
    assert np.asarray(frame.pixel).dtype == np.float32

    layer = make_image_layer("input", frame.pixel)
    reading = probe_at([layer], 1408, 1408)
    assert reading is not None
    # C-03: the probe reports the stored float32 original, not a render value.
    expected = float(np.asarray(frame.pixel)[1408, 1408])
    assert reading.values["input"] == pytest.approx(expected)
    assert np.isfinite(reading.values["input"])


# -- 045 (b): diff / blink vs `_result` target layer --------------------------


@pytest.mark.realdata
def test_tc_045_diff_blink_vs_result_target(qtbot, tmp_path):
    raw, result = _first_capture_and_result("nps")
    capture = _load_full_with_sidecar(raw, tmp_path)
    target = _load_full_with_sidecar(result, tmp_path)

    # `_result` is a TARGET layer only (zero numeric authority) — a diff layer,
    # never a bit-identity/tolerance reference.
    diff = make_diff_layer(capture, target)
    assert diff.array.shape == (3072, 3072)
    assert np.all(np.isfinite(diff.array))

    before = make_image_layer("capture", capture.pixel)
    after = make_image_layer("result_target", target.pixel)
    view = CompareView(before, after, pg.PlotWidget(), pg.PlotWidget())
    qtbot.addWidget(view.plot_before)
    qtbot.addWidget(view.plot_after)
    start = view.showing_after
    assert view.toggle_blink() != start  # single-key blink flips the visible layer


# -- 046 (c): module panel offset -> gain runs + finite output ----------------


def test_tc_046_module_panel_offset_then_gain(qtbot):
    signal = _load_crop(ing.FIXTURE_CALSET)
    offset_calib = ing.build_offset_calibset(_load_crop(ing.FIXTURE_MASTERDARK))
    gain_calib = ing.build_gain_calibset(_load_crop(ing.FIXTURE_CALSET))
    params = corr_params()

    r1 = run_module(offset, signal, offset_calib, params)
    r2 = run_module(gain, r1.output_frame, gain_calib, params)

    out = np.asarray(r2.output_frame.pixel)
    # sanity: the 2-stage process path produced a finite, non-degenerate frame.
    assert out.shape == (256, 256)
    assert np.all(np.isfinite(out))
    assert float(np.std(out)) > 0.0
    # `run_module` produces the output via process() (not the fixture harness).
    assert r2.verification is None


# -- 047 (d): metrics panel/engine runs + finite output -----------------------


def test_tc_047_metrics_engine_delegation_and_finite(qtbot):
    flat = _load_crop(ing.FIXTURE_CALSET)

    # MTF via the panel DELEGATES to metrics.mtf (GUI computes nothing itself,
    # C-09): a flat sample crop has no valid slanted edge, so the engine's own
    # gate fires — proving the engine, not the GUI, made the decision.
    with pytest.raises(MetricReadError):
        plot_mtf(pg.PlotWidget(), flat, Params(_DEFAULTS))

    # NPS engine on the real flat crop -> finite, non-degenerate.
    nps_params = Params({**_DEFAULTS, "nps_roi_size": 64})
    nps_result = nps.compute_nps([flat], nps_params)
    nps1d = np.asarray(nps_result.get("nps"))
    assert nps1d.size > 0 and np.all(np.isfinite(nps1d)) and float(np.nanmax(nps1d)) > 0.0

    # SNR engine on a uniform ROI -> finite.
    snr, mean, std = compute_snr(flat, (16, 16, 128, 128), Params(_DEFAULTS))
    assert np.isfinite(snr) and std > 0.0


# -- 048 (e): guard_output_path refuses data/ write (always-on) ---------------


def test_tc_048_guard_refuses_data_write(tmp_path):
    project_root = tmp_path
    (project_root / "data").mkdir()
    with pytest.raises(DataWriteRejectedError):
        guard_output_path(project_root / "data" / "leak.npz", project_root)
    # a path outside data/ is allowed (returns a resolved path).
    ok = guard_output_path(project_root / "exports" / "ok.npz", project_root)
    assert ok.name == "ok.npz"


# -- 049 (f): 3072^2 downsample smoke: reduced shape + finite/non-constant ----


@pytest.mark.slow
@pytest.mark.realdata
def test_tc_049_full_res_downsample_smoke(tmp_path):
    raw, _ = _first_capture_and_result("nps")
    frame = _load_full_with_sidecar(raw, tmp_path)
    assert frame.shape == (3072, 3072)

    reduced = np.asarray(frame.pixel, dtype=np.float64)
    for _ in range(3):  # 3072 -> 1536 -> 768 -> 384
        reduced = reduce_once(reduced)
    out = new_frame(reduced.astype(np.float32))

    # D1: concrete shape + statistics assertion, not a vacuous "done".
    assert out.shape == (384, 384)
    arr = np.asarray(out.pixel)
    assert np.all(np.isfinite(arr))
    assert float(np.std(arr)) > 0.0  # non-constant
