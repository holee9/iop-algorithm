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
from enum import Enum
from typing import Iterable

import numpy as np

from common.xframe import XFrame

# SWR-1302 integer path: offset/gain/defect/line_noise are the bit-identical
# obligation. Every other stage is the floating-point path (+/-1 LSB target). The
# names are literal strings here — common is the foundational layer and must not
# import pipeline.orchestrator.CANONICAL_ORDER (import-linter forbidden edge).
INTEGER_PATH_STAGES: frozenset[str] = frozenset(
    {"offset", "gain", "defect", "line_noise"}
)


class PathClass(str, Enum):
    """Which SWR-1302 numeric-equality gate a comparison will fall under (P2).

    INTEGER = bit-identical obligation (integer path); FLOAT = +/-1 LSB tolerance
    (floating-point path). This is a STRUCTURAL label marking WHICH P2 gate
    applies later — T10 asserts no tolerance itself (Exclusions).
    """

    INTEGER = "integer"
    FLOAT = "float"


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


@dataclass(frozen=True)
class PathEquivalence:
    """A structural equivalence result tagged with its SWR-1302 path class (P2).

    Bundles the reused ``diff_frames`` result with the integer/float path label
    so a caller knows which numeric gate (bit-identical vs +/-1 LSB) would apply
    in P2. No tolerance is decided here.
    """

    diff: EquivalenceDiff
    path: PathClass

    @property
    def structurally_equal(self) -> bool:
        return self.diff.structurally_equal

    @property
    def max_pixel_abs_diff(self) -> float:
        return self.diff.max_pixel_abs_diff


def classify_path(stages: Iterable[str]) -> PathClass:
    """Classify a comparison's P2 numeric-gate type by its producing stages.

    @MX:NOTE: [AUTO] All-integer-path stages -> INTEGER (bit-identical target);
    any non-integer-path stage taints the comparison to FLOAT (+/-1 LSB target),
    matching SWR-1302's "정수 경로 ... / 그 외" split. Empty input is refused —
    an empty stage set has no P2 gate to mark (no silent default).
    """
    stages = tuple(stages)
    if not stages:
        raise ValueError("cannot classify an empty stage set into a path")
    if all(s in INTEGER_PATH_STAGES for s in stages):
        return PathClass.INTEGER
    return PathClass.FLOAT


def compare_paths(a: XFrame, b: XFrame, stages: Iterable[str]) -> PathEquivalence:
    """Structural equivalence of two outputs plus their SWR-1302 path class.

    @MX:NOTE: [AUTO] REUSES ``diff_frames`` (the T0 CI-4 hook) verbatim — this is
    its first real consumer (T10); the frame diff is never reimplemented
    (SWR-000-9). Only the integer/float path label is added on top.
    """
    return PathEquivalence(diff=diff_frames(a, b), path=classify_path(stages))
