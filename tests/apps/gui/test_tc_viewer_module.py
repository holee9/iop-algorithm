"""XDET-TC-033 -- Phase 1 module verifier: run_module output + compare/mask layers.

SPEC-VIEWER-001 REQ-VIEW-RUN-1, REQ-VIEW-COMPARE-1..6 (docs/GUI_CRITERIA.md
C-05..07). Headless via qtbot/pytest-qt (QT_QPA_PLATFORM=offscreen).

Per SPEC-VIEWER-001 v0.1.1 decision D9, GUI test sources must not contain the
Gen 1 TC id string range ("000"-"021") so the capstone scan
(tests/test_tc_skeletons.py `_GEN1_TC_RANGE`) never mis-registers a deleted
Gen 1 test as alive.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("qtpy")  # C-12: must not block a [gui]-less core-no-gui collection

import numpy as np
import pyqtgraph as pg

from apps.gui.history_panel import HistoryPanel
from apps.gui.io_panel import DataWriteRejectedError, IoPanel, guard_output_path
from apps.gui.layers import CompareView, make_diff_layer, make_image_layer, make_mask_overlay_layers
from apps.gui.module_panel import run_module
from apps.gui.probe import probe_at
from common.calibset import CalibKind
from common.contract import Params
from common.synth_calibset import make_synthetic_calibset
from common.xframe import HistoryEntry, MaskFlag, new_frame


class _AddConstantModule:
    """Minimal test-only ProcessModule double: adds a constant, records history."""

    MODULE_NAME = "test_add_constant"
    MODULE_VERSION = "1.0.0"

    def __init__(self, constant: float = 10.0) -> None:
        self.constant = constant

    def process(self, frame, calib, params):
        pixel = np.asarray(frame.pixel, dtype=np.float32) + self.constant
        new = frame.with_pixel(pixel)
        entry = HistoryEntry(
            module_name=self.MODULE_NAME,
            module_version=self.MODULE_VERSION,
            params_hash=params.hash(),
            calibset_id=calib.calibset_id,
        )
        return new.record_history(entry)


def _input_frame():
    pixel = np.arange(30, dtype=np.float32).reshape(5, 6)
    masks = np.zeros((5, 6), dtype=np.uint8)
    masks[0, 0] = int(MaskFlag.DEFECT)
    masks[1, 1] = int(MaskFlag.SATURATION)
    masks[2, 2] = int(MaskFlag.INTERPOLATION)
    masks[3, 3] = int(MaskFlag.SATURATION_BAND)
    return new_frame(pixel, masks)


def _calib(frame):
    return make_synthetic_calibset(frame.shape, CalibKind.OTHER)


# -- REQ-VIEW-RUN-1: process() is the sole output-producing path ------------


def test_run_module_produces_output_frame_via_process_only():
    module = _AddConstantModule(constant=5.0)
    frame = _input_frame()
    calib = _calib(frame)
    params = Params({})

    result = run_module(module, frame, calib, params)

    assert result.input_frame is frame
    assert np.array_equal(result.output_frame.pixel, frame.pixel + 5.0)
    assert result.verification is None  # no expected golden supplied


def test_run_module_runs_harness_alongside_process_when_expected_supplied():
    """Fixture-verification mode: run_harness badge is PARALLEL, not a substitute."""
    module = _AddConstantModule(constant=5.0)
    frame = _input_frame()
    calib = _calib(frame)
    params = Params({})
    expected = module.process(frame, calib, params)  # deterministic expected

    result = run_module(module, frame, calib, params, expected=expected)

    assert result.verification is not None
    assert result.verification.passed is True
    # The harness never substitutes the displayed output frame.
    assert result.output_frame.equals(expected)


def test_run_module_harness_badge_reports_mismatch():
    module = _AddConstantModule(constant=5.0)
    frame = _input_frame()
    calib = _calib(frame)
    params = Params({})
    real_output = module.process(frame, calib, params)
    wrong_expected = real_output.with_pixel(np.asarray(real_output.pixel) + 999.0)

    result = run_module(module, frame, calib, params, expected=wrong_expected)

    assert result.verification.passed is False
    # Displayed output is still the real process() output, not the golden.
    assert np.array_equal(result.output_frame.pixel, frame.pixel + 5.0)


# -- REQ-VIEW-COMPARE-1/2 (C-05): linked side-by-side + blink toggle --------


def test_compare_view_links_zoom_pan_between_before_after(qtbot):
    frame = _input_frame()
    output = _AddConstantModule().process(frame, _calib(frame), Params({}))
    before_layer = make_image_layer("before", frame.pixel)
    after_layer = make_image_layer("after", output.pixel)
    plot_before, plot_after = pg.PlotWidget(), pg.PlotWidget()
    qtbot.addWidget(plot_before)
    qtbot.addWidget(plot_after)

    CompareView(before_layer, after_layer, plot_before, plot_after)

    view_before = plot_before.getViewBox()
    view_after = plot_after.getViewBox()
    assert view_after.linkedView(pg.ViewBox.XAxis) is view_before
    assert view_after.linkedView(pg.ViewBox.YAxis) is view_before


def test_compare_view_blink_toggles_single_key_visibility(qtbot):
    frame = _input_frame()
    output = _AddConstantModule().process(frame, _calib(frame), Params({}))
    before_layer = make_image_layer("before", frame.pixel)
    after_layer = make_image_layer("after", output.pixel)
    plot_before, plot_after = pg.PlotWidget(), pg.PlotWidget()
    qtbot.addWidget(plot_before)
    qtbot.addWidget(plot_after)
    compare = CompareView(before_layer, after_layer, plot_before, plot_after)

    assert compare.showing_after is True
    compare.toggle_blink()
    assert compare.showing_after is False
    assert before_layer.item.isVisible() is True
    assert after_layer.item.isVisible() is False
    compare.toggle_blink()
    assert compare.showing_after is True
    assert after_layer.item.isVisible() is True


def test_compare_view_syncs_wl_across_both_views(qtbot):
    frame = _input_frame()
    output = _AddConstantModule().process(frame, _calib(frame), Params({}))
    before_layer = make_image_layer("before", frame.pixel)
    after_layer = make_image_layer("after", output.pixel)
    plot_before, plot_after = pg.PlotWidget(), pg.PlotWidget()
    qtbot.addWidget(plot_before)
    qtbot.addWidget(plot_after)
    compare = CompareView(before_layer, after_layer, plot_before, plot_after)

    compare.sync_levels(-5.0, 50.0)

    assert before_layer.levels() == (-5.0, 50.0)
    assert after_layer.levels() == (-5.0, 50.0)


# -- REQ-VIEW-COMPARE-3/4 (C-06): diff diverging render + signed hover ------


def test_diff_layer_is_signed_after_minus_before():
    frame = _input_frame()
    output = _AddConstantModule(constant=7.0).process(frame, _calib(frame), Params({}))

    diff_layer = make_diff_layer(frame, output)

    assert np.allclose(diff_layer.array, 7.0)


def test_diff_layer_default_range_is_symmetric_max_abs():
    frame = _input_frame()
    output = _AddConstantModule(constant=-3.0).process(frame, _calib(frame), Params({}))

    diff_layer = make_diff_layer(frame, output)
    lo, hi = diff_layer.levels()

    assert lo == pytest.approx(-3.0)
    assert hi == pytest.approx(3.0)


def test_diff_layer_hover_reports_signed_float_value():
    frame = _input_frame()
    output = _AddConstantModule(constant=-12.5).process(frame, _calib(frame), Params({}))
    diff_layer = make_diff_layer(frame, output)

    reading = probe_at([diff_layer], row=0, col=0)

    assert reading.values["diff"] == pytest.approx(-12.5)


# -- REQ-VIEW-COMPARE-5/6 (C-07): 4 independent mask overlays, pixel-aligned -


def test_mask_overlays_are_independent_per_flag():
    frame = _input_frame()

    overlays = make_mask_overlay_layers(frame.masks)

    assert set(overlays) == {
        MaskFlag.DEFECT,
        MaskFlag.SATURATION,
        MaskFlag.INTERPOLATION,
        MaskFlag.SATURATION_BAND,
    }
    assert overlays[MaskFlag.DEFECT].array[0, 0]
    assert not overlays[MaskFlag.DEFECT].array[1, 1]
    assert overlays[MaskFlag.SATURATION].array[1, 1]


def test_mask_overlay_visibility_and_opacity_toggle_independently():
    frame = _input_frame()
    overlays = make_mask_overlay_layers(frame.masks)
    defect_layer = overlays[MaskFlag.DEFECT]
    sat_layer = overlays[MaskFlag.SATURATION]

    defect_layer.set_visible(False)
    sat_layer.set_opacity(0.9)

    assert defect_layer.visible is False
    assert defect_layer.item.opacity() == 0.0
    assert sat_layer.opacity == pytest.approx(0.9)
    assert sat_layer.item.opacity() == pytest.approx(0.9)


def test_mask_overlays_are_pixel_aligned_with_base_shape():
    """C-07: every mask overlay shares the base image's (rows, cols) shape --
    the same implicit 1:1 pyqtgraph pixel transform applies at every zoom.
    """
    frame = _input_frame()
    overlays = make_mask_overlay_layers(frame.masks)

    for layer in overlays.values():
        assert layer.array.shape == frame.shape


# -- REQ-VIEW-COMPARE-7 (C-08): processing-history display, WHERE it exists -


def test_history_panel_shows_chain_when_history_present(qtbot):
    frame = _input_frame()
    output = _AddConstantModule(constant=1.0).process(frame, _calib(frame), Params({}))
    panel = HistoryPanel()
    qtbot.addWidget(panel)

    panel.show_history(output.history)

    assert panel.isVisible() is True
    assert panel.rowCount() == len(output.history) == 1
    assert panel.item(0, 0).text() == "test_add_constant"


def test_history_panel_hidden_when_history_empty(qtbot):
    panel = HistoryPanel()
    qtbot.addWidget(panel)

    panel.show_history(())

    assert panel.isVisible() is False
    assert panel.rowCount() == 0


# -- REQ-VIEW-RUN-7/8 (C-20): read-execute-only -- data/ writes are refused -


def test_guard_output_path_rejects_writes_under_data_root(tmp_path):
    (tmp_path / "data").mkdir()

    with pytest.raises(DataWriteRejectedError):
        guard_output_path(tmp_path / "data" / "golden" / "out.npz", project_root=tmp_path)


def test_guard_output_path_allows_writes_outside_data_root(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "exports").mkdir()

    resolved = guard_output_path(tmp_path / "exports" / "out.npz", project_root=tmp_path)

    assert resolved == (tmp_path / "exports" / "out.npz").resolve()


# -- REQ-VIEW-CORE-1: raw/JSON loading through the actual IoPanel widget -----


def test_open_raw_loads_a_real_raw_json_file_losslessly(qtbot, tmp_path):
    """A genuine 16-bit .raw + .json sidecar pair, read through the real
    `IoPanel.open_raw` code path (not `.frame =` assignment bypass) -- the
    e2e smoke tests exercise `.frame =` directly, so this was the one
    remaining unverified code path in the load pipeline."""
    shape = (12, 20)
    pixel_u16 = np.linspace(0, 60000, shape[0] * shape[1], dtype=np.uint16).reshape(shape)
    raw_path = tmp_path / "sample.raw"
    pixel_u16.tofile(raw_path)
    meta_path = tmp_path / "sample.json"
    meta_path.write_text(
        json.dumps({"resolution": list(shape), "dtype": "uint16"}), encoding="utf-8"
    )

    panel = IoPanel()
    qtbot.addWidget(panel)
    frame = panel.open_raw(raw_path, meta_path)

    assert frame is not None
    assert frame.shape == shape
    assert np.array_equal(np.asarray(frame.pixel), pixel_u16.astype(np.float32))
    assert panel.frame is frame
    assert f"{shape}" in panel._label.text()


# -- REQ-VIEW-CORE-1: malformed raw/JSON input reports an error, never crashes --


def test_open_raw_reports_error_on_malformed_metadata_without_raising(qtbot, tmp_path):
    """Regression: a Qt click-slot call site with no CallableWorker/exception
    boundary must not let `load_raw_frame`'s ValueError propagate and crash
    the app (found by code review)."""
    raw_path = tmp_path / "bad.raw"
    raw_path.write_bytes(b"\x00" * 8)
    meta_path = tmp_path / "bad.json"
    meta_path.write_text("{}", encoding="utf-8")  # missing required "resolution" key

    panel = IoPanel()
    qtbot.addWidget(panel)

    result = panel.open_raw(raw_path, meta_path)

    assert result is None
    assert panel.frame is None
    assert "Failed to load" in panel._label.text()
