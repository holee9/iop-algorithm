"""Processing-history display: WHERE history exists, show it; else hide it (C-08).

@MX:NOTE: [AUTO] REQ-VIEW-COMPARE-7 is an Optional/WHERE requirement -- an
empty `XFrame.history` chain must not render an empty table, it must hide the
panel entirely (Scenario 10).
"""

from __future__ import annotations

from typing import Sequence

from qtpy.QtWidgets import QTableWidget, QTableWidgetItem, QWidget

from common.xframe import HistoryEntry

_COLUMNS = ("module_name", "module_version", "params_hash", "calibset_id")


class HistoryPanel(QTableWidget):
    """Table view of an `XFrame.history` chain (module_name/version/params_hash/calibset_id)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setColumnCount(len(_COLUMNS))
        self.setHorizontalHeaderLabels(list(_COLUMNS))
        self.setRowCount(0)
        self.setVisible(False)
        self.setToolTip(
            "Processing history chain of the displayed output XFrame -- one "
            "row per module that ran (module_name/version/params_hash/"
            "calibset_id), in execution order (C-08). Hidden automatically "
            "when the frame carries no history."
        )

    def show_history(self, history: Sequence[HistoryEntry]) -> None:
        """Populate rows from `history`; hides the panel when `history` is empty (C-08)."""
        if not history:
            self.setRowCount(0)
            self.setVisible(False)
            return
        self.setRowCount(len(history))
        for row, entry in enumerate(history):
            self.setItem(row, 0, QTableWidgetItem(entry.module_name))
            self.setItem(row, 1, QTableWidgetItem(entry.module_version))
            self.setItem(row, 2, QTableWidgetItem(entry.params_hash))
            self.setItem(row, 3, QTableWidgetItem(entry.calibset_id or ""))
        self.setVisible(True)
