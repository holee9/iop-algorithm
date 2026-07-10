"""XDET-TC-040: sample (plumbing-only) acquisition-set ingest (REQ-REALDATA-INGEST).

Sample-set quarantine (REQ-REALDATA-QUARANTINE): `images/에드로지16BIT/` is a
plumbing-only partial sample. These tests verify the ingest TOOLING (filename /
dose parsing, sidecar + manifest emission, no-copy guard) only — no metric is
derived, tuned, or promoted to a threshold from the sample numbers.

The pure parser / dose-normalization / no-copy-guard tests are always-on (no
real data needed). The full-walk sidecar+manifest tests carry the `realdata`
marker and skip cleanly when the sample tree is absent (REQ-REALDATA-TESTARM-5).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import ingest_edrogi as ing


# ---------------------------------------------------------------------------
# Always-on: pure filename / dose parsing (no real data required).
# ---------------------------------------------------------------------------


def test_parse_kv_ma_mas_from_acrylic_name():
    meta = ing.parse_acquisition_meta("Bright_아크릴1장_45kv100ma2.5mAs_00.raw", folder="아크릴")
    assert meta["kv"] == 45.0
    assert meta["ma"] == 100.0
    assert meta["mas"] == 2.5
    assert meta["category"] == "acrylic_step"
    assert meta["plate_count"] == 1
    assert meta["frame_index"] == 0
    assert meta["usage"] == "sample-plumbing"


def test_parse_double_v_kv_in_ghost_name():
    # GHOST names carry a "kvv" typo (75kvv320ma25.6mAs); parsing must be robust.
    meta = ing.parse_acquisition_meta(
        "Bright_ghost_75kvv320ma25.6mAs_03.raw", folder="GHOST"
    )
    assert meta["kv"] == 75.0
    assert meta["ma"] == 320.0
    assert meta["mas"] == 25.6
    assert meta["category"] == "ghost_lag"
    assert meta["frame_index"] == 3


def test_parse_calibration_frames_have_no_exposure_meta():
    for name, cat in (
        ("MasterDark.raw", "offset_dark"),
        ("CalSet_19008.raw", "gain_flat"),
        ("BPM.raw", "bad_pixel_map"),
    ):
        meta = ing.parse_acquisition_meta(name, folder="16bit cal")
        assert meta["category"] == cat
        assert meta["kv"] is None and meta["ma"] is None and meta["mas"] is None
        assert meta["usage"] == "sample-plumbing"


def test_dose_token_normalized_to_ugy_preserving_raw_token():
    # D5: normalize dose to microGy but preserve the original unit token.
    assert ing.normalize_dose_token("8.5uGy") == pytest.approx(8.5)
    assert ing.normalize_dose_token("850nGy") == pytest.approx(0.85)
    assert ing.normalize_dose_token("1.57uGy") == pytest.approx(1.57)


def test_parse_dose_meter_keys_by_plate_count():
    text = (
        "아크릴 1장 : 1700 / 8.5uGy\n"
        "아크릴 5장 : 260 / 850nGy\n"
    )
    table = ing.parse_dose_meter(text)
    assert table[1]["dose_dn"] == 1700
    assert table[1]["dose_ugy"] == pytest.approx(8.5)
    assert table[1]["dose_raw"] == "8.5uGy"
    # nGy token normalized to microGy, original token preserved (D5).
    assert table[5]["dose_ugy"] == pytest.approx(0.85)
    assert table[5]["dose_raw"] == "850nGy"


# ---------------------------------------------------------------------------
# Always-on: no-copy guard (REQ-REALDATA-INGEST-4, EC-1).
# ---------------------------------------------------------------------------


def test_fullres_copy_into_data_is_refused(tmp_path):
    data_root = tmp_path / "data" / "edrogi"
    dest = data_root / "MasterDark.raw"
    with pytest.raises(ing.RefusedFullResCopyError):
        ing.guard_no_fullres_copy(dest, resolution=(3072, 3072), data_root=tmp_path / "data")


def test_small_roi_fixture_write_into_tests_is_allowed(tmp_path):
    # The 256^2 ROI crop is the only committed binary; it is NOT a full-res copy.
    dest = tmp_path / "tests" / "fixtures" / "edrogi" / "masterdark_256.raw"
    # No exception: a 256^2 crop under tests/ is permitted.
    ing.guard_no_fullres_copy(dest, resolution=(256, 256), data_root=tmp_path / "data")


def test_manifest_entry_always_carries_sample_plumbing_usage():
    entry = ing.make_manifest_entry(
        raw_path="16bit cal/MasterDark.raw",
        folder="16bit cal",
        filename="MasterDark.raw",
        resolution=(3072, 3072),
        has_result_pair=False,
    )
    assert entry["usage"] == "sample-plumbing"
    assert entry["category"] == "offset_dark"
    assert entry["resolution"] == [3072, 3072]
    assert entry["dtype"] == "uint16"


# ---------------------------------------------------------------------------
# realdata: full-walk sidecar + manifest emission (skips when tree absent).
# ---------------------------------------------------------------------------


@pytest.mark.realdata
def test_ingest_walk_emits_sidecars_and_manifest(tmp_path):
    root = ing.require_edrogi()
    out = tmp_path / "data" / "edrogi"
    result = ing.ingest(root, out, emit_fixtures=False)

    # VALIDATE-1: non-empty, verifiable outputs (not a vacuous pass).
    assert result.sidecar_count > 0
    assert result.manifest_path.exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["frames"]) == result.sidecar_count

    # INGEST-2: every entry carries usage="sample-plumbing".
    assert all(f["usage"] == "sample-plumbing" for f in manifest["frames"])

    # INGEST-1: at least one sidecar exists with the loader-contract schema.
    a_sidecar = next(out.rglob("*.json"))
    if a_sidecar.name != "manifest.json":
        meta = json.loads(a_sidecar.read_text(encoding="utf-8"))
        assert meta["resolution"] == [3072, 3072]
        assert meta["dtype"] == "uint16"

    # INGEST-4: no full-resolution raw was copied under data/.
    copied = [p for p in out.rglob("*.raw") if p.stat().st_size > 1_000_000]
    assert not copied, f"full-res raw must never be copied into data/: {copied}"


@pytest.mark.realdata
def test_ingest_parses_acrylic_dose_into_manifest(tmp_path):
    root = ing.require_edrogi()
    out = tmp_path / "data" / "edrogi"
    result = ing.ingest(root, out, emit_fixtures=False)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    acrylic = [f for f in manifest["frames"] if f["category"] == "acrylic_step"]
    assert acrylic, "acrylic step frames must be indexed"
    # Dose reference values are display-only; present but never a threshold.
    with_dose = [f for f in acrylic if f.get("dose_ugy") is not None]
    assert with_dose, "acrylic frames must carry the parsed dose reference"
    assert all(f["dose_raw"] for f in with_dose)
