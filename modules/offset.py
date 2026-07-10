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
from common.xframe import HistoryEntry, MaskFlag, NoiseModel, XFrame

MODULE_NAME = "offset"
MODULE_VERSION = "1.1.0"

# CalibSet(OFFSET) data payload keys (SWR-101).
K_OFFSET_MAP = "O_map"  # static dark offset map O(x,y)
K_SIGMA_D = "sigma_d"  # per-pixel read-noise std (SWR-104 hook / noise init)
K_DELTA_O = "delta_O"  # Optional dynamic offset increment DeltaO(T) [B]

# Params keys.
P_RAW_SAT = "raw_saturation_threshold"  # raw saturation point S_th [B] (SWR-601)

# Params key names this module requires (SPEC-ERGO-001 REQUIRED_PARAMS manifest).
REQUIRED_PARAMS: tuple[str, ...] = (P_RAW_SAT,)

# Physical floor for unsigned raw after subtraction ([S], not tunable).
_RAW_FLOOR = 0.0


def _require(params: Params, key: str) -> float:
    """Fetch a REQUIRED Params key, raising an explicit error when absent.

    @MX:NOTE: [AUTO] TBD-[B] values (raw_saturation_threshold) are never given a
    silent in-module default (SWR-000-5 / no-silent-default). The caller must
    inject the dose-step response saturation point (appendix A); a missing key
    is a configuration error, not a reason to invent ~0.98*full-scale.
    """
    value = params.get(key)
    if value is None:
        raise ValueError(f"offset: missing required parameter '{key}'")
    return float(value)


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

    # REQ-CORR-OFFSET-4: raw saturation detection BEFORE subtraction. offset is
    # the only stage that receives I_raw, so it is the sole locus of raw
    # saturation detection (SPEC-LNSG-001 decision 2). Pixels with I_raw >= S_th
    # are flagged SATURATION; the flag accumulates (union) with the gain-clamp
    # SATURATION downstream and is consumed by the T3 saturation module.
    s_th = _require(params, P_RAW_SAT)
    raw_in = np.asarray(frame.pixel, dtype=np.float64)
    raw_sat = raw_in >= s_th
    raw_sat_rate = float(np.count_nonzero(raw_sat)) / raw_sat.size

    corrected, clamp_rate = _subtract_clamp(raw_in, o_map)
    out_pixel = corrected.astype(frame.pixel.dtype)

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64, _ = _subtract_clamp(np.asarray(frame.pixel_f64, dtype=np.float64), o_map)

    new = frame.with_pixel(out_pixel, out_f64)

    if raw_sat.any():
        new_masks = np.asarray(frame.masks, dtype=np.uint8).copy()
        new_masks[raw_sat] |= np.uint8(MaskFlag.SATURATION)
        new = _with_masks(new, new_masks)

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
        extra={"neg_clamp_rate": clamp_rate, "raw_sat_rate": raw_sat_rate},
    )
    return new.record_history(entry)


def _with_noise(frame: XFrame, noise: NoiseModel) -> XFrame:
    from dataclasses import replace

    return replace(frame, noise=noise)


def _with_masks(frame: XFrame, masks: np.ndarray) -> XFrame:
    from dataclasses import replace

    return replace(frame, masks=masks)
