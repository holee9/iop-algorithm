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
"""
