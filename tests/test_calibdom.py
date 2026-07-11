"""XDET-TC-060..062, 066, 067: CalibSet domain/beam_quality descriptors.

Covers the additive, behavior-preserving descriptor contract (SPEC-CALDOM-001):

  - TC-060: schema defaults (UNSPECIFIED / None) + specified-descriptor validate.
  - TC-061: a legacy JSON sidecar without the descriptor keys loads with the
    defaults and passes validate() (no unauthorized failure).
  - TC-062: a save/load round-trip preserves the descriptors AND keeps the npz
    payload, the legacy meta keys, and the `calibset_id` format unchanged.
  - TC-066: the ingest SAMPLE builders stamp domain=MEDICAL while staying
    non-authoritative (SAMPLE panel_id, provenance sample=true, beam_quality None).
  - TC-067: the SWR-000-10 schema clause and the CalibSet docstring both
    enumerate the descriptors, and the enumerated domain values match the code.

Plus the negative/edge cases: invalid descriptor detection (EC-5), an
unrecognized domain string on load failing explicitly (D3), and legacy defaults
surviving a re-save round-trip (EC-4). Evidence is REAL (lesson L#1): actual
round-trip equality and actual raised errors, never a vacuous pass.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from common.calibset import (
    CalibDomain,
    CalibKind,
    CalibProvenance,
    CalibSchemaError,
    CalibSet,
)

_ROOT = Path(__file__).resolve().parent.parent


def _mk(
    *,
    domain: CalibDomain = CalibDomain.UNSPECIFIED,
    beam_quality: str | None = None,
    with_descriptors: bool = True,
) -> CalibSet:
    """A small valid CalibSet with a real ndarray payload.

    `with_descriptors=False` constructs it the pre-descriptor way (no domain /
    beam_quality kwargs) to prove defaults for legacy call sites.
    """
    common = dict(
        panel_id="PANEL-A",
        resolution=(4, 4),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=CalibKind.OFFSET,
        data={"map": np.zeros((4, 4), dtype=np.float32)},
        provenance=CalibProvenance(created_at="2026-07-11", source="unit-test"),
    )
    if with_descriptors:
        return CalibSet(**common, domain=domain, beam_quality=beam_quality)
    return CalibSet(**common)


# --- TC-060: schema defaults + specified-descriptor validate ------------------


def test_tc060_legacy_construction_gets_default_descriptors():
    calib = _mk(with_descriptors=False)
    assert calib.domain == CalibDomain.UNSPECIFIED
    assert calib.beam_quality is None
    calib.validate()  # must not raise


def test_tc060_specified_descriptors_validate():
    calib = _mk(domain=CalibDomain.MEDICAL, beam_quality="RQA5")
    calib.validate()
    assert calib.domain == CalibDomain.MEDICAL
    assert calib.beam_quality == "RQA5"


def test_tc060_domain_is_a_closed_str_enum():
    assert {m.value for m in CalibDomain} == {"medical", "ndt", "unspecified"}
    # str-enum precedent (CalibKind): the value compares equal to its string.
    assert CalibDomain.MEDICAL == "medical"


# --- EC-5: invalid descriptor detection ---------------------------------------


def test_ec5_non_calibdomain_domain_rejected():
    bad = replace(_mk(), domain="medical")  # raw string, not a CalibDomain member
    with pytest.raises(CalibSchemaError):
        bad.validate()


def test_ec5_empty_beam_quality_rejected():
    bad = replace(_mk(), beam_quality="")
    with pytest.raises(CalibSchemaError):
        bad.validate()


def test_ec5_existing_schema_checks_unchanged():
    # A pre-existing structural error still surfaces as CalibSchemaError.
    with pytest.raises(CalibSchemaError):
        replace(_mk(), panel_id="").validate()


# --- TC-061: legacy JSON (no descriptor keys) loads with defaults -------------


def test_tc061_legacy_sidecar_without_descriptor_keys_loads_defaults(tmp_path):
    calib = _mk(domain=CalibDomain.MEDICAL, beam_quality="RQA5")
    _, json_path = calib.save(tmp_path / "legacy")
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    # Simulate a pre-descriptor sidecar: the new keys simply do not exist.
    meta.pop("domain", None)
    meta.pop("beam_quality", None)
    json_path.write_text(json.dumps(meta), encoding="utf-8")

    loaded = CalibSet.load(tmp_path / "legacy")
    assert loaded.domain == CalibDomain.UNSPECIFIED
    assert loaded.beam_quality is None
    loaded.validate()  # legacy payload remains valid


def test_d3_unrecognized_domain_string_on_load_fails_explicitly(tmp_path):
    calib = _mk()
    _, json_path = calib.save(tmp_path / "bogus")
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    meta["domain"] = "not-a-real-domain"
    json_path.write_text(json.dumps(meta), encoding="utf-8")
    # No silent default substitution — the load path raises loudly.
    with pytest.raises((ValueError, CalibSchemaError)):
        CalibSet.load(tmp_path / "bogus")


# --- TC-062: round-trip preservation + format invariance ----------------------


def test_tc062_roundtrip_preserves_descriptors_and_payload(tmp_path):
    calib = CalibSet(
        panel_id="PANEL-B",
        resolution=(8, 8),
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=CalibKind.GAIN,
        data={"gain": np.arange(64, dtype=np.float32).reshape(8, 8)},
        provenance=CalibProvenance(created_at="2026-07-11", source="unit-test"),
        domain=CalibDomain.NDT,
        beam_quality="E2597-classA",
    )
    id_before = calib.calibset_id
    calib.save(tmp_path / "rt")
    loaded = CalibSet.load(tmp_path / "rt")

    # Descriptors preserved.
    assert loaded.domain == CalibDomain.NDT
    assert loaded.beam_quality == "E2597-classA"
    # Existing payload + meta preserved.
    assert loaded.panel_id == calib.panel_id
    assert loaded.resolution == calib.resolution
    assert loaded.kind == calib.kind
    assert np.array_equal(loaded.data["gain"], calib.data["gain"])
    assert loaded.provenance.source == "unit-test"
    # calibset_id format unchanged (descriptors NOT embedded in the id).
    assert loaded.calibset_id == id_before
    assert "ndt" not in loaded.calibset_id and "E2597" not in loaded.calibset_id


def test_tc062_save_adds_only_new_meta_keys(tmp_path):
    calib = _mk(domain=CalibDomain.MEDICAL, beam_quality="RQA5")
    _, json_path = calib.save(tmp_path / "keys")
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    legacy_keys = {
        "panel_id",
        "resolution",
        "valid_from",
        "valid_until",
        "kind",
        "data_keys",
        "provenance",
    }
    # Legacy keys intact; exactly the two descriptors added.
    assert legacy_keys.issubset(meta.keys())
    assert set(meta.keys()) == legacy_keys | {"domain", "beam_quality"}
    assert meta["domain"] == "medical"
    assert meta["beam_quality"] == "RQA5"


def test_ec4_legacy_defaults_survive_resave(tmp_path):
    calib = _mk()  # UNSPECIFIED / None
    calib.save(tmp_path / "a")
    loaded = CalibSet.load(tmp_path / "a")
    loaded.save(tmp_path / "b")
    reloaded = CalibSet.load(tmp_path / "b")
    assert reloaded.domain == CalibDomain.UNSPECIFIED
    assert reloaded.beam_quality is None
    assert np.array_equal(reloaded.data["map"], calib.data["map"])


# --- TC-066: SAMPLE builders stamp MEDICAL, stay non-authoritative ------------


def test_tc066_sample_builders_stamp_medical_non_authoritative():
    from common.xframe import new_frame
    from scripts import ingest_edrogi as ing

    frame = new_frame(np.ones((8, 8), dtype=np.float32))
    builders = (
        ing.build_offset_calibset,
        ing.build_gain_calibset,
        ing.build_defect_calibset,
    )
    for build in builders:
        calib = build(frame)
        # Domain stamped explicitly (not relying on the default).
        assert calib.domain == CalibDomain.MEDICAL
        # No validated metrology basis -> beam_quality stays None.
        assert calib.beam_quality is None
        # Non-authoritative markers unchanged (QUARANTINE).
        assert calib.panel_id == ing.SAMPLE_PANEL_ID
        assert calib.provenance is not None
        assert "sample=true" in calib.provenance.note
        calib.validate()


# --- TC-067: doc / docstring enumerate descriptors, values match code ---------


def _swr_00010_row() -> str:
    doc = _ROOT / "docs" / "XDET_SWR_spec_v1.2.md"
    text = doc.read_text(encoding="utf-8")
    rows = [ln for ln in text.splitlines() if "SWR-000-10" in ln]
    assert rows, "SWR-000-10 clause must exist in the schema doc"
    return rows[0]


def test_tc067_swr_00010_clause_enumerates_descriptors():
    row = _swr_00010_row()
    assert "domain" in row
    assert "beam_quality" in row
    # Every code-side domain value is enumerated in the doc (no drift).
    for member in CalibDomain:
        assert member.value in row, f"domain value {member.value!r} missing from SWR-000-10"
    # Metrology reference beam-quality example present.
    assert "RQA5" in row


def test_tc067_calibset_docstring_enumerates_descriptors():
    doc = CalibSet.__doc__ or ""
    assert "domain" in doc
    assert "beam_quality" in doc
    for member in CalibDomain:
        assert member.value in doc, f"domain value {member.value!r} missing from CalibSet docstring"


def test_tc067_doc_and_code_domain_values_agree():
    # The doc's enumerated set and the code's enum must be the SAME closed set.
    row = _swr_00010_row()
    code_values = {m.value for m in CalibDomain}
    assert code_values == {"medical", "ndt", "unspecified"}
    for value in code_values:
        assert value in row
