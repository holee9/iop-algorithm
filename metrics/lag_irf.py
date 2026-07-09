"""IRF fitting tool: multi-exposure step-response -> CalibSet(LAG) (SWR-401).

Offline calibration builder (spec decision 5, metrics.defect_map precedent). It
fits the exponential-sum lag IRF h[n] = sum_i a_i * b_i**n (M = 3..4, [L]) from
rising/falling step-response afterglow curves acquired at MULTIPLE exposure
levels (saturation 2..90% multi-point) and emits a CalibSet(kind=LAG) whose
data payload feeds modules.lag.

Fitting model (LTI): the afterglow residual after a step of amplitude A is, per
the SWR-402 state recursion, residual[m] = A * sum_i a_i * b_i**m (m = 1..N).
Normalizing each exposure by its amplitude, all levels must collapse onto the
same exponential-sum curve (LTI premise); the tool fits (a_i, b_i) jointly over
the stacked normalized residuals.

- REQ-LAG-IRF-2: a SINGLE-exposure calibration is rejected (IRF is sensitive to
  measurement technique / exposure level, [L]); >= 2 exposures are required.
- REQ-LAG-IRF-3: while real step-response is measurement-pending [B], a known
  synthetic IRF must be recovered within a [T] tolerance.

Layering stays metrics -> common (the produced CalibSet lives in common); the
correction module modules.lag never imports metrics.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from common.calibset import CalibKind, CalibProvenance, CalibSet

# modules.lag CalibSet(LAG) payload keys (kept in sync with modules.lag).
K_IRF_A = "irf_a"
K_IRF_B = "irf_b"


class LagIRFCalibrationError(ValueError):
    """Raised on an invalid IRF calibration request (e.g. single exposure)."""


@dataclass(frozen=True)
class StepResponse:
    """One exposure level's falling-edge afterglow residual.

    amplitude: the exposed-step amplitude A (above baseline).
    residual:  residual signal at m = 1..N after the step ends (baseline
               removed), i.e. A * sum_i a_i * b_i**m plus measurement noise.
    """

    amplitude: float
    residual: np.ndarray


def _model(theta: np.ndarray, m: np.ndarray, m_terms: int) -> np.ndarray:
    a = theta[:m_terms][:, None]
    b = theta[m_terms:][:, None]
    return (a * b ** m[None, :]).sum(axis=0)


# @MX:ANCHOR: [AUTO] sole IRF producer feeding modules.lag via CalibSet(LAG).
# @MX:REASON: fan_in spans the synthetic-recovery gate (REQ-LAG-IRF-3), the
# single-exposure rejection (EC-2), and the fit -> correct round-trip test; the
# (irf_a, irf_b) payload schema and the >=2-exposure premise are contractual.
def fit_lag_irf(
    step_responses: list[StepResponse],
    *,
    m_terms: int = 3,
    panel_id: str,
    resolution: tuple[int, int],
    valid_from: str,
    valid_until: str,
    created_at: str = "",
    source: str = "lag-irf-builder",
    max_nfev: int = 20000,
) -> CalibSet:
    """Fit (a_i, b_i) from multi-exposure step responses -> CalibSet(LAG).

    Raises:
        LagIRFCalibrationError: fewer than 2 exposures (single-exposure ban,
            SWR-401), or a non-positive amplitude / empty residual.
    """
    if len(step_responses) < 2:
        raise LagIRFCalibrationError(
            "lag IRF: single-exposure calibration is forbidden (SWR-401); "
            "supply >= 2 exposure levels (saturation 2..90% multi-point)"
        )
    if m_terms < 1:
        raise LagIRFCalibrationError(f"lag IRF: M must be >= 1 (got {m_terms})")

    # Stack normalized residuals from every exposure onto a common m-grid.
    m_grids: list[np.ndarray] = []
    normalized: list[np.ndarray] = []
    for sr in step_responses:
        if sr.amplitude <= 0:
            raise LagIRFCalibrationError("lag IRF: exposure amplitude must be > 0")
        res = np.asarray(sr.residual, dtype=np.float64).reshape(-1)
        if res.size == 0:
            raise LagIRFCalibrationError("lag IRF: empty residual curve")
        m_grids.append(np.arange(1, res.size + 1, dtype=np.float64))
        normalized.append(res / float(sr.amplitude))
    m_all = np.concatenate(m_grids)
    y_all = np.concatenate(normalized)

    def _residuals(theta: np.ndarray) -> np.ndarray:
        return _model(theta, m_all, m_terms) - y_all

    # Deterministic initial guess: amplitudes share the first normalized sample;
    # poles spread across (0, 1). Bounds keep a_i >= 0 and 0 < b_i < 1 (a
    # physically decaying afterglow).
    a0 = max(float(np.max(y_all)) / m_terms, 1e-6)
    a_init = np.full(m_terms, a0, dtype=np.float64)
    b_init = np.linspace(0.2, 0.85, m_terms, dtype=np.float64)
    x0 = np.concatenate([a_init, b_init])
    lower = np.concatenate([np.zeros(m_terms), np.full(m_terms, 1e-6)])
    upper = np.concatenate([np.full(m_terms, np.inf), np.full(m_terms, 1.0 - 1e-9)])

    fit = least_squares(
        _residuals, x0, bounds=(lower, upper), method="trf", max_nfev=max_nfev
    )
    a_fit = fit.x[:m_terms]
    b_fit = fit.x[m_terms:]
    # Sort by descending pole for a stable, identifiable ordering.
    order = np.argsort(-b_fit)
    a_fit = a_fit[order]
    b_fit = b_fit[order]

    return CalibSet(
        panel_id=panel_id,
        resolution=tuple(resolution),
        valid_from=valid_from,
        valid_until=valid_until,
        kind=CalibKind.LAG,
        data={
            K_IRF_A: a_fit.astype(np.float32),
            K_IRF_B: b_fit.astype(np.float32),
        },
        provenance=CalibProvenance(created_at=created_at, source=source),
    )
