"""Geometry module: Scenarios 9a/9b + 12 (REQ-LNSG-GEOM, VALIDATE-5)."""

from __future__ import annotations

import numpy as np

from common.xframe import new_frame
from modules import geometry
from tests.modules.phantoms.linesat import (
    EV_LNSG,
    dot_centroids,
    geometry_calib,
    lnsg_params,
    make_grid_phantom,
    max_grid_residual,
)


def test_scenario9a_active_correction_reduces_grid_residual():
    """REQ-LNSG-GEOM-1 / VALIDATE-5: an active polynomial correction drives the
    grid-line residual within EV-106 min (<= 1px)."""
    ph = make_grid_phantom(a=6.0, degree=2)
    assert ph.residual_px >= EV_LNSG["ev106_residual_px_max"]  # distorted enough

    # Pre-correction residual (sanity: distortion is actually visible).
    pre = max_grid_residual(dot_centroids(ph.observed), ph.centers)
    assert pre >= EV_LNSG["ev106_residual_px_max"]

    frame = new_frame(ph.observed)
    calib = geometry_calib(frame.shape, ph.coeffs_x, ph.coeffs_y, ph.residual_px)
    params = lnsg_params()
    out = geometry.process(frame, calib, params)

    post = max_grid_residual(dot_centroids(np.asarray(out.pixel)), ph.centers)
    assert post <= EV_LNSG["ev106_residual_px_max"], (pre, post)
    assert out.history[-1].extra["active"] == "true"


def test_scenario9b_inactive_passthrough_below_threshold():
    """REQ-LNSG-GEOM-2: residual below EV-106 min -> identity passthrough,
    history records the inactive marker."""
    ph = make_grid_phantom(a=0.4, degree=2)  # tiny distortion (< 1px)
    assert ph.residual_px < EV_LNSG["ev106_residual_px_max"]

    frame = new_frame(ph.observed)
    calib = geometry_calib(frame.shape, ph.coeffs_x, ph.coeffs_y, ph.residual_px)
    out = geometry.process(frame, calib, lnsg_params())

    # Identity passthrough: pixels returned unchanged.
    assert np.array_equal(np.asarray(out.pixel), np.asarray(frame.pixel))
    assert out.history[-1].extra["active"] == "false"
    assert out.history[-1].module_name == "geometry"


def test_scenario12_activation_boundary_is_deterministic():
    """REQ-LNSG-GEOM-1/2: activation is decided by residual vs the externally
    injected EV-106 min, not an invented default."""
    ph = make_grid_phantom(a=6.0, degree=2)
    frame = new_frame(ph.observed)
    calib = geometry_calib(frame.shape, ph.coeffs_x, ph.coeffs_y, ph.residual_px)

    # Raise the injected activation threshold above the residual -> inactive.
    high = lnsg_params(geometry_activation_residual_px=ph.residual_px + 1.0)
    out_hi = geometry.process(frame, calib, high)
    assert out_hi.history[-1].extra["active"] == "false"
    assert np.array_equal(np.asarray(out_hi.pixel), np.asarray(frame.pixel))

    # Lower it below the residual -> active.
    low = lnsg_params(geometry_activation_residual_px=ph.residual_px - 1.0)
    out_lo = geometry.process(frame, calib, low)
    assert out_lo.history[-1].extra["active"] == "true"
