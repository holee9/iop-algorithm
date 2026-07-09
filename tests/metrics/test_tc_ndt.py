"""XDET-TC-018 / XDET-TC-019 live release gates for the T9/WP10 NDT module.

Converts the deferred T9 skeletons (tests/test_tc_skeletons.py) into working
gate cases. These gate the NEW T9 processing (streaming SNRn accumulation +
single-wire IQI report + thickness correction) against EV thresholds on
synthetic phantoms — NOT the pre-existing T1 read functions. Measurement !=
judgment: the EV min values are external-injected (tests.metrics.phantoms.params
EV_NDT); the engine only produces values.

- XDET-TC-018 (VV-011, hard DoD): synthetic known SNRn / SRb / minimum-visible-
  wire reproduced by the streaming accumulator + single-wire read + Class A/B
  report vs EV-301 min.
- XDET-TC-019 (VV-011, hard DoD): thickness correction preserves the high-freq
  defect band -> SRb degradation <= EV-102 min AND MTF@Nyquist retention >=
  EV-102 min (deterministic, via the T1 metrics/mtf engine), plus a CSa proxy vs
  EV-303 min. The edge-based MTF/SRb leg uses the Gaussian estimator (see the
  SPEC deviation note in the SPEC-NDT-001 completion report).
"""

from __future__ import annotations

import numpy as np

from common.xframe import new_frame
from metrics import mtf, ndt
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import EV_NDT, make_params


# -- XDET-TC-018: streaming SNRn + duplex SRb + single-wire + Class A/B --------


def test_tc018_snrn_srb_iqi_autoread_meets_ev301():
    """Known SNRn / SRb / min-visible-wire reproduced; Class A satisfied (EV-301)."""
    params = make_params()

    # (1) duplex SRb reused from T1 (SWR-1202) — known SRb.
    duplex = gen.make_duplex_profile()
    srb = ndt.read_duplex_srb(duplex.profile, duplex.pairs, params).get("srb_um")
    assert srb == duplex.known_srb_um

    # (2) streaming SNRn accumulation (SWR-1201, NEW T9) over a known sequence.
    seq = gen.make_snrn_sequence(srb_um=srb)
    acc = ndt.SNRnAccumulator(seq.roi, srb, params)
    for frame in seq.frames:
        acc.update(frame)
    final_snrn = acc.current.snrn
    # Reproduces the analytic sqrt(k) progression at the last frame.
    expected = seq.known_snrn(seq.n_frames, norm_um=88.6)
    assert abs(final_snrn - expected) / expected < 0.15, (final_snrn, expected)

    # (3) single-wire IQI minimum visible wire (SWR-1204, NEW T9).
    wire_ph = gen.make_single_wire_iqi()
    min_wire = ndt.read_single_wire_iqi(
        wire_ph.profile, wire_ph.wires, params
    ).get("min_visible_wire")
    assert min_wire == wire_ph.known_min_visible_wire

    # (4) Class A/B report (SWR-1204, NEW T9) combining the three.
    report = ndt.build_iqi_report(
        [ndt.IqiShot(shot_index=1, snrn=final_snrn, srb_um=srb, min_visible_wire=min_wire)],
        params,
    )
    row = report.get("shots")[0]

    # EV-301 min is external-injected (measurement != judgment).
    ev301_snrn_min = EV_NDT["ev301_snrn_class_a_min"]
    assert final_snrn >= ev301_snrn_min
    assert row.class_a_pass  # SNRn Class A met AND required wire read
    assert row.verdict in ("A", "B")


# -- XDET-TC-019: thickness correction SRb protection + CSa --------------------

_MTF_PARAMS = make_params()  # default angle range [1.5, 3.0] deg


def _mtf_nyquist_and_srb(image: np.ndarray) -> tuple[float, float]:
    res = mtf.compute_mtf(new_frame(image.astype(np.float32)), _MTF_PARAMS)
    freq = res.get("frequencies_lpmm")
    m = res.get("mtf")
    idx = np.where(m < 0.5)[0]
    f50 = float(freq[idx[0]]) if idx.size else float(freq[-1])
    return res.get("mtf_at_nyquist"), 1.0 / f50  # SRb ~ 1 / f50


def test_tc019_thickness_srb_protection_meets_ev102():
    """Hard DoD: MTF@Nyquist retention >= EV-102 min AND SRb degrade <= EV-102 min."""
    ph = gen.make_thickness_edge_phantom()
    raw = np.asarray(ph.frame.pixel, dtype=np.float64)

    # Edge-based resolution measurement uses the Gaussian estimator.
    params = make_params(ndt_thickness_method="gaussian", ndt_thickness_scale_px=40)
    res = ndt.correct_thickness(ph.frame, params)
    assert res.changed

    mtf_before, srb_before = _mtf_nyquist_and_srb(raw[ph.band])
    mtf_after, srb_after = _mtf_nyquist_and_srb(res.flattened[ph.band])

    retention = mtf_after / mtf_before
    srb_degrade = (srb_after - srb_before) / srb_before
    assert retention >= EV_NDT["ev102_mtf_retention_min"], retention
    assert srb_degrade <= EV_NDT["ev102_srb_degrade_max_frac"], srb_degrade


def test_tc019_thickness_preserves_defect_and_csa_meets_ev303():
    """Defect band preserved and CSa (achieved contrast sensitivity) <= EV-303 min."""
    ph = gen.make_thickness_defect_phantom()
    params = make_params(ndt_thickness_method="gaussian", ndt_thickness_scale_px=20)
    res = ndt.correct_thickness(ph.frame, params)

    # High-frequency defect amplitude preserved.
    amp_after = ph.defect_amplitude(res.flattened)
    assert abs(amp_after - ph.known_defect_amp) / ph.known_defect_amp <= 0.10

    # CSa proxy = residual-noise / signal in the flat (defect-free) region.
    from common import robust_stats

    residual = robust_stats.robust_std(res.flattened[ph.flat_roi])
    csa = residual / ph.signal_level
    assert csa <= EV_NDT["ev303_csa_max_frac"], csa
