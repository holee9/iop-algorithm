"""Line-noise correction (SWR-501~504, FR-C007).

Two deterministic, mutually exclusive paths selected by CalibSet(LINE_NOISE)
content (spec decision 1):

- REQ-LNSG-LINE-1 (P1 priority, reference-absent, SWR-503): row/column low-
  frequency profile subtraction with high-pass limiting. Per-row (and per-column)
  robust means form 1D profiles; a low-order median filter (window length [T])
  robustifies them and a Gaussian low-pass (cutoff [T]) estimates the protected
  anatomical low-frequency baseline. Only the HIGH-PASS residual (profile minus
  baseline) is subtracted, so slow anatomical gradients are preserved while
  row/column banding is removed.
- REQ-LNSG-LINE-2 (Optional, reference-provided, SWR-501/502): reference-region
  row-median subtraction with k*MAD contamination exclusion (k default 6). Rows
  whose reference median deviates > k*MAD from the global median are treated as
  contaminated (metal structure / direct-beam) and replaced by adjacent-row
  interpolation before subtraction.

REQ-LNSG-LINE-3: robust statistics exclude DEFECT / INTERPOLATION / SATURATION
pixels; the XFrame noise model (alpha, sigma) is never re-estimated (SWR-701/T5).

@MX:ANCHOR: [AUTO] `process` is the line_noise pipeline stage entry point invoked
via the orchestrator registry (REQ-LNSG-CONTRACT-1/6).
@MX:REASON: fan_in is the orchestrator registry plus the harness and the
XDET-TC-006/007 release gates; the path-selection contract and the high-pass
limiting are what the detect_line_noise before/after judgment reads against.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import HistoryEntry, MaskFlag, XFrame

MODULE_NAME = "line_noise"
MODULE_VERSION = "1.0.0"

# CalibSet(LINE_NOISE) data payload keys.
K_REFERENCE = "reference_region"  # Optional bool mask of non-irradiated ref pixels

# Params keys.
P_WINDOW = "line_noise_profile_window"  # median-filter window length [T] (SWR-503)
P_CUTOFF = "line_noise_highpass_cutoff"  # high-pass cutoff, cycles/sample [T]
P_CONTAM_K = "line_noise_contam_k"  # k*MAD contamination exclusion (SWR-502, def 6)

# Mask bits excluded from robust profile statistics (REQ-LNSG-LINE-3).
_EXCLUDE = np.uint8(MaskFlag.DEFECT | MaskFlag.INTERPOLATION | MaskFlag.SATURATION)


def _require(params: Params, key: str) -> float:
    value = params.get(key)
    if value is None:
        raise ValueError(f"line_noise: missing required parameter '{key}'")
    return float(value)


def _masked(image: np.ndarray, exclude: np.ndarray) -> np.ndarray:
    """Return `image` with excluded pixels set to NaN (dropped from medians)."""
    out = image.copy()
    out[exclude] = np.nan
    return out


def _axis_profile(masked: np.ndarray, axis: int) -> np.ndarray:
    """Robust 1D profile: median along `axis`, ignoring NaN (masked) pixels.

    axis=1 -> per-row profile (length ny), axis=0 -> per-column (length nx).
    Fully-masked lines yield NaN and are handled by the caller (zero correction).
    """
    with np.errstate(invalid="ignore"):
        return np.nanmedian(masked, axis=axis)


def _highpass_correction(
    profile: np.ndarray, window: int, cutoff: float
) -> np.ndarray:
    """SWR-503 high-pass limited correction for a 1D profile.

    profile -> median_filter(window) robustification (removes impulsive per-line
    outliers) -> FFT low-pass baseline (frequencies below `cutoff` cycles/sample
    = the protected anatomical low-frequency trend, incl. DC) -> correction =
    robust - baseline. Only the high-pass component (line-to-line banding above
    the cutoff) is subtracted, so genuine slow anatomical gradients are
    preserved. NaN (fully-masked) entries contribute zero correction.

    The FFT low-pass keeps the sharp separation exact for band-limited line
    noise; a real (non-periodic) profile incurs the standard mild wrap seam,
    accepted for the P1 golden model (accuracy over speed).
    """
    finite = np.isfinite(profile)
    if not finite.any():
        return np.zeros_like(profile)
    filled = np.where(finite, profile, float(np.median(profile[finite])))
    win = max(1, int(window))
    if win % 2 == 0:  # median_filter needs an odd footprint for a symmetric window
        win += 1
    robust = median_filter(filled, size=win, mode="reflect")
    n = robust.size
    spectrum = np.fft.rfft(robust)
    freq = np.fft.rfftfreq(n)  # cycles/sample
    baseline = np.fft.irfft(spectrum * (freq < float(cutoff)), n)
    correction = robust - baseline
    correction[~finite] = 0.0
    return correction


def _correct_no_reference(
    image: np.ndarray, exclude: np.ndarray, window: int, cutoff: float
) -> tuple[np.ndarray, dict[str, float]]:
    """REQ-LNSG-LINE-1 (SWR-503): subtract high-pass row AND column corrections."""
    masked = _masked(image, exclude)
    row_corr = _highpass_correction(_axis_profile(masked, axis=1), window, cutoff)
    col_corr = _highpass_correction(_axis_profile(masked, axis=0), window, cutoff)
    out = image - row_corr[:, None] - col_corr[None, :]
    diag = {
        "path": "no_reference",
        "row_corr_max": float(np.max(np.abs(row_corr))),
        "col_corr_max": float(np.max(np.abs(col_corr))),
    }
    return out, diag


def _interp_contaminated(m: np.ndarray, contaminated: np.ndarray) -> np.ndarray:
    """Replace contaminated row-reference medians by adjacent-row linear interp."""
    out = m.copy()
    idx = np.arange(m.size)
    good = ~contaminated & np.isfinite(m)
    if good.sum() >= 2:
        out[contaminated] = np.interp(idx[contaminated], idx[good], m[good])
    elif good.sum() == 1:
        out[contaminated] = m[good][0]
    else:  # pragma: no cover - degenerate all-contaminated reference
        out[contaminated] = 0.0
    return out


def _correct_reference(
    image: np.ndarray, exclude: np.ndarray, reference: np.ndarray, k: float
) -> tuple[np.ndarray, dict[str, float]]:
    """REQ-LNSG-LINE-2 (SWR-501/502): reference-row median subtraction with
    k*MAD contamination exclusion."""
    ref_valid = reference & ~exclude
    masked = np.where(ref_valid, image, np.nan)
    with np.errstate(invalid="ignore"):
        m = np.nanmedian(masked, axis=1)  # per-row reference median m(r)
    finite = np.isfinite(m)
    med = float(np.median(m[finite])) if finite.any() else 0.0
    mad = float(np.median(np.abs(m[finite] - med))) if finite.any() else 0.0
    contaminated = (~finite) | (np.abs(m - med) > k * mad if mad > 0 else ~finite)
    m_clean = _interp_contaminated(np.where(finite, m, np.nan), contaminated)
    out = image - m_clean[:, None]
    diag = {
        "path": "reference",
        "contaminated_rows": float(np.count_nonzero(contaminated)),
        "ref_mad": mad,
    }
    return out, diag


def _has_reference(calib: CalibSet, shape: tuple[int, ...]) -> np.ndarray | None:
    """Return the reference-region bool mask when the CalibSet supplies a non-
    empty one, else None (deterministic path selection, spec decision 1)."""
    if K_REFERENCE not in calib.data:
        return None
    ref = np.asarray(calib.data[K_REFERENCE]).astype(bool)
    if ref.shape != shape:
        raise ValueError(
            f"line_noise: reference_region shape {ref.shape} != frame {shape}"
        )
    if not ref.any():
        return None
    return ref


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Correct row/column line noise; select path by CalibSet content.

    Returns a new XFrame; the input frame is treated as immutable (DATA-6). The
    noise model is preserved unchanged (REQ-LNSG-LINE-3).
    """
    window = _require(params, P_WINDOW)
    cutoff = _require(params, P_CUTOFF)
    exclude = (np.asarray(frame.masks, dtype=np.uint8) & _EXCLUDE) != 0
    reference = _has_reference(calib, frame.shape)

    def _apply(img: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
        if reference is not None:
            k = _require(params, P_CONTAM_K)
            return _correct_reference(img, exclude, reference, k)
        return _correct_no_reference(img, exclude, int(window), cutoff)

    out_f64_full, diag = _apply(np.asarray(frame.pixel, dtype=np.float64))
    out_pixel = out_f64_full.astype(frame.pixel.dtype)

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64, _ = _apply(np.asarray(frame.pixel_f64, dtype=np.float64))

    new = frame.with_pixel(out_pixel, out_f64)
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra=diag,
    )
    return new.record_history(entry)
