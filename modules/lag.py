"""Lag (afterglow) correction: exponential-sum state-variable recursion.

SWR-401~404 / FR-C005-C006. Gen 1 implements the LTI exponential-sum IRF
h[n] = sum_i a_i * b_i**n (M = 3..4, [L]) via the state-variable recursion
(SWR-402)::

    s_i[k] = b_i * (s_i[k-1] + a_i * I_hat[k-1])
    I_hat[k] = I[k] - sum_i s_i[k]

lag is the one processing module that carries state across a continuous capture
SEQUENCE. It is the SWR-000-7 explicitly-permitted stateful exception: the
per-frame exponential-term state {s_i} (M planes of the frame shape) is internal
but MUST be serializable to an XFrame container (REQ-INFRA-CONTRACT-2, the first
RUNTIME validation of the T0 `StatefulModule` interface).

Design decisions (spec, RESOLVED):
- Decision 2: state {s_i} is packed as an (M, ny, nx) float32 XFrame pixel +
  zeros masks; float32 is fixed so serialize -> load is byte-identical.
- Decision 6 / REQ-LAG-CORR-5: a SATURATION pixel keeps its input value (no
  sub-saturation value is invented, SWR-602 spirit, modules.line_noise
  precedent), but the internal recursion still advances that pixel using the
  CALCULATED I_hat, so state evolution stays physical.

IRF coefficients (a_i, b_i, M) are real-measurement-pending [B] and arrive only
through CalibSet(kind=LAG); they are never hardcoded (SWR-000-5). The module
exposes no [T]/[P] tuning constant (the recursion is fully IRF-determined).

Dependency direction is modules -> common only (SWR-000-8); the module never
imports pipeline/metrics/other modules. first-frame-lag / ghost-CNR judgment is
performed by tests consuming metrics.lag alongside this module (CONTRACT-3).

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import HistoryEntry, MaskFlag, XFrame

MODULE_NAME = "lag"
MODULE_VERSION = "1.0.0"

# CalibSet(LAG) data payload keys: the exponential-sum IRF coefficients ([B]).
K_IRF_A = "irf_a"  # (M,) amplitudes a_i
K_IRF_B = "irf_b"  # (M,) poles b_i (0 < b_i < 1 for a decaying afterglow)

# State XFrame payload dtype is fixed to make serialize/load byte-identical
# (spec decision 2). This mirrors common.xframe.PIXEL_DTYPE (float32).
STATE_DTYPE = np.float32


class LagCalibError(ValueError):
    """Raised when CalibSet(LAG) lacks the IRF coefficient payload.

    @MX:NOTE: [AUTO] No silent default IRF is ever substituted (SWR-000-5,
    offset raw_saturation_threshold precedent); the missing key is named.
    """


class LagStateError(RuntimeError):
    """Raised on an inconsistent state operation (shape / M mismatch)."""


def _load_irf(calib: CalibSet) -> tuple[np.ndarray, np.ndarray]:
    """Extract and validate the (a_i, b_i) IRF vectors from CalibSet(LAG)."""
    for key in (K_IRF_A, K_IRF_B):
        if key not in calib.data:
            raise LagCalibError(
                f"lag: CalibSet(LAG) missing required IRF coefficient '{key}' "
                f"(present keys: {sorted(calib.data.keys())})"
            )
    a = np.asarray(calib.data[K_IRF_A], dtype=np.float64).reshape(-1)
    b = np.asarray(calib.data[K_IRF_B], dtype=np.float64).reshape(-1)
    if a.size != b.size or a.size == 0:
        raise LagCalibError(
            f"lag: IRF vectors must be equal-length and non-empty "
            f"(got len(a)={a.size}, len(b)={b.size})"
        )
    return a, b


class LagCorrector:
    """Stateful lag-correction module (SWR-000-7 permitted exception).

    A fresh instance carries the initial state s_i[-1] = 0. The sequence runner
    (pipeline.sequence) creates one instance per capture sequence, so a new
    instance IS the between-sequence reset (REQ-LAG-STATE-4); there is no
    separate reset protocol method. Within a sequence the same instance is
    reused frame to frame so state threads forward (REQ-LAG-STATE-5).
    """

    def __init__(self) -> None:
        # None until the first frame fixes (M, ny, nx); then float32 (M,ny,nx).
        self._state: np.ndarray | None = None

    # -- correction --------------------------------------------------------

    # @MX:ANCHOR: [AUTO] lag stage entry point; the SWR-402 recursion contract.
    # @MX:REASON: fan_in spans the orchestrator registry, the module harness,
    # the sequence runner, and the XDET-TC-004/005 release gates; the recursion
    # order and the SATURATION value-preservation rule are what those consumers
    # read against.
    def process(self, frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
        """Apply one recursion step; return a new XFrame (input immutable).

        The input `params` carries no lag tuning constant (the recursion is
        fully determined by the CalibSet(LAG) IRF); it is threaded through only
        for the deterministic history-chain params hash (REQ-LAG-CONTRACT-2).
        """
        a, b = _load_irf(calib)
        m_terms = a.size
        shape = frame.shape
        if self._state is None:
            self._state = np.zeros((m_terms, *shape), dtype=STATE_DTYPE)
        elif self._state.shape != (m_terms, *shape):
            raise LagStateError(
                f"lag: state shape {self._state.shape} incompatible with frame "
                f"{shape} and M={m_terms} (sequence frame geometry must be fixed)"
            )

        a3 = a[:, None, None]
        b3 = b[:, None, None]

        def _correct(image: np.ndarray, protect: np.ndarray) -> np.ndarray:
            # I_hat[k] = I[k] - sum_i s_i[k]. State s_i[k] carried into this call.
            state = self._state.astype(np.float64)
            lag_sum = state.sum(axis=0)
            i_hat = image - lag_sum
            # SATURATION pixel output preserved (REQ-LAG-CORR-5) but the state
            # recursion below advances every pixel with the CALCULATED i_hat.
            out = np.where(protect, image, i_hat)
            # Advance to s_i[k+1] = b_i * (s_i[k] + a_i * I_hat[k]) (all pixels).
            self._state = (b3 * (state + a3 * i_hat[None, :, :])).astype(STATE_DTYPE)
            return out

        masks_u8 = np.asarray(frame.masks, dtype=np.uint8)
        protect = (masks_u8 & np.uint8(MaskFlag.SATURATION)) != 0

        # Authoritative float32 path drives the (serialized) state. A validation
        # float64 buffer, when present, is corrected with the same state sum
        # snapshot (sequence-axis state threading is separate from the per-stage
        # validation buffer, plan section 7); it does not re-advance state.
        image_f64 = np.asarray(frame.pixel, dtype=np.float64)
        state_snapshot = self._state.astype(np.float64).sum(axis=0)
        out_pixel = _correct(image_f64, protect).astype(frame.pixel.dtype)

        out_f64: np.ndarray | None = None
        if frame.pixel_f64 is not None:
            vimg = np.asarray(frame.pixel_f64, dtype=np.float64)
            vhat = vimg - state_snapshot
            out_f64 = np.where(protect, vimg, vhat)

        new = frame.with_pixel(out_pixel, out_f64)
        entry = HistoryEntry(
            module_name=MODULE_NAME,
            module_version=MODULE_VERSION,
            params_hash=params.hash(),
            calibset_id=calib.calibset_id,
            extra={
                "m_terms": int(m_terms),
                "saturation_preserved": int(np.count_nonzero(protect)),
                "state_l1": float(np.abs(self._state).sum()),
            },
        )
        return new.record_history(entry)

    # -- state serialization (CONTRACT-2 runtime validation) ---------------

    # @MX:ANCHOR: [AUTO] first runtime exercise of the StatefulModule interface
    # deferred from T0 (REQ-INFRA-CONTRACT-2); {s_i} <-> XFrame round-trip.
    # @MX:REASON: REQ-LAG-VALIDATE-4 requires the serialize -> load round-trip to
    # be byte-identical; the (M,ny,nx) float32 packing contract is what the
    # resume-equivalence gate and the harness state comparison read against.
    def serialize_state(self) -> XFrame:
        """Pack {s_i} into an (M, ny, nx) float32 XFrame (zeros masks)."""
        if self._state is None:
            raise LagStateError(
                "lag: no state to serialize (process has not run on any frame)"
            )
        state = np.array(self._state, dtype=STATE_DTYPE)
        masks = np.zeros(state.shape, dtype=np.uint8)
        return XFrame(pixel=state, masks=masks)

    def load_state(self, frame: XFrame) -> None:
        """Restore {s_i} from an (M, ny, nx) float32 state XFrame."""
        state = np.asarray(frame.pixel, dtype=STATE_DTYPE)
        if state.ndim != 3:
            raise LagStateError(
                f"lag: state XFrame pixel must be (M, ny, nx); got ndim {state.ndim}"
            )
        self._state = np.array(state, dtype=STATE_DTYPE)
