"""XDET-TC-042/043 sample linearity + SNRn SANITY arms (REQ-REALDATA-TESTARM-3/4).

[HARD] QUARANTINE (D2): the acrylic step + minimum-dose frames are a plumbing
sample. These arms are SANITY GATES ONLY — plate-count monotonicity (더 많은
장수 -> 더 큰 감쇠 -> 더 낮은 신호), finiteness, non-degeneracy, and a physically
plausible band. The `DOSE METER` reference is display-only and NEVER promoted to
a threshold; the absolute tolerance and the DN-vs-µGy decision axis are
run-deferred, and fitting from this sample is BLOCKED (guiding set only —
QUARANTINE-2/4). Every arm skips cleanly when the sample tree is absent.
"""

from __future__ import annotations

import re

import numpy as np
import pytest

from common.contract import Params
from metrics.ndt import compute_snr, compute_snrn
from scripts import ingest_edrogi as ing
from tests.metrics.phantoms.params import _DEFAULTS

pytestmark = pytest.mark.realdata

_PLATE_RE = re.compile(r"아크릴(\d+)장")
# Fixed central uniform ROI (geometry choice, not a fitted value).
_ROI = (1408, 1408, 256, 256)


def _median_dn(frame, roi=_ROI):
    t, l, h, w = roi
    region = np.asarray(frame.pixel, dtype=np.float64)[t : t + h, l : l + w]
    return float(np.median(region))


# -- XDET-TC-042: acrylic step-phantom monotonicity sanity --------------------


def test_tc_042_acrylic_plate_monotonicity_sanity():
    root = ing.require_edrogi()
    by_plate: dict[int, list[float]] = {}
    for raw in sorted((root / "아크릴").glob("*.raw")):
        if raw.name.endswith("_result.raw"):
            continue
        m = _PLATE_RE.search(raw.name)
        if not m:
            continue
        by_plate.setdefault(int(m.group(1)), []).append(_median_dn(ing._load_full(raw)))

    if len(by_plate) < 2:
        pytest.skip("insufficient acrylic plate-count coverage")

    plates = sorted(by_plate)
    means = [float(np.mean(by_plate[p])) for p in plates]

    # finite + non-degenerate
    assert all(np.isfinite(v) for v in means)
    assert max(means) > min(means)  # non-degenerate spread
    # physically plausible band for a 16-bit panel
    assert all(0.0 < v < 65535.0 for v in means)
    # sanity monotonicity: more plates -> more attenuation -> lower signal.
    assert all(earlier > later for earlier, later in zip(means, means[1:])), (
        f"expected monotonic signal decrease with plate count, got {list(zip(plates, means))}"
    )


# -- XDET-TC-043: minimum-dose SNRn sanity ------------------------------------


def test_tc_043_min_dose_snrn_sanity():
    frame = _min_dose_frame()
    params = Params(_DEFAULTS)  # ndt_srb_norm_um = 88.6 (IEC constant, not sample-derived)

    snr, mean, std = compute_snr(frame, _ROI, params)
    assert np.isfinite(snr) and np.isfinite(mean) and np.isfinite(std)
    assert std > 0.0  # non-degenerate noise floor (dark-current-limited region)
    assert snr > 0.0

    # Fixed placeholder SRb (non-authoritative) exercises the SNRn engine path.
    result = compute_snrn(frame, _ROI, srb_um=88.6, params=params)
    snrn = float(result.get("snrn"))
    assert np.isfinite(snrn) and snrn > 0.0


def _min_dose_frame():
    root = ing.require_edrogi()
    for raw in sorted((root / "최소선량선형").glob("*.raw")):
        if not raw.name.endswith("_result.raw"):
            return ing._load_full(raw)
    pytest.skip("no minimum-dose frames")
