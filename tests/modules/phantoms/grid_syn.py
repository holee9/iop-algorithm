"""Synthetic phantoms + externalized Params/EV for T7 grid suppression
(SPEC-GRID-001).

Known grid-frequency / known-direction / known-anatomy injectors for the
grid-line suppression module (modules.grid). Every threshold is externalized:
D_th, the residual-peak significance threshold, the moire cutoff, the attenuation
cap and the EV-102 MTF guardrail live here as external-injected values
(measurement != judgment, EVAL v1.1 legs) — never embedded in the module.

Grid-density three classes (SWR-1006, required in the TC-015 matrix):
  - below   f_grid < f_N              (f_grid = 2.5 lp/mm, observed 2.5)
  - near    f_grid ~= f_N             (f_grid = 3.4 lp/mm, observed 3.4)
  - aliased f_grid > f_N (folds back) (f_grid = 5.0 lp/mm, observed f_a = 2.143)

The aliased class is the observed-spectrum-search negative control (SWR-1001):
the nominal 5.0 lp/mm exceeds Nyquist and is NOT representable, so a
nominal-frequency search finds nothing while the observed-spectrum search finds
the folded peak f_a. Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.contract import Params
from common.xframe import MaskFlag, NoiseModel, new_frame

# Physical panel constants (pitch 140 um; f_N and f_s are DERIVED, never hardcoded
# in the module — they are recomputed from Params pitch there).
PITCH_MM = 0.14
F_NYQUIST = 1.0 / (2.0 * PITCH_MM)  # 3.5714 lp/mm
F_SAMPLING = 1.0 / PITCH_MM  # 7.1429 /mm

# Three grid-density classes (nominal f_grid lp/mm), chosen bin-aligned for a
# 128-wide frame so the injected sinusoid lands on a single FFT bin (no finite-
# window leakage). Real 3072-wide frames have far finer bins, so this is a
# synthetic-validation convenience, not a physical assumption. The observed peak
# is the aliased fold for f_grid > f_N.
_N_REF = 128  # reference frame width the density classes are bin-aligned to
_BIN = 1.0 / (_N_REF * PITCH_MM)  # 0.05580 lp/mm per FFT bin
F_GRID_BELOW = 45 * _BIN  # 2.5112 lp/mm  (< f_N)
F_GRID_NEAR = 61 * _BIN  # 3.4040 lp/mm  (~ f_N)
F_GRID_ALIASED = 90 * _BIN  # 5.0223 lp/mm (> f_N; folds to f_a = 2.1205)
F_GRID_MOIRE = 121 * _BIN  # 6.7522 lp/mm (> f_N; folds to f_a = 0.3906, moire band)

# External-injected thresholds (EVAL v1.1 / Params legs; injected here, never
# embedded in the module or the judgment code).
EV = {
    "d_th_db": 6.0,  # peak significance vs local background (D_th) [T]
    "residual_db": 6.0,  # residual-peak "invisible" threshold (reuse D_th)
    "ev102_mtf_retention_min": 0.90,  # grid-orthogonal MTF@Nyquist retention >= 90%
    "direction_margin_db": 3.0,  # row/col energy-ratio decision margin [T]
    "notch_fwhm_mult": 1.5,  # notch bandwidth = peak FWHM x 1.5 [T]
    "moire_cutoff_lpmm": 0.5,  # low-freq fold cutoff [ungraded]
    "moire_atten_cap": 0.5,  # attenuation cap under the moire band [T]
    "harmonic_max_order": 3,  # folded-harmonic candidate max order [T]
}


def fold_frequency(f_lpmm: float) -> float:
    """Alias a spatial frequency into [0, f_N] the way integer sampling does.

    This is the analytic expectation the tests compare the module's OBSERVED peak
    against; the module never consumes a nominal frequency (SWR-1001).
    """
    r = float(f_lpmm) % F_SAMPLING
    return r if r <= F_NYQUIST else F_SAMPLING - r


# -- Params / CalibSet builders ------------------------------------------------


def grid_params(**overrides) -> Params:
    """Externalized grid-suppression Params (all tunables; grades per SWR app A)."""
    values = {
        "grid_pitch_mm": PITCH_MM,  # panel pitch; f_N, f_s derived from this
        "grid_search_band_lo_lpmm": 0.3,  # [ungraded] search band lower edge
        "grid_peak_significance_db": EV["d_th_db"],  # D_th [T]
        "grid_direction_margin_db": EV["direction_margin_db"],  # [T]
        "grid_harmonic_max_order": EV["harmonic_max_order"],  # [T]
        "grid_notch_fwhm_mult": EV["notch_fwhm_mult"],  # [T]
        "grid_moire_lowfreq_cutoff_lpmm": EV["moire_cutoff_lpmm"],  # [ungraded]
        "grid_moire_atten_cap": EV["moire_atten_cap"],  # [T]
    }
    values.update(overrides)
    return Params(values=values)


def other_calib(
    shape: tuple[int, int],
    *,
    panel_id: str = "PANEL-A",
    valid_from: str = "2026-01-01",
    valid_until: str = "2027-01-01",
) -> CalibSet:
    """Empty CalibSet(OTHER) placeholder satisfying the entry gate (decision 2)."""
    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(shape),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=CalibKind.OTHER,
        data={},
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
    )


def make_frame(pixel: np.ndarray, masks: np.ndarray | None = None):
    """XFrame carrying a benign noise model (grid does not consume it)."""
    return new_frame(np.asarray(pixel, dtype=np.float32), masks, NoiseModel(0.0, 0.0))


# -- phantom generators --------------------------------------------------------


def _smooth_anatomy(shape: tuple[int, int], base: float) -> np.ndarray:
    """Low-frequency-only anatomy: a smooth gradient + a central attenuation slab.

    Deliberately band-limited BELOW the search band lower edge (0.3 lp/mm) so it
    never masquerades as a grid peak; its edges are broadband but low energy per
    frequency bin.
    """
    ny, nx = shape
    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    clean = np.full(shape, base, dtype=np.float64)
    clean += 0.05 * base * (xs / max(nx - 1, 1))  # slow gradient
    # Smooth Gaussian attenuation blob (NO sharp edges) so all anatomy energy is
    # band-limited below the 0.3 lp/mm search-band edge and never masquerades as a
    # grid peak.
    r2 = ((xs - nx / 2) / (nx / 4.0)) ** 2 + ((ys - ny / 2) / (ny / 4.0)) ** 2
    clean -= 0.15 * base * np.exp(-r2)
    return clean


def make_grid_phantom(
    shape: tuple[int, int] = (128, 128),
    f_grid_lpmm: float = F_GRID_BELOW,
    *,
    direction: str = "vertical",
    amp: float = 200.0,
    base: float = 2000.0,
    anatomy: bool = True,
    noise_sigma: float = 20.0,
    seed: int = 7,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (clean_anatomy, with_grid) for a known grid frequency + direction.

    A "vertical" grid is a set of vertical lines whose intensity is periodic along
    x (columns); a "horizontal" grid varies along y (rows). Sampling at integer
    pixels naturally aliases f_grid > f_N to f_a, so no explicit fold is applied
    to the phantom. `clean` is the noiseless anatomy-only frame (used by the
    numeric-identity passthrough tests); `with_grid` adds the grid plus a realistic
    broadband noise floor so the post-notch residual settles at the noise floor
    (physically = invisible) rather than in an artificial float-zero valley.
    """
    ny, nx = shape
    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    clean = _smooth_anatomy(shape, base) if anatomy else np.full(shape, base)
    if direction == "vertical":
        grid = amp * np.cos(2.0 * np.pi * f_grid_lpmm * xs * PITCH_MM)
    elif direction == "horizontal":
        grid = amp * np.cos(2.0 * np.pi * f_grid_lpmm * ys * PITCH_MM)
    else:  # pragma: no cover - guarded by callers
        raise ValueError("direction must be 'vertical' or 'horizontal'")
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, noise_sigma, size=shape) if noise_sigma > 0 else 0.0
    noisy = clean + grid + noise
    return clean, noisy


