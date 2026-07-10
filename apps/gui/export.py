"""Phase 2 minimal XFrame export/import (#17 reduced schema, REQ-VIEW-RUN-7/8).

@MX:ANCHOR: [AUTO] `export_frame`/`import_frame` are the sole read-execute-only
export round-trip for the pipeline comparison viewer.
@MX:REASON: C-20/REQ-VIEW-RUN-7/-8 is a HARD invariant; every export path must
reuse `apps.gui.io_panel.guard_output_path` (the single choke point, Phase 1)
rather than re-implementing the `data/` write refusal ad hoc.

Schema (spec.md HISTORY v0.1.3 decision 3, npz + JSON sidecar -- follows
`common/calibset.py::CalibSet.save/load` naming convention):
    <path>.npz  -- arrays: pixel (float32), masks (uint8), pixel_f64 (float64,
                   ONLY when validation_mode and a float64 buffer is present)
    <path>.json -- {"noise": {"alpha": float, "sigma": float},
                     "validation_mode": bool,
                     "history": [{"module_name", "module_version",
                                   "params_hash", "calibset_id", "extra"}, ...],
                     "array_keys": [...names actually written to the npz...]}

`intermediates` (per-stage preserved frames) are explicitly EXCLUDED from this
reduced schema -- stage-by-stage comparison is a display-only concern
(`pipeline_panel.py`), not an export concern (spec.md confirmed decision).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from apps.gui.io_panel import guard_output_path
from common.xframe import HistoryEntry, NoiseModel, XFrame


def _sidecar_paths(path: str | Path) -> tuple[Path, Path]:
    """Resolve `<path>.npz` / `<path>.json` (suffix APPENDED, not replaced).

    Mirrors `common/calibset.py::_sidecar_paths` so dotted basenames (e.g.
    versioned export names) are never truncated by `Path.with_suffix`.
    """
    base = Path(path)
    return base.parent / (base.name + ".npz"), base.parent / (base.name + ".json")


def export_frame(
    frame: XFrame, path: str | Path, project_root: str | Path
) -> tuple[Path, Path]:
    """Write `frame` to `<path>.npz` + `<path>.json` (#17 reduced schema).

    Raises:
        apps.gui.io_panel.DataWriteRejectedError: `path` resolves under
            `<project_root>/data` (C-20/REQ-VIEW-RUN-8 -- checked BEFORE any
            file is written).
    """
    resolved = guard_output_path(path, project_root)
    npz_path, json_path = _sidecar_paths(resolved)

    arrays: dict[str, np.ndarray] = {
        "pixel": np.asarray(frame.pixel, dtype=np.float32),
        "masks": np.asarray(frame.masks, dtype=np.uint8),
    }
    if frame.validation_mode and frame.pixel_f64 is not None:
        arrays["pixel_f64"] = np.asarray(frame.pixel_f64, dtype=np.float64)

    npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(npz_path, **arrays)

    meta: dict[str, Any] = {
        "noise": {"alpha": frame.noise.alpha, "sigma": frame.noise.sigma},
        "validation_mode": frame.validation_mode,
        "history": [
            {
                "module_name": entry.module_name,
                "module_version": entry.module_version,
                "params_hash": entry.params_hash,
                "calibset_id": entry.calibset_id,
                "extra": dict(entry.extra) if entry.extra is not None else None,
            }
            for entry in frame.history
        ],
        "array_keys": list(arrays.keys()),
    }
    json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return npz_path, json_path


def import_frame(path: str | Path) -> XFrame:
    """Load an XFrame previously written by `export_frame` (round-trip)."""
    npz_path, json_path = _sidecar_paths(path)
    meta = json.loads(json_path.read_text(encoding="utf-8"))

    with np.load(npz_path) as npz:
        pixel = npz["pixel"]
        masks = npz["masks"]
        pixel_f64 = npz["pixel_f64"] if "pixel_f64" in meta["array_keys"] else None

    noise = NoiseModel(alpha=meta["noise"]["alpha"], sigma=meta["noise"]["sigma"])
    history = tuple(
        HistoryEntry(
            module_name=item["module_name"],
            module_version=item["module_version"],
            params_hash=item["params_hash"],
            calibset_id=item["calibset_id"],
            extra=item.get("extra"),
        )
        for item in meta["history"]
    )
    return XFrame(
        pixel=pixel,
        masks=masks,
        noise=noise,
        history=history,
        pixel_f64=pixel_f64,
        validation_mode=meta["validation_mode"],
    )
