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
    (3) DRC on the low-frequency component B = reconstruction of the top-K coarsest
        levels (residual + the K coarsest detail bands, K = mse_drc_low_levels [T],
        SWR-804 "B = sum of multiple top levels"): B' = B_mid + (B - B_mid)*gamma_DRC
        (gamma_DRC < 1). B_mid is Params if provided else the robust mean of B
        (common.robust_stats); the FINER detail bands are left uncompressed so bone
        and soft tissue are jointly visualized. Compressing only the coarsest
        residual (a single band) would leave a large-scale gradient spanning the
        top detail levels uncompressed — hence the multi-level base.
    (4) reconstruct, then percentile [p0.1, p99.9] linear range normalization
        ("linear cutoff", SWR-805) excluding SATURATION / SATURATION_BAND pixels
        from the percentile estimate (common.robust masking via common.mask_ops).

An optional soft-clip alternative modulation (REQ-POST-MSE-5, ⚠P patent flag) is
selected by Params; when unselected the power-law base form is used.

Mask contract (REQ-POST-CONTRACT-6): SATURATION / SATURATION_BAND pixels are
preserved in the OUTPUT DOMAIN — they are mapped to the normalized domain maximum
(1.0) rather than passed through as raw detector DN. "Preservation" means no
fabricated detail is injected at those pixels (SWR-602: no restoration), NOT a
raw-DN passthrough: injecting thousands-scale DN into a [0,1]-normalized image
would blow out downstream statistics. The SATURATION mask flags are kept unchanged
(no flag is set or cleared). Every tunable is externalized via Params (no
hardcoding); [P]/[T] grades are annotated per SWR appendix A/A-2 (⚠P on the
SWR-802 modulation form).

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
P_DRC_LOW_LEVELS = "mse_drc_low_levels"  # K coarsest detail bands folded into B [T] (SWR-804)
P_NORM_PLOW = "mse_norm_plow"  # low percentile p0.1 [ungraded] (SWR-805)
P_NORM_PHIGH = "mse_norm_phigh"  # high percentile p99.9 [ungraded] (SWR-805)
# soft-clip alternative modulation params (⚠P, REQ-POST-MSE-5); only WHERE method == "soft_clip".
P_SOFTCLIP_GAIN = "mse_softclip_gain"  # low-contrast linear gain [T]
P_SOFTCLIP_KNEE = "mse_softclip_knee"  # saturation knee (coefficient magnitude) [T]

# Params keys always required by a MSE/DRC run (raise-on-missing), independent of
# the modulation method. Key NAMES only (SPEC-ERGO-001 REQUIRED_PARAMS manifest).
_REQUIRED_COMMON: tuple[str, ...] = (
    P_LEVELS,
    P_GAMMA,
    P_NOISE_BETA,
    P_DRC_GAMMA,
    P_NORM_PLOW,
    P_NORM_PHIGH,
)


def _required_keys(method: str) -> tuple[str, ...]:
    """Method-specific required Params key set (power_law | soft_clip)."""
    if method == "soft_clip":
        return _REQUIRED_COMMON + (P_SOFTCLIP_GAIN, P_SOFTCLIP_KNEE)
    # power_law (default) additionally needs the per-level exponent sequence.
    return _REQUIRED_COMMON + (P_POWER,)


def required_params(params: Params) -> tuple[str, ...]:
    """Selector-dependent required-Params manifest (SPEC-ERGO-001 REQUIRED_PARAMS).

    # @MX:NOTE: [AUTO] mse's required key set depends on the method selector
    # (power_law | soft_clip), so it is exposed as a function. Derived from the
    # module's own P_* constants — key NAMES only, never numeric values.
    """
    method = str(params.get(P_METHOD, "power_law"))
    return _required_keys(method)

# Mask bits excluded from the SWR-805 percentile estimate (EC-4) and mapped to the
# normalized domain maximum in the output (no raw-DN passthrough, no restoration;
# SWR-602 / REQ-POST-CONTRACT-6).
_SATURATION = np.uint8(MaskFlag.SATURATION | MaskFlag.SATURATION_BAND)

# Normalized output domain maximum: SATURATION pixels are pinned here so they read
# as "brightest, no fabricated detail" rather than corrupting the [0,1] range with
# raw detector DN.
_DOMAIN_MAX = 1.0

