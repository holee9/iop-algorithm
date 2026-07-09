"""Sequence runner: threads per-frame state across a continuous capture.

Additive to T0 (spec decision 1, BLOCK #1 resolved). `run_pipeline` processes a
single frame in fixed canonical stage order; it has no loop over a continuous
capture sequence. The lag correction (SWR-402) is intrinsically a sequence
operation (s_i[k] depends on s_i[k-1] / I_hat[k-1]), so this runner owns the
sequence axis:

- It wraps `run_pipeline` per frame, reusing ONE registry (hence one stateful
  lag instance) across the whole sequence, so frame k's final state seeds frame
  k+1 (REQ-LAG-STATE-5).
- A fresh registry is built per sequence via the injected `registry_factory`, so
  a new sequence gets a fresh lag instance = the between-sequence reset
  (REQ-LAG-STATE-4); there is no separate reset protocol.
- It owns the forward-bias (FB) trigger handshake (SWR-404, decision 4): the SW
  only defines the request/confirm INTERFACE; the FB capture itself is panel FW.
  The trigger is a no-op by default and mock-tested.

`run_pipeline`, `CANONICAL_ORDER`, the entry gate, and the process contract are
UNCHANGED (additive). This module imports only `common` + the orchestrator (its
own layer); processing callables (including the lag instance) are injected via
`registry_factory`, so pipeline never imports `modules` (registry pattern,
orchestrator precedent).
"""

from __future__ import annotations

from typing import Callable, Mapping, Protocol, Sequence, runtime_checkable

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import XFrame
from pipeline.orchestrator import (
    PipelineDefinition,
    ProcessCallable,
    run_pipeline,
)

# A factory yields a fresh stage-name -> callable registry per sequence. Building
# it per sequence is what expresses the reset: a new lag instance starts at
# s_i[-1] = 0 (REQ-LAG-STATE-4).
RegistryFactory = Callable[[], Mapping[str, ProcessCallable]]


@runtime_checkable
class FBTrigger(Protocol):
    """Forward-bias trigger handshake (SWR-404 interface-only, decision 4).

    The SW defines only the request/confirm contract; the FB capture is panel
    firmware (Exclusions). P1 has no real acquisition layer, so this is a stub
    exercised with a mock.
    """

    def request(self) -> None:  # pragma: no cover - structural protocol
        ...

    def confirm(self) -> bool:  # pragma: no cover - structural protocol
        ...


class NoOpFBTrigger:
    """Default FB trigger: issues no real request and confirms trivially."""

    def request(self) -> None:
        return None

    def confirm(self) -> bool:
        return True


# @MX:ANCHOR: [AUTO] sole sequence-driving entry point; owns lag state lifetime
# (= sequence lifetime) and the FB trigger handshake.
# @MX:REASON: fan_in spans the XDET-TC-004/005 live gates and the CONTRACT-2
# resume-equivalence test; the per-sequence fresh-registry reset semantics and
# the frame-to-frame state threading are the invariants those consumers rely on.
def run_sequence(
    frames: Sequence[XFrame],
    definition: PipelineDefinition,
    registry_factory: RegistryFactory,
    calib_map: Mapping[str, CalibSet],
    params_map: Mapping[str, Params] | None = None,
    *,
    panel_id: str | None = None,
    timestamp: str | None = None,
    fb_trigger: FBTrigger | None = None,
) -> list[XFrame]:
    """Run one continuous capture sequence, threading state across frames.

    Args:
        frames: the ordered capture sequence (each treated immutable, DATA-6).
        definition: the canonical stage subset (includes "lag").
        registry_factory: builds a FRESH registry (fresh lag instance) for THIS
            sequence; calling it is the between-sequence reset.
        calib_map / params_map: per-stage CalibSet / Params (entry gate input).
        fb_trigger: FB request/confirm handshake; defaults to a no-op.

    Returns:
        the per-frame output XFrames, in capture order.
    """
    trigger = fb_trigger if fb_trigger is not None else NoOpFBTrigger()
    # FB is requested before the capture sequence begins (REQ-LAG-CORR-3).
    trigger.request()
    trigger.confirm()

    # One registry (one stateful lag instance) for the whole sequence.
    registry = registry_factory()

    outputs: list[XFrame] = []
    for frame in frames:
        result = run_pipeline(
            frame,
            definition,
            registry,
            calib_map,
            params_map,
            panel_id=panel_id,
            timestamp=timestamp,
        )
        outputs.append(result)
    return outputs
