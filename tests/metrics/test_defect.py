"""Bad-pixel E2597 classification (Scenario 6; EC-4)."""

from __future__ import annotations

import pytest

from metrics import defect_stats
from metrics.defect_stats import DefectClass
from metrics.result import MetricReadError
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import make_params


def test_scenario6_seven_class_map_reproduced():
    """Each planted E2597 class is detected at its known coordinate."""
    phantom = gen.make_defect_stacks()
    result = defect_stats.classify_defects(
        phantom.dark_frames, phantom.flat_frames, make_params(), truth_map=phantom.truth_map
    )
    class_map = result.get("class_map")
    for (r, c), kind in phantom.planted.items():
        assert class_map[r, c] == kind, (r, c, DefectClass(class_map[r, c]).name, kind.name)


def test_scenario6_miss_rate_zero_and_fractions():
    """Miss rate is 0 when all planted defects are found; fractions present."""
    phantom = gen.make_defect_stacks()
    result = defect_stats.classify_defects(
        phantom.dark_frames, phantom.flat_frames, make_params(), truth_map=phantom.truth_map
    )
    assert result.get("miss_rate") == 0.0
    fractions = result.get("fractions")
    assert set(fractions) == {c.name for c in DefectClass}
    assert abs(sum(fractions.values()) - 1.0) < 1e-9


def test_ec4_insufficient_stack_rejected():
    """EC-4: stack count below minimum -> reject with error."""
    phantom = gen.make_defect_stacks(n_frames=10)
    with pytest.raises(MetricReadError):
        defect_stats.classify_defects(
            phantom.dark_frames[:3], phantom.flat_frames[:3], make_params()
        )


def test_ec4_all_dead_region_rejected():
    """EC-4: all-dead ROI (no gain) -> reject with error."""
    phantom = gen.make_defect_stacks()
    # Flat == dark everywhere -> median gain 0 -> non-positive -> reject.
    dead_flats = phantom.dark_frames
    with pytest.raises(MetricReadError):
        defect_stats.classify_defects(phantom.dark_frames, dead_flats, make_params())
