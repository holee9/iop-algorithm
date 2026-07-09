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


def _otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    """Otsu's between-class-variance-maximizing threshold over `values`.

    Robust to class imbalance: it separates a dark and a bright mode regardless of
    their relative areas, so a border-dominant frame (border >= 50% area) is split
    correctly where a median anchor falls inside the border and fails.
    """
    a = values.ravel()
    lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        return lo
    hist, edges = np.histogram(a, bins=bins, range=(lo, hi))
    p = hist.astype(np.float64)
    total = p.sum()
    if total <= 0.0:
        return lo
    p /= total
    centers = 0.5 * (edges[:-1] + edges[1:])
    w0 = np.cumsum(p)
    w1 = 1.0 - w0
    m0 = np.cumsum(p * centers) / np.maximum(w0, 1e-12)
    m_total = float(np.sum(p * centers))
    m1 = (m_total - np.cumsum(p * centers)) / np.maximum(w1, 1e-12)
    between = w0 * w1 * (m0 - m1) ** 2
    return float(centers[int(np.argmax(between))])


# A distinct collimated border is UNEXPOSED (behind the blades): its level sits
# far below the exposed bulk. Only when the dark-class level is under this fraction
# of the bright-class level is a border deemed present ([P] gap ratio); otherwise
# the frame is treated as fully exposed (no border to exclude).
_BORDER_GAP_RATIO = 0.15


def detect_collimation_field(
    image: np.ndarray, *, rel_threshold: float = 0.35
) -> np.ndarray:
    """Recognize the collimation field: the exposed region inside the collimator.

    Extends detect_fov for the windowing WP (SWR-901 step 1, REQ-POST-WINDOW-1).
    The collimated border (unexposed, very low signal behind the collimator blades)
    is a distinct dark mode far below the exposed bulk. The dark/exposed split is
    found with an Otsu threshold on LOG intensity — log-space compresses the bright
    direct-exposure tail so Otsu locks onto the border/exposed valley rather than an
    exposed/direct valley (immunity to bright outliers), while still splitting a
    border-dominant frame (>= 50% area) correctly where a plain median anchor fails.

    A border is only excluded when it is genuinely dark: the dark-class median must
    fall below ``_BORDER_GAP_RATIO * bright-class median``. Otherwise (unimodal full
    exposure, or an anatomy+direct frame with NO dark border) the whole frame is the
    field (EC-2). When a border is present, pixels below ``rel_threshold *
    bright_reference`` (bright_reference = median of the exposed/bright class, robust
    to the direct-exposure minority) are classified as collimated.

    Returns a boolean mask (True = inside the exposed field). A degenerate
    non-positive median, or an unsplittable (flat) frame, yields an all-True mask.
    """
    arr = np.asarray(image, dtype=np.float64)
    median = float(np.median(arr))
    if median <= 0.0:
        return np.ones(arr.shape, dtype=bool)
    positive = arr[arr > 0.0]
    if positive.size == 0:
        return np.ones(arr.shape, dtype=bool)
    log_arr = np.log10(np.maximum(arr, float(positive.min()) * 1e-3))
    t = _otsu_threshold(log_arr)
    dark = arr[log_arr < t]
    bright = arr[log_arr >= t]
    if dark.size == 0 or bright.size == 0:
        return np.ones(arr.shape, dtype=bool)
    bright_reference = float(np.median(bright))
    dark_level = float(np.median(dark))
    if bright_reference <= 0.0 or dark_level > _BORDER_GAP_RATIO * bright_reference:
        # No distinct dark border (fully exposed / anatomy+direct only).
        return np.ones(arr.shape, dtype=bool)
    return arr >= rel_threshold * bright_reference


_MAD_TO_STD = 1.4826  # normal-consistency MAD scaling ([S] statistical constant)


def separate_direct_exposure(
    image: np.ndarray,
    field_mask: np.ndarray,
    *,
    fence_k: float = 3.0,
) -> np.ndarray:
    """Separate direct-exposure (unattenuated) pixels from the anatomy region.

    SWR-901 step 2 (REQ-POST-WINDOW-1): within the collimation field, direct
    exposure (X-rays reaching the detector without passing through anatomy) forms
    a bright upper mode of the histogram that would otherwise drag the VOI. Pixels
    above the robust upper fence ``median + fence_k * (1.4826 * MAD)`` of the
    field's intensity distribution are classified as direct exposure and excluded.

    The MAD-based fence is scale-robust: it removes a distinct bright mode however
    large, yet leaves an unimodal anatomy distribution intact (full-exposure EC-2).
    Returns a boolean anatomy mask (True = attenuated anatomy inside the field).
    When the field is empty the result is all False.
    """
    arr = np.asarray(image, dtype=np.float64)
    field = np.asarray(field_mask, dtype=bool)
    if not field.any():
        return np.zeros(arr.shape, dtype=bool)
    vals = arr[field]
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med)))
    threshold = med + fence_k * _MAD_TO_STD * mad
    return field & (arr < threshold)


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
