"""End-to-end smoke test exercising the real T0-T10 production code paths.

This drives the ACTUAL production pipeline (real orchestrator + real modules +
real CalibSets, no mocks/stubs) through a meaningful cross-subsystem slice of
XDET, plus the T1 MTF engine, the T9 streaming SNRn accumulator, the T10 tier
gate, and the T10 equivalence diff. Its job is to catch INTEGRATION regressions
that the per-module suites cannot -- e.g. one module changing its output
contract (mask stack, history chain, dtype) and silently breaking a downstream
consumer, or a fixture/orchestrator drift that only shows up when the whole
chain runs together.

It is NOT a replacement for the focused per-module / per-metric test suites
under tests/modules, tests/metrics and tests/pipeline -- those own the exhaustive
correctness, edge-case and contract coverage. This file is a single, fast,
deterministic "does the whole thing still compose" tripwire. Every numeric
expectation is a physically-justified deterministic assertion (RNG is seeded)
with a generous tolerance band, never a reproduce-these-exact-decimals lock.

Chapters (one focused test per subsystem so a failure pinpoints the break):
  1. Correction chain recovers a known scene (offset/gain/defect/line_noise/
     saturation/geometry over the real orchestrator).
  2. Correction chain records a full provenance history (incl. inactive geometry).
  3. Correction chain flags the injected defects in the mask stack.
  4. T1 MTF engine reproduces the analytic Gaussian-blur MTF.
  5. T9 streaming SNRn follows the sqrt(N) dose-integration scaling law.
  6. T10 tier gate selects the highest supported execution tier.
  7. T10 equivalence diff is reflexive and detects a pixel perturbation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from common.equivalence import diff_frames
from common.mask_ops import DefectMorphology
from common.xframe import MaskFlag, XFrame, new_frame
from metrics.mtf import compute_mtf, mtf_value_at
from metrics.ndt import SNRnAccumulator
from modules import defect, gain, geometry, line_noise, offset, saturation
from pipeline.orchestrator import PipelineDefinition, run_pipeline
from pipeline.tier import Tier, decide_tier

# Reuse the existing phantom / CalibSet / Params builders -- no hand-rolled
# duplicate calibration or params construction where a helper already exists.
from tests.metrics.phantoms import generators as gen
from tests.metrics.phantoms.params import TOLERANCES, make_params
from tests.modules.phantoms.corrections import (
    corr_params,
    defect_calib,
    gain_calib,
    offset_calib,
)
from tests.modules.phantoms.linesat import (
    geometry_calib,
    line_noise_calib,
    lnsg_params,
    saturation_calib,
)
from tests.pipeline.tier_fixtures import cap_tier2, tier_policy_params

# -- Shared correction-scene constants ----------------------------------------

_SHAPE = (256, 256)
_OFFSET_SCALAR = 180.0  # additive dark offset injected into the raw frame
_GAIN_SCALAR = 1.15  # multiplicative gain injected into the raw frame
_SEED = 42  # deterministic RNG for the row-banding (line noise)
_PANEL_ID = "PANEL-A"
# A subsequence of CANONICAL_ORDER (offset -> ... -> geometry); the orchestrator
# is the sole order authority, so this is the whole WP1/WP3/WP4 slice in order.
_CORRECTION_STAGES = (
    "offset",
    "gain",
    "defect",
    "line_noise",
    "saturation",
    "geometry",
)


@dataclass(frozen=True)
class _CorrectionScene:
    """A synthesized raw frame plus the ground-truth scene it should recover to."""

    frame: XFrame
    true_scene: np.ndarray  # float64 scene the corrected output must reproduce
    morph: np.ndarray  # int8 DefectMorphology class map (defect CalibSet payload)


def _make_correction_scene() -> _CorrectionScene:
    """Synthesize a raw frame with known offset/gain/defect/line-noise distortion.

    The forward model is raw = true_scene / gain + offset, with dead pixels
    zeroed at planted single/line/cluster morphologies and a per-row Gaussian
    banding (line noise) added on top. The correction chain must invert all of
    this and land back on ``true_scene`` (bar small residual edge effects).
    """
    r, c = np.mgrid[0 : _SHAPE[0], 0 : _SHAPE[1]].astype(np.float64)
    true_scene = 3000.0 + 400.0 * np.exp(
        -((r - 128) ** 2 + (c - 128) ** 2) / (2 * 60.0**2)
    )
    true_scene += 15.0 * np.sin(c / 6.0)

    raw = true_scene / _GAIN_SCALAR + _OFFSET_SCALAR

    # Planted E2597 morphologies; the raw pixels are dead (zeroed) at each.
    morph = np.full(_SHAPE, DefectMorphology.NORMAL, dtype=np.int8)
    morph[50, 50] = DefectMorphology.SINGLE
    morph[100, 60:70] = DefectMorphology.LINE
    morph[180:183, 180:183] = DefectMorphology.CLUSTER
    raw[50, 50] = 0.0
    raw[100, 60:70] = 0.0
    raw[180:183, 180:183] = 0.0

    # Deterministic per-row banding removed by the SWR-503 no-reference path.
    rng = np.random.default_rng(_SEED)
    row_bias = rng.normal(0.0, 25.0, size=_SHAPE[0])
    raw += row_bias[:, None]

    return _CorrectionScene(
        frame=new_frame(raw.astype(np.float32)),
        true_scene=true_scene,
        morph=morph,
    )


@pytest.fixture(scope="module")
def correction_output() -> tuple[_CorrectionScene, XFrame]:
    """Run the real correction pipeline ONCE; the frozen output is shared.

    Module-scoped so the (deliberately slow, accuracy-first) golden-model chain
    is executed a single time across the three correction-chapter tests and the
    equivalence test. XFrame buffers are read-only, so sharing the output across
    tests is safe -- no test can mutate it out from under another.
    """
    scene = _make_correction_scene()
    registry = {
        "offset": offset.process,
        "gain": gain.process,
        "defect": defect.process,
        "line_noise": line_noise.process,
        "saturation": saturation.process,
        "geometry": geometry.process,
    }
    calib_map = {
        "offset": offset_calib(np.full(_SHAPE, _OFFSET_SCALAR)),
        "gain": gain_calib(np.full(_SHAPE, _GAIN_SCALAR)),
        "defect": defect_calib(scene.morph),
        "line_noise": line_noise_calib(_SHAPE),  # SWR-503 no-reference path
        "saturation": saturation_calib(_SHAPE),
        # residual 0.05 px < EV-106 min (1.0) -> geometry stays inactive.
        "geometry": geometry_calib(_SHAPE, [0.0], [0.0], residual=0.05),
    }
    corr = corr_params()
    lnsg = lnsg_params()
    params_map = {
        "offset": corr,
        "gain": corr,
        "defect": corr,
        "line_noise": lnsg,
        "saturation": lnsg,
        "geometry": lnsg,
    }
    out = run_pipeline(
        scene.frame,
        PipelineDefinition(_CORRECTION_STAGES),
        registry,
        calib_map,
        params_map,
        panel_id=_PANEL_ID,
    )
    return scene, out


# -- Chapter 1: correction chain recovers a known scene -----------------------


def test_correction_chain_recovers_known_scene(correction_output):
    scene, out = correction_output
    recovered = np.asarray(out.pixel, dtype=np.float64)

    assert out.pixel.shape == _SHAPE
    # The global level is recovered: offset removed, gain applied, the line-noise
    # DC preserved by the high-pass banding removal.
    assert recovered.mean() == pytest.approx(scene.true_scene.mean(), abs=20.0)
    # Per-pixel recovery: only small residual line-noise / defect-edge effects
    # survive. An un-inverted stage would leave a difference in the hundreds
    # (offset ~180, gain ~15%, zeroed defects), far above this ceiling.
    max_abs = float(np.max(np.abs(recovered - scene.true_scene)))
    assert max_abs < 150.0


# -- Chapter 2: full provenance history (IEC 62304 tracking) ------------------


def test_correction_chain_records_full_provenance_history(correction_output):
    _, out = correction_output

    # One append-only history entry per executed stage, in canonical order.
    assert [h.module_name for h in out.history] == list(_CORRECTION_STAGES)
    for entry in out.history:
        assert entry.module_version  # non-empty version string
        assert entry.params_hash  # deterministic params hash recorded

    # Geometry ran last and is an inactive identity passthrough (residual below
    # EV-106 min); it must still record itself with an explicit active=false.
    geometry_entry = out.history[-1]
    assert geometry_entry.module_name == "geometry"
    assert geometry_entry.extra is not None
    assert geometry_entry.extra["active"] == "false"


# -- Chapter 3: injected defects flagged in the mask stack --------------------


def test_correction_chain_flags_injected_defects(correction_output):
    _, out = correction_output
    masks = np.asarray(out.masks)

    # The defect stage marks the dead pixels DEFECT and their repairs
    # INTERPOLATION; both flags must be present after the full chain.
    assert np.any((masks & int(MaskFlag.DEFECT)) != 0)
    assert np.any((masks & int(MaskFlag.INTERPOLATION)) != 0)


# -- Chapter 4: T1 MTF engine reproduces the analytic Gaussian-blur MTF -------


def test_mtf_engine_matches_analytic_gaussian_mtf():
    # A slanted edge blurred by a known Gaussian -> the presampled MTF equals the
    # pure Gaussian MTF (the phantom exposes the analytic value).
    phantom = gen.make_slanted_edge(shape=(96, 96), angle_deg=2.2, sigma_px=0.6)
    result = compute_mtf(phantom.frame, make_params(), calibset_id="DEMO-CS")

    # The automatic edge-angle estimator recovers the injected tilt.
    assert result.get("edge_angle_deg") == pytest.approx(2.2, abs=0.5)
    # Normalized presampled MTF is 1.0 at DC.
    assert mtf_value_at(result, 0.0) == pytest.approx(1.0, abs=1e-6)

    nyquist = 1.0 / (2.0 * phantom.pitch_mm)
    mtf_at_nyq = mtf_value_at(result, nyquist)
    # A real, physically meaningful value (~0.17), matched to the phantom's own
    # analytic Gaussian MTF within the externalized Nyquist tolerance.
    assert mtf_at_nyq == pytest.approx(
        phantom.analytic_mtf(nyquist), abs=TOLERANCES["mtf_nyquist_abs"]
    )


# -- Chapter 5: T9 streaming SNRn follows the sqrt(N) dose-integration law -----


def test_streaming_snrn_follows_sqrt_dose_scaling():
    # Independent noisy frames streamed one at a time: averaging k frames drops
    # the temporal noise as 1/sqrt(k), so the running SNRn grows as sqrt(k).
    seq = gen.make_snrn_sequence()
    acc = SNRnAccumulator(seq.roi, seq.srb_um, make_params())
    for frame in seq.frames:
        acc.update(frame)

    log = acc.shot_log
    assert len(log) == seq.n_frames

    tol = TOLERANCES["snrn_progression_rel"]
    snrn1 = log[0].snrn
    for k in (4, 9, 16):
        # The dose-integration scaling law: SNRn(k) / SNRn(1) == sqrt(k).
        ratio = log[k - 1].snrn / snrn1
        assert ratio == pytest.approx(np.sqrt(k), rel=tol)
        # And the absolute running SNRn tracks the analytic known progression.
        assert log[k - 1].snrn == pytest.approx(seq.known_snrn(k), rel=tol)

    # Monotone growth as frames accumulate (noise averages down).
    snrns = [e.snrn for e in log]
    assert snrns[-1] > snrns[0]


# -- Chapter 6: T10 tier gate selects the highest supported tier --------------


def test_tier_decision_selects_highest_supported_tier():
    # A Tier 2-capable descriptor against the injected P2-placeholder policy
    # (both reused from tier_fixtures) satisfies both rules; the highest wins.
    decision = decide_tier(cap_tier2(), tier_policy_params())
    assert decision.tier is Tier.TIER2
    assert decision.detected_tier is Tier.TIER2
    assert decision.forced is False


# -- Chapter 7: T10 equivalence diff is reflexive and detects perturbation -----


def test_equivalence_diff_is_reflexive_and_detects_perturbation(correction_output):
    _, out = correction_output

    # Positive control: a frame is structurally identical to itself.
    same = diff_frames(out, out)
    assert same.structurally_equal is True
    assert same.max_pixel_abs_diff == 0.0

    # Negative control: a uniform +5.0 pixel shift MUST be detected, and the
    # reported magnitude must equal the injected delta (not merely be nonzero).
    perturbed = out.with_pixel(np.asarray(out.pixel) + 5.0)
    changed = diff_frames(out, perturbed)
    assert changed.structurally_equal is False
    assert changed.max_pixel_abs_diff == pytest.approx(5.0, abs=1e-2)
