"""Input/output/diff/mask layer builders on pyqtgraph (C-04/C-06/C-07).

@MX:ANCHOR: [AUTO] `make_image_layer`/`make_diff_layer`/`make_mask_overlay_layers`
are the sole producers of on-screen layers for module_panel.py and app.py.
@MX:REASON: every REQ-VIEW-IMAGE/COMPARE display path (input, output, diff,
4 mask overlays) is built through these three functions; a change to the
row/column axis convention or the diff colormap ripples into every consumer.

Design notes:
- `pg.setConfigOptions(imageAxisOrder="row-major")` is set at import time so
  every `pg.ImageItem` in this app interprets a (rows, cols) numpy array with
  the SAME (row, col) indexing as `XFrame.pixel` -- no manual transpose at the
  call sites (C-04 no re-derivation of pipeline array orientation).
- `ImageLayer.array` is the untransformed float32 (or signed float diff)
  source; 8-bit LUT mapping happens only inside pyqtgraph's render path via
  `ImageItem.setLevels`/`setColorMap` (C-04 -- no separate uint8 copy is kept
  as "the" stored value; `probe.py` reads `ImageLayer.array` directly, C-03).
- Mask overlays are plain RGBA arrays of the SAME (rows, cols) shape as the
  base image, so they are pixel-aligned at every zoom level by construction
  (C-07) -- pyqtgraph's ImageItem applies the identical implicit 1:1 pixel
  transform to every layer added to the same ViewBox.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pyqtgraph as pg
from qtpy.QtWidgets import QDoubleSpinBox, QFormLayout, QWidget

from apps.gui.config import GuiConfig, diff_range
from common.xframe import MaskFlag, XFrame

# Applied once at import: every ImageItem in this process reads (row, col).
pg.setConfigOptions(imageAxisOrder="row-major")

# Independent color per mask flag (C-07); alpha is carried per-pixel in the
# RGBA overlay array, opacity slider scales it further via QGraphicsItem.setOpacity.
MASK_COLORS: dict[MaskFlag, tuple[int, int, int]] = {
    MaskFlag.DEFECT: (220, 20, 20),
    MaskFlag.SATURATION: (255, 165, 0),
    MaskFlag.INTERPOLATION: (0, 170, 255),
    MaskFlag.SATURATION_BAND: (230, 230, 0),
}


@dataclass
class ImageLayer:
    """A single image layer: the stored source array + its pyqtgraph ImageItem."""

    name: str
    array: np.ndarray  # untransformed source values (C-04); probe reads this
    item: pg.ImageItem

    def set_levels(self, low: float, high: float) -> None:
        """Apply W/L contrast limits (C-01) -- render-path only, no array copy."""
        self.item.setLevels((float(low), float(high)))

    def levels(self) -> tuple[float, float]:
        low, high = self.item.getLevels()
        return (float(low), float(high))

    def value_at(self, row: int, col: int) -> float:
        """Stored raw value at (row, col) -- the C-03 probe's source of truth."""
        return float(self.array[row, col])


def make_image_layer(name: str, array: np.ndarray) -> ImageLayer:
    """Build a float32 image layer with an identity (no-op) initial LUT range."""
    arr = np.asarray(array, dtype=np.float32)
    item = pg.ImageItem(arr)
    layer = ImageLayer(name=name, array=arr, item=item)
    lo = float(np.min(arr)) if arr.size else 0.0
    hi = float(np.max(arr)) if arr.size else 1.0
    if hi <= lo:
        hi = lo + 1.0
    layer.set_levels(lo, hi)
    return layer


