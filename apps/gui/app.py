"""PySide6 + pyqtgraph verification GUI shell -- SPEC-VIEWER-001 (Phase 1+2).

@MX:ANCHOR: [AUTO] `MainWindow` is the single running entry point that wires
every Phase 1/2 building block (`io_panel`/`module_panel`/`layers`/`probe`/
`history_panel`/`metrics_panel`/`pipeline_panel`/`export`) into one operable
app -- the "GUI 앱으로 동작" requirement, not just a set of
independently-tested functions. napari is not used (Phase 0 spike fallback,
pyqtgraph single path -- `.moai/reports/SPEC-VIEWER-001-spike.md`).
@MX:REASON: `tests/apps/gui/test_tc_viewer_headless.py`'s end-to-end smoke
test drives THIS class (button clicks via qtbot, not the underlying
functions directly) as the project's real "does the app actually run"
verification (C-15). `CompareDisplay` below is the single place W/L, diff,
mask overlays, hover probe, and blink are wired into an actually-visible
widget tree -- found missing (only unit-tested in isolation, never wired
into `MainWindow`) via direct user verification of the running app.

Each tab surfaces failures as status text rather than raising -- a module
requiring a real (non-synthetic) CalibSet payload or specific Params is a
normal, expected outcome for an interactive verification tool, not a crash.

Module/pipeline execution runs on a background `CallableWorker` thread
(`apps.gui.worker`, REQ-VIEW-ARCH-8) with an indeterminate progress bar and a
best-effort Cancel button -- cancel discards the result rather than
interrupting the underlying pure computation (no core cancellation hook
exists, and REQ-VIEW-CORE-4 forbids adding one).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from apps.gui.export import export_frame, import_frame
from apps.gui.help_dialog import ABOUT_TEXT, HelpDialog
from apps.gui.history_panel import HistoryPanel
from apps.gui.io_panel import DataWriteRejectedError, IoPanel
from apps.gui.layers import (
    CompareView,
    MaskOverlayLayer,
    WindowLevelControl,
    make_diff_layer,
    make_image_layer,
    make_mask_overlay_layers,
)
from apps.gui.metrics_panel import RoiBounds, plot_mtf, recompute_mtf_for_roi, roi_bounds_from_rect_roi
from apps.gui.module_panel import ModuleRunResult, ParamsForm, run_module
from apps.gui.pipeline_panel import (
    SELECTABLE_STAGES,
    PipelineRunResult,
    run_partial_pipeline,
)
from apps.gui.probe import make_hover_proxy, probe_at, scene_pos_to_pixel
from apps.gui.worker import CallableWorker
from common.contract import Params
from common.synth_calibset import make_synthetic_calibset
from common.xframe import MaskFlag, XFrame
from modules.registry import default_registry
from pipeline.orchestrator import calib_kind_for_stage

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MASK_FLAGS: tuple[MaskFlag, ...] = (
    MaskFlag.DEFECT,
    MaskFlag.SATURATION,
    MaskFlag.INTERPOLATION,
    MaskFlag.SATURATION_BAND,
)


class CompareDisplay(QWidget):
    """Before/after/diff/mask/probe/W-L/blink display block (C-01/02/03/04/05/06/07).

    @MX:ANCHOR: [AUTO] The single wiring point for every REQ-VIEW-IMAGE and
    REQ-VIEW-COMPARE display requirement, shared by `ModuleVerifierTab` and
    `PipelineViewerTab` so this wiring exists exactly once instead of being
    duplicated (and drifting) across both tabs.
    """

    _MASK_TOOLTIPS = {
        MaskFlag.DEFECT: "Toggle the DEFECT overlay -- bad/dead pixel map.",
        MaskFlag.SATURATION: "Toggle the SATURATION overlay -- over/under-range pixels.",
        MaskFlag.INTERPOLATION: "Toggle the INTERPOLATION overlay -- defect-corrected pixels.",
        MaskFlag.SATURATION_BAND: (
            "Toggle the SATURATION_BAND overlay -- the dilated boundary "
            "buffer ring around saturated pixels."
        ),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.plot_before = pg.PlotWidget(self)
        self.plot_before.setToolTip(
            "Input (before) frame -- float32 values rendered via W/L levels only."
        )
        self.plot_after = pg.PlotWidget(self)
        self.plot_after.setToolTip(
            "Output (after) frame with mask overlays -- hover here to read "
            "the exact stored float32 value at a pixel (C-03)."
        )
        self.plot_diff = pg.PlotWidget(self)
        self.plot_diff.setToolTip(
            "Signed difference (after - before), 0-centered diverging "
            "colormap (C-06)."
        )
        self.mask_checks: dict[MaskFlag, QCheckBox] = {
            flag: QCheckBox(flag.name, self) for flag in _MASK_FLAGS
        }
        for flag, check in self.mask_checks.items():
            check.setChecked(True)
            check.setToolTip(self._MASK_TOOLTIPS[flag])
        self.mask_opacity = QSlider(Qt.Orientation.Horizontal, self)
        self.mask_opacity.setRange(0, 100)
        self.mask_opacity.setValue(50)
        self.mask_opacity.setToolTip(
            "Shared opacity (0-100%) for all currently visible mask overlays."
        )
        self.blink_button = QPushButton("Blink toggle", self)
        self.blink_button.setToolTip(
            "Toggle the Output view between the before and after image "
            "(single-key blink comparison, C-05)."
        )
        self.probe_label = QLabel("Probe: hover over Output once a run completes", self)
        self.probe_label.setToolTip(
            "Shows the exact stored float32 value (not the rendered color) "
            "at the pixel under the mouse in the Output view."
        )
        self.wl_container = QWidget(self)
        self._wl_layout = QVBoxLayout(self.wl_container)

        self._compare_view: CompareView | None = None
        self._wl_control: WindowLevelControl | None = None
        self._mask_overlays: dict[MaskFlag, MaskOverlayLayer] = {}
        self._probe_layers: list = []
        self._after_layer = None

        for flag, check in self.mask_checks.items():
            check.toggled.connect(lambda checked, f=flag: self._on_mask_toggle(f, checked))
        self.mask_opacity.valueChanged.connect(self._on_mask_opacity_changed)
        self.blink_button.clicked.connect(self._on_blink_clicked)
        make_hover_proxy(self.plot_after.getViewBox(), self._on_hover)

        plots = QHBoxLayout()
        plots.addWidget(self.plot_before)
        plots.addWidget(self.plot_after)
        plots.addWidget(self.plot_diff)
        mask_row = QHBoxLayout()
        for check in self.mask_checks.values():
            mask_row.addWidget(check)
        mask_row.addWidget(self.mask_opacity)

        layout = QVBoxLayout(self)
        layout.addWidget(self.wl_container)
        layout.addLayout(plots)
        layout.addLayout(mask_row)
        layout.addWidget(self.blink_button)
        layout.addWidget(self.probe_label)

    def show_comparison(self, before_frame: XFrame, after_frame: XFrame) -> None:
        """Rebuild every layer for a new before/after pair (called after each run)."""
        self.plot_before.clear()
        self.plot_after.clear()
        self.plot_diff.clear()

        before_layer = make_image_layer("before", before_frame.pixel)
        after_layer = make_image_layer("after", after_frame.pixel)
        self._compare_view = CompareView(
            before=before_layer,
            after=after_layer,
            plot_before=self.plot_before,
            plot_after=self.plot_after,
        )
        diff_layer = make_diff_layer(before_frame, after_frame)
        self.plot_diff.addItem(diff_layer.item)

        if self._wl_control is not None:
            self._wl_layout.removeWidget(self._wl_control)
            self._wl_control.deleteLater()
        self._wl_control = WindowLevelControl(after_layer, self.wl_container)
        self._wl_layout.addWidget(self._wl_control)

        self._mask_overlays = make_mask_overlay_layers(
            after_frame.masks, opacity=self.mask_opacity.value() / 100.0
        )
        for flag, overlay in self._mask_overlays.items():
            self.plot_after.getPlotItem().addItem(overlay.item)
            overlay.set_visible(self.mask_checks[flag].isChecked())

        self._after_layer = after_layer
        self._probe_layers = [before_layer, after_layer, diff_layer]

    def _on_mask_toggle(self, flag: MaskFlag, checked: bool) -> None:
        overlay = self._mask_overlays.get(flag)
        if overlay is not None:
            overlay.set_visible(checked)

    def _on_mask_opacity_changed(self, value: int) -> None:
        for overlay in self._mask_overlays.values():
            overlay.set_opacity(value / 100.0)

    def _on_blink_clicked(self) -> None:
        if self._compare_view is not None:
            self._compare_view.toggle_blink()

    def _on_hover(self, evt) -> None:
        if self._after_layer is None:
            return
        row, col = scene_pos_to_pixel(self._after_layer.item, evt[0])
        reading = probe_at(self._probe_layers, row, col)
        if reading is None:
            self.probe_label.setText(f"Probe (row={row}, col={col}): out of bounds")
            return
        parts = ", ".join(f"{name}={value:.4g}" for name, value in reading.values.items())
        self.probe_label.setText(f"Probe (row={reading.row}, col={reading.col}): {parts}")


# @MX:WARN: [AUTO] apps/gui/app.py is 772 lines, the largest file in the
# scanned source set, and ModuleVerifierTab coordinates a background
# CallableWorker (QThread) run against a mutable cancel flag plus a
# stale-result guard (compare/export only valid for the run that produced
# them).
# @MX:REASON: the run/cancel/compare state machine spans multiple Qt signal
# callbacks; a race between a late `succeeded`/`failed` signal and a new run
# started after Cancel could apply a stale result if the guard is ever
# weakened.
class ModuleVerifierTab(QWidget):
    """Phase 1: load a frame -> pick one module -> run -> compare + history (REQ-VIEW-RUN-1)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.io_panel = IoPanel(self)
        self.module_combo = QComboBox(self)
        self.module_combo.addItems(sorted(default_registry()))
        self.module_combo.setToolTip(
            "Select one processing module (stage) to run directly via "
            "ProcessModule.process() (REQ-VIEW-RUN-1)."
        )
        self.params_form = ParamsForm(keys=(), parent=self)
        self.param_key_edit = QLineEdit(self)
        self.param_key_edit.setPlaceholderText("param name (see modules/<stage>.py P_* constants)")
        self.param_key_edit.setToolTip(
            "Exact Params key name the selected module needs (see the P_* "
            "constants documented in modules/<stage>.py), then click "
            "'Add param field'."
        )
        self.add_param_button = QPushButton("Add param field", self)
        self.add_param_button.setToolTip(
            "Add a text field for the typed Params key name so you can "
            "enter its value below."
        )
        self.add_param_button.clicked.connect(self._on_add_param_clicked)
        self.run_button = QPushButton("Run module", self)
        self.run_button.setToolTip(
            "Run the selected module against the loaded frame on a "
            "background thread (REQ-VIEW-ARCH-8)."
        )
        self.run_button.clicked.connect(self._on_run_clicked)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setToolTip(
            "Best-effort cancel: discards the result once the background "
            "run completes (does not interrupt the computation itself)."
        )
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.export_button = QPushButton("Export output...", self)
        self.export_button.setToolTip(
            "Export the last run's output XFrame to a chosen path (npz + "
            "JSON sidecar, #17). Refused if the path is under data/ (C-20)."
        )
        self.export_button.clicked.connect(self._on_export_clicked)
        self.load_expected_button = QPushButton("Load expected (optional)...", self)
        self.load_expected_button.setToolTip(
            "Load a previously-exported XFrame as the 'expected' golden for "
            "fixture verification -- enables a PASS/FAIL badge next to the "
            "run status via run_harness."
        )
        self.load_expected_button.clicked.connect(self._on_load_expected_clicked)
        self.expected_frame: XFrame | None = None
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)  # indeterminate (no per-stage % from the engine)
        self.progress.setVisible(False)
        self.progress.setToolTip("A module run is in progress on a background thread.")
        self.status_label = QLabel("No run yet", self)
        self.status_label.setToolTip("Shows the result or error of the last action.")
        self.compare_display = CompareDisplay(self)
        # Aliases kept for the existing e2e smoke tests, which reach into
        # `tab.plot_before`/`tab.plot_after` directly.
        self.plot_before = self.compare_display.plot_before
        self.plot_after = self.compare_display.plot_after
        self.history_panel = HistoryPanel(self)
        self.last_result: ModuleRunResult | None = None
        self._worker: CallableWorker | None = None
        self._cancelled = False

        controls = QHBoxLayout()
        controls.addWidget(self.module_combo)
        controls.addWidget(self.run_button)
        controls.addWidget(self.cancel_button)
        controls.addWidget(self.export_button)
        controls.addWidget(self.load_expected_button)
        param_row = QHBoxLayout()
        param_row.addWidget(self.param_key_edit)
        param_row.addWidget(self.add_param_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.io_panel)
        layout.addLayout(controls)
        layout.addLayout(param_row)
        layout.addWidget(self.params_form)
        layout.addWidget(self.progress)
        layout.addWidget(self.compare_display)
        layout.addWidget(self.status_label)
        layout.addWidget(self.history_panel)

    def _on_add_param_clicked(self) -> None:
        """Add a named Params field on demand (REQ-VIEW-RUN-1 Params input).

        No per-module key table is hardcoded here -- the SWR `P_*` constant
        names are documented in each `modules/<stage>.py` file; the user
        supplies the exact key name for the stage they selected.
        """
        self.params_form.add_field(self.param_key_edit.text().strip())
        self.param_key_edit.clear()

    def _on_load_expected_clicked(self) -> None:  # pragma: no cover - exercised via dialog only
        path, _ = QFileDialog.getOpenFileName(self, "Load expected golden frame", "", "")
        if path:
            self.load_expected(path)

    def load_expected(self, path: str | Path) -> XFrame | None:
        """Load a previously-exported XFrame as the fixture-verification
        `expected` golden (REQ-VIEW-RUN-1 fixture-verification mode) -- reuses
        `apps.gui.export.import_frame`'s npz+JSON format rather than
        inventing a second fixture format. Testable directly, mirroring
        `IoPanel.open_raw`/`export_to`."""
        try:
            frame = import_frame(path)
        except (OSError, KeyError, ValueError) as exc:
            self.status_label.setText(f"Failed to load expected frame: {exc}")
            return None
        self.expected_frame = frame
        self.status_label.setText(f"Expected frame loaded: {frame.shape}")
        return frame

    def _on_run_clicked(self) -> None:
        """Start `run_module` on a background thread (REQ-VIEW-ARCH-8)."""
        frame = self.io_panel.frame
        if frame is None:
            self.status_label.setText("Load a frame first")
            return
        stage = self.module_combo.currentText()
        module = default_registry()[stage]
        calib = make_synthetic_calibset(frame.shape, calib_kind_for_stage(stage))
        params = self.params_form.build_params()
        expected = self.expected_frame

        self._cancelled = False
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setVisible(True)
        self.status_label.setText(f"Running '{stage}'...")

        self._worker = CallableWorker(
            lambda: run_module(module, frame, calib, params, expected), self
        )
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(lambda msg: self._on_failed(stage, msg))
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_cancel_clicked(self) -> None:
        """Best-effort cancel: discard the result once the thread completes."""
        self._cancelled = True
        self.status_label.setText("Cancelling...")

    def _on_succeeded(self, result: ModuleRunResult) -> None:
        if self._cancelled:
            self.status_label.setText("Cancelled")
            return
        self.last_result = result
        self.compare_display.show_comparison(result.input_frame, result.output_frame)
        self.history_panel.show_history(result.output_frame.history)
        badge = ""
        if result.verification is not None:
            badge = f" [{'PASS' if result.verification.passed else 'FAIL'}]"
        self.status_label.setText(f"Ran '{self.module_combo.currentText()}'{badge}")

    def _on_failed(self, stage: str, message: str) -> None:
        if self._cancelled:
            self.status_label.setText("Cancelled")
            return
        self.status_label.setText(f"{stage} failed: {message}")

    def _on_finished(self) -> None:
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(False)

    def export_to(self, path: str | Path) -> tuple[Path, Path] | None:
        """Export the last run's output frame to `path` (#17, C-20). Testable
        directly, bypassing the file dialog (mirrors `IoPanel.open_raw`)."""
        if self.last_result is None:
            self.status_label.setText("Nothing to export yet")
            return None
        try:
            npz_path, json_path = export_frame(self.last_result.output_frame, path, _PROJECT_ROOT)
        except DataWriteRejectedError as exc:
            self.status_label.setText(f"Export refused: {exc}")
            return None
        self.status_label.setText(f"Exported to {npz_path.name}")
        return npz_path, json_path

    def _on_export_clicked(self) -> None:  # pragma: no cover - exercised via dialog only
        path, _ = QFileDialog.getSaveFileName(self, "Export output frame", "", "")
        if path:
            self.export_to(path)


