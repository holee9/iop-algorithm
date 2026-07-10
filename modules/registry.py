"""Default module registry: `default_registry()` (#15, additive, SPEC-VIEWER-001).

@MX:NOTE: [AUTO] Read-only name -> ProcessModule lookup consumed by the GUI
module-selection UI (REQ-VIEW-CORE-2). This is a hand-enumerated convenience
mapping; it does NOT replace `pipeline.orchestrator.CANONICAL_ORDER` or the
per-run registry `pipeline.orchestrator.run_pipeline` requires (stage ->
process CALLABLE, see `tests/test_e2e_smoke.py`). Values here are the module
OBJECTS themselves (or a fresh stateful instance for `lag`), each satisfying
`common.contract.ProcessModule` structurally
(`.process(frame, calib, params) -> XFrame`) -- the shape both direct
execution (REQ-VIEW-RUN-1) and `common.contract.run_harness` expect (see
`tests/test_tc000.py::test_tc000_A_passthrough_harness_passes`, which passes
the module object, not its bare `process` function).

additive only: `pipeline/orchestrator.py`'s `CANONICAL_ORDER` and every
module's `process(XFrame, CalibSet, Params) -> XFrame` signature are
unchanged (REQ-VIEW-CORE-4, SWR-000-6/-7).
"""

from __future__ import annotations

from common.contract import ProcessModule
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


def default_registry() -> dict[str, ProcessModule]:
    """Return the default stage-name -> ProcessModule mapping (REQ-VIEW-CORE-2).

    Values expose `.process(XFrame, CalibSet, Params) -> XFrame` directly
    (stateless stage modules) or via a fresh instance (`lag`, the SWR-000-7
    stateful exception -- a new `LagCorrector()` carries the
    between-sequence-reset initial state, REQ-LAG-STATE-4).
    """
    return {
        "offset": offset,
        "gain": gain,
        "defect": defect,
        "lag": lag.LagCorrector(),
        "line_noise": line_noise,
        "saturation": saturation,
        "geometry": geometry,
        "grid": grid,
        "virtual_grid": virtual_grid,
        "denoise": denoise,
        "mse": mse,
        "window": window,
    }
