"""Raw 16-bit + metadata JSON frame loader (#16, additive, SPEC-VIEWER-001).

@MX:NOTE: [AUTO] Additive Phase 0.5 loader for the verification GUI
(REQ-VIEW-CORE-1). Reuses the existing `data/` convention documented in
`data/README.md` (`raw/` = headerless 16-bit `.raw` frames + per-frame `.json`
metadata sidecars) and `common.xframe.new_frame` to hand back a float32
XFrame. Does not alter `common/contract.py`, `common/xframe.py`, or
`pipeline/orchestrator.py` surfaces (REQ-VIEW-CORE-4 -- additive only).

Metadata JSON schema (minimal, [P] -- additive, may grow in later phases):
    {
        "resolution": [rows, cols],   # required: raw pixel grid shape
        "dtype": "uint16"             # optional: defaults to uint16 (CLAUDE.md)
    }
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from common.xframe import XFrame, new_frame

_DEFAULT_DTYPE = "uint16"


def load_raw_frame(
    raw_path: str | Path, meta_path: str | Path | None = None
) -> XFrame:
    """Load a headerless 16-bit raw frame + JSON metadata sidecar into a XFrame.

    C-04 lossless: the raw dtype (uint16 by default) is upcast to float32,
    a value-preserving conversion (every uint16 value is exactly representable
    in float32's 24-bit mantissa) -- no information is lost (REQ-VIEW-CORE-1).

    Args:
        raw_path: path to the headerless raw frame (`data/README.md` `raw/`
            convention: `<name>.raw`).
        meta_path: path to the metadata JSON sidecar. Defaults to `raw_path`
            with its suffix replaced by `.json` (`<name>.raw` + `<name>.json`).

    Raises:
        ValueError: metadata is missing the required `resolution` field, or
            the raw payload's element count disagrees with `resolution`.
    """
    raw_path = Path(raw_path)
    meta_path = Path(meta_path) if meta_path is not None else raw_path.with_suffix(".json")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    try:
        rows, cols = meta["resolution"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"{meta_path}: metadata must define 'resolution' as [rows, cols]"
        ) from exc
    dtype = np.dtype(meta.get("dtype", _DEFAULT_DTYPE))

    raw = np.fromfile(raw_path, dtype=dtype)
    expected = rows * cols
    if raw.size != expected:
        raise ValueError(
            f"{raw_path}: raw element count {raw.size} != "
            f"resolution {rows}x{cols} ({expected})"
        )
    pixel = raw.reshape(rows, cols).astype(np.float32)
    return new_frame(pixel)
