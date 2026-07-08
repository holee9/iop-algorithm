"""XDET orchestration layer.

The orchestrator (pipeline definition) is the ONLY place that decides module
execution order and composition (SWR-000-8/-2, REQ-INFRA-ORCH-1). It may import
`modules` and `common`; modules never call each other directly.
"""

from pipeline.orchestrator import (
    CANONICAL_ORDER,
    PipelineDefinition,
    CalibrationError,
    run_pipeline,
)

__all__ = [
    "CANONICAL_ORDER",
    "PipelineDefinition",
    "CalibrationError",
    "run_pipeline",
]
