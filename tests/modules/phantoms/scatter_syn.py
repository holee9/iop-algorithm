"""Synthetic GDS-scatter phantoms + externalized Params/EV for T8 (SPEC-VGRID-001).

Known-kernel / known-scatter injectors for the kernel virtual-grid module
(modules.virtual_grid). A known dual-Gaussian scatter kernel injects a known
low-frequency veiling into a known-contrast primary; the module must recover it
and improve CNR (measurement != judgment — every EV/tolerance lives here as an
external-injected value, never embedded in the module or the engine; LAG
synthetic-IRF / DENOISE synthetic-lambda precedent). Real GDS-scatter phantom
data is measurement-pending [B]; this pre-validates the module (CLAUDE.md T8).

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from common.calibset import (
    CalibKind,
    CalibProvenance,
    CalibSet,
    K_SCATTER_AMP,
    K_SCATTER_SIGMA,
)
from common.contract import Params
from common.robust_stats import robust_mean, robust_std
from common.xframe import new_frame

# External-injected EV / tolerance thresholds (EVAL v1.1 EV-202 leg + [T]
# tolerances; injected here, never embedded in the module/engine).
EV = {
    "ev202_cnr_improvement_min": 0.20,  # CNR improvement >= +20% (EV-202 min, hard DoD)
    "scatter_rel_err_tol": 0.25,  # Ŝ vs S_inj relative L2 tolerance [T]
    "lowsignal_noise_boost_tol": 0.05,  # low-signal noise must not grow > 5% [T]
}

# Kernel geometry in the x8-downsampled (levels=3) SKS domain.
DOWNSAMPLE_LEVELS = 3
KERNEL_AMP = np.array([0.30, 0.30], dtype=np.float64)  # SPR 0.6 (high-SPR, < 1)
KERNEL_SIGMA_DOWN = np.array([1.0, 3.5], dtype=np.float64)  # downsampled px


def scatter_calib(
    shape: tuple[int, int],
    *,
    amp: np.ndarray = KERNEL_AMP,
    sigma: np.ndarray = KERNEL_SIGMA_DOWN,
    panel_id: str = "PANEL-A",
    valid_from: str = "2026-01-01",
    valid_until: str = "2027-01-01",
    data: dict | None = None,
) -> CalibSet:
    """CalibSet(SCATTER) carrying the dual-Gaussian kernel (sole module source)."""
    if data is None:
        data = {
            K_SCATTER_AMP: np.asarray(amp, dtype=np.float64),
            K_SCATTER_SIGMA: np.asarray(sigma, dtype=np.float64),
        }
    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(shape),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=CalibKind.SCATTER,
        data=data,
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic-scatter"),
    )


def other_calib(
    shape: tuple[int, int],
    *,
    panel_id: str = "PANEL-A",
    valid_from: str = "2026-01-01",
    valid_until: str = "2027-01-01",
) -> CalibSet:
    """Empty CalibSet(OTHER) placeholder (used for kind-mismatch gate tests)."""
    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(shape),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=CalibKind.OTHER,
        data={},
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
    )


def vgrid_params(**overrides) -> Params:
    """virtual_grid Params: iterations, downsample levels, weight, low-signal ramp."""
    values = {
        "vgrid_sks_iterations": 3,  # [T] SKS iterations 2..3
        "vgrid_downsample_levels": DOWNSAMPLE_LEVELS,  # [T] x8 downsample
        "vgrid_grid_ratio_w": 1.0,  # [T]/[P] grid-ratio conversion weight
        "vgrid_lowsignal_threshold": 50.0,  # [T] low-signal attenuation midpoint
        "vgrid_lowsignal_softness": 30.0,  # [T] attenuation transition width
    }
    values.update(overrides)
    return Params(values=values)


def _inject(primary: np.ndarray, amp: np.ndarray, sigma_down: np.ndarray) -> np.ndarray:
    """Full-resolution known scatter S_inj = conv(P, K_full).

    The full-resolution Gaussian sigmas are the downsampled sigmas scaled by the
    x2^levels downsample factor, so the injected veiling matches what the module
    estimates in the downsampled domain.
    """
    sigma_full = np.asarray(sigma_down, dtype=np.float64) * (2**DOWNSAMPLE_LEVELS)
    return amp[0] * ndimage.gaussian_filter(
        primary, float(sigma_full[0]), mode="reflect"
    ) + amp[1] * ndimage.gaussian_filter(primary, float(sigma_full[1]), mode="reflect")


def make_cnr_phantom(
    shape: tuple[int, int] = (96, 96), *, seed: int = 0, noise_std: float = 1.0
):
    """Known-contrast phantom with a structured scatter halo (hard DoD, TC-017).

    A bright structure on the left half produces a strong scatter ramp across the
    background ROI surrounding a bright detail; the ramp inflates the background
    dispersion, degrading CNR. Removing the estimated scatter flattens the ramp
    and restores CNR (EV-202 improvement). Returns (primary, observed, S_inj,
    feat_roi, bg_roi).
    """
    ny, nx = shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    primary = np.full(shape, 400.0, dtype=np.float64)
    primary[:, : nx // 2] = 2000.0  # bright structure -> scatter ramp
    cy, cx = ny // 2, (3 * nx) // 4
    feat = (yy - cy) ** 2 + (xx - cx) ** 2 <= 6**2
    primary[feat] = 700.0  # bright detail on the dark right background
    s_inj = _inject(primary, KERNEL_AMP, KERNEL_SIGMA_DOWN)
    rng = np.random.default_rng(seed)
    observed = primary + s_inj + rng.normal(0.0, noise_std, shape)
    r2 = (yy - cy) ** 2 + (xx - cx) ** 2
    feat_roi = r2 <= 4**2
    bg_roi = (r2 >= 7**2) & (r2 <= 16**2)
    return primary, observed, s_inj, feat_roi, bg_roi


def make_smooth_scatter_phantom(shape: tuple[int, int] = (96, 96)):
    """Smooth primary with an injected known scatter (Ŝ-vs-S_inj accuracy, TC-017).

    A smooth (edge-free) primary keeps the down/up-sample estimation error low so
    the SKS estimate can be checked against the injected scatter within the [T]
    tolerance. Returns (primary, observed, S_inj).
    """
    ny, nx = shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    primary = (
        800.0
        + 400.0 * np.exp(-(((yy - ny / 2) ** 2 + (xx - nx / 2) ** 2) / (2 * 25.0**2)))
        + 2.0 * xx
    )
    s_inj = _inject(primary, KERNEL_AMP, KERNEL_SIGMA_DOWN)
    return primary, primary + s_inj, s_inj


def make_lowsignal_phantom(shape: tuple[int, int] = (96, 96), *, seed: int = 1):
    """Phantom with a dark low-signal region for noise-boost / non-negativity tests.

    The left third is near-zero signal (below the low-signal threshold); the rest
    is a bright field with a scatter halo. Returns (observed, lowsignal_mask).
    """
    ny, nx = shape
    primary = np.full(shape, 1500.0, dtype=np.float64)
    lowsig = np.zeros(shape, dtype=bool)
    lowsig[:, : nx // 3] = True
    primary[lowsig] = 5.0  # near-zero signal
    s_inj = _inject(primary, KERNEL_AMP, KERNEL_SIGMA_DOWN)
    rng = np.random.default_rng(seed)
    observed = primary + s_inj + rng.normal(0.0, 3.0, shape)
    return observed, lowsig


def make_frame(pixel: np.ndarray, masks: np.ndarray | None = None):
    """XFrame from a synthetic pixel field."""
    return new_frame(np.asarray(pixel, dtype=np.float32), masks)


def cnr(image: np.ndarray, feat_roi: np.ndarray, bg_roi: np.ndarray) -> float:
    """Contrast-to-noise ratio from robust ROI statistics (measurement side)."""
    img = np.asarray(image, dtype=np.float64)
    contrast = abs(robust_mean(img[feat_roi]) - robust_mean(img[bg_roi]))
    return contrast / robust_std(img[bg_roi])
