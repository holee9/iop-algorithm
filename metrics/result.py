"""Structured metric result container (REQ-METRICS-CORE-6).

@MX:ANCHOR: [AUTO] MetricResult is the single return structure for every metric
entry point (mtf/nps/dqe/lag/defect/ndt). It carries the metric value(s) plus
the deterministic acquisition-condition metadata mandated by measurement
protocol §4 (IEC 62304 traceability).
@MX:REASON: fan_in spans all seven metric functions; a field change ripples to
every consumer and every acceptance scenario that inspects result metadata.

The engine measures; it never gates. EV min/typ/max pass/fail thresholds are
injected and evaluated OUTSIDE the engine (REQ-METRICS-CORE-5), so they are
deliberately absent from this structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, TypeVar


@dataclass(frozen=True)
class MetricCondition:
    """Deterministic acquisition-condition metadata (measurement protocol §4).

    Fields mirror the metadata list fixed across spec / plan / acceptance:
    beam quality, dose level, temperature, added filter, correction state, ROI,
    the Params hash and the consumed CalibSet id.
    """

    beam_quality: str | None = None  # 선질 (e.g. "RQA5")
    dose_level: str | None = None  # 선량 수준 (e.g. "XN", "XN/2", "2XN")
    temperature_c: float | None = None  # 온도
    added_filter: str | None = None  # 필터 (e.g. "Al 21mm")
    correction_state: str | None = None  # 보정 상태 (e.g. "raw", "post-gain")
    roi: tuple[int, int, int, int] | None = None  # (top, left, height, width)
    params_hash: str | None = None  # 파라미터 해시
    calibset_id: str | None = None  # 소비 CalibSet ID


@dataclass(frozen=True)
class MetricResult:
    """Metric value(s) + condition metadata + non-fatal warnings.

    Args:
        name: metric identifier (e.g. "MTF", "NPS", "DQE").
        values: named numeric outputs (scalars or arrays).
        condition: acquisition-condition metadata (CORE-6).
        warnings: non-fatal advisories (boundary-proximity, premise violation).
    """

    name: str
    values: Mapping[str, Any]
    condition: MetricCondition = field(default_factory=MetricCondition)
    warnings: tuple[str, ...] = ()

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)


class MetricReadError(ValueError):
    """Raised when a metric cannot be produced from the given input.

    Used for explicit, non-silent read failures: MTF edge angle out of the
    permitted range (REQ-METRICS-MTF-3), duplex-wire no-dip-found
    (REQ-METRICS-NDT-4), and insufficient defect-stack input
    (REQ-METRICS-DEFECT-5). The engine never substitutes a default estimate.
    """


_T = TypeVar("_T")


def require_param(params: Any, key: str, cast: Callable[[Any], _T] = lambda x: x) -> _T:
    """Fetch a REQUIRED Params key, failing explicitly when it is absent.

    @MX:ANCHOR: [AUTO] single required-parameter accessor for every metric.
    @MX:REASON: fan_in spans mtf/nps/dqe/defect/ndt; a missing required key must
    raise MetricReadError (naming the key) rather than crash with an opaque
    TypeError from ``int(params.get(key))`` on a ``None`` (REQ-METRICS-CORE-4).

    Args:
        params: the Params container (anything exposing ``.get(key)``).
        key: the required parameter name.
        cast: value converter (e.g. ``float`` / ``int``); defaults to identity.

    Raises:
        MetricReadError: the key is missing (``None``), naming the key.
    """
    value = params.get(key)
    if value is None:
        raise MetricReadError(f"missing required parameter '{key}'")
    return cast(value)
