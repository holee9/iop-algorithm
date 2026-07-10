"""PySide6 + pyqtgraph verification GUI shell -- SPEC-VIEWER-001 (Phase 1+2).

@MX:ANCHOR: [AUTO] `MainWindow` is the single running entry point that wires
every Phase 1/2 building block (`io_panel`/`module_panel`/`layers`/`probe`/
`history_panel`/`metrics_panel`/`pipeline_panel`) into one operable app --
the "GUI 앱으로 동작" requirement, not just a set of independently-tested
functions. napari is not used (Phase 0 spike fallback, pyqtgraph single path
-- `.moai/reports/SPEC-VIEWER-001-spike.md`).
@MX:REASON: `tests/apps/gui/test_tc_viewer_headless.py`'s end-to-end smoke
test drives THIS class (button clicks via qtbot, not the underlying
functions directly) as the project's real "does the app actually run"
verification (C-15).

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

import pyqtgraph as pg
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from apps.gui.history_panel import HistoryPanel
from apps.gui.io_panel import IoPanel
from apps.gui.layers import CompareView, make_image_layer
from apps.gui.module_panel import ModuleRunResult, ParamsForm, run_module
from apps.gui.pipeline_panel import (
    SELECTABLE_STAGES,
    PipelineRunResult,
    run_partial_pipeline,
)
from apps.gui.worker import CallableWorker
from common.calibset import CalibKind
from common.synth_calibset import make_synthetic_calibset
from modules.registry import default_registry
from pipeline.orchestrator import _KIND_BY_STAGE


class ModuleVerifierTab(QWidget):
    """Phase 1: load a frame -> pick one module -> run -> compare + history (REQ-VIEW-RUN-1)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.io_panel = IoPanel(self)
        self.module_combo = QComboBox(self)
        self.module_combo.addItems(sorted(default_registry()))
        self.params_form = ParamsForm(keys=(), parent=self)
        self.run_button = QPushButton("Run module", self)
        self.run_button.clicked.connect(self._on_run_clicked)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)  # indeterminate (no per-stage % from the engine)
        self.progress.setVisible(False)
        self.status_label = QLabel("No run yet", self)
        self.plot_before = pg.PlotWidget(self)
        self.plot_after = pg.PlotWidget(self)
        self.history_panel = HistoryPanel(self)
        self.last_result: ModuleRunResult | None = None
        self._worker: CallableWorker | None = None
        self._cancelled = False

        controls = QHBoxLayout()
        controls.addWidget(self.module_combo)
        controls.addWidget(self.run_button)
        controls.addWidget(self.cancel_button)
        plots = QHBoxLayout()
        plots.addWidget(self.plot_before)
        plots.addWidget(self.plot_after)

        layout = QVBoxLayout(self)
        layout.addWidget(self.io_panel)
        layout.addLayout(controls)
        layout.addWidget(self.params_form)
        layout.addWidget(self.progress)
        layout.addLayout(plots)
        layout.addWidget(self.status_label)
        layout.addWidget(self.history_panel)

    def _on_run_clicked(self) -> None:
        """Start `run_module` on a background thread (REQ-VIEW-ARCH-8)."""
        frame = self.io_panel.frame
        if frame is None:
            self.status_label.setText("Load a frame first")
            return
        stage = self.module_combo.currentText()
        module = default_registry()[stage]
        calib = make_synthetic_calibset(
            frame.shape, CalibKind(_KIND_BY_STAGE.get(stage, "other"))
        )
        params = self.params_form.build_params()

        self._cancelled = False
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setVisible(True)
        self.status_label.setText(f"Running '{stage}'...")

        self._worker = CallableWorker(
            lambda: run_module(module, frame, calib, params), self
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
        self.plot_before.clear()
        self.plot_after.clear()
        before_layer = make_image_layer("input", result.input_frame.pixel)
        after_layer = make_image_layer("output", result.output_frame.pixel)
        CompareView(
            before=before_layer,
            after=after_layer,
            plot_before=self.plot_before,
            plot_after=self.plot_after,
        )
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


class PipelineViewerTab(QWidget):
    """Phase 2: pick a CANONICAL_ORDER subset -> run_pipeline -> compare (REQ-VIEW-RUN-2)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.io_panel = IoPanel(self)
        self.stage_checks: dict[str, QCheckBox] = {
            stage: QCheckBox(stage, self) for stage in SELECTABLE_STAGES
        }
        self.run_button = QPushButton("Run pipeline", self)
        self.run_button.clicked.connect(self._on_run_clicked)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.status_label = QLabel("No run yet", self)
        self.plot_before = pg.PlotWidget(self)
        self.plot_after = pg.PlotWidget(self)
        self.last_result: PipelineRunResult | None = None
        self._worker: CallableWorker | None = None
        self._cancelled = False

        stage_row = QHBoxLayout()
        for stage in SELECTABLE_STAGES:
            stage_row.addWidget(self.stage_checks[stage])
        run_row = QHBoxLayout()
        run_row.addWidget(self.run_button)
        run_row.addWidget(self.cancel_button)
        plots = QHBoxLayout()
        plots.addWidget(self.plot_before)
        plots.addWidget(self.plot_after)

        layout = QVBoxLayout(self)
        layout.addWidget(self.io_panel)
        layout.addLayout(stage_row)
        layout.addLayout(run_row)
        layout.addWidget(self.progress)
        layout.addLayout(plots)
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
        self.plot_before.clear()
        self.plot_after.clear()
        if result.stage_comparisons:
            last = result.stage_comparisons[-1]
            before_layer = make_image_layer("before", last.before.pixel)
            after_layer = make_image_layer("after", last.after.pixel)
            CompareView(
                before=before_layer,
                after=after_layer,
                plot_before=self.plot_before,
                plot_after=self.plot_after,
            )
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


class MainWindow(QMainWindow):
    """Verification GUI shell: Module Verifier (Phase 1) + Pipeline Viewer (Phase 2)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("XDET Verification GUI")
        self.module_tab = ModuleVerifierTab(self)
        self.pipeline_tab = PipelineViewerTab(self)

        tabs = QTabWidget(self)
        tabs.addTab(self.module_tab, "Module Verifier")
        tabs.addTab(self.pipeline_tab, "Pipeline Viewer")
        self.setCentralWidget(tabs)
