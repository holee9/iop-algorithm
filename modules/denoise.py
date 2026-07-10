"""VST + BM3D noise reduction (SWR-701~706, FR-C010, T5/WP5).

Three-stage, stateless, pure-functional denoise (SPEC-DENOISE-001):

    (1) GAT forward transform stabilizes the signal-dependent Poisson-Gaussian
        noise to (approximately) unit variance (SWR-702):
            f(z) = (2/alpha) * sqrt(alpha*z + (3/8)*alpha^2 + sigma^2)
        radicand < 0 pixels are clamped to 0.
    (2) BM3D two-stage denoiser (hard-threshold + Wiener) on the stabilized
        image, noise std sigma_BM3D = 1 (unit variance after GAT) * k_s (SWR-704).
        Own pure numpy/scipy golden implementation (decision 3, no new deps).
    (3) exact unbiased inverse (Makitalo & Foi 2011) via a precomputed LUT +
        interpolation (SWR-703). The asymptotic / algebraic inverse ((f/2)^2
        family) is PROHIBITED (REQ-DENOISE-INV-2, CLAUDE.md) — no such code path
        exists here; the LUT node values are the closed-form E{f(z)|lambda}
        integral evaluated numerically.

The noise model (alpha, sigma) is consumed from CalibSet(NOISE) — the sole
source. A missing / degenerate model (alpha <= 0, or only the XFrame default
(0, 0)) is refused with an explicit error (REQ-DENOISE-VST-2, SWR-000-5); there
is no default-substitution branch. The resolved (alpha, sigma) is written to the
output XFrame.noise for downstream T6 reuse (REQ-DENOISE-CONTRACT-2).

Mask weighting (REQ-DENOISE-BM3D-2, SWR-706): DEFECT / INTERPOLATION /
SATURATION / SATURATION_BAND pixels are excluded from block-matching statistics.
SATURATION / SATURATION_BAND pixel values are preserved unchanged (no
"restoration", SWR-602 precedent). No mask flag is set or cleared.

@MX:ANCHOR: [AUTO] `process` is the denoise pipeline stage entry point invoked
via the orchestrator registry (REQ-DENOISE-CONTRACT-1/6).
@MX:REASON: fan_in is the orchestrator registry plus the harness and the
XDET-TC-010/011 release gates; the VST round-trip unbiasedness and the
mask/preserve contract are what those gates read against.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from common.calibset import CalibSet, K_NOISE_ALPHA, K_NOISE_SIGMA
from common.contract import Params
from common.xframe import HistoryEntry, MaskFlag, NoiseModel, XFrame

MODULE_NAME = "denoise"
MODULE_VERSION = "1.0.0"

# -- Params keys (all externalized; grades per SWR appendix A) -----------------
P_METHOD = "denoise_method"  # "bm3d" (default) | "nlm" (SWR-704 [C] alt path)
P_STRENGTH = "denoise_strength_ks"  # k_s in {0.6, 0.8, 1.0} [T] (SWR-705)
# BM3D original parameters [L] (Dabov 2007 / SWR-704).
P_BLOCK = "denoise_bm3d_block"  # block edge (8)
P_STEP = "denoise_bm3d_step"  # reference-block grid step (3)
P_MAX_MATCH = "denoise_bm3d_max_match"  # max grouped blocks N2 (16)
P_SEARCH = "denoise_bm3d_search_window"  # search window edge Ns (39)
P_LAMBDA3D = "denoise_bm3d_lambda3d"  # hard-threshold factor lambda_3D (2.7)
P_KAISER_BETA = "denoise_bm3d_kaiser_beta"  # aggregation Kaiser beta (2.0)
P_MATCH_TAU_HARD = "denoise_bm3d_match_tau_hard"  # grouping distance thr, stage 1 [T]
P_MATCH_TAU_WIENER = "denoise_bm3d_match_tau_wiener"  # grouping distance thr, stage 2 [T]
# exact unbiased inverse LUT construction [L].
P_LUT_LAMBDA_MAX = "denoise_inv_lut_lambda_max"  # LUT upper signal bound [P]
P_LUT_NODES = "denoise_inv_lut_nodes"  # LUT node count [P]
P_LUT_GH_NODES = "denoise_inv_lut_gh_nodes"  # Gauss-Hermite nodes for sigma [P]
# NLM alternative path params (SWR-704 [C]); required only WHERE method == "nlm".
P_NLM_H = "denoise_nlm_h"  # filter strength h [P]
P_NLM_PATCH = "denoise_nlm_patch"  # patch edge [P]
P_NLM_WINDOW = "denoise_nlm_window"  # search window edge [P]

# Mask bits excluded from block-matching statistics (REQ-DENOISE-BM3D-2).
_EXCLUDE_MATCH = np.uint8(
    MaskFlag.DEFECT | MaskFlag.INTERPOLATION | MaskFlag.SATURATION | MaskFlag.SATURATION_BAND
)
# Mask bits whose pixel VALUE is preserved unchanged (no restoration, SWR-602).
_PRESERVE_VALUE = np.uint8(MaskFlag.SATURATION | MaskFlag.SATURATION_BAND)


class DenoiseError(ValueError):
    """Raised on a missing/degenerate noise model or an invalid denoise request."""


def _require(params: Params, key: str, cast=float):
    value = params.get(key)
    if value is None:
        raise DenoiseError(f"denoise: missing required parameter '{key}'")
    return cast(value)


def required_params(params: Params) -> tuple[str, ...]:
    """Selector-dependent required-Params manifest (SPEC-ERGO-001 REQUIRED_PARAMS).

    # @MX:NOTE: [AUTO] denoise's required key set depends on the method selector
    # (bm3d | nlm), so it is exposed as a function rather than a constant. It
    # reuses `_required_keys` (single source) so the manifest can never drift from
    # what `process` actually requires. Key NAMES only — no numeric values.
    """
    method = str(params.get(P_METHOD, "bm3d"))
    return _required_keys(method)


def _required_keys(method: str) -> tuple[str, ...]:
    """The Params keys a denoise run requires, given the selected method."""
    keys = [P_STRENGTH, P_LUT_LAMBDA_MAX, P_LUT_NODES, P_LUT_GH_NODES]
    if method == "bm3d":
        keys += [
            P_BLOCK, P_STEP, P_MAX_MATCH, P_SEARCH, P_LAMBDA3D,
            P_KAISER_BETA, P_MATCH_TAU_HARD, P_MATCH_TAU_WIENER,
        ]
    elif method == "nlm":
        keys += [P_NLM_H, P_NLM_PATCH, P_NLM_WINDOW]
    return tuple(keys)


def _require_present(params: Params, keys: tuple[str, ...]) -> None:
    """Fail fast with an explicit named error if any required key is absent."""
    missing = [k for k in keys if params.get(k) is None]
    if missing:
        raise DenoiseError(
            f"denoise: missing required parameter(s) {missing}"
        )


# -- noise model resolution (REQ-DENOISE-VST-1/2) ------------------------------


def _resolve_noise(calib: CalibSet) -> tuple[float, float]:
    """Resolve (alpha, sigma) from CalibSet(NOISE); refuse on absent/degenerate.

    The XFrame default NoiseModel(0, 0) is never used as a fallback — the
    CalibSet is the sole source (REQ-DENOISE-VST-2, SWR-000-5).
    """
    data = calib.data
    if K_NOISE_ALPHA not in data or K_NOISE_SIGMA not in data:
        raise DenoiseError(
            "denoise: CalibSet(NOISE) is missing the (alpha, sigma) payload; "
            "refusing to substitute a default noise model (SWR-000-5)"
        )
    alpha = float(np.asarray(data[K_NOISE_ALPHA]).reshape(-1)[0])
    sigma = float(np.asarray(data[K_NOISE_SIGMA]).reshape(-1)[0])
    if not np.isfinite(alpha) or not np.isfinite(sigma) or alpha <= 0.0 or sigma < 0.0:
        raise DenoiseError(
            f"denoise: degenerate noise model (alpha={alpha}, sigma={sigma}); "
            "alpha must be > 0 and sigma >= 0 (refusing default substitution)"
        )
    return alpha, sigma


# -- GAT forward (SWR-702) -----------------------------------------------------


def _gat_forward(z: np.ndarray, alpha: float, sigma: float) -> tuple[np.ndarray, float]:
    """Generalized Anscombe forward transform; clamp negative radicand to 0.

    Returns (transformed, clamp_rate) where clamp_rate is the fraction of pixels
    whose radicand fell below the domain (EC-6: no NaN propagation).
    """
    radicand = alpha * z + (3.0 / 8.0) * alpha * alpha + sigma * sigma
    clamped = radicand < 0.0
    clamp_rate = float(np.count_nonzero(clamped)) / float(radicand.size)
    radicand = np.where(clamped, 0.0, radicand)
    return (2.0 / alpha) * np.sqrt(radicand), clamp_rate


# -- exact unbiased inverse LUT (SWR-703, Makitalo-Foi 2011) -------------------


def _gauss_hermite(n: int) -> tuple[np.ndarray, np.ndarray]:
    """Physicists' Gauss-Hermite nodes/weights for integrating N(0, sigma^2)."""
    nodes, weights = np.polynomial.hermite.hermgauss(int(n))
    return nodes, weights


