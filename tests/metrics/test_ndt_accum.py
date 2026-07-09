"""T9 streaming SNRn accumulation (SPEC-NDT-001 Scenarios 2, 3; EC-1).

Welford online mean/variance vs the batch temporal_mean_std reference
(REQ-NDT-ACCUM-1/-5), real-time SNRn progression + acquisition-termination
signal + per-shot log (REQ-NDT-ACCUM-2/-3/-4), and the zero-noise / degenerate
ROI rejection (REQ-NDT-ACCUM-6).
"""

from __future__ import annotations

import numpy as np
import pytest

from common.robust_stats import WelfordAccumulator, online_mean_var, temporal_mean_std
from common.xframe import new_frame
from metrics.ndt import SNRnAccumulator
from metrics.result import MetricReadError
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import TOLERANCES, make_params


# -- Scenario 2: Welford online == batch temporal_mean_std ---------------------


def test_scenario2_welford_online_matches_batch_mean_std():
    """Streaming (count, mean, M2) reproduces the batch per-pixel mean/std."""
    phantom = gen.make_welford_sequence()
    acc = WelfordAccumulator()
    for frame in phantom.frames:  # streamed one at a time (stack never held)
        acc.update(frame)

    batch_mean, batch_std = temporal_mean_std(phantom.stack)
    atol = TOLERANCES["welford_atol"]
    rtol = TOLERANCES["welford_rtol"]
    assert acc.count == len(phantom.frames)
    assert np.allclose(acc.mean, batch_mean, atol=atol, rtol=rtol)
    # Population variance (ddof=0) matches np.std default used by the batch ref.
    assert np.allclose(acc.std(ddof=0), batch_std, atol=atol, rtol=rtol)


def test_welford_online_mean_var_helper_matches_batch():
    phantom = gen.make_welford_sequence(seed=42)
    mean, var = online_mean_var(phantom.frames, ddof=0)
    batch_mean, batch_std = temporal_mean_std(phantom.stack)
    assert np.allclose(mean, batch_mean, atol=TOLERANCES["welford_atol"])
    assert np.allclose(np.sqrt(var), batch_std, atol=TOLERANCES["welford_atol"])


def test_welford_empty_accumulator_raises():
    acc = WelfordAccumulator()
    assert acc.count == 0
    with pytest.raises(ValueError):
        _ = acc.mean
    with pytest.raises(ValueError):
        _ = acc.variance()


def test_welford_shape_mismatch_raises():
    acc = WelfordAccumulator()
    acc.update(np.zeros((4, 4)))
    with pytest.raises(ValueError):
        acc.update(np.zeros((4, 5)))


# -- Scenario 3: streaming SNRn progression + termination + shot log -----------


def test_scenario3_streaming_snrn_reproduces_sqrt_k_progression():
    """Running SNRn tracks the known (mean/sigma)*sqrt(k) * 88.6/SRb curve."""
    params = make_params()
    seq = gen.make_snrn_sequence()
    acc = SNRnAccumulator(seq.roi, seq.srb_um, params)

    for frame in seq.frames:
        acc.update(frame)

    tol = TOLERANCES["snrn_progression_rel"]
    for k in (1, 4, 9, 16):
        entry = acc.shot_log[k - 1]
        expected_snrn = seq.known_snrn(k, norm_um=88.6)
        rel = abs(entry.snrn - expected_snrn) / expected_snrn
        assert rel < tol, (k, entry.snrn, expected_snrn, rel)
        # SNR grows monotonically as frames accumulate (noise averages down).
    snrns = [e.snrn for e in acc.shot_log]
    assert snrns[-1] > snrns[0]


def test_scenario3_acquisition_termination_signal():
    """Termination fires at the first frame whose running SNRn >= target."""
    seq = gen.make_snrn_sequence()
    # Target between the SNRn at k=4 and k=9 -> reached somewhere in that window.
    target = 0.5 * (seq.known_snrn(4) + seq.known_snrn(9))
    params = make_params(ndt_target_snrn=target)
    acc = SNRnAccumulator(seq.roi, seq.srb_um, params)

    reached_at = None
    for frame in seq.frames:
        entry = acc.update(frame)
        if acc.target_reached and reached_at is None:
            reached_at = entry.frame_count

    assert acc.target_reached
    assert acc.target_frame_index == reached_at
    # The signalled frame is the FIRST at or above target; the prior one is below.
    idx = acc.target_frame_index
    assert acc.shot_log[idx - 1].snrn >= target
    assert acc.shot_log[idx - 2].snrn < target


def test_scenario3_target_not_reached_stays_false():
    seq = gen.make_snrn_sequence()
    params = make_params(ndt_target_snrn=1e9)  # unreachable
    acc = SNRnAccumulator(seq.roi, seq.srb_um, params)
    for frame in seq.frames:
        acc.update(frame)
    assert not acc.target_reached
    assert acc.target_frame_index is None


def test_scenario3_shot_log_records_iso_fields():
    """Every shot logs (index, SNRn, SRb, frame count) per ISO 17636-2."""
    seq = gen.make_snrn_sequence()
    params = make_params()
    acc = SNRnAccumulator(seq.roi, seq.srb_um, params)
    for frame in seq.frames:
        acc.update(frame)

    log = acc.shot_log
    assert len(log) == seq.n_frames
    for i, entry in enumerate(log, start=1):
        assert entry.shot_index == i
        assert entry.frame_count == i
        assert entry.srb_um == seq.srb_um
        assert entry.snrn > 0.0


# -- EC-1: degenerate ROI / zero-noise rejection -------------------------------


def test_ec1_zero_noise_region_rejected():
    """A constant (zero-noise) accumulated region raises, no silent SNR."""
    params = make_params()
    const = new_frame(np.full((64, 64), 2000.0, dtype=np.float32))
    acc = SNRnAccumulator((8, 8, 40, 40), srb_um=150.0, params=params)
    with pytest.raises(MetricReadError):
        acc.update(const)


def test_ec1_roi_out_of_bounds_rejected():
    params = make_params()
    frame = new_frame(np.full((32, 32), 2000.0, dtype=np.float32))
    acc = SNRnAccumulator((0, 0, 40, 40), srb_um=150.0, params=params)
    with pytest.raises(MetricReadError):
        acc.update(frame)


def test_ec1_insufficient_pixels_rejected():
    params = make_params(ndt_min_roi_pixels=100)
    seq = gen.make_snrn_sequence()
    acc = SNRnAccumulator((0, 0, 4, 4), seq.srb_um, params)  # 16 < 100 pixels
    with pytest.raises(MetricReadError):
        acc.update(seq.frames[0])


def test_ec1_nonpositive_srb_rejected():
    params = make_params()
    with pytest.raises(MetricReadError):
        SNRnAccumulator((0, 0, 8, 8), srb_um=0.0, params=params)
