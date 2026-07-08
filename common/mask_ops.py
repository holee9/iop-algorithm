"""Shared component stub: mask-stack operations (SWR-000-9, REQ-INFRA-STATIC-3).

@MX:NOTE: [AUTO] T0 interface stub only; algorithm deferred to first consumer.
Note: the MaskFlag bit-flag definition itself lives in common.xframe; this
module will hold higher-level mask manipulation (dilate, combine, count).
"""

from __future__ import annotations

import numpy as np


def combine_masks(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Bitwise-combine two mask stacks. Not implemented at T0."""
    raise NotImplementedError("mask_ops.combine_masks is a T0 stub")


def dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    """Morphologically dilate a mask. Not implemented at T0."""
    raise NotImplementedError("mask_ops.dilate_mask is a T0 stub")
