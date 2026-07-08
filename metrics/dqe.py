"""DQE(f) = MTF^2(f) * q * Ka / NPS(f) (REQ-METRICS-NPS-3, measurement §1.4).

Consumes the MTF-group and NPS-group outputs (metrics.mtf, metrics.nps). q is an
IEC table constant [S] and Ka is a per-acquisition measured input; both are
injected via Params (REQ-METRICS-CORE-4). A divide-by-zero guard marks
frequencies where NPS -> 0 as invalid (REQ-METRICS-NPS-7 / EC-3).

@MX:ANCHOR: [AUTO] `compute_dqe` is the DQE public entry point (acceptance
Scenario 3/4).
@MX:REASON: DQE composition is the terminal Common-Core physics metric; its
frequency-alignment and zero-guard contract are relied on by every DQE scenario.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.contract import Params
from metrics.result import MetricCondition, MetricResult

P_Q = "dqe_q"  # RQA5 photon fluence per air kerma [S] (IEC table value)
P_KA = "dqe_ka"  # detector-plane air kerma (per-acquisition measured input)
P_NPS_FLOOR = "dqe_nps_floor"  # NPS magnitude below which DQE is invalid [P]


def compute_dqe(
    frequencies_lpmm: np.ndarray,
    mtf: np.ndarray,
    nps: np.ndarray,
    params: Params,
    *,
    calibset_id: str | None = None,
    dose_level: str | None = None,
) -> MetricResult:
    """Compose DQE(f) from aligned MTF and NPS samples.

    Args:
        frequencies_lpmm: common frequency axis for `mtf` and `nps`.
        mtf: presampled MTF(f) on that axis.
        nps: NPS(f) on that axis.
        params: externalized q, Ka and the NPS zero-guard floor.
        calibset_id: consumed CalibSet id (metadata).
        dose_level: dose-level tag (metadata).

    Frequencies where NPS <= floor yield DQE = NaN (invalid) rather than a
    division by zero; their indices are reported in `invalid_indices`.
    """
    freq = np.asarray(frequencies_lpmm, dtype=np.float64)
    mtf_a = np.asarray(mtf, dtype=np.float64)
    nps_a = np.asarray(nps, dtype=np.float64)
    if not (freq.shape == mtf_a.shape == nps_a.shape):
        raise ValueError("frequencies, mtf and nps must share the same shape")

    q = float(params.get(P_Q))
    ka = float(params.get(P_KA))
    floor = float(params.get(P_NPS_FLOOR))

    invalid = nps_a <= floor
    dqe = np.full_like(freq, np.nan)
    valid = ~invalid
    dqe[valid] = (mtf_a[valid] ** 2) * q * ka / nps_a[valid]

    warnings: list[str] = []
    if invalid.any():
        warnings.append(
            f"DQE: {int(invalid.sum())} frequency bin(s) with NPS <= floor "
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
