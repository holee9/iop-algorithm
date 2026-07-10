"""Namespace package for GUI verification sub-projects (SPEC-VIEWER-001).

Not part of the core golden-model pipeline (`common/modules/pipeline/metrics`).
`apps.gui` consumes those four packages unidirectionally (REQ-VIEW-ARCH-1); the
core packages never import `apps` (import-linter forbidden contract, tracked
separately per plan.md).
"""

from __future__ import annotations
