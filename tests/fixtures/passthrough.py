"""Reference passthrough (identity) module — tests/ fixture only.

@MX:NOTE: [AUTO] Framework self-test target (REQ-INFRA-CONTRACT-3). It obeys the
canonical `process(XFrame, CalibSet, Params) -> XFrame` contract, mutates
nothing on the input (DATA-6), and appends a deterministic history entry
(DATA-4). The output pixel/mask/noise are identical to the input (identity);
only the history chain grows.

This module is intentionally under tests/ and NOT in modules/ (SPEC decision 1).
It imports only from `common`, mirroring the dependency rule real modules obey.
"""

from __future__ import annotations

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import HistoryEntry, XFrame

MODULE_NAME = "reference_passthrough"
MODULE_VERSION = "1.0.0"


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Identity transform that records its invocation in the history chain."""
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
    )
    return frame.record_history(entry)


def expected_output(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """The deterministic expected result for a given input (identity + history).

    Used by the harness fixture to build the expected XFrame independently of
    `process`, so the comparison is meaningful.
    """
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
    )
    return frame.record_history(entry)
