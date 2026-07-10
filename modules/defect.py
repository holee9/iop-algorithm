"""Defect correction: map-based interpolation only (SWR-301~304, FR-C003/C004).

This module is a pure CONSUMER of a pre-generated CalibSet(DEFECT) classification
map (single-point / line / cluster morphology). Detection and map generation live
in the offline builder metrics.defect_map (spec decision 1); this module never
regenerates the map — it applies the SWR-303 interpolation and marks corrected
pixels INTERPOLATION (REQ-CORR-DEFECT-1/2).

Interpolation by morphology (SWR-303):
- single  : 8-neighbour distance-weighted mean of NORMAL neighbours.
- line    : orthogonal 1D linear interpolation.
- cluster : edge-directed 4-direction (0/45/90/135 deg) min-variance 1D linear.
- gain hand-off (DEFECT mask set, no map classification): treated as single
  (REQ-CORR-DEFECT-8, spec decision 4).

Safety:
- no valid normal neighbour -> keep DEFECT, do NOT set INTERPOLATION, value
  unchanged (REQ-CORR-DEFECT-5 / EC-3, SWR-602 no-fabrication principle).
- cluster connected-component size > C_max -> refuse the map + panel warning
  (REQ-CORR-DEFECT-4, consumption-time gate).
- missing/invalid classification labels -> explicit schema rejection
  (REQ-CORR-DEFECT-7).

@MX:ANCHOR: [AUTO] `process` is the defect pipeline stage entry point invoked via
the orchestrator registry (REQ-CORR-CONTRACT-1/6).
@MX:REASON: this is the last WP1 correction stage; its interpolation + masking
contract is what the residual-cluster gate (VALIDATE-3) and every downstream
noise-weighted stage read against.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibSet
from common.contract import Params
from common.mask_ops import DefectMorphology, component_sizes, thin_line_masks
from common.xframe import HistoryEntry, MaskFlag, XFrame

MODULE_NAME = "defect"
MODULE_VERSION = "1.0.0"

K_CLASS_MAP = "class_map"  # CalibSet(DEFECT) morphology labels (SWR-302)

P_CMAX = "defect_cmax_pixels"  # max connected cluster size (5x5 -> 25) [T]
P_LINE_MIN = "defect_line_min"  # min row/col run length for a LINE (>=8) [T]
P_LINE_MAX_WIDTH = "defect_line_max_width"  # max perpendicular extent of a LINE [T]

# Params key names this module requires (SPEC-ERGO-001 REQUIRED_PARAMS manifest).
# Only P_CMAX is mandatory (raises if absent); P_LINE_MIN/P_LINE_MAX_WIDTH have
# module defaults and are therefore optional, not part of the required manifest.
REQUIRED_PARAMS: tuple[str, ...] = (P_CMAX,)

_VALID_LABELS = frozenset(int(m) for m in DefectMorphology)

# 4 interpolation axes for the edge-directed cluster branch (0/45/90/135 deg).
_AXES: tuple[tuple[int, int], ...] = ((0, 1), (1, 1), (1, 0), (1, -1))
# 8-neighbour offsets with their euclidean distances (single-point branch).
_NEIGH8: tuple[tuple[int, int, float], ...] = (
    (-1, -1, np.sqrt(2.0)),
    (-1, 0, 1.0),
    (-1, 1, np.sqrt(2.0)),
    (0, -1, 1.0),
    (0, 1, 1.0),
    (1, -1, np.sqrt(2.0)),
    (1, 0, 1.0),
    (1, 1, np.sqrt(2.0)),
)


class DefectMapSchemaError(ValueError):
    """CalibSet(DEFECT) map violates the classification-label schema (DEFECT-7)."""


class DefectMapRefused(RuntimeError):
    """Map refused for interpolation + panel-quality warning (DEFECT-4)."""


def _read_class_map(calib: CalibSet, shape: tuple[int, ...]) -> np.ndarray:
    if K_CLASS_MAP not in calib.data:
        raise DefectMapSchemaError(
            f"defect: CalibSet(DEFECT) missing required data key '{K_CLASS_MAP}'"
        )
    morph = np.asarray(calib.data[K_CLASS_MAP])
    if morph.shape != shape:
        raise DefectMapSchemaError(
            f"defect: class_map shape {morph.shape} != frame shape {shape}"
        )
    if not np.issubdtype(morph.dtype, np.integer):
        raise DefectMapSchemaError(
            f"defect: class_map must carry integer classification labels, "
            f"got dtype {morph.dtype}"
        )
    present = set(int(v) for v in np.unique(morph))
    invalid = present - _VALID_LABELS
    if invalid:
        raise DefectMapSchemaError(
            f"defect: class_map contains invalid classification label(s) "
            f"{sorted(invalid)}; valid labels are {sorted(_VALID_LABELS)} "
            f"(single/line/cluster/normal)"
        )
    return morph.astype(np.int8)


def _refuse_oversize_clusters(
    morph: np.ndarray, cmax: int, line_min: int, line_max_width: int
) -> None:
    """Consumption-time C_max gate (DEFECT-4).

    Applies the same THIN-run rule as the builder (review finding 1): a
    LINE-labelled region that is not actually a thin run (a solid blob a
    hand-crafted map mislabelled LINE) is treated as a cluster so it cannot
    bypass the C_max gate. Genuine thin lines are exempt.
    """
    line_lbl = morph == DefectMorphology.LINE
    h_line, v_line = thin_line_masks(line_lbl, line_min, line_max_width)
    genuine_line = h_line | v_line
    fat_line = line_lbl & ~genuine_line  # blob mislabelled LINE -> gate as cluster
    cluster = (morph == DefectMorphology.CLUSTER) | fat_line
    if not cluster.any():
        return
    for size in component_sizes(cluster, connectivity=8):
        if size > cmax:
            raise DefectMapRefused(
                f"defect: connected cluster of {size} px exceeds C_max ({cmax}); "
                f"refusing map for interpolation (panel diagnostic ROI not "
                f"quality-assured, SWR-302)"
            )


def _ray(
    img: np.ndarray, valid_normal: np.ndarray, r: int, c: int, dr: int, dc: int
) -> tuple[float, int] | None:
    """Walk from (r,c) along (dr,dc); return (value, steps) at the first valid
    normal pixel, or None if the border is reached first."""
    ny, nx = img.shape
    rr, cc, steps = r + dr, c + dc, 1
    while 0 <= rr < ny and 0 <= cc < nx:
        if valid_normal[rr, cc]:
            return float(img[rr, cc]), steps
        rr += dr
        cc += dc
        steps += 1
    return None


def _linear_two_sided(
    a: tuple[float, int] | None, b: tuple[float, int] | None
) -> float | None:
    """1D linear value from two opposing anchors (distance-weighted). Falls back
    to the single available anchor; None when neither side has a normal pixel."""
    if a is not None and b is not None:
        (va, sa), (vb, sb) = a, b
        return (va * sb + vb * sa) / (sa + sb)
    if a is not None:
        return a[0]
    if b is not None:
        return b[0]
    return None


def _interp_single(img: np.ndarray, valid_normal: np.ndarray, r: int, c: int) -> float | None:
    ny, nx = img.shape
    wsum = 0.0
    vsum = 0.0
    for dr, dc, dist in _NEIGH8:
        rr, cc = r + dr, c + dc
        if 0 <= rr < ny and 0 <= cc < nx and valid_normal[rr, cc]:
            w = 1.0 / dist
            wsum += w
            vsum += w * float(img[rr, cc])
    if wsum == 0.0:
        return None
    return vsum / wsum


def _interp_line(
    img: np.ndarray, valid_normal: np.ndarray, r: int, c: int, orthogonal: tuple[int, int]
) -> float | None:
    dr, dc = orthogonal
    a = _ray(img, valid_normal, r, c, dr, dc)
    b = _ray(img, valid_normal, r, c, -dr, -dc)
    return _linear_two_sided(a, b)


def _interp_cluster(
    img: np.ndarray, valid_normal: np.ndarray, r: int, c: int
) -> float | None:
    """Edge-directed: pick the axis whose two anchors are most similar
    (min |a-b| -> aligned with the edge), then linear-interpolate along it."""
    best_value: float | None = None
    best_diff = np.inf
    single_fallback: float | None = None
    single_dist = np.inf
    for dr, dc in _AXES:
        a = _ray(img, valid_normal, r, c, dr, dc)
        b = _ray(img, valid_normal, r, c, -dr, -dc)
        if a is not None and b is not None:
            diff = abs(a[0] - b[0])
            if diff < best_diff:
                best_diff = diff
                best_value = _linear_two_sided(a, b)
        else:
            # One-sided (or none). Among one-sided axes pick the NEAREST anchor
            # (review finding 3); ties break by axis order via strict `<`.
            anchor = a if a is not None else b
            if anchor is not None and anchor[1] < single_dist:
                single_dist = anchor[1]
                single_fallback = anchor[0]
    if best_value is not None:
        return best_value
    return single_fallback


def _line_orientation(
    morph: np.ndarray, line_min: int, line_max_width: int
) -> dict[tuple[int, int], tuple[int, int]]:
    """Map each LINE pixel -> orthogonal interpolation axis, PER PIXEL by run
    membership (review finding 2).

    A pixel on a horizontal run interpolates vertically (dr,dc)=(1,0); a pixel
    on a vertical run interpolates horizontally (0,1). A pixel on BOTH (a
    crossing point) is omitted so the caller routes it to the cluster/
    single-point branch instead of picking one wrong axis. This fixes the
    per-component bounding-box heuristic that gave crossing/touching H+V lines
    a single wrong axis.
    """
    orientation: dict[tuple[int, int], tuple[int, int]] = {}
    line_lbl = morph == DefectMorphology.LINE
    if not line_lbl.any():
        return orientation
    h_line, v_line = thin_line_masks(line_lbl, line_min, line_max_width)
    both = h_line & v_line
    only_h = h_line & ~both
    only_v = v_line & ~both
    for r, c in zip(*np.nonzero(only_h)):
        orientation[(int(r), int(c))] = (1, 0)
    for r, c in zip(*np.nonzero(only_v)):
        orientation[(int(r), int(c))] = (0, 1)
    return orientation


def _interpolate(
    img: np.ndarray,
    morph: np.ndarray,
    defect_set: np.ndarray,
    single_pixels: np.ndarray,
    line_orientation: dict[tuple[int, int], tuple[int, int]],
    valid_normal: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (corrected_img, interpolated_mask). Neighbour sourcing uses the
    ORIGINAL values (valid_normal), so the result is order-independent."""
    out = img.copy()
    interpolated = np.zeros(img.shape, dtype=bool)
    coords = np.argwhere(defect_set)
    for r, c in coords:
        r = int(r)
        c = int(c)
        label = int(morph[r, c])
        if single_pixels[r, c]:
            value = _interp_single(img, valid_normal, r, c)
        elif label == DefectMorphology.LINE:
            axis = line_orientation.get((r, c))
            if axis is None:
                # Crossing point / non-thin LINE pixel: no single orthogonal
                # axis applies -> edge-directed cluster interpolation (finding 2).
                value = _interp_cluster(img, valid_normal, r, c)
            else:
                value = _interp_line(img, valid_normal, r, c, axis)
        elif label == DefectMorphology.CLUSTER:
            value = _interp_cluster(img, valid_normal, r, c)
        else:  # pragma: no cover - defensive; defect_set is a strict union
            value = _interp_single(img, valid_normal, r, c)
        if value is not None:
            out[r, c] = value
            interpolated[r, c] = True
    return out, interpolated


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Interpolate classified defects and gain hand-off pixels (SWR-303).

    Returns a new XFrame; the input frame is treated as immutable (DATA-6).
    """
    cmax_val = params.get(P_CMAX)
    if cmax_val is None:
        raise ValueError(f"defect: missing required parameter '{P_CMAX}'")
    cmax = int(cmax_val)
    line_min_val = params.get(P_LINE_MIN)
    line_min = 8 if line_min_val is None else int(line_min_val)
    line_max_width_val = params.get(P_LINE_MAX_WIDTH)
    line_max_width = 1 if line_max_width_val is None else int(line_max_width_val)

    morph = _read_class_map(calib, frame.shape)
    _refuse_oversize_clusters(morph, cmax, line_min, line_max_width)

    masks_in = np.asarray(frame.masks, dtype=np.uint8)
    defect_flag = (masks_in & np.uint8(MaskFlag.DEFECT)) != 0
    # Saturation-flagged (e.g. gain-clamped) pixels are excluded from anchors:
    # interpolating a defect from a clipped 65535 value fabricates data
    # (review finding 7, EC-3 no-fabrication principle).
    sat_flag = (masks_in & np.uint8(MaskFlag.SATURATION)) != 0

    map_defect = morph != DefectMorphology.NORMAL
    defect_set = map_defect | defect_flag
    valid_normal = ~defect_set & ~sat_flag
    # single = map single-points OR gain hand-off (DEFECT flag, no map class).
    single_pixels = (morph == DefectMorphology.SINGLE) | (
        defect_flag & (morph == DefectMorphology.NORMAL)
    )
    line_orientation = _line_orientation(morph, line_min, line_max_width)

    out_pixel_f64, interpolated = _interpolate(
        np.asarray(frame.pixel, dtype=np.float64),
        morph,
        defect_set,
        single_pixels,
        line_orientation,
        valid_normal,
    )
    out_pixel = out_pixel_f64.astype(frame.pixel.dtype)

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64, _ = _interpolate(
            np.asarray(frame.pixel_f64, dtype=np.float64),
            morph,
            defect_set,
            single_pixels,
            line_orientation,
            valid_normal,
        )

    # Mask update: all defective pixels carry DEFECT; interpolated ones add
    # INTERPOLATION. Non-interpolated defects keep DEFECT only (EC-3).
    new_masks = masks_in.copy()
    new_masks[defect_set] |= np.uint8(MaskFlag.DEFECT)
    new_masks[interpolated] |= np.uint8(MaskFlag.INTERPOLATION)

    new = frame.with_pixel(out_pixel, out_f64)
    new = _with_masks(new, new_masks)

    n_defect = int(np.count_nonzero(defect_set))
    n_interp = int(np.count_nonzero(interpolated))
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra={
            "defect_pixels": n_defect,
            "interpolated_pixels": n_interp,
            "uncorrected_pixels": n_defect - n_interp,
        },
    )
    return new.record_history(entry)


def _with_masks(frame: XFrame, masks: np.ndarray) -> XFrame:
    from dataclasses import replace

    return replace(frame, masks=masks)
