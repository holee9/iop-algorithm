"""XDET-TC-032 -- Phase 1 image interaction: W/L, zoom/pan, probe, lossless receive.

SPEC-VIEWER-001 REQ-VIEW-IMAGE-1..4 (docs/GUI_CRITERIA.md C-01..04). All tests
run headlessly (QT_QPA_PLATFORM=offscreen, qtbot/pytest-qt -- pyqtgraph single
path, napari fallback per the Phase 0 spike).

Per SPEC-VIEWER-001 v0.1.1 decision D9, GUI test sources must not contain the
Gen 1 TC id string range ("000"-"021") so the capstone scan
(tests/test_tc_skeletons.py `_GEN1_TC_RANGE`) never mis-registers a deleted
Gen 1 test as alive.
"""

from __future__ import annotations

import pytest

pytest.importorskip("qtpy")  # C-12: must not block a [gui]-less core-no-gui collection

import numpy as np
import pyqtgraph as pg

from apps.gui.layers import WindowLevelControl, make_image_layer
from apps.gui.probe import probe_at


def _synthetic_frame(rows: int = 16, cols: int = 20, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (rng.standard_normal((rows, cols)) * 1000.0 - 250.0).astype(np.float32)


# -- REQ-VIEW-IMAGE-1 (C-01): W/L adjustment + direct numeric input ----------


def test_wl_adjustment_updates_display_levels():
    array = _synthetic_frame()
    layer = make_image_layer("input", array)

    layer.set_levels(-100.0, 100.0)

    assert layer.levels() == (-100.0, 100.0)


def test_wl_numeric_spinbox_input_updates_layer_levels(qtbot):
    """C-01: precise numeric entry (not only drag) must update the display."""
    array = _synthetic_frame()
    layer = make_image_layer("input", array)
    control = WindowLevelControl(layer)
    qtbot.addWidget(control)

    control.low_spin.setValue(-42.5)
    control.high_spin.setValue(317.25)

    assert layer.levels() == (-42.5, 317.25)


def test_wl_covers_full_float32_data_range():
    """C-01: the viewer must accept levels spanning the actual data extremes."""
    array = np.array([[-1.0e6, 0.0], [1.0e6, 1.0]], dtype=np.float32)
    layer = make_image_layer("input", array)

    lo, hi = float(np.min(array)), float(np.max(array))
    layer.set_levels(lo, hi)

    assert layer.levels() == (lo, hi)


# -- REQ-VIEW-IMAGE-2 (C-02): zoom/pan without per-event array copy ---------


def test_zoom_pan_does_not_copy_or_recompute_the_stored_array():
    array = _synthetic_frame()
    layer = make_image_layer("input", array)
    view = pg.ViewBox()
    view.addItem(layer.item)
    stored_id_before = id(layer.array)

    # Several zoom/pan events via the ViewBox's own transform API -- never
    # touching layer.array (C-02: GPU/pixmap view path, no per-event recompute
    # or array copy).
    view.setRange(xRange=(0, 5), yRange=(0, 5))
    view.setRange(xRange=(2, 18), yRange=(2, 14))
    view.scaleBy((0.5, 0.5))
    view.translateBy((1.0, 1.0))

    assert id(layer.array) == stored_id_before
    assert np.array_equal(layer.array, array)


# -- REQ-VIEW-IMAGE-3 (C-03): hover probe: integer coords + raw float value -


def test_hover_probe_reports_integer_coords_and_exact_stored_value():
    array = _synthetic_frame()
    layer = make_image_layer("input", array)

    reading = probe_at([layer], row=3, col=7)

    assert reading is not None
    assert reading.row == 3 and reading.col == 7
    assert reading.values["input"] == float(array[3, 7])


def test_hover_probe_value_is_independent_of_render_levels():
    """C-03: the probed value is the stored raw value, NOT the 8-bit display value."""
    array = _synthetic_frame()
    layer = make_image_layer("input", array)
    # Force the render levels far away from the actual pixel value.
    layer.set_levels(0.0, 1.0)

    reading = probe_at([layer], row=2, col=2)

    assert reading.values["input"] == float(array[2, 2])


def test_hover_probe_out_of_bounds_returns_none():
    array = _synthetic_frame()
    layer = make_image_layer("input", array)

    assert probe_at([layer], row=-1, col=0) is None
    assert probe_at([layer], row=0, col=array.shape[1]) is None


# -- REQ-VIEW-IMAGE-4 (C-04): lossless receive, 8-bit mapping in render path


def test_layer_array_receives_float32_pixels_untransformed():
    array = _synthetic_frame()
    layer = make_image_layer("input", array)

    assert layer.array.dtype == np.float32
    assert np.array_equal(layer.array, array.astype(np.float32))
    # ImageItem is fed the SAME float32 source values, not a pre-quantized copy.
    assert np.array_equal(layer.item.image, layer.array)


def test_layer_set_levels_does_not_mutate_the_stored_float32_array():
    """C-04: 8-bit mapping is render-path only -- set_levels must not touch `array`."""
    array = _synthetic_frame()
    layer = make_image_layer("input", array)
    before = layer.array.copy()

    layer.set_levels(-9999.0, 9999.0)

    assert np.array_equal(layer.array, before)
    assert layer.array.dtype == np.float32
