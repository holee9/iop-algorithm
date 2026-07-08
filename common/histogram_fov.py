"""Shared component stub: histogram / field-of-view analysis
(SWR-000-9, REQ-INFRA-STATIC-3).

@MX:NOTE: [AUTO] T0 interface stub only; algorithm deferred to first consumer.
"""

from __future__ import annotations

import numpy as np


def compute_histogram(image: np.ndarray, bins: int) -> np.ndarray:
    """Compute an intensity histogram. Not implemented at T0."""
    raise NotImplementedError("histogram_fov.compute_histogram is a T0 stub")


def detect_fov(image: np.ndarray) -> np.ndarray:
    """Detect the field-of-view (collimation) mask. Not implemented at T0."""
    raise NotImplementedError("histogram_fov.detect_fov is a T0 stub")
