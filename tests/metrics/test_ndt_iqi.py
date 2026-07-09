"""T9 IQI auto-read + Class A/B report (SPEC-NDT-001 Scenario 4; EC-3).

Duplex-wire SRb reuse from T1 (REQ-NDT-IQI-1), single-wire minimum-visible-wire
detection (REQ-NDT-IQI-2), and the ISO 17636-2 Class A/B inspection report
(REQ-NDT-IQI-3/-4). Class thresholds are Params-consumed for the report; the
EV-301 pass line stays external.
"""

from __future__ import annotations

import pytest

from metrics import ndt
from metrics.ndt import IqiShot, build_iqi_report, read_single_wire_iqi
from metrics.result import MetricReadError
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import make_params


# -- REQ-NDT-IQI-1: duplex SRb reuse (T1 read_duplex_srb, not reimplemented) ----


def test_iqi_reuses_t1_duplex_srb_read():
    params = make_params()
    duplex = gen.make_duplex_profile()
    result = ndt.read_duplex_srb(duplex.profile, duplex.pairs, params)
    assert result.get("srb_um") == duplex.known_srb_um


def test_ec3_duplex_no_dip_read_failure():
    """EC-3: no 20% dip -> explicit read failure (T1 contract inherited)."""
    params = make_params()
    flat = gen.make_flat_duplex_profile()
    with pytest.raises(MetricReadError):
        ndt.read_duplex_srb(flat.profile, flat.pairs, params)


# -- REQ-NDT-IQI-2: single-wire minimum visible wire ---------------------------


def test_single_wire_minimum_visible_reproduced():
    """Finest visible wire = highest-numbered wire above the visibility threshold."""
    params = make_params()
    phantom = gen.make_single_wire_iqi()
    result = read_single_wire_iqi(phantom.profile, phantom.wires, params)
    assert result.get("min_visible_wire") == phantom.known_min_visible_wire


def test_single_wire_visibility_threshold_is_externalized():
    """A stricter injected threshold hides more wires -> coarser sensitivity."""
    phantom = gen.make_single_wire_iqi()
    strict = make_params(ndt_wire_visibility_threshold=0.35)
    result = read_single_wire_iqi(phantom.profile, phantom.wires, strict)
    # Only wires 10 (0.50) and 11 (0.40) clear 0.35 -> finest visible is 11.
    assert result.get("min_visible_wire") == 11


def test_single_wire_no_visible_wire_rejected():
    phantom = gen.make_single_wire_iqi()
    params = make_params(ndt_wire_visibility_threshold=0.99)
    with pytest.raises(MetricReadError):
        read_single_wire_iqi(phantom.profile, phantom.wires, params)


def test_single_wire_empty_rejected():
    params = make_params()
    with pytest.raises(MetricReadError):
        read_single_wire_iqi([1000.0, 1000.0], [], params)


# -- REQ-NDT-IQI-3/-4: Class A/B report ----------------------------------------


def _shots():
    # (snrn, wire) against defaults A:(snrn>=100, wire>=12) B:(snrn>=130, wire>=13)
    return [
        IqiShot(shot_index=1, snrn=150.0, srb_um=130.0, min_visible_wire=13),  # B
        IqiShot(shot_index=2, snrn=110.0, srb_um=130.0, min_visible_wire=13),  # A
        IqiShot(shot_index=3, snrn=90.0, srb_um=130.0, min_visible_wire=13),  # FAIL (SNRn)
        IqiShot(shot_index=4, snrn=150.0, srb_um=130.0, min_visible_wire=11),  # FAIL (wire)
    ]


def test_class_ab_report_reproduces_known_verdicts():
    params = make_params()
    report = build_iqi_report(_shots(), params)
    verdicts = [s.verdict for s in report.get("shots")]
    assert verdicts == ["B", "A", "FAIL", "FAIL"]


def test_class_ab_pass_flags():
    params = make_params()
    report = build_iqi_report(_shots(), params)
    rows = report.get("shots")
    assert rows[0].class_a_pass and rows[0].class_b_pass  # B implies A
    assert rows[1].class_a_pass and not rows[1].class_b_pass
    assert not rows[2].class_a_pass and not rows[2].class_b_pass
    assert not rows[3].class_a_pass and not rows[3].class_b_pass


def test_report_carries_shot_fields():
    """The inspection report row carries SNRn / SRb / min-visible-wire per shot."""
    params = make_params()
    report = build_iqi_report(_shots(), params)
    rows = report.get("shots")
    assert rows[0].snrn == 150.0
    assert rows[0].srb_um == 130.0
    assert rows[0].min_visible_wire == 13
    assert rows[0].shot_index == 1


def test_report_class_thresholds_are_params_not_embedded():
    """Loosening the injected Class B requirement changes the verdict."""
    loose = make_params(ndt_class_b_snrn_min=100.0, ndt_class_b_required_wire=12)
    report = build_iqi_report(_shots(), loose)
    # Shot 2 (snrn 110, wire 13) now clears the relaxed Class B.
    assert report.get("shots")[1].verdict == "B"
