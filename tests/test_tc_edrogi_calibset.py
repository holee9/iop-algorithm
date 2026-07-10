"""XDET-TC-041: sample CalibSet builder STRUCTURE verification (REQ-REALDATA-CALIB).

Sample-set quarantine (REQ-REALDATA-QUARANTINE): the built CalibSets are
NON-AUTHORITATIVE (`panel_id="SAMPLE-EDROGI-16BIT"`, provenance `sample=true`,
artifacts resident under `tests/`). This verifies the BUILDER WIRING only —
build -> `_calibration_gate` -> save/load round-trip — never a numeric golden.
CalSet-DN / dose values are recorded but never promoted to a constant/threshold.

The committed 256^2 source-crop path (CALIB-6/D6) is ALWAYS-ON (realdata-
independent CI). The 3072^2 arm carries the `realdata` marker and skips cleanly
when the sample tree is absent (TESTARM-5).
"""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, CalibSet
from common.io import load_raw_frame
from common.xframe import new_frame
from modules.defect import K_CLASS_MAP
from modules.gain import K_GAIN_MAP
from modules.offset import K_OFFSET_MAP
from pipeline.orchestrator import _calibration_gate
from scripts import ingest_edrogi as ing

_FIXTURE = ing.FIXTURE_DIR


def _load_fixture(base: str):
    raw = _FIXTURE / f"{base}.raw"
    meta = _FIXTURE / f"{base}.json"
    return load_raw_frame(raw, meta)


def _build_three(masterdark, calset, bpm):
    return {
        "offset": ing.build_offset_calibset(masterdark),
        "gain": ing.build_gain_calibset(calset),
        "defect": ing.build_defect_calibset(bpm),
    }


# ---------------------------------------------------------------------------
# Always-on (CALIB-6 / D6): committed 256^2 source crops -> build -> gate -> RT.
# ---------------------------------------------------------------------------


def test_committed_crops_build_gate_and_roundtrip(tmp_path):
    md = _load_fixture(ing.FIXTURE_MASTERDARK)
    cs = _load_fixture(ing.FIXTURE_CALSET)
    bp = _load_fixture(ing.FIXTURE_BPM)
    assert md.shape == (256, 256)

    calib_map = _build_three(md, cs, bp)

    # (a) schema-valid, filled payload with the confirmed D4 literals.
    calib_map["offset"].validate()
    calib_map["gain"].validate()
    calib_map["defect"].validate()
    assert K_OFFSET_MAP in calib_map["offset"].data
    assert K_GAIN_MAP in calib_map["gain"].data
    assert K_CLASS_MAP in calib_map["defect"].data

    # (b) non-authoritative labels: shared panel_id, sample provenance, kind.
    for stage, kind in (("offset", CalibKind.OFFSET), ("gain", CalibKind.GAIN), ("defect", CalibKind.DEFECT)):
        c = calib_map[stage]
        assert c.panel_id == ing.SAMPLE_PANEL_ID
        assert c.kind == kind
        assert c.resolution == (256, 256)
        assert c.valid_from and c.valid_until
        assert c.provenance is not None and "sample=true" in c.provenance.note

    # (c) the existing entry gate accepts the wiring (kind-stage/panel/res/validity).
    frame = new_frame(np.zeros((256, 256), dtype=np.float32))
    _calibration_gate(
        frame,
        calib_map,
        stages=("offset", "gain", "defect"),
        panel_id=ing.SAMPLE_PANEL_ID,
        timestamp="2026-07-11",
    )

    # (d) save -> load round-trip preserves schema + payload (VALIDATE-3).
    for stage in ("offset", "gain", "defect"):
        base = tmp_path / stage
        calib_map[stage].save(base)
        reloaded = CalibSet.load(base)
        assert reloaded.panel_id == ing.SAMPLE_PANEL_ID
        assert reloaded.kind == calib_map[stage].kind
        (key,) = list(calib_map[stage].data.keys())
        assert np.array_equal(
            np.asarray(reloaded.data[key]), np.asarray(calib_map[stage].data[key])
        )


def test_committed_crops_are_deterministic_source_frames():
    # D6: the committed fixtures are the CalibSet source crops (named per source).
    for base in (ing.FIXTURE_MASTERDARK, ing.FIXTURE_CALSET, ing.FIXTURE_BPM):
        frame = _load_fixture(base)
        arr = np.asarray(frame.pixel)
        assert arr.shape == (256, 256)
        assert np.all(np.isfinite(arr))


def test_bpm_crop_yields_single_defect_labels():
    bp = _load_fixture(ing.FIXTURE_BPM)
    defect = ing.build_defect_calibset(bp)
    labels = np.asarray(defect.data[K_CLASS_MAP])
    assert np.issubdtype(labels.dtype, np.integer)
    # non-degenerate: the BPM crop carries at least one flagged pixel.
    assert labels.max() >= 1


# ---------------------------------------------------------------------------
# Always-on (CALIB-4 / EC-3): missing source -> explicit refusal, no default.
# ---------------------------------------------------------------------------


def test_missing_source_frame_is_refused_not_defaulted():
    with pytest.raises(ing.CalibSourceMissingError):
        ing.build_offset_calibset(None)
    with pytest.raises(ing.CalibSourceMissingError):
        ing.build_gain_calibset(None)
    with pytest.raises(ing.CalibSourceMissingError):
        ing.build_defect_calibset(None)


# ---------------------------------------------------------------------------
# realdata (CALIB-1..3): full 3072^2 build -> gate -> round-trip.
# ---------------------------------------------------------------------------


@pytest.mark.realdata
def test_full_res_sample_calibset_builds_and_gates(tmp_path):
    root = ing.require_edrogi()
    cal_dir = root / "16bit cal"
    md = ing._load_full(cal_dir / "MasterDark.raw")
    cs = ing._load_full(cal_dir / f"{ing.REPRESENTATIVE_CALSET}.raw")
    bp = ing._load_full(cal_dir / "BPM.raw")

    calib_map = _build_three(md, cs, bp)
    assert calib_map["offset"].resolution == (3072, 3072)

    frame = new_frame(np.zeros((3072, 3072), dtype=np.float32))
    _calibration_gate(
        frame,
        calib_map,
        stages=("offset", "gain", "defect"),
        panel_id=ing.SAMPLE_PANEL_ID,
        timestamp="2026-07-11",
    )

    base = tmp_path / "offset_full"
    calib_map["offset"].save(base)
    reloaded = CalibSet.load(base)
    assert reloaded.resolution == (3072, 3072)
    assert np.array_equal(
        np.asarray(reloaded.data[K_OFFSET_MAP]),
        np.asarray(calib_map["offset"].data[K_OFFSET_MAP]),
    )
