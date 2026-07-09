"""Synthetic lag-sequence phantoms + CalibSet(LAG) builders (plan.md section 6).

Known-IRF injectors for the T4 lag module. A forward lag model corrupts a known
"true" capture sequence; a correction driven by the SAME IRF must invert it
exactly (matched-IRF premise). Every constant is externalized; EV thresholds
live in the tests as external-injected values (measurement != judgment).

Forward lag model (inverse of the SWR-402 correction recursion):
    g_i[k] = b_i * (g_i[k-1] + a_i * true[k-1]),   g_i[-1] = 0
    measured[k] = true[k] + sum_i g_i[k]

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.contract import Params
from common.xframe import new_frame
from modules.lag import K_IRF_A, K_IRF_B

# Known synthetic IRF ([B] in production; injected here). M = 3 (SWR-401 M=3..4).
IRF_A = (0.030, 0.020, 0.010)
IRF_B = (0.50, 0.80, 0.90)

# External-injected EV thresholds (EVAL v1.1 XDET-EV-104 legs); tests compare
# engine outputs against these — the module/engine never embed them.
EV = {
    "ev104_first_frame_lag_min_pct": 5.0,  # after-correction first-frame lag <= 5%
}


def lag_calib(
    shape: tuple[int, int],
    a: tuple[float, ...] = IRF_A,
    b: tuple[float, ...] = IRF_B,
    *,
    panel_id: str = "PANEL-A",
    valid_from: str = "2026-01-01",
    valid_until: str = "2027-01-01",
) -> CalibSet:
    """A valid CalibSet(LAG) carrying the exponential-sum IRF coefficients."""
    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(shape),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=CalibKind.LAG,
        data={
            K_IRF_A: np.asarray(a, dtype=np.float32),
            K_IRF_B: np.asarray(b, dtype=np.float32),
        },
        provenance=CalibProvenance(created_at="2026-07-09", source="synthetic"),
    )


def lag_params(**overrides) -> Params:
    """Params for the lag stage (no tuning constant; carried for the hash)."""
    values = {"lag_context": "synthetic-validation"}
    values.update(overrides)
    return Params(values=values)


def forward_lag(
    true_stack: np.ndarray, a: tuple[float, ...], b: tuple[float, ...]
) -> np.ndarray:
    """Corrupt a (K, ny, nx) true sequence with the forward lag model."""
    a_arr = np.asarray(a, dtype=np.float64)[:, None, None]
    b_arr = np.asarray(b, dtype=np.float64)[:, None, None]
    k, ny, nx = true_stack.shape
    g = np.zeros((a_arr.shape[0], ny, nx), dtype=np.float64)
    measured = np.empty_like(true_stack, dtype=np.float64)
    prev_true = np.zeros((ny, nx), dtype=np.float64)
    for idx in range(k):
        g = b_arr * (g + a_arr * prev_true[None, :, :])
        measured[idx] = true_stack[idx] + g.sum(axis=0)
        prev_true = true_stack[idx]
    return measured


def _frames(stack: np.ndarray) -> list:
    return [new_frame(stack[i].astype(np.float32)) for i in range(stack.shape[0])]


@dataclass(frozen=True)
class LagCorruptionPhantom:
    measured_frames: list  # XFrames fed to the lag correction
    true_frames: list  # XFrames the matched-IRF correction must recover
    a: tuple[float, ...]
    b: tuple[float, ...]


def make_matched_sequence(
    shape: tuple[int, int] = (8, 8),
    offset: float = 1000.0,
    n_frames: int = 8,
    a: tuple[float, ...] = IRF_A,
    b: tuple[float, ...] = IRF_B,
    seed: int = 7,
) -> LagCorruptionPhantom:
    """A deterministic ramp/step true sequence corrupted by the forward IRF."""
    rng = np.random.default_rng(seed)
    ny, nx = shape
    true = np.empty((n_frames, ny, nx), dtype=np.float64)
    for k in range(n_frames):
        # A spatially structured, frame-varying true signal (deterministic).
        level = offset + 500.0 * ((k % 3) + 1)
        pattern = rng.uniform(-50.0, 50.0, size=shape)
        true[k] = level + pattern
    measured = forward_lag(true, a, b)
    return LagCorruptionPhantom(_frames(measured), _frames(true), a, b)


@dataclass(frozen=True)
class FirstFrameLagPhantom:
    measured_frames: list
    offset: float
    exposed_amp: float
    exposure_end_index: int


def make_first_frame_lag_sequence(
    shape: tuple[int, int] = (16, 16),
    offset: float = 1000.0,
    exposed_amp: float = 4000.0,
    n_expose: int = 4,
    n_residual: int = 6,
    a: tuple[float, ...] = IRF_A,
    b: tuple[float, ...] = IRF_B,
) -> FirstFrameLagPhantom:
    """Saturation-near exposure plateau -> X-ray blocked -> afterglow decay.

    true = [offset+amp]*n_expose + [offset]*n_residual; measured carries the
    forward lag. Before correction the residual frames show first-frame lag;
    after matched-IRF correction they return to the dark offset (lag ~ 0).
    """
    ny, nx = shape
    true = np.concatenate(
        [
            np.full((n_expose, ny, nx), offset + exposed_amp, dtype=np.float64),
            np.full((n_residual, ny, nx), offset, dtype=np.float64),
        ]
    )
    measured = forward_lag(true, a, b)
    return FirstFrameLagPhantom(_frames(measured), offset, exposed_amp, n_expose - 1)


@dataclass(frozen=True)
class GhostPhantom:
    measured_frames: list  # pattern frame + uniform ghost-bearing frames
    ghost_index: int  # index (in measured_frames) of the frame judged for ghost
    foreground_roi: tuple[int, int, int, int]
    background_roi: tuple[int, int, int, int]


def make_ghost_sequence(
    shape: tuple[int, int] = (64, 64),
    offset: float = 1000.0,
    pattern_amp: float = 5000.0,
    n_uniform: int = 3,
    noise_sigma: float = 5.0,
    a: tuple[float, ...] = IRF_A,
    b: tuple[float, ...] = IRF_B,
    seed: int = 11,
) -> GhostPhantom:
    """High-contrast pattern frame -> uniform frames carrying its ghost."""
    rng = np.random.default_rng(seed)
    ny, nx = shape
    pattern = np.full(shape, offset, dtype=np.float64)
    pattern[:, : nx // 2] = offset + pattern_amp  # left half bright
    uniform = np.full((n_uniform, ny, nx), offset, dtype=np.float64)
    true = np.concatenate([pattern[None, :, :], uniform])
    measured = forward_lag(true, a, b)
    # Add read noise so the ghost-CNR background std is non-zero.
    measured = measured + rng.normal(0.0, noise_sigma, size=measured.shape)
    fg = (24, 8, 16, 16)  # former bright (left) region
    bg = (24, 40, 16, 16)  # former dark (right) region
    return GhostPhantom(_frames(measured), 1, fg, bg)
