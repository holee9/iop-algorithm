"""First-frame lag and ghost CNR (REQ-METRICS-LAG, measurement protocol §1.5).

first-frame lag % (ASTM E2597): from a post-exposure frame sequence, the first
residual-frame signal as a percentage of the last exposed-frame signal, both
referenced to the settled dark baseline (REQ-METRICS-LAG-1..2). Ghost CNR
(REQ-METRICS-LAG-5, mandatory): residual contrast-to-noise after a high-contrast
exposure followed by uniform exposure.

@MX:ANCHOR: [AUTO] `compute_first_frame_lag` and `compute_ghost_cnr` are the
LAG-group public entry points (acceptance Scenario 5 and Scenario 8).
@MX:REASON: XDET-TC-004 / XDET-TC-005 decision engines consume these; the
percentage and CNR conventions are contractual.

All constants arrive through Params (REQ-METRICS-CORE-4). Accuracy is the single
goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common import robust_stats
from common.contract import Params
from common.xframe import XFrame
from metrics.result import MetricCondition, MetricReadError, MetricResult

P_EXPOSURE_END = "lag_exposure_end_index"  # index of last exposed frame (optional)
P_BASELINE = "lag_dark_baseline"  # settled dark offset (optional; else last frame)
P_MIN_EXPOSED = "lag_min_exposed_signal"  # saturation-near premise floor [P]


def _frame_signal(frame: XFrame) -> float:
    return robust_stats.robust_mean(np.asarray(frame.pixel, dtype=np.float64))


def compute_first_frame_lag(
    frames: list[XFrame],
    params: Params,
    *,
    calibset_id: str | None = None,
) -> MetricResult:
    """Compute first-frame lag % from an exposure/decay frame sequence.

    Args:
        frames: ordered frames spanning exposure end into the residual decay
            (consumed read-only).
        params: externalized constants (optional exposure-end index / baseline,
            saturation-near premise floor).
        calibset_id: consumed CalibSet id (metadata).

    Raises:
        MetricReadError: sequence too short to contain a residual frame.
    """
    if len(frames) < 2:
        raise MetricReadError("first-frame lag: need >= 2 frames (exposed + residual)")
    signals = np.array([_frame_signal(f) for f in frames], dtype=np.float64)

    end_idx = params.get(P_EXPOSURE_END)
    last_exposed = int(end_idx) if end_idx is not None else int(np.argmax(signals))
    first_res = last_exposed + 1
    if first_res >= len(frames):
        raise MetricReadError(
            "first-frame lag: no residual frame after the exposed frame"
        )

    baseline = params.get(P_BASELINE)
    dark = float(baseline) if baseline is not None else float(signals[-1])

    exposed_signal = signals[last_exposed] - dark
    residual_signal = signals[first_res] - dark

    warnings: list[str] = []
    min_exposed = params.get(P_MIN_EXPOSED)
    if min_exposed is not None and exposed_signal < float(min_exposed):
        warnings.append(
            f"first-frame lag: exposed signal {exposed_signal:.2f} below the "
            f"saturation-near premise floor ({min_exposed}); result low-confidence"
        )
    if exposed_signal <= 0:
        raise MetricReadError(
            "first-frame lag: non-positive exposed signal after baseline removal"
        )

    lag_pct = float(residual_signal / exposed_signal * 100.0)
    return MetricResult(
        name="first_frame_lag",
        values={
            "first_frame_lag_pct": lag_pct,
            "last_exposed_index": last_exposed,
            "first_residual_index": first_res,
            "dark_baseline": dark,
        },
        condition=MetricCondition(
            params_hash=params.hash(),
            calibset_id=calibset_id,
            beam_quality=params.get("beam_quality"),
            dose_level=params.get("dose_level"),
        ),
        warnings=tuple(warnings),
    )


def compute_ghost_cnr(
    ghost_frame: XFrame,
    foreground_roi: tuple[int, int, int, int],
    background_roi: tuple[int, int, int, int],
    params: Params,
    *,
    calibset_id: str | None = None,
) -> MetricResult:
    """Compute residual (ghost) CNR from a uniform frame after high contrast.

    CNR = |mean_fg - mean_bg| / std_bg, where the foreground ROI overlays the
    location of the prior high-contrast pattern and the background ROI a clean
    area (REQ-METRICS-LAG-5).

    Args:
        ghost_frame: uniform-exposure frame carrying the residual (read-only).
        foreground_roi / background_roi: (top, left, height, width) boxes.
        params: externalized constants (metadata pass-through).
        calibset_id: consumed CalibSet id (metadata).
    """
    image = np.asarray(ghost_frame.pixel, dtype=np.float64)

    def _crop(box: tuple[int, int, int, int]) -> np.ndarray:
        t, l, h, w = box
        return image[t : t + h, l : l + w]

    fg = _crop(foreground_roi)
    bg = _crop(background_roi)
    mean_fg = float(fg.mean())
    mean_bg = float(bg.mean())
    std_bg = float(bg.std())
    if std_bg == 0:
        raise MetricReadError("ghost CNR: background noise is zero")
    cnr = abs(mean_fg - mean_bg) / std_bg
    return MetricResult(
        name="ghost_cnr",
        values={
            "ghost_cnr": cnr,
            "mean_foreground": mean_fg,
            "mean_background": mean_bg,
            "std_background": std_bg,
        },
        condition=MetricCondition(
            roi=foreground_roi,
            params_hash=params.hash(),
            calibset_id=calibset_id,
        ),
    )
