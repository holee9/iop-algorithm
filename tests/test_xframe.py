"""XFrame data-contract tests (REQ-INFRA-DATA)."""

from __future__ import annotations

import numpy as np
import pytest

from common.xframe import (
    HistoryEntry,
    MaskFlag,
    NoiseModel,
    XFrame,
    hash_params,
    new_frame,
)


def test_pixel_defaults_to_float32(synthetic_frame):
    assert synthetic_frame.pixel.dtype == np.float32


def test_input_pixel_buffer_is_readonly(synthetic_frame):
    """DATA-6: pixel buffer is read-only; in-place writes raise."""
    with pytest.raises(ValueError):
        synthetic_frame.pixel[0, 0] = 1.0


def test_record_history_is_append_only_and_pure(synthetic_frame):
    entry = HistoryEntry("m", "1.0.0", "abc", "calib-1")
    out = synthetic_frame.record_history(entry)
    assert out is not synthetic_frame
    assert out.history == (entry,)
    assert synthetic_frame.history == ()  # original untouched


def test_history_entry_is_deterministic():
    p = {"b": 2, "a": 1}
    # Insertion order does not change the hash (sorted-key canonicalization).
    assert hash_params(p) == hash_params({"a": 1, "b": 2})


def test_mask_flags_compose():
    combined = MaskFlag.SATURATION | MaskFlag.INTERPOLATION
    assert combined & MaskFlag.SATURATION
    assert combined & MaskFlag.INTERPOLATION
    assert not (combined & MaskFlag.DEFECT)


def test_validation_mode_carries_float64_parallel_buffer(validation_frame):
    """DATA-1 / CI-3b: validation frame holds a float64 parallel buffer."""
    assert validation_frame.validation_mode is True
    assert validation_frame.pixel_f64 is not None
    assert validation_frame.pixel_f64.dtype == np.float64
    # Default single path has no float64 buffer.
    plain = new_frame(np.zeros((2, 2), dtype=np.float32))
    assert plain.pixel_f64 is None


def test_shape_mismatch_rejected():
    with pytest.raises(ValueError):
        XFrame(pixel=np.zeros((2, 2)), masks=np.zeros((3, 3), dtype=np.uint8))


def test_equals_full_structural_comparison(synthetic_frame):
    same = new_frame(
        synthetic_frame.pixel, synthetic_frame.masks, synthetic_frame.noise
    )
    assert synthetic_frame.equals(same)
    diff = synthetic_frame.with_pixel(synthetic_frame.pixel + 1)
    assert not synthetic_frame.equals(diff)
