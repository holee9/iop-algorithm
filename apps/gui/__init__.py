"""Verification GUI (Phase 1: unit-module verifier) -- SPEC-VIEWER-001.

@MX:NOTE: [AUTO] `apps/gui` is a read-execute-only consumer of the core
4-layer pipeline (`common`/`modules`/`pipeline`/`metrics`); it never mutates
`data/` golden fixtures/CalibSets (C-20) and never computes metrics itself
(C-09). Stack: pyqtgraph + PySide6 (Phase 0 spike fallback from napari --
`.moai/reports/SPEC-VIEWER-001-spike.md`).
"""

from __future__ import annotations
