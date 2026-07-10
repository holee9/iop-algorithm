"""Off-GUI-thread execution wrapper (REQ-VIEW-ARCH-8, C-19).

@MX:ANCHOR: [AUTO] `CallableWorker` is the sole mechanism `app.py`'s tabs use
to run a long operation (module execution, pipeline execution) outside the
GUI thread with a progress indicator and a best-effort cancel.
@MX:REASON: REQ-VIEW-ARCH-8 requires long-running work to run off the GUI
thread with progress display + cancel. `run_module`/`run_partial_pipeline`
are pure synchronous functions with no internal cancellation hook, and
REQ-VIEW-CORE-4 forbids adding one to the core pipeline -- cancel here is
necessarily best-effort: it discards the result on completion rather than
interrupting the computation mid-flight.
"""

from __future__ import annotations

from typing import Any, Callable

from qtpy.QtCore import QThread, Signal


class CallableWorker(QThread):
    """Runs a zero-argument callable on a background thread.

    Emits `succeeded(result)` on normal return, `failed(message)` when the
    callable raises -- never lets an exception escape onto the GUI thread.
    """

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[[], Any], parent: Any = None) -> None:
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:  # noqa: D102 - QThread override, not a public API
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001 - surfaced via `failed`, not raised
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)
