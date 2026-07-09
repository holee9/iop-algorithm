"""T9 thickness correction mechanics (SPEC-NDT-001 Scenario 5; EC-2).

Low-frequency gradient flattening with high-frequency defect-band preservation
(REQ-NDT-THICK-1/-2) and the no-gradient / oversized-scale passthrough with a
warning (REQ-NDT-THICK-3). The deterministic MTF@Nyquist / SRb / CSa hard gates
live in the XDET-TC-019 release gate (tests/metrics/test_tc_ndt.py).
"""

from __future__ import annotations

import numpy as np
import pytest

from metrics.ndt import correct_thickness
from metrics.result import MetricReadError
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import TOLERANCES, make_params


def _row_mean_range(image: np.ndarray, rows=slice(24, 104)) -> float:
    """Peak-to-peak of the along-column row means (the vertical trend range)."""
    prof = image[rows, :].mean(axis=1)
    return float(prof.max() - prof.min())


def test_correct_thickness_removes_low_freq_gradient_gaussian():
    """The vertical thickness ramp is flattened away (Gaussian estimator)."""
    ph = gen.make_thickness_defect_phantom()
    params = make_params(ndt_thickness_method="gaussian", ndt_thickness_scale_px=20)
    res = correct_thickness(ph.frame, params)

    raw = np.asarray(ph.frame.pixel, dtype=np.float64)
    before = _row_mean_range(raw)
    after = _row_mean_range(res.flattened)
    assert res.changed
    assert after < 0.1 * before, (before, after)


def test_correct_thickness_preserves_defect_default_opening():
    """DEFAULT morphological opening preserves the high-frequency defect band."""
    ph = gen.make_thickness_defect_phantom()
    params = make_params()  # default method = morphological_opening
    res = correct_thickness(ph.frame, params)

    raw = np.asarray(ph.frame.pixel, dtype=np.float64)
    amp_before = ph.defect_amplitude(raw)
    amp_after = ph.defect_amplitude(res.flattened)
    rel = abs(amp_after - ph.known_defect_amp) / ph.known_defect_amp
    assert rel <= TOLERANCES["thickness_defect_rel"], (amp_before, amp_after)


def test_correct_thickness_preserves_defect_gaussian():
    ph = gen.make_thickness_defect_phantom()
    params = make_params(ndt_thickness_method="gaussian", ndt_thickness_scale_px=20)
    res = correct_thickness(ph.frame, params)
    amp_after = ph.defect_amplitude(res.flattened)
    rel = abs(amp_after - ph.known_defect_amp) / ph.known_defect_amp
    assert rel <= TOLERANCES["thickness_defect_rel"], amp_after


def test_correct_thickness_input_frame_unchanged():
    """The input XFrame is consumed read-only (measurement-local copy out)."""
    ph = gen.make_thickness_defect_phantom()
    before = np.asarray(ph.frame.pixel, dtype=np.float64).copy()
    correct_thickness(ph.frame, make_params())
    assert np.array_equal(np.asarray(ph.frame.pixel, dtype=np.float64), before)


# -- EC-2: no gradient / oversized scale -> numerically unchanged + warning -----


def test_ec2_no_gradient_passthrough_unchanged():
    frame = gen.make_flat_frame()
    params = make_params()
    res = correct_thickness(frame, params)
    assert not res.changed
    assert res.warnings
    original = np.asarray(frame.pixel, dtype=np.float64)
    assert np.array_equal(res.flattened, original)


def test_ec2_oversized_scale_passthrough_unchanged():
    ph = gen.make_thickness_defect_phantom()
    params = make_params(ndt_thickness_scale_px=200)  # >= frame size 128
    res = correct_thickness(ph.frame, params)
    assert not res.changed
    assert any("scale" in w for w in res.warnings)
    original = np.asarray(ph.frame.pixel, dtype=np.float64)
    assert np.array_equal(res.flattened, original)


def test_unknown_thickness_method_rejected():
    ph = gen.make_thickness_defect_phantom()
    params = make_params(ndt_thickness_method="wavelet", ndt_thickness_scale_px=20)
    with pytest.raises(MetricReadError):
        correct_thickness(ph.frame, params)


def test_missing_scale_param_rejected():
    ph = gen.make_thickness_defect_phantom()
    params = make_params(ndt_thickness_scale_px=None)
    with pytest.raises(MetricReadError):
        correct_thickness(ph.frame, params)
