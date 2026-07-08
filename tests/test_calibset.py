"""CalibSet schema and serialization tests (REQ-INFRA-DATA-3)."""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, CalibProvenance, CalibSchemaError, CalibSet


def test_valid_calibset_passes_validation(calib):
    calib.validate()  # should not raise


def test_calibset_id_is_stable(calib):
    assert calib.calibset_id == calib.calibset_id
    assert "PANEL-A" in calib.calibset_id


@pytest.mark.parametrize(
    "mutation",
    [
        {"panel_id": ""},
        {"resolution": (0, 4)},
        {"valid_from": ""},
    ],
)
def test_invalid_schema_rejected(calib, mutation):
    from dataclasses import replace

    bad = replace(calib, **mutation)
    with pytest.raises(CalibSchemaError):
        bad.validate()


def test_resolution_match(calib):
    assert calib.matches_resolution((4, 4))
    assert not calib.matches_resolution((4, 5))


def test_npz_json_sidecar_roundtrip(tmp_path):
    """[P] format: npz + JSON sidecar save/load preserves the schema + data."""
    calib = CalibSet(
        panel_id="PANEL-B",
        resolution=(8, 8),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=CalibKind.GAIN,
        data={"gain": np.arange(64, dtype=np.float32).reshape(8, 8)},
        provenance=CalibProvenance(created_at="2026-07-08", source="unit-test"),
    )
    base = tmp_path / "calib_gain"
    npz_path, json_path = calib.save(base)
    assert npz_path.exists() and json_path.exists()

    loaded = CalibSet.load(base)
    assert loaded.panel_id == calib.panel_id
    assert loaded.resolution == calib.resolution
    assert loaded.kind == calib.kind
    assert np.array_equal(loaded.data["gain"], calib.data["gain"])
    assert loaded.provenance.source == "unit-test"
