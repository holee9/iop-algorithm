"""NPS / NNPS and line-noise spectrum (REQ-METRICS-NPS, measurement protocol §1.3).

Procedure (REQ-METRICS-NPS-1):
    central-region 256x256 ROIs (half-overlap)
        -> detrend
        -> 2D FFT ensemble average (common.fft_psd)
        -> 1D axial extraction (central axes excluded).
NNPS normalizes NPS by the large-signal squared (REQ-METRICS-NPS-2).

@MX:ANCHOR: [AUTO] `compute_nps` is the NPS-group public entry point consumed by
metrics.dqe and the acceptance suite.
@MX:REASON: DQE(f) = MTF^2 q Ka / NPS(f) depends on this function's NPS
frequency convention and normalization; a change ripples into every DQE value.

All constants arrive through Params (REQ-METRICS-CORE-4). Accuracy is the single
goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common import fft_psd
from common.contract import Params
from common.xframe import XFrame
from metrics.result import MetricCondition, MetricReadError, MetricResult

P_PITCH = "pixel_pitch_mm"
P_ROI_SIZE = "nps_roi_size"  # ROI side (px), IEC default 256 [P]
P_DETREND_ORDER = "nps_detrend_order"  # 2D polynomial detrend order [P]
P_EXCLUDE_AXIS = "nps_exclude_axis_bins"  # central bins excluded per side [P]
P_AVG_LINES = "nps_average_lines"  # off-axis lines averaged per side [P]


def _detrend(roi: np.ndarray, order: int) -> np.ndarray:
    """Subtract a low-order 2D polynomial trend (IEC background removal)."""
    ny, nx = roi.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    yn = yy / ny
    xn = xx / nx
    terms = [np.ones_like(xn)]
    for i in range(1, order + 1):
        terms.append(xn**i)
        terms.append(yn**i)
    design = np.stack([t.ravel() for t in terms], axis=1)
    coef, *_ = np.linalg.lstsq(design, roi.ravel(), rcond=None)
    fit = (design @ coef).reshape(ny, nx)
    return roi - fit


def _central_rois(image: np.ndarray, roi_size: int) -> list[tuple[tuple[int, int, int, int], np.ndarray]]:
    """Half-overlap tiling of the central region into square ROIs."""
    ny, nx = image.shape
    if roi_size > ny or roi_size > nx:
        raise MetricReadError(
            f"NPS: 256x256 ROI ({roi_size}) exceeds frame {ny}x{nx} "
            "(ROI leaves the frame boundary)"
        )
    stride = roi_size // 2  # half-overlap
    rois: list[tuple[tuple[int, int, int, int], np.ndarray]] = []
    for top in range(0, ny - roi_size + 1, stride):
        for left in range(0, nx - roi_size + 1, stride):
            rois.append(((top, left, roi_size, roi_size), image[top : top + roi_size, left : left + roi_size]))
    return rois


def compute_nps(
    frames: list[XFrame],
    params: Params,
    *,
    calibset_id: str | None = None,
    dose_level: str | None = None,
) -> MetricResult:
    """Compute NPS and NNPS from a stack of uniform frames.

    Args:
        frames: uniform-exposure XFrames (consumed read-only).
        params: externalized constants (pitch, ROI size, detrend order).
        calibset_id: id of the consumed CalibSet (metadata).
        dose_level: dose-level tag for the result metadata (e.g. "XN").

    Raises:
        MetricReadError: no valid uniform ROI can be extracted (NPS-6 / EC-2).
    """
    if not frames:
        raise MetricReadError("NPS: no input frames")
    pitch = float(params.get(P_PITCH))
    roi_size = int(params.get(P_ROI_SIZE))
    order = int(params.get(P_DETREND_ORDER))
    exclude = int(params.get(P_EXCLUDE_AXIS))
    avg_lines = int(params.get(P_AVG_LINES))
    pixel_area = pitch * pitch

    detrended: list[np.ndarray] = []
    roi_means: list[float] = []
    for frame in frames:
        image = np.asarray(frame.pixel, dtype=np.float64)
        for _extent, roi in _central_rois(image, roi_size):
            roi_means.append(float(roi.mean()))
            detrended.append(_detrend(roi, order))
    if not detrended:
        raise MetricReadError("NPS: insufficient uniform region for any ROI")

    mean_signal = float(np.mean(roi_means))
    nps2d = fft_psd.nps_2d(np.stack(detrended), pixel_area)
    freq, nps1d = fft_psd.axial_1d_nps(
        nps2d, pitch, exclude_axis_bins=exclude, n_average_lines=avg_lines
    )
    nnps1d = nps1d / (mean_signal**2) if mean_signal != 0 else np.full_like(nps1d, np.nan)

    condition = MetricCondition(
        correction_state="raw",
        roi=(0, 0, roi_size, roi_size),
        params_hash=params.hash(),
        calibset_id=calibset_id,
        dose_level=dose_level,
        beam_quality=params.get("beam_quality"),
        added_filter=params.get("added_filter"),
        temperature_c=params.get("temperature_c"),
    )
    return MetricResult(
        name="NPS",
        values={
            "frequencies_lpmm": freq,
            "nps": nps1d,
            "nnps": nnps1d,
            "nps_2d": nps2d,
            "mean_signal": mean_signal,
            "n_roi": len(detrended),
        },
        condition=condition,
    )


def detect_line_noise(
    frames: list[XFrame],
    params: Params,
    *,
    calibset_id: str | None = None,
) -> MetricResult:
    """Quantify row/column low-frequency line-noise peaks (REQ-METRICS-NPS-8).

    Averages each uniform frame along rows and columns to form 1D profiles,
    computes their (mean-removed) 1D power spectra, and reports the dominant
    low-frequency anomalous peak in each direction. Optional: only invoked when
    line-noise quantification is requested (Scenario 10).
    """
    if not frames:
        raise MetricReadError("line-noise: no input frames")
    pitch = float(params.get(P_PITCH))

    col_spectra = []
    row_spectra = []
    for frame in frames:
        image = np.asarray(frame.pixel, dtype=np.float64)
        col_profile = image.mean(axis=0)  # one value per column -> vertical lines
        row_profile = image.mean(axis=1)  # one value per row -> horizontal lines
        col_spectra.append(np.abs(np.fft.rfft(col_profile - col_profile.mean())) ** 2)
        row_spectra.append(np.abs(np.fft.rfft(row_profile - row_profile.mean())) ** 2)
    col_ps = np.mean(col_spectra, axis=0)
    row_ps = np.mean(row_spectra, axis=0)
    ny, nx = np.asarray(frames[0].pixel).shape
    col_freq = np.fft.rfftfreq(nx, d=pitch)
    row_freq = np.fft.rfftfreq(ny, d=pitch)

    def _peak(ps: np.ndarray, freq: np.ndarray) -> dict:
        # Skip DC; the anomalous peak is the maximum of the remaining spectrum.
        k = int(np.argmax(ps[1:])) + 1
        return {"peak_freq_lpmm": float(freq[k]), "peak_power": float(ps[k])}

    return MetricResult(
        name="line_noise",
        values={
            "column_peak": _peak(col_ps, col_freq),
            "row_peak": _peak(row_ps, row_freq),
            "column_spectrum": col_ps,
            "row_spectrum": row_ps,
        },
        condition=MetricCondition(params_hash=params.hash(), calibset_id=calibset_id),
    )
