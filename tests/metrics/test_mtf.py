"""MTF edge-method reproduction and edge cases (Scenario 2, 9; EC-1)."""

from __future__ import annotations

import numpy as np
import pytest

from metrics import mtf
from metrics.result import MetricReadError
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import TOLERANCES, make_params


def test_scenario2_mtf_reproduces_analytic_curve():
    """Presampled MTF reproduces the analytic Gaussian MTF within [T]."""
    phantom = gen.make_slanted_edge(angle_deg=2.0, sigma_px=0.6)
    params = make_params()
    result = mtf.compute_mtf(phantom.frame, params, calibset_id="CS-MTF")

    freqs = result.get("frequencies_lpmm")
    got = result.get("mtf")
    expected = phantom.analytic_mtf(freqs)
    # Compare over 0 .. Nyquist (the panel-derived band).
    nyq = result.get("nyquist_lpmm")
    band = freqs <= nyq
    assert np.max(np.abs(got[band] - expected[band])) < TOLERANCES["mtf_abs"]


def test_scenario2_mtf_at_nyquist():
    """MTF@3.57 lp/mm reproduces the analytic Nyquist value."""
    phantom = gen.make_slanted_edge(angle_deg=2.2, sigma_px=0.6)
    params = make_params()
    result = mtf.compute_mtf(phantom.frame, params)
    nyq = result.get("nyquist_lpmm")
    assert abs(nyq - 3.5714) < 1e-2  # 1/(2*0.14)
    expected = float(phantom.analytic_mtf(np.array([nyq]))[0])
    assert abs(result.get("mtf_at_nyquist") - expected) < TOLERANCES["mtf_nyquist_abs"]


def test_angle_estimation_is_automatic():
    """Edge angle is recovered without human input, within the phantom tilt."""
    phantom = gen.make_slanted_edge(angle_deg=2.5, sigma_px=0.6)
    result = mtf.compute_mtf(phantom.frame, make_params())
    assert abs(result.get("edge_angle_deg") - 2.5) < 0.3


def test_ec1_angle_out_of_range_rejected():
    """EC-1(a): angle outside [1.5,3] deg -> explicit MetricReadError."""
    phantom = gen.make_slanted_edge(angle_deg=10.0, sigma_px=0.6)
    with pytest.raises(MetricReadError):
        mtf.compute_mtf(phantom.frame, make_params())


def test_ec1_angle_near_boundary_warns():
    """EC-1(b): in-range but within margin -> computed WITH a warning."""
    # 1.6 deg is within 0.2 deg of the 1.5 lower boundary.
    phantom = gen.make_slanted_edge(angle_deg=1.6, sigma_px=0.6)
    result = mtf.compute_mtf(phantom.frame, make_params())
    assert result.warnings, "boundary-proximity must emit a warning"
    assert result.get("mtf") is not None  # still computed (not rejected)


def test_scenario9_directional_mtf():
    """MTF-5 Optional: horizontal-direction MTF is produced when requested.

    A horizontal edge is a vertical edge transposed; `direction="horizontal"`
    transposes it back so the near-vertical estimator applies.
    """
    from common.xframe import new_frame

    vertical = gen.make_slanted_edge(angle_deg=2.0, sigma_px=0.6)
    horizontal_frame = new_frame(np.asarray(vertical.frame.pixel).T.copy())
    result = mtf.compute_mtf(horizontal_frame, make_params(), direction="horizontal")
    assert result.get("direction") == "horizontal"
    # Same analytic MTF along the transposed axis.
    freqs = result.get("frequencies_lpmm")
    expected = vertical.analytic_mtf(freqs)
    nyq = result.get("nyquist_lpmm")
    band = freqs <= nyq
    assert np.max(np.abs(result.get("mtf")[band] - expected[band])) < TOLERANCES["mtf_abs"]
