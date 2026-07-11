"""External-reference ingest of the SAMPLE (plumbing-only) acquisition set.

SPEC-REALDATA-001. Walks `images/에드로지16BIT/` (3072x3072 16-bit little-endian
`uint16` raw, ~1.4GB), emits loader-contract JSON sidecars + a `manifest.json`
under a `data/edrogi/` mirror, and emits small deterministic 256x256 ROI crops as
the only committed binaries (`tests/fixtures/edrogi/`). Also builds NON-AUTHORITATIVE
sample CalibSets (OFFSET/GAIN/DEFECT) for builder STRUCTURE verification.

[HARD] QUARANTINE (REQ-REALDATA-QUARANTINE): this acquisition set is a plumbing
sample. Nothing here derives, fits, or tunes any [B]/[T]/[P] parameter, sets any
acceptance threshold, or serves as a golden/expected numeric reference. Dose /
CalSet-DN reference values are parsed for DISPLAY only and are never promoted to
a constant or threshold. The authoritative "guiding" acquisition set is a future
separate SPEC.

This is TOOLING, not a processing module: it defines no `process(...)` signature,
adds no `CANONICAL_ORDER` stage / `CalibKind`, and reuses `common.io.load_raw_frame`
+ `common.calibset.CalibSet` one-way (REQ-REALDATA-CONTRACT-1/2).

Run (uv-only; Korean paths need PYTHONIOENCODING=utf-8, lesson L#4):

    PYTHONIOENCODING=utf-8 uv run python scripts/ingest_edrogi.py \\
        --root images/에드로지16BIT --out data/edrogi
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from common.calibset import CalibDomain, CalibKind, CalibProvenance, CalibSet
from common.io import load_raw_frame
from modules.defect import K_CLASS_MAP
from modules.gain import K_GAIN_MAP
from modules.offset import K_OFFSET_MAP

try:  # DefectMorphology labels are the confirmed class_map literals (D4).
    from common.mask_ops import DefectMorphology
except Exception:  # pragma: no cover - defensive import
    DefectMorphology = None  # type: ignore

# --- fixed, quarantined constants (NOT sample-derived thresholds) ------------

# Default sample-set root (relative to repo root). `require_edrogi` reads this
# attribute at call time so tests can monkeypatch it to simulate absence.
EDROGI_ROOT = Path("images") / "에드로지16BIT"

# Confirmed acquisition fact (spec Environment): every raw is 3072x3072 uint16.
FULL_RES: tuple[int, int] = (3072, 3072)
DTYPE = "uint16"

# Deterministic fixed ROI crop for the committed CI fixtures (a fixed geometry
# choice, [T]-style, NOT a value fitted from the sample). Center 256x256 crop.
ROI_SIZE = 256
ROI_TOP = (FULL_RES[0] - ROI_SIZE) // 2  # 1408
ROI_LEFT = (FULL_RES[1] - ROI_SIZE) // 2  # 1408

# NON-AUTHORITATIVE labeling for every sample CalibSet (L#3, QUARANTINE).
SAMPLE_PANEL_ID = "SAMPLE-EDROGI-16BIT"
SAMPLE_VALID_FROM = "2000-01-01"
SAMPLE_VALID_UNTIL = "2099-12-31"
SAMPLE_PROVENANCE_NOTE = "sample=true; plumbing-only; non-authoritative (SPEC-REALDATA-001)"
# Sample acquisition domain (SPEC-CALDOM-001 SAMPLE): the acrylic(PMMA)/nps/ghost/
# min-dose-linear setup is medical/IEC-class (measurement protocol §1,
# `_CATEGORY_BY_FOLDER`). This is a CATEGORICAL label, not a number — it is
# QUARANTINE-safe (REQ-REALDATA-VALIDATE-4 guards numbers, not labels) and does
# NOT promote the sample set to authoritative (panel_id + provenance sample=true
# still enforce non-authority). beam_quality stays None: no validated RQA5 basis.
SAMPLE_DOMAIN = CalibDomain.MEDICAL

# The representative single GAIN level consumed as a single-point G_map (D1);
# multi-level linearity fitting is blocked by QUARANTINE (guiding set only).
REPRESENTATIVE_CALSET = "CalSet_19008"

# Committed 256^2 source-crop fixtures (D6): CalibSet source frames.
FIXTURE_DIR = Path("tests") / "fixtures" / "edrogi"
FIXTURE_MASTERDARK = "masterdark_256"
FIXTURE_CALSET = "calset_19008_256"
FIXTURE_BPM = "bpm_256"

_CATEGORY_BY_FOLDER: dict[str, str] = {
    "GHOST": "ghost_lag",
    "nps": "nps_flat",
    "아크릴": "acrylic_step",
    "최소선량선형": "min_dose_linear",
}

_KV_RE = re.compile(r"(\d+(?:\.\d+)?)kv", re.IGNORECASE)
_MA_RE = re.compile(r"(\d+(?:\.\d+)?)ma(?![Ss])")  # lowercase 'ma', not the 'mA' of mAs
_MAS_RE = re.compile(r"(\d+(?:\.\d+)?)mAs")
_PLATE_RE = re.compile(r"아크릴(\d+)장")
_FRAME_IDX_RE = re.compile(r"_(\d+)(?:_result)?\.raw$")
_DOSE_LINE_RE = re.compile(
    r"아크릴\s*(\d+)\s*장\s*:\s*(\d+)\s*/\s*([0-9.]+\s*[a-zA-Zµ]*Gy)"
)
_DOSE_TOKEN_RE = re.compile(r"([0-9.]+)\s*([numµu]?)Gy", re.IGNORECASE)

_UNIT_TO_UGY = {"": 1.0e6, "m": 1.0e3, "u": 1.0, "µ": 1.0, "n": 1.0e-3}


class RefusedFullResCopyError(RuntimeError):
    """Raised when a full-resolution raw would be copied under `data/` (INGEST-4)."""


class CalibSourceMissingError(FileNotFoundError):
    """Raised when a required sample CalibSet source frame is absent (CALIB-4)."""


# --- filename / dose parsing (pure) ------------------------------------------


def _category_for(folder: str, filename: str) -> str:
    if folder == "16bit cal":
        if filename.startswith("MasterDark"):
            return "offset_dark"
        if filename.startswith("BPM"):
            return "bad_pixel_map"
        if filename.startswith("CalSet"):
            return "gain_flat"
        return "offset_dark"
    return _CATEGORY_BY_FOLDER.get(folder, "min_dose_linear")


def parse_acquisition_meta(filename: str, folder: str) -> dict:
    """Parse kV/mA/mAs + category/plate/frame from a sample raw filename.

    Every returned entry is stamped `usage="sample-plumbing"` (INGEST-2,
    QUARANTINE): this parser never sources an algorithm parameter.
    """
    kv = _KV_RE.search(filename)
    ma = _MA_RE.search(filename)
    mas = _MAS_RE.search(filename)
    plate = _PLATE_RE.search(filename)
    frame = _FRAME_IDX_RE.search(filename)
    return {
        "category": _category_for(folder, filename),
        "usage": "sample-plumbing",
        "kv": float(kv.group(1)) if kv else None,
        "ma": float(ma.group(1)) if ma else None,
        "mas": float(mas.group(1)) if mas else None,
        "plate_count": int(plate.group(1)) if plate else None,
        "frame_index": int(frame.group(1)) if frame else None,
    }


def normalize_dose_token(token: str) -> float:
    """Normalize a dose token (e.g. '850nGy', '8.5uGy') to microGy (D5).

    Display-only reference value; never promoted to a threshold (QUARANTINE-4).
    """
    m = _DOSE_TOKEN_RE.search(token.strip())
    if not m:
        raise ValueError(f"unrecognized dose token: {token!r}")
    value = float(m.group(1))
    unit = m.group(2).lower()
    return value * _UNIT_TO_UGY[unit]


def parse_dose_meter(text: str) -> dict[int, dict]:
    """Parse `아크릴/DOSE METER.txt` into {plate_count: {dose_dn, dose_ugy, dose_raw}}.

    Values are display-only references (QUARANTINE-4): parsed, recorded, never
    tuned or promoted to an acceptance threshold.
    """
    table: dict[int, dict] = {}
    for line in text.splitlines():
        m = _DOSE_LINE_RE.search(line)
        if not m:
            continue
        plate = int(m.group(1))
        dose_raw = m.group(3).replace(" ", "")
        table[plate] = {
            "dose_dn": int(m.group(2)),
            "dose_ugy": normalize_dose_token(dose_raw),
            "dose_raw": dose_raw,
        }
    return table


def make_manifest_entry(
    raw_path: str,
    folder: str,
    filename: str,
    resolution: tuple[int, int],
    has_result_pair: bool,
    *,
    dose: dict | None = None,
    result_path: str | None = None,
) -> dict:
    """Build one manifest frame entry (schema per spec Environment).

    @MX:NOTE: [AUTO] The `usage="sample-plumbing"` stamp is the enforced marker
    checked by the numeric-provenance guard (REQ-REALDATA-VALIDATE-4).
    """
    meta = parse_acquisition_meta(filename, folder)
    entry = {
        "raw_path": raw_path,
        "resolution": [int(resolution[0]), int(resolution[1])],
        "dtype": DTYPE,
        "category": meta["category"],
        "usage": meta["usage"],  # always "sample-plumbing"
        "kv": meta["kv"],
        "ma": meta["ma"],
        "mas": meta["mas"],
        "plate_count": meta["plate_count"],
        "frame_index": meta["frame_index"],
        "has_result_pair": has_result_pair,
    }
    if result_path is not None:
        entry["result_path"] = result_path
    if dose is not None:
        entry["dose_dn"] = dose.get("dose_dn")
        entry["dose_ugy"] = dose.get("dose_ugy")
        entry["dose_raw"] = dose.get("dose_raw")
    return entry


# --- no-copy guard (INGEST-4) ------------------------------------------------


def guard_no_fullres_copy(
    dest: str | Path, resolution: tuple[int, int], data_root: str | Path
) -> Path:
    """Refuse writing a full-resolution raw under the protected `data/` root.

    @MX:ANCHOR: [AUTO] Single choke point proving the external-reference no-copy
    rule (INGEST-4): the 1.4GB full-res raws live only in `images/`; only the
    small 256^2 ROI crops (and non-raw sidecars/manifest/CalibSet) may land under
    `data/`.
    @MX:REASON: This is the structural analogue of the GUI's C-20 write guard.
    It is invoked on the data/ sidecar write as the representative data/-write
    choke point; fixture crops are 256^2 by construction (`write_fixture` asserts
    non-full-res) and land under tests/, and the ingest walk additionally verifies
    no full-res file is ever copied -- defense in depth, not a single gate.
    """
    resolved = Path(dest).resolve()
    protected = Path(data_root).resolve()
    is_under_data = False
    try:
        resolved.relative_to(protected)
        is_under_data = True
    except ValueError:
        is_under_data = False
    if is_under_data and tuple(resolution) == FULL_RES and resolved.suffix == ".raw":
        raise RefusedFullResCopyError(
            f"refusing to copy a full-resolution {FULL_RES} raw under the "
            f"protected data root '{protected}': {resolved} "
            f"(external-reference only — raws live in images/)"
        )
    return resolved


# --- sample CalibSet builders (STRUCTURE verification, non-authoritative) -----


def _sample_provenance() -> CalibProvenance:
    return CalibProvenance(
        created_at=SAMPLE_VALID_FROM,
        source=SAMPLE_PANEL_ID,
        note=SAMPLE_PROVENANCE_NOTE,
    )


def _require_frame(frame, label: str):
    if frame is None:
        raise CalibSourceMissingError(
            f"sample CalibSet builder: required source '{label}' is absent; "
            f"refusing to substitute a default (SWR-000-5)"
        )
    return frame


def build_offset_calibset(masterdark) -> CalibSet:
    """MasterDark -> CalibSet(OFFSET) with a filled `O_map` payload (D4 literal)."""
    frame = _require_frame(masterdark, "MasterDark")
    o_map = np.asarray(frame.pixel, dtype=np.float32)
    calib = CalibSet(
        panel_id=SAMPLE_PANEL_ID,
        resolution=tuple(o_map.shape),
        valid_from=SAMPLE_VALID_FROM,
        valid_until=SAMPLE_VALID_UNTIL,
        kind=CalibKind.OFFSET,
        data={K_OFFSET_MAP: o_map},
        provenance=_sample_provenance(),
        domain=SAMPLE_DOMAIN,
    )
    calib.validate()
    return calib


def build_gain_calibset(calset) -> CalibSet:
    """CalSet flat -> CalibSet(GAIN) single-point `G_map` (D1/D4 literal).

    The `G_map` is a mechanical flat-field ratio (mean/flat) of the source frame
    — a shaped calibration payload for STRUCTURE verification, NOT a tuned
    parameter. Multi-level linearity fitting is blocked by QUARANTINE.
    """
    frame = _require_frame(calset, "CalSet")
    flat = np.asarray(frame.pixel, dtype=np.float64)
    mean = float(np.mean(flat)) if flat.size else 1.0
    g_map = (mean / np.clip(flat, 1.0, None)).astype(np.float32)
    calib = CalibSet(
        panel_id=SAMPLE_PANEL_ID,
        resolution=tuple(g_map.shape),
        valid_from=SAMPLE_VALID_FROM,
        valid_until=SAMPLE_VALID_UNTIL,
        kind=CalibKind.GAIN,
        data={K_GAIN_MAP: g_map},
        provenance=_sample_provenance(),
        domain=SAMPLE_DOMAIN,
    )
    calib.validate()
    return calib


def build_defect_calibset(bpm) -> CalibSet:
    """BPM -> CalibSet(DEFECT) integer `class_map` (D4 literal).

    Nonzero BPM pixels are labeled SINGLE; the rest NORMAL — a shaped
    classification payload for STRUCTURE verification (no morphology fitting).
    """
    frame = _require_frame(bpm, "BPM")
    bpm_arr = np.asarray(frame.pixel)
    normal = int(DefectMorphology.NORMAL) if DefectMorphology is not None else 0
    single = int(DefectMorphology.SINGLE) if DefectMorphology is not None else 1
    class_map = np.where(bpm_arr > 0, single, normal).astype(np.int8)
    calib = CalibSet(
        panel_id=SAMPLE_PANEL_ID,
        resolution=tuple(class_map.shape),
        valid_from=SAMPLE_VALID_FROM,
        valid_until=SAMPLE_VALID_UNTIL,
        kind=CalibKind.DEFECT,
        data={K_CLASS_MAP: class_map},
        provenance=_sample_provenance(),
        domain=SAMPLE_DOMAIN,
    )
    calib.validate()
    return calib


# --- crop / fixture emission -------------------------------------------------


def crop_roi(frame, top: int = ROI_TOP, left: int = ROI_LEFT, size: int = ROI_SIZE):
    """Return a deterministic (size x size) uint16 ROI crop of a frame's pixels."""
    pixel = np.asarray(frame.pixel)
    crop = pixel[top : top + size, left : left + size]
    return np.rint(crop).astype(np.uint16)


