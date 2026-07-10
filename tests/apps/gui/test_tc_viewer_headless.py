"""Headless smoke e2e + resource/responsiveness structure -- Phase 2 (XDET-TC-037).

@MX:ANCHOR: [AUTO] `test_end_to_end_module_verifier_smoke` and
`test_end_to_end_pipeline_viewer_smoke` are the project's actual "does the
running app work" verification (C-15) -- they construct `apps.gui.app.MainWindow`
under `QT_QPA_PLATFORM=offscreen`, drive it via `qtbot` button CLICKS (not the
underlying functions directly), and assert on what the running app produced.
This is the mandatory e2e coverage layer above Phase 1/2's per-function unit
tests (`test_tc_viewer_image/module/metrics/pipeline.py`).

C-18/19 (`apps/gui/config.py` `[T]` externalization) and C-20 (`data/` write
refusal) are exercised at the unit level in Phase 1/2 test modules already;
this file adds only the structural completeness check that is genuinely new
here (every `[T]` key required for those criteria resolves without a
`GuiConfigError`), avoiding duplicate/vacuous re-assertion of an
already-covered fact.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("qtpy")

from qtpy.QtCore import Qt

from apps.gui.app import MainWindow
from apps.gui.config import (
    T_EVENT_LOOP_MS,
    T_LRU_FRAMES,
    T_RSS_LIMIT_MB,
    default_config,
)
from common.xframe import MaskFlag, new_frame


def _synthetic_frame(shape: tuple[int, int] = (16, 16)):
    pixel = np.arange(shape[0] * shape[1], dtype=np.float32).reshape(shape)
    return new_frame(pixel)


# -- C-14/15: headless end-to-end smoke (real running app, not just functions) --


def test_end_to_end_module_verifier_smoke(qtbot):
    """Load a frame -> select a param-free module -> click Run -> compare + history.

    Drives `MainWindow` exactly as an interactive session would (qtbot mouse
    click on the real `QPushButton`), under the CI-mandated offscreen
    platform -- the app must actually construct and run without a display.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    tab = window.module_tab
    tab.io_panel.frame = _synthetic_frame()
    # "saturation" needs neither a real CalibSet payload nor any Params
    # (verified independently: modules.saturation.process runs against an
    # empty-data synthetic CalibSet and an empty Params()) -- a genuine,
    # non-trivial pipeline stage that this smoke test can run end-to-end
    # without requiring measured calibration data.
    index = tab.module_combo.findText("saturation")
    assert index >= 0, "'saturation' must be a selectable module"
    tab.module_combo.setCurrentIndex(index)

    qtbot.mouseClick(tab.run_button, Qt.MouseButton.LeftButton)
    # Execution runs on a background CallableWorker thread (REQ-VIEW-ARCH-8):
    # immediately after the click returns, the GUI-thread handler has already
    # disabled Run and shown the progress indicator, while the worker itself
    # is still running in the background.
    assert not tab.run_button.isEnabled()
    assert tab.progress.isVisible()
    # `_on_finished` re-enables Run once the background thread completes.
    qtbot.waitUntil(lambda: tab.run_button.isEnabled(), timeout=5000)
    assert not tab.progress.isVisible()

    assert tab.last_result is not None, "clicking Run must produce a ModuleRunResult"
    assert tab.last_result.output_frame.history[-1].module_name == "saturation"
    assert "Ran 'saturation'" in tab.status_label.text()
    # The compare view actually added on-screen image layers to both plots (C-05).
    assert len(tab.plot_before.getPlotItem().items) > 0
    assert len(tab.plot_after.getPlotItem().items) > 0
    assert tab.history_panel.isVisible()


