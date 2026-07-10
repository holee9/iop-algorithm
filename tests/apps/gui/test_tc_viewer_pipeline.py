"""Pipeline comparison viewer -- Phase 2 (REQ-VIEW-RUN-2/7/8, REQ-VIEW-ARCH-7, XDET-TC-035).

Headless (`QT_QPA_PLATFORM=offscreen`), logic-level only (C-15) -- no pixel-grab
visual assertions. Uses an injected passthrough registry/calib for the
stage-mechanics and determinism tests (REQ-VIEW-RUN-2/C-16) so they do not
depend on real per-module calibration payloads (offset/gain/etc. require a
measured O_map/G_map that `make_synthetic_calibset`'s empty payload does not
provide); `build_pipeline_registry`/`build_synthetic_calib_map` themselves are
checked structurally against the real registry separately.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("qtpy")

from common.xframe import HistoryEntry, new_frame
from pipeline.orchestrator import CANONICAL_ORDER, PipelineDefinition
from tests.fixtures import passthrough

from apps.gui.export import export_frame, import_frame
from apps.gui.io_panel import DataWriteRejectedError
from apps.gui.pipeline_panel import (
    SELECTABLE_STAGES,
    build_pipeline_registry,
    build_synthetic_calib_map,
    run_partial_pipeline,
)


def _frame(shape: tuple[int, int] = (8, 8)):
    pixel = np.arange(shape[0] * shape[1], dtype=np.float32).reshape(shape)
    return new_frame(pixel)


def _passthrough_registry_and_calib(stages: tuple[str, ...], shape: tuple[int, int]):
    registry = {s: passthrough.process for s in stages}
    # Kind-match via the real adapter (offset/gain/etc. are wired in
    # _KIND_BY_STAGE and the entry gate rejects a mismatched CalibKind even
    # when the process callable itself is an identity passthrough).
    calib_map = build_synthetic_calib_map(PipelineDefinition(stages), shape)
    return registry, calib_map


# -- SELECTABLE_STAGES / registry / calib-map adapters (structural) ----------


def test_selectable_stages_excludes_reserved_post_tail():
    assert "post" not in SELECTABLE_STAGES
    assert set(SELECTABLE_STAGES).issubset(set(CANONICAL_ORDER))
    # Canonical relative order preserved (PipelineDefinition requires a subsequence).
    assert list(SELECTABLE_STAGES) == [s for s in CANONICAL_ORDER if s in SELECTABLE_STAGES]


def test_build_pipeline_registry_adapts_module_objects_to_callables():
    registry = build_pipeline_registry()
    assert set(registry) == set(SELECTABLE_STAGES)
    for stage, callable_ in registry.items():
        assert callable(callable_), f"{stage}: adapter must yield a bare callable"


def test_build_synthetic_calib_map_is_schema_valid_and_kind_matched():
    definition = PipelineDefinition(("geometry", "grid"))
    calib_map = build_synthetic_calib_map(definition, (16, 16))
    assert set(calib_map) == {"geometry", "grid"}
    for calib in calib_map.values():
        calib.validate()  # raises CalibSchemaError on violation
        assert calib.resolution == (16, 16)


# -- REQ-VIEW-RUN-2: stage-by-stage before/after -----------------------------


def test_partial_pipeline_produces_stage_comparisons_in_order():
    frame = _frame()
    stages = ("offset", "gain")
    registry, calib_map = _passthrough_registry_and_calib(stages, frame.shape)

    result = run_partial_pipeline(frame, stages, registry=registry, calib_map=calib_map)

    assert [c.stage for c in result.stage_comparisons] == list(stages)
    # First stage's "before" is the original input frame's pixel data.
    assert np.array_equal(result.stage_comparisons[0].before.pixel, frame.pixel)
    # Each stage's "after" chains into the next stage's "before".
    assert result.stage_comparisons[0].after is result.stage_comparisons[1].before
    # Passthrough is identity on pixel data; only the history chain grows.
    assert np.array_equal(result.final_frame.pixel, frame.pixel)
    assert len(result.final_frame.history) == len(stages)


def test_partial_pipeline_is_subset_of_canonical_order():
    frame = _frame()
    stages = ("geometry", "grid")
    registry, calib_map = _passthrough_registry_and_calib(stages, frame.shape)
    result = run_partial_pipeline(frame, stages, registry=registry, calib_map=calib_map)
    assert [c.stage for c in result.stage_comparisons] == list(stages)


# -- REQ-VIEW-ARCH-7 / C-16: determinism --------------------------------------


def test_pipeline_diff_layers_are_bit_identical_across_runs():
    frame = _frame()
    stages = ("offset", "gain", "geometry")
    registry, calib_map = _passthrough_registry_and_calib(stages, frame.shape)

    result_a = run_partial_pipeline(frame, stages, registry=registry, calib_map=calib_map)
    result_b = run_partial_pipeline(frame, stages, registry=registry, calib_map=calib_map)

    assert np.array_equal(result_a.final_frame.pixel, result_b.final_frame.pixel)
    for comp_a, comp_b in zip(result_a.stage_comparisons, result_b.stage_comparisons):
        diff_a = np.asarray(comp_a.after.pixel) - np.asarray(comp_a.before.pixel)
        diff_b = np.asarray(comp_b.after.pixel) - np.asarray(comp_b.before.pixel)
        assert np.array_equal(diff_a, diff_b)


# -- #17 export/import round-trip + C-20 data/ write refusal ----------------


def test_export_import_round_trip(tmp_path):
    frame = _frame().record_history(
        HistoryEntry(
            module_name="offset",
            module_version="1.1.0",
            params_hash="deadbeef",
            calibset_id="SYNTH-PANEL:other:8x8:2026-01-01",
        )
    )
    project_root = tmp_path / "proj"
    out_dir = project_root / "exports"
    out_dir.mkdir(parents=True)

    npz_path, json_path = export_frame(frame, out_dir / "case1", project_root)
    assert npz_path.exists()
    assert json_path.exists()

    reloaded = import_frame(out_dir / "case1")
    assert np.array_equal(reloaded.pixel, frame.pixel)
    assert np.array_equal(reloaded.masks, frame.masks)
    assert reloaded.noise == frame.noise
    assert reloaded.history == frame.history
    assert reloaded.validation_mode == frame.validation_mode
    # Reduced schema excludes intermediates (spec.md confirmed decision).
    assert reloaded.intermediates == ()


def test_export_refuses_write_under_data_root(tmp_path):
    frame = _frame()
    project_root = tmp_path / "proj"
    (project_root / "data").mkdir(parents=True)

    with pytest.raises(DataWriteRejectedError):
        export_frame(frame, project_root / "data" / "case1", project_root)

    # Nothing was written when the guard rejects the path.
    assert not (project_root / "data" / "case1.npz").exists()


def test_export_includes_pixel_f64_only_in_validation_mode(tmp_path):
    frame = new_frame(np.zeros((4, 4), dtype=np.float32), validation_mode=True)
    project_root = tmp_path / "proj"
    out_dir = project_root / "exports"
    out_dir.mkdir(parents=True)

    _, json_path = export_frame(frame, out_dir / "vmode", project_root)
    import json as _json

    meta = _json.loads(json_path.read_text(encoding="utf-8"))
    assert "pixel_f64" in meta["array_keys"]
    assert meta["validation_mode"] is True

    reloaded = import_frame(out_dir / "vmode")
    assert reloaded.pixel_f64 is not None
    assert np.array_equal(reloaded.pixel_f64, frame.pixel_f64)