# DRC default coarsest-level count folded into the low-frequency base B (SWR-804
# "sum of multiple top levels"); externalized via P_DRC_LOW_LEVELS, this is only
# the fallback when the caller omits the [T] parameter.
_DRC_LOW_LEVELS_DEFAULT = 2


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
    decisions: dict[str, float] | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    """Full MSE + DRC + normalization for one buffer; returns (out, diagnostics).

    Data-dependent scalar decisions (DRC B_mid, normalization [lo, hi]) are taken
    from `decisions` when provided (the authoritative f32 path) so the f64 buffer
    applies the SAME classification/threshold choices and differs only in
    arithmetic — never in which decisions were made (equivalence gate TC-021).
    """
    z = np.asarray(pixel, dtype=np.float64)
    levels = _require(params, P_LEVELS, int)
    beta = _require(params, P_NOISE_BETA, float)
    drc_gamma = _require(params, P_DRC_GAMMA, float)
    plow = _require(params, P_NORM_PLOW, float)
    phigh = _require(params, P_NORM_PHIGH, float)

    feasible = pyramid.max_feasible_levels(z.shape)
    if levels > feasible:
        raise MseError(
            f"mse: requested {levels} pyramid levels but frame {tuple(z.shape)} "
            f"supports at most {feasible}; honor the parameter or enlarge the frame "
            f"(no silent truncation, SWR-000-5)"
        )
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

    # Per-level noise variance GAIN from white input to each Laplacian band,
    # propagated exactly through the REDUCE/EXPAND chain (autocorrelation algebra,
    # SWR-803). This replaces the naive independent-noise (sum(k^2)^k) model that
    # underestimates correlated noise badly at coarse levels.
    band_gains = pyramid.laplacian_band_noise_gains(z.shape, n_bands)

    # Gaussian levels track the local signal for the noise-variance propagation.
    # G_0 = z; G_{k+1} = reduce(G_k). The bandpass detail band k shares G_k's shape.
    modulated: list[np.ndarray] = []
    g_level = z
    for k in range(n_bands):
        c = pyr[k]
        # Local input noise variance (alpha*|G_k| + sigma^2) scaled by the exact
        # white-input -> band-k variance gain (correlated-noise propagation).
        base_var = alpha * np.abs(g_level) + sigma * sigma
        sigma_l_sq = base_var * band_gains[k]
        if method == "power_law":
            c_mod = _modulate_power_law(c, gammas[k], powers[k])
        else:
            c_mod = _modulate_soft_clip(c, gain, knee) * gammas[k]
        g = _noise_gate(c, sigma_l_sq, beta)
        modulated.append((1.0 - g) * c + g * c_mod)
        g_level = pyramid.reduce_once(g_level)

    # DRC on the low-frequency base B = reconstruction of the top-K coarsest levels
    # (residual + the K coarsest detail bands), NOT just the residual — a
    # large-scale gradient spanning the top detail levels must be compressed too
    # (SWR-804 "sum of multiple top levels"). B_mid: Params else robust mean.
    residual = np.asarray(pyr[-1], dtype=np.float64)
    k_low = int(params.get(P_DRC_LOW_LEVELS, _DRC_LOW_LEVELS_DEFAULT))
    k_low = max(1, min(k_low, n_bands))  # honor >=1 coarse band; clamp to available
    # Reconstruct the low-frequency base by folding the K coarsest detail bands
    # (indices [n_bands-k_low, n_bands-1]) back onto the residual, stopping at the
    # resolution of the finest included level.
    base = residual
    for k in range(n_bands - 1, n_bands - 1 - k_low, -1):
        base = modulated[k] + pyramid._expand(base, modulated[k].shape)
    b_mid_param = params.get(P_DRC_BMID)
    if decisions is not None:
        b_mid = float(decisions["b_mid"])
    elif b_mid_param is not None:
        b_mid = float(b_mid_param)
    else:
        b_mid = robust_stats.robust_mean(base)
    compressed_base = b_mid + (base - b_mid) * drc_gamma
    lowband_range = float(np.ptp(base))
    compression_rate = (
        1.0 - float(np.ptp(compressed_base)) / lowband_range
        if lowband_range > 0.0
        else 0.0
    )
    # Reconstruct the remaining (finer, uncompressed) detail bands on the
    # compressed base.
    recon = compressed_base
    for k in range(n_bands - 1 - k_low, -1, -1):
        recon = modulated[k] + pyramid._expand(recon, modulated[k].shape)

    # SWR-805 percentile range normalization ("linear cutoff") excluding
    # saturation pixels from the percentile estimate (EC-4).
    if decisions is not None:
        lo, hi = float(decisions["norm_low"]), float(decisions["norm_high"])
    else:
        valid = (masks_u8 & _SATURATION) == 0
        sample = recon[valid] if valid.any() else recon
        lo = float(np.percentile(sample, plow))
        hi = float(np.percentile(sample, phigh))
        if hi <= lo:
            hi = lo + 1.0  # degenerate flat region — avoid division by zero
    out = np.clip((recon - lo) / (hi - lo), 0.0, 1.0)

    # Preserve saturation pixels IN THE OUTPUT DOMAIN: pin to the normalized domain
    # maximum (no fabricated detail; no raw-DN passthrough). Injecting raw DN
    # (thousands) into a [0,1] image would corrupt downstream statistics
    # (SWR-602 no-restoration / REQ-POST-CONTRACT-6).
    preserve = (masks_u8 & _SATURATION) != 0
    out[preserve] = _DOMAIN_MAX

    diagnostics = {
        "gamma_mean": float(np.mean(gammas)),
        "drc_gamma": float(drc_gamma),
        "drc_low_levels": float(k_low),
        "drc_compression_rate": float(compression_rate),
        "b_mid": float(b_mid),
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
        # Reuse the authoritative f32 threshold decisions so the f64 buffer differs
        # only arithmetically, not in classification (defect: divergent decisions).
        decisions = {
            "b_mid": diag["b_mid"],
            "norm_low": diag["norm_low"],
            "norm_high": diag["norm_high"],
        }
        out_f64, _ = _run(
            frame.pixel_f64, masks_u8, alpha, sigma, params, method, decisions
        )

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