class PipelineViewerTab(QWidget):
    """Phase 2: pick a CANONICAL_ORDER subset -> run_pipeline -> compare (REQ-VIEW-RUN-2)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.io_panel = IoPanel(self)
        self.stage_checks: dict[str, QCheckBox] = {
            stage: QCheckBox(stage, self) for stage in SELECTABLE_STAGES
        }
        for stage, check in self.stage_checks.items():
            check.setToolTip(
                f"Include the '{stage}' stage in this partial pipeline run "
                "(always executed in CANONICAL_ORDER, regardless of check order)."
            )
        self.run_button = QPushButton("Run pipeline", self)
        self.run_button.setToolTip(
            "Execute the checked stages via run_pipeline on a background "
            "thread, in CANONICAL_ORDER (REQ-VIEW-RUN-2/ARCH-8)."
        )
        self.run_button.clicked.connect(self._on_run_clicked)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setToolTip(
            "Best-effort cancel: discards the result once the background "
            "run completes (does not interrupt the computation itself)."
        )
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.export_button = QPushButton("Export final frame...", self)
        self.export_button.setToolTip(
            "Export the last run's final XFrame to a chosen path (npz + "
            "JSON sidecar, #17). Refused if the path is under data/ (C-20)."
        )
        self.export_button.clicked.connect(self._on_export_clicked)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setToolTip("A pipeline run is in progress on a background thread.")
        self.status_label = QLabel("No run yet", self)
        self.status_label.setToolTip("Shows the result or error of the last action.")
        self.compare_display = CompareDisplay(self)
        self.plot_before = self.compare_display.plot_before
        self.plot_after = self.compare_display.plot_after
        self.last_result: PipelineRunResult | None = None
        self._worker: CallableWorker | None = None
        self._cancelled = False

        stage_row = QHBoxLayout()
        for stage in SELECTABLE_STAGES:
            stage_row.addWidget(self.stage_checks[stage])
        run_row = QHBoxLayout()
        run_row.addWidget(self.run_button)
        run_row.addWidget(self.cancel_button)
        run_row.addWidget(self.export_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.io_panel)
        layout.addLayout(stage_row)
        layout.addLayout(run_row)
        layout.addWidget(self.progress)
        layout.addWidget(self.compare_display)
        layout.addWidget(self.status_label)

    def selected_stages(self) -> tuple[str, ...]:
        """Checked stages, in canonical relative order (`PipelineDefinition` requirement)."""
        return tuple(s for s in SELECTABLE_STAGES if self.stage_checks[s].isChecked())

    def _on_run_clicked(self) -> None:
        """Start `run_partial_pipeline` on a background thread (REQ-VIEW-ARCH-8)."""
        frame = self.io_panel.frame
        stages = self.selected_stages()
        if frame is None or not stages:
            self.status_label.setText("Load a frame and check at least one stage")
            return

        self._cancelled = False
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setVisible(True)
        self.status_label.setText(f"Running {len(stages)} stage(s)...")

        self._worker = CallableWorker(
            lambda: run_partial_pipeline(frame, stages), self
        )
        self._worker.succeeded.connect(lambda result: self._on_succeeded(result, stages))
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_cancel_clicked(self) -> None:
        """Best-effort cancel: discard the result once the thread completes."""
        self._cancelled = True
        self.status_label.setText("Cancelling...")

    def _on_succeeded(self, result: PipelineRunResult, stages: tuple[str, ...]) -> None:
        if self._cancelled:
            self.status_label.setText("Cancelled")
            return
        self.last_result = result
        if result.stage_comparisons:
            last = result.stage_comparisons[-1]
            self.compare_display.show_comparison(last.before, last.after)
        self.status_label.setText(f"Ran {len(stages)} stage(s): {', '.join(stages)}")

    def _on_failed(self, message: str) -> None:
        if self._cancelled:
            self.status_label.setText("Cancelled")
            return
        self.status_label.setText(f"pipeline failed: {message}")

    def _on_finished(self) -> None:
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(False)

    def export_to(self, path: str | Path) -> tuple[Path, Path] | None:
        """Export the last run's final frame to `path` (#17, C-20)."""
        if self.last_result is None:
            self.status_label.setText("Nothing to export yet")
            return None
        try:
            npz_path, json_path = export_frame(self.last_result.final_frame, path, _PROJECT_ROOT)
        except DataWriteRejectedError as exc:
            self.status_label.setText(f"Export refused: {exc}")
            return None
        self.status_label.setText(f"Exported to {npz_path.name}")
        return npz_path, json_path

    def _on_export_clicked(self) -> None:  # pragma: no cover - exercised via dialog only
        path, _ = QFileDialog.getSaveFileName(self, "Export final frame", "", "")
        if path:
            self.export_to(path)


