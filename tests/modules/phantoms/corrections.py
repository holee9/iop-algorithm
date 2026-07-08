"""Synthetic phantoms + CalibSet builders for the T2/WP1 correction modules.

Known-distortion injectors (plan.md section 6). Every constant is externalized
via Params (grade annotations [S]/[P]/[T]); EV thresholds live in the tests as
external-injected values (measurement != judgment).

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.contract import Params
from common.mask_ops import DefectMorphology
from common.xframe import new_frame

# Reuse the T1 phantom defaults (all defect_* [P] thresholds) and extend with
# the T2 module Params ([T] grades).
from tests.metrics.phantoms.params import _DEFAULTS as _T1_DEFAULTS

_CORR_DEFAULTS = dict(_T1_DEFAULTS)
_CORR_DEFAULTS.update(
    {
        "gain_min": 0.5,  # [T] valid gain lower bound
        "gain_max": 2.0,  # [T] valid gain upper bound
        "defect_line_min": 8,  # [T] row/col run length -> LINE (SWR-302)
        "defect_line_max_width": 1,  # [T] max perpendicular extent of a LINE
        "defect_cmax_pixels": 25,  # [T] C_max 5x5 -> 25 px connected cluster
        # [B] raw saturation point S_th (SWR-601, dose-step response pending
        # real measurement, appendix A). Injected here as a documented test
        # default; the offset module REQUIRES it (no silent in-module default).
        "raw_saturation_threshold": 0.98 * 65535.0,  # ~= 64224.3
    }
)

# External-injected EV thresholds (EVAL v1.1 min legs); tests compare engine
# outputs against these — the modules never embed them.
EV = {
    "ev101_dqe_degrade_max": 0.10,  # max relative DQE degradation after correction
    "ev102_mtf_retention_min": 0.90,  # min MTF@Nyquist retention after correction
    "ev103_miss_rate_max": 0.0,  # max builder detection miss rate
    "ev103_residual_cluster_max": 0,  # max residual visible clusters
    "offset_residual_frac": 0.10,  # SWR-104 residual <= 10% of median sigma_d
}


def corr_params(**overrides) -> Params:
    values = dict(_CORR_DEFAULTS)
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


def offset_calib(o_map, sigma_d=None, delta_o=None) -> CalibSet:
    data = {"O_map": np.asarray(o_map, dtype=np.float32)}
    if sigma_d is not None:
        data["sigma_d"] = np.asarray(sigma_d, dtype=np.float32)
    if delta_o is not None:
        data["delta_O"] = np.asarray(delta_o, dtype=np.float32)
    return _calib(CalibKind.OFFSET, data, np.shape(o_map))


def gain_calib(g_map, anchor_gains=None) -> CalibSet:
    data = {"G_map": np.asarray(g_map, dtype=np.float32)}
    if anchor_gains is not None:
        data["anchor_gains"] = np.asarray(anchor_gains, dtype=np.float32)
    return _calib(CalibKind.GAIN, data, np.shape(g_map))


def defect_calib(class_map) -> CalibSet:
    return _calib(
        CalibKind.DEFECT,
        {"class_map": np.asarray(class_map, dtype=np.int8)},
        np.shape(class_map),
    )


# ---------------------------------------------------------------------------
# Defect dark/flat stacks with planted bad pixels (dead => gain 0).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DefectStacks:
    dark_frames: list
    flat_frames: list
    planted: np.ndarray  # bool ground-truth defect map
    morph_truth: np.ndarray  # int8 expected morphology labels


def make_defect_stacks(
    shape=(64, 64),
    singles=((10, 10), (20, 40)),
    lines=(),  # each: (row, col0, length) horizontal run
    clusters=(),  # each: (row0, col0, h, w) block
    noisy=(),  # each: (row, col) -> high temporal-variance (E2597 NOISY) pixel
    n_frames=8,
    dark_level=100.0,
    flat_level=5000.0,
    sigma=3.0,
    noisy_sigma=200.0,
    seed=0,
) -> DefectStacks:
    """Build dark/flat stacks; dead pixels are flat == dark (zero gain), noisy
    pixels carry a large per-frame temporal spike (E2597 NOISY, review finding
    6). All planted positions are single-point morphology for interpolation."""
    rng = np.random.default_rng(seed)
    ny, nx = shape
    planted = np.zeros(shape, dtype=bool)
    dead = np.zeros(shape, dtype=bool)
    morph = np.full(shape, DefectMorphology.NORMAL, dtype=np.int8)

    for (r, c) in singles:
        planted[r, c] = dead[r, c] = True
        morph[r, c] = DefectMorphology.SINGLE
    for (r, c0, length) in lines:
        planted[r, c0 : c0 + length] = True
        dead[r, c0 : c0 + length] = True
        morph[r, c0 : c0 + length] = DefectMorphology.LINE
    for (r0, c0, h, w) in clusters:
        planted[r0 : r0 + h, c0 : c0 + w] = True
        dead[r0 : r0 + h, c0 : c0 + w] = True
        morph[r0 : r0 + h, c0 : c0 + w] = DefectMorphology.CLUSTER
    for (r, c) in noisy:
        planted[r, c] = True
        morph[r, c] = DefectMorphology.SINGLE  # corrected as an isolated bad pixel

    dark_frames = []
    flat_frames = []
    for _ in range(n_frames):
        dark = dark_level + rng.normal(0.0, sigma, size=shape)
        flat = flat_level + rng.normal(0.0, sigma, size=shape)
        # Dead pixels: flat collapses to the dark level (zero gain).
        flat[dead] = dark[dead]
        # Noisy pixels: large per-frame temporal variance in the flat stack.
        for (r, c) in noisy:
            flat[r, c] = flat_level + rng.normal(0.0, noisy_sigma)
        dark_frames.append(new_frame(dark.astype(np.float32)))
        flat_frames.append(new_frame(flat.astype(np.float32)))
    return DefectStacks(dark_frames, flat_frames, planted, morph)
