"""Tests for metrics.scatter_kernel: dual-Gaussian CalibSet(SCATTER) builder.

Covers the offline builder (REQ-VGRID-CALIB-1), degenerate-kernel refusal
(SWR-000-5), the ⚠P provenance note (REQ-VGRID-CALIB-3 / Scenario 8), and the
avoidance-alternative builder-side substitution path (fit-from-samples emits the
identical CalibSet schema).
"""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, K_SCATTER_AMP, K_SCATTER_SIGMA
from metrics.scatter_kernel import (
    PATENT_PROVENANCE_NOTE,
    ScatterKernelCalibrationError,
    build_scatter_kernel,
    fit_scatter_kernel_from_samples,
)

SHAPE = (96, 96)

_KW = dict(
    panel_id="PANEL-A",
    resolution=SHAPE,
    valid_from="2026-01-01",
    valid_until="2027-01-01",
)

_PARAMS = dict(
    spr_per_cm=0.05,
    spr_max=0.6,
    sigma_narrow_px=1.0,
    sigma_wide_px=3.5,
    wide_fraction=0.5,
    thickness_sigma_gain_per_cm=0.02,
    kv_sigma_ref=100.0,
)


def test_build_emits_scatter_calibset_with_dual_gaussian_payload():
    calib = build_scatter_kernel(8.0, 100.0, **_KW, **_PARAMS)
    assert calib.kind is CalibKind.SCATTER
    assert K_SCATTER_AMP in calib.data and K_SCATTER_SIGMA in calib.data
    amp = np.asarray(calib.data[K_SCATTER_AMP])
    sigma = np.asarray(calib.data[K_SCATTER_SIGMA])
    assert amp.shape == (2,) and sigma.shape == (2,)
    assert float(amp.sum()) < 1.0  # SPR < 1 (SKS convergence)
    assert np.all(sigma > 0.0)


def test_spr_grows_with_thickness_and_saturates():
    thin = build_scatter_kernel(2.0, 100.0, **_KW, **_PARAMS)
    thick = build_scatter_kernel(8.0, 100.0, **_KW, **_PARAMS)
    thin_spr = float(np.asarray(thin.data[K_SCATTER_AMP]).sum())
    thick_spr = float(np.asarray(thick.data[K_SCATTER_AMP]).sum())
    assert thick_spr > thin_spr
    # saturates at spr_max
    huge = build_scatter_kernel(100.0, 100.0, **_KW, **_PARAMS)
    assert float(np.asarray(huge.data[K_SCATTER_AMP]).sum()) == pytest.approx(0.6)


def test_higher_kv_broadens_scatter_spread():
    low_kv = build_scatter_kernel(8.0, 80.0, **_KW, **_PARAMS)
    high_kv = build_scatter_kernel(8.0, 120.0, **_KW, **_PARAMS)
    assert np.all(
        np.asarray(high_kv.data[K_SCATTER_SIGMA])
        > np.asarray(low_kv.data[K_SCATTER_SIGMA])
    )


def test_patent_provenance_note_recorded():
    """Scenario 8: ⚠P provenance recorded for release-gate patent traceability."""
    calib = build_scatter_kernel(8.0, 100.0, **_KW, **_PARAMS)
    assert calib.provenance is not None
    assert "US 11,911,202" in calib.provenance.note
    assert PATENT_PROVENANCE_NOTE in calib.provenance.note


def test_degenerate_spr_over_one_refused():
    with pytest.raises(ScatterKernelCalibrationError, match="ratio"):
        build_scatter_kernel(
            8.0, 100.0, **_KW, **{**_PARAMS, "spr_per_cm": 0.5, "spr_max": 2.0}
        )


def test_zero_thickness_refused():
    with pytest.raises(ScatterKernelCalibrationError):
        build_scatter_kernel(0.0, 100.0, **_KW, **_PARAMS)


def test_fit_from_samples_emits_identical_schema():
    """REQ-VGRID-CALIB-3: the avoidance-alternative builder path emits the same
    CalibSet(SCATTER) schema (builder-side substitution, no module redesign)."""
    from scipy import ndimage

    rng = np.random.default_rng(0)
    primary = 800.0 + 400.0 * rng.random(SHAPE)
    amp_true = np.array([0.2, 0.3])
    sigma = (8.0, 28.0)
    scatter = amp_true[0] * ndimage.gaussian_filter(
        primary, sigma[0], mode="reflect"
    ) + amp_true[1] * ndimage.gaussian_filter(primary, sigma[1], mode="reflect")
    calib = fit_scatter_kernel_from_samples(primary, scatter, sigma, **_KW)
    assert calib.kind is CalibKind.SCATTER
    fitted = np.asarray(calib.data[K_SCATTER_AMP])
    np.testing.assert_allclose(fitted, amp_true, atol=1e-3)
    assert PATENT_PROVENANCE_NOTE in calib.provenance.note
