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


class WelfordAccumulator:
    """Streaming (online) element-wise mean/variance via Welford's algorithm.

    @MX:ANCHOR: [AUTO] Single online (incremental) mean/variance accumulator —
    the streaming sibling of ``temporal_mean_std`` (SWR-000-9, first consumer
    SPEC-NDT-001 T9 real-time SNRn adaptation). Consumed by
    ``metrics.ndt.SNRnAccumulator`` and any streaming statistic that must not
    retain the whole frame stack.
    @MX:REASON: fan_in spans the NDT streaming SNRn path plus its equivalence
    gate; the running (count, mean, M2) recurrence must stay numerically equal
    to the batch ``temporal_mean_std`` (population variance) or every streamed
    SNRn value diverges from the batch reference.

    Frames (or samples) are fed one at a time via :meth:`update`; the running
    mean and variance are updated incrementally so the full stack is never held
    in memory. The population variance (``ddof=0``) matches ``temporal_mean_std``
    (``np.std`` default). Accuracy is the single goal; no speed optimization (P2).
    """

    def __init__(self) -> None:
        self._count = 0
        self._mean: np.ndarray | None = None
        self._m2: np.ndarray | None = None

    @property
    def count(self) -> int:
        """Number of samples accumulated so far."""
        return self._count

    def update(self, sample: np.ndarray) -> "WelfordAccumulator":
        """Fold one sample (scalar or ndarray) into the running statistics."""
        arr = np.asarray(sample, dtype=np.float64)
        if self._count == 0:
            self._mean = np.zeros(arr.shape, dtype=np.float64)
            self._m2 = np.zeros(arr.shape, dtype=np.float64)
        elif arr.shape != self._mean.shape:
            raise ValueError(
                f"WelfordAccumulator: sample shape {arr.shape} != "
                f"accumulated shape {self._mean.shape}"
            )
        self._count += 1
        delta = arr - self._mean
        self._mean = self._mean + delta / self._count
        delta2 = arr - self._mean
        self._m2 = self._m2 + delta * delta2
        return self

    @property
    def mean(self) -> np.ndarray:
        """Running element-wise mean (a copy; empty accumulator is an error)."""
        if self._count == 0:
            raise ValueError("WelfordAccumulator.mean: no samples accumulated")
        return self._mean.copy()

    def variance(self, ddof: int = 0) -> np.ndarray:
        """Running element-wise variance (population ``ddof=0`` by default)."""
        if self._count == 0:
            raise ValueError("WelfordAccumulator.variance: no samples accumulated")
        denom = self._count - ddof
        if denom <= 0:
            raise ValueError(
                f"WelfordAccumulator.variance: ddof={ddof} >= count={self._count}"
            )
        return self._m2 / denom

    def std(self, ddof: int = 0) -> np.ndarray:
        """Running element-wise standard deviation (population by default)."""
        return np.sqrt(self.variance(ddof))


def online_mean_var(
    samples, ddof: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Run a :class:`WelfordAccumulator` over ``samples`` -> (mean, variance)."""
    acc = WelfordAccumulator()
    for sample in samples:
        acc.update(sample)
    return acc.mean, acc.variance(ddof)
