"""PySide6 + pyqtgraph verification GUI shell (Phase 1) -- SPEC-VIEWER-001.

Wires `io_panel` (file open), `module_panel` (module selection/execution),
`layers`/`probe` (image/diff/mask display + hover) and `history_panel`
(WHERE history exists) into one `QMainWindow`. napari is not used (Phase 0
spike fallback, pyqtgraph single path -- `.moai/reports/SPEC-VIEWER-001-spike.md`).

Phase 2 (pipeline comparison viewer) reuses this shell via an additional tab;
this Phase 1 shell only wires the unit-module verifier surface.
"""

from __future__ import annotations

from qtpy.QtWidgets import QMainWindow, QTabWidget, QWidget

from apps.gui.history_panel import HistoryPanel
from apps.gui.io_panel import IoPanel
from apps.gui.module_panel import ParamsForm


class MainWindow(QMainWindow):
    """Phase 1 unit-module verifier shell (tab/dock switch reserved for Phase 2)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("XDET Verification GUI (Phase 1)")
        self.io_panel = IoPanel(self)
        self.history_panel = HistoryPanel(self)
        self.params_form = ParamsForm(keys=(), parent=self)

        tabs = QTabWidget(self)
        tabs.addTab(self.io_panel, "Load")
        tabs.addTab(self.params_form, "Params")
        tabs.addTab(self.history_panel, "History")
        self.setCentralWidget(tabs)
