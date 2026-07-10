"""XDET common layer: shared data contracts and foundational components.

This package is the bottom of the dependency graph. It must NOT import from
`modules`, `pipeline`, or `metrics` (enforced by import-linter, SWR-000-8).

Curated public re-exports + `__all__` (SPEC-ERGO-001 REQ-ERGO-EXPORTS,
`pipeline/__init__.py` precedent). Re-exports come ONLY from this package's own
submodules (never an upward/cross-package import), so the layering contract and
the acyclic import graph stay intact. Existing deep-path imports (e.g.
`from common.contract import Params`) keep working unchanged (additive).
"""

from common.calibset import CalibKind, CalibSet
from common.contract import (
    PROCESS_PARAM_NAMES,
    MismatchReport,
    Params,
    ProcessModule,
    StatefulModule,
    check_process_contract,
    run_harness,
    run_stateful_harness,
)
from common.xframe import (
    HistoryEntry,
    MaskFlag,
    NoiseModel,
    XFrame,
    hash_params,
    new_frame,
)

__all__ = [
    # xframe
    "XFrame",
    "NoiseModel",
    "HistoryEntry",
    "MaskFlag",
    "new_frame",
    "hash_params",
    # contract
    "Params",
    "ProcessModule",
    "StatefulModule",
    "MismatchReport",
    "check_process_contract",
    "run_harness",
    "run_stateful_harness",
    "PROCESS_PARAM_NAMES",
    # calibset
    "CalibSet",
    "CalibKind",
]
