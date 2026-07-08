"""XFrame: the sole module input/output unit for the XDET pipeline.

@MX:ANCHOR: [AUTO] XFrame is the single data-transfer container for every
processing module (SWR-000-6, REQ-INFRA-DATA-1). All pipeline modules and the
metrics engine consume and produce XFrame instances exclusively.
@MX:REASON: fan_in is effectively every module (13 pipeline stages + metrics);
any change to this contract ripples across the entire codebase.

Design rules (REQ-INFRA-DATA):
- pixel buffer: float32 by default (single golden-model path, SWR-000-1/CI-3a).
- validation-mode float64 parallel buffer: an internal XFrame field, NOT a
  side channel (REQ-INFRA-DATA-1/CI-3b). It is the only permitted float64
  transfer channel.
- mask stack: bit-flags for defect / saturation / interpolation (DATA-1).
- noise model: (alpha, sigma) (DATA-1).
- processing history chain: append-only, deterministic; each entry carries the
  module version, params hash, and CalibSet id (DATA-4, IEC 62304 tracking).
- input immutability: modules must treat the input XFrame as immutable
  (DATA-6). Buffers are marked read-only; mutation of an input is detectable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from enum import IntFlag
from typing import Any, Mapping

import numpy as np

# Canonical dtypes for the two computation paths.
PIXEL_DTYPE = np.float32
PIXEL_DTYPE_VALIDATION = np.float64
MASK_DTYPE = np.uint8


class MaskFlag(IntFlag):
    """Bit-flags composing the XFrame mask stack (REQ-INFRA-DATA-1)."""

    NONE = 0
    DEFECT = 1
    SATURATION = 2
    INTERPOLATION = 4


@dataclass(frozen=True)
class NoiseModel:
    """Per-frame noise model: variance ~= alpha * signal + sigma**2."""

    alpha: float = 0.0
    sigma: float = 0.0


@dataclass(frozen=True)
class HistoryEntry:
    """One deterministic step in the processing history chain (DATA-4).

    @MX:NOTE: [AUTO] params_hash and calibset_id make each module invocation
    reproducible and auditable (IEC 62304). Ordering in the chain is the
    execution order; the chain is append-only.
    """

    module_name: str
    module_version: str
    params_hash: str
    calibset_id: str | None


def hash_params(params: Mapping[str, Any]) -> str:
    """Deterministic hash of a parameter mapping (DATA-4).

    Uses canonical JSON (sorted keys) so the same parameters always yield the
    same hash regardless of insertion order.
    """
    canonical = json.dumps(params, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class XFrame:
    """Immutable frame container passed between processing modules.

    @MX:ANCHOR: [AUTO] Public API boundary for all module I/O.
    @MX:REASON: Every module signature is `process(XFrame, ...) -> XFrame`.

    Instances are frozen dataclasses; the numpy buffers are additionally set
    read-only at construction so accidental in-place mutation of an input frame
    raises (enforces DATA-6 immutability). Modules produce new frames via the
    pure helpers below.
    """

    pixel: np.ndarray
    masks: np.ndarray
    noise: NoiseModel = NoiseModel()
    history: tuple[HistoryEntry, ...] = ()
    # Validation-mode only: parallel float64 buffer (DATA-1 / CI-3b). None on
    # the default float32 single path.
    pixel_f64: np.ndarray | None = None
    validation_mode: bool = False
    # Validation-mode only: preserved per-stage intermediate frames (DATA-5).
    intermediates: tuple["XFrame", ...] = ()

    def __post_init__(self) -> None:
        # Normalize dtypes and lock buffers read-only for the immutability
        # contract. object.__setattr__ is required because the dataclass is
        # frozen.
        pixel = np.asarray(self.pixel, dtype=PIXEL_DTYPE)
        masks = np.asarray(self.masks, dtype=MASK_DTYPE)
        if pixel.shape != masks.shape:
            raise ValueError(
                f"pixel shape {pixel.shape} != masks shape {masks.shape}"
            )
        pixel = pixel.copy()
        masks = masks.copy()
        pixel.flags.writeable = False
        masks.flags.writeable = False
        object.__setattr__(self, "pixel", pixel)
        object.__setattr__(self, "masks", masks)

        if self.pixel_f64 is not None:
            f64 = np.asarray(self.pixel_f64, dtype=PIXEL_DTYPE_VALIDATION).copy()
            if f64.shape != pixel.shape:
                raise ValueError("pixel_f64 shape must match pixel shape")
            f64.flags.writeable = False
            object.__setattr__(self, "pixel_f64", f64)

    # -- pure constructors -------------------------------------------------

    @property
    def shape(self) -> tuple[int, ...]:
        return self.pixel.shape

    def with_pixel(
        self, pixel: np.ndarray, pixel_f64: np.ndarray | None = None
    ) -> "XFrame":
        """Return a new XFrame with replaced pixel data, preserving metadata."""
        return replace(
            self,
            pixel=pixel,
            pixel_f64=pixel_f64 if pixel_f64 is not None else self.pixel_f64,
        )

    def record_history(self, entry: HistoryEntry) -> "XFrame":
        """Return a new XFrame with `entry` appended to the history chain.

        @MX:NOTE: [AUTO] Append-only; never mutates the existing chain.
        """
        return replace(self, history=self.history + (entry,))

    def with_intermediate(self, frame: "XFrame") -> "XFrame":
        """Return a new XFrame recording a preserved intermediate (DATA-5).

        Only meaningful while validation_mode is active; the orchestrator uses
        this to retain per-stage outputs.
        """
        return replace(self, intermediates=self.intermediates + (frame,))

    # -- structural equality ----------------------------------------------

    def equals(self, other: "XFrame") -> bool:
        """Full structural comparison used by the harness (CONTRACT-4).

        Compares pixel, mask stack, noise model, and history chain. Validation
        float64 buffers are compared when present on either side.
        """
        if not isinstance(other, XFrame):
            return False
        if not np.array_equal(self.pixel, other.pixel):
            return False
        if not np.array_equal(self.masks, other.masks):
            return False
        if self.noise != other.noise:
            return False
        if self.history != other.history:
            return False
        if (self.pixel_f64 is None) != (other.pixel_f64 is None):
            return False
        if self.pixel_f64 is not None and not np.array_equal(
            self.pixel_f64, other.pixel_f64
        ):
            return False
        return True


def new_frame(
    pixel: np.ndarray,
    masks: np.ndarray | None = None,
    noise: NoiseModel | None = None,
    *,
    validation_mode: bool = False,
) -> XFrame:
    """Convenience constructor for a fresh XFrame.

    When `validation_mode` is set, a float64 parallel buffer is initialized
    from the pixel data (CI-3b).
    """
    pixel_arr = np.asarray(pixel, dtype=PIXEL_DTYPE)
    if masks is None:
        masks = np.zeros(pixel_arr.shape, dtype=MASK_DTYPE)
    pixel_f64 = (
        np.asarray(pixel, dtype=PIXEL_DTYPE_VALIDATION) if validation_mode else None
    )
    return XFrame(
        pixel=pixel_arr,
        masks=masks,
        noise=noise or NoiseModel(),
        pixel_f64=pixel_f64,
        validation_mode=validation_mode,
    )
