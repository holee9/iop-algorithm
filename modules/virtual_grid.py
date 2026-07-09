"""Kernel virtual grid: SKS scatter estimation + subtraction (SWR-1101~1103, T8/WP9).

Stateless, pure-functional scatter correction for a GRID-LESS detector: it
estimates the scene-dependent low-frequency scatter (veiling glare) by Scatter
Kernel Superposition (SKS) and subtracts it, virtually reproducing the
scatter-suppression effect of a physical anti-scatter grid (SPEC-VGRID-001).
This is distinct from the T7 `grid` stage, which removes the periodic grid-LINE
modulation of a detector that HAS a physical grid; the two stages are mutually
exclusive by acquisition context and virtual_grid performs NO grid-line notch.

Two stages (SWR-1101/1102):

  (1) SKS scatter estimation (SWR-1101) in the x8-downsampled domain. The
      downsample reuses the shared component common.pyramid.reduce_once (x2 three
      times) — a SPATIAL-domain operator, NOT common.fft_psd (this is why
      virtual_grid consumes pyramid, unlike the frequency-domain T7 grid). In the
      downsampled domain the SKS fixed-point iteration runs
          P_hat_0 = I_down,   S_i = conv(P_hat_i, K),   P_hat_{i+1} = I_down - S_i
      for a Params-specified number of iterations (2..3, [L]); the final S is the
      scatter estimate S_hat_down. The dual-Gaussian kernel K is sourced ONLY from
      CalibSet(SCATTER) (REQ-VGRID-ESTIMATE-2) — never hardcoded. Because the
      kernel DC gain (sum of amplitudes = SPR) is < 1 the iteration converges
      (spectral radius < 1, SWR-1101 high-SPR robustness).

  (2) Subtraction (SWR-1102): S_hat_down is bilinear-upsampled to full resolution
      (scipy, distinct from the pyramid Gaussian expand) and subtracted,
          I' = I - w_eff * S_hat_up
      where w is the SW grid-ratio conversion weight from Params (user-selected
      3:1..12:1 equivalent, NOT a calibration). In low-signal regions the
      effective weight is AUTOMATICALLY ATTENUATED (a smooth C-infinity logistic
      of the local signal) so scatter subtraction never boosts noise there
      (SWR-1102), and the output is clamped NON-NEGATIVE (a negative X-ray signal
      is physically impossible, SWR-1102). Both are a single deterministic path.

Mask handling (EC-5/EC-6): DEFECT / SATURATION / SATURATION_BAND / INTERPOLATION
pixel VALUES are replaced by a local valid-neighborhood estimate BEFORE the
downsample so extreme masked values cannot contaminate the low-frequency scatter
estimate. The mask substrate is never set or cleared and saturated pixels are
never "restored" (their clipped information is not reconstructed; the monotone
downward subtraction is not a restoration, SWR-602 precedent, REQ-VGRID-CONTRACT-6).

⚠P (SWR-1101/1103, CLAUDE.md T8, patent flag preserved): the SKS formulation is
claimed by an ACTIVE patent (US 11,911,202 and related). This module is
implemented on technical-necessity grounds; the patent claim comparison and
release gating are OUT OF the P1 SW scope and deferred to a release gate (see
.moai/specs/SPEC-VGRID-001/spec.md). No patent judgment is made here; the kernel
provenance is recorded in the history diagnostics for release-gate traceability.
The avoidance alternative (MC-precomputed-LUT kernel, SWR-1103) is reserved as a
builder-side substitution (metrics.scatter_kernel) with no change to this module.

@MX:ANCHOR: [AUTO] `process` is the virtual_grid pipeline stage entry point
invoked via the orchestrator registry (REQ-VGRID-CONTRACT-1/5).
@MX:REASON: fan_in is the orchestrator registry plus the harness and the
XDET-TC-017 CNR release gate; the SKS estimate, the non-negativity/low-signal
subtraction contract, and the CalibSet(SCATTER)-only kernel sourcing are what
those gates read against.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from common.calibset import CalibSet, K_SCATTER_AMP, K_SCATTER_SIGMA
from common.contract import Params
from common.pyramid import reduce_once
from common.xframe import HistoryEntry, MaskFlag, XFrame

MODULE_NAME = "virtual_grid"
MODULE_VERSION = "1.0.0"

# -- Params keys (all externalized; grades per SWR appendix A) ------------------
P_ITERATIONS = "vgrid_sks_iterations"  # SKS iteration count 2..3 [T] (SWR-1101)
P_DOWNSAMPLE_LEVELS = "vgrid_downsample_levels"  # reduce_once repeats; 3 -> x8 [T]
P_GRID_RATIO_W = "vgrid_grid_ratio_w"  # grid-ratio conversion weight [T]/[P] (SWR-1102)
P_LOWSIGNAL_THRESHOLD = "vgrid_lowsignal_threshold"  # low-signal attenuation midpoint [T]
P_LOWSIGNAL_SOFTNESS = "vgrid_lowsignal_softness"  # attenuation transition width [T]

# Mask bits whose pixel VALUE is replaced before downsampling so they do not
# contaminate the low-frequency scatter estimate (EC-5).
_EXCLUDE_ESTIMATE = np.uint8(
    MaskFlag.DEFECT | MaskFlag.INTERPOLATION | MaskFlag.SATURATION | MaskFlag.SATURATION_BAND
)


class VirtualGridError(ValueError):
    """Raised on a missing/degenerate scatter kernel or an invalid request."""


def _require(params: Params, key: str, cast=float):
    value = params.get(key)
    if value is None:
        raise VirtualGridError(f"virtual_grid: missing required parameter '{key}'")
    return cast(value)


# -- scatter-kernel resolution (REQ-VGRID-CALIB-1/2, ESTIMATE-2/3) -------------


def _resolve_kernel(calib: CalibSet) -> tuple[np.ndarray, np.ndarray]:
    """Resolve the dual-Gaussian (amp, sigma) from CalibSet(SCATTER); refuse on
    absent/degenerate.

    The kernel is the SOLE source (no default/nominal kernel branch exists,
    REQ-VGRID-ESTIMATE-3 / CALIB-2, SWR-000-5). A missing payload, wrong arity,
    non-finite coefficient, non-positive sigma/amplitude, or an SPR (sum of
    amplitudes) >= 1 that would diverge the SKS iteration is refused.
    """
    data = calib.data
    if K_SCATTER_AMP not in data or K_SCATTER_SIGMA not in data:
        raise VirtualGridError(
            "virtual_grid: CalibSet(SCATTER) is missing the dual-Gaussian "
            "(scatter_amp, scatter_sigma) payload; refusing to substitute a "
            "default kernel (SWR-000-5)"
        )
    amp = np.asarray(data[K_SCATTER_AMP], dtype=np.float64).reshape(-1)
    sigma = np.asarray(data[K_SCATTER_SIGMA], dtype=np.float64).reshape(-1)
    if amp.size != 2 or sigma.size != 2:
        raise VirtualGridError(
            "virtual_grid: degenerate scatter kernel — expected 2 amplitudes and "
            f"2 sigmas, got amp={amp.size}, sigma={sigma.size} (no substitution)"
        )
    if not np.all(np.isfinite(amp)) or not np.all(np.isfinite(sigma)):
        raise VirtualGridError(
            "virtual_grid: degenerate scatter kernel — non-finite coefficient "
            "(refusing default substitution)"
        )
    if np.any(sigma <= 0.0) or np.any(amp <= 0.0):
        raise VirtualGridError(
            f"virtual_grid: degenerate scatter kernel — sigmas and amplitudes "
            f"must be > 0, got amp={amp.tolist()}, sigma={sigma.tolist()}"
        )
    spr = float(amp.sum())
    if spr >= 1.0:
        raise VirtualGridError(
            f"virtual_grid: scatter kernel SPR (sum of amplitudes) = {spr:.6g} "
            ">= 1; the SKS iteration would diverge (spectral radius < 1 required, "
            "SWR-1101)"
        )
    return amp, sigma


# -- SKS estimation (SWR-1101) -------------------------------------------------


def _dual_gaussian_conv(image: np.ndarray, amp: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """Scatter operator S = conv(image, K) for the dual-Gaussian kernel K.

    Each Gaussian preserves the DC (sum = 1), so the operator's DC gain is
    amp[0]+amp[1] = SPR. Spatial-domain (scipy gaussian_filter), reflecting
    boundary (a smooth veiling has no edge discontinuity). NOT an FFT conv (P1
    forbids speed optimization; spatial keeps the boundary handling explicit).
    """
    return amp[0] * ndimage.gaussian_filter(
        image, sigma=float(sigma[0]), mode="reflect"
    ) + amp[1] * ndimage.gaussian_filter(image, sigma=float(sigma[1]), mode="reflect")


def _downsample(image: np.ndarray, levels: int) -> np.ndarray:
    """x2^levels downsample by reusing common.pyramid.reduce_once (SWR-000-9 (1)).

    reduce_once is the SHARED Burt-Adelson REDUCE (Gaussian low-pass + decimate);
    the downsample is NOT re-implemented in this module.
    """
    out = np.asarray(image, dtype=np.float64)
    for _ in range(int(levels)):
        out = reduce_once(out)
    return out


def _bilinear_upsample(image: np.ndarray, out_shape: tuple[int, int]) -> np.ndarray:
    """Bilinear-upsample `image` to `out_shape` (SWR-1102, distinct from the
    pyramid Gaussian expand).

    Uses a first-order (bilinear) interpolation on an aligned coordinate grid so
    the result matches the original frame resolution exactly regardless of the
    ceil-decimation shapes produced by reduce_once.
    """
    src = np.asarray(image, dtype=np.float64)
    sy, sx = src.shape
    ty, tx = int(out_shape[0]), int(out_shape[1])
    # Map each target pixel to source coordinates spanning [0, s-1] end-to-end.
    ys = np.linspace(0.0, sy - 1, ty) if ty > 1 else np.zeros(1)
    xs = np.linspace(0.0, sx - 1, tx) if tx > 1 else np.zeros(1)
    grid_y, grid_x = np.meshgrid(ys, xs, indexing="ij")
    coords = np.vstack([grid_y.reshape(-1), grid_x.reshape(-1)])
    up = ndimage.map_coordinates(src, coords, order=1, mode="nearest")
    return up.reshape(ty, tx)


def estimate_scatter(
    image: np.ndarray,
    amp: np.ndarray,
    sigma: np.ndarray,
    iterations: int,
    levels: int,
) -> np.ndarray:
    """Full-resolution SKS scatter estimate S_hat for `image` (SWR-1101).

    Downsamples to the x2^levels SKS domain (pyramid.reduce_once), runs the SKS
    fixed-point iteration (P_hat_0 = I_down; S_i = conv(P_hat_i, K);
    P_hat_{i+1} = I_down - S_i) `iterations` times, then bilinear-upsamples the
    final scatter estimate back to the input resolution. Public so the harness /
    tests can exercise the estimate in isolation.
    """
    i_down = _downsample(image, levels)
    p_hat = i_down
    s_down = _dual_gaussian_conv(p_hat, amp, sigma)
    for _ in range(int(iterations)):
        s_down = _dual_gaussian_conv(p_hat, amp, sigma)
        p_hat = i_down - s_down
    return _bilinear_upsample(s_down, image.shape)


# -- low-signal attenuation (SWR-1102) -----------------------------------------


def _lowsignal_weight(image: np.ndarray, w: float, threshold: float, softness: float) -> np.ndarray:
    """Per-pixel effective subtraction weight with low-signal auto-attenuation.

    w_eff(I) = w * 0.5 * (1 + tanh((I - threshold) / softness)): a smooth
    (C-infinity) logistic ramp that -> 0 well below `threshold` (suppressing the
    noise boost of scatter subtraction in low-signal regions, SWR-1102) and -> w
    well above it. The smoothness guarantees no boundary-discontinuity artifact at
    the threshold (EC-3). threshold/softness/w are all Params-externalized.
    """
    soft = max(float(softness), 1e-12)
    ramp = 0.5 * (1.0 + np.tanh((np.asarray(image, dtype=np.float64) - float(threshold)) / soft))
    return float(w) * ramp


# -- masked-pixel fill for estimation (EC-5) -----------------------------------


def _fill_masked(image: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Replace masked (invalid) pixel values with the global valid median so
    extreme defect/saturation values do not contaminate the low-frequency scatter
    estimate (EC-5, DENOISE mask-weighting precedent). The masked pixels' OWN
    outputs are unaffected (subtraction still applies to them; only the ESTIMATE
    input is cleaned)."""
    if valid.all():
        return np.asarray(image, dtype=np.float64)
    filled = np.asarray(image, dtype=np.float64).copy()
    if valid.any():
        filled[~valid] = float(np.median(filled[valid]))
    return filled


