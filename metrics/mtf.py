"""MTF via the edge method (REQ-METRICS-MTF, measurement protocol §1.2).

Pipeline (fully scripted, no human reading — REQ-METRICS-MTF-1):
    automatic edge-angle estimation
        -> oversampled ESF
        -> LSF (differentiate + window)
        -> FFT
        -> presampled MTF.

@MX:ANCHOR: [AUTO] `compute_mtf` is the MTF-group public entry point consumed by
metrics.dqe and the acceptance suite.
@MX:REASON: DQE composition and every MTF acceptance scenario depend on this
function's presampled-MTF contract and frequency convention (lp/mm).

All thresholds/constants arrive through Params (REQ-METRICS-CORE-4); none are
hardcoded. Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.contract import Params
from common.xframe import XFrame
from metrics.result import MetricCondition, MetricReadError, MetricResult

# Param keys (defaults documented by callers, never baked in as gate literals).
P_PITCH = "pixel_pitch_mm"  # panel pitch (mm); Nyquist = 1/(2*pitch)
P_OVERSAMPLE = "mtf_oversample"  # ESF oversampling factor [P]
P_ANGLE_MIN = "mtf_angle_min_deg"  # permitted edge-angle range low  [T]/[P]
P_ANGLE_MAX = "mtf_angle_max_deg"  # permitted edge-angle range high [T]/[P]
P_ANGLE_MARGIN = "mtf_angle_margin_deg"  # boundary-proximity warning margin [T]


def _condition(params: Params, calibset_id: str | None, roi, direction: str) -> MetricCondition:
    return MetricCondition(
        correction_state="raw",
        roi=roi,
        params_hash=params.hash(),
        calibset_id=calibset_id,
        added_filter=params.get("added_filter"),
        beam_quality=params.get("beam_quality"),
        dose_level=params.get("dose_level"),
        temperature_c=params.get("temperature_c"),
    )


def estimate_edge_angle(image: np.ndarray) -> tuple[float, float, float]:
    """Estimate the near-vertical edge angle (deg), slope and intercept.

    For each row the sub-pixel edge location is the centroid of the horizontal
    gradient magnitude; a linear fit of location vs row gives the slope, whose
    arctangent is the tilt of the edge relative to the pixel grid.
    """
    arr = np.asarray(image, dtype=np.float64)
    ny, nx = arr.shape
    grad = np.abs(np.diff(arr, axis=1))  # (ny, nx-1)
    xpos = np.arange(nx - 1, dtype=np.float64) + 0.5
    rows = []
    centroids = []
    for y in range(ny):
        w = grad[y]
        s = w.sum()
        if s <= 0:
            continue
        rows.append(y)
        centroids.append(float((xpos * w).sum() / s))
    if len(rows) < 2:
        raise MetricReadError("MTF: edge not detectable (no gradient signal)")
    slope, intercept = np.polyfit(np.asarray(rows), np.asarray(centroids), 1)
    angle_deg = abs(np.degrees(np.arctan(slope)))
    return float(angle_deg), float(slope), float(intercept)


def _oversampled_esf(
    image: np.ndarray, slope: float, intercept: float, oversample: int
) -> np.ndarray:
    """Project pixels onto the edge-normal axis and bin into a super-sampled ESF."""
    arr = np.asarray(image, dtype=np.float64)
    ny, nx = arr.shape
    ys, xs = np.mgrid[0:ny, 0:nx]
    angle = np.arctan(slope)
    # Signed perpendicular distance (in pixels) from each pixel to the edge line
    # x = slope*y + intercept.
    horiz = xs - (slope * ys + intercept)
    dist = horiz * np.cos(angle)
    bin_idx = np.round(dist.ravel() * oversample).astype(np.int64)
    bin_idx -= bin_idx.min()
    n_bins = int(bin_idx.max()) + 1
    acc = np.zeros(n_bins, dtype=np.float64)
    cnt = np.zeros(n_bins, dtype=np.float64)
    np.add.at(acc, bin_idx, arr.ravel())
    np.add.at(cnt, bin_idx, 1.0)
    valid = cnt > 0
    esf = np.zeros(n_bins, dtype=np.float64)
    esf[valid] = acc[valid] / cnt[valid]
    # Fill any empty bins by interpolation to keep a regular grid.
    if not valid.all():
        idx = np.arange(n_bins)
        esf = np.interp(idx, idx[valid], esf[valid])
    return esf


def _presampled_mtf(
    esf: np.ndarray, oversample: int, pitch_mm: float
) -> tuple[np.ndarray, np.ndarray]:
    """LSF (differentiate + Hann window) -> FFT -> normalized presampled MTF.

    Returns (freq_lpmm, mtf) over the non-negative frequency half-axis.
    """
    lsf = np.gradient(esf)
    # Window the LSF (measurement protocol §1.2: differentiate + window) to
    # suppress truncation tails before the transform.
    window = np.hanning(lsf.size)
    lsf = lsf * window
    n = lsf.size
    spectrum = np.abs(np.fft.rfft(lsf))
    mtf = spectrum / spectrum[0]
    # Sample spacing of the ESF is 1/oversample pixels -> cycles/pixel axis.
    freq_cyc_px = np.fft.rfftfreq(n, d=1.0 / oversample)
    freq_lpmm = freq_cyc_px / pitch_mm
    return freq_lpmm, mtf


def compute_mtf(
    frame: XFrame,
    params: Params,
    *,
    calibset_id: str | None = None,
    direction: str = "vertical",
) -> MetricResult:
    """Compute the presampled MTF of an edge-slab ROI (REQ-METRICS-MTF-1..4).

    Args:
        frame: XFrame whose pixels contain the edge ROI (consumed read-only).
        params: externalized constants (pitch, oversample, angle range/margin).
        calibset_id: id of the consumed CalibSet (metadata).
        direction: "vertical" (default) or "horizontal"; horizontal transposes
            the ROI so the same near-vertical estimator applies (MTF-5).

    Raises:
        MetricReadError: edge angle outside the permitted range (MTF-3).
    """
    image = np.asarray(frame.pixel, dtype=np.float64)
    if direction == "horizontal":
        image = image.T
    elif direction != "vertical":
        raise ValueError("direction must be 'vertical' or 'horizontal'")

    pitch = float(params.get(P_PITCH))
    oversample = int(params.get(P_OVERSAMPLE))
    angle_min = float(params.get(P_ANGLE_MIN))
    angle_max = float(params.get(P_ANGLE_MAX))
    margin = float(params.get(P_ANGLE_MARGIN))

    angle_deg, slope, intercept = estimate_edge_angle(image)

    # REQ-METRICS-MTF-3 deterministic branch: out-of-range = reject (error),
    # inside-but-near-boundary (within margin) = compute + warn.
    if angle_deg < angle_min or angle_deg > angle_max:
        raise MetricReadError(
            f"MTF: edge angle {angle_deg:.3f} deg outside permitted range "
            f"[{angle_min}, {angle_max}] (0/90-deg undersampling or misalignment)"
        )
    warnings: list[str] = []
    if (angle_deg - angle_min) < margin or (angle_max - angle_deg) < margin:
        warnings.append(
            f"MTF: edge angle {angle_deg:.3f} deg within {margin} deg of the "
            f"permitted-range boundary [{angle_min}, {angle_max}]"
        )

    esf = _oversampled_esf(image, slope, intercept, oversample)
    freq_lpmm, mtf = _presampled_mtf(esf, oversample, pitch)

    nyquist = 1.0 / (2.0 * pitch)
    mtf_at_nyquist = float(np.interp(nyquist, freq_lpmm, mtf))

    ny, nx = np.asarray(frame.pixel).shape
    roi = (0, 0, ny, nx)
    return MetricResult(
        name="MTF",
        values={
            "frequencies_lpmm": freq_lpmm,
            "mtf": mtf,
            "edge_angle_deg": angle_deg,
            "nyquist_lpmm": nyquist,
            "mtf_at_nyquist": mtf_at_nyquist,
            "direction": direction,
        },
        condition=_condition(params, calibset_id, roi, direction),
        warnings=tuple(warnings),
    )


def mtf_value_at(result: MetricResult, freq_lpmm: float) -> float:
    """Interpolate the presampled MTF at an arbitrary frequency (lp/mm)."""
    freqs = result.get("frequencies_lpmm")
    mtf = result.get("mtf")
    return float(np.interp(freq_lpmm, freqs, mtf))
