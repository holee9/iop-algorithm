"""Contract-violating fixture modules — tests/ only (EC-3, EC-4).

These deliberately break the module contract so the harness / contract checker
can be shown to DETECT and REPORT the violation (negative-path coverage).
"""

from __future__ import annotations

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import HistoryEntry, XFrame

MODULE_VERSION = "0.0.0"


class WrongSignatureModule:
    """EC-3: signature does not match process(frame, calib, params)."""

    # Missing the `params` argument -> contract check must flag it.
    def process(self, frame: XFrame, calib: CalibSet) -> XFrame:  # noqa: D401
        return frame


class ExtraReturnModule:
    """EC-4: returns an extra value (tuple) instead of a bare XFrame."""

    def process(self, frame: XFrame, calib: CalibSet, params: Params):
        entry = HistoryEntry("extra_return", MODULE_VERSION, params.hash(), calib.calibset_id)
        # Contract violation: side-channel extra return value.
        return frame.record_history(entry), {"leak": 1}


class MutatingModule:
    """DATA-6: attempts to mutate the input frame's pixel buffer in place."""

    def process(self, frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
        # The buffer is read-only; this write raises ValueError, proving the
        # immutability contract is enforced.
        frame.pixel[0, 0] = 999.0
        return frame
