"""Shared component stub: robust statistics (SWR-000-9, REQ-INFRA-STATIC-3).

@MX:NOTE: [AUTO] T0 interface stub only; algorithm deferred to first consumer.
"""

from __future__ import annotations

import numpy as np


def robust_mean(values: np.ndarray) -> float:
    """Outlier-resistant central tendency. Not implemented at T0."""
    raise NotImplementedError("robust_stats.robust_mean is a T0 stub")


def robust_std(values: np.ndarray) -> float:
    """Outlier-resistant dispersion (e.g. MAD-based). Not implemented at T0."""
    raise NotImplementedError("robust_stats.robust_std is a T0 stub")
