"""Shared component: Laplacian image pyramid (SWR-000-9 (1), SWR-801).

@MX:ANCHOR: [AUTO] `build_pyramid` / `reconstruct_pyramid` are the single
Laplacian-pyramid decomposition/synthesis shared by the multi-scale enhancement
module (modules.mse, the first consumer) and any downstream pyramid user.
@MX:REASON: fan_in is the MSE band-modulation + DRC path plus its harness/gates;
the perfect-reconstruction property (an unmodulated round trip restores the
input within float tolerance) is the invariant the MSE non-degradation gate
reads against, so a divergent reduce/expand rule would break it silently.

Burt-Adelson pyramid with the standard separable 5x5 binomial kernel
[1 4 6 4 1]/16 (SWR-801, decomposition method [L]; level count [T] via caller).
Perfect reconstruction holds by construction: L_k = G_k - expand(reduce(G_k)),
so reconstruct adds back exactly what decomposition subtracted, regardless of the
convolution boundary rule.

T0 provided the interface stub only; T6 (SPEC-POST-001) is the first consumer and
supplies the real algorithm here (SWR-000-9 first-consumer deferral). Placed once
in common/ (no duplication). Accuracy is the single goal; no speed optimization
(P2).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

# Standard 5x5 separable binomial kernel [1 4 6 4 1]/16 (SWR-801). Fixed by the
# SWR (not a tunable) — the level count is the externalized [T] parameter.
_KERNEL_1D = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float64) / 16.0


def _blur(image: np.ndarray) -> np.ndarray:
    """Separable 5x5 binomial low-pass with reflecting boundary."""
    out = ndimage.correlate1d(image, _KERNEL_1D, axis=0, mode="reflect")
    out = ndimage.correlate1d(out, _KERNEL_1D, axis=1, mode="reflect")
    return out


def _reduce(image: np.ndarray) -> np.ndarray:
    """Low-pass then decimate by 2 (Burt-Adelson REDUCE)."""
    return _blur(image)[::2, ::2]


def _expand(image: np.ndarray, out_shape: tuple[int, int]) -> np.ndarray:
    """Upsample to `out_shape` (zero-insert) then interpolate (Burt-Adelson EXPAND).

    The 4x gain (2x per separable axis) compensates for the energy lost to the
    zero-inserted samples so EXPAND(REDUCE(x)) approximates x.
    """
    up = np.zeros(out_shape, dtype=np.float64)
    up[::2, ::2] = image
    return 4.0 * _blur(up)


def build_pyramid(image: np.ndarray, levels: int) -> list[np.ndarray]:
    """Build a Laplacian pyramid with `levels` detail bands + 1 coarse residual.

    Returns a list of length ``levels + 1``: ``[L_0, ..., L_{levels-1}, residual]``
    where ``L_k`` is the bandpass detail at scale k (same shape as Gaussian level
    k) and ``residual`` is the coarsest Gaussian level (the DRC low-band, SWR-804).

    `levels` must be >= 1. Decimation stops early if a Gaussian level becomes too
    small to reduce further (< 2 px on an axis); the residual is then that level.
    """
    if levels < 1:
        raise ValueError(f"pyramid.build_pyramid: levels must be >= 1, got {levels}")
    g = np.asarray(image, dtype=np.float64)
    bands: list[np.ndarray] = []
    for _ in range(int(levels)):
        if min(g.shape) < 2:
            break  # too small to reduce further; current g becomes the residual
        g_next = _reduce(g)
        bands.append(g - _expand(g_next, g.shape))
        g = g_next
    bands.append(g)  # coarse residual (lowest band)
    return bands


def reconstruct_pyramid(pyramid: list[np.ndarray]) -> np.ndarray:
    """Invert build_pyramid: sum detail bands back onto the coarse residual.

    Perfect reconstruction (up to float rounding): for an unmodulated pyramid this
    restores the original input exactly by construction.
    """
    if not pyramid:
        raise ValueError("pyramid.reconstruct_pyramid: empty pyramid")
    g = np.asarray(pyramid[-1], dtype=np.float64)
    for band in reversed(pyramid[:-1]):
        g = np.asarray(band, dtype=np.float64) + _expand(g, band.shape)
    return g