def _correct(
    pixel: np.ndarray,
    masks_u8: np.ndarray,
    amp: np.ndarray,
    sigma: np.ndarray,
    iterations: int,
    levels: int,
    w: float,
    threshold: float,
    softness: float,
) -> tuple[np.ndarray, dict[str, float]]:
    """SKS estimate -> weighted subtraction -> non-negativity for one buffer.

    Returns (corrected, diagnostics) where diagnostics carries the scatter
    fraction, the low-signal attenuation fraction, and the non-negativity clamp
    count (surfaced to the history chain, REQ-VGRID-CONTRACT-2).
    """
    z = np.asarray(pixel, dtype=np.float64)
    valid = (masks_u8 & _EXCLUDE_ESTIMATE) == 0
    est_input = _fill_masked(z, valid)
    s_hat = estimate_scatter(est_input, amp, sigma, iterations, levels)
    w_eff = _lowsignal_weight(z, w, threshold, softness)
    corrected = z - w_eff * s_hat
    # Non-negativity: a corrected pixel is never a physically-impossible negative
    # X-ray signal (SWR-1102). Single deterministic clamp — no arbitrary rescale.
    negative = corrected < 0.0
    clamp_count = int(np.count_nonzero(negative))
    corrected = np.where(negative, 0.0, corrected)

    denom = float(np.sum(np.abs(z))) or 1.0
    scatter_fraction = float(np.sum(np.abs(w_eff * s_hat))) / denom
    # Fraction of pixels whose weight was attenuated below ~99% of w (low-signal).
    attenuated = np.count_nonzero(w_eff < 0.99 * float(w)) if float(w) != 0.0 else 0
    atten_fraction = float(attenuated) / float(w_eff.size)
    diag = {
        "scatter_fraction": scatter_fraction,
        "lowsignal_attenuated_fraction": atten_fraction,
        "nonneg_clamp_count": float(clamp_count),
    }
    return corrected, diag


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """SKS scatter estimation + subtraction; return a new XFrame (input immutable).

    Sources the dual-Gaussian kernel from CalibSet(SCATTER) (sole source; refuse
    on absent/degenerate), runs the SKS estimate in the x8-downsampled domain
    (pyramid.reduce_once), subtracts w*S_hat with low-signal auto-attenuation and
    a non-negativity clamp, and appends processing meta + scalar diagnostics
    (iterations, applied w, scatter fraction, low-signal attenuation, non-neg
    clamp count, ⚠P kernel provenance) to the history chain (REQ-VGRID-CONTRACT-2).
    The mask substrate and noise model are preserved unchanged (REQ-VGRID-CONTRACT-6).
    """
    amp, sigma = _resolve_kernel(calib)
    iterations = _require(params, P_ITERATIONS, int)
    levels = _require(params, P_DOWNSAMPLE_LEVELS, int)
    w = _require(params, P_GRID_RATIO_W, float)
    threshold = _require(params, P_LOWSIGNAL_THRESHOLD, float)
    softness = _require(params, P_LOWSIGNAL_SOFTNESS, float)
    if iterations < 1:
        raise VirtualGridError(
            f"virtual_grid: '{P_ITERATIONS}' must be >= 1, got {iterations}"
        )
    if levels < 1:
        raise VirtualGridError(
            f"virtual_grid: '{P_DOWNSAMPLE_LEVELS}' must be >= 1, got {levels}"
        )

    masks_u8 = np.asarray(frame.masks, dtype=np.uint8)
    out_pixel, diag = _correct(
        frame.pixel, masks_u8, amp, sigma, iterations, levels, w, threshold, softness
    )

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64, _ = _correct(
            frame.pixel_f64, masks_u8, amp, sigma, iterations, levels, w, threshold, softness
        )

    new = frame.with_pixel(out_pixel.astype(frame.pixel.dtype), out_f64)
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra={
            "iterations": int(iterations),
            "downsample_levels": int(levels),
            "grid_ratio_w": float(w),
            "scatter_fraction": diag["scatter_fraction"],
            "lowsignal_attenuated_fraction": diag["lowsignal_attenuated_fraction"],
            "nonneg_clamp_count": diag["nonneg_clamp_count"],
            # ⚠P kernel provenance for release-gate patent traceability (the SW
            # makes no patent judgment; clearance is a release gate, out of P1).
            "sks_patent_flag": "US11911202-clearance-deferred",
            "kernel_provenance": str(calib.calibset_id),
        },
    )
    return new.record_history(entry)
