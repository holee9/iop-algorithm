"""Numeric-provenance guard: QUARANTINE enforcement (REQ-REALDATA-VALIDATE-4).

Always-on (no real data required). This is the NUMERIC analogue of the GUI's
C-20 physical write guard (`apps.gui.io_panel.guard_output_path`): it enforces
REQ-REALDATA-QUARANTINE structurally by asserting that

  (a) no `modules/*.py` Params default references a sample-derived number,
  (b) no acceptance EV / metrics-phantom default references a sample-derived
      number,
  (c) every sample manifest entry is stamped `usage="sample-plumbing"`.

Non-vacuous (lesson L#1): the scan reports real counts (files scanned, tokens
checked, entries validated) and would FAIL if a distinctive sample CalSet-DN /
dose token were ever hardcoded as a module/EV constant, or if a manifest entry
dropped its `usage` stamp (EC-7).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import ingest_edrogi as ing

_ROOT = Path(__file__).resolve().parent.parent

# Distinctive sample-derived numbers that must NEVER become a module/EV constant
# (QUARANTINE-2/4): the 5 CalSet flat-DN levels and the DOSE METER references.
_SAMPLE_CALSET_LEVELS = ("19008", "22245", "25827", "35685", "47302")
_SAMPLE_DOSE_TOKENS = ("8.5uGy", "6.5uGy", "3.2uGy", "1.57uGy", "850nGy")
# The distinctive sample-derived tokens actually enforced by the substring scan.
# The DOSE-METER *DN* reference values (1700/1100/700/400/260) are intentionally
# NOT scanned: they are common small integers, so substring matching would raise
# false positives against unrelated code. The CalSet flat-DN levels and the
# dose-unit tokens are distinctive enough to serve as the representative
# enforcement of QUARANTINE-2/4.
_FORBIDDEN_IN_CODE = _SAMPLE_CALSET_LEVELS + _SAMPLE_DOSE_TOKENS

# Files whose numeric literals must be free of sample-derived provenance.
_MODULE_DIR = _ROOT / "modules"
_EV_SOURCES = (
    _ROOT / "tests" / "modules" / "phantoms" / "corrections.py",  # EV thresholds
    _ROOT / "tests" / "metrics" / "phantoms" / "params.py",  # metrics defaults
)


def test_a_no_module_param_default_references_sample_numbers(capsys):
    module_files = sorted(_MODULE_DIR.glob("*.py"))
    assert module_files, "expected modules/*.py to scan (guard must not be vacuous)"

    offenders: list[str] = []
    for path in module_files:
        text = path.read_text(encoding="utf-8")
        for token in _FORBIDDEN_IN_CODE:
            if token in text:
                offenders.append(f"{path.name}:{token}")

    print(
        f"[VALIDATE-4a] scanned {len(module_files)} module file(s) for "
        f"{len(_FORBIDDEN_IN_CODE)} sample token(s); offenders={offenders}"
    )
    assert not offenders, (
        f"sample-derived number(s) hardcoded in module defaults (QUARANTINE-2): {offenders}"
    )


def test_b_no_acceptance_ev_references_sample_numbers():
    scanned = 0
    offenders: list[str] = []
    for path in _EV_SOURCES:
        if not path.exists():
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8")
        for token in _FORBIDDEN_IN_CODE:
            if token in text:
                offenders.append(f"{path.name}:{token}")

    assert scanned > 0, "expected EV / metrics-default sources to scan"
    assert not offenders, (
        f"sample-derived number(s) in acceptance EV / metrics defaults (QUARANTINE-4): {offenders}"
    )


def test_c_every_manifest_entry_is_sample_plumbing():
    # Build real manifest entries from the committed CalibSet-source fixtures.
    fixtures = [
        ("16bit cal", "masterdark_256.raw"),
        ("16bit cal", "calset_19008_256.raw"),
        ("16bit cal", "bpm_256.raw"),
    ]
    entries = [
        ing.make_manifest_entry(
            raw_path=f"{folder}/{name}",
            folder=folder,
            filename=name,
            resolution=(256, 256),
            has_result_pair=False,
        )
        for folder, name in fixtures
    ]
    assert entries, "guard must validate a non-empty manifest (L#1)"
    assert all(e["usage"] == "sample-plumbing" for e in entries)


def test_c_make_manifest_entry_always_stamps_usage():
    # QUARANTINE enforcement (EC-7): the manifest builder has NO code path that
    # yields a sample entry without the usage stamp, regardless of inputs.
    for resolution in [(3072, 3072), (256, 256)]:
        entry = ing.make_manifest_entry(
            raw_path="nps/Bright_NPS_00.raw",
            folder="nps",
            filename="Bright_NPS_00.raw",
            resolution=resolution,
            has_result_pair=True,
        )
        assert entry["usage"] == "sample-plumbing"


def test_sample_calibsets_are_labeled_non_authoritative():
    # QUARANTINE-3 label enforcement: sample panel_id + provenance sample marker.
    import numpy as np

    from common.xframe import new_frame

    frame = new_frame(np.ones((8, 8), dtype=np.float32))
    calib = ing.build_offset_calibset(frame)
    assert calib.panel_id == "SAMPLE-EDROGI-16BIT"
    assert calib.provenance is not None
    assert "sample=true" in calib.provenance.note
