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


def combine_masks(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Bitwise-combine two mask stacks. Not implemented at T0."""
    raise NotImplementedError("mask_ops.combine_masks is a T0 stub")


def dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    """Morphologically dilate a mask. Not implemented at T0."""
    raise NotImplementedError("mask_ops.dilate_mask is a T0 stub")
