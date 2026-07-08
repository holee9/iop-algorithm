"""Shared component stub: FFT / power spectral density
(SWR-000-9, REQ-INFRA-STATIC-3).

@MX:NOTE: [AUTO] T0 interface stub only; algorithm deferred to first consumer
(e.g. NPS/PSD at T1, grid suppression at T7).
"""

from __future__ import annotations

import numpy as np


def compute_psd(image: np.ndarray) -> np.ndarray:
    """Compute the 2D power spectral density. Not implemented at T0."""
    raise NotImplementedError("fft_psd.compute_psd is a T0 stub")
