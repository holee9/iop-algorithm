"""NDT duplex-wire SRb and SNRn (Scenario 7; EC-5)."""

from __future__ import annotations

import pytest

from metrics import ndt
from metrics.result import MetricReadError
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import TOLERANCES, make_params


def test_scenario7_srb_first_unresolved_pair():
    """First pair with dip < 20% determines SRb_image."""
    phantom = gen.make_duplex_profile()
    result = ndt.read_duplex_srb(phantom.profile, phantom.pairs, make_params())
    assert result.get("first_unresolved_pair") == phantom.known_first_unresolved
    assert result.get("srb_um") == phantom.known_srb_um


def test_scenario7_snrn_reproduced():
    """SNRn = SNR * 88.6 / SRb reproduces the known value within [T]."""
    params = make_params()
    duplex = gen.make_duplex_profile()
    srb = ndt.read_duplex_srb(duplex.profile, duplex.pairs, params).get("srb_um")
    uniform = gen.make_uniform_snr_frame()
    result = ndt.compute_snrn(uniform.frame, uniform.roi, srb, params)

    expected_snrn = uniform.known_snr * 88.6 / srb
    rel = abs(result.get("snrn") - expected_snrn) / expected_snrn
    assert rel < TOLERANCES["snrn_rel"], (result.get("snrn"), expected_snrn)
    # SNR itself reproduced.
    assert abs(result.get("snr") - uniform.known_snr) / uniform.known_snr < TOLERANCES["snrn_rel"]


def test_ec5_no_dip_read_failure():
    """EC-5: no resolvable dip -> explicit read failure (no SRb estimate)."""
    phantom = gen.make_flat_duplex_profile()
    with pytest.raises(MetricReadError):
        ndt.read_duplex_srb(phantom.profile, phantom.pairs, make_params())
