"""File selection panel + read-execute-only write guard (REQ-VIEW-CORE-1, C-20).

@MX:ANCHOR: [AUTO] `guard_output_path` is the single choke point every export
path (Phase 1 minimal, Phase 2 #17 full) must call before writing anything.
@MX:REASON: C-20/REQ-VIEW-RUN-7/-8 is a HARD invariant (read-execute-only);
every future export utility (`export.py`, Phase 2) reuses this exact guard so
the "single deterministic path" the spec requires is not re-implemented ad hoc.
"""

from __future__ import annotations

from pathlib import Path

from qtpy.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from common.io import load_raw_frame
from common.xframe import XFrame

# The one golden-data root the GUI must never write under (C-20, REQ-VIEW-RUN-8).
_PROTECTED_ROOT_NAME = "data"


class DataWriteRejectedError(PermissionError):
    """Raised when a GUI operation attempts to write under the protected `data/` root."""


def guard_output_path(path: str | Path, project_root: str | Path) -> Path:
    """Refuse any output path resolving under `<project_root>/data` (C-20/EC-4).

    Returns:
        The resolved (absolute) path when it is OUTSIDE the protected root.

    Raises:
        DataWriteRejectedError: `path` resolves under `<project_root>/data`.
    """
    resolved = Path(path).resolve()
    protected = Path(project_root).resolve() / _PROTECTED_ROOT_NAME
    try:
        resolved.relative_to(protected)
    except ValueError:
        return resolved
    raise DataWriteRejectedError(
        f"refusing to write under the protected root '{protected}': {resolved}"
    )


class IoPanel(QWidget):
    """File-open widget: dialog -> `common.io.load_raw_frame` -> XFrame (C-04)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.frame: XFrame | None = None
        self.raw_path: Path | None = None
        self._label = QLabel("No file loaded", self)
        self._button = QPushButton("Open raw...", self)
        self._button.clicked.connect(self._on_open_clicked)
        layout = QVBoxLayout(self)
        layout.addWidget(self._button)
        layout.addWidget(self._label)

    def _on_open_clicked(self) -> None:  # pragma: no cover - exercised via dialog only
        path, _ = QFileDialog.getOpenFileName(
            self, "Open raw frame", "", "Raw files (*.raw *.dat)"
        )
        if path:
            self.open_raw(path)

    def open_raw(self, raw_path: str | Path, meta_path: str | Path | None = None) -> XFrame | None:
        """Load a raw+JSON frame directly (used by both the dialog handler and tests).

        Returns `None` (and reports a status message) on malformed input --
        `load_raw_frame` raises `ValueError` for a missing `resolution` key or
        a raw/metadata size mismatch, and this is a Qt click-slot call site
        with no surrounding `CallableWorker`/exception boundary, so letting it
        propagate would crash the app instead of reporting a load error.
        """
        try:
            frame = load_raw_frame(raw_path, meta_path)
        except (ValueError, OSError) as exc:
            self._label.setText(f"Failed to load {Path(raw_path).name}: {exc}")
            return None
        self.frame = frame
        self.raw_path = Path(raw_path)
        self._label.setText(f"Loaded {self.raw_path.name} {frame.shape}")
        return frame
