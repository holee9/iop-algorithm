"""Code-review regression gates for T9 NDT (SPEC-NDT-001, review round 2).

Each test pins one verified defect fixed in ``metrics/ndt.py``:

- defect 1: ``correct_thickness`` oversized-scale guard must compare the ACTUAL
  kernel extent (``2*scale+1`` for morphological opening), not the raw scale, so
  a default-method call whose doubled kernel exceeds the frame passes through
  numerically unchanged with a warning (REQ-NDT-THICK-3 / EC-2). The guard stays
  method-specific: the Gaussian path keys off its own effective radius (sigma).
- defect 2: ``SNRnAccumulator.update`` must validate and reject a degenerate
  frame BEFORE mutating the shared Welford accumulator (reject = true no-op).
- defect 3: ``read_single_wire_iqi`` raises ``MetricReadError`` (not a raw
  ``IndexError``) for an out-of-range wire index.
- defect 5: ``SNRnAccumulator.update`` reuses ``compute_snrn`` (single source of
  the SNR -> SNRn normalization); the streamed SNRn equals ``compute_snrn`` on
  the accumulated ROI mean.
- defect 6: ``morphological_opening`` uses a circular (disk) structuring element
  (plan.md HOW), verified by isotropic corner-rounding vs a square SE.
"""

from __future__ import annotations

import numpy as np
import pytest

from common.robust_stats import WelfordAccumulator
from common.xframe import new_frame
from metrics.ndt import (
    SNRnAccumulator,
    WireElement,
    compute_snrn,
    correct_thickness,
    read_single_wire_iqi,
)
from metrics.result import MetricReadError
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import make_params


# -- defect 1: oversized-scale guard uses the ACTUAL kernel extent -------------


def test_defect1_oversized_opening_kernel_passes_through():
    """scale=70 -> opening kernel 2*70+1 = 141 px exceeds the 128 px frame.

    The raw scale (70) is < 128, so the old raw-scale guard missed it and the
    default (morphological_opening) call silently produced a degenerate flatten.
    The kernel-aware guard must pass through unchanged with a warning.
    """
    ph = gen.make_thickness_defect_phantom()  # 128x128, real low-freq ramp
    params = make_params(ndt_thickness_scale_px=70)  # DEFAULT method = opening
    res = correct_thickness(ph.frame, params)

    assert not res.changed
    assert any("scale" in w for w in res.warnings)
    original = np.asarray(ph.frame.pixel, dtype=np.float64)
    assert np.array_equal(res.flattened, original)


def test_defect1_guard_is_method_specific_gaussian_still_processes():
    """The same numeric scale that trips the opening kernel guard must NOT trip
    the gaussian path: the gaussian's effective radius is sigma (70) < 128."""
    ph = gen.make_thickness_defect_phantom()
    params = make_params(ndt_thickness_method="gaussian", ndt_thickness_scale_px=70)
    res = correct_thickness(ph.frame, params)
    assert res.changed


# -- defect 2: rejected frame is a true no-op on accumulator state -------------


def test_defect2_rejected_frame_is_noop_on_accumulator():
    """A degenerate frame rejected mid-stream must not poison the running mean."""
    params = make_params()
    seq = gen.make_snrn_sequence()
    shape = np.asarray(seq.frames[0].pixel).shape
    degenerate = new_frame(np.full(shape, 2000.0, dtype=np.float32))  # zero-noise

    poisoned = SNRnAccumulator(seq.roi, seq.srb_um, params)
    with pytest.raises(MetricReadError):
        poisoned.update(degenerate)  # must reject WITHOUT folding the frame in
    for frame in seq.frames:
        poisoned.update(frame)

    clean = SNRnAccumulator(seq.roi, seq.srb_um, params)
    for frame in seq.frames:
        clean.update(frame)

    # The rejected frame must have left accumulator state untouched: the two
    # runs must be bit-identical.
    assert poisoned.current.frame_count == clean.current.frame_count
    assert poisoned.current.snr == clean.current.snr
    assert poisoned.current.snrn == clean.current.snrn
    assert [e.snrn for e in poisoned.shot_log] == [e.snrn for e in clean.shot_log]


# -- defect 5: single source of truth (compute_snrn reuse) ---------------------


def test_defect5_streamed_snrn_equals_compute_snrn_on_accumulated_roi():
    """The streamed SNRn equals compute_snrn evaluated on the accumulated ROI."""
    params = make_params()
    seq = gen.make_snrn_sequence()
    acc = SNRnAccumulator(seq.roi, seq.srb_um, params)
    welford = WelfordAccumulator()
    t, l, h, w = seq.roi

    for frame in seq.frames:
        entry = acc.update(frame)
        region = np.asarray(frame.pixel, dtype=np.float64)[t : t + h, l : l + w]
        welford.update(region)
        ref = compute_snrn(
            new_frame(welford.mean), (0, 0, h, w), seq.srb_um, params
        )
        assert entry.snrn == ref.get("snrn")
        assert entry.snr == ref.get("snr")


# -- defect 3: out-of-range wire index -> MetricReadError, not IndexError -------


def test_defect3_out_of_range_wire_index_raises_metricreaderror():
    params = make_params()
    profile = np.full(50, 1000.0, dtype=np.float64)
    wires = [WireElement(number=10, index=500)]  # 500 >= len 50
    with pytest.raises(MetricReadError):
        read_single_wire_iqi(profile, wires, params)


def test_defect3_negative_wire_index_raises_metricreaderror():
    params = make_params()
    profile = np.full(50, 1000.0, dtype=np.float64)
    profile[47] = 500.0  # a real dip at index -3 (wrap) so a pre-fix read "sees" it
    wires = [WireElement(number=10, index=-3)]
    with pytest.raises(MetricReadError):
        read_single_wire_iqi(profile, wires, params)


# -- defect 6: morphological opening uses a circular (disk) SE ------------------


def test_defect6_opening_uses_circular_structuring_element():
    """A disk of radius r cannot cover a bright block's corner from inside
    (corner distance r*sqrt(2) > r), so the corner is rounded away; an
    edge-midpoint (distance r) is kept. A square SE (the bug) keeps the corner."""
    n = 61
    img = np.zeros((n, n), dtype=np.float32)
    img[15:46, 15:46] = 100.0  # a 31x31 bright block
    frame = new_frame(img)
    params = make_params(
        ndt_thickness_method="morphological_opening",
        ndt_thickness_scale_px=6,
        ndt_thickness_gradient_min_frac=0.0,
    )
    res = correct_thickness(frame, params)
    low = np.asarray(res.low_freq, dtype=np.float64)  # the opening (low-freq est.)

    assert low[15, 15] < 50.0  # corner rounded away by the disk
    assert low[15, 30] > 50.0  # mid-edge kept (a disk fits inside covering it)
