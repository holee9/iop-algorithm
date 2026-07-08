"""Module contract, immutability enforcement, and equivalence-hook tests
(REQ-INFRA-CONTRACT, DATA-6, CI-4)."""

from __future__ import annotations

import numpy as np
import pytest

from common.contract import (
    Params,
    ProcessModule,
    StatefulModule,
    check_process_contract,
    run_harness,
)
from common.equivalence import diff_frames
from common.xframe import new_frame
from tests.fixtures import passthrough
from tests.fixtures.violations import MutatingModule


def test_passthrough_satisfies_process_protocol():
    """CONTRACT-1: canonical process signature is accepted."""
    assert check_process_contract(passthrough) == ()


def test_stateful_protocol_interface_exists():
    """Scenario 4: the state-serialization contract EXISTS structurally.

    Runtime round-trip through a stateful module (lag) is deferred to T4.
    """
    assert hasattr(StatefulModule, "serialize_state")
    assert hasattr(StatefulModule, "load_state")
    # ProcessModule is the primary runtime-checkable structural contract.
    assert issubclass(ProcessModule, object)


def test_mutating_module_blocked_by_immutability(synthetic_frame, calib, params):
    """DATA-6: an attempt to mutate the input frame raises (buffer read-only)."""
    with pytest.raises(ValueError):
        MutatingModule().process(synthetic_frame, calib, params)


def test_params_hash_is_deterministic():
    a = Params(values={"x": 1, "y": 2})
    b = Params(values={"y": 2, "x": 1})
    assert a.hash() == b.hash()


def test_equivalence_hook_structural_diff():
    """CI-4: diff hook reports per-field equality (no numeric threshold at T0)."""
    base = new_frame(np.zeros((3, 3), dtype=np.float32))
    same = new_frame(np.zeros((3, 3), dtype=np.float32))
    diff = diff_frames(base, same)
    assert diff.structurally_equal
    assert diff.max_pixel_abs_diff == 0.0

    other = new_frame(np.ones((3, 3), dtype=np.float32))
    d2 = diff_frames(base, other)
    assert not d2.structurally_equal
    assert d2.max_pixel_abs_diff == 1.0
