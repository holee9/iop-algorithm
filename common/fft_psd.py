"""Shared component: FFT / power spectral density (SWR-000-9, REQ-INFRA-STATIC-3).

@MX:ANCHOR: [AUTO] Single implementation of the 2D FFT / PSD primitives shared
by the metrics engine (NPS/DQE) and later grid-suppression (T7). Consumers must
reference these functions, never re-implement FFT/PSD locally (SWR-000-9 no
duplication).
@MX:REASON: fan_in spans metrics.nps, metrics.dqe (via nps), and future
modules/grid; a divergent PSD normalization would silently corrupt every
downstream NPS/DQE value.

First real definition triggered by SPEC-METRICS-001 (T1). Accuracy is the single
goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np


def compute_psd(image: np.ndarray) -> np.ndarray:
    """2D power spectral density of a single (zero-mean) ROI, fftshift-centred.

    Returns |FFT(image)|**2 with the zero-frequency component at the array
    centre. The caller is responsible for detrending; this primitive does not
    subtract any trend so it stays a pure spectral estimator.
    """
    arr = np.asarray(image, dtype=np.float64)
    spectrum = np.fft.fft2(arr)
    return np.fft.fftshift(np.abs(spectrum) ** 2)


def nps_2d(
    rois: np.ndarray,
    pixel_area_mm2: float,
) -> np.ndarray:
    """Ensemble-averaged 2D noise power spectrum (NPS), fftshift-centred.

    NPS(u,v) = (dx*dy) / (Nx*Ny) * < |DFT{roi}|^2 >  over the ROI ensemble,
    where each ROI is zero-mean (detrended by the caller). For white noise of
    variance s^2 this yields a flat NPS at level s^2 * dx * dy — the analytic
    identity the synthetic-validation phantoms check against.

    Args:
        rois: array of shape (n_roi, Ny, Nx), each ROI already detrended.
        pixel_area_mm2: dx*dy in mm^2 (from the panel pitch, CalibSet/Params).
    """
    stack = np.asarray(rois, dtype=np.float64)
    if stack.ndim != 3:
        raise ValueError("rois must have shape (n_roi, Ny, Nx)")
    n_roi, ny, nx = stack.shape
    acc = np.zeros((ny, nx), dtype=np.float64)
    for roi in stack:
        acc += np.abs(np.fft.fft2(roi)) ** 2
    acc /= n_roi
    acc *= pixel_area_mm2 / (nx * ny)
    return np.fft.fftshift(acc)


def radial_frequency_axes(
    ny: int, nx: int, pitch_mm: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return fftshift-aligned spatial-frequency axes (lp/mm) for a NY x NX NPS.

    The sample spacing is the panel pitch, so the axis extends to the detector
    Nyquist 1/(2*pitch) at the array edge.
    """
    fy = np.fft.fftshift(np.fft.fftfreq(ny, d=pitch_mm))
    fx = np.fft.fftshift(np.fft.fftfreq(nx, d=pitch_mm))
    return fy, fx


