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


def reduce_once(image: np.ndarray) -> np.ndarray:
    """Low-pass then decimate by 2 (Burt-Adelson REDUCE), public API.

    Exposed so consumers (e.g. modules.mse noise propagation) do not couple to a
    private helper (single shared REDUCE rule, SWR-000-9).
    """
    return _blur(image)[::2, ::2]


# Backward-compatible internal alias (kept for existing intra-module use).
_reduce = reduce_once


def _zero_insert(image: np.ndarray, out_shape: tuple[int, int]) -> np.ndarray:
    """Upsample by 2 with zero-insertion into `out_shape` (no interpolation)."""
    up = np.zeros(out_shape, dtype=np.float64)
    up[::2, ::2] = image
    return up


def _reduce_adjoint(image: np.ndarray, out_shape: tuple[int, int]) -> np.ndarray:
    """Adjoint of REDUCE: zero-insert to `out_shape` then blur (B o S)."""
    return _blur(_zero_insert(image, out_shape))


def _expand(image: np.ndarray, out_shape: tuple[int, int]) -> np.ndarray:
    """Upsample to `out_shape` (zero-insert) then interpolate (Burt-Adelson EXPAND).

    The 4x gain (2x per separable axis) compensates for the energy lost to the
    zero-inserted samples so EXPAND(REDUCE(x)) approximates x.
    """
    up = np.zeros(out_shape, dtype=np.float64)
    up[::2, ::2] = image
    return 4.0 * _blur(up)


def max_feasible_levels(shape: tuple[int, int]) -> int:
    """Number of REDUCE steps possible before an axis drops below 2 px.

    A Laplacian pyramid with L detail bands requires L feasible REDUCEs; this is
    the largest L that ``build_pyramid`` can honor for `shape`.
    """
    ny, nx = int(shape[0]), int(shape[1])
    n = 0
    while min(ny, nx) >= 2:
        ny = (ny + 1) // 2  # decimation [::2] of size s yields ceil(s/2)
        nx = (nx + 1) // 2
        n += 1
    return n


def build_pyramid(image: np.ndarray, levels: int) -> list[np.ndarray]:
    """Build a Laplacian pyramid with `levels` detail bands + 1 coarse residual.

    Returns a list of length ``levels + 1``: ``[L_0, ..., L_{levels-1}, residual]``
    where ``L_k`` is the bandpass detail at scale k (same shape as Gaussian level
    k) and ``residual`` is the coarsest Gaussian level (the DRC low-band, SWR-804).

    `levels` must be >= 1 and <= ``max_feasible_levels(image.shape)``. An infeasible
    request is refused with a ValueError naming the maximum feasible level count —
    the requested level count is honored exactly, never silently truncated
    (params-must-be-honored, SWR-000-5).
    """
    if levels < 1:
        raise ValueError(f"pyramid.build_pyramid: levels must be >= 1, got {levels}")
    g = np.asarray(image, dtype=np.float64)
    feasible = max_feasible_levels(g.shape)
    if levels > feasible:
        raise ValueError(
            f"pyramid.build_pyramid: requested {levels} levels but image shape "
            f"{tuple(g.shape)} supports at most {feasible} (an axis would drop "
            f"below 2 px); reduce the level count or enlarge the frame"
        )
    bands: list[np.ndarray] = []
    for _ in range(int(levels)):
        g_next = _reduce(g)
        bands.append(g - _expand(g_next, g.shape))
        g = g_next
    bands.append(g)  # coarse residual (lowest band)
    return bands


def laplacian_band_noise_gains(shape: tuple[int, int], levels: int) -> list[float]:
    """Per-level noise variance gain from white input to each Laplacian band.

    Returns ``[gain_0, ..., gain_{levels-1}]`` where ``gain_k`` is the factor by
    which a spatially white, unit-variance input noise field's variance is
    transformed into the variance of the level-k Laplacian detail band coefficient
    (an interior, decimation-phase-averaged value). This is the exact-for-LSI
    autocorrelation propagation of noise through the REDUCE/EXPAND chain — it does
    NOT assume per-level independence (the naive ``sum(kernel^2)^k`` model
    underestimates correlated noise badly at coarse levels).

    The band operator ``A_k = R^k - E o R^{k+1}`` (R=REDUCE, E=EXPAND) is linear;
    for white input of variance v the band variance is ``v * ||A_k^T e_p||^2`` at
    band pixel p. Using the adjoints ``R^T`` (zero-insert then blur) and
    ``E^T = 4 R``, the squared norm of the impulse response is summed and averaged
    over the 2x2 interior decimation phases. Deterministic (Monte-Carlo-free).
    """
    feasible = max_feasible_levels(shape)
    if levels > feasible:
        raise ValueError(
            f"pyramid.laplacian_band_noise_gains: {levels} levels exceed the "
            f"{feasible} feasible for shape {tuple(shape)}"
        )
    # Gaussian-level shapes S_0..S_{levels} (S_{j+1} = REDUCE shape of S_j).
    s_shapes: list[tuple[int, int]] = [(int(shape[0]), int(shape[1]))]
    for _ in range(levels + 1):
        s = s_shapes[-1]
        s_shapes.append(((s[0] + 1) // 2, (s[1] + 1) // 2))

    gains: list[float] = []
    for k in range(levels):
        sk = s_shapes[k]
        cy, cx = sk[0] // 2, sk[1] // 2
        phase_gains: list[float] = []
        seen: set[tuple[int, int]] = set()
        for dy in (0, 1):
            for dx in (0, 1):
                py, px = min(cy + dy, sk[0] - 1), min(cx + dx, sk[1] - 1)
                if (py, px) in seen:
                    continue
                seen.add((py, px))
                y = np.zeros(sk, dtype=np.float64)
                y[py, px] = 1.0
                # term1 = (R^T)^k y  -> full input grid S_0.
                t1 = y
                for j in range(k, 0, -1):
                    t1 = _reduce_adjoint(t1, s_shapes[j - 1])
                # term2 = (R^T)^{k+1} (E^T y) with E^T = 4 R.
                t2 = 4.0 * _reduce(y)  # on S_{k+1}
                for j in range(k + 1, 0, -1):
                    t2 = _reduce_adjoint(t2, s_shapes[j - 1])
                band_response = t1 - t2
                phase_gains.append(float(np.sum(band_response**2)))
        gains.append(float(np.mean(phase_gains)))
    return gains


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
