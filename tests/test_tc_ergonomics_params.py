"""XDET-TC-051 / XDET-TC-055 — module REQUIRED_PARAMS manifest (key names only).

SPEC-ERGO-001 (REQ-ERGO-PARAMS-1/2/3, REQ-ERGO-VALIDATE-2/3).

Consumer-ergonomics gap #2: each `modules/` processing module exposes the Params
KEY NAMES it requires — a `REQUIRED_PARAMS: tuple[str, ...]` constant for fixed
key sets, or a `required_params(params) -> tuple[str, ...]` function for
selector-dependent modules (denoise: method; mse: method). The manifest carries
key NAMES only — never sample/phantom numeric values (SPEC-REALDATA-001
QUARANTINE, CLAUDE.md parameter policy).
"""

from __future__ import annotations

from common.contract import Params
from modules import (
    defect,
    denoise,
    gain,
    geometry,
    grid,
    lag,
    line_noise,
    mse,
    offset,
    saturation,
    virtual_grid,
    window,
)

# The 12 processing modules under the import-linter `independence` contract.
_MODULES = [
    offset,
    gain,
    defect,
    lag,
    line_noise,
    saturation,
    geometry,
    grid,
    virtual_grid,
    denoise,
    mse,
    window,
]

# Phantom numeric values that live ONLY in tests/modules/phantoms/corrections.py
# and must NEVER surface in a module manifest (isolation boundary).
_PHANTOM_NUMERIC_VALUES = {0.5, 2.0}
_PHANTOM_NUMERIC_STRINGS = {"0.5", "2.0"}


def _manifest(mod, params: Params | None = None) -> tuple[str, ...]:
    """Resolve a module's required-params manifest in either exposed form."""
    if params is None:
        params = Params()
    if hasattr(mod, "REQUIRED_PARAMS"):
        return tuple(mod.REQUIRED_PARAMS)
    return tuple(mod.required_params(params))


# -- XDET-TC-051: manifest matches the keys the module actually reads ---------


def test_tc_051_gain_manifest_is_the_two_gain_constants():
    assert gain.REQUIRED_PARAMS == (gain.P_GAIN_MIN, gain.P_GAIN_MAX)
    assert gain.REQUIRED_PARAMS == ("gain_min", "gain_max")


def test_tc_051_denoise_required_params_tracks_required_keys_helper():
    for method in ("bm3d", "nlm"):
        params = Params({denoise.P_METHOD: method})
        got = set(denoise.required_params(params))
        expected = set(denoise._required_keys(method))
        assert got == expected, (method, got, expected)


def test_tc_051_denoise_default_method_matches_bm3d_key_set():
    # No selector supplied -> the module default method ("bm3d") key set.
    got = set(denoise.required_params(Params()))
    assert got == set(denoise._required_keys("bm3d"))


def test_tc_051_every_module_manifest_is_a_tuple_of_str():
    for mod in _MODULES:
        manifest = _manifest(mod)
        assert isinstance(manifest, tuple), mod.__name__
        assert all(isinstance(k, str) for k in manifest), mod.__name__


def test_tc_051_manifest_keys_derive_from_module_constants():
    # Non-invention spot-checks against the modules' own P_* constants.
    assert set(offset.REQUIRED_PARAMS) == {offset.P_RAW_SAT}
    assert set(defect.REQUIRED_PARAMS) == {defect.P_CMAX}
    assert set(geometry.REQUIRED_PARAMS) == {geometry.P_ACTIVATE_PX, geometry.P_DEGREE}
    assert set(virtual_grid.REQUIRED_PARAMS) == {
        virtual_grid.P_ITERATIONS,
        virtual_grid.P_DOWNSAMPLE_LEVELS,
        virtual_grid.P_GRID_RATIO_W,
        virtual_grid.P_LOWSIGNAL_THRESHOLD,
        virtual_grid.P_LOWSIGNAL_SOFTNESS,
    }
    # Pure-passthrough / all-optional modules expose an empty tuple.
    assert lag.REQUIRED_PARAMS == ()
    assert saturation.REQUIRED_PARAMS == ()
    # line_noise / grid / window: complete the derive-from-constants invariant
    # to all 12 modules (these three previously carried only the tuple-of-str
    # check, not an explicit value-match against their own P_* constants).
    assert set(line_noise.REQUIRED_PARAMS) == {
        line_noise.P_WINDOW,
        line_noise.P_CUTOFF,
        line_noise.P_CONTAM_K,
    }
    assert set(grid.REQUIRED_PARAMS) == {
        grid.P_PITCH,
        grid.P_SEARCH_LO,
        grid.P_DTH_DB,
        grid.P_DIR_MARGIN_DB,
        grid.P_HARMONIC_MAX,
        grid.P_NOTCH_FWHM_MULT,
        grid.P_MOIRE_CUTOFF,
        grid.P_MOIRE_ATTEN_CAP,
    }
    assert set(window.REQUIRED_PARAMS) == {
        window.P_LUM_MIN,
        window.P_LUM_MAX,
        window.P_PVALUE_MAX,
        window.P_COLLIM_REL,
        window.P_DIRECT_FENCE,
    }


def test_tc_051_mse_selector_covers_both_methods():
    power = set(mse.required_params(Params({mse.P_METHOD: "power_law"})))
    soft = set(mse.required_params(Params({mse.P_METHOD: "soft_clip"})))
    assert mse.P_POWER in power
    assert {mse.P_SOFTCLIP_GAIN, mse.P_SOFTCLIP_KNEE} <= soft


# -- XDET-TC-055: key names only, zero sample numeric leakage -----------------


def _all_manifest_elements() -> list[str]:
    elements: list[str] = []
    for mod in _MODULES:
        elements.extend(_manifest(mod))
    # Also fold in the selector-dependent alternate branches so every reachable
    # manifest element is covered by the isolation guard.
    for method in ("bm3d", "nlm"):
        elements.extend(denoise.required_params(Params({denoise.P_METHOD: method})))
    for method in ("power_law", "soft_clip"):
        elements.extend(mse.required_params(Params({mse.P_METHOD: method})))
    return elements


def test_tc_055_every_manifest_element_is_a_string_key_name():
    for element in _all_manifest_elements():
        assert isinstance(element, str)
        # bool is a subclass of int; both must be excluded explicitly.
        assert not isinstance(element, (bool, int, float))


def test_tc_055_no_phantom_numeric_value_in_any_manifest():
    elements = _all_manifest_elements()
    for element in elements:
        assert element not in _PHANTOM_NUMERIC_STRINGS
        assert not _looks_numeric(element)
    # Negative control: the gain KEY NAMES are present, their phantom VALUES are not.
    assert "gain_min" in elements and "gain_max" in elements
    assert not (_PHANTOM_NUMERIC_VALUES & set(_maybe_floats(elements)))


def _looks_numeric(text: str) -> bool:
    try:
        float(text)
    except (TypeError, ValueError):
        return False
    return True


def _maybe_floats(elements: list[str]) -> list[float]:
    out: list[float] = []
    for e in elements:
        try:
            out.append(float(e))
        except (TypeError, ValueError):
            continue
    return out
