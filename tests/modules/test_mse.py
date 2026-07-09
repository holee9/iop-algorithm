"""modules/mse.py unit tests (SWR-801~805, REQ-POST-MSE / DRC / CONTRACT).

Covers acceptance Scenarios 4/5/6/7/8/13 and EC-4/EC-6.
"""

from __future__ import annotations

import numpy as np
import pytest

from common import pyramid
from common.contract import Params
from common.xframe import HistoryEntry, MaskFlag, NoiseModel, new_frame
from modules import mse
from tests.modules.phantoms.post_syn import (
    EV,
    make_bone_soft_phantom,
    make_noise_frame,
    mse_params,
    other_calib,
)


def _process(noisy, params=None, masks=None):
    frame = make_noise_frame(noisy, masks)
    return mse.process(frame, other_calib(noisy.shape), params or mse_params())


# -- Scenario 5: band modulation + noise gating --------------------------------


def test_power_law_modulation_known_value():
    # A single detail coefficient c under the power-law form with the noise gate
    # forced open (beta=0) yields exactly gamma*sign(c)*|c|^p.
    c = 4.0
    gamma, p = 1.6, 0.75
    out = mse._modulate_power_law(np.array([c, -c]), gamma, p)
    expected = gamma * np.array([1.0, -1.0]) * (c**p)
    assert np.allclose(out, expected)


def test_noise_gate_suppresses_subnoise_amplification():
    # Sub-noise coefficient (|c| << sigma_l) is gated toward the original (no
    # amplification); a strong coefficient (|c| >> sigma_l) passes the modulation.
    small = np.array([0.1])
    large = np.array([100.0])
    sig2 = np.array([25.0])  # sigma_l^2
    g_small = mse._noise_gate(small, sig2, beta=1.0)
    g_large = mse._noise_gate(large, sig2, beta=1.0)
    assert g_small[0] < 0.05  # gate nearly closed for noise-level detail
    assert g_large[0] > 0.99  # gate open for real structure


def test_structural_detail_retained_above_noise():
    # Genuine (above-noise) structural detail must be preserved through MSE. Use a
    # strong-detail clean phantom (amplitude >> noise sigma) processed with the
    # known noise model; compare detail-band energy of the processed clean output
    # against the clean input (scale-normalized). The noise gate leaves real
    # structure untouched, so retention stays high.
    clean, _ = make_bone_soft_phantom(seed=1, detail_amp=400.0)
    out = mse.process(
        make_noise_frame(clean), other_calib(clean.shape), mse_params()
    )
    cin = clean - clean.mean()
    cin /= cin.std()
    op = np.asarray(out.pixel, np.float64)
    op = (op - op.mean()) / op.std()
    e_in = sum(float(np.sum(b**2)) for b in pyramid.build_pyramid(cin, 4)[:-1])
    e_out = sum(float(np.sum(b**2)) for b in pyramid.build_pyramid(op, 4)[:-1])
    assert e_out / e_in >= EV["detail_energy_retention_min"]


# -- Scenario 7: noise model refusal (REQ-POST-MSE-4, Unwanted) ----------------


def test_missing_noise_model_refused():
    _, noisy = make_bone_soft_phantom()
    frame = new_frame(noisy.astype(np.float32))  # default NoiseModel(0, 0)
    with pytest.raises(mse.MseError):
        mse.process(frame, other_calib(noisy.shape), mse_params())


def test_degenerate_alpha_refused():
    _, noisy = make_bone_soft_phantom()
    frame = new_frame(noisy.astype(np.float32), noise=NoiseModel(alpha=-1.0, sigma=2.0))
    with pytest.raises(mse.MseError):
        mse.process(frame, other_calib(noisy.shape), mse_params())


# -- Scenario 8 + EC-4: DRC + normalization + saturation exclusion -------------


def test_drc_compression_applied():
    _, noisy = make_bone_soft_phantom()
    out = _process(noisy)
    rate = out.history[-1].extra["drc_compression_rate"]
    assert rate > EV["drc_compression_min"]


