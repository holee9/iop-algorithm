"""Scatter-kernel calibration builder: thickness/kV -> CalibSet(SCATTER) (SWR-1101).

Offline calibration builder (SPEC-VGRID-001 decision 2, metrics.lag_irf /
metrics.noise_model precedent). It derives the dual-Gaussian scatter PSF used by
the T8 kernel virtual-grid stage (modules.virtual_grid) and emits a
CalibSet(kind=SCATTER) whose (scatter_amp, scatter_sigma) payload feeds that
module as its SOLE source (REQ-VGRID-CALIB-1). Layering stays metrics -> common;
the correction module modules.virtual_grid never imports metrics.

Model (SWR-1101, SKS [L]): the object-thickness-dependent scatter point-spread
function is approximated by a sum of two Gaussians in the x8-downsampled SKS
estimation domain,

    K(r) = amp[0] * G(r; sigma[0]) + amp[1] * G(r; sigma[1])

where each G integrates to 1, so amp[i] are the scatter-to-primary weights and
amp[0]+amp[1] is the DC scatter-to-primary ratio (SPR). The SPR grows with object
thickness; the scatter spread (sigma) grows with thickness and softens with kV.
This single-thickness-proxy dual-Gaussian is the P1 scope; the multi-thickness /
kV-indexed kernel switch (ASKS-class) is a reserved promotion path ([B], deferred
to real measurement).

Two builder entry points, both emitting the SAME CalibSet(SCATTER) schema so the
consumer never changes:
  - ``build_scatter_kernel``: parametric thickness/kV -> dual-Gaussian, the
    pre-validation path (synthetic known kernel, LAG synthetic-IRF / DENOISE
    synthetic-lambda precedent). Real beam-stop/kernel-fit measurement is [B].
  - ``fit_scatter_kernel_from_samples``: least-squares fit of the two amplitudes
    from a measured primary/scatter sample pair at fixed sigmas. This exists to
    demonstrate that the reserved MC-precomputed-LUT avoidance alternative
    (SWR-1103, REQ-VGRID-CALIB-3) is a BUILDER-side substitution — a different
    kernel derivation emits the identical CalibSet(SCATTER) with no redesign of
    modules.virtual_grid. The MC-LUT alternative itself is out of P1 scope.

WARNING (SWR-1101/1103, CLAUDE.md T8, patent flag preserved): the SKS
formulation is claimed by an ACTIVE patent (US 11,911,202 and related). This
builder is implemented on technical-necessity grounds; the patent claim
comparison and release gating are OUT OF the P1 SW scope and deferred to a
release gate (see .moai/specs/SPEC-VGRID-001/spec.md). No patent judgment is made
here; the kernel provenance carries a deferred-clearance note for traceability.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import (
    CalibKind,
    CalibProvenance,
    CalibSet,
    K_SCATTER_AMP,
    K_SCATTER_SIGMA,
)

__all__ = [
    "ScatterKernelCalibrationError",
    "PATENT_PROVENANCE_NOTE",
    "build_scatter_kernel",
    "fit_scatter_kernel_from_samples",
]

# ⚠P provenance note (SWR-1101/1103, patent flag preserved). Recorded on every
# emitted CalibSet(SCATTER) so the release-gate patent comparison can trace the
# kernel origin. The SW makes no patent judgment (out of P1 scope).
PATENT_PROVENANCE_NOTE = (
    "SKS scatter kernel; patent US 11,911,202 (and related) claims the SKS "
    "formulation — clearance deferred to release gate, out of P1 SW scope "
    "(SWR-1101/1103, SPEC-VGRID-001)"
)


class ScatterKernelCalibrationError(ValueError):
    """Raised on an invalid scatter-kernel calibration request or degenerate fit."""


def _emit(
    amp: np.ndarray,
    sigma: np.ndarray,
    *,
    panel_id: str,
    resolution: tuple[int, int],
    valid_from: str,
    valid_until: str,
    created_at: str,
    source: str,
    note: str,
) -> CalibSet:
    """Validate the dual-Gaussian coefficients and package a CalibSet(SCATTER).

    A degenerate kernel (non-finite, non-positive sigma, non-positive amplitude,
    or an SPR >= 1 that would make the SKS iteration diverge) is refused with an
    explicit error rather than emitting a silently bad CalibSet (SWR-000-5).
    """
    amp = np.asarray(amp, dtype=np.float64).reshape(-1)
    sigma = np.asarray(sigma, dtype=np.float64).reshape(-1)
    if amp.size != 2 or sigma.size != 2:
        raise ScatterKernelCalibrationError(
            "scatter kernel: dual-Gaussian requires exactly 2 amplitudes and "
            f"2 sigmas, got amp={amp.size}, sigma={sigma.size}"
        )
    if not np.all(np.isfinite(amp)) or not np.all(np.isfinite(sigma)):
        raise ScatterKernelCalibrationError(
            "scatter kernel: non-finite dual-Gaussian coefficient (degenerate)"
        )
    if np.any(sigma <= 0.0):
        raise ScatterKernelCalibrationError(
            f"scatter kernel: Gaussian sigmas must be > 0, got {sigma.tolist()}"
        )
    if np.any(amp <= 0.0):
        raise ScatterKernelCalibrationError(
            f"scatter kernel: amplitudes (SPR weights) must be > 0, got {amp.tolist()}"
        )
    spr = float(amp.sum())
    if spr >= 1.0:
        raise ScatterKernelCalibrationError(
            f"scatter kernel: DC scatter-to-primary ratio (sum of amplitudes) "
            f"= {spr:.6g} must be < 1 for the SKS fixed-point iteration to "
            "converge (spectral radius < 1, SWR-1101)"
        )
    full_note = f"{note}; SPR={spr:.6g}; {PATENT_PROVENANCE_NOTE}"
    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(resolution),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=CalibKind.SCATTER,
        data={
            K_SCATTER_AMP: np.asarray(amp, dtype=np.float64),
            K_SCATTER_SIGMA: np.asarray(sigma, dtype=np.float64),
        },
        provenance=CalibProvenance(
            created_at=created_at, source=source, note=full_note
        ),
    )


# @MX:ANCHOR: [AUTO] sole dual-Gaussian scatter-kernel producer feeding
# modules.virtual_grid via CalibSet(SCATTER).
# @MX:REASON: fan_in spans the synthetic-recovery / CNR gate (XDET-TC-017), the
# virtual_grid consumer, and the entry-gate kind-vs-stage wiring; the (amp,
# sigma) payload schema and the SPR < 1 convergence premise are contractual.
def build_scatter_kernel(
    thickness_proxy_cm: float,
    kv: float,
    *,
    panel_id: str,
    resolution: tuple[int, int],
    valid_from: str,
    valid_until: str,
    spr_per_cm: float,
    spr_max: float,
    sigma_narrow_px: float,
    sigma_wide_px: float,
    wide_fraction: float,
    thickness_sigma_gain_per_cm: float,
    kv_sigma_ref: float,
    created_at: str = "",
    source: str = "scatter-kernel-builder",
) -> CalibSet:
    """Parametric thickness/kV -> dual-Gaussian scatter kernel -> CalibSet(SCATTER).

    The scatter-to-primary ratio scales with object thickness and saturates at
    ``spr_max``; the scatter spread (both Gaussian sigmas) grows with thickness
    and softens (broadens) with a higher kV via the ``kv/kv_sigma_ref`` factor.
    ``wide_fraction`` splits the SPR between the wide and narrow Gaussians. Every
    coefficient is an externalized argument (documented grade in the SPEC; no
    hardcoded magic — CLAUDE.md parameter policy). Refuses a degenerate kernel
    (SWR-000-5) via ``_emit``.

    Grades (SWR appendix A, registration requested): spr_per_cm / spr_max /
    wide_fraction / sigma_*_px / thickness_sigma_gain_per_cm / kv_sigma_ref are
    [B] (panel-measured scatter fit) — supplied synthetically for pre-validation.
    """
    if thickness_proxy_cm < 0.0 or kv <= 0.0:
        raise ScatterKernelCalibrationError(
            f"scatter kernel: thickness_proxy_cm must be >= 0 and kv > 0, got "
            f"thickness={thickness_proxy_cm}, kv={kv}"
        )
    spr = min(float(spr_max), float(spr_per_cm) * float(thickness_proxy_cm))
    if spr <= 0.0:
        raise ScatterKernelCalibrationError(
            f"scatter kernel: derived SPR={spr:.6g} is non-positive (thickness "
            f"{thickness_proxy_cm} cm too small to produce scatter)"
        )
    wide = float(np.clip(wide_fraction, 0.0, 1.0))
    amp = np.array([spr * (1.0 - wide), spr * wide], dtype=np.float64)
    # Spread grows with thickness and softens with kV.
    thickness_gain = 1.0 + float(thickness_sigma_gain_per_cm) * float(thickness_proxy_cm)
    kv_gain = float(kv) / float(kv_sigma_ref)
    scale = thickness_gain * kv_gain
    sigma = np.array(
        [float(sigma_narrow_px) * scale, float(sigma_wide_px) * scale],
        dtype=np.float64,
    )
    note = (
        f"parametric scatter kernel: thickness={thickness_proxy_cm:g}cm, kv={kv:g}"
    )
    return _emit(
        amp,
        sigma,
        panel_id=panel_id,
        resolution=resolution,
        valid_from=valid_from,
        valid_until=valid_until,
        created_at=created_at,
        source=source,
        note=note,
    )


def fit_scatter_kernel_from_samples(
    primary: np.ndarray,
    scatter: np.ndarray,
    sigma_px: tuple[float, float],
    *,
    panel_id: str,
    resolution: tuple[int, int],
    valid_from: str,
    valid_until: str,
    created_at: str = "",
    source: str = "scatter-kernel-fit",
) -> CalibSet:
    """Least-squares fit of the two dual-Gaussian amplitudes at fixed sigmas.

    Given a measured primary field and the scatter it produced, fit
    ``scatter ~= amp[0]*G(primary; sigma[0]) + amp[1]*G(primary; sigma[1])`` for
    the two non-negative amplitudes (fixed sigmas). This second derivation path
    demonstrates the SWR-1103 avoidance-alternative reservation
    (REQ-VGRID-CALIB-3): a different kernel origin emits the IDENTICAL
    CalibSet(SCATTER) schema, so swapping in the MC-precomputed-LUT alternative is
    a builder-side change with no modules.virtual_grid redesign. Refuses a
    degenerate fit (SWR-000-5) via ``_emit``.
    """
    from scipy import ndimage

    p = np.asarray(primary, dtype=np.float64)
    s = np.asarray(scatter, dtype=np.float64)
    if p.shape != s.shape:
        raise ScatterKernelCalibrationError(
            f"scatter kernel fit: primary {p.shape} and scatter {s.shape} shapes "
            "must match"
        )
    if len(sigma_px) != 2:
        raise ScatterKernelCalibrationError(
            "scatter kernel fit: exactly 2 fixed sigmas are required"
        )
    g0 = ndimage.gaussian_filter(p, sigma=float(sigma_px[0]), mode="reflect")
    g1 = ndimage.gaussian_filter(p, sigma=float(sigma_px[1]), mode="reflect")
    design = np.vstack([g0.reshape(-1), g1.reshape(-1)]).T
    coeffs, *_ = np.linalg.lstsq(design, s.reshape(-1), rcond=None)
    amp = np.asarray(coeffs, dtype=np.float64)
    note = "least-squares amplitude fit from primary/scatter samples"
    return _emit(
        amp,
        np.asarray(sigma_px, dtype=np.float64),
        panel_id=panel_id,
        resolution=resolution,
        valid_from=valid_from,
        valid_until=valid_until,
        created_at=created_at,
        source=source,
        note=note,
    )