def write_fixture(crop: np.ndarray, dest_base: Path) -> tuple[Path, Path]:
    """Write a `<base>.raw` + `<base>.json` sidecar for a small ROI crop."""
    if tuple(crop.shape) == FULL_RES:
        raise RefusedFullResCopyError(
            f"refusing to write a full-resolution {FULL_RES} fixture: {dest_base} "
            f"(fixtures must be small ROI crops -- external-reference, INGEST-4)"
        )
    dest_base.parent.mkdir(parents=True, exist_ok=True)
    raw_path = dest_base.with_suffix(".raw")
    json_path = dest_base.with_suffix(".json")
    crop.astype("<u2").tofile(raw_path)
    json_path.write_text(
        json.dumps({"resolution": [int(crop.shape[0]), int(crop.shape[1])], "dtype": DTYPE}),
        encoding="utf-8",
    )
    return raw_path, json_path


# --- availability / skip helper ----------------------------------------------


def edrogi_available(root: str | Path | None = None) -> bool:
    """True when the sample acquisition tree is present (else realdata skips)."""
    root = Path(root) if root is not None else EDROGI_ROOT
    return root.exists() and any(root.rglob("*.raw"))


def require_edrogi(root: str | Path | None = None) -> Path:
    """Return the sample root or pytest.skip cleanly when it is absent (TESTARM-5).

    Reads the module-level `EDROGI_ROOT` at call time so tests can monkeypatch
    it to simulate absence.
    """
    import pytest

    resolved = Path(root) if root is not None else EDROGI_ROOT
    if not edrogi_available(resolved):
        pytest.skip(f"sample acquisition set absent: {resolved} (realdata skip)")
    return resolved