class WindowLevelControl(QWidget):
    """Numeric W/L input widget wired directly to an `ImageLayer` (C-01).

    Two `QDoubleSpinBox` fields (low/high) let the user type EXACT contrast
    limits, in addition to any slider-driven adjustment; both paths converge
    on `ImageLayer.set_levels` so display updates identically either way.
    """

    def __init__(self, layer: ImageLayer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layer = layer
        self.low_spin = QDoubleSpinBox(self)
        self.high_spin = QDoubleSpinBox(self)
        self.low_spin.setToolTip(
            "Lower contrast limit (W/L) for the Output display. Type an "
            "exact float32 value -- the render updates immediately (C-01)."
        )
        self.high_spin.setToolTip(
            "Upper contrast limit (W/L) for the Output display. Type an "
            "exact float32 value -- the render updates immediately (C-01)."
        )
        for spin in (self.low_spin, self.high_spin):
            spin.setRange(-1.0e30, 1.0e30)
            spin.setDecimals(6)
        low, high = layer.levels()
        self.low_spin.setValue(low)
        self.high_spin.setValue(high)
        self.low_spin.valueChanged.connect(self._on_changed)
        self.high_spin.valueChanged.connect(self._on_changed)
        layout = QFormLayout(self)
        layout.addRow("Low", self.low_spin)
        layout.addRow("High", self.high_spin)

    def _on_changed(self, _value: float) -> None:
        self.layer.set_levels(self.low_spin.value(), self.high_spin.value())


def _diverging_colormap() -> pg.ColorMap:
    """0-centered blue-white-red diverging colormap (C-06), no external cmap dep."""
    pos = np.array([0.0, 0.5, 1.0])
    color = np.array(
        [
            [30, 60, 220, 255],
            [255, 255, 255, 255],
            [220, 30, 30, 255],
        ],
        dtype=np.ubyte,
    )
    return pg.ColorMap(pos, color)


def make_diff_layer(before: XFrame, after: XFrame, config: GuiConfig | None = None) -> ImageLayer:
    """Signed (after - before) diff layer, 0-centered diverging colormap (C-06).

    Default display range is `[T]` symmetric ±max|diff| (`apps.gui.config`);
    the returned layer's `array` carries the SIGNED float diff so `probe.py`
    reports the true signed value, not the colormap-normalized render value.
    """
    before_arr = np.asarray(before.pixel, dtype=np.float32)
    after_arr = np.asarray(after.pixel, dtype=np.float32)
    diff = after_arr - before_arr
    item = pg.ImageItem(diff)
    layer = ImageLayer(name="diff", array=diff, item=item)
    lo, hi = diff_range(diff, config)
    layer.set_levels(lo, hi)
    item.setColorMap(_diverging_colormap())
    return layer


@dataclass
class MaskOverlayLayer:
    """Independent overlay layer for one `MaskFlag` bit (C-07)."""

    flag: MaskFlag
    color: tuple[int, int, int]
    array: np.ndarray  # boolean membership, same (rows, cols) shape as the base
    item: pg.ImageItem
    visible: bool = True
    opacity: float = 0.5

    def set_opacity(self, value: float) -> None:
        self.opacity = float(value)
        self.item.setOpacity(self.opacity if self.visible else 0.0)

    def set_visible(self, value: bool) -> None:
        self.visible = bool(value)
        self.item.setOpacity(self.opacity if self.visible else 0.0)


def make_mask_overlay_layers(
    masks: np.ndarray, opacity: float = 0.5
) -> dict[MaskFlag, MaskOverlayLayer]:
    """Build one independent, pixel-aligned RGBA overlay per `MaskFlag` (C-07)."""
    masks_u8 = np.asarray(masks, dtype=np.uint8)
    layers: dict[MaskFlag, MaskOverlayLayer] = {}
    for flag, color in MASK_COLORS.items():
        member = (masks_u8 & np.uint8(int(flag))) != 0
        rgba = np.zeros(member.shape + (4,), dtype=np.uint8)
        rgba[..., 0] = color[0]
        rgba[..., 1] = color[1]
        rgba[..., 2] = color[2]
        rgba[..., 3] = np.where(member, 255, 0).astype(np.uint8)
        item = pg.ImageItem(rgba)
        layer = MaskOverlayLayer(flag=flag, color=color, array=member, item=item)
        layer.set_opacity(opacity)
        layers[flag] = layer
    return layers


@dataclass
class CompareView:
    """Zoom/pan/W-L-linked before/after pair + single-key blink toggle (C-05).

    `plot_before`/`plot_after` are `pg.PlotWidget` instances the caller places
    side by side; each layer's `ImageItem` is added to its plot and the two
    ViewBoxes are linked via pyqtgraph's native axis link (no re-derivation of
    the pan/zoom transform, C-02). A bare `pg.ViewBox()` with no backing
    `QGraphicsScene` is NOT supported here -- `ViewBox.linkView` requires a
    real scene/view to wire its range-changed signals against; `PlotWidget`
    is pyqtgraph's standard scene-backed container for this.
    """

    before: ImageLayer
    after: ImageLayer
    plot_before: pg.PlotWidget
    plot_after: pg.PlotWidget
    _showing_after: bool = field(default=True, init=False, repr=False)

    def __post_init__(self) -> None:
        self.plot_before.addItem(self.before.item)
        self.plot_after.addItem(self.after.item)
        view_before = self.plot_before.getViewBox()
        view_after = self.plot_after.getViewBox()
        view_after.linkView(pg.ViewBox.XAxis, view_before)
        view_after.linkView(pg.ViewBox.YAxis, view_before)

    def toggle_blink(self) -> bool:
        """Toggle single-key blink between before/after (C-05); returns new state."""
        self._showing_after = not self._showing_after
        self.after.item.setVisible(self._showing_after)
        self.before.item.setVisible(not self._showing_after)
        return self._showing_after

    @property
    def showing_after(self) -> bool:
        return self._showing_after

    def sync_levels(self, low: float, high: float) -> None:
        """Apply the SAME W/L to both linked views (C-05 W/L linkage)."""
        self.before.set_levels(low, high)
        self.after.set_levels(low, high)