def _build_inverse_lut(
    alpha: float,
    sigma: float,
    lambda_max: float,
    n_nodes: int,
    gh_nodes: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Precompute the exact unbiased inverse LUT for GAT under the PG model.

    Generative model consistent with var(z) = alpha*lambda + sigma^2:
        z = alpha * k + eps,  k ~ Poisson(lambda/alpha),  eps ~ N(0, sigma^2).
    For a grid of signal means lambda, tabulate the forward-transform mean
        M(lambda) = E{ f(z) | lambda }
    by summing over the Poisson counts k and integrating the Gaussian eps with
    Gauss-Hermite quadrature (the closed-form integral evaluated numerically at
    the LUT nodes). M is monotone increasing, so the exact unbiased inverse of a
    denoised transform value D is lambda = interp(D, M_grid, lambda_grid).

    This is the ONLY inverse — there is no asymptotic ((f/2)^2) branch anywhere.

    lambda_max MUST be chosen >= the panel full-scale signal (e.g. the 16-bit
    range) so the LUT domain covers every unmasked pixel's transform value;
    process() validates this at entry and refuses (rather than silently clamping
    bright highlights) when the frame's GAT range exceeds M(lambda_max). The node
    grid is quadratically spaced (dense near 0, coarse near lambda_max) so the LUT
    stays accurate at low counts while still covering the full 16-bit range with a
    manageable node count.
    """
    t = np.linspace(0.0, 1.0, int(n_nodes))
    lambda_grid = float(lambda_max) * t * t  # quadratic: dense near 0
    gh_x, gh_w = _gauss_hermite(gh_nodes)
    # eps = sqrt(2)*sigma*gh_x with normalized weights gh_w/sqrt(pi).
    eps = np.sqrt(2.0) * sigma * gh_x
    w_eps = gh_w / np.sqrt(np.pi)

    const = (3.0 / 8.0) * alpha * alpha + sigma * sigma
    scale = 2.0 / alpha

    m_grid = np.empty_like(lambda_grid)
    for i, lam in enumerate(lambda_grid):
        mu = lam / alpha  # Poisson rate of the photon count k
        # Truncate the Poisson support generously (mean + margin*sqrt(mean)).
        k_max = int(np.ceil(mu + 12.0 * np.sqrt(mu + 1.0))) + 5
        k = np.arange(0, k_max + 1)
        log_pk = -mu + k * np.log(mu + 1e-300) - _log_factorial(k)
        pk = np.exp(log_pk)
        pk /= pk.sum()  # renormalize after truncation
        # radicand(k, eps) = alpha*(alpha*k + eps) + const, clamped at 0.
        rad = alpha * (alpha * k[:, None] + eps[None, :]) + const
        np.maximum(rad, 0.0, out=rad)
        f = scale * np.sqrt(rad)  # (k, gh)
        # Integrate eps then sum over k.
        ef_given_k = f @ w_eps
        m_grid[i] = float(pk @ ef_given_k)
    return m_grid, lambda_grid


def _log_factorial(k: np.ndarray) -> np.ndarray:
    from scipy.special import gammaln

    return gammaln(k + 1.0)


def _gat_inverse(
    d: np.ndarray, m_grid: np.ndarray, lambda_grid: np.ndarray
) -> np.ndarray:
    """Exact unbiased inverse: map denoised transform values back to signal.

    np.interp requires increasing xp; M(lambda) is monotone increasing, so
    interpolate d over (M_grid -> lambda_grid). Values below M(0) map to 0.
    """
    return np.interp(d, m_grid, lambda_grid)


# -- orthonormal Haar transforms (the 3D-transform domain, SWR-704) ------------


def _haar_forward_1d(a: np.ndarray, axis: int) -> np.ndarray:
    """Multi-level orthonormal Haar transform along `axis` (length power of 2)."""
    a = np.asarray(a, dtype=np.float64)
    a = np.moveaxis(a, axis, 0)
    n = a.shape[0]
    out = a.copy()
    length = n
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    while length > 1:
        block = out[:length]
        even = block[0:length:2]
        odd = block[1:length:2]
        approx = (even + odd) * inv_sqrt2
        detail = (even - odd) * inv_sqrt2
        out[: length // 2] = approx
        out[length // 2 : length] = detail
        length //= 2
    return np.moveaxis(out, 0, axis)


def _haar_inverse_1d(a: np.ndarray, axis: int) -> np.ndarray:
    """Inverse of _haar_forward_1d along `axis`."""
    a = np.asarray(a, dtype=np.float64)
    a = np.moveaxis(a, axis, 0)
    n = a.shape[0]
    out = a.copy()
    length = 2
    inv_sqrt2 = 1.0 / np.sqrt(2.0)
    while length <= n:
        approx = out[: length // 2]
        detail = out[length // 2 : length]
        even = (approx + detail) * inv_sqrt2
        odd = (approx - detail) * inv_sqrt2
        block = np.empty_like(out[:length])
        block[0:length:2] = even
        block[1:length:2] = odd
        out[:length] = block
        length *= 2
    return np.moveaxis(out, 0, axis)


def _haar3d_forward(group: np.ndarray) -> np.ndarray:
    """3D orthonormal Haar (2D intra-block + 1D across the group depth)."""
    g = _haar_forward_1d(group, axis=1)
    g = _haar_forward_1d(g, axis=2)
    g = _haar_forward_1d(g, axis=0)
    return g


def _haar3d_inverse(group: np.ndarray) -> np.ndarray:
    g = _haar_inverse_1d(group, axis=0)
    g = _haar_inverse_1d(g, axis=2)
    g = _haar_inverse_1d(g, axis=1)
    return g


def _kaiser2d(block: int, beta: float) -> np.ndarray:
    w = np.kaiser(block, beta)
    return np.outer(w, w)


# -- block matching + aggregation ----------------------------------------------


def _largest_pow2(n: int) -> int:
    if n < 1:
        return 1
    return 1 << (int(n).bit_length() - 1)


def _is_pow2(n: int) -> bool:
    return n >= 1 and (int(n) & (int(n) - 1)) == 0


def _fill_masked(noisy: np.ndarray, valid: np.ndarray, block: int) -> np.ndarray:
    """Replace masked (invalid) pixel values with a local valid-neighborhood
    estimate so extreme saturated/defect values never enter the Haar spectrum and
    bleed into neighboring blocks (REQ-DENOISE-BM3D-2). Each invalid pixel takes
    the block-median of the valid pixels in its surrounding block-sized window;
    isolated invalid pixels fall back to the global valid median. Masked pixels'
    own OUTPUTS are handled separately (value-preserved in _run)."""
    if valid.all():
        return noisy
    ny, nx = noisy.shape
    filled = noisy.copy()
    half = max(1, block) // 2
    global_med = float(np.median(noisy[valid])) if valid.any() else 0.0
    inv_ys, inv_xs = np.nonzero(~valid)
    for y, x in zip(inv_ys.tolist(), inv_xs.tolist()):
        y0, y1 = max(0, y - half), min(ny, y + half + 1)
        x0, x1 = max(0, x - half), min(nx, x + half + 1)
        win_valid = valid[y0:y1, x0:x1]
        if win_valid.any():
            filled[y, x] = float(np.median(noisy[y0:y1, x0:x1][win_valid]))
        else:
            filled[y, x] = global_med
    return filled


def _ref_positions(size: int, block: int, step: int) -> list[int]:
    if size < block:
        return []
    positions = list(range(0, size - block + 1, max(1, step)))
    last = size - block
    if positions[-1] != last:
        positions.append(last)
    return positions


def _match_group(
    ref_pos: tuple[int, int],
    signal: np.ndarray,
    windows: np.ndarray,
    valid_windows: np.ndarray,
    block: int,
    search: int,
    max_match: int,
    tau: float,
) -> np.ndarray:
    """Return candidate top-left positions grouped with the reference block.

    Distance is the mean squared difference over pixels valid in BOTH the
    reference and the candidate (REQ-DENOISE-BM3D-2 mask exclusion). Candidates
    are limited to a search window centred on the reference block. The group size
    is truncated to a power of two (<= max_match) for the Haar depth transform.
    """
    ny, nx = signal.shape
    ry, rx = ref_pos
    half = search // 2
    y0 = max(0, ry - half)
    y1 = min(ny - block, ry + half)
    x0 = max(0, rx - half)
    x1 = min(nx - block, rx + half)

    ref_block = windows[ry, rx]
    ref_valid = valid_windows[ry, rx]

    cand = windows[y0 : y1 + 1, x0 : x1 + 1]  # (H, W, block, block)
    cand_valid = valid_windows[y0 : y1 + 1, x0 : x1 + 1]
    both = ref_valid[None, None] & cand_valid
    counts = both.sum(axis=(2, 3))
    diff2 = ((cand - ref_block[None, None]) ** 2) * both
    with np.errstate(invalid="ignore", divide="ignore"):
        dist = diff2.sum(axis=(2, 3)) / np.maximum(counts, 1)
    # Only candidates that share enough valid pixels and fall within tau qualify.
    min_valid = max(1, (block * block) // 4)
    qualifies = (counts >= min_valid) & (dist <= tau)

    ys, xs = np.nonzero(qualifies)
    if ys.size == 0:
        return np.array([[ry, rx]], dtype=np.int64)  # self-group fallback
    d = dist[ys, xs]
    order = np.argsort(d)
    keep = _largest_pow2(min(max_match, order.size))
    order = order[:keep]
    ay = ys[order] + y0
    ax = xs[order] + x0
    return np.stack([ay, ax], axis=1)


def _bm3d(
    noisy: np.ndarray,
    valid: np.ndarray,
    sigma_bm3d: float,
    params: Params,
) -> np.ndarray:
    """Two-stage BM3D (hard-threshold basic estimate -> Wiener final estimate)."""
    block = _require(params, P_BLOCK, int)
    step = _require(params, P_STEP, int)
    max_match = _require(params, P_MAX_MATCH, int)
    search = _require(params, P_SEARCH, int)
    lambda3d = _require(params, P_LAMBDA3D, float)
    beta = _require(params, P_KAISER_BETA, float)
    tau_hard = _require(params, P_MATCH_TAU_HARD, float)
    tau_wiener = _require(params, P_MATCH_TAU_WIENER, float)

    # The orthonormal Haar depth transform requires power-of-two block and group
    # sizes; a non-power-of-two would otherwise fail deep inside numpy with a
    # cryptic shape error. Validate up front with an explicit, named error.
    if not _is_pow2(block):
        raise DenoiseError(
            f"denoise: '{P_BLOCK}' must be a power of two, got {block}"
        )
    if not _is_pow2(max_match):
        raise DenoiseError(
            f"denoise: '{P_MAX_MATCH}' (N2 group size) must be a power of two, "
            f"got {max_match}"
        )

    ny, nx = noisy.shape
    if ny < block or nx < block:
        return noisy.copy()  # too small to group — pass through (EC-3 spirit)

    # Masked pixel VALUES are replaced by a local valid-neighborhood estimate
    # before block stacking so they cannot contaminate the spectrum of the groups
    # they fall into (REQ-DENOISE-BM3D-2). Block-matching statistics already
    # exclude masked pixels; the fill affects only the aggregated estimate.
    filled = _fill_masked(noisy, valid, block)

    kaiser = _kaiser2d(block, beta)
    windows = sliding_window_view(filled, (block, block))
    valid_windows = sliding_window_view(valid, (block, block))
    positions = [
        (ry, rx)
        for ry in _ref_positions(ny, block, step)
        for rx in _ref_positions(nx, block, step)
    ]
    thr = lambda3d * sigma_bm3d
    sigma2 = sigma_bm3d * sigma_bm3d

    # ---- Stage 1: hard-threshold basic estimate ----
    num = np.zeros((ny, nx), dtype=np.float64)
    den = np.zeros((ny, nx), dtype=np.float64)
    for ry, rx in positions:
        coords = _match_group(
            (ry, rx), filled, windows, valid_windows, block, search, max_match, tau_hard
        )
        group = np.stack([filled[y : y + block, x : x + block] for y, x in coords])
        depth = _largest_pow2(group.shape[0])
        group = group[:depth]
        spec = _haar3d_forward(group)
        # Hard-threshold every coefficient EXCEPT the DC (spec[0,0,0]): standard
        # BM3D excludes the DC/mean from thresholding so the group mean survives.
        # This also guarantees nnz >= 1, preventing a zero estimate from crushing
        # dark low-count uniform regions (their mean is preserved).
        dc = spec[0, 0, 0]
        spec = np.where(np.abs(spec) < thr, 0.0, spec)
        spec[0, 0, 0] = dc
        nnz = int(np.count_nonzero(spec))
        estimate = _haar3d_inverse(spec)
        weight = 1.0 / max(nnz, 1)
        for j, (y, x) in enumerate(coords[:depth]):
            num[y : y + block, x : x + block] += weight * kaiser * estimate[j]
            den[y : y + block, x : x + block] += weight * kaiser
    basic = np.where(den > 0.0, num / np.maximum(den, 1e-12), noisy)

    # ---- Stage 2: Wiener filtering using the basic estimate as pilot ----
    basic_windows = sliding_window_view(basic, (block, block))
    num.fill(0.0)
    den.fill(0.0)
    for ry, rx in positions:
        coords = _match_group(
            (ry, rx), basic, basic_windows, valid_windows, block, search, max_match, tau_wiener
        )
        depth = _largest_pow2(coords.shape[0])
        coords = coords[:depth]
        noisy_group = np.stack([filled[y : y + block, x : x + block] for y, x in coords])
        basic_group = np.stack([basic[y : y + block, x : x + block] for y, x in coords])
        basic_spec = _haar3d_forward(basic_group)
        noisy_spec = _haar3d_forward(noisy_group)
        wiener = basic_spec**2 / (basic_spec**2 + sigma2)
        filtered = noisy_spec * wiener
        estimate = _haar3d_inverse(filtered)
        weight = 1.0 / max(float(np.sum(wiener**2)), 1e-12)
        for j, (y, x) in enumerate(coords):
            num[y : y + block, x : x + block] += weight * kaiser * estimate[j]
            den[y : y + block, x : x + block] += weight * kaiser
    final = np.where(den > 0.0, num / np.maximum(den, 1e-12), basic)
    return final


# -- NLM alternative path (SWR-704 [C], REQ-DENOISE-BM3D-4) --------------------


def _nlm(noisy: np.ndarray, valid: np.ndarray, params: Params, k_s: float) -> np.ndarray:
    """Non-local means denoiser (alternative path). Masked pixels excluded from
    patch-similarity statistics (same mask-weighting contract as BM3D).

    The filtering strength h is scaled by the preset k_s (SWR-705) so the NLM path
    honours the strength presets monotonically, matching the BM3D sigma*k_s wiring."""
    h = _require(params, P_NLM_H, float) * float(k_s)
    patch = _require(params, P_NLM_PATCH, int)
    window = _require(params, P_NLM_WINDOW, int)
    ny, nx = noisy.shape
    if ny < patch or nx < patch:
        return noisy.copy()
    rad_p = patch // 2
    rad_w = window // 2
    padded = np.pad(noisy, rad_p, mode="reflect")
    valid_pad = np.pad(valid, rad_p, mode="constant", constant_values=False)
    out = np.zeros_like(noisy, dtype=np.float64)
    wsum = np.zeros_like(noisy, dtype=np.float64)
    h2 = h * h
    for dy in range(-rad_w, rad_w + 1):
        for dx in range(-rad_w, rad_w + 1):
            ys = np.clip(np.arange(ny) + dy, 0, ny - 1)
            xs = np.clip(np.arange(nx) + dx, 0, nx - 1)
            shifted = noisy[np.ix_(ys, xs)]
            dist = np.zeros((ny, nx), dtype=np.float64)
            cnt = np.zeros((ny, nx), dtype=np.float64)
            for py in range(-rad_p, rad_p + 1):
                for px in range(-rad_p, rad_p + 1):
                    a = padded[
                        rad_p + py : rad_p + py + ny, rad_p + px : rad_p + px + nx
                    ]
                    ay = np.clip(np.arange(ny) + dy, 0, ny - 1)
                    ax = np.clip(np.arange(nx) + dx, 0, nx - 1)
                    b = a[np.ix_(ay, ax)]
                    va = valid_pad[
                        rad_p + py : rad_p + py + ny, rad_p + px : rad_p + px + nx
                    ]
                    vb = va[np.ix_(ay, ax)]
                    both = va & vb
                    dist += ((a - b) ** 2) * both
                    cnt += both
            with np.errstate(invalid="ignore", divide="ignore"):
                dist = dist / np.maximum(cnt, 1)
            weight = np.exp(-dist / h2)
            out += weight * shifted
            wsum += weight
    return np.where(wsum > 0.0, out / np.maximum(wsum, 1e-12), noisy)


# -- transformed-domain denoise dispatch ---------------------------------------


def _denoise_transformed(
    f: np.ndarray, valid: np.ndarray, params: Params, method: str, k_s: float
) -> np.ndarray:
    sigma_bm3d = 1.0 * k_s  # GAT stabilizes to unit variance; k_s scales strength
    if method == "nlm":
        return _nlm(f, valid, params, k_s)
    if method == "bm3d":
        return _bm3d(f, valid, sigma_bm3d, params)
    raise DenoiseError(f"denoise: unknown method '{method}' (expected 'bm3d' or 'nlm')")


def _run(
    pixel: np.ndarray,
    masks_u8: np.ndarray,
    alpha: float,
    sigma: float,
    params: Params,
    method: str,
    k_s: float,
    lut: tuple[np.ndarray, np.ndarray],
) -> tuple[np.ndarray, float]:
    """Full GAT -> denoise -> exact-inverse round trip for one buffer."""
    z = np.asarray(pixel, dtype=np.float64)
    f, clamp_rate = _gat_forward(z, alpha, sigma)
    valid = (masks_u8 & _EXCLUDE_MATCH) == 0
    m_grid, lambda_grid = lut
    # Refuse (rather than silently clamp/posterize highlights) when the inverse
    # LUT domain does not cover the frame's actual GAT range on unmasked pixels
    # (REQ-DENOISE-INV: np.interp clamps everything above M(lambda_max)).
    if valid.any():
        max_f = float(f[valid].max())
        m_max = float(m_grid[-1])
        if max_f > m_max:
            raise DenoiseError(
                f"denoise: inverse LUT domain too small — an unmasked pixel's GAT "
                f"value {max_f:.6g} exceeds M(lambda_max)={m_max:.6g} "
                f"(lambda_max={float(lambda_grid[-1]):.6g}); choose "
                f"'{P_LUT_LAMBDA_MAX}' >= panel full-scale (no silent clamp)"
            )
    d = _denoise_transformed(f, valid, params, method, k_s)
    out = _gat_inverse(d, m_grid, lambda_grid)
    # Preserve saturated / saturation-band pixel values (no restoration).
    preserve = (masks_u8 & _PRESERVE_VALUE) != 0
    out[preserve] = z[preserve]
    return out, clamp_rate


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Denoise via VST + BM3D; return a new XFrame (input treated immutable).

    Records the resolved (alpha, sigma) to the output XFrame.noise (T6 reuse,
    REQ-DENOISE-CONTRACT-2) and appends processing meta + scalar diagnostics
    (applied k_s, clamp rate, resolved alpha/sigma, method) to the history chain.
    """
    alpha, sigma = _resolve_noise(calib)
    method = str(params.get(P_METHOD, "bm3d"))
    # Fail fast: validate that every required denoise parameter is present BEFORE
    # any frame computation or LUT construction. When this stage runs as part of
    # PipelineDefinition.full() without a complete denoise Params bundle, the
    # failure is an explicit named DenoiseError at entry, not a cryptic mid-run
    # crash (SPEC-DENOISE-001 decision 2; complements the orchestrator's
    # CalibSet(NOISE) entry gate).
    _require_present(params, _required_keys(method))
    k_s = _require(params, P_STRENGTH, float)

    # Build the exact unbiased inverse LUT once (shared by both buffers).
    lambda_max = _require(params, P_LUT_LAMBDA_MAX, float)
    lut_nodes = _require(params, P_LUT_NODES, int)
    gh_nodes = _require(params, P_LUT_GH_NODES, int)
    lut = _build_inverse_lut(alpha, sigma, lambda_max, lut_nodes, gh_nodes)

    masks_u8 = np.asarray(frame.masks, dtype=np.uint8)
    out_pixel, clamp_rate = _run(
        frame.pixel, masks_u8, alpha, sigma, params, method, k_s, lut
    )

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64, _ = _run(
            frame.pixel_f64, masks_u8, alpha, sigma, params, method, k_s, lut
        )

    new = frame.with_pixel(out_pixel.astype(frame.pixel.dtype), out_f64)
    # Record the resolved noise model for downstream T6 (REQ-DENOISE-CONTRACT-2).
    new = replace(new, noise=NoiseModel(alpha=alpha, sigma=sigma))
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra={
            "method": method,
            "k_s": float(k_s),
            "clamp_rate": float(clamp_rate),
            "resolved_alpha": float(alpha),
            "resolved_sigma": float(sigma),
        },
    )
    return new.record_history(entry)
