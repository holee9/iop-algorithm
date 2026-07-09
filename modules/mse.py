"""Multi-scale contrast enhancement (MSE) + DRC (SWR-801~805, T6/WP6).

Stateless, pure-functional display post-processing (SPEC-POST-001). Four stages:

    (1) Laplacian pyramid L-level decomposition via common.pyramid (SWR-801,
        kernel 5x5 [1 4 6 4 1]/16; L=7 @3072 is the [T] default via Params).
    (2) per-level power-law band modulation c' = gamma_l * sign(c) * |c|^p_l
        (SWR-802, p_l in (0,1] relatively amplifies small detail) combined with a
        local noise gate g = c^2 / (c^2 + beta * sigma_l^2) (SWR-803) so that
        sub-noise coefficients are NOT amplified. The gate blends the modulated
        band back toward the original coefficient where noise dominates:
            out = (1 - g) * c + g * c'.
        sigma_l is propagated from the input XFrame.noise (alpha, sigma) written
        by the upstream T5 denoise stage; a missing/degenerate model is refused
        (REQ-POST-MSE-4, SWR-000-5) — no default substitution.
    (3) DRC on the coarse residual (lowest band) B' = B_mid + (B - B_mid)*gamma_DRC
        (SWR-804, gamma_DRC < 1). B_mid is Params if provided else the robust mean
        of B (common.robust_stats); the detail bands are left uncompressed so bone
        and soft tissue are jointly visualized.
    (4) reconstruct, then percentile [p0.1, p99.9] linear range normalization
        ("linear cutoff", SWR-805) excluding SATURATION / SATURATION_BAND pixels
        from the percentile estimate (common.robust masking via common.mask_ops).

An optional soft-clip alternative modulation (REQ-POST-MSE-5, ⚠P patent flag) is
selected by Params; when unselected the power-law base form is used.

Mask contract (REQ-POST-CONTRACT-6): saturation pixel VALUES are preserved
unchanged (no restoration, SWR-602 precedent, denoise precedent); no mask flag is
set or cleared. Every tunable is externalized via Params (no hardcoding); [P]/[T]
grades are annotated per SWR appendix A/A-2 (⚠P on the SWR-802 modulation form).

@MX:ANCHOR: [AUTO] `process` is the mse pipeline stage entry point invoked via the
orchestrator registry (REQ-POST-CONTRACT-1/5).
@MX:REASON: fan_in is the orchestrator registry plus the harness and the
XDET-TC-012 IQA/MTF-guardrail gate; the pyramid round-trip fidelity, the noise
gate, and the mask/preserve contract are what that gate reads against.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibSet
from common.contract import Params
from common import pyramid, robust_stats
from common.xframe import HistoryEntry, MaskFlag, XFrame

MODULE_NAME = "mse"
MODULE_VERSION = "1.0.0"

# -- Params keys (all externalized; grades per SWR appendix A/A-2) --------------
P_LEVELS = "mse_levels"  # Laplacian level count L (=7 @3072) [T] (SWR-801)
P_METHOD = "mse_method"  # "power_law" (default) | "soft_clip" (⚠P alt, SWR-802)
P_GAMMA = "mse_gamma"  # per-level gain gamma_l (list, broadcast) [T] (SWR-802)
P_POWER = "mse_power"  # per-level exponent p_l in (0,1] (list) [T] (SWR-802)
P_NOISE_BETA = "mse_noise_beta"  # noise-gate strength beta [T] (SWR-803, appendix-A request)
P_DRC_GAMMA = "mse_drc_gamma"  # DRC low-band compression gamma_DRC (<1) [ungraded] (SWR-804)
P_DRC_BMID = "mse_drc_bmid"  # DRC mid reference B_mid; Params else robust mean (SWR-804)
P_NORM_PLOW = "mse_norm_plow"  # low percentile p0.1 [ungraded] (SWR-805)
P_NORM_PHIGH = "mse_norm_phigh"  # high percentile p99.9 [ungraded] (SWR-805)
# soft-clip alternative modulation params (⚠P, REQ-POST-MSE-5); only WHERE method == "soft_clip".
P_SOFTCLIP_GAIN = "mse_softclip_gain"  # low-contrast linear gain [T]
P_SOFTCLIP_KNEE = "mse_softclip_knee"  # saturation knee (coefficient magnitude) [T]

# Mask bits excluded from the SWR-805 percentile estimate (EC-4) and whose pixel
# VALUE is preserved unchanged (no restoration, SWR-602 / REQ-POST-CONTRACT-6).
_SATURATION = np.uint8(MaskFlag.SATURATION | MaskFlag.SATURATION_BAND)

# Per-level Gaussian noise-variance attenuation factor: independent per-pixel
# noise variance is scaled by sum(kernel2d^2) at each REDUCE. kernel_1d =
# [1 4 6 4 1]/16 -> sum(k^2) = 70/256; sum over the 2D separable kernel is that
# squared. This propagates (alpha*signal + sigma^2) to each pyramid level (SWR-803).
_K1D = np.array([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0
_VAR_ATTEN_PER_LEVEL = float(np.sum(_K1D**2) ** 2)  # (70/256)^2


class MseError(ValueError):
    """Raised on a missing/degenerate noise model or an invalid MSE request."""


def _require(params: Params, key: str, cast=float):
    value = params.get(key)
    if value is None:
        raise MseError(f"mse: missing required parameter '{key}'")
    return cast(value)


def _resolve_noise(frame: XFrame) -> tuple[float, float]:
    """Consume (alpha, sigma) from the input XFrame.noise; refuse if degenerate.

    The upstream T5 denoise stage writes the resolved model to XFrame.noise
    (SPEC-DENOISE-001 CONTRACT-2). The default NoiseModel(0, 0) or alpha <= 0 is
    refused — no default substitution (REQ-POST-MSE-4, SWR-000-5).
    """
    noise = frame.noise
    alpha = float(getattr(noise, "alpha", 0.0))
    sigma = float(getattr(noise, "sigma", 0.0))
    if not np.isfinite(alpha) or not np.isfinite(sigma) or alpha <= 0.0 or sigma < 0.0:
        raise MseError(
            f"mse: absent/degenerate input noise model (alpha={alpha}, sigma={sigma}); "
            "T5 denoise must record (alpha, sigma) on XFrame.noise "
            "(refusing default substitution, SWR-000-5)"
        )
    return alpha, sigma


def _level_sequence(params: Params, key: str, n_bands: int) -> list[float]:
    """Broadcast a per-level Params value to the n_bands detail levels.

    Accepts a scalar (applied to every level) or a sequence (per level, last value
    reused if shorter than the pyramid).
    """
    raw = params.get(key)
    if raw is None:
        raise MseError(f"mse: missing required parameter '{key}'")
    if np.isscalar(raw):
        return [float(raw)] * n_bands
    seq = [float(v) for v in raw]
    if not seq:
        raise MseError(f"mse: parameter '{key}' is an empty sequence")
    return [seq[min(i, len(seq) - 1)] for i in range(n_bands)]


def _modulate_power_law(c: np.ndarray, gamma: float, p: float) -> np.ndarray:
    """Power-law band modulation c' = gamma * sign(c) * |c|^p (SWR-802)."""
    return gamma * np.sign(c) * np.power(np.abs(c), p)


