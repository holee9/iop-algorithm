"""Defect-map builder: dark/flat stacks -> CalibSet(DEFECT) (REQ-CORR-DEFECT-6).

Offline calibration-time tool (spec decision 1). It reuses the T1 engine
metrics.defect_stats.classify_defects to detect bad pixels from dark/flat stacks,
then classifies their spatial MORPHOLOGY (single-point / line / cluster per
SWR-302) into a CalibSet(DEFECT) class_map that the correction module
modules.defect consumes. Layering stays metrics -> common (the produced CalibSet
lives in common.calibset); the correction module never imports metrics.

Generation-time C_max gate: a connected cluster exceeding C_max refuses map
generation + raises a panel warning (REQ-CORR-DEFECT-6, dual to the module's
consumption-time gate).

@MX:ANCHOR: [AUTO] `build_defect_map` is the sole DEFECT-map producer feeding the
XDET-TC-003 miss-rate gate (REQ-CORR-VALIDATE-7).
@MX:REASON: its class_map schema and morphology thresholds are what modules.defect
interpolates against and what the ground-truth miss-rate comparison reads.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.contract import Params
from common.mask_ops import DefectMorphology, label_components
from metrics.defect_stats import DefectClass, classify_defects

P_LINE_MIN = "defect_line_min"  # min row/col run length for a LINE (>=8) [T]
P_CMAX = "defect_cmax_pixels"  # max connected cluster size (5x5 -> 25) [T]


class DefectMapBuildRefused(RuntimeError):
    """Cluster exceeds C_max at generation time; map generation refused (D6)."""


def _require_int(params: Params, key: str) -> int:
    value = params.get(key)
    if value is None:
        raise ValueError(f"defect_map: missing required parameter '{key}'")
    return int(value)


def _runs_ge(row: np.ndarray, min_len: int) -> np.ndarray:
    """Boolean mask of a 1-D array where a True-run has length >= min_len."""
    out = np.zeros(row.shape, dtype=bool)
    n = row.size
    i = 0
    while i < n:
        if row[i]:
            j = i
            while j < n and row[j]:
                j += 1
            if (j - i) >= min_len:
                out[i:j] = True
            i = j
        else:
            i += 1
    return out


def _line_mask(defect: np.ndarray, line_min: int) -> np.ndarray:
    """Mark pixels belonging to a horizontal or vertical run >= line_min."""
    mask = np.zeros(defect.shape, dtype=bool)
    for r in range(defect.shape[0]):
        mask[r, :] |= _runs_ge(defect[r, :], line_min)
    for c in range(defect.shape[1]):
        mask[:, c] |= _runs_ge(defect[:, c], line_min)
    return mask & defect


def classify_morphology(
    defect: np.ndarray, line_min: int, cmax: int
) -> np.ndarray:
    """Turn a boolean defect mask into a morphology class_map (SWR-302).

    Row/col runs >= line_min => LINE; of the rest, connected components >= 2px
    => CLUSTER, size-1 => SINGLE. Raises DefectMapBuildRefused when a cluster
    exceeds C_max.
    """
    morph = np.full(defect.shape, DefectMorphology.NORMAL, dtype=np.int8)

    line = _line_mask(defect, line_min)
    morph[line] = DefectMorphology.LINE

    remaining = defect & ~line
    labels, n = label_components(remaining, connectivity=8)
    for lbl in range(1, n + 1):
        comp = labels == lbl
        size = int(np.count_nonzero(comp))
        if size >= 2:
            if size > cmax:
                raise DefectMapBuildRefused(
                    f"defect_map: connected cluster of {size} px exceeds C_max "
                    f"({cmax}); refusing map generation (panel diagnostic ROI "
                    f"not quality-assured, SWR-302)"
                )
            morph[comp] = DefectMorphology.CLUSTER
        else:
            morph[comp] = DefectMorphology.SINGLE
    return morph


def build_defect_map(
    dark_frames: list,
    flat_frames: list,
    params: Params,
    *,
    panel_id: str,
    resolution: tuple[int, int],
    valid_from: str,
    valid_until: str,
    created_at: str = "",
    source: str = "defect-map-builder",
) -> CalibSet:
    """Detect + morphology-classify defects into a CalibSet(DEFECT).

    Raises:
        MetricReadError: propagated from classify_defects on bad stack input.
        DefectMapBuildRefused: a cluster exceeds C_max (generation-time gate).
    """
    line_min = _require_int(params, P_LINE_MIN)
    cmax = _require_int(params, P_CMAX)

    result = classify_defects(dark_frames, flat_frames, params)
    e2597 = np.asarray(result.get("class_map"))
    defect = e2597 != int(DefectClass.GOOD)

    morph = classify_morphology(defect, line_min, cmax)

    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(resolution),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=CalibKind.DEFECT,
        data={"class_map": morph},
        provenance=CalibProvenance(created_at=created_at, source=source),
    )
