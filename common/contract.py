"""Module contract, Params container, and the module test harness.

@MX:ANCHOR: [AUTO] `process(XFrame, CalibSet, Params) -> XFrame` is the single
signature every processing module must expose (SWR-000-7, REQ-INFRA-CONTRACT-1).
@MX:REASON: The orchestrator and harness both dispatch on this exact contract;
a deviation breaks pipeline composition and module self-tests.

Scope (T0):
- Params: externalized parameter container (no hardcoding; [P] defaults are
  documented by callers, never baked into modules).
- ProcessModule Protocol: structural type for the process callable, plus an
  optional state-serialization interface (STRUCTURAL check only; runtime
  round-trip via a stateful module is deferred to T4/lag — CONTRACT-2).
- Harness: load fixture -> run process -> full XFrame comparison -> report.
- Contract check: signature + return-type violations are auto-detectable
  (CONTRACT-1, EC-3/EC-4). Global-state / file side channels are a design rule
  handled by code review, not by this checker (DATA-2, EC-4 out-of-scope).
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

from common.calibset import CalibSet
from common.xframe import XFrame, hash_params

# Canonical parameter names of the process contract, in order.
PROCESS_PARAM_NAMES: tuple[str, ...] = ("frame", "calib", "params")


@dataclass(frozen=True)
class Params:
    """Immutable, externalized parameter container (no hardcoding).

    @MX:NOTE: [AUTO] All tunable/[P]/[B]/[T] values arrive through Params or
    CalibSet — never as literals inside modules (CLAUDE.md parameter policy).
    """

    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Snapshot + freeze: never alias the caller's mutable dict, so the
        # hash recorded in the history chain always matches what modules read.
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def hash(self) -> str:
        """Deterministic hash of the parameter set (feeds history chain)."""
        return hash_params(self.values)


@runtime_checkable
class ProcessModule(Protocol):
    """Structural contract for a processing module.

    A module is any object exposing a `process` callable of the canonical
    signature. Stateful modules additionally expose serialize_state /
    load_state; the harness only checks these exist structurally at T0.
    """

    def process(
        self, frame: XFrame, calib: CalibSet, params: Params
    ) -> XFrame:  # pragma: no cover - structural protocol
        ...


@runtime_checkable
class StatefulModule(Protocol):
    """Optional state-serialization interface (CONTRACT-2, Scenario 4).

    @MX:NOTE: [AUTO] T0 verifies this interface EXISTS in the contract layer.
    Runtime round-trip validation through a real stateful module (lag) is
    deferred to T4.
    """

    def serialize_state(self) -> XFrame:  # pragma: no cover - structural protocol
        ...

    def load_state(self, frame: XFrame) -> None:  # pragma: no cover
        ...


@dataclass(frozen=True)
class MismatchReport:
    """Result of a harness comparison (CONTRACT-4)."""

    passed: bool
    violations: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.passed


def check_process_contract(module: Any) -> tuple[str, ...]:
    """Return signature/return-contract violations for `module` (EC-3/EC-4).

    Detects (statically, via inspect):
    - missing `process` callable,
    - wrong parameter count / names (canonical: frame, calib, params).

    Return-type violations (e.g. returning a tuple with an extra value) are not
    fully knowable statically and are caught at runtime by the harness.
    """
    violations: list[str] = []
    process = getattr(module, "process", None)
    if not callable(process):
        return (f"{_name(module)}: missing callable 'process'",)

    sig = inspect.signature(process)
    # Drop an implicit self/cls-style first positional if bound method already
    # strips it; inspect.signature on a bound method excludes self.
    param_names = [
        p.name
        for p in sig.parameters.values()
        if p.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if tuple(param_names) != PROCESS_PARAM_NAMES:
        violations.append(
            f"{_name(module)}: process must take exactly "
            f"{PROCESS_PARAM_NAMES}, got {tuple(param_names)}"
        )
    return tuple(violations)


def run_harness(
    module: Any,
    input_frame: XFrame,
    calib: CalibSet,
    params: Params,
    expected: XFrame,
) -> MismatchReport:
    """Load fixture -> run process -> compare full XFrame (CONTRACT-3/4).

    @MX:ANCHOR: [AUTO] TC-000 decision engine A. Compares pixel, mask stack,
    noise model, and history chain; also detects return-contract violations
    (non-XFrame / extra return value).
    @MX:REASON: This is the harness every module's fixture self-test runs
    through; its comparison semantics define what "module output matches" means.
    """
    violations: list[str] = list(check_process_contract(module))
    if violations:
        return MismatchReport(passed=False, violations=tuple(violations))

    result = module.process(input_frame, calib, params)
    violations.extend(_compare_output(module, result, expected))
    return MismatchReport(passed=not violations, violations=tuple(violations))


def _compare_output(module: Any, result: Any, expected: XFrame) -> list[str]:
    """Return output-comparison violations shared by both harness variants.

    Detects the return-type / extra-return-value violation (EC-4 auto-detectable
    range) and, for a valid XFrame, the full structural mismatch (CONTRACT-4).
    """
    if not isinstance(result, XFrame):
        return [
            f"{_name(module)}: process must return XFrame, got {type(result).__name__}"
        ]
    if not result.equals(expected):
        return [f"{_name(module)}: output != expected ({_diff_summary(result, expected)})"]
    return []


def run_stateful_harness(
    module: Any,
    input_frame: XFrame,
    calib: CalibSet,
    params: Params,
    expected: XFrame,
    *,
    pre_state: XFrame | None = None,
    expected_state: XFrame | None = None,
) -> MismatchReport:
    """Harness for stateful modules (REQ-LAG-CONTRACT-6, Scenario 8).

    @MX:NOTE: [AUTO] Additive extension of run_harness for the SWR-000-7
    stateful exception (lag). The pure single-call path (run_harness) is
    unchanged; this variant injects a pre-state via load_state, runs process,
    compares the full output XFrame, and (when expected_state is given) compares
    the post-state via serialize_state. This is the T4 runtime exercise of the
    StatefulModule interface deferred at T0 (CONTRACT-2).
    """
    violations: list[str] = list(check_process_contract(module))
    if violations:
        return MismatchReport(passed=False, violations=tuple(violations))

    if pre_state is not None:
        load = getattr(module, "load_state", None)
        if not callable(load):
            return MismatchReport(
                passed=False,
                violations=(f"{_name(module)}: missing callable 'load_state'",),
            )
        # Module-raised exceptions during load_state (e.g. an M-mismatch
        # pre-state) must surface as a MismatchReport, consistent with the
        # harness contract — never escape as a traceback.
        try:
            load(pre_state)
        except Exception as exc:  # noqa: BLE001 - convert to a named violation
            return MismatchReport(
                passed=False,
                violations=(
                    f"{_name(module)}: load_state raised "
                    f"{type(exc).__name__}: {exc}",
                ),
            )

    try:
        result = module.process(input_frame, calib, params)
    except Exception as exc:  # noqa: BLE001 - convert to a named violation
        return MismatchReport(
            passed=False,
            violations=(
                f"{_name(module)}: process raised {type(exc).__name__}: {exc}",
            ),
        )
    out_violations = _compare_output(module, result, expected)
    violations.extend(out_violations)
    if not isinstance(result, XFrame):
        return MismatchReport(passed=False, violations=tuple(violations))

    if expected_state is not None:
        serialize = getattr(module, "serialize_state", None)
        if not callable(serialize):
            violations.append(f"{_name(module)}: missing callable 'serialize_state'")
        else:
            state = serialize()
            if not isinstance(state, XFrame):
                violations.append(
                    f"{_name(module)}: serialize_state must return XFrame, "
                    f"got {type(state).__name__}"
                )
            elif not state.equals(expected_state):
                violations.append(
                    f"{_name(module)}: post-state != expected_state "
                    f"({_diff_summary(state, expected_state)})"
                )

    return MismatchReport(passed=not violations, violations=tuple(violations))


def _diff_summary(result: XFrame, expected: XFrame) -> str:
    # Field coverage must mirror XFrame.equals so a FAIL always names a field.
    parts: list[str] = []
    import numpy as np

    if not np.array_equal(result.pixel, expected.pixel, equal_nan=True):
        parts.append("pixel")
    if not np.array_equal(result.masks, expected.masks):
        parts.append("masks")
    if result.noise != expected.noise:
        parts.append("noise")
    if result.history != expected.history:
        parts.append("history")
    if result.validation_mode != expected.validation_mode:
        parts.append("validation_mode")
    if (result.pixel_f64 is None) != (expected.pixel_f64 is None) or (
        result.pixel_f64 is not None
        and not np.array_equal(result.pixel_f64, expected.pixel_f64, equal_nan=True)
    ):
        parts.append("pixel_f64")
    if len(result.intermediates) != len(expected.intermediates) or not all(
        a.equals(b) for a, b in zip(result.intermediates, expected.intermediates)
    ):
        parts.append("intermediates")
    return ",".join(parts) or "unknown"


def _name(module: Any) -> str:
    return getattr(module, "__name__", type(module).__name__)
