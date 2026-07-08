"""Bad-pixel statistics: ASTM E2597 classification (REQ-METRICS-DEFECT, §2).

Seven defect classes are mapped from dark/flat stack statistics
(REQ-METRICS-DEFECT-1). The noisy rule (temporal std > 6x median) is the fixed
E2597-22 standard constant [S]; every other threshold is [P]-grade and injected
via Params (REQ-METRICS-DEFECT-3, no hardcoding).

@MX:ANCHOR: [AUTO] `classify_defects` is the DEFECT-group public entry point
(acceptance Scenario 6, XDET-TC-003 decision engine).
@MX:REASON: the class-code contract and per-class fractions are consumed by the
EV-103 miss-rate comparison; a code change desynchronizes downstream gating.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from enum import IntEnum

import numpy as np

from common import robust_stats
from common.contract import Params
from common.xframe import XFrame
from metrics.result import MetricCondition, MetricReadError, MetricResult, require_param

# @MX:NOTE: [AUTO] 6x-median noisy threshold is fixed by ASTM E2597-22 [S];
# it is intentionally NOT a Param (standard constant, not tunable).
NOISY_MEDIAN_MULTIPLIER = 6.0

P_MIN_FRAMES = "defect_min_frames"  # minimum stack count for statistics [P]
P_OVER_VALUE = "defect_over_value"  # over-range saturation level [P]
P_UNDER_VALUE = "defect_under_value"  # under-range floor level [P]
P_DEAD_GAIN_FRAC = "defect_dead_gain_frac"  # gain below frac*median => dead [P]
P_NONUNIFORM_FRAC = "defect_nonuniform_frac"  # gain deviation fraction [P]
P_LAG_FRAC = "defect_lag_frac"  # dark residual fraction (of median gain) [P]
P_UNSTABLE_FRAC = "defect_unstable_frac"  # dark temporal-std multiple [P]


class DefectClass(IntEnum):
    """E2597 pixel classification codes (0 = good, 1..7 = defect classes)."""

    GOOD = 0
    OVER_RANGE = 1
    UNDER_RANGE = 2
    NOISY = 3
    UNSTABLE = 4
    LAG = 5
    DEAD = 6
    NON_UNIFORM = 7


def _stack(frames: list[XFrame]) -> np.ndarray:
    return np.stack([np.asarray(f.pixel, dtype=np.float64) for f in frames], axis=0)


def classify_defects(
    dark_frames: list[XFrame],
    flat_frames: list[XFrame],
    params: Params,
    *,
    calibset_id: str | None = None,
    truth_map: np.ndarray | None = None,
) -> MetricResult:
    """Classify each pixel into the E2597 seven-class scheme.

    Args:
        dark_frames / flat_frames: dark and flat stacks (consumed read-only).
        params: externalized [P] thresholds (see module constants).
        calibset_id: consumed CalibSet id (metadata).
        truth_map: optional ground-truth class map; when provided the detection
            miss rate is computed against it (Scenario 6).

    Raises:
        MetricReadError: stack count below the minimum, or no valid (responsive)
            pixels remain (e.g. an all-dead ROI) (REQ-METRICS-DEFECT-5 / EC-4).
    """
    min_frames = require_param(params, P_MIN_FRAMES, int)
    if len(dark_frames) < min_frames or len(flat_frames) < min_frames:
        raise MetricReadError(
            f"defect stats: stack count below minimum ({min_frames}); "
            f"got dark={len(dark_frames)}, flat={len(flat_frames)}"
        )

    dark_mean, dark_std = robust_stats.temporal_mean_std(_stack(dark_frames))
    flat_mean, flat_std = robust_stats.temporal_mean_std(_stack(flat_frames))
    gain = flat_mean - dark_mean

    median_gain = float(np.median(gain))
    if median_gain <= 0:
        raise MetricReadError(
            "defect stats: non-positive median gain (no valid pixels / all-dead ROI)"
        )
    median_dark = float(np.median(dark_mean))
    median_flat_std = float(np.median(flat_std))
    median_dark_std = float(np.median(dark_std))

    over_value = require_param(params, P_OVER_VALUE, float)
    under_value = require_param(params, P_UNDER_VALUE, float)
    dead_frac = require_param(params, P_DEAD_GAIN_FRAC, float)
    nonuniform_frac = require_param(params, P_NONUNIFORM_FRAC, float)
    lag_frac = require_param(params, P_LAG_FRAC, float)
    unstable_frac = require_param(params, P_UNSTABLE_FRAC, float)

    over = flat_mean >= over_value
    under = flat_mean <= under_value
    noisy = flat_std > NOISY_MEDIAN_MULTIPLIER * median_flat_std
    unstable = dark_std > unstable_frac * median_dark_std
    lag = (dark_mean - median_dark) > lag_frac * median_gain
    dead = gain < dead_frac * median_gain
    nonuniform = np.abs(gain - median_gain) > nonuniform_frac * median_gain

    # Priority order: higher-priority classifications win (first match).
    class_map = np.full(gain.shape, DefectClass.GOOD, dtype=np.int8)
    for mask, code in (
        (over, DefectClass.OVER_RANGE),
        (under, DefectClass.UNDER_RANGE),
        (noisy, DefectClass.NOISY),
        (unstable, DefectClass.UNSTABLE),
        (lag, DefectClass.LAG),
        (dead, DefectClass.DEAD),
        (nonuniform, DefectClass.NON_UNIFORM),
    ):
        take = mask & (class_map == DefectClass.GOOD)
        class_map[take] = code

    total = class_map.size
    counts = {c.name: int(np.count_nonzero(class_map == c.value)) for c in DefectClass}
    fractions = {name: counts[name] / total for name in counts}

    warnings: list[str] = []
    miss_rate: float | None = None
    if truth_map is not None:
        truth = np.asarray(truth_map)
        planted = truth != DefectClass.GOOD
        n_planted = int(np.count_nonzero(planted))
        if n_planted > 0:
            detected = class_map != DefectClass.GOOD
            missed = int(np.count_nonzero(planted & ~detected))
            miss_rate = missed / n_planted

    return MetricResult(
        name="bad_pixel",
        values={
            "class_map": class_map,
            "counts": counts,
            "fractions": fractions,
            "miss_rate": miss_rate,
            "median_gain": median_gain,
        },
        condition=MetricCondition(
            correction_state="raw",
            params_hash=params.hash(),
            calibset_id=calibset_id,
        ),
        warnings=tuple(warnings),
    )
