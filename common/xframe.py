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
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np

# Canonical dtypes for the two computation paths.
PIXEL_DTYPE = np.float32
PIXEL_DTYPE_VALIDATION = np.float64
MASK_DTYPE = np.uint8


def _locked(arr: np.ndarray, dtype: np.dtype | type) -> np.ndarray:
    """Return a read-only ndarray of `dtype` backed by safe (unaliased) memory.

    @MX:NOTE: [AUTO] Buffers that are already read-only and of the right dtype
    are shared as-is — metadata-only dataclasses.replace() (record_history,
    with_intermediate) must not copy ~120MB of frame data per call. Writable
    input is copied before locking so the caller's array is never mutated.
    """
    out = np.asarray(arr, dtype=dtype)
    if out is arr:
        if out.flags.writeable:
            out = out.copy()
            out.flags.writeable = False
        return out
    # np.asarray produced a new array (dtype cast) or a view; a view shares
    # memory with a possibly-writable base, so copy in that case.
    if out.base is not None:
        out = out.copy()
    out.flags.writeable = False
    return out


class MaskFlag(IntFlag):
    """Bit-flags composing the XFrame mask stack (REQ-INFRA-DATA-1)."""

    NONE = 0
    DEFECT = 1
    SATURATION = 2
    INTERPOLATION = 4
    # Boundary buffer band around a saturated core (SWR-602 W_band). Distinct
    # from SATURATION so the saturation stage is idempotent (the band is never
    # re-dilated into a wider band on re-run) and so downstream consumers can
    # tell the invented buffer zone from a truly saturated pixel.
    SATURATION_BAND = 8


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

    `extra` carries scalar processing diagnostics (e.g. clamp rate, panel
    warnings) as a committed channel — NOT a side channel (SWR-000-6). It is
    the sanctioned way for a module to surface a scalar by-product without an
    extra return value or a global. Defaults to None for backward compatibility
    with the 4-field construction used by earlier stages.
    """

    module_name: str
    module_version: str
    params_hash: str
    calibset_id: str | None
    extra: Mapping[str, str | int | float] | None = None

    def __post_init__(self) -> None:
        # Freeze a mapping copy so the recorded diagnostics cannot be mutated
        # after the entry is appended (same immutability contract as buffers).
        if self.extra is not None:
            object.__setattr__(
                self, "extra", MappingProxyType(dict(self.extra))
            )


def _canonical_param(value: Any) -> Any:
    """Canonicalize a parameter value for hashing.

    @MX:NOTE: [AUTO] numpy arrays are hashed over dtype+shape+raw bytes, never
    str() (whose truncation for >1000 elements would make the hash
    non-injective and corrupt the IEC 62304 audit chain).
    """
    if isinstance(value, np.ndarray):
        digest = hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
        return {"__ndarray__": [str(value.dtype), list(value.shape), digest]}
    if isinstance(value, np.generic):
        return value.item()
    return str(value)


def hash_params(params: Mapping[str, Any]) -> str:
    """Deterministic hash of a parameter mapping (DATA-4).

    Uses canonical JSON (sorted keys) so the same parameters always yield the
    same hash regardless of insertion order; ndarray values are hashed over
    their raw bytes via _canonical_param.
    """
    canonical = json.dumps(
        dict(params), sort_keys=True, default=_canonical_param, separators=(",", ":")
    )
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
        pixel = _locked(self.pixel, PIXEL_DTYPE)
        masks = _locked(self.masks, MASK_DTYPE)
        if pixel.shape != masks.shape:
            raise ValueError(
                f"pixel shape {pixel.shape} != masks shape {masks.shape}"
            )
        object.__setattr__(self, "pixel", pixel)
        object.__setattr__(self, "masks", masks)

        if self.pixel_f64 is not None:
            f64 = _locked(self.pixel_f64, PIXEL_DTYPE_VALIDATION)
            if f64.shape != pixel.shape:
                raise ValueError("pixel_f64 shape must match pixel shape")
            object.__setattr__(self, "pixel_f64", f64)

    # -- pure constructors -------------------------------------------------

    @property
    def shape(self) -> tuple[int, ...]:
        return self.pixel.shape

    def with_pixel(
        self, pixel: np.ndarray, pixel_f64: np.ndarray | None = None
    ) -> "XFrame":
        """Return a new XFrame with replaced pixel data, preserving metadata.

        When this frame carries a validation-mode float64 buffer, a new
        `pixel_f64` MUST be supplied alongside the new pixels — silently
        keeping the old buffer would desynchronize the CI-3b parallel path.
        """
        if self.pixel_f64 is not None and pixel_f64 is None:
            raise ValueError(
                "frame carries a validation-mode pixel_f64 buffer; with_pixel "
                "requires an explicit updated pixel_f64 (stale buffer refused)"
            )
        return replace(self, pixel=pixel, pixel_f64=pixel_f64)

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

        Compares pixel, mask stack, noise model, history chain,
        validation_mode flag, float64 parallel buffer, and preserved
        intermediates. NaN pixels compare equal (equal_nan) — dead pixels in
        float golden-model fixtures are commonly NaN-marked.
        """
        if not isinstance(other, XFrame):
            return False
        if not np.array_equal(self.pixel, other.pixel, equal_nan=True):
            return False
        if not np.array_equal(self.masks, other.masks):
            return False
        if self.noise != other.noise:
            return False
        if self.history != other.history:
            return False
        if self.validation_mode != other.validation_mode:
            return False
        if (self.pixel_f64 is None) != (other.pixel_f64 is None):
            return False
        if self.pixel_f64 is not None and not np.array_equal(
            self.pixel_f64, other.pixel_f64, equal_nan=True
        ):
            return False
        if len(self.intermediates) != len(other.intermediates):
            return False
        return all(
            a.equals(b) for a, b in zip(self.intermediates, other.intermediates)
        )


# @MX:ANCHOR: [AUTO] Public constructor for XFrame, the sole ingestion path from
# raw pixel arrays (common.io.load_raw_frame, common.synth_calibset test/GUI
# fixtures, scripts.ingest_edrogi) into the pipeline's canonical container.
# @MX:REASON: fan_in spans every external XFrame-construction call site (raw
# loader, synthetic fixtures, ingest tooling); a signature change here breaks
# every non-orchestrator entry into the pipeline.
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
