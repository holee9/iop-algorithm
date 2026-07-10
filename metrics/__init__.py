"""XDET metrics-engine layer (SPEC-METRICS-001, T1).

Pure measurement layer consuming XFrame read-only and returning MetricResult
structures (value + acquisition-condition metadata). It is NOT a processing
module: it does not implement `process(XFrame, CalibSet, Params) -> XFrame`.

Public entry points:
- result.MetricResult / MetricCondition / MetricReadError / require_param
- mtf.compute_mtf                (MTF edge method)
- nps.compute_nps / detect_line_noise   (NPS / NNPS / line noise)
- dqe.compute_dqe                (DQE = MTF^2 / (q Ka NNPS), IEC 62220-1)
- lag.compute_first_frame_lag / compute_ghost_cnr
- defect_stats.classify_defects  (ASTM E2597 7-class)
- ndt.read_duplex_srb / compute_snrn

Dependency direction is metrics -> common only (import-linter enforced).

Curated public re-exports + `__all__` (SPEC-ERGO-001 REQ-ERGO-EXPORTS): the
symbols this docstring enumerates plus the new `metric_view` return-type adapter.
Re-exports come only from this package's own submodules; existing deep-path
imports (e.g. `from metrics.mtf import compute_mtf`) keep working unchanged.
"""

from metrics.defect_stats import classify_defects
from metrics.dqe import compute_dqe
from metrics.lag import compute_first_frame_lag, compute_ghost_cnr
from metrics.mtf import compute_mtf
from metrics.ndt import compute_snrn, read_duplex_srb
from metrics.nps import compute_nps, detect_line_noise
from metrics.result import (
    MetricCondition,
    MetricReadError,
    MetricResult,
    metric_view,
    require_param,
)

__all__ = [
    # result
    "MetricResult",
    "MetricCondition",
    "MetricReadError",
    "require_param",
    "metric_view",
    # mtf
    "compute_mtf",
    # nps
    "compute_nps",
    "detect_line_noise",
    # dqe
    "compute_dqe",
    # lag
    "compute_first_frame_lag",
    "compute_ghost_cnr",
    # defect_stats
    "classify_defects",
    # ndt
    "read_duplex_srb",
    "compute_snrn",
]
