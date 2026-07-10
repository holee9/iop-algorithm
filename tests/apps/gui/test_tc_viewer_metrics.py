"""XDET-TC-034 -- Phase 1 metrics delegation + ROI round-trip.

SPEC-VIEWER-001 REQ-VIEW-RUN-3..6 (docs/GUI_CRITERIA.md C-09/C-10). Headless
via qtbot/pytest-qt (QT_QPA_PLATFORM=offscreen).

Per SPEC-VIEWER-001 v0.1.1 decision D9, GUI test sources must not contain the
Gen 1 TC id string range ("000"-"021") so the capstone scan
(tests/test_tc_skeletons.py `_GEN1_TC_RANGE`) never mis-registers a deleted
Gen 1 test as alive.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytest.importorskip("qtpy")  # C-12: must not block a [gui]-less core-no-gui collection

import numpy as np
import pyqtgraph as pg

from apps.gui import metrics_panel
from apps.gui.metrics_panel import RoiBounds, plot_mtf, recompute_mtf_for_roi, roi_bounds_from_rect_roi
from metrics.mtf import compute_mtf
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import make_params


def _phantom(shape=(128, 128), angle_deg=2.0):
    return gen.make_slanted_edge(shape=shape, angle_deg=angle_deg, sigma_px=0.6)


# -- REQ-VIEW-RUN-3/4 (C-09): plotted values ARE the engine's output, verbatim


def test_plot_mtf_plots_exact_engine_output_arrays(qtbot):
    phantom = _phantom()
    params = make_params()
    plot_widget = pg.PlotWidget()
    qtbot.addWidget(plot_widget)

    result = plot_mtf(plot_widget, phantom.frame, params)

    direct = compute_mtf(phantom.frame, params)
    assert np.array_equal(result.get("frequencies_lpmm"), direct.get("frequencies_lpmm"))
    assert np.array_equal(result.get("mtf"), direct.get("mtf"))

    # The plotted curve is literally the returned arrays -- not a re-derived copy.
    curves = plot_widget.getPlotItem().listDataItems()
    assert len(curves) == 1
    x_data, y_data = curves[0].getData()
    assert np.array_equal(x_data, result.get("frequencies_lpmm"))
    assert np.array_equal(y_data, result.get("mtf"))


def test_gui_metrics_path_invokes_the_engine_exactly_once_per_plot(qtbot):
    """C-09/EC-6: no separate GUI-side computation -- exactly one engine call."""
    phantom = _phantom()
    params = make_params()
    plot_widget = pg.PlotWidget()
    qtbot.addWidget(plot_widget)

    with patch.object(metrics_panel, "compute_mtf", wraps=compute_mtf) as spy:
        plot_mtf(plot_widget, phantom.frame, params)

    assert spy.call_count == 1


# -- REQ-VIEW-RUN-5 (C-10): the exact ROI boundary used is reported ----------


def test_roi_bounds_from_rect_roi_reports_exact_boundary():
    roi = pg.RectROI(pos=[16, 32], size=[64, 64])

    bounds = roi_bounds_from_rect_roi(roi, frame_shape=(128, 128))

    assert bounds == RoiBounds(top=32, left=16, height=64, width=64)


def test_roi_bounds_clamped_to_frame_when_partially_off_frame():
    roi = pg.RectROI(pos=[-10, 100], size=[64, 64])

    bounds = roi_bounds_from_rect_roi(roi, frame_shape=(128, 128))

    assert 0 <= bounds.left <= 127
    assert 0 <= bounds.top <= 127
    assert bounds.top + bounds.height <= 128
    assert bounds.left + bounds.width <= 128


# -- REQ-VIEW-RUN-6 (C-10): same ROI boundary -> identical recomputed value --


def test_roi_round_trip_recompute_matches_displayed_value(qtbot):
    full_frame = _phantom().frame
    params = make_params()
    bounds = RoiBounds(top=32, left=16, height=64, width=64)

    sub_frame = bounds.slice_frame(full_frame)
    plot_widget = pg.PlotWidget()
    qtbot.addWidget(plot_widget)
    displayed = plot_mtf(plot_widget, sub_frame, params)

    recomputed = recompute_mtf_for_roi(full_frame, params, bounds)

    assert np.array_equal(displayed.get("frequencies_lpmm"), recomputed.get("frequencies_lpmm"))
    assert np.array_equal(displayed.get("mtf"), recomputed.get("mtf"))


def test_roi_round_trip_is_deterministic_across_repeated_recompute():
    """C-16 determinism inheritance: repeated recompute with the same bounds
    yields bit-identical results (no incidental randomness/state leakage).
    """
    full_frame = _phantom().frame
    params = make_params()
    bounds = RoiBounds(top=32, left=16, height=64, width=64)

    first = recompute_mtf_for_roi(full_frame, params, bounds)
    second = recompute_mtf_for_roi(full_frame, params, bounds)

    assert np.array_equal(first.get("mtf"), second.get("mtf"))
    assert np.array_equal(first.get("frequencies_lpmm"), second.get("frequencies_lpmm"))
