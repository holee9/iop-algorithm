"""Shared component: robust statistics (SWR-000-9, REQ-INFRA-STATIC-3).

@MX:ANCHOR: [AUTO] Single implementation of the outlier-resistant statistics
shared by metrics.mtf (LSF handling), metrics.defect_stats (median / MAD, the
6x-median noise rule) and metrics.ndt (uniform-region SNR).
@MX:REASON: fan_in spans three metric groups; a divergent MAD scaling would
change the E2597 noisy-pixel counts and every SNR value.

First real definition triggered by SPEC-METRICS-001 (T1). Accuracy is the single
goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

# Consistency constant making MAD an unbiased estimator of the standard
# deviation for normally distributed data ([S] statistical constant).
_MAD_TO_STD = 1.4826


def robust_mean(values: np.ndarray) -> float:
    """Outlier-resistant central tendency (the median)."""
    arr = np.asarray(values, dtype=np.float64).ravel()
    if arr.size == 0:
        raise ValueError("robust_mean requires at least one value")
    return float(np.median(arr))


def robust_std(values: np.ndarray) -> float:
    """Outlier-resistant dispersion via the median absolute deviation (MAD)."""
    arr = np.asarray(values, dtype=np.float64).ravel()
    if arr.size == 0:
        raise ValueError("robust_std requires at least one value")
    med = np.median(arr)
    mad = np.median(np.abs(arr - med))
    return float(_MAD_TO_STD * mad)


def mad(values: np.ndarray) -> float:
    """Raw median absolute deviation (no normal-consistency scaling)."""
    arr = np.asarray(values, dtype=np.float64).ravel()
    med = np.median(arr)
    return float(np.median(np.abs(arr - med)))


def temporal_mean_std(stack: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-pixel temporal mean and standard deviation over a frame stack.

    Args:
        stack: array of shape (n_frames, Ny, Nx).

    Returns:
        (mean_map, std_map), each (Ny, Nx).
    """
    arr = np.asarray(stack, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError("stack must have shape (n_frames, Ny, Nx)")
    return arr.mean(axis=0), arr.std(axis=0)
