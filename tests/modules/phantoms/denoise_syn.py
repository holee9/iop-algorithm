"""Synthetic Poisson-Gaussian phantoms + CalibSet(NOISE) builders for T5.

Known-(alpha, sigma) injectors for the denoise module and its VST round-trip
gate. Every constant is externalized; EV thresholds live here as
external-injected values (measurement != judgment, EVAL v1.1 legs).

Poisson-Gaussian generative model (consistent with var = alpha*lambda + sigma^2,
SWR-701):
    z = alpha * k + eps,  k ~ Poisson(lambda/alpha),  eps ~ N(0, sigma^2).

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
from common.contract import Params
from common.xframe import MaskFlag, new_frame

# Known synthetic noise model ([B] in production; injected here).
ALPHA = 2.0
SIGMA = 3.0

# External-injected EV thresholds (EVAL v1.1 XDET-EV-201 / EV-102 legs); tests
# compare engine outputs against these — the module/engine never embed them.
EV = {
    "ev201_snr_improve_min_frac": 0.20,  # SNR improvement >= +20%
    "ev102_mtf_retention_min": 0.90,  # MTF@Nyquist retention >= 90%
    "ev102_srb_degrade_max_frac": 0.10,  # SRb degradation <= 10%
}

# VST round-trip unbiasedness thresholds ([T]); external-injected.
EPS_UNBIAS = 0.06  # normalized bias ceiling max_j bias(lambda_j)/max(lambda_j, floor)
# End-to-end (full process(), BM3D active) patch-mean unbiasedness bound ([T]);
# looser than the transform-domain exact-inverse property because it also folds
# in the BM3D estimator variance/bias on a finite patch.
EPS_UNBIAS_E2E = 0.12
LAMBDA_FLOOR = 5.0  # low-count normalization floor (prevents lambda-division blowup)

_BM3D_PARAMS = {
    # BM3D original parameters [L] (Dabov 2007 / SWR-704), injected (no hardcode).
    "denoise_bm3d_block": 8,
    "denoise_bm3d_step": 3,
    "denoise_bm3d_max_match": 16,
    "denoise_bm3d_search_window": 39,
    "denoise_bm3d_lambda3d": 2.7,
    "denoise_bm3d_kaiser_beta": 2.0,
    "denoise_bm3d_match_tau_hard": 2500.0,  # [T] grouping distance, stage 1
    "denoise_bm3d_match_tau_wiener": 2500.0,  # [T] grouping distance, stage 2
    # exact unbiased inverse LUT construction [L]/[P]. lambda_max covers the
    # 16-bit panel full-scale so the inverse never silently clamps highlights
    # (SPEC-DENOISE-001; quadratic node spacing keeps low-count accuracy).
    "denoise_inv_lut_lambda_max": 65535.0,
    "denoise_inv_lut_nodes": 2048,
    "denoise_inv_lut_gh_nodes": 24,
}


def denoise_params(k_s: float = 0.8, method: str = "bm3d", **overrides) -> Params:
    """Denoise-stage Params: BM3D originals + strength preset k_s [T]."""
    values = dict(_BM3D_PARAMS)
    values["denoise_strength_ks"] = k_s
    values["denoise_method"] = method
    # NLM alternative-path params (only consumed WHERE method == "nlm").
    values.setdefault("denoise_nlm_h", 30.0)
    values.setdefault("denoise_nlm_patch", 5)
    values.setdefault("denoise_nlm_window", 11)
    values.update(overrides)
    return Params(values=values)


def noise_calib(
    shape: tuple[int, int],
    alpha: float = ALPHA,
    sigma: float = SIGMA,
    *,
    panel_id: str = "PANEL-A",
    kind: CalibKind = CalibKind.NOISE,
    valid_from: str = "2026-01-01",
    valid_until: str = "2027-01-01",
) -> CalibSet:
    """A valid CalibSet(NOISE) carrying the (alpha, sigma) payload."""
    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(shape),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=kind,
        data={
            K_NOISE_ALPHA: np.asarray(alpha, dtype=np.float64),
            K_NOISE_SIGMA: np.asarray(sigma, dtype=np.float64),
        },
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
    )


def sample_pg(
    lam: np.ndarray | float, alpha: float, sigma: float, rng: np.random.Generator
) -> np.ndarray:
    """Draw Poisson-Gaussian samples with mean `lam` and var alpha*lam+sigma^2."""
    lam_arr = np.asarray(lam, dtype=np.float64)
    k = rng.poisson(np.maximum(lam_arr, 0.0) / alpha)
    eps = rng.normal(0.0, sigma, size=lam_arr.shape)
    return alpha * k + eps


def asymptotic_inverse(f: np.ndarray, alpha: float, sigma: float) -> np.ndarray:
    """Algebraic/asymptotic inverse of the GAT forward (TEST-LOCAL ONLY).

    This is the PROHIBITED ((f/2)^2 family) inverse computed locally in the test
    for the EC-2 negative control — it is NOT a module code path
    (REQ-DENOISE-INV-2; module exposes only the exact LUT inverse).
    """
    rad = (alpha * f / 2.0) ** 2
    return (rad - (3.0 / 8.0) * alpha * alpha - sigma * sigma) / alpha


@dataclass(frozen=True)
class EdgePhantom:
    clean: np.ndarray
    noisy: np.ndarray


def make_uniform_field(
    shape: tuple[int, int] = (96, 96),
    level: float = 400.0,
    alpha: float = ALPHA,
    sigma: float = SIGMA,
    seed: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """Flat field at `level` counts: (clean, noisy) buffers."""
    rng = np.random.default_rng(seed)
    clean = np.full(shape, level, dtype=np.float64)
    noisy = sample_pg(clean, alpha, sigma, rng)
    return clean, noisy


def make_slanted_edge(
    shape: tuple[int, int] = (96, 96),
    low: float = 200.0,
    high: float = 800.0,
    slope: float = 0.06,
    alpha: float = ALPHA,
    sigma: float = SIGMA,
    seed: int = 5,
) -> EdgePhantom:
    """A near-vertical slanted edge (for MTF), clean + Poisson-Gaussian noisy."""
    ny, nx = shape
    ys, xs = np.mgrid[0:ny, 0:nx]
    edge_x = nx / 2.0 + slope * (ys - ny / 2.0)
    # Smooth transition over ~1 px so the sampled edge is well-posed.
    clean = low + (high - low) * 0.5 * (1.0 + np.tanh((xs - edge_x) * 2.0))
    rng = np.random.default_rng(seed)
    noisy = sample_pg(clean, alpha, sigma, rng)
    return EdgePhantom(clean.astype(np.float64), noisy.astype(np.float64))


def frame_with_masks(pixel: np.ndarray, mask_spec: dict | None = None):
    """Build an XFrame with the given mask flags set at the given pixels."""
    masks = np.zeros(np.asarray(pixel).shape, dtype=np.uint8)
    if mask_spec:
        for flag, coords in mask_spec.items():
            for (y, x) in coords:
                masks[y, x] |= int(flag)
    return new_frame(np.asarray(pixel, dtype=np.float32), masks)
