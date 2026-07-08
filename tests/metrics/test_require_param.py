"""Code-review defect #9: required Params access must fail explicitly.

`int(params.get(KEY))` / `float(params.get(KEY))` crash with an opaque TypeError
when the key is missing (None). Every required key across metrics/ must instead
raise MetricReadError naming the missing key (via metrics.result.require_param).
"""

from __future__ import annotations

import numpy as np
import pytest

from common.contract import Params
from common.xframe import new_frame
from metrics import defect_stats, dqe, mtf, ndt, nps
from metrics.result import MetricReadError, require_param
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import make_params


def _params_without(key):
    p = make_params()
    values = {k: v for k, v in p.values.items() if k != key}
    return Params(values=values)


def test_require_param_names_missing_key():
    p = Params(values={})
    with pytest.raises(MetricReadError, match="missing required parameter 'foo'"):
        require_param(p, "foo", int)


def test_require_param_casts_present_value():
    p = Params(values={"n": "4"})
    assert require_param(p, "n", int) == 4


def test_mtf_missing_required_param_raises():
    phantom = gen.make_slanted_edge()
    with pytest.raises(MetricReadError, match="mtf_oversample"):
        mtf.compute_mtf(phantom.frame, _params_without("mtf_oversample"))


def test_nps_missing_required_param_raises():
    noise = gen.make_white_noise_frames(shape=(256, 256), n_frames=4)
    with pytest.raises(MetricReadError, match="nps_roi_size"):
        nps.compute_nps(noise.frames, _params_without("nps_roi_size"))


def test_dqe_missing_required_param_raises():
    freqs = np.array([0.0, 1.0, 2.0])
    with pytest.raises(MetricReadError, match="dqe_q"):
        dqe.compute_dqe(freqs, np.ones(3), np.ones(3), _params_without("dqe_q"))


def test_defect_missing_required_param_raises():
    phantom = gen.make_defect_stacks()
    with pytest.raises(MetricReadError, match="defect_over_value"):
        defect_stats.classify_defects(
            phantom.dark_frames, phantom.flat_frames, _params_without("defect_over_value")
        )


def test_ndt_missing_required_param_raises():
    phantom = gen.make_duplex_profile()
    with pytest.raises(MetricReadError, match="ndt_dip_threshold"):
        ndt.read_duplex_srb(phantom.profile, phantom.pairs, _params_without("ndt_dip_threshold"))