def make_crossed_grid_phantom(
    shape: tuple[int, int] = (128, 128),
    f_grid_lpmm: float = F_GRID_BELOW,
    *,
    amp: float = 200.0,
    base: float = 2000.0,
) -> np.ndarray:
    """Equal-amplitude grid on BOTH axes -> direction is ambiguous (EC-2)."""
    ny, nx = shape
    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    clean = _smooth_anatomy(shape, base)
    clean += amp * np.cos(2.0 * np.pi * f_grid_lpmm * xs * PITCH_MM)
    clean += amp * np.cos(2.0 * np.pi * f_grid_lpmm * ys * PITCH_MM)
    return clean


def make_slanted_edge_with_grid(
    shape: tuple[int, int] = (128, 128),
    *,
    f_grid_lpmm: float = F_GRID_BELOW,
    low: float = 800.0,
    high: float = 6000.0,
    slope: float = 0.05,
    amp: float = 150.0,
    with_grid: bool = True,
    noise_sigma: float = 15.0,
    seed: int = 5,
) -> np.ndarray:
    """A near-vertical slanted edge (probes horizontal frequency = the notched
    axis) optionally carrying a vertical grid. Used for the EV-102 MTF@Nyquist
    guardrail: suppressing the grid must not destroy edge sharpness. Uses the same
    tanh soft-edge profile the T6 MTF guardrail tests use (valid edge angle)."""
    ny, nx = shape
    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    edge_col = nx / 2.0 + slope * (ys - ny / 2.0)
    img = low + (high - low) * 0.5 * (1.0 + np.tanh((xs - edge_col) * 2.0))
    if with_grid:
        img = img + amp * np.cos(2.0 * np.pi * f_grid_lpmm * xs * PITCH_MM)
    if noise_sigma > 0:
        img = img + np.random.default_rng(seed).normal(0.0, noise_sigma, size=shape)
    return img
