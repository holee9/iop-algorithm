"""XDET-TC-001..007 sample (plumbing-only) arms (REQ-REALDATA-TESTARM-1/2).

These are the in-place sample arms for the existing release-gate TC ids
XDET-TC-001/002/003 (offset/gain/defect), XDET-TC-004/005 (GHOST lag) and
XDET-TC-006/007 (NPS/NNPS). The synthetic release gates for the SAME ids remain
live and untouched under tests/modules/ + tests/metrics/ (REQ-REALDATA-TESTARM-6);
these add the parallel sample arm only.

[HARD] QUARANTINE: the sample set is NON-AUTHORITATIVE. Assertions are SANITY
ONLY (shape (3072,3072) / float32 / finite / non-degenerate) — no metric is
compared against a golden, no tolerance is fitted, no `_result` frame is used as
a numeric reference (REQ-REALDATA-CONTRACT-3, QUARANTINE-2/3/4). Every sample
arm skips cleanly when `images/에드로지16BIT/` is absent (TESTARM-5).

Engine constants come from the IEC/standard-derived metrics phantom defaults —
NOT from the sample images.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, CalibProvenance, CalibSet, K_IRF_A, K_IRF_B
from common.contract import Params
from metrics import nps
from modules import defect, gain, offset
from modules.lag import LagCorrector
from scripts import ingest_edrogi as ing
from tests.metrics.phantoms.params import _DEFAULTS
from tests.modules.phantoms.corrections import corr_params

pytestmark = pytest.mark.realdata

_CAL_DIR = "16bit cal"


def _cal_frame(name: str):
    root = ing.require_edrogi()
    return ing._load_full(root / _CAL_DIR / name)


def _first_raw(folder: str):
    root = ing.require_edrogi()
    for raw in sorted((root / folder).rglob("*.raw")):
        if not raw.name.endswith("_result.raw"):
            return ing._load_full(raw)
    pytest.skip(f"no raw frame under {folder}")


def _assert_sane(frame):
    arr = np.asarray(frame.pixel)
    assert arr.shape == (3072, 3072)
    assert arr.dtype == np.float32
    assert np.all(np.isfinite(arr))
    assert float(np.std(arr)) > 0.0  # non-degenerate


# -- XDET-TC-001: offset arm (real acrylic frame - real MasterDark OFFSET) ----


def test_tc_001_offset_arm_sanity():
    signal = _first_raw("아크릴")
    calib = ing.build_offset_calibset(_cal_frame("MasterDark.raw"))
    out = offset.process(signal, calib, corr_params())
    _assert_sane(out)


# -- XDET-TC-002: gain arm (single-point G_map from CalSet_19008) -------------


def test_tc_002_gain_arm_sanity():
    signal = _first_raw("아크릴")
    calib = ing.build_gain_calibset(_cal_frame(f"{ing.REPRESENTATIVE_CALSET}.raw"))
    out = gain.process(signal, calib, corr_params())
    _assert_sane(out)


# -- XDET-TC-003: defect arm (BPM DEFECT map). Full-res Python interp loop over
#    ~1.75e4 flagged pixels -> marked slow so `-m realdata` (no slow) stays fast.


@pytest.mark.slow
def test_tc_003_defect_arm_sanity():
    signal = _first_raw("아크릴")
    calib = ing.build_defect_calibset(_cal_frame("BPM.raw"))
    out = defect.process(signal, calib, corr_params())
    _assert_sane(out)


# -- XDET-TC-004/005: GHOST decay-series lag arm. Non-authoritative fixed IRF
#    (NOT fitted from the sample; a decaying placeholder) proves the recursion
#    code path runs on the real GHOST frames (QUARANTINE: no IRF fitting).


def _placeholder_lag_calib(resolution):
    return CalibSet(
        panel_id=ing.SAMPLE_PANEL_ID,
        resolution=tuple(resolution),
        valid_from=ing.SAMPLE_VALID_FROM,
        valid_until=ing.SAMPLE_VALID_UNTIL,
        kind=CalibKind.LAG,
        # Fixed placeholder IRF (single decaying term), documented non-authoritative.
        data={K_IRF_A: np.array([0.05], dtype=np.float64), K_IRF_B: np.array([0.5], dtype=np.float64)},
        provenance=CalibProvenance(
            created_at=ing.SAMPLE_VALID_FROM, source=ing.SAMPLE_PANEL_ID, note=ing.SAMPLE_PROVENANCE_NOTE
        ),
    )


def test_tc_004_005_ghost_lag_arm_sanity():
    root = ing.require_edrogi()
    ghost = sorted(
        p for p in (root / "GHOST").glob("*.raw") if not p.name.endswith("_result.raw")
    )
    if len(ghost) < 2:
        pytest.skip("insufficient GHOST decay-series frames")
    corrector = LagCorrector()  # one instance == the sequence (between-seq reset)
    calib = _placeholder_lag_calib((3072, 3072))
    out = None
    for raw in ghost[:2]:  # first two frames of the decay series is enough for sanity
        frame = ing._load_full(raw)
        out = corrector.process(frame, calib, Params())
    _assert_sane(out)


# -- XDET-TC-006/007: NPS/NNPS arm on the Bright_NPS flat ensemble ------------


def test_tc_006_007_nps_nnps_arm_sanity():
    root = ing.require_edrogi()
    frames = [
        ing._load_full(p)
        for p in sorted((root / "nps").glob("*.raw"))
        if not p.name.endswith("_result.raw")
    ]
    if not frames:
        pytest.skip("no NPS flat frames")
    result = nps.compute_nps(frames, Params(_DEFAULTS))
    nps1d = np.asarray(result.get("nps"))
    nnps1d = np.asarray(result.get("nnps"))
    # sanity: finite, non-degenerate, physically non-negative power spectra.
    assert nps1d.size > 0 and np.all(np.isfinite(nps1d))
    assert np.all(np.isfinite(nnps1d))
    assert float(np.nanmax(nps1d)) > 0.0
