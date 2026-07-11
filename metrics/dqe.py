"""DQE(f) = MTF^2(f) / (q * Ka * NNPS(f)) (REQ-METRICS-NPS-3, IEC 62220-1).

Consumes the MTF-group and NPS-group outputs (metrics.mtf, metrics.nps). The
input noise spectrum is the NORMALIZED NPS (NNPS = NPS / large-area-signal^2),
so DQE is dimensionless: q*Ka is the photon fluence [1/mm^2] (q = photons per
mm^2 per air-kerma [1/(mm^2*uGy)] [S], Ka = detector-plane air kerma [uGy]) and
NNPS carries [mm^2], leaving DQE(f) dimensionless. Both q and Ka are injected via
Params (REQ-METRICS-CORE-4). A divide-by-zero guard marks frequencies where
NNPS -> 0 as invalid (REQ-METRICS-NPS-7 / EC-3).

@MX:ANCHOR: [AUTO] `compute_dqe` is the DQE public entry point (acceptance
Scenario 3/4).
@MX:REASON: DQE composition is the terminal Common-Core physics metric; its
frequency-alignment and zero-guard contract are relied on by every DQE scenario.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.contract import Params
from metrics.result import MetricCondition, MetricResult, require_param

P_Q = "dqe_q"  # photon fluence per air kerma [1/(mm^2*uGy)] [S] (IEC table value)
P_KA = "dqe_ka"  # detector-plane air kerma [uGy] (per-acquisition measured input)
P_NNPS_FLOOR = "dqe_nps_floor"  # NNPS magnitude below which DQE is invalid [P]


def compute_dqe(
    frequencies_lpmm: np.ndarray,
    mtf: np.ndarray,
    nnps: np.ndarray,
    params: Params,
    *,
    calibset_id: str | None = None,
    dose_level: str | None = None,
) -> MetricResult:
    """Compose DQE(f) from aligned MTF and NNPS samples (IEC 62220-1).

    Args:
        frequencies_lpmm: common frequency axis for `mtf` and `nnps`.
        mtf: presampled MTF(f) on that axis (dimensionless).
        nnps: normalized NPS(f) = NPS/signal^2 on that axis [mm^2].
        params: externalized q [1/(mm^2*uGy)], Ka [uGy] and the NNPS zero-guard
            floor.
        calibset_id: consumed CalibSet id (metadata).
        dose_level: dose-level tag (metadata).

    Frequencies where NNPS <= floor yield DQE = NaN (invalid) rather than a
    division by zero; their indices are reported in `invalid_indices`.
    """
    freq = np.asarray(frequencies_lpmm, dtype=np.float64)
    mtf_a = np.asarray(mtf, dtype=np.float64)
    nnps_a = np.asarray(nnps, dtype=np.float64)
    if not (freq.shape == mtf_a.shape == nnps_a.shape):
        raise ValueError("frequencies, mtf and nnps must share the same shape")

    q = require_param(params, P_Q, float)
    ka = require_param(params, P_KA, float)
    floor = require_param(params, P_NNPS_FLOOR, float)
    fluence = q * ka  # photons per mm^2 [1/mm^2]

    invalid = nnps_a <= floor
    dqe = np.full_like(freq, np.nan)
    valid = ~invalid
    dqe[valid] = (mtf_a[valid] ** 2) / (fluence * nnps_a[valid])

    warnings: list[str] = []
    if invalid.any():
        warnings.append(
            f"DQE: {int(invalid.sum())} frequency bin(s) with NNPS <= floor "
            f"({floor}) marked invalid (zero-division guard)"
        )

    return MetricResult(
        name="DQE",
        values={
            "frequencies_lpmm": freq,
            "dqe": dqe,
            "invalid_indices": np.nonzero(invalid)[0],
            "q": q,
            "ka": ka,
        },
        condition=MetricCondition(
            params_hash=params.hash(),
            calibset_id=calibset_id,
            dose_level=dose_level,
            beam_quality=params.get("beam_quality"),
        ),
        warnings=tuple(warnings),
    )


def dqe_value_at(result: MetricResult, freq_lpmm: float) -> float:
    """Interpolate DQE at an arbitrary frequency (lp/mm), ignoring invalid bins."""
    freq = np.asarray(result.get("frequencies_lpmm"), dtype=np.float64)
    dqe = np.asarray(result.get("dqe"), dtype=np.float64)
    good = ~np.isnan(dqe)
    return float(np.interp(freq_lpmm, freq[good], dqe[good]))
