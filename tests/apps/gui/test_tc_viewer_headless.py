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
from common.xframe import new_frame


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

    assert tab.last_result is not None, "clicking Run must produce a ModuleRunResult"
    assert tab.last_result.output_frame.history[-1].module_name == "saturation"
    assert "Ran 'saturation'" in tab.status_label.text()
    # The compare view actually added on-screen image layers to both plots (C-05).
    assert len(tab.plot_before.getPlotItem().items) > 0
    assert len(tab.plot_after.getPlotItem().items) > 0
    assert tab.history_panel.isVisible()


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

    assert tab.last_result is not None
    assert [c.stage for c in tab.last_result.stage_comparisons] == ["saturation"]
    assert "Ran 1 stage(s): saturation" in tab.status_label.text()


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
