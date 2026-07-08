"""Shared pytest fixtures for XDET T0 framework tests."""

from __future__ import annotations

import numpy as np
import pytest

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.contract import Params
from common.xframe import MaskFlag, NoiseModel, new_frame

# Small synthetic frame keeps the framework self-test fast and deterministic.
FRAME_SHAPE = (4, 4)


@pytest.fixture
def synthetic_frame():
    """A small deterministic input XFrame with a non-trivial mask stack."""
    pixel = np.arange(16, dtype=np.float32).reshape(FRAME_SHAPE)
    masks = np.zeros(FRAME_SHAPE, dtype=np.uint8)
    masks[0, 0] = int(MaskFlag.DEFECT)
    masks[1, 1] = int(MaskFlag.SATURATION | MaskFlag.INTERPOLATION)
    return new_frame(pixel, masks, NoiseModel(alpha=0.7, sigma=1.3))


@pytest.fixture
def validation_frame():
    """A frame with validation mode active (float64 parallel buffer present)."""
    pixel = np.arange(16, dtype=np.float32).reshape(FRAME_SHAPE)
    return new_frame(pixel, validation_mode=True)


@pytest.fixture
def calib():
    """A valid CalibSet matching FRAME_SHAPE."""
    return CalibSet(
        panel_id="PANEL-A",
        resolution=FRAME_SHAPE,
        valid_from="2026-01-01",
        valid_until="2027-01-01",
        kind=CalibKind.OFFSET,
        data={"map": np.zeros(FRAME_SHAPE, dtype=np.float32)},
        provenance=CalibProvenance(created_at="2026-07-08", source="synthetic"),
    )


@pytest.fixture
def params():
    return Params(values={"threshold": 6, "mode": "reference"})