class MetricsTab(QWidget):
    """Metrics delegation (C-09) + ROI round-trip (C-10) -- consumes the last
    Module Verifier / Pipeline Viewer output rather than loading its own file."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.frame: XFrame | None = None
        self.source_module_button = QPushButton("Use Module Verifier output", self)
        self.source_module_button.setToolTip(
            "Load the Module Verifier tab's last output frame as the metrics source."
        )
        self.source_pipeline_button = QPushButton("Use Pipeline Viewer output", self)
        self.source_pipeline_button.setToolTip(
            "Load the Pipeline Viewer tab's last final frame as the metrics source."
        )
        self.source_module_button.clicked.connect(lambda: self._load_source("module"))
        self.source_pipeline_button.clicked.connect(lambda: self._load_source("pipeline"))
        self.get_module_frame: Callable[[], XFrame | None] | None = None
        self.get_pipeline_frame: Callable[[], XFrame | None] | None = None

        self.image_plot = pg.PlotWidget(self)
        self.image_plot.setToolTip(
            "Metrics source frame -- drag the yellow ROI rectangle to move "
            "or resize it before 'Recompute MTF for ROI'."
        )
        self.roi = pg.RectROI([10, 10], [40, 40], pen="y")
        self.roi.setToolTip("ROI used by 'Recompute MTF for ROI' (C-10). Drag to move, corners to resize.")
        self._layer = None

        self.pitch_spin = QDoubleSpinBox(self)
        self.pitch_spin.setDecimals(4)
        self.pitch_spin.setRange(0.001, 10.0)
        self.pitch_spin.setValue(0.14)  # detector pitch (CLAUDE.md: CsI, 140um) -- editable, not hardcoded
        self.pitch_spin.setToolTip(
            "Detector pixel pitch in mm, used to convert MTF cycles/pixel to "
            "lp/mm (Nyquist = 1/(2*pitch)). Default 0.14mm = 140um CsI panel."
        )
        self.compute_button = QPushButton("Compute MTF (full frame)", self)
        self.compute_button.setToolTip(
            "Compute MTF over the full source frame via metrics.mtf.compute_mtf "
            "-- the GUI performs zero calculation itself (C-09)."
        )
        self.compute_button.clicked.connect(self._on_compute_clicked)
        self.roi_button = QPushButton("Recompute MTF for ROI (round-trip check)", self)
        self.roi_button.setToolTip(
            "Recompute MTF restricted to the yellow ROI rectangle, twice, "
            "and verify the results are bit-identical (reproducibility "
            "round-trip, C-10/C-16)."
        )
        self.roi_button.clicked.connect(self._on_roi_clicked)
        self.mtf_plot = pg.PlotWidget(self)
        self.mtf_plot.setToolTip("MTF curve -- the exact array metrics.mtf.compute_mtf returned.")
        self.roi_label = QLabel("ROI: none selected", self)
        self.roi_label.setToolTip("The exact ROI boundary used for the last recompute (C-10).")
        self.status_label = QLabel("No metrics computed yet", self)
        self.status_label.setToolTip("Shows the result or error of the last action.")

        source_row = QHBoxLayout()
        source_row.addWidget(self.source_module_button)
        source_row.addWidget(self.source_pipeline_button)
        button_row = QHBoxLayout()
        button_row.addWidget(QLabel("Pixel pitch (mm)", self))
        button_row.addWidget(self.pitch_spin)
        button_row.addWidget(self.compute_button)
        button_row.addWidget(self.roi_button)
        plots = QHBoxLayout()
        plots.addWidget(self.image_plot)
        plots.addWidget(self.mtf_plot)

        layout = QVBoxLayout(self)
        layout.addLayout(source_row)
        layout.addLayout(plots)
        layout.addLayout(button_row)
        layout.addWidget(self.roi_label)
        layout.addWidget(self.status_label)

    def _load_source(self, which: str) -> None:
        getter = self.get_module_frame if which == "module" else self.get_pipeline_frame
        frame = getter() if getter is not None else None
        if frame is None:
            self.status_label.setText(f"No {which} output available yet -- run it first")
            return
        self.set_frame(frame)
        self.status_label.setText(f"Loaded {which} output frame {frame.shape}")

    def set_frame(self, frame: XFrame) -> None:
        self.frame = frame
        self._layer = make_image_layer("metrics_source", frame.pixel)
        self.image_plot.clear()
        self.image_plot.addItem(self._layer.item)
        self.image_plot.addItem(self.roi)

    def _params(self) -> Params:
        # Only pixel pitch varies meaningfully per detector/session and is
        # user-editable (`pitch_spin`, C-10 measurement input). The remaining
        # MTF fitting knobs (oversample/edge-angle window) are the same [P]
        # defaults `tests/metrics/phantoms/params.py::make_params` uses --
        # tuning constants for the slanted-edge fit, not per-run inputs.
        return Params({
            "pixel_pitch_mm": self.pitch_spin.value(),
            "mtf_oversample": 4,
            "mtf_angle_min_deg": 1.5,
            "mtf_angle_max_deg": 3.0,
            "mtf_angle_margin_deg": 0.2,
        })

    def _on_compute_clicked(self) -> None:
        if self.frame is None:
            self.status_label.setText("Load a source frame first")
            return
        try:
            result = plot_mtf(self.mtf_plot, self.frame, self._params())
        except Exception as exc:  # noqa: BLE001 -- surfaced as status text (interactive tool)
            self.status_label.setText(f"MTF computation failed: {exc}")
            return
        self.status_label.setText(f"MTF computed: {len(result.get('mtf'))} frequency points")

    def _on_roi_clicked(self) -> None:
        if self.frame is None:
            self.status_label.setText("Load a source frame first")
            return
        bounds: RoiBounds = roi_bounds_from_rect_roi(self.roi, self.frame.shape)
        self.roi_label.setText(
            f"ROI: top={bounds.top} left={bounds.left} height={bounds.height} width={bounds.width}"
        )
        try:
            result_a = recompute_mtf_for_roi(self.frame, self._params(), bounds)
            result_b = recompute_mtf_for_roi(self.frame, self._params(), bounds)
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"ROI recompute failed: {exc}")
            return
        match = np.array_equal(result_a.get("mtf"), result_b.get("mtf"))
        self.status_label.setText(
            f"ROI round-trip {'MATCH (bit-identical)' if match else 'MISMATCH'} "
            f"({len(result_a.get('mtf'))} points)"
        )


class MainWindow(QMainWindow):
    """Verification GUI shell: Module Verifier + Pipeline Viewer + Metrics tabs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("XDET Verification GUI")
        self.module_tab = ModuleVerifierTab(self)
        self.pipeline_tab = PipelineViewerTab(self)
        self.metrics_tab = MetricsTab(self)
        self.metrics_tab.get_module_frame = (
            lambda: self.module_tab.last_result.output_frame
            if self.module_tab.last_result is not None
            else None
        )
        self.metrics_tab.get_pipeline_frame = (
            lambda: self.pipeline_tab.last_result.final_frame
            if self.pipeline_tab.last_result is not None
            else None
        )

        tabs = QTabWidget(self)
        tabs.addTab(self.module_tab, "Module Verifier")
        tabs.setTabToolTip(0, "Run one processing module directly and compare input/output.")
        tabs.addTab(self.pipeline_tab, "Pipeline Viewer")
        tabs.setTabToolTip(1, "Run a CANONICAL_ORDER subset via run_pipeline and compare stages.")
        tabs.addTab(self.metrics_tab, "Metrics")
        tabs.setTabToolTip(2, "Compute MTF (metrics/ engine delegation) and verify ROI round-trip.")
        self.setCentralWidget(tabs)

        self._build_menu()

    def _build_menu(self) -> None:
        """Menu bar with a Help menu ('How to use...' + 'About') -- the
        in-app entry point for usage guidance beyond per-widget tooltips."""
        help_menu = self.menuBar().addMenu("&Help")
        how_to_use_action = help_menu.addAction("How to use...")
        how_to_use_action.setToolTip("Open the usage guide for this app.")
        how_to_use_action.triggered.connect(self._show_help_dialog)
        about_action = help_menu.addAction("About")
        about_action.setToolTip("Show version and SPEC information.")
        about_action.triggered.connect(self._show_about_dialog)

    def _show_help_dialog(self) -> None:
        HelpDialog(self).exec()

    def _show_about_dialog(self) -> None:
        QMessageBox.about(self, "About XDET Verification GUI", ABOUT_TEXT)


def main() -> int:
    """Launch the verification GUI as a real, standalone process.

    @MX:ANCHOR: [AUTO] The actual `uv run python -m apps.gui.app` entry point
    -- prior to this, the app could only be exercised through pytest-qt's
    offscreen `qtbot` harness, which never launches it as a real process a
    user would run (found via user report, not covered by the Phase 1/2 test
    suite).
    """
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.resize(1400, 900)
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover - exercised by direct launch, not pytest
    import sys

    sys.exit(main())
