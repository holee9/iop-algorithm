"""NDT metrics: duplex-wire SRb and SNRn (REQ-METRICS-NDT, §2, SWR-1201/1202).

SRb_image is auto-read from a duplex-wire IQI profile using the ISO 20% dip
criterion (REQ-METRICS-NDT-1). SNRn = SNR * 88.6[um] / SRb_image
(REQ-METRICS-NDT-2); 88.6 is the standard normalization constant [S], injected
via Params. When no resolvable dip is found the read fails explicitly — the
engine never substitutes a default SRb estimate (REQ-METRICS-NDT-4 / EC-5).

@MX:ANCHOR: [AUTO] `read_duplex_srb` and `compute_snrn` are the NDT-group public
entry points (acceptance Scenario 7, XDET-TC-018 decision engine).
@MX:REASON: the SRb read-failure contract and the SNRn normalization are
consumed by EV-301 gating; silent estimation would corrupt the NDT verdict.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common import robust_stats
from common.contract import Params
from common.xframe import XFrame
from metrics.result import MetricCondition, MetricReadError, MetricResult

P_DIP_THRESHOLD = "ndt_dip_threshold"  # ISO 20% dip criterion (fraction) [P]
P_SRB_NORM_UM = "ndt_srb_norm_um"  # 88.6 um normalization constant [S]


@dataclass(frozen=True)
class WirePair:
    """One duplex-wire pair: the two peak positions, the valley, and its SRb.

    Args:
        peak1_index / peak2_index: sample indices of the two wire peaks.
        valley_index: sample index of the valley between them.
        srb_um: basic spatial resolution (unsharpness) this pair marks, in um.
    """

    peak1_index: int
    valley_index: int
    peak2_index: int
    srb_um: float


def _dip(profile: np.ndarray, pair: WirePair) -> float:
    """Relative modulation (dip) of a wire pair: 1 - valley / mean(peaks)."""
    peak = 0.5 * (profile[pair.peak1_index] + profile[pair.peak2_index])
    valley = profile[pair.valley_index]
    if peak <= 0:
        return 0.0
    return float(1.0 - valley / peak)


def read_duplex_srb(
    profile: np.ndarray,
    pairs: list[WirePair],
    params: Params,
    *,
    calibset_id: str | None = None,
) -> MetricResult:
    """Auto-read SRb_image from a duplex-wire profile (20% dip criterion).

    Pairs are scanned in the given (coarse -> fine) order. SRb is the srb_um of
    the first unresolved pair (dip < threshold). If no pair is resolvable at all
    (no dip pattern found), the read fails explicitly.

    Args:
        profile: 1D intensity profile along the duplex-wire IQI.
        pairs: ordered wire pairs with known element geometry.
        params: externalized 20% dip threshold.
        calibset_id: consumed CalibSet id (metadata).

    Raises:
        MetricReadError: no resolvable dip found (REQ-METRICS-NDT-4 / EC-5).
    """
    prof = np.asarray(profile, dtype=np.float64)
    threshold = float(params.get(P_DIP_THRESHOLD))
    if not pairs:
        raise MetricReadError("duplex SRb: no wire pairs provided")

    dips = [_dip(prof, p) for p in pairs]
    resolved = [d >= threshold for d in dips]
    if not any(resolved):
        raise MetricReadError(
            "duplex SRb: no resolvable dip found (no 20% dip pattern) — "
            "read failure, no SRb estimate substituted"
        )

    warnings: list[str] = []
    first_unresolved = next((i for i, r in enumerate(resolved) if not r), None)
    if first_unresolved is None:
        # Every pair resolved: the resolution limit is beyond the finest pair.
        srb_pair = pairs[-1]
        warnings.append(
            "duplex SRb: all pairs resolved; SRb taken at the finest pair "
            "(true limit is finer than the IQI)"
        )
    else:
        srb_pair = pairs[first_unresolved]

    return MetricResult(
        name="duplex_srb",
        values={
            "srb_um": srb_pair.srb_um,
            "dips": np.asarray(dips),
            "first_unresolved_pair": first_unresolved,
        },
        condition=MetricCondition(params_hash=params.hash(), calibset_id=calibset_id),
        warnings=tuple(warnings),
    )


def compute_snr(
    frame: XFrame,
    roi: tuple[int, int, int, int],
    params: Params,
) -> tuple[float, float, float]:
    """Robust SNR of a uniform ROI: (snr, mean, std)."""
    t, l, h, w = roi
    region = np.asarray(frame.pixel, dtype=np.float64)[t : t + h, l : l + w]
    mean = robust_stats.robust_mean(region)
    std = robust_stats.robust_std(region)
    if std == 0:
        raise MetricReadError("SNR: zero noise in the uniform region")
    return float(mean / std), float(mean), float(std)


def compute_snrn(
    frame: XFrame,
    roi: tuple[int, int, int, int],
    srb_um: float,
    params: Params,
    *,
    calibset_id: str | None = None,
) -> MetricResult:
    """Compute SNRn = SNR * 88.6[um] / SRb_image (REQ-METRICS-NDT-2/3).

    Args:
        frame: uniform-exposure frame (consumed read-only).
        roi: (top, left, height, width) of the uniform region.
        srb_um: SRb_image (um) from `read_duplex_srb`.
        params: externalized 88.6 um normalization constant.
        calibset_id: consumed CalibSet id (metadata).
    """
    snr, mean, std = compute_snr(frame, roi, params)
    norm_um = float(params.get(P_SRB_NORM_UM))
    snrn = snr * norm_um / srb_um
    return MetricResult(
        name="SNRn",
        values={
            "snrn": snrn,
            "snr": snr,
            "mean": mean,
            "std": std,
            "srb_um": srb_um,
        },
        condition=MetricCondition(
            roi=roi,
            params_hash=params.hash(),
            calibset_id=calibset_id,
            beam_quality=params.get("beam_quality"),
        ),
    )
