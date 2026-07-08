"""Shared component stub: image pyramid (SWR-000-9, REQ-INFRA-STATIC-3).

@MX:NOTE: [AUTO] T0 provides the interface stub ONLY. The real algorithm is
deferred to the first consuming WP. Placed once in common/ (no duplication).
"""

from __future__ import annotations

import numpy as np


def build_pyramid(image: np.ndarray, levels: int) -> list[np.ndarray]:
    """Build a multi-resolution pyramid. Not implemented at T0."""
    raise NotImplementedError("pyramid.build_pyramid is a T0 stub (deferred to first consumer)")
