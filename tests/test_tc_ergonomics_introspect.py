"""XDET-TC-052 — Params lookup/validation surface (additive, backward-compatible).

SPEC-ERGO-001 (REQ-ERGO-INTROSPECT-1/2/3, REQ-ERGO-VALIDATE-4).

Consumer-ergonomics gap #3: `common.contract.Params` gains an additive
`validate(required)` (collects ALL missing keys, then raises), a non-raising
`missing(required) -> tuple[str, ...]`, and `keys()` to list present keys. The
existing `.get()`/`.hash()`/`.values` behaviour and the frozen/MappingProxy
immutability are unchanged. The manifest (gap #2) plugs straight into `validate`.
"""

from __future__ import annotations

import pytest

from common.contract import Params
from modules import gain


def test_tc_052_validate_lists_all_missing_keys_not_just_first():
    params = Params({"present": 1})
    with pytest.raises(ValueError) as exc:
        params.validate(("alpha", "present", "beta"))
    message = str(exc.value)
    # Every missing key is named (all-missing collection, not first-fail).
    assert "alpha" in message
    assert "beta" in message
    assert "present" not in message


def test_tc_052_validate_passes_when_all_present():
    params = Params({"a": 1, "b": 2, "c": 3})
    # No exception, returns None.
    assert params.validate(("a", "b", "c")) is None


def test_tc_052_missing_returns_absent_keys_without_raising():
    params = Params({"a": 1})
    assert params.missing(("a", "b", "c")) == ("b", "c")
    assert params.missing(("a",)) == ()


def test_tc_052_keys_lists_present_keys():
    params = Params({"a": 1, "b": 2})
    assert set(params.keys()) == {"a", "b"}


def test_tc_052_existing_surface_unchanged():
    params = Params({"gain_min": 0.5, "gain_max": 2.0})
    # .get() behaviour preserved.
    assert params.get("gain_min") == 0.5
    assert params.get("absent", "default") == "default"
    # .hash() still deterministic and present.
    assert isinstance(params.hash(), str)
    assert params.hash() == Params({"gain_min": 0.5, "gain_max": 2.0}).hash()
    # .values is still an immutable MappingProxy (frozen).
    with pytest.raises(TypeError):
        params.values["gain_min"] = 9.9


def test_tc_052_manifest_and_validate_compose():
    # The gap #2 manifest connects to the gap #3 validation surface.
    with pytest.raises(ValueError) as exc:
        Params().validate(gain.REQUIRED_PARAMS)
    message = str(exc.value)
    assert "gain_min" in message and "gain_max" in message
    # A complete Params passes the same manifest.
    assert Params({"gain_min": 0.4, "gain_max": 1.8}).validate(gain.REQUIRED_PARAMS) is None
