"""Grid line suppression (SWR-1001~1006, FR-M006/M007, T7/WP8).

Stateless, pure-functional suppression of the periodic modulation a physical
anti-scatter grid imprints on the frame. The design premise is ALIASING
(SWR-1001): commercial grid densities (30~85 lines/cm = 3.0~8.5 lp/mm) mostly
exceed the panel Nyquist f_N = 1/(2*pitch) = 3.571 lp/mm, so an f_grid > f_N grid
folds to an observed alias f_a = |f_grid - k*f_s| (f_s = 1/pitch). The notch
target is therefore derived ONLY from the OBSERVED spectrum peak — never from a
nominal grid frequency or the (optional) mount metadata ([HARD] SWR-1001,
REQ-GRID-SEARCH-4). There is a single deterministic path; no nominal-frequency
branch exists.

Five steps (SWR-1001~1006):
  (1) direction estimation: compare the row-averaged (x) and column-averaged (y)
      1D Welch PSD narrowband energy; the axis carrying the dominant narrowband
      peak (by >= direction margin dB) is the grid direction. Ambiguous
      (crossed/diagonal, below margin) -> no confident direction -> passthrough.
  (2) observed-spectrum peak search on that axis: within [lo, f_N], local maxima
      whose significance vs the local background is >= D_th dB are accepted;
      folded harmonics (fold(k*f_a)) that clear D_th are added.
  (3) 1D Gaussian notch per detected peak on the grid-ORTHOGONAL frequency axis
      only (vertical grid -> horizontal frequency axis), bandwidth = peak FWHM x
      notch_fwhm_mult. A 2D isotropic notch is PROHIBITED (REQ-GRID-NOTCH-2,
      anatomy loss).
  (4) low-frequency fold (< moire cutoff): cap the attenuation and record a
      grid-replacement quality warning (SWR-1004).
  (5) no significant peak (or ambiguous direction): numerically-identical
      passthrough + a "grid undetected" diagnostic (SWR-1005, FR-M007). No notch
      or pixel change happens without a detected peak (no unauthorized
      suppression).

Spectral estimation consumes common.fft_psd (SWR-000-9 shared FFT/PSD); FFT/PSD
is not re-implemented here. All thresholds arrive via Params (no hardcoding);
f_N and f_s are derived from the Params pitch. The mask substrate is never
mutated and saturated pixels are never "restored" (SWR-602 precedent). The
module consumes CalibSet(OTHER) only for the entry gate (no detector
calibration).

@MX:ANCHOR: [AUTO] `process` is the grid pipeline stage entry point invoked via
the orchestrator registry (REQ-GRID-CONTRACT-1/5).
@MX:REASON: fan_in is the orchestrator registry plus the harness and the
XDET-TC-015/016 release gates; the observed-spectrum-only search and the 1D-notch
contract are what those gates read against.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import median_filter

from common.calibset import CalibSet
from common.contract import Params
from common.fft_psd import axial_welch_psd
from common.xframe import HistoryEntry, XFrame

MODULE_NAME = "grid"
MODULE_VERSION = "1.0.0"

# -- Params keys (all externalized; grades per SWR appendix A) ------------------
P_PITCH = "grid_pitch_mm"  # panel pitch (mm); f_N, f_s DERIVED from this
P_SEARCH_LO = "grid_search_band_lo_lpmm"  # search band lower edge (0.3) [ungraded]
P_DTH_DB = "grid_peak_significance_db"  # peak significance D_th [T]
P_DIR_MARGIN_DB = "grid_direction_margin_db"  # row/col decision margin [T]
P_HARMONIC_MAX = "grid_harmonic_max_order"  # folded-harmonic max order [T]
P_NOTCH_FWHM_MULT = "grid_notch_fwhm_mult"  # notch bw = peak FWHM x mult [T]
P_MOIRE_CUTOFF = "grid_moire_lowfreq_cutoff_lpmm"  # low-freq fold cutoff (0.5) [ungraded]
P_MOIRE_ATTEN_CAP = "grid_moire_atten_cap"  # attenuation cap under the moire band [T]
P_BG_WINDOW_BINS = "grid_bg_window_bins"  # local-background rolling-median width [T]
# Optional acquisition-context metadata (SWR-1005). Consumed ONLY for the
# comparison warning; NEVER fed into peak-position search (SWR-1001 [HARD]).
P_META_MOUNTED = "grid_meta_mounted"  # bool: grid mounted per acquisition metadata
P_META_NOMINAL = "grid_meta_nominal_lpmm"  # nominal density (comparison only)

_META_TOL_LPMM = 0.25  # observed-vs-metadata agreement tolerance (warning only)
_2SQRT2LN2 = 2.0 * np.sqrt(2.0 * np.log(2.0))  # FWHM -> Gaussian sigma factor


class GridError(ValueError):
    """Raised on a missing required parameter."""


def _require(params: Params, key: str, cast=float):
    value = params.get(key)
    if value is None:
        raise GridError(f"grid: missing required parameter '{key}'")
    return cast(value)


@dataclass(frozen=True)
class Peak:
    """One detected spectral peak, in OBSERVED-spectrum coordinates."""

    freq_lpmm: float
    significance_db: float
    fwhm_lpmm: float


@dataclass(frozen=True)
class GridAnalysis:
    """Result of the observed-spectrum analysis (pure; consumed by process + tests)."""

    detected: bool
    direction: str  # "vertical" | "horizontal" | "none"
    energy_ratio_db: float
    peaks: tuple[Peak, ...]


def _fold(f: float, f_s: float, f_nyq: float) -> float:
    """Alias a frequency into [0, f_N] exactly as integer sampling does."""
    r = float(f) % f_s
    return r if r <= f_nyq else f_s - r


def _fwhm(freq: np.ndarray, psd: np.ndarray, i: int, bg: float) -> float:
    """Full width at half maximum (above background) around the peak bin i."""
    half = bg + 0.5 * (psd[i] - bg)
    lo = i
    while lo > 0 and psd[lo - 1] > half:
        lo -= 1
    hi = i
    n = psd.size
    while hi < n - 1 and psd[hi + 1] > half:
        hi += 1
    df = float(freq[1] - freq[0]) if freq.size > 1 else 0.0
    width = float(freq[hi] - freq[lo])
    return width if width > 0.0 else max(df, 1e-9)


def _find_peaks(
    freq: np.ndarray,
    psd: np.ndarray,
    lo: float,
    f_nyq: float,
    d_th: float,
    max_peaks: int,
    bg_window: int,
) -> tuple[list[Peak], float]:
    """Return (peaks, best_significance_db) for local maxima clearing D_th.

    Significance is 10*log10(psd / LOCAL background) (SWR-1002 "국소 배경 대비").
    The local background is a rolling median over `bg_window` bins: it tracks a
    sloped baseline (e.g. the decaying spectrum of a strong edge) so a narrowband
    grid peak still stands out, while a window several times wider than a peak is
    unperturbed by the peak itself.
    """
    band = (freq >= lo) & (freq <= f_nyq)
    if not np.any(band):
        return [], 0.0
    win = max(3, int(bg_window) | 1)  # odd, >= 3
    # `mirror` (reflect excluding the edge sample) keeps the rolling-median
    # background from replicating a peak that sits ON the Nyquist edge into its own
    # background window -- with edge replication a grid peak at exactly f_N inflates
    # its own background and its significance collapses to 0 (never detected).
    bg = median_filter(psd, size=win, mode="mirror")
    floor = max(float(np.median(psd[band])) * 1e-6, 1e-30)
    bg = np.maximum(bg, floor)
    sig = 10.0 * np.log10(np.maximum(psd, 1e-30) / bg)

    n = psd.size
    last = n - 1
    idx = np.nonzero(band)[0]
    candidates: list[Peak] = []
    for i in idx:
        if i <= 0:
            continue
        if i >= last:
            # The Nyquist (last) bin has no right neighbour; treat it as a local
            # maximum when it strictly exceeds its single left neighbour so a grid
            # peak landing exactly at Nyquist is not silently dropped.
            is_local_max = psd[i] > psd[i - 1]
        else:
            is_local_max = psd[i] > psd[i - 1] and psd[i] >= psd[i + 1]
        if is_local_max and sig[i] >= d_th:
            candidates.append(
                Peak(float(freq[i]), float(sig[i]), _fwhm(freq, psd, i, float(bg[i])))
            )

    df = float(freq[1] - freq[0]) if freq.size > 1 else 0.0
    min_sep = 2.5 * df

    # Explicit folded-harmonic candidates (SWR-1002 / EC-3): for each detected
    # fundamental and k = 2..max_order, the folded harmonic fold(k*f) can land on
    # the shoulder of a stronger neighbouring bin -- elevated above the local
    # background yet not a strict local maximum, so the search above misses it.
    # Check fold(k*f) significance directly against D_th and add it as a candidate
    # when it clears the threshold (not requiring a local maximum).
    if candidates:
        f_s = 2.0 * f_nyq
        existing = [c.freq_lpmm for c in candidates]
        base_freqs = [c.freq_lpmm for c in candidates]
        for f0 in base_freqs:
            for k in range(2, max(2, int(max_peaks)) + 1):
                f_h = _fold(k * f0, f_s, f_nyq)
                if f_h < lo or f_h > f_nyq:
                    continue
                j = int(np.argmin(np.abs(freq - f_h)))
                if not band[j] or sig[j] < d_th:
                    continue
                if any(abs(freq[j] - e) <= min_sep for e in existing):
                    continue
                candidates.append(
                    Peak(float(freq[j]), float(sig[j]), _fwhm(freq, psd, j, float(bg[j])))
                )
                existing.append(float(freq[j]))

    if not candidates:
        return [], float(np.max(sig[band]))

    # Greedy dedupe: sort by significance, keep peaks separated by > ~2 bins so a
    # single broad peak is not double-counted; cap at max_peaks (SWR-1002
    # harmonic max order bounds the reported set).
    candidates.sort(key=lambda p: p.significance_db, reverse=True)
    kept: list[Peak] = []
    for cand in candidates:
        if all(abs(cand.freq_lpmm - k.freq_lpmm) > min_sep for k in kept):
            kept.append(cand)
        if len(kept) >= max(1, max_peaks):
            break
    best_sig = kept[0].significance_db if kept else float(np.max(sig[band]))
    return kept, best_sig


def analyze(image, params: Params) -> GridAnalysis:
    """Estimate grid direction and detect observed-spectrum peaks (pure).

    Accepts an XFrame or a 2D array. Consumes common.fft_psd for the axial Welch
    PSD (SWR-000-9). Never consumes a nominal frequency or metadata.
    """
    arr = np.asarray(getattr(image, "pixel", image), dtype=np.float64)
    pitch = _require(params, P_PITCH, float)
    lo = _require(params, P_SEARCH_LO, float)
    d_th = _require(params, P_DTH_DB, float)
    margin = _require(params, P_DIR_MARGIN_DB, float)
    max_order = _require(params, P_HARMONIC_MAX, int)
    bg_window = int(params.get(P_BG_WINDOW_BINS, 11))
    f_nyq = 1.0 / (2.0 * pitch)

    # axis=1 scans x (vertical grid, periodic along columns); axis=0 scans y.
    freq_x, psd_x = axial_welch_psd(arr, axis=1, pitch_mm=pitch)
    freq_y, psd_y = axial_welch_psd(arr, axis=0, pitch_mm=pitch)
    peaks_x, sig_x = _find_peaks(freq_x, psd_x, lo, f_nyq, d_th, max_order, bg_window)
    peaks_y, sig_y = _find_peaks(freq_y, psd_y, lo, f_nyq, d_th, max_order, bg_window)

    # Direction selection compares ONLY axes where a peak was actually found. A
    # peakless axis reports its in-band noise-floor maximum as its "significance";
    # that noise floor must never outrank a genuine peak on the other axis.
    if peaks_x and peaks_y:
        # Both axes carry real peaks -> crossed/diagonal ambiguity. Pick the
        # stronger axis, but require it to lead the other by the direction margin
        # (ambiguous grids fall through to passthrough, EC-2).
        if sig_x >= sig_y:
            direction, peaks, best, other = "vertical", peaks_x, sig_x, sig_y
        else:
            direction, peaks, best, other = "horizontal", peaks_y, sig_y, sig_x
        energy_ratio_db = float(best - other)
        detected = best >= d_th and energy_ratio_db >= margin
    elif peaks_x or peaks_y:
        # Only one axis has a real peak -> unambiguous grid direction; the
        # peakless axis's noise floor is not a competing peak.
        if peaks_x:
            direction, peaks, best, other = "vertical", peaks_x, sig_x, sig_y
        else:
            direction, peaks, best, other = "horizontal", peaks_y, sig_y, sig_x
        energy_ratio_db = float(best - other)
        detected = best >= d_th
    else:
        # Neither axis has a peak -> no detection.
        return GridAnalysis(False, "none", 0.0, ())

    if not detected:
        return GridAnalysis(False, "none", energy_ratio_db, ())
    return GridAnalysis(True, direction, energy_ratio_db, tuple(peaks))


def _gaussian_notch_gain(
    f: np.ndarray,
    peaks: tuple[Peak, ...],
    fwhm_mult: float,
    moire_cutoff: float,
    atten_cap: float,
) -> tuple[np.ndarray, bool]:
    """Single source of truth for the multiplicative Gaussian notch gain.

    Each peak contributes a Gaussian notch summing TWO terms at +/-f_peak (the
    real-signal spectral symmetry the applied notch requires). Peaks folding below
    the moire cutoff have their attenuation capped (SWR-1004). Returns
    (gain, capped). Both the analytic proxy `notch_gain_1d` and the applied notch
    `_notch_axis_gain` delegate here so the two can never diverge (EV-102 gate).
    """
    f = np.asarray(f, dtype=np.float64)
    gain = np.ones_like(f)
    capped = False
    for pk in peaks:
        atten = 1.0
        if pk.freq_lpmm < moire_cutoff:
            atten = min(1.0, atten_cap)
            capped = True
        sigma = max(pk.fwhm_lpmm * fwhm_mult, 1e-6) / _2SQRT2LN2
        notch = atten * (
            np.exp(-((f - pk.freq_lpmm) ** 2) / (2.0 * sigma * sigma))
            + np.exp(-((f + pk.freq_lpmm) ** 2) / (2.0 * sigma * sigma))
        )
        gain = gain * (1.0 - np.minimum(notch, atten))
    return gain, capped


def notch_gain_1d(
    freqs_lpmm,
    peaks: tuple[Peak, ...],
    params: Params,
) -> np.ndarray:
    """The 1D notch transfer function |H(f)| at the given frequencies.

    For a linear notch the post-suppression MTF along the grid-orthogonal axis is
    MTF_after(f) = MTF_before(f) * |H(f)|, so |H(Nyquist)| IS the exact MTF@Nyquist
    retention the notch imposes -- free of the Gibbs-ringing artifact a slanted-
    edge re-estimation of a notched hard edge would introduce (EV-102 guardrail,
    REQ-GRID-VALIDATE-2). Consumed by tests alongside metrics.mtf for the baseline.

    Delegates to `_gaussian_notch_gain` so this proxy is bit-for-bit identical to
    the notch actually applied in `_notch_axis_gain` (both sum the +/-f_peak mirror
    terms); a single-term approximation would under-report the attenuation a
    low-frequency wide-bandwidth peak imposes at +Nyquist.
    """
    fwhm_mult = _require(params, P_NOTCH_FWHM_MULT, float)
    moire_cutoff = _require(params, P_MOIRE_CUTOFF, float)
    atten_cap = _require(params, P_MOIRE_ATTEN_CAP, float)
    gain, _ = _gaussian_notch_gain(
        np.asarray(freqs_lpmm, dtype=np.float64), peaks, fwhm_mult, moire_cutoff, atten_cap
    )
    return gain


def _notch_axis_gain(
    n: int,
    pitch: float,
    peaks: tuple[Peak, ...],
    fwhm_mult: float,
    moire_cutoff: float,
    atten_cap: float,
) -> tuple[np.ndarray, bool]:
    """1D multiplicative notch gain over the full (fftfreq) axis of length n.

    Each peak contributes a Gaussian notch at +/-f_peak. Peaks folding below the
    moire cutoff have their attenuation capped (SWR-1004). Returns (gain, capped).
    """
    f = np.fft.fftfreq(n, d=pitch)
    return _gaussian_notch_gain(f, peaks, fwhm_mult, moire_cutoff, atten_cap)


def _apply_notch(
    image: np.ndarray, direction: str, gain: np.ndarray
) -> np.ndarray:
    """Apply the 1D notch gain along the grid-orthogonal frequency axis only.

    Vertical grid -> notch the horizontal frequency axis (columns / axis 1);
    horizontal grid -> notch the vertical frequency axis (rows / axis 0). The
    gain depends on a SINGLE axis frequency, so the orthogonal (grid-parallel)
    axis is untouched -- this is the 1D notch, not a 2D isotropic one.
    """
    spectrum = np.fft.fft2(np.asarray(image, dtype=np.float64))
    if direction == "vertical":
        spectrum *= gain[None, :]  # gain indexed by fx (columns)
    else:
        spectrum *= gain[:, None]  # gain indexed by fy (rows)
    return np.real(np.fft.ifft2(spectrum))


def _metadata_warning(params: Params, analysis: GridAnalysis, f_s: float, f_nyq: float):
    """Comparison-only mount-metadata check (SWR-1005). Never a search input."""
    mounted = params.get(P_META_MOUNTED)
    nominal = params.get(P_META_NOMINAL)
    if not mounted:
        return None
    if not analysis.detected:
        return "grid mounted per metadata but no grid detected in spectrum"
    if nominal is None:
        return None
    expected = _fold(float(nominal), f_s, f_nyq)
    observed = analysis.peaks[0].freq_lpmm
    if abs(observed - expected) > _META_TOL_LPMM:
        return (
            f"observed grid {observed:.3f} lp/mm disagrees with mounted nominal "
            f"(folded {expected:.3f} lp/mm)"
        )
    return None


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Suppress observed grid-line peaks with a 1D notch; else identity passthrough.

    Returns a new XFrame; the input is treated as immutable (DATA-6). The mask
    substrate and noise model are preserved unchanged. Scalar diagnostics are
    appended to the history chain (`HistoryEntry.extra`).
    """
    pitch = _require(params, P_PITCH, float)
    fwhm_mult = _require(params, P_NOTCH_FWHM_MULT, float)
    moire_cutoff = _require(params, P_MOIRE_CUTOFF, float)
    atten_cap = _require(params, P_MOIRE_ATTEN_CAP, float)
    f_nyq = 1.0 / (2.0 * pitch)
    f_s = 1.0 / pitch

    analysis = analyze(frame, params)
    meta_warning = _metadata_warning(params, analysis, f_s, f_nyq)

    extra: dict[str, str | int | float] = {
        "direction": analysis.direction,
        "direction_energy_ratio_db": float(analysis.energy_ratio_db),
        "n_peaks": int(len(analysis.peaks)),
    }
    if meta_warning is not None:
        extra["metadata_mismatch_warning"] = meta_warning

    if not analysis.detected:
        # SWR-1005 / FR-M007: numerically-identical passthrough, log only. No
        # notch or pixel change happens without a detected peak.
        extra["grid_detected"] = "false"
        extra["grid_undetected"] = "true"
        entry = HistoryEntry(
            module_name=MODULE_NAME,
            module_version=MODULE_VERSION,
            params_hash=params.hash(),
            calibset_id=calib.calibset_id,
            extra=extra,
        )
        return frame.record_history(entry)

    ny, nx = frame.shape
    axis_len = nx if analysis.direction == "vertical" else ny
    gain, capped = _notch_axis_gain(
        axis_len, pitch, analysis.peaks, fwhm_mult, moire_cutoff, atten_cap
    )
    out_pixel = _apply_notch(
        np.asarray(frame.pixel, dtype=np.float64), analysis.direction, gain
    ).astype(frame.pixel.dtype)

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64 = _apply_notch(
            np.asarray(frame.pixel_f64, dtype=np.float64), analysis.direction, gain
        )

    new = frame.with_pixel(out_pixel, out_f64)
    fundamental = analysis.peaks[0]
    total_bw = float(fundamental.fwhm_lpmm * fwhm_mult)
    extra.update(
        {
            "grid_detected": "true",
            "peak_freq_lpmm": float(fundamental.freq_lpmm),
            "peak_significance_db": float(fundamental.significance_db),
            "notch_bandwidth_lpmm": total_bw,
            "moire_atten_capped": "true" if capped else "false",
        }
    )
    if capped:
        extra["moire_warning"] = (
            "low-frequency grid fold overlaps anatomy; attenuation capped -- this "
            "grid is unsuitable with this panel (grid replacement recommended)"
        )
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra=extra,
    )
    return new.record_history(entry)
