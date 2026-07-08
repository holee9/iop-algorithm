"""Shared component: mask-stack operations (SWR-000-9, REQ-INFRA-STATIC-3).

@MX:NOTE: [AUTO] The MaskFlag bit-flag definition itself lives in common.xframe;
this module holds higher-level mask manipulation (connected components, defect
morphology labels) shared by the defect-map builder (metrics.defect_map) and the
defect correction module (modules.defect) so neither duplicates it (SWR-000-9).

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from enum import IntEnum

import numpy as np
from scipy import ndimage


class DefectMorphology(IntEnum):
    """Spatial defect morphology labels carried by a CalibSet(DEFECT) class_map.

    @MX:ANCHOR: [AUTO] Shared class_map schema between the defect-map builder
    (producer) and the defect correction module (consumer).
    @MX:REASON: both metrics.defect_map and modules.defect read/write these
    exact integer labels; a divergent code would silently mis-route the SWR-303
    interpolation branch (single vs line vs cluster).
    """

    NORMAL = 0
    SINGLE = 1  # isolated bad pixel -> 8-neighbour distance-weighted mean
    LINE = 2  # row/col run >= line_min -> orthogonal 1D linear
    CLUSTER = 3  # connected component >= 2px -> edge-directed 1D linear


# 4- and 8-connectivity structuring elements for scipy.ndimage.label.
_STRUCT_4 = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
_STRUCT_8 = np.ones((3, 3), dtype=bool)


def label_components(
    binary: np.ndarray, connectivity: int = 8
) -> tuple[np.ndarray, int]:
    """Label connected components of a boolean mask.

    Args:
        binary: 2-D boolean array (True = foreground).
        connectivity: 4 or 8 (8 = diagonal-connected, default).

    Returns:
        (labels, n) where `labels` is an int array (0 = background, 1..n the
        components) and `n` is the component count.
    """
    struct = _STRUCT_8 if connectivity == 8 else _STRUCT_4
    labels, n = ndimage.label(np.asarray(binary, dtype=bool), structure=struct)
    return labels, int(n)


def component_sizes(mask: np.ndarray, connectivity: int = 8) -> list[int]:
    """Pixel size of every connected component in `mask` (background excluded).

    @MX:ANCHOR: [AUTO] Single source of the C_max component-size measurement
    shared by the defect-map builder and the correction module.
    @MX:REASON: both gates (metrics.defect_map generation-time and
    modules.defect consumption-time) must measure cluster size identically or
    the two C_max gates silently drift (review finding 8).
    """
    labels, n = label_components(mask, connectivity=connectivity)
    if n == 0:
        return []
    counts = np.bincount(labels.ravel())
    return [int(counts[lbl]) for lbl in range(1, n + 1)]


def max_component_size(mask: np.ndarray, connectivity: int = 8) -> int:
    """Largest connected-component size in `mask` (0 when empty)."""
    sizes = component_sizes(mask, connectivity=connectivity)
    return max(sizes) if sizes else 0


def _fill_run_lengths(line_bool: np.ndarray, line_out: np.ndarray) -> None:
    """Write, for each True cell of the 1-D `line_bool`, its maximal
    consecutive-True run length into the aligned `line_out` view."""
    n = int(line_bool.size)
    i = 0
    while i < n:
        if line_bool[i]:
            j = i
            while j < n and line_bool[j]:
                j += 1
            line_out[i:j] = j - i
            i = j
        else:
            i += 1


def _run_length_map(mask: np.ndarray, axis: int) -> np.ndarray:
    """For each True pixel, the length of its maximal consecutive-True run along
    `axis` (axis=1 -> horizontal runs per row, axis=0 -> vertical runs per col)."""
    m = np.asarray(mask, dtype=bool)
    out = np.zeros(m.shape, dtype=np.int64)
    if axis == 1:
        for r in range(m.shape[0]):
            _fill_run_lengths(m[r, :], out[r, :])
    else:
        for c in range(m.shape[1]):
            _fill_run_lengths(m[:, c], out[:, c])
    return out


def thin_line_masks(
    mask: np.ndarray, line_min: int, line_max_width: int = 1
) -> tuple[np.ndarray, np.ndarray]:
    """Classify LINE pixels by the THIN-run rule (SWR-302, review finding 1).

    A pixel is a horizontal LINE pixel when it lies on a horizontal run of
    length >= line_min whose perpendicular (vertical) extent is <=
    line_max_width; symmetrically for vertical LINE pixels. A solid blob (whose
    runs reach line_min but whose perpendicular extent exceeds line_max_width)
    is therefore NOT a line and falls through to the cluster gate.

    @MX:ANCHOR: [AUTO] Single source of the line-vs-blob thinness rule shared by
    the builder classifier and the module orientation/gate.
    @MX:REASON: builder morphology and module orientation/C_max gate must agree
    on what counts as a line or the two sides silently disagree (finding 1/8).

    Returns:
        (h_line, v_line) boolean masks (a crossing pixel may be in both).
    """
    m = np.asarray(mask, dtype=bool)
    h_len = _run_length_map(m, axis=1)
    v_len = _run_length_map(m, axis=0)
    h_line = (h_len >= line_min) & (v_len <= line_max_width) & m
    v_line = (v_len >= line_min) & (h_len <= line_max_width) & m
    return h_line, v_line


def combine_masks(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Bitwise-combine two mask stacks. Not implemented at T0."""
    raise NotImplementedError("mask_ops.combine_masks is a T0 stub")


def dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    """Morphologically dilate a boolean mask by `radius` pixels.

    @MX:ANCHOR: [AUTO] Single source of mask dilation shared by the saturation
    boundary-band module (SWR-602 W_band) and any downstream consumer.
    @MX:REASON: the 2px saturation boundary band (SWR-602) must be produced by
    exactly one dilation rule; a divergent structuring element would change the
    buffer-weighting substrate handed to the T5 denoiser.

    Uses 8-connectivity (Chebyshev distance): `radius` iterations grow the mask
    into a square band of half-width `radius`.

    `radius` MUST be a positive integer. A fractional radius in (0, 1) would
    truncate to iterations=0, which scipy.ndimage.binary_dilation interprets as
    "dilate until convergence" and floods the entire frame (review finding 8);
    a non-integer or non-positive radius therefore raises ValueError rather than
    silently producing a wrong band.
    """
    if isinstance(radius, bool) or not isinstance(radius, (int, np.integer)):
        raise ValueError(
            f"dilate_mask: radius must be a positive integer, got {radius!r}"
        )
    if radius <= 0:
        raise ValueError(
            f"dilate_mask: radius must be a positive integer, got {radius!r}"
        )
    m = np.asarray(mask, dtype=bool)
    struct = _STRUCT_8
    return ndimage.binary_dilation(m, structure=struct, iterations=int(radius))