def axial_welch_psd(
    image: np.ndarray,
    axis: int,
    pitch_mm: float,
    *,
    detrend: bool = True,
    window: str | None = "hann",
) -> tuple[np.ndarray, np.ndarray]:
    """1D power spectral density along `axis`, averaged over perpendicular lines.

    @MX:NOTE: [AUTO] First-consumer extension for grid-line suppression (T7,
    SPEC-GRID-001, SWR-1002 "해당 축 1D PSD (전 행 평균, Welch)"). Kept in the
    shared FFT/PSD component so the grid module consumes it rather than
    re-implementing FFT locally (SWR-000-9 no duplication).

    The estimate is a Bartlett/Welch average: each line perpendicular to the
    scanned axis contributes one periodogram and the periodograms are averaged,
    trading resolution for variance. This is the axial equivalent of the
    ensemble average axial_1d_nps performs on 2D NPS.

    Args:
        image: 2D array.
        axis: axis ALONG which the spectrum is taken. axis=1 scans columns (x),
            averaging over rows — the estimator for a VERTICAL grid whose
            modulation is periodic along x. axis=0 scans rows (y), averaging over
            columns — for a HORIZONTAL grid.
        pitch_mm: sample spacing (mm); the frequency axis extends to the detector
            Nyquist 1/(2*pitch).
        detrend: subtract each line's mean before the transform so the DC / slow
            trend of anatomy does not leak into the low-frequency bins.
        window: taper applied along `axis` before the transform ("hann" by
            default, or None). Windowing suppresses the sinc leakage a sharp step
            (edge) would otherwise spread across the band as spurious sidelobe
            peaks — the standard Welch/Bartlett tapering that makes a narrowband
            grid peak stand out cleanly against a sloped edge spectrum.

    Returns:
        (freq_lpmm, psd) over the non-negative half-axis (rfft), both length
        n//2 + 1 where n = image.shape[axis].
    """
    arr = np.asarray(image, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("axial_welch_psd expects a 2D image")
    if axis not in (0, 1):
        raise ValueError("axis must be 0 or 1")
    if detrend:
        arr = arr - arr.mean(axis=axis, keepdims=True)
    n = arr.shape[axis]
    if window == "hann":
        taper = np.hanning(n)
        shape = [1, 1]
        shape[axis] = n
        arr = arr * taper.reshape(shape)
    elif window is not None:
        raise ValueError("window must be 'hann' or None")
    spectrum = np.fft.rfft(arr, axis=axis)
    power = np.abs(spectrum) ** 2
    other = 1 - axis
    psd = power.mean(axis=other)
    freq = np.fft.rfftfreq(n, d=pitch_mm)
    return freq, psd


def axial_1d_nps(
    nps2d: np.ndarray,
    pitch_mm: float,
    *,
    exclude_axis_bins: int = 1,
    n_average_lines: int = 7,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract the 1D axial NPS by averaging lines adjacent to the axes.

    IEC 62220-1: the two central rows/columns (the axes themselves) carry
    residual low-frequency trend and are excluded; a band of lines on either
    side is averaged. Positive frequencies (0 .. Nyquist) are returned.

    Args:
        nps2d: fftshift-centred 2D NPS.
        pitch_mm: panel pitch (mm).
        exclude_axis_bins: number of central bins on each side to skip [P].
        n_average_lines: number of off-axis lines averaged per side [P].

    Returns:
        (freq_lpmm, nps_1d) over the non-negative frequency half-axis.
    """
    ny, nx = nps2d.shape
    cy, cx = ny // 2, nx // 2
    # Rows adjacent to the horizontal axis (average |offset| in a band).
    lo = exclude_axis_bins
    hi = exclude_axis_bins + n_average_lines
    row_band = np.concatenate(
        [nps2d[cy - hi : cy - lo, :], nps2d[cy + lo + 1 : cy + hi + 1, :]], axis=0
    )
    col_band = np.concatenate(
        [nps2d[:, cx - hi : cx - lo], nps2d[:, cx + lo + 1 : cx + hi + 1]], axis=1
    )
    horiz = row_band.mean(axis=0)  # 1D over x (length nx)
    vert = col_band.mean(axis=1)  # 1D over y (length ny)

    fx = np.fft.fftshift(np.fft.fftfreq(nx, d=pitch_mm))
    fy = np.fft.fftshift(np.fft.fftfreq(ny, d=pitch_mm))
    # Combine the two orthogonal 1D estimates onto the positive half-axis by
    # interpolating the vertical estimate onto the horizontal frequency grid.
    # For a non-square NPS (nx != ny) the two axes have different Nyquist limits;
    # np.interp would CLAMP the vertical estimate beyond fy.max(), biasing the
    # top band. Restrict the combined average to the common frequency range
    # min(fx.max(), fy.max()) so no bin is fabricated by clamping.
    fmax_common = min(float(fx.max()), float(fy.max()))
    pos = (fx >= 0) & (fx <= fmax_common)
    freq = fx[pos]
    horiz_pos = horiz[pos]
    vert_interp = np.interp(freq, fy, vert)
    nps_1d = 0.5 * (horiz_pos + vert_interp)
    return freq, nps_1d
