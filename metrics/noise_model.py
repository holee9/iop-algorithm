"""Noise-model calibration builder: dose-step frames -> CalibSet(NOISE) (SWR-701).

Offline calibration builder (SPEC-DENOISE-001 decision 2, metrics.lag_irf /
metrics.defect_map precedent). It estimates the Poisson-Gaussian noise model
from flat-field frame stacks acquired at MULTIPLE dose levels and emits a
CalibSet(kind=NOISE) whose (alpha, sigma) payload feeds modules.denoise.

Model (SWR-701): per-pixel variance is affine in the mean signal,

    var(z) = alpha * mean(z) + sigma**2

so a linear regression of the per-dose variance against the per-dose mean
recovers the gain slope alpha and the read-noise intercept sigma**2. At least
two dose levels are required (a single point cannot separate slope from
intercept). While real dose-step data is measurement-pending [B], a known
synthetic (alpha, sigma) must be recovered within a [T] tolerance
(REQ-DENOISE-VST-3).

Layering stays metrics -> common (the produced CalibSet lives in common); the
correction module modules.denoise never imports metrics.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.calibset import (
    CalibKind,
    CalibProvenance,
    CalibSet,
    K_NOISE_ALPHA,
    K_NOISE_SIGMA,
)

__all__ = [
    "DoseLevel",
    "NoiseModelCalibrationError",
    "fit_noise_model",
]


class NoiseModelCalibrationError(ValueError):
    """Raised on an invalid noise-model calibration request or a degenerate fit."""


@dataclass(frozen=True)
class DoseLevel:
    """One dose level's flat-field capture(s).

    frames: a (K, ny, nx) stack (K repeated captures) or a single (ny, nx) frame
        of a spatially uniform flat field. The per-dose mean and variance are
        pooled over all pixels (and repeats) — the synthetic flat field has no
        fixed-pattern structure, so the spatial spread equals the pixel variance
        alpha*mean + sigma**2.
    """

    frames: np.ndarray


def _mean_var(level: DoseLevel) -> tuple[float, float]:
    arr = np.asarray(level.frames, dtype=np.float64).reshape(-1)
    if arr.size < 2:
        raise NoiseModelCalibrationError(
            "noise model: each dose level needs >= 2 samples to estimate variance"
        )
    return float(arr.mean()), float(arr.var(ddof=1))


# @MX:ANCHOR: [AUTO] sole (alpha, sigma) producer feeding modules.denoise via
# CalibSet(NOISE).
# @MX:REASON: fan_in spans the synthetic-recovery gate (REQ-DENOISE-VST-3), the
# denoise consumer, and the entry-gate kind-vs-stage wiring; the (alpha, sigma)
# payload schema and the >=2-dose premise are contractual.
def fit_noise_model(
    dose_levels: list[DoseLevel],
    *,
    panel_id: str,
    resolution: tuple[int, int],
    valid_from: str,
    valid_until: str,
    created_at: str = "",
    source: str = "noise-model-builder",
    sigma2_floor_tol: float = 1e-6,
    sigma2_clamp_tol_frac: float = 0.05,
) -> CalibSet:
    """Fit var = alpha*mean + sigma**2 from dose levels -> CalibSet(NOISE).

    Raises:
        NoiseModelCalibrationError: fewer than 2 dose levels, degenerate design
            (all dose means equal -> slope unidentifiable), a non-positive gain
            slope alpha, or a negative read-noise variance beyond
            ``sigma2_floor_tol`` (a physically impossible fit must surface as an
            explicit error, never a silently bad CalibSet).
    """
    if len(dose_levels) < 2:
        raise NoiseModelCalibrationError(
            "noise model: >= 2 dose levels are required to separate the gain "
            "slope from the read-noise intercept (single dose is forbidden)"
        )

    means = np.empty(len(dose_levels), dtype=np.float64)
    variances = np.empty(len(dose_levels), dtype=np.float64)
    for i, level in enumerate(dose_levels):
        means[i], variances[i] = _mean_var(level)

    # Near-equal dose means (within measurement noise) leave the slope
    # unidentifiable: the design matrix is effectively singular. Use a relative
    # spread test so noise-perturbed identical doses are still rejected.
    mean_scale = float(np.mean(np.abs(means))) or 1.0
    if float(np.ptp(means)) / mean_scale <= 1e-3:
        raise NoiseModelCalibrationError(
            "noise model: dose means are (near-)equal; the regression is singular "
            "(supply distinct dose levels)"
        )

    # Ordinary least squares fit of variance = alpha*mean + sigma**2.
    design = np.vstack([means, np.ones_like(means)]).T
    (alpha, sigma_sq), *_ = np.linalg.lstsq(design, variances, rcond=None)
    alpha = float(alpha)
    sigma_sq = float(sigma_sq)

    if alpha <= 0.0:
        raise NoiseModelCalibrationError(
            f"noise model: fitted gain slope alpha={alpha:.6g} is non-positive; "
            "variance must increase with signal (degenerate calibration)"
        )
    # A small negative intercept is an estimation artifact (the read-noise
    # variance is tiny relative to alpha*mean); clamp it to 0 within a [T]
    # tolerance scaled to the variance range (``sigma2_clamp_tol_frac``). A
    # grossly negative intercept is a degenerate fit and is refused.
    var_scale = float(np.mean(np.abs(variances))) or 1.0
    clamp_tol = abs(sigma2_floor_tol) + abs(sigma2_clamp_tol_frac) * var_scale
    if sigma_sq < -clamp_tol:
        raise NoiseModelCalibrationError(
            f"noise model: fitted read-noise variance sigma^2={sigma_sq:.6g} is "
            "negative beyond tolerance (degenerate calibration)"
        )
    clamped_negative = sigma_sq < 0.0
    sigma = float(np.sqrt(max(sigma_sq, 0.0)))

    # Regression quality note for the audit trail (IEC 62304 traceability).
    predicted = design @ np.array([alpha, sigma_sq])
    residual = variances - predicted
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((variances - variances.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    quality_note = (
        f"noise-model fit: alpha={alpha:.6g}, sigma={sigma:.6g}, "
        f"n_dose={len(dose_levels)}, r2={r2:.6g}"
    )
    if clamped_negative:
        # Record the clamp in provenance so a high-dose-only calibration (whose
        # intercept the regression cannot resolve) is not silently masked.
        quality_note += (
            f"; WARNING: negative read-noise variance sigma^2={sigma_sq:.6g} "
            f"clamped to 0 (within tolerance {clamp_tol:.6g})"
        )

    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(resolution),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=CalibKind.NOISE,
        data={
            K_NOISE_ALPHA: np.asarray(alpha, dtype=np.float64),
            K_NOISE_SIGMA: np.asarray(sigma, dtype=np.float64),
        },
        provenance=CalibProvenance(
            created_at=created_at, source=source, note=quality_note
        ),
    )
