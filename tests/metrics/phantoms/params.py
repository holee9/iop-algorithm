"""Default externalized Params for the synthetic-validation phantoms.

Every constant the metrics engine reads is set here (never hardcoded in the
engine, REQ-METRICS-CORE-4). Grade annotations: [S] standard, [P] tunable,
[T] tolerance. The reproduction tolerances are themselves [T] parameters.
"""

from __future__ import annotations

from common.contract import Params

PIXEL_PITCH_MM = 0.14  # panel pitch -> Nyquist 3.57 lp/mm (EVAL v1.1 §0)

_DEFAULTS = {
    # -- MTF --
    "pixel_pitch_mm": PIXEL_PITCH_MM,
    "mtf_oversample": 4,  # [P]
    "mtf_angle_min_deg": 1.5,  # [P]
    "mtf_angle_max_deg": 3.0,  # [P]
    "mtf_angle_margin_deg": 0.2,  # [T]
    # -- NPS --
    "nps_roi_size": 256,  # [P] IEC default
    "nps_detrend_order": 2,  # [P]
    "nps_exclude_axis_bins": 1,  # [P]
    "nps_average_lines": 7,  # [P]
    "nps_central_frac": 0.8,  # [P] central-region fraction tiled for ROIs
    "line_noise_sig_factor": 10.0,  # [P] peak significance: n x MAD above median
    # -- DQE --
    "dqe_q": 30000.0,  # [S] RQA5 photon fluence per air kerma (IEC table value)
    "dqe_ka": 2.5,  # per-acquisition measured detector-plane air kerma
    "dqe_nps_floor": 1e-9,  # [P] zero-division guard (on NNPS)
    # -- lag --
    "lag_min_exposed_signal": 500.0,  # [P] saturation-near premise floor
    "lag_plateau_frac": 0.5,  # [P] exposed-plateau level fraction
    "lag_settle_frac": 0.05,  # [P] dark-tail settle criterion fraction
    # -- defect --
    "defect_min_frames": 8,  # [P]
    "defect_over_value": 65530.0,  # [P]
    "defect_under_value": 5.0,  # [P]
    "defect_dead_gain_frac": 0.1,  # [P]
    "defect_nonuniform_frac": 0.2,  # [P]
    "defect_lag_frac": 0.2,  # [P]
    "defect_unstable_frac": 6.0,  # [P]
    # -- NDT --
    "ndt_dip_threshold": 0.20,  # [P] ISO 20% dip
    "ndt_srb_norm_um": 88.6,  # [S] SNRn normalization constant
    # -- metadata pass-through --
    "beam_quality": "RQA5",
    "added_filter": "Al 21mm",
    "temperature_c": 25.0,
}

# Reproduction tolerances ([T]); externalized, not baked into assertions.
TOLERANCES = {
    "mtf_abs": 0.02,  # tightened (finding #8: derivative-sinc correction)
    "mtf_nyquist_abs": 0.06,
    "nps_rel": 0.15,
    "nnps_rel": 0.15,
    "dqe_rel": 1e-6,  # DQE is formula-composed -> exact up to float noise
    "dqe_ideal_abs": 0.10,  # ideal quantum-limited detector DQE ~ 1 (analytic)
    "lag_rel": 1e-6,
    "ghost_cnr_rel": 0.20,
    "snrn_rel": 0.10,
}


def make_params(**overrides) -> Params:
    """Return the default phantom Params, with optional key overrides."""
    values = dict(_DEFAULTS)
    values.update(overrides)
    return Params(values=values)
