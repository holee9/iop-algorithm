"""Module selection + execution (REQ-VIEW-RUN-1): the sole output-producing path.

@MX:ANCHOR: [AUTO] `run_module` is the single function that turns a selected
`ProcessModule` + input XFrame into the input/output XFrame pair every
REQ-VIEW-COMPARE layer (C-05/C-06/C-07) is built from.
@MX:REASON: spec.md D1 draws a hard line between "producing the displayed
output" (`process()`, always) and "fixture-verification pass/fail" (
`run_harness`, only when an `expected` golden frame is supplied) -- this
function is where that separation is enforced so no caller can accidentally
wire the harness's `MismatchReport` in as the displayed frame.

Params input has no `magicgui` auto-form generator at Phase 1 (napari
fallback, spike report risk item 3); `ParamsForm` builds the PySide6 form
directly from a declared list of keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from qtpy.QtWidgets import QFormLayout, QLineEdit, QWidget

from common.calibset import CalibSet
from common.contract import MismatchReport, Params, ProcessModule, run_harness
from common.xframe import XFrame


@dataclass(frozen=True)
class ModuleRunResult:
    """Output of one module execution + optional fixture-verification badge."""

    input_frame: XFrame
    output_frame: XFrame
    verification: MismatchReport | None = None  # None when no `expected` golden was supplied


def run_module(
    module: ProcessModule,
    input_frame: XFrame,
    calib: CalibSet,
    params: Params,
    expected: XFrame | None = None,
) -> ModuleRunResult:
    """Execute `module.process` -- the SOLE producer of the displayed output XFrame.

    When `expected` is supplied (fixture-verification mode), `run_harness` is
    additionally invoked for a `MismatchReport` PASS/FAIL badge; this call
    never replaces or gates the `output_frame` already produced by `process`
    above (measurement != judgment, REQ-VIEW-RUN-1).
    """
    output = module.process(input_frame, calib, params)
    verification: MismatchReport | None = None
    if expected is not None:
        verification = run_harness(module, input_frame, calib, params, expected)
    return ModuleRunResult(
        input_frame=input_frame, output_frame=output, verification=verification
    )


class ParamsForm(QWidget):
    """Direct PySide6 form for `Params` input (no magicgui auto-form, napari fallback).

    One `QLineEdit` per declared key; `build_params()` casts the entered text
    (default `float`, overridable per key) into an immutable `Params` instance.

    @MX:NOTE: [AUTO] `add_field` lets the app add fields at runtime for a
    module the user selects (no hardcoded per-module key table in `apps/gui`
    -- SWR Params names are documented per-module in `modules/*.py`, not
    duplicated here; the user names the key they know a stage needs). Found
    missing entirely: `ParamsForm` was constructed with `keys=()` in
    `app.py`, so the running app could never actually accept a Params value
    for any module regardless of selection (zero prior test coverage caught
    this -- no test exercised `ParamsForm` at all before this fix).
    """

    def __init__(self, keys: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._edits: dict[str, QLineEdit] = {}
        self._layout = QFormLayout(self)
        for key in keys:
            self._add_row(key)

    def _add_row(self, key: str) -> QLineEdit:
        edit = QLineEdit(self)
        self._layout.addRow(key, edit)
        self._edits[key] = edit
        return edit

    def add_field(self, key: str) -> None:
        """Add a new named field at runtime; a no-op if `key` already exists
        or is blank (idempotent -- safe to call repeatedly from a UI handler)."""
        if not key or key in self._edits:
            return
        self._add_row(key)

    def set_value(self, key: str, value: Any) -> None:
        if key not in self._edits:
            self._add_row(key)
        self._edits[key].setText(str(value))

    def build_params(self, casts: Mapping[str, Callable[[str], Any]] | None = None) -> Params:
        """Read every non-empty field into a fresh `Params` (unset keys are omitted)."""
        casts = casts or {}
        values: dict[str, Any] = {}
        for key, edit in self._edits.items():
            text = edit.text()
            if text == "":
                continue
            cast = casts.get(key, float)
            try:
                values[key] = cast(text)
            except ValueError:
                values[key] = text
        return Params(values)
