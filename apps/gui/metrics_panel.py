"""Delegated metrics plotting: GUI never computes metrics itself (C-09/C-10).

@MX:ANCHOR: [AUTO] `plot_mtf`/`recompute_mtf_for_roi` are the sole metrics
entry points for this panel.
@MX:REASON: REQ-VIEW-RUN-3/4 is a HARD invariant -- every plotted array MUST be
the direct return value of a `metrics/` engine call
(`metrics.mtf.compute_mtf`), never a value computed inline in `apps/gui`; the
array-identity assertion in `tests/apps/gui/test_tc_viewer_metrics.py` is what
makes "GUI computes 0 metrics" a checked fact rather than a convention.

ROI round-trip (C-10): `RoiBounds` is the exact boundary reported to the user;
`recompute_mtf_for_roi` re-slices the ORIGINAL frame with those same bounds and
re-invokes the engine, so the same boundary fed twice yields identical results.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg

from common.contract import Params
from common.xframe import XFrame, new_frame
from metrics.mtf import compute_mtf
from metrics.result import MetricResult


@dataclass(frozen=True)
class RoiBounds:
    """The exact ROI boundary used for a metric computation (C-10, must be reported)."""

    top: int
    left: int
    height: int
    width: int

    def slice_frame(self, frame: XFrame) -> XFrame:
        """Return a fresh XFrame restricted to this ROI (the metrics-engine input)."""
        pixel = np.asarray(frame.pixel)[
            self.top : self.top + self.height, self.left : self.left + self.width
        ]
        return new_frame(pixel)


def roi_bounds_from_rect_roi(roi: pg.RectROI, frame_shape: tuple[int, int]) -> RoiBounds:
    """Read the exact (top, left, height, width) an on-screen `pg.RectROI` covers.

    Clamps to the frame bounds so a partially-off-frame ROI still yields a
    valid, reportable boundary (C-10).
    """
    pos = roi.pos()
    size = roi.size()
    left = int(round(pos.x()))
    top = int(round(pos.y()))
    width = int(round(size.x()))
    height = int(round(size.y()))
    top = max(0, min(top, frame_shape[0] - 1))
    left = max(0, min(left, frame_shape[1] - 1))
    height = max(1, min(height, frame_shape[0] - top))
    width = max(1, min(width, frame_shape[1] - left))
    return RoiBounds(top=top, left=left, height=height, width=width)


def plot_mtf(plot_widget: pg.PlotWidget, frame: XFrame, params: Params) -> MetricResult:
    """Invoke `metrics.mtf.compute_mtf` and plot ITS output arrays only (C-09).

    Returns the full `MetricResult` so callers/tests can assert the plotted
    curve equals `result.get("frequencies_lpmm")`/`result.get("mtf")` exactly.
    """
    result = compute_mtf(frame, params)
    plot_widget.clear()
    plot_widget.plot(result.get("frequencies_lpmm"), result.get("mtf"))
    return result


def recompute_mtf_for_roi(frame: XFrame, params: Params, roi_bounds: RoiBounds) -> MetricResult:
    """Re-invoke the metrics engine on the ROI sub-frame (C-10 round-trip path).

    `frame` is the ORIGINAL (un-cropped) frame; `roi_bounds` re-derives the
    identical sub-array the first computation used, so the recomputed result
    is bit-identical when fed the same boundary (deterministic engine, C-16
    determinism inheritance).
    """
    sub_frame = roi_bounds.slice_frame(frame)
    return compute_mtf(sub_frame, params)