def _modulate_soft_clip(
    c: np.ndarray, gain: float, knee: float
) -> np.ndarray:
    """Soft-clip alternative modulation (⚠P, REQ-POST-MSE-5, SWR-802 preliminary).

    Piecewise form: linear low-contrast gain that gently saturates past a knee
    (tanh), covering the "linear cutoff" reading. Under the same noise-gating /
    DRC / normalization contract as the power-law base form.
    """
    knee = max(knee, 1e-12)
    return gain * knee * np.tanh(c / knee)


def _noise_gate(c: np.ndarray, sigma_l_sq: np.ndarray, beta: float) -> np.ndarray:
    """Amplification-suppression gate g = c^2 / (c^2 + beta * sigma_l^2) (SWR-803)."""
    c2 = c * c
    denom = c2 + beta * sigma_l_sq
    return np.where(denom > 0.0, c2 / np.maximum(denom, 1e-300), 0.0)


def _run(
    pixel: np.ndarray,
    masks_u8: np.ndarray,
    alpha: float,
    sigma: float,
    params: Params,
    method: str,
) -> tuple[np.ndarray, dict[str, float]]:
    """Full MSE + DRC + normalization for one buffer; returns (out, diagnostics)."""
    z = np.asarray(pixel, dtype=np.float64)
    levels = _require(params, P_LEVELS, int)
    beta = _require(params, P_NOISE_BETA, float)
    drc_gamma = _require(params, P_DRC_GAMMA, float)
    plow = _require(params, P_NORM_PLOW, float)
    phigh = _require(params, P_NORM_PHIGH, float)

    pyr = pyramid.build_pyramid(z, levels=levels)
    n_bands = len(pyr) - 1  # detail bands (excl. residual)

    gammas = _level_sequence(params, P_GAMMA, n_bands)
    if method == "power_law":
        powers = _level_sequence(params, P_POWER, n_bands)
    elif method == "soft_clip":
        gain = _require(params, P_SOFTCLIP_GAIN, float)
        knee = _require(params, P_SOFTCLIP_KNEE, float)
    else:
        raise MseError(
            f"mse: unknown method '{method}' (expected 'power_law' or 'soft_clip')"
        )

    # Gaussian levels track the local signal for the noise-variance propagation.
    # G_0 = z; G_{k+1} = reduce(G_k). The bandpass detail band k shares G_k's shape.
    modulated: list[np.ndarray] = []
    g_level = z
    for k in range(n_bands):
        c = pyr[k]
        # Local noise variance at level k: (alpha*|G_k| + sigma^2) attenuated by
        # the low-pass energy at each prior REDUCE (independent-noise propagation).
        base_var = alpha * np.abs(g_level) + sigma * sigma
        sigma_l_sq = base_var * (_VAR_ATTEN_PER_LEVEL**k)
        if method == "power_law":
            c_mod = _modulate_power_law(c, gammas[k], powers[k])
        else:
            c_mod = _modulate_soft_clip(c, gain, knee) * gammas[k]
        g = _noise_gate(c, sigma_l_sq, beta)
        modulated.append((1.0 - g) * c + g * c_mod)
        g_level = pyramid._reduce(g_level)

    # DRC on the coarse residual (lowest band) — bone/soft-tissue joint dynamic
    # range compression (SWR-804). B_mid: Params else robust mean (single rule).
    residual = np.asarray(pyr[-1], dtype=np.float64)
    b_mid_param = params.get(P_DRC_BMID)
    b_mid = (
        float(b_mid_param)
        if b_mid_param is not None
        else robust_stats.robust_mean(residual)
    )
    compressed_residual = b_mid + (residual - b_mid) * drc_gamma
    lowband_range = float(np.ptp(residual))
    compression_rate = (
        1.0 - float(np.ptp(compressed_residual)) / lowband_range
        if lowband_range > 0.0
        else 0.0
    )

    recon = pyramid.reconstruct_pyramid(modulated + [compressed_residual])

    # SWR-805 percentile range normalization ("linear cutoff") excluding
    # saturation pixels from the percentile estimate (EC-4).
    valid = (masks_u8 & _SATURATION) == 0
    sample = recon[valid] if valid.any() else recon
    lo = float(np.percentile(sample, plow))
    hi = float(np.percentile(sample, phigh))
    if hi <= lo:
        hi = lo + 1.0  # degenerate flat region — avoid division by zero
    out = np.clip((recon - lo) / (hi - lo), 0.0, 1.0)

    # Preserve saturation pixel VALUES unchanged (no restoration, SWR-602 /
    # REQ-POST-CONTRACT-6; denoise precedent).
    preserve = (masks_u8 & _SATURATION) != 0
    out[preserve] = z[preserve]

    diagnostics = {
        "gamma_mean": float(np.mean(gammas)),
        "drc_gamma": float(drc_gamma),
        "drc_compression_rate": float(compression_rate),
        "norm_low": lo,
        "norm_high": hi,
    }
    return out, diagnostics


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Multi-scale enhancement + DRC; return a new XFrame (input treated immutable).

    Consumes (alpha, sigma) from the input XFrame.noise, appends processing meta +
    scalar diagnostics (gamma summary, beta, gamma_DRC, DRC compression rate,
    normalization range) to the history chain (REQ-POST-CONTRACT-2).
    """
    alpha, sigma = _resolve_noise(frame)
    method = str(params.get(P_METHOD, "power_law"))
    beta = _require(params, P_NOISE_BETA, float)

    masks_u8 = np.asarray(frame.masks, dtype=np.uint8)
    out_pixel, diag = _run(frame.pixel, masks_u8, alpha, sigma, params, method)

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64, _ = _run(frame.pixel_f64, masks_u8, alpha, sigma, params, method)

    new = frame.with_pixel(out_pixel.astype(frame.pixel.dtype), out_f64)
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra={
            "method": method,
            "noise_beta": float(beta),
            "resolved_alpha": float(alpha),
            "resolved_sigma": float(sigma),
            **diag,
        },
    )
    return new.record_history(entry)
