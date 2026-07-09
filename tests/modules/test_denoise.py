"""Denoise module contract + behaviour scenarios (SPEC-DENOISE-001).

Covers Scenario 3 (GAT + clamp), 4 (noise-model refusal), 5 (no asymptotic
inverse path), 6 (BM3D core params injected + sigma wiring), 7 (mask exclusion +
flag immutability), 9 (NLM alt path), 11 (module contract: immutability, history,
resolved noise recorded, layering), 12 (entry-gate refusal), and EC-3/EC-4/EC-6.

The XDET-TC-010/011 release gates live in test_tc_denoise.py.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest

from common.calibset import CalibKind, CalibProvenance, CalibSet
from common.contract import Params, check_process_contract
from common.xframe import MaskFlag, NoiseModel, new_frame
from modules import denoise
from pipeline.orchestrator import (
    CalibrationError,
    PipelineDefinition,
    run_pipeline,
)
from tests.modules.phantoms.denoise_syn import (
    ALPHA,
    SIGMA,
    denoise_params,
    make_uniform_field,
    noise_calib,
)

SHAPE = (48, 48)


def _fast_params(**overrides):
    # Small LUT keeps the contract suite quick; the round-trip accuracy gate uses
    # its own high-resolution LUT.
    base = dict(
        denoise_inv_lut_nodes=512,
        denoise_inv_lut_gh_nodes=12,
        denoise_inv_lut_lambda_max=3000.0,
    )
    base.update(overrides)
    return denoise_params(**base)


def _frame(seed=3, masks=None):
    _, noisy = make_uniform_field(SHAPE, level=400.0, seed=seed)
    return new_frame(noisy.astype(np.float32), masks)


# -- Scenario 3 + EC-6: GAT forward + domain clamp ----------------------------


def test_scenario3_gat_forward_and_clamp():
    z = np.array([[400.0, 500.0], [600.0, 700.0]], dtype=np.float64)
    f, clamp_rate = denoise._gat_forward(z, ALPHA, SIGMA)
    # Reference GAT: (2/alpha) sqrt(alpha z + 3/8 alpha^2 + sigma^2).
    expected = (2.0 / ALPHA) * np.sqrt(
        ALPHA * z + (3.0 / 8.0) * ALPHA**2 + SIGMA**2
    )
    assert np.allclose(f, expected)
    assert clamp_rate == 0.0


def test_ec6_negative_radicand_clamped_no_nan():
    # Extreme negative residual -> radicand < 0 -> clamp to 0, no NaN.
    z = np.array([[-1e6, 400.0]], dtype=np.float64)
    f, clamp_rate = denoise._gat_forward(z, ALPHA, SIGMA)
    assert np.isfinite(f).all()
    assert f[0, 0] == 0.0
    assert clamp_rate == 0.5


# -- Scenario 4: noise-model absent / degenerate -> refusal -------------------


def test_scenario4_missing_noise_payload_refused():
    calib = CalibSet(
        "PANEL-A", SHAPE, "2026-01-01", "2027-01-01", CalibKind.NOISE, data={}
    )
    with pytest.raises(denoise.DenoiseError, match="missing"):
        denoise.process(_frame(), calib, _fast_params())


def test_scenario4_degenerate_alpha_refused():
    bad = noise_calib(SHAPE, alpha=0.0, sigma=1.0)
    with pytest.raises(denoise.DenoiseError, match="degenerate"):
        denoise.process(_frame(), bad, _fast_params())


def test_scenario4_xframe_default_noise_not_used():
    """The XFrame default NoiseModel(0, 0) is never a fallback source."""
    frame = new_frame(np.full(SHAPE, 400.0, np.float32))  # noise defaults to (0,0)
    empty = CalibSet(
        "PANEL-A", SHAPE, "2026-01-01", "2027-01-01", CalibKind.NOISE, data={}
    )
    with pytest.raises(denoise.DenoiseError):
        denoise.process(frame, empty, _fast_params())


# -- Scenario 5: exact LUT inverse is the only path (no asymptotic) -----------


def test_scenario5_no_asymptotic_inverse_path():
    src = Path(inspect.getfile(denoise)).read_text(encoding="utf-8")
    # The prohibited algebraic inverse ((alpha*f/2)^2 solved for z) must not exist
    # as a module code path (REQ-DENOISE-INV-2). The only inverse is the LUT.
    assert "asymptotic" not in src.lower() or "PROHIBITED" in src
    assert not hasattr(denoise, "asymptotic_inverse")
    assert hasattr(denoise, "_gat_inverse")
    # The inverse is interpolation over the monotone forward-mean LUT.
    inv_src = inspect.getsource(denoise._gat_inverse)
    assert "interp" in inv_src


def test_inverse_lut_is_monotone_and_deterministic():
    m1, lam1 = denoise._build_inverse_lut(ALPHA, SIGMA, 300.0, 512, 12)
    m2, lam2 = denoise._build_inverse_lut(ALPHA, SIGMA, 300.0, 512, 12)
    assert np.array_equal(m1, m2) and np.array_equal(lam1, lam2)  # deterministic
    assert np.all(np.diff(m1) > 0)  # strictly increasing -> invertible


# -- Scenario 6: BM3D core params injected (no hardcode) + sigma wiring --------


def test_scenario6_bm3d_params_are_injected_not_hardcoded():
    # Removing any required BM3D original parameter must raise — proving the
    # module reads them from Params rather than embedding literals.
    for key in (
        "denoise_bm3d_block",
        "denoise_bm3d_lambda3d",
        "denoise_bm3d_kaiser_beta",
        "denoise_bm3d_search_window",
    ):
        vals = dict(_fast_params().values)
        del vals[key]
        with pytest.raises(denoise.DenoiseError, match="missing required"):
            denoise.process(_frame(), noise_calib(SHAPE), Params(values=vals))


def test_scenario6_sigma_bm3d_scales_with_ks():
    # sigma_BM3D = 1 * k_s: different presets give different denoised outputs, and
    # the applied k_s is recorded in the history diagnostics.
    frame, calib = _frame(), noise_calib(SHAPE)
    out06 = denoise.process(frame, calib, _fast_params(k_s=0.6))
    out10 = denoise.process(frame, calib, _fast_params(k_s=1.0))
    assert out06.history[-1].extra["k_s"] == 0.6
    assert out10.history[-1].extra["k_s"] == 1.0
    assert not np.allclose(out06.pixel, out10.pixel)


def test_no_new_dependency_stdlib_numpy_scipy_only():
    src = Path(inspect.getfile(denoise)).read_text(encoding="utf-8")
    assert "import bm3d" not in src and "from bm3d" not in src


# -- Scenario 7 + EC-3: mask exclusion + flag immutability --------------------


def test_scenario7_saturation_value_preserved_flags_unchanged():
    masks = np.zeros(SHAPE, np.uint8)
    masks[5, 5] = int(MaskFlag.SATURATION)
    masks[6, 6] = int(MaskFlag.SATURATION_BAND)
    masks[7, 7] = int(MaskFlag.DEFECT)
    masks[8, 8] = int(MaskFlag.INTERPOLATION)
    frame = _frame(masks=masks)
    out = denoise.process(frame, noise_calib(SHAPE), _fast_params())
    # Saturation / band values preserved unchanged (no restoration).
    assert out.pixel[5, 5] == frame.pixel[5, 5]
    assert out.pixel[6, 6] == frame.pixel[6, 6]
    # No mask flag set or cleared (mask substrate is upstream-owned).
    assert np.array_equal(out.masks, frame.masks)


def test_ec3_fully_masked_region_passes_without_error():
    masks = np.full(SHAPE, int(MaskFlag.SATURATION), np.uint8)  # everything masked
    frame = _frame(masks=masks)
    out = denoise.process(frame, noise_calib(SHAPE), _fast_params())
    # Fully-masked (saturation) region: values preserved, no NaN / divergence.
    assert np.isfinite(out.pixel).all()
    assert np.allclose(out.pixel, frame.pixel)


# -- Scenario 9: NLM alternative path -----------------------------------------


def test_scenario9_nlm_path_selected_by_params():
    frame, calib = _frame(), noise_calib(SHAPE)
    out = denoise.process(frame, calib, _fast_params(method="nlm"))
    assert out.history[-1].extra["method"] == "nlm"
    # NLM still reduces noise on a uniform field (SNR improves).
    assert out.pixel.std() < frame.pixel.std()


def test_unknown_method_rejected():
    with pytest.raises(denoise.DenoiseError, match="unknown method"):
        denoise.process(_frame(), noise_calib(SHAPE), _fast_params(method="wavelet"))


# -- Scenario 11 + EC-4: module contract --------------------------------------


def test_scenario11_process_contract_signature():
    assert check_process_contract(denoise) == ()


def test_scenario11_input_immutable_and_history_recorded():
    frame, calib = _frame(), noise_calib(SHAPE)
    before = np.array(frame.pixel, copy=True)
    out = denoise.process(frame, calib, _fast_params())
    assert np.array_equal(frame.pixel, before)  # input untouched (DATA-6)
    assert frame.history == ()
    entry = out.history[-1]
    assert entry.module_name == "denoise"
    assert set(entry.extra) >= {"k_s", "clamp_rate", "resolved_alpha", "resolved_sigma"}


def test_scenario11_resolved_noise_written_to_output():
    out = denoise.process(_frame(), noise_calib(SHAPE, alpha=2.0, sigma=3.0), _fast_params())
    assert out.noise == NoiseModel(alpha=2.0, sigma=3.0)


def test_ec4_layering_no_metrics_or_pipeline_import():
    src = Path(inspect.getfile(denoise)).read_text(encoding="utf-8")
    assert "import metrics" not in src and "from metrics" not in src
    assert "import pipeline" not in src and "from pipeline" not in src


# -- Scenario 12: orchestrator entry-gate refusal -----------------------------


def _registry():
    return {"denoise": denoise.process}


def test_scenario12_missing_calibset_refused():
    frame = _frame()
    with pytest.raises(CalibrationError, match="missing"):
        run_pipeline(frame, PipelineDefinition(("denoise",)), _registry(), calib_map={})


def test_scenario12_wrong_kind_refused():
    frame = _frame()
    wrong = CalibSet(
        "PANEL-A", SHAPE, "2026-01-01", "2027-01-01", CalibKind.OFFSET, data={}
    )
    with pytest.raises(CalibrationError, match="kind"):
        run_pipeline(
            frame, PipelineDefinition(("denoise",)), _registry(), {"denoise": wrong}
        )


def test_scenario12_denoise_runs_via_orchestrator():
    frame = _frame()
    out = run_pipeline(
        frame,
        PipelineDefinition(("denoise",)),
        _registry(),
        {"denoise": noise_calib(SHAPE)},
        {"denoise": _fast_params()},
    )
    assert out.history[-1].module_name == "denoise"
