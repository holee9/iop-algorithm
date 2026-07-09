"""Synthetic phantoms + externalized Params/EV for T6 (SPEC-POST-001).

Known-anatomy / known-VOI injectors for the MSE-DRC (modules.mse) and
auto-windowing/GSDF (modules.window) modules. Every constant is externalized;
EV thresholds and the GSDF conformance threshold live here as external-injected
values (measurement != judgment, EVAL v1.1 legs). Accuracy is the single goal;
no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.contract import Params
from common.xframe import MaskFlag, NoiseModel, new_frame

# Known synthetic noise model (as recorded by upstream T5 on XFrame.noise).
ALPHA = 2.0
SIGMA = 3.0

# External-injected EV / conformance thresholds (EVAL v1.1 legs; injected here,
# never embedded in the modules/engine).
EV = {
    "ev205_window_fit_min": 0.85,  # auto-window fit rate >= 85% (EV-205 min)
    "ev102_mtf_retention_min": 0.90,  # MTF@Nyquist retention >= 90% (EV-102 min)
    "eps_gsdf": 5.0e-3,  # GSDF LUT per-JND deviation ceiling ([S]-adjacent)
    "voi_tolerance_frac": 0.10,  # window fit tolerance (frac of anatomy span) [T]
    "local_contrast_min_gain": 1.0,  # MSE local contrast improvement >= 1x
    "detail_energy_retention_min": 0.5,  # detail-band energy retained >= 50% [T]
    "drc_compression_min": 0.0,  # low-band dynamic-range compression > 0
    "clip_fraction_max": 0.02,  # <= 2% pixels clipped at the [0,1] rails
}


def other_calib(
    shape: tuple[int, int],
    *,
    panel_id: str = "PANEL-A",
    valid_from: str = "2026-01-01",
    valid_until: str = "2027-01-01",
) -> CalibSet:
    """Empty CalibSet(OTHER) placeholder satisfying the entry gate (decision 2)."""
    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(shape),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=CalibKind.OTHER,
        data={},
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
    )


def full_calib_map(
    shape: tuple[int, int],
    *,
    panel_id: str = "PANEL-A",
) -> dict:
    """Complete CalibSet map for a ``PipelineDefinition.full()`` run.

    Supplies a resolution-/panel_id-matching CalibSet for every canonical stage:
    a kind-matched CalibSet for the detector-calibrated stages, CalibSet(NOISE) for
    denoise, and CalibSet(OTHER) placeholders for saturation/geometry and the T6
    display post stages mse/window/post (which have no detector calibration but
    still pass the entry gate, decision 2). All share `panel_id` (gate requires it).
    """
    from pipeline.orchestrator import CANONICAL_ORDER

    kind_by_stage = {
        "offset": CalibKind.OFFSET,
        "gain": CalibKind.GAIN,
        "defect": CalibKind.DEFECT,
        "lag": CalibKind.LAG,
        "line_noise": CalibKind.LINE_NOISE,
        "denoise": CalibKind.NOISE,
        "virtual_grid": CalibKind.SCATTER,
    }
    out: dict = {}
    for stage in CANONICAL_ORDER:
        kind = kind_by_stage.get(stage, CalibKind.OTHER)
        out[stage] = CalibSet(
            panel_id=panel_id,
            resolution=tuple(shape),
            valid_from="2026-01-01",
            valid_until="2027-01-01",
            kind=kind,
            data={},
            provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
        )
    return out


def mse_params(**overrides) -> Params:
    """MSE/DRC Params: pyramid levels, per-level gain/exponent, gate, DRC, norm."""
    values = {
        "mse_levels": 4,  # [T] (7 @3072; smaller for compact synthetic frames)
        "mse_method": "power_law",
        # Per-level gain/exponent: the FINEST level (0, edge/MTF-bearing) is left
        # near-identity (gamma=1, p=1) to preserve MTF@Nyquist (EV-102 guardrail);
        # coarser levels enhance subtle large-scale contrast (p<1 relative boost).
        "mse_gamma": [1.0, 1.3, 1.5, 1.6],  # [T] per-level gain
        "mse_power": [1.0, 0.85, 0.75, 0.7],  # [T] per-level exponent p in (0,1]
        "mse_noise_beta": 1.0,  # [T] noise-gate strength
        "mse_drc_gamma": 0.5,  # DRC low-band compression (<1)
        "mse_drc_low_levels": 2,  # [T] K coarsest detail bands folded into base B

        "mse_norm_plow": 0.1,  # [ungraded] SWR-805 low percentile
        "mse_norm_phigh": 99.9,  # [ungraded] SWR-805 high percentile
        # soft-clip alternative (⚠P) — only consumed WHERE method == "soft_clip".
        "mse_softclip_gain": 1.6,
        "mse_softclip_knee": 50.0,
    }
    values.update(overrides)
    return Params(values=values)


def window_params(**overrides) -> Params:
    """Window/GSDF Params: presets, P-value scale, display luminance."""
    values = {
        "window_voi_default": (2.0, 98.0),  # [T] fallback percentiles
        "window_voi_presets": {  # [P] region preset table
            "CHEST": (3.0, 97.0),
            "BONE": (1.0, 99.0),
        },
        "window_pvalue_levels": 4096,  # [P] standard P-value scale
        "window_collim_rel_threshold": 0.2,  # [P] collimation-field threshold (frac of median)
        "window_direct_fence_k": 3.0,  # [P] direct-exposure robust upper-fence k
        "gsdf_lum_min": 0.5,  # display L_min (cd/m^2), Params single source
        "gsdf_lum_max": 400.0,  # display L_max (cd/m^2)
        "gsdf_jnd_grid_size": 8192,  # [P] JND inversion grid resolution
    }
    values.update(overrides)
    return Params(values=values)


def make_noise_frame(pixel: np.ndarray, masks: np.ndarray | None = None):
    """XFrame carrying the known (alpha, sigma) on XFrame.noise (T5 handoff)."""
    return new_frame(
        np.asarray(pixel, dtype=np.float32),
        masks,
        NoiseModel(alpha=ALPHA, sigma=SIGMA),
    )


def _add_pg_noise(clean: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    k = rng.poisson(np.maximum(clean, 0.0) / ALPHA)
    eps = rng.normal(0.0, SIGMA, size=clean.shape)
    return ALPHA * k + eps


def make_bone_soft_phantom(
    shape: tuple[int, int] = (96, 96),
    soft_level: float = 2000.0,
    bone_level: float = 700.0,
    detail_amp: float = 40.0,
    seed: int = 11,
) -> tuple[np.ndarray, np.ndarray]:
    """Bone/soft-tissue dual-distribution phantom with fine detail texture.

    Returns (clean, noisy). Soft tissue fills the frame; a lower-signal bone slab
    (more attenuation) sits in the centre; a fine sinusoidal texture provides the
    detail bands whose energy retention MSE must preserve.
    """
    ny, nx = shape
    ys, xs = np.mgrid[0:ny, 0:nx]
    clean = np.full(shape, soft_level, dtype=np.float64)
    bone = (np.abs(xs - nx / 2) < nx / 6) & (np.abs(ys - ny / 2) < ny / 3)
    clean[bone] = bone_level
    clean += detail_amp * np.sin(xs / 3.0) * np.cos(ys / 4.0)  # fine detail
    noisy = _add_pg_noise(clean, seed)
    return clean, noisy


def make_slanted_edge(
    shape: tuple[int, int] = (128, 128),
    low: float = 800.0,
    high: float = 6000.0,
    slope: float = 0.04,
    seed: int = 12,
) -> tuple[np.ndarray, np.ndarray]:
    """Near-vertical slanted edge for the MSE MTF guardrail (clean, noisy)."""
    ny, nx = shape
    ys, xs = np.mgrid[0:ny, 0:nx]
    edge_x = nx / 2.0 + slope * (ys - ny / 2.0)
    clean = low + (high - low) * 0.5 * (1.0 + np.tanh((xs - edge_x) * 2.0))
    noisy = _add_pg_noise(clean, seed)
    return clean.astype(np.float64), noisy.astype(np.float64)


def make_region_phantom(
    region_code: str,
    voi_pct: tuple[float, float],
    shape: tuple[int, int] = (96, 96),
    anat_low: float = 500.0,
    anat_high: float = 3000.0,
    *,
    with_collimation: bool = True,
    with_direct: bool = True,
    seed: int = 20,
) -> tuple[np.ndarray, float, float]:
    """A collimated region phantom with a known anatomy VOI.

    The anatomy is a horizontal gradient from anat_low to anat_high; a low-signal
    collimation border and a bright direct-exposure stripe contaminate the raw
    histogram. Returns (image, expected_low, expected_high) where the expected
    window bounds are the `voi_pct` percentiles of the PURE anatomy region — the
    auto-windowing must recover these despite the contamination.
    """
    ny, nx = shape
    ys, xs = np.mgrid[0:ny, 0:nx]
    anatomy_val = anat_low + (anat_high - anat_low) * (xs / (nx - 1))
    image = anatomy_val.astype(np.float64).copy()

    anatomy_mask = np.ones(shape, dtype=bool)
    if with_collimation:
        border = 8
        collim = np.zeros(shape, dtype=bool)
        collim[:border, :] = collim[-border:, :] = True
        collim[:, :border] = collim[:, -border:] = True
        image[collim] = anat_low * 0.05  # unexposed collimated border (low signal)
        anatomy_mask &= ~collim
    if with_direct:
        direct = xs > (nx - nx // 8)  # bright unattenuated stripe on one side
        direct &= anatomy_mask
        image[direct] = anat_high * 3.0
        anatomy_mask &= ~direct

    anatomy_values = anatomy_val[anatomy_mask]
    expected_low = float(np.percentile(anatomy_values, voi_pct[0]))
    expected_high = float(np.percentile(anatomy_values, voi_pct[1]))
    image = _add_pg_noise(image, seed)
    return image, expected_low, expected_high
