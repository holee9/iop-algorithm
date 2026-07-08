"""Offset correction: dark-frame subtraction (SWR-101~104, FR-C001).

I1 = I_raw - O, where O is the CalibSet(OFFSET) dark map. Negative results are
clamped to 0 (physical floor for unsigned raw) and the clamp rate is surfaced as
a scalar diagnostic on the history-chain entry (REQ-CORR-OFFSET-2). The module
consumes the pre-generated offset map; it never regenerates darks (SWR-101).

@MX:ANCHOR: [AUTO] `process` is the offset pipeline stage entry point invoked via
the orchestrator registry (REQ-CORR-CONTRACT-1/6).
@MX:REASON: every end-to-end run enters offset first; the subtract-and-clamp
contract and the history diagnostics are consumed by the SWR-104 residual gate.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import HistoryEntry, NoiseModel, XFrame

MODULE_NAME = "offset"
MODULE_VERSION = "1.0.0"

# CalibSet(OFFSET) data payload keys (SWR-101).
K_OFFSET_MAP = "O_map"  # static dark offset map O(x,y)
K_SIGMA_D = "sigma_d"  # per-pixel read-noise std (SWR-104 hook / noise init)
K_DELTA_O = "delta_O"  # Optional dynamic offset increment DeltaO(T) [B]

# Physical floor for unsigned raw after subtraction ([S], not tunable).
_RAW_FLOOR = 0.0


def _read_offset(calib: CalibSet, shape: tuple[int, ...]) -> np.ndarray:
    if K_OFFSET_MAP not in calib.data:
        raise ValueError(
            f"offset: CalibSet(OFFSET) missing required data key '{K_OFFSET_MAP}'"
        )
    o_map = np.asarray(calib.data[K_OFFSET_MAP], dtype=np.float64)
    if o_map.shape != shape:
        raise ValueError(
            f"offset: O_map shape {o_map.shape} != frame shape {shape}"
        )
    # Optional dynamic offset O_ref + DeltaO(T) (REQ-CORR-OFFSET-3, [B]).
    if K_DELTA_O in calib.data:
        delta = np.asarray(calib.data[K_DELTA_O], dtype=np.float64)
        if delta.shape != shape:
            raise ValueError(
                f"offset: delta_O shape {delta.shape} != frame shape {shape}"
            )
        o_map = o_map + delta
    return o_map


def _subtract_clamp(pixel: np.ndarray, o_map: np.ndarray) -> tuple[np.ndarray, float]:
    corrected = pixel - o_map
    negative = corrected < _RAW_FLOOR
    clamp_rate = float(np.count_nonzero(negative)) / corrected.size
    corrected = np.where(negative, _RAW_FLOOR, corrected)
    return corrected, clamp_rate


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Subtract the dark offset map, clamp negatives, record diagnostics.

    Returns a new XFrame; the input frame is treated as immutable (DATA-6).
    """
    o_map = _read_offset(calib, frame.shape)

    corrected, clamp_rate = _subtract_clamp(
        np.asarray(frame.pixel, dtype=np.float64), o_map
    )
    out_pixel = corrected.astype(frame.pixel.dtype)

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64, _ = _subtract_clamp(np.asarray(frame.pixel_f64, dtype=np.float64), o_map)

    new = frame.with_pixel(out_pixel, out_f64)

    # Initialize the read-noise sigma from the offset calibration when supplied
    # (SWR-101); alpha is untouched — correction modules do not re-estimate the
    # gain-scaling noise term (spec decision 2, SWR-701/T5 owns that).
    if K_SIGMA_D in calib.data:
        sigma_d = float(np.median(np.asarray(calib.data[K_SIGMA_D], dtype=np.float64)))
        new = _with_noise(new, NoiseModel(alpha=frame.noise.alpha, sigma=sigma_d))

    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra={"neg_clamp_rate": repr(clamp_rate)},
    )
    return new.record_history(entry)


def _with_noise(frame: XFrame, noise: NoiseModel) -> XFrame:
    from dataclasses import replace

    return replace(frame, noise=noise)
