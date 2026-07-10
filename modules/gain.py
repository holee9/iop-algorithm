"""Gain correction: flat-field normalization (SWR-201~204, FR-C002).

I2 = I1 * G, where G is the CalibSet(GAIN) single-point gain map. Results above
the 16-bit ceiling are clamped and the clamp rate is surfaced on the history
entry (REQ-CORR-GAIN-2). Gain-map pixels outside the valid range [gain_min,
gain_max] ([T], Params) are NOT applied — the output keeps the ungained I1 value
and the pixel is flagged DEFECT so the fixed-order gain->defect hand-off carries
the candidate downstream (REQ-CORR-GAIN-3, spec decision 4).

@MX:ANCHOR: [AUTO] `process` is the gain pipeline stage entry point invoked via
the orchestrator registry (REQ-CORR-CONTRACT-1/6).
@MX:REASON: the range-guard + DEFECT hand-off is a load-bearing precondition for
the defect module's single-point interpolation of unclassified pixels (DEFECT-8).

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import HistoryEntry, MaskFlag, XFrame

MODULE_NAME = "gain"
MODULE_VERSION = "1.0.0"

# CalibSet(GAIN) data payload keys (SWR-201/202).
K_GAIN_MAP = "G_map"  # single-point gain map G(x,y)
K_ANCHOR_GAINS = "anchor_gains"  # Optional multi-point anchors (SWR-202, [B])

# Params keys.
P_GAIN_MIN = "gain_min"  # valid gain lower bound [T]
P_GAIN_MAX = "gain_max"  # valid gain upper bound [T]

# Params key names this module requires (SPEC-ERGO-001 REQUIRED_PARAMS manifest,
# key NAMES only — never sample values). Derived from the module constants above.
REQUIRED_PARAMS: tuple[str, ...] = (P_GAIN_MIN, P_GAIN_MAX)

# 16-bit unsigned ceiling ([S] fixed, not tunable — analogous to the raw floor).
_UPPER_LIMIT = 65535.0


def _require(params: Params, key: str) -> float:
    value = params.get(key)
    if value is None:
        raise ValueError(f"gain: missing required parameter '{key}'")
    return float(value)


def _read_gain(calib: CalibSet, shape: tuple[int, ...]) -> np.ndarray:
    if K_ANCHOR_GAINS in calib.data:
        # REQ-CORR-GAIN-4 (Optional, SWR-202) multi-point piecewise-linear gain
        # is deferred in P1 T2: the [B] dose-step anchors are not yet available
        # (spec Exclusions). Single-point path only.
        raise NotImplementedError(
            "gain: multi-point anchor gain (SWR-202) is deferred to a later "
            "milestone; provide a single-point 'G_map' CalibSet"
        )
    if K_GAIN_MAP not in calib.data:
        raise ValueError(
            f"gain: CalibSet(GAIN) missing required data key '{K_GAIN_MAP}'"
        )
    g_map = np.asarray(calib.data[K_GAIN_MAP], dtype=np.float64)
    if g_map.shape != shape:
        raise ValueError(f"gain: G_map shape {g_map.shape} != frame shape {shape}")
    return g_map


def _apply_gain(
    pixel: np.ndarray, g_map: np.ndarray, valid: np.ndarray
) -> tuple[np.ndarray, float, np.ndarray]:
    """Multiply valid pixels by G, clamp to the 16-bit ceiling.

    Invalid-gain pixels keep the ungained input value (no G applied).
    Returns (corrected, clamp_rate, over) where clamp_rate is over all pixels
    and `over` is the boolean mask of clamped (saturated) pixels.
    """
    gained = np.where(valid, pixel * g_map, pixel)
    over = gained > _UPPER_LIMIT
    clamp_rate = float(np.count_nonzero(over)) / gained.size
    corrected = np.where(over, _UPPER_LIMIT, gained)
    return corrected, clamp_rate, over


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Flat-field normalize, clamp, and hand off out-of-range gain pixels.

    Returns a new XFrame; the input frame is treated as immutable (DATA-6).
    """
    gain_min = _require(params, P_GAIN_MIN)
    gain_max = _require(params, P_GAIN_MAX)
    g_map = _read_gain(calib, frame.shape)

    valid = (g_map >= gain_min) & (g_map <= gain_max)
    invalid = ~valid

    corrected, clamp_rate, over = _apply_gain(
        np.asarray(frame.pixel, dtype=np.float64), g_map, valid
    )
    out_pixel = corrected.astype(frame.pixel.dtype)

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64, _, _ = _apply_gain(
            np.asarray(frame.pixel_f64, dtype=np.float64), g_map, valid
        )

    # Hand off out-of-range gain pixels as defect candidates (SWR-203).
    new_masks = np.asarray(frame.masks, dtype=np.uint8).copy()
    new_masks[invalid] |= np.uint8(MaskFlag.DEFECT)
    # Flag 16-bit-clamped pixels SATURATION so the defect stage does not
    # interpolate neighbours from clipped values (review finding 7).
    new_masks[over] |= np.uint8(MaskFlag.SATURATION)

    new = frame.with_pixel(out_pixel, out_f64)
    new = _with_masks(new, new_masks)

    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra={
            "upper_clamp_rate": clamp_rate,
            "invalid_gain_rate": float(np.count_nonzero(invalid)) / invalid.size,
        },
    )
    return new.record_history(entry)


def _with_masks(frame: XFrame, masks: np.ndarray) -> XFrame:
    from dataclasses import replace

    return replace(frame, masks=masks)
