"""GUI-only `[T]` threshold settings (#SPEC-VIEWER-001 "확정 사항" 1).

@MX:NOTE: [AUTO] Every runtime `[T]` budget referenced by REQ-VIEW-IMAGE/ARCH
(W/L response, cold start, RSS ceiling, LRU frame cap, event-loop block, diff
display-range policy) is externalized here rather than hardcoded inside widget
code (HARD parameter policy, CLAUDE.md). This module carries over the
`modules/window.py` `P_*` naming + `_require` validation convention to a
GUI-local settings mapping. It is deliberately NOT `common.contract.Params`
(that container is the frame-processing contract consumed by `process()`, a
different concern than the GUI runtime budget) and NOT a `pyproject.toml`
`[tool.*]` section (those are build/tool configuration, not runtime state).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, TypeVar

import numpy as np

# -- [T] setting keys (GUI-local, mirrors modules/window.py P_* convention) --
T_WL_RESPONSE_MS = "wl_response_ms"  # C-01/SG-2: W/L display-update response budget
T_COLD_START_S = "cold_start_s"  # C-17/SG-3: cold-start-to-interactive budget
T_RSS_LIMIT_MB = "rss_limit_mb"  # C-18: resident-memory ceiling for loaded frames
T_LRU_FRAMES = "lru_frames"  # C-18: max cached frames before LRU eviction (K)
T_EVENT_LOOP_MS = "event_loop_block_ms"  # C-19: max GUI-thread block per long op step
T_DIFF_RANGE_MODE = "diff_range_mode"  # C-06: diff colormap default-range policy

# Literature-anchored defaults (spec.md "확정 사항" 1): Nielsen 0.1s / RAIL
# <100ms for W/L, Nielsen 10s attention limit for cold start (pyqtgraph
# measured 0.52s in the Phase 0 spike, ~20x headroom).
_DEFAULTS: dict[str, Any] = {
    T_WL_RESPONSE_MS: 100.0,
    T_COLD_START_S: 10.0,
    T_RSS_LIMIT_MB: 2048.0,
    T_LRU_FRAMES: 8,
    T_EVENT_LOOP_MS: 200.0,
    T_DIFF_RANGE_MODE: "symmetric_max_abs",
}

_T = TypeVar("_T")


class GuiConfigError(ValueError):
    """Raised when a required GUI `[T]` setting is missing (no silent default)."""


def _require(
    settings: Mapping[str, Any], key: str, cast: Callable[[Any], _T] = float
) -> _T:
    """Fetch a required `[T]` setting, failing loudly when absent (SWR-000-5 style).

    Mirrors `modules/window.py::_require` so GUI settings and core Params share
    the same "no hardcoded literal, no silent default substitution" discipline.
    """
    value = settings.get(key)
    if value is None:
        raise GuiConfigError(f"gui config: missing required setting '{key}'")
    return cast(value)


@dataclass(frozen=True)
class GuiConfig:
    """Immutable snapshot of GUI `[T]` runtime thresholds."""

    values: Mapping[str, Any] = field(default_factory=lambda: dict(_DEFAULTS))

    def get(self, key: str, cast: Callable[[Any], _T] = float) -> _T:
        return _require(self.values, key, cast)


def default_config() -> GuiConfig:
    """Return the default `[T]` settings snapshot (all keys populated)."""
    return GuiConfig()


def diff_range(diff: np.ndarray, config: GuiConfig | None = None) -> tuple[float, float]:
    """Default 0-centered diff display range: (-max|diff|, +max|diff|) (C-06).

    `config` is accepted (and its `T_DIFF_RANGE_MODE` read) for forward
    compatibility with alternative range policies; only the symmetric-max-abs
    policy is implemented at Phase 1 (the only mode declared in `_DEFAULTS`).
    """
    cfg = config or default_config()
    mode = cfg.get(T_DIFF_RANGE_MODE, cast=str)
    if mode != "symmetric_max_abs":
        raise GuiConfigError(f"gui config: unsupported {T_DIFF_RANGE_MODE!r} '{mode}'")
    arr = np.asarray(diff)
    peak = float(np.max(np.abs(arr))) if arr.size else 0.0
    if peak == 0.0:
        peak = 1.0
    return (-peak, peak)