def test_output_in_unit_range_and_low_clipping():
    _, noisy = make_bone_soft_phantom()
    out = _process(noisy)
    op = np.asarray(out.pixel, np.float64)
    assert op.min() >= 0.0 and op.max() <= 1.0
    clipped = np.mean((op <= 0.0) | (op >= 1.0))
    assert clipped <= EV["clip_fraction_max"]


def test_saturation_excluded_from_normalization():
    _, noisy = make_bone_soft_phantom()
    masks = np.zeros(noisy.shape, dtype=np.uint8)
    # Inject an extreme saturated core; without exclusion it would drag the p99.9
    # percentile and crush the anatomy contrast.
    masks[40:44, 40:44] = int(MaskFlag.SATURATION)
    sat_noisy = noisy.copy()
    sat_noisy[40:44, 40:44] = 60000.0
    out = _process(sat_noisy, masks=masks)
    hi = out.history[-1].extra["norm_high"]
    # Normalization high stays near the anatomy range, not near the saturated value.
    assert hi < 10000.0


def test_saturation_mapped_to_domain_max_not_raw_dn():
    _, noisy = make_bone_soft_phantom()
    masks = np.zeros(noisy.shape, dtype=np.uint8)
    masks[10, 10] = int(MaskFlag.SATURATION)
    sat_noisy = noisy.copy()
    sat_noisy[10, 10] = 55000.0
    out = _process(sat_noisy, masks=masks)
    # Preserved IN THE OUTPUT DOMAIN: mapped to the normalized domain max (1.0),
    # NOT the raw detector DN (which would blow out the [0,1] output).
    op = np.asarray(out.pixel, np.float64)
    assert op[10, 10] == pytest.approx(1.0)
    assert op.max() <= 1.0  # no raw-DN outlier corrupting the range


def test_masks_substrate_unchanged():
    _, noisy = make_bone_soft_phantom()
    masks = np.zeros(noisy.shape, dtype=np.uint8)
    masks[5, 5] = int(MaskFlag.DEFECT)
    out = _process(noisy, masks=masks)
    assert np.array_equal(np.asarray(out.masks), masks)


# -- Scenario 6: soft-clip alternative (Optional, ⚠P) --------------------------


def test_soft_clip_alternative_path_selected():
    _, noisy = make_bone_soft_phantom()
    out_pl = _process(noisy, mse_params(mse_method="power_law"))
    out_sc = _process(noisy, mse_params(mse_method="soft_clip"))
    assert out_sc.history[-1].extra["method"] == "soft_clip"
    # Different modulation form yields a different result (deterministic path pick).
    assert not np.allclose(np.asarray(out_pl.pixel), np.asarray(out_sc.pixel))


def test_unknown_method_refused():
    _, noisy = make_bone_soft_phantom()
    with pytest.raises(mse.MseError):
        _process(noisy, mse_params(mse_method="bogus"))


# -- Scenario 13: contract (immutability + history) ----------------------------


def test_input_immutable_and_history_appended():
    _, noisy = make_bone_soft_phantom()
    frame = make_noise_frame(noisy)
    before = np.asarray(frame.pixel).copy()
    out = mse.process(frame, other_calib(noisy.shape), mse_params())
    assert np.array_equal(np.asarray(frame.pixel), before)  # input untouched
    assert len(out.history) == len(frame.history) + 1
    entry = out.history[-1]
    assert isinstance(entry, HistoryEntry)
    assert entry.module_name == "mse"
    for key in ("drc_gamma", "noise_beta", "norm_high", "gamma_mean"):
        assert key in entry.extra


def test_b_mid_param_overrides_robust_mean():
    _, noisy = make_bone_soft_phantom()
    out_default = _process(noisy)
    out_bmid = _process(noisy, mse_params(mse_drc_bmid=1500.0))
    assert not np.allclose(np.asarray(out_default.pixel), np.asarray(out_bmid.pixel))
