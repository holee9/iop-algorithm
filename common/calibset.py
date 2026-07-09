"""CalibSet: common calibration-data schema and serialization (REQ-INFRA-DATA-3).

@MX:ANCHOR: [AUTO] CalibSet is the single calibration container shared by every
processing stage (SWR-000-10). Its schema (panel id, resolution, validity
period, kind, data, provenance) is the one contract all modules read against.
@MX:REASON: fan_in spans all calibrated modules (offset/gain/defect/...); a
schema change affects every consumer and the entry gate.

Serialization format ([P], revisitable at T2 per plan.md decision 4): array
payload as .npz + a JSON sidecar for metadata. The format is intentionally
isolated behind save()/load() so T2 can swap it without touching consumers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np


class CalibKind(str, Enum):
    """Category of calibration payload."""

    OFFSET = "offset"
    GAIN = "gain"
    DEFECT = "defect"
    LAG = "lag"
    LINE_NOISE = "line_noise"
    # Noise model (alpha, sigma) for the T5 denoise stage (SPEC-DENOISE-001
    # decision 2). A dedicated kind — rather than reusing OTHER — lets the
    # orchestrator entry gate enforce kind-vs-stage wiring for denoise, which
    # structurally blocks unauthorized default substitution (SWR-000-5).
    NOISE = "noise"
    # Scatter kernel (dual-Gaussian PSF) for the T8 virtual_grid stage
    # (SPEC-VGRID-001 decision 2, SWR-000-10 "scatter 커널"). A dedicated kind —
    # rather than reusing OTHER — lets the orchestrator entry gate enforce
    # kind-vs-stage wiring for virtual_grid, which structurally blocks
    # unauthorized default-kernel substitution (SWR-000-5). Distinct from T7
    # grid, which has no detector calibration and uses CalibSet(OTHER).
    SCATTER = "scatter"
    OTHER = "other"


# CalibSet(kind=LAG) data payload keys: the exponential-sum IRF coefficients
# ([B]). Single source of truth shared by the producer (metrics.lag_irf) and the
# consumer (modules.lag) so the two never drift on the key literals.
K_IRF_A = "irf_a"  # (M,) amplitudes a_i
K_IRF_B = "irf_b"  # (M,) poles b_i (0 < b_i < 1 for a decaying afterglow)
LAG_PAYLOAD_KEYS: tuple[str, ...] = (K_IRF_A, K_IRF_B)

# CalibSet(kind=NOISE) data payload keys: the Poisson-Gaussian noise model
# variance ~= alpha * signal + sigma**2 ([B], SWR-701). Single source of truth
# shared by the producer (metrics.noise_model) and the consumer (modules.denoise)
# so the two never drift on the key literals (LAG_PAYLOAD_KEYS precedent).
K_NOISE_ALPHA = "alpha"  # () gain slope alpha (>0)
K_NOISE_SIGMA = "sigma"  # () read-noise sigma (>=0)
NOISE_PAYLOAD_KEYS: tuple[str, ...] = (K_NOISE_ALPHA, K_NOISE_SIGMA)

# CalibSet(kind=SCATTER) data payload keys: the dual-Gaussian scatter PSF
# K(r) = amp[0]*Gauss(sigma[0]) + amp[1]*Gauss(sigma[1]), applied in the
# x8-downsampled SKS domain ([B], SWR-1101). The Gaussian sigmas are expressed in
# DOWNSAMPLED pixels (the SKS estimation domain). The amplitudes are the
# scatter-to-primary weights; their sum is the DC scatter-to-primary ratio (SPR)
# and MUST be < 1 for the SKS fixed-point iteration to converge (spectral radius
# < 1, SWR-1101 high-SPR robustness). Single source of truth shared by the
# producer (metrics.scatter_kernel) and the consumer (modules.virtual_grid) so
# the two never drift on the key literals (NOISE_PAYLOAD_KEYS precedent). The
# thickness/kV dependence that shapes (amp, sigma) is resolved offline by the
# builder; the exact multi-thickness schema is [B]-deferred to real measurement.
K_SCATTER_AMP = "scatter_amp"  # (2,) dual-Gaussian amplitudes (SPR weights, > 0)
K_SCATTER_SIGMA = "scatter_sigma"  # (2,) dual-Gaussian sigmas in downsampled px (> 0)
SCATTER_PAYLOAD_KEYS: tuple[str, ...] = (K_SCATTER_AMP, K_SCATTER_SIGMA)


@dataclass(frozen=True)
class CalibProvenance:
    """Generation history of a CalibSet (IEC 62304 traceability)."""

    created_at: str
    source: str
    note: str = ""


class CalibSchemaError(ValueError):
    """Raised when a CalibSet violates the common schema."""


def _sidecar_paths(path: str | Path) -> tuple[Path, Path]:
    """Resolve `<path>.npz` / `<path>.json` by appending to the full name."""
    base = Path(path)
    return base.parent / (base.name + ".npz"), base.parent / (base.name + ".json")


@dataclass(frozen=True)
class CalibSet:
    """Calibration data following the single common schema (DATA-3).

    Fields:
        panel_id:   detector panel identifier.
        resolution: (rows, cols) the calibration applies to.
        valid_from / valid_until: ISO-8601 validity window.
        kind:       CalibKind category.
        data:       named ndarray payloads.
        provenance: generation history.
    """

    panel_id: str
    resolution: tuple[int, int]
    valid_from: str
    valid_until: str
    kind: CalibKind
    data: Mapping[str, np.ndarray] = field(default_factory=dict)
    provenance: CalibProvenance | None = None

    def __post_init__(self) -> None:
        # Immutability: modules must not mutate calibration payloads in place
        # (same contract as XFrame buffers, DATA-6). Writable caller arrays are
        # copied before locking; the mapping itself is frozen.
        frozen: dict[str, np.ndarray] = {}
        for name, arr in dict(self.data).items():
            if isinstance(arr, np.ndarray):
                if arr.flags.writeable:
                    arr = arr.copy()
                    arr.flags.writeable = False
            frozen[name] = arr
        object.__setattr__(self, "data", MappingProxyType(frozen))

    @property
    def calibset_id(self) -> str:
        """Stable identifier used in XFrame history entries (DATA-4)."""
        r, c = self.resolution
        return f"{self.panel_id}:{self.kind.value}:{r}x{c}:{self.valid_from}"

    def validate(self) -> None:
        """Validate against the common schema. Raises CalibSchemaError.

        @MX:NOTE: [AUTO] Structural schema check only (types/shape of the
        contract), not numeric range validation of payloads.
        """
        if not self.panel_id:
            raise CalibSchemaError("panel_id must be a non-empty string")
        if (
            not isinstance(self.resolution, tuple)
            or len(self.resolution) != 2
            or not all(isinstance(x, int) and x > 0 for x in self.resolution)
        ):
            raise CalibSchemaError("resolution must be (rows, cols) positive ints")
        if not self.valid_from or not self.valid_until:
            raise CalibSchemaError("validity window (valid_from/valid_until) required")
        if not isinstance(self.kind, CalibKind):
            raise CalibSchemaError("kind must be a CalibKind")
        for name, arr in self.data.items():
            if not isinstance(arr, np.ndarray):
                raise CalibSchemaError(f"data[{name!r}] must be a numpy ndarray")

    def matches_resolution(self, resolution: tuple[int, int]) -> bool:
        """True when the CalibSet applies to the given frame resolution."""
        return tuple(self.resolution) == tuple(resolution)

    # -- serialization ([P] format: npz + JSON sidecar) --------------------

    def save(self, path: str | Path) -> tuple[Path, Path]:
        """Persist to `<path>.npz` (arrays) + `<path>.json` (metadata).

        @MX:NOTE: [AUTO] [P]-grade format; isolated here so T2 can revisit
        without changing callers.
        """
        # NOTE: suffixes are APPENDED to the full basename. Path.with_suffix
        # would truncate dotted names ("gain_v1.0" -> "gain_v1.npz"), letting
        # different calibration versions collide on the same files.
        npz_path, json_path = _sidecar_paths(path)
        np.savez(npz_path, **{k: np.asarray(v) for k, v in self.data.items()})
        meta: dict[str, Any] = {
            "panel_id": self.panel_id,
            "resolution": list(self.resolution),
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "kind": self.kind.value,
            "data_keys": list(self.data.keys()),
            "provenance": (
                {
                    "created_at": self.provenance.created_at,
                    "source": self.provenance.source,
                    "note": self.provenance.note,
                }
                if self.provenance
                else None
            ),
        }
        json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return npz_path, json_path

    @classmethod
    def load(cls, path: str | Path) -> "CalibSet":
        """Load from the `<path>.npz` + `<path>.json` sidecar pair."""
        npz_path, json_path = _sidecar_paths(path)
        meta = json.loads(json_path.read_text(encoding="utf-8"))
        with np.load(npz_path) as npz:
            data = {k: npz[k] for k in meta.get("data_keys", [])}
        prov = meta.get("provenance")
        provenance = (
            CalibProvenance(
                created_at=prov["created_at"],
                source=prov["source"],
                note=prov.get("note", ""),
            )
            if prov
            else None
        )
        calib = cls(
            panel_id=meta["panel_id"],
            resolution=tuple(meta["resolution"]),
            valid_from=meta["valid_from"],
            valid_until=meta["valid_until"],
            kind=CalibKind(meta["kind"]),
            data=data,
            provenance=provenance,
        )
        calib.validate()
        return calib
