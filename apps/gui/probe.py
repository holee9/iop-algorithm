"""Hover pixel probe: integer coordinates + stored raw float values (C-03).

@MX:NOTE: [AUTO] `probe_at` and `scene_pos_to_pixel` are pure functions so
hover behavior is testable headlessly without dispatching real QMouseEvents
(REQ-VIEW-ARCH-6 logic-level coverage). `make_hover_proxy` wires the actual
`pg.SignalProxy` idiom for interactive use; it is exercised at the app-wiring
level, not asserted pixel-by-pixel in CI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
import pyqtgraph as pg

from apps.gui.layers import ImageLayer


@dataclass(frozen=True)
class ProbeReading:
    """Integer pixel coordinate + the raw stored value of every visible layer."""

    row: int
    col: int
    values: dict[str, float]  # layer name -> raw stored value (NOT the 8-bit render value)


def probe_at(layers: Sequence[ImageLayer], row: int, col: int) -> ProbeReading | None:
    """Return the raw stored value from every layer at (row, col), or None if OOB.

    Reads `ImageLayer.array` directly (C-03: "저장된 float32 원값", never the
    ImageItem's 8-bit rendered pixmap).
    """
    if not layers:
        return None
    shape = layers[0].array.shape
    if not (0 <= row < shape[0] and 0 <= col < shape[1]):
        return None
    values = {layer.name: layer.value_at(row, col) for layer in layers}
    return ProbeReading(row=row, col=col, values=values)


def scene_pos_to_pixel(item: pg.ImageItem, scene_pos) -> tuple[int, int]:
    """Map a scene-space position to an integer (row, col) via ImageItem's own
    view transform (C-02: reuse pyqtgraph's GPU/pixmap-view mapping, never a
    manually re-derived pan/zoom transform).
    """
    view_pos = item.mapFromScene(scene_pos)
    row = int(np.floor(view_pos.y()))
    col = int(np.floor(view_pos.x()))
    return row, col


def make_hover_proxy(
    view_box: pg.ViewBox, callback: Callable[[object], None], *, rate_limit: int = 60
) -> pg.SignalProxy:
    """Wire mouse-move hover events to `callback(event)` via `pg.SignalProxy`.

    `SignalProxy` is pyqtgraph's standard rate-limited hover idiom: it defers
    delivery until the event loop is idle instead of re-deriving the view
    transform / re-copying arrays on every raw mouse-move event (C-02).
    """
    scene = view_box.scene()
    return pg.SignalProxy(scene.sigMouseMoved, rateLimit=rate_limit, slot=callback)
