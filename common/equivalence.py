"""Equivalence diff hook for the implementation-swap contract (REQ-INFRA-CI-4).

@MX:ANCHOR: [AUTO] TC-021-family hook. Lets golden / optimized / FPGA
implementations sharing the same `process` signature be compared structurally.
@MX:REASON: This is the single comparison entry point the P2 numeric-equality
gate (bit-identical / +/-1 LSB) will build on; its diff shape is a contract.

T0 scope: STRUCTURE ONLY. Numeric thresholds (bit-identical integer path,
+/-1 LSB float path, TC-021) are deferred to P2 (Exclusions). This util reports
per-field differences without asserting any tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.xframe import XFrame


@dataclass(frozen=True)
class EquivalenceDiff:
    """Per-field difference summary between two implementations' outputs.

    max_pixel_abs_diff is reported for information; T0 asserts NO threshold on
    it (P2 owns the numeric gate).
    """

    pixel_equal: bool
    masks_equal: bool
    noise_equal: bool
    max_pixel_abs_diff: float

    @property
    def structurally_equal(self) -> bool:
        return self.pixel_equal and self.masks_equal and self.noise_equal


def diff_frames(a: XFrame, b: XFrame) -> EquivalenceDiff:
    """Compute a structural diff between two candidate output frames (CI-4)."""
    if a.shape != b.shape:
        raise ValueError(f"frame shapes differ: {a.shape} vs {b.shape}")
    # equal_nan: NaN-marked dead pixels must not spuriously differ.
    pixel_equal = bool(np.array_equal(a.pixel, b.pixel, equal_nan=True))
    masks_equal = bool(np.array_equal(a.masks, b.masks))
    noise_equal = a.noise == b.noise
    max_abs = float(np.max(np.abs(a.pixel.astype(np.float64) - b.pixel.astype(np.float64))))
    return EquivalenceDiff(
        pixel_equal=pixel_equal,
        masks_equal=masks_equal,
        noise_equal=noise_equal,
        max_pixel_abs_diff=max_abs,
    )
