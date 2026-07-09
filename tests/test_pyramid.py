"""common/pyramid.py — Laplacian pyramid unit tests (SWR-801, REQ-POST-MSE-1).

Scenario 4: the shared component decomposes/reconstructs and an unmodulated round
trip restores the input within numerical tolerance (perfect reconstruction).
"""

from __future__ import annotations

import numpy as np
import pytest

from common import pyramid


def _phantom(shape=(64, 48), seed=0):
    rng = np.random.default_rng(seed)
    ys, xs = np.mgrid[0 : shape[0], 0 : shape[1]]
    smooth = 100.0 + 50.0 * np.sin(xs / 7.0) + 30.0 * np.cos(ys / 5.0)
    return smooth + rng.normal(0.0, 2.0, size=shape)


def test_build_pyramid_band_count():
    img = _phantom()
    pyr = pyramid.build_pyramid(img, levels=4)
    # levels detail bands + 1 residual.
    assert len(pyr) == 5
    # First band has the input shape; residual is the smallest.
    assert pyr[0].shape == img.shape
    assert pyr[-1].size <= pyr[0].size


def test_perfect_reconstruction_within_tolerance():
    img = _phantom((64, 64), seed=1)
    for levels in (1, 3, 7):
        pyr = pyramid.build_pyramid(img, levels=levels)
        recon = pyramid.reconstruct_pyramid(pyr)
        assert recon.shape == img.shape
        assert np.max(np.abs(recon - img)) < 1e-9, levels


def test_reconstruction_non_square_odd_dims():
    img = _phantom((45, 37), seed=2)  # odd, non-square exercises decimation edges
    pyr = pyramid.build_pyramid(img, levels=5)
    recon = pyramid.reconstruct_pyramid(pyr)
    assert np.max(np.abs(recon - img)) < 1e-9


def test_levels_must_be_positive():
    with pytest.raises(ValueError):
        pyramid.build_pyramid(_phantom(), levels=0)


def test_constant_field_has_zero_detail_bands():
    # EXPAND(REDUCE(constant)) == constant, so every bandpass detail band of a
    # flat field is zero (interior); the residual carries the DC. This is the
    # property the DRC low-band separation (SWR-804) relies on.
    const = np.full((64, 64), 500.0)
    pyr = pyramid.build_pyramid(const, levels=4)
    # Interior is exactly zero; only the outermost ring carries the standard
    # Burt-Adelson zero-insertion boundary ripple (harmless, reconstructs exactly).
    for band in pyr[:-1]:
        assert np.max(np.abs(band[2:-2, 2:-2])) < 1e-9
    assert abs(float(np.mean(pyr[-1])) - 500.0) < 1e-9