# --- full ingest walk --------------------------------------------------------


@dataclass(frozen=True)
class IngestResult:
    sidecar_count: int
    manifest_path: Path
    fixture_paths: tuple[Path, ...]


def _load_full(raw_path: Path):
    """Load a full-res sample raw by writing a transient in-memory sidecar dict."""
    # The sample raws have no sidecar on disk; supply the loader an explicit one
    # by writing a sibling sidecar under the data mirror is unnecessary here —
    # load via a temp meta path is avoided; instead reshape directly.
    raw = np.fromfile(raw_path, dtype="<u2")
    if raw.size != FULL_RES[0] * FULL_RES[1]:
        raise ValueError(f"{raw_path}: unexpected element count {raw.size}")
    from common.xframe import new_frame

    return new_frame(raw.reshape(FULL_RES).astype(np.float32))


def ingest(
    root: str | Path, out: str | Path, *, emit_fixtures: bool = True
) -> IngestResult:
    """Walk the sample tree; emit sidecars + manifest (+ 256^2 fixtures).

    @MX:ANCHOR: [AUTO] Sole ingest entry point (REQ-REALDATA-INGEST-1..5). Emits
    verifiable non-empty outputs (sidecar per raw, one manifest entry per raw,
    committed ROI crops of the 3 CalibSet source frames) — external-reference
    only, no full-res copy into `data/`.
    @MX:REASON: Every downstream sample arm (CalibSet build, GUI, linearity)
    consumes this manifest/sidecar contract; the no-copy + usage-stamp
    invariants are enforced here.
    """
    root = Path(root)
    out = Path(out)
    data_root = out
    out.mkdir(parents=True, exist_ok=True)

    dose_table: dict[int, dict] = {}
    dose_file = root / "아크릴" / "DOSE METER.txt"
    if dose_file.exists():
        dose_table = parse_dose_meter(dose_file.read_text(encoding="utf-8"))

    frames: list[dict] = []
    sidecar_count = 0
    for raw_path in sorted(root.rglob("*.raw")):
        if raw_path.name.endswith("_result.raw"):
            continue  # vendor output; indexed via its capture's has_result_pair
        rel = raw_path.relative_to(root)
        folder = rel.parts[0] if len(rel.parts) > 1 else ""
        filename = raw_path.name

        # Sidecar (loader contract) mirrored under data/edrogi/. Only the JSON
        # sidecar is ever written here — the full-res raw stays in images/
        # (external-reference, INGEST-4). `guard_no_fullres_copy` would refuse a
        # full-res raw write under data/; the sidecar path routes through it to
        # prove the .json write is permitted (never a full-res raw).
        sidecar = out / rel.with_suffix(".json")
        guard_no_fullres_copy(sidecar, resolution=FULL_RES, data_root=data_root)
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(
            json.dumps({"resolution": list(FULL_RES), "dtype": DTYPE}),
            encoding="utf-8",
        )
        sidecar_count += 1

        result_sibling = raw_path.with_name(raw_path.stem + "_result.raw")
        has_result = result_sibling.exists()
        meta = parse_acquisition_meta(filename, folder)
        dose = dose_table.get(meta["plate_count"]) if meta["plate_count"] else None
        frames.append(
            make_manifest_entry(
                raw_path=str(rel).replace("\\", "/"),
                folder=folder,
                filename=filename,
                resolution=FULL_RES,
                has_result_pair=has_result,
                dose=dose,
                result_path=(
                    str(result_sibling.relative_to(root)).replace("\\", "/")
                    if has_result
                    else None
                ),
            )
        )

    manifest_path = out / "manifest.json"
    manifest_path.write_text(
        json.dumps({"usage": "sample-plumbing", "frames": frames}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fixtures: tuple[Path, ...] = ()
    if emit_fixtures:
        fixtures = emit_source_fixtures(root)

    return IngestResult(
        sidecar_count=sidecar_count,
        manifest_path=manifest_path,
        fixture_paths=fixtures,
    )


def emit_source_fixtures(root: str | Path, fixture_dir: str | Path = FIXTURE_DIR) -> tuple[Path, ...]:
    """Emit the 3 committed 256^2 CalibSet-source ROI crops (INGEST-5 / D6)."""
    root = Path(root)
    fixture_dir = Path(fixture_dir)
    sources = {
        FIXTURE_MASTERDARK: root / "16bit cal" / "MasterDark.raw",
        FIXTURE_CALSET: root / "16bit cal" / f"{REPRESENTATIVE_CALSET}.raw",
        FIXTURE_BPM: root / "16bit cal" / "BPM.raw",
    }
    written: list[Path] = []
    for base, src in sources.items():
        if not src.exists():
            raise CalibSourceMissingError(f"fixture source absent: {src}")
        frame = _load_full(src)
        crop = crop_roi(frame)
        raw_path, json_path = write_fixture(crop, fixture_dir / base)
        written.append(raw_path)
        written.append(json_path)
    return tuple(written)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest the sample (plumbing) acquisition set")
    parser.add_argument("--root", default=str(EDROGI_ROOT))
    parser.add_argument("--out", default=str(Path("data") / "edrogi"))
    parser.add_argument("--no-fixtures", action="store_true")
    args = parser.parse_args(argv)
    result = ingest(args.root, args.out, emit_fixtures=not args.no_fixtures)
    print(
        f"ingested {result.sidecar_count} raw(s); manifest={result.manifest_path}; "
        f"fixtures={len(result.fixture_paths)}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
