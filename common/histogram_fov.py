"""Shared component: histogram / field-of-view analysis
(SWR-000-9, REQ-INFRA-STATIC-3).

@MX:NOTE: [AUTO] First real definition triggered by SPEC-METRICS-001 (T1). Used
by metrics.ndt (automatic uniform-region detection) and metrics.defect_stats
(distribution-based classification aid). Accuracy is the single goal; no speed
optimization (P2).
"""

from __future__ import annotations

import numpy as np


def compute_histogram(image: np.ndarray, bins: int) -> np.ndarray:
    """Intensity histogram counts over `bins` equal-width bins."""
    arr = np.asarray(image, dtype=np.float64).ravel()
    counts, _ = np.histogram(arr, bins=bins)
    return counts


def detect_fov(image: np.ndarray, *, rel_threshold: float = 0.5) -> np.ndarray:
    """Detect the exposed field-of-view as a boolean mask.

    A simple intensity threshold at `rel_threshold` of the dynamic range
    separates the collimated (low-signal) border from the exposed field. This
    is the minimal detector needed by the NDT uniform-region selector; a richer
    collimation model is deferred to the windowing WP (T6).
    """
    arr = np.asarray(image, dtype=np.float64)
    lo, hi = float(arr.min()), float(arr.max())
    if hi <= lo:
        return np.ones(arr.shape, dtype=bool)
    level = lo + rel_threshold * (hi - lo)
    return arr >= level


def largest_uniform_region(
    image: np.ndarray,
    roi_size: int,
    *,
    stride: int | None = None,
) -> tuple[tuple[int, int], np.ndarray]:
    """Return the (top,left) origin and pixels of the most uniform ROI.

    Scans candidate square ROIs of side `roi_size` on a regular grid and picks
    the one with the lowest coefficient of variation (std / |mean|). Used by the
    NDT SNR estimator to auto-select a uniform area when the caller does not
    supply an explicit ROI.
    """
    arr = np.asarray(image, dtype=np.float64)
    ny, nx = arr.shape
    if roi_size > ny or roi_size > nx:
        raise ValueError("roi_size larger than image")
    step = stride if stride is not None else roi_size // 2 or 1
    best_cov = np.inf
    best_origin = (0, 0)
    for top in range(0, ny - roi_size + 1, step):
        for left in range(0, nx - roi_size + 1, step):
            roi = arr[top : top + roi_size, left : left + roi_size]
            mean = roi.mean()
            if mean == 0:
                continue
            cov = roi.std() / abs(mean)
            if cov < best_cov:
                best_cov = cov
                best_origin = (top, left)
    top, left = best_origin
    return best_origin, arr[top : top + roi_size, left : left + roi_size]