def test_end_to_end_module_verifier_full_wiring(qtbot, tmp_path):
    """Click through every REQ-VIEW-IMAGE/COMPARE/RUN control wired into
    `CompareDisplay`/`ModuleVerifierTab`, not just Run -- found missing (built
    and unit-tested but never wired into a visible widget) via direct live
    verification of the running app (diff view, mask overlays, hover probe,
    W/L control, blink, export were absent from `MainWindow` despite being
    unit-tested in isolation)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    tab = window.module_tab
    cd = tab.compare_display
    shape = (40, 40)
    pixel = np.zeros(shape, dtype=np.float32)
    masks = np.zeros(shape, dtype=np.uint8)
    masks[10:20, 10:20] = int(MaskFlag.SATURATION)
    tab.io_panel.frame = new_frame(pixel, masks=masks)
    tab.module_combo.setCurrentIndex(tab.module_combo.findText("saturation"))

    qtbot.mouseClick(tab.run_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.run_button.isEnabled(), timeout=5000)
    assert tab.last_result is not None

    # C-06 diff view: a real layer was added (before == after here since
    # saturation.py never touches pixel values, only masks -- diff is exactly 0).
    assert len(cd.plot_diff.getPlotItem().items) > 0

    # C-07 mask overlay: saturation.py dilates the seeded SATURATION core into
    # a SATURATION_BAND ring, so both flags are non-empty and independently toggleable.
    assert np.any(np.asarray(tab.last_result.output_frame.masks) & int(MaskFlag.SATURATION_BAND))
    sat_overlay = cd._mask_overlays[MaskFlag.SATURATION]
    qtbot.mouseClick(cd.mask_checks[MaskFlag.SATURATION], Qt.MouseButton.LeftButton)
    assert sat_overlay.visible is False
    qtbot.mouseClick(cd.mask_checks[MaskFlag.SATURATION], Qt.MouseButton.LeftButton)
    assert sat_overlay.visible is True
    cd.mask_opacity.setValue(75)
    assert sat_overlay.opacity == pytest.approx(0.75)

    # C-05 blink toggle: a real button click flips the CompareView's visible layer.
    showing_after_before = cd._compare_view.showing_after
    qtbot.mouseClick(cd.blink_button, Qt.MouseButton.LeftButton)
    assert cd._compare_view.showing_after != showing_after_before

    # C-01 W/L control: the real QDoubleSpinBox widgets drive ImageLayer.set_levels.
    cd._wl_control.high_spin.setValue(123.0)
    assert cd._after_layer.levels()[1] == pytest.approx(123.0)

    # C-03 hover probe: reads the stored float32 array, not the render LUT.
    view_box = cd.plot_after.getViewBox()
    scene_pos = view_box.mapViewToScene(view_box.viewRect().center())
    cd._on_hover((scene_pos,))
    assert "Probe (row=" in cd.probe_label.text()

    # #17/C-20 export: a real button-driven save path round-trips through export_frame.
    out_path = tmp_path / "case1"
    result = tab.export_to(str(out_path))
    assert result is not None
    npz_path, json_path = result
    assert npz_path.exists() and json_path.exists()


def test_end_to_end_metrics_tab_full_wiring(qtbot):
    """Metrics tab: load a source frame, compute MTF, and verify the ROI
    round-trip (C-09/C-10) -- found unwired (metrics_panel.py existed and was
    unit-tested but no Metrics tab existed in `MainWindow`)."""
    from tests.metrics.phantoms.generators import make_slanted_edge

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    edge = make_slanted_edge(shape=(64, 64), angle_deg=2.0, sigma_px=0.8, pitch_mm=0.14)
    mtab = window.metrics_tab
    mtab.set_frame(edge.frame)

    qtbot.mouseClick(mtab.compute_button, Qt.MouseButton.LeftButton)
    assert "MTF computed" in mtab.status_label.text()
    assert len(mtab.mtf_plot.getPlotItem().items) > 0

    qtbot.mouseClick(mtab.roi_button, Qt.MouseButton.LeftButton)
    assert "ROI: top=" in mtab.roi_label.text()
    assert "MATCH" in mtab.status_label.text(), (
        f"ROI round-trip must be deterministic (C-16 inheritance): {mtab.status_label.text()}"
    )


def test_end_to_end_module_verifier_smoke_reports_failure_without_crashing(qtbot):
    """A module needing real calibration data (offset) fails gracefully, not fatally."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    tab = window.module_tab
    tab.io_panel.frame = _synthetic_frame()
    index = tab.module_combo.findText("offset")
    assert index >= 0
    tab.module_combo.setCurrentIndex(index)

    qtbot.mouseClick(tab.run_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.run_button.isEnabled(), timeout=5000)

    # offset requires a real O_map (missing from the synthetic CalibSet) and a
    # required Param -- either way, the app must survive and report status text.
    assert tab.last_result is None
    assert "failed" in tab.status_label.text()


def test_end_to_end_pipeline_viewer_smoke(qtbot):
    """Load a frame -> check a stage -> click Run pipeline -> stage comparisons."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    tab = window.pipeline_tab
    tab.io_panel.frame = _synthetic_frame()
    tab.stage_checks["saturation"].setChecked(True)

    qtbot.mouseClick(tab.run_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.run_button.isEnabled(), timeout=5000)

    assert tab.last_result is not None
    assert [c.stage for c in tab.last_result.stage_comparisons] == ["saturation"]
    assert "Ran 1 stage(s): saturation" in tab.status_label.text()


def test_module_verifier_cancel_discards_result(qtbot):
    """Clicking Cancel while the worker is running discards the result (REQ-VIEW-ARCH-8)."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    tab = window.module_tab
    tab.io_panel.frame = _synthetic_frame()
    tab.module_combo.setCurrentIndex(tab.module_combo.findText("saturation"))

    qtbot.mouseClick(tab.run_button, Qt.MouseButton.LeftButton)
    assert tab.cancel_button.isEnabled()
    qtbot.mouseClick(tab.cancel_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.run_button.isEnabled(), timeout=5000)

    assert tab.last_result is None, "a cancelled run must not populate a result"
    assert tab.status_label.text() == "Cancelled"


def test_module_verifier_reports_when_no_frame_loaded(qtbot):
    """Clicking Run with nothing loaded reports status text, never raises."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    qtbot.mouseClick(window.module_tab.run_button, Qt.MouseButton.LeftButton)
    assert window.module_tab.last_result is None
    assert "Load a frame first" in window.module_tab.status_label.text()


# -- C-18/19: [T] resource/responsiveness thresholds externalized (structural) --


def test_resource_and_responsiveness_thresholds_are_externalized():
    """C-18 (RSS/LRU) and C-19 (event-loop block) settings resolve from config,
    never as literals scattered through widget code (HARD parameter policy)."""
    config = default_config()
    assert config.get(T_RSS_LIMIT_MB) > 0
    assert config.get(T_LRU_FRAMES, cast=int) > 0
    assert config.get(T_EVENT_LOOP_MS) > 0
