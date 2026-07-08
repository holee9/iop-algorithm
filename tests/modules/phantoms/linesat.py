"""Synthetic phantoms + CalibSet builders for the T3 WP3/WP4 modules
(line_noise / saturation / geometry).

Known-distortion injectors with their ground truth (plan.md section 6). Every
constant is externalized via Params; EV thresholds live here as external-injected
values (measurement != judgment) and are compared against in the tests only.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.contract import Params
from tests.modules.phantoms.corrections import _CORR_DEFAULTS

# T3 module Params on top of the shared correction/metric defaults.
_LNSG_DEFAULTS = dict(_CORR_DEFAULTS)
_LNSG_DEFAULTS.update(
    {
        # line noise (SWR-503 priority path) [T] / SWR-502 k [appendix pending]
        "line_noise_profile_window": 1,  # [T] along-profile median window (1=off)
        "line_noise_highpass_cutoff": 0.03,  # [T] high-pass cutoff (cycles/sample)
        "line_noise_contam_k": 6.0,  # SWR-502 k*MAD (appendix A pending)
        "line_noise_miscorr_tol": 8.0,  # [T] structure miscorrection abs tolerance
        "line_noise_gradient_tol": 6.0,  # [T] max anatomy distortion at the FFT wrap seam (counts)
        # saturation
        "saturation_band_width": 2,  # SWR-602 W_band (appendix A pending)
        "raw_saturation_threshold": 60000.0,  # [B] S_th (offset stage)
        # geometry
        "geometry_poly_degree": 2,  # [B] SWR-603 degree (2-6)
        "geometry_activation_residual_px": 1.0,  # EV-106 min (external inject)
        "geometry_spline_order": 3,  # [P] resampling order
        "geometry_inverse_iters": 8,  # [P] fixed-point inverse iterations
    }
)

# External-injected EV thresholds (EVAL v1.1 min legs) -- modules never embed.
EV_LNSG = {
    "ev105_miscorr_rate_max": 0.01,  # structure miscorrection rate <= 1%
    "ev106_residual_px_max": 1.0,  # saturation-band / geometry residual <= 1px
}


def lnsg_params(**overrides) -> Params:
    values = dict(_LNSG_DEFAULTS)
    values.update(overrides)
    return Params(values=values)


def _calib(kind: CalibKind, data, shape) -> CalibSet:
    return CalibSet(
        panel_id="PANEL-A",
        resolution=tuple(shape),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=kind,
        data=data,
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
    )


def line_noise_calib(shape, reference=None) -> CalibSet:
    """CalibSet(LINE_NOISE). When `reference` (bool mask) is provided the
    reference SWR-501/502 path is selected; otherwise the SWR-503 path."""
    data = {}
    if reference is not None:
        data["reference_region"] = np.asarray(reference, dtype=bool)
    return _calib(CalibKind.LINE_NOISE, data, shape)


def saturation_calib(shape) -> CalibSet:
    """CalibSet(OTHER) for the saturation stage (no payload -- raw detection is
    the offset stage's responsibility, spec decision 2)."""
    return _calib(CalibKind.OTHER, {}, shape)


def geometry_calib(shape, coeffs_x, coeffs_y, residual) -> CalibSet:
    return _calib(
        CalibKind.OTHER,
        {
            "distortion_coeffs_x": np.asarray(coeffs_x, dtype=np.float64),
            "distortion_coeffs_y": np.asarray(coeffs_y, dtype=np.float64),
            "calibration_residual": np.asarray([float(residual)], dtype=np.float64),
        },
        shape,
    )


# ---------------------------------------------------------------------------
# Line-noise phantom (uniform illumination + known row/column banding).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinePhantom:
    observed: np.ndarray  # uniform + line noise + read noise
    clean: np.ndarray  # ground-truth (no line noise)
    row_offset: np.ndarray  # injected per-row banding
    col_offset: np.ndarray  # injected per-column banding


def make_line_noise_phantom(
    shape=(128, 128),
    background=3000.0,
    row_amp=40.0,
    col_amp=30.0,
    row_cycles=8,
    col_cycles=6,
    noise_sigma=2.0,
    seed=0,
) -> LinePhantom:
    """Uniform field with sinusoidal row/column banding (line noise) above the
    Gaussian cutoff so SWR-503 removes it while the flat anatomy is preserved."""
    ny, nx = shape
    rng = np.random.default_rng(seed)
    clean = np.full(shape, background, dtype=np.float64)
    r = np.arange(ny)
    c = np.arange(nx)
    row_offset = row_amp * np.sin(2.0 * np.pi * row_cycles * r / ny)
    col_offset = col_amp * np.sin(2.0 * np.pi * col_cycles * c / nx)
    observed = (
        clean
        + row_offset[:, None]
        + col_offset[None, :]
        + rng.normal(0.0, noise_sigma, size=shape)
    )
    return LinePhantom(
        observed.astype(np.float32), clean.astype(np.float32), row_offset, col_offset
    )


@dataclass(frozen=True)
class StructurePhantom:
    observed: np.ndarray  # structure + line noise + noise
    structure_true: np.ndarray  # structure WITHOUT line noise (ground truth)
    structure_mask: np.ndarray  # bool: high-attenuation structure region


def make_structure_phantom(
    shape=(128, 128),
    background=3000.0,
    structure_value=1200.0,  # high-attenuation (metal) feature
    block=(52, 60, 12, 8),  # (row0, col0, h, w) thin high-attenuation feature
    row_amp=40.0,
    col_amp=30.0,
    row_cycles=8,
    col_cycles=6,
    noise_sigma=2.0,
    seed=1,
) -> StructurePhantom:
    ny, nx = shape
    rng = np.random.default_rng(seed)
    structure_true = np.full(shape, background, dtype=np.float64)
    r0, c0, h, w = block
    smask = np.zeros(shape, dtype=bool)
    smask[r0 : r0 + h, c0 : c0 + w] = True
    structure_true[smask] = structure_value
    r = np.arange(ny)
    c = np.arange(nx)
    row_offset = row_amp * np.sin(2.0 * np.pi * row_cycles * r / ny)
    col_offset = col_amp * np.sin(2.0 * np.pi * col_cycles * c / nx)
    observed = (
        structure_true
        + row_offset[:, None]
        + col_offset[None, :]
        + rng.normal(0.0, noise_sigma, size=shape)
    )
    return StructurePhantom(
        observed.astype(np.float32), structure_true.astype(np.float32), smask
    )


@dataclass(frozen=True)
class GradientLinePhantom:
    observed: np.ndarray  # gradient anatomy + NON-periodic line noise + noise
    clean: np.ndarray  # ground-truth (gradient anatomy, no line noise)
    row_offset: np.ndarray  # injected per-row NON-periodic banding


def make_nonperiodic_line_noise_phantom(
    shape=(128, 128),
    background=3000.0,
    grad_row=6.0,  # anatomy: linear ramp along rows (non-periodic, big seam)
    grad_col=4.0,  # anatomy: linear ramp along columns
    band_amp=40.0,  # NON-periodic row banding (random, not a clean sinusoid)
    noise_sigma=2.0,
    seed=7,
) -> GradientLinePhantom:
    """Anatomy = a smooth linear gradient (deliberately NON-periodic so the FFT
    wrap seam is exercised, review finding 9) plus high-frequency, NON-periodic
    per-row banding (random offsets). SWR-503 must remove the banding while
    preserving the gradient across the whole field, including the edges where a
    naive rfft rings."""
    ny, nx = shape
    rng = np.random.default_rng(seed)
    r = np.arange(ny)
    c = np.arange(nx)
    ramp = grad_row * (r / (ny - 1))[:, None] + grad_col * (c / (nx - 1))[None, :]
    clean = background + ramp
    # Non-periodic high-frequency banding: white per-row offsets high-passed by
    # construction (subtract a slow moving average so it is banding, not ramp).
    raw_band = band_amp * rng.standard_normal(ny)
    slow = np.convolve(raw_band, np.ones(9) / 9.0, mode="same")
    row_offset = raw_band - slow  # zero-mean high-frequency per-row banding
    observed = (
        clean
        + row_offset[:, None]
        + rng.normal(0.0, noise_sigma, size=shape)
    )
    return GradientLinePhantom(
        observed.astype(np.float32), clean.astype(np.float64), row_offset
    )


# ---------------------------------------------------------------------------
# Geometry phantom (ideal grid of Gaussian dots + known polynomial distortion).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GridPhantom:
    ideal: np.ndarray  # undistorted grid of dots
    observed: np.ndarray  # forward-distorted grid
    centers: np.ndarray  # (N, 2) ideal (row, col) dot centers
    coeffs_x: np.ndarray  # forward D_col polynomial coeffs
    coeffs_y: np.ndarray  # forward D_row polynomial coeffs
    residual_px: float  # max |D| over the field (calibration residual)


def _linear_coeffs(a: float, degree: int) -> tuple[np.ndarray, np.ndarray]:
    """D_col(u,v)=a*(u-0.5), D_row(u,v)=a*(v-0.5) as (degree+1)^2 coeff arrays."""
    cx = np.zeros((degree + 1, degree + 1), dtype=np.float64)
    cy = np.zeros((degree + 1, degree + 1), dtype=np.float64)
    cx[0, 0] = -a / 2.0
    cx[1, 0] = a  # u term
    cy[0, 0] = -a / 2.0
    cy[0, 1] = a  # v term
    return cx, cy


def make_grid_phantom(
    shape=(120, 120),
    spacing=20,
    margin=15,
    dot_sigma=1.3,
    amplitude=1000.0,
    a=6.0,  # distortion strength (px); peak |D| = a/sqrt(2)
    degree=2,
) -> GridPhantom:
    ny, nx = shape
    rows = np.arange(margin, ny - margin + 1, spacing)
    cols = np.arange(margin, nx - margin + 1, spacing)
    centers = np.array([(r, c) for r in rows for c in cols], dtype=np.float64)

    rr, cc = np.mgrid[0:ny, 0:nx].astype(np.float64)

    def _gaussian_field(sr: np.ndarray, sc: np.ndarray) -> np.ndarray:
        """Analytic sum-of-Gaussians image sampled at coordinates (sr, sc)."""
        field = np.zeros(shape, dtype=np.float64)
        for (r, c) in centers:
            field += amplitude * np.exp(
                -(((sr - r) ** 2 + (sc - c) ** 2) / (2.0 * dot_sigma**2))
            )
        return field

    ideal = _gaussian_field(rr, cc)

    cx, cy = _linear_coeffs(a, degree)
    u = cc / max(nx - 1, 1)
    v = rr / max(ny - 1, 1)
    d_col = a * (u - 0.5)
    d_row = a * (v - 0.5)
    # observed[p] = ideal[p + D(p)] evaluated ANALYTICALLY (the Gaussian field
    # sampled directly at the distorted coordinates), NOT via the same
    # map_coordinates spline the corrector uses. This avoids the inverse crime
    # (review finding 10): a sign or normalization error in the module's inverse
    # warp now fails the residual gate instead of cancelling out.
    observed = _gaussian_field(rr + d_row, cc + d_col)
    residual = float(np.max(np.sqrt(d_row**2 + d_col**2)))
    return GridPhantom(
        ideal.astype(np.float32),
        observed.astype(np.float32),
        centers,
        cx,
        cy,
        residual,
    )


def dot_centroids(image, threshold_frac=0.4):
    """Locate bright-dot centroids by thresholding + connected-component COM."""
    from scipy import ndimage

    img = np.asarray(image, dtype=np.float64)
    thr = threshold_frac * float(img.max())
    labels, n = ndimage.label(img > thr)
    if n == 0:
        return np.empty((0, 2), dtype=np.float64)
    coms = ndimage.center_of_mass(img, labels, index=range(1, n + 1))
    return np.array(coms, dtype=np.float64)


def max_grid_residual(centroids, centers):
    """Max Euclidean distance from each ideal center to the nearest centroid."""
    if centroids.shape[0] == 0:
        return np.inf
    worst = 0.0
    for ctr in centers:
        d = np.min(np.sqrt(np.sum((centroids - ctr) ** 2, axis=1)))
        worst = max(worst, float(d))
    return worst
