"""Geometric distortion correction (SWR-603, FR-C009).

Consumes a low-order polynomial distortion model from CalibSet(OTHER) and, when
active, resamples the frame onto the ideal grid to remove the distortion.

REQ-LNSG-GEOM-1 (Optional, active): a distortion model (forward displacement
field, polynomial degree [B]) whose calibration residual >= EV-106 min is
inverted (fixed-point) and applied by spline resampling, driving the post-
correction residual within EV-106 min.
REQ-LNSG-GEOM-2 (State-Driven, inactive): WHILE the calibration residual is
BELOW EV-106 min (FPD direct-imaging distortion negligible), the module is an
identity passthrough -- input pixels are returned unchanged. A history entry is
still recorded with an explicit 'active=False' marker. The active/inactive
decision is deterministic (residual vs the externally injected EV-106 min); no
default is invented.

Distortion model convention: the CalibSet supplies the FORWARD displacement
field D (pixels) as polynomials in normalized coordinates u=x/(nx-1),
v=y/(ny-1): observed[p] = ideal[p + D(p)]. Correction resamples
corrected[p] = observed[p + E(p)] where E is the numerically inverted field
(E(p) = -D(p + E(p)), fixed-point), so corrected[p] == ideal[p].

@MX:ANCHOR: [AUTO] `process` is the geometry pipeline stage entry point invoked
via the orchestrator registry (REQ-LNSG-CONTRACT-1/6).
@MX:REASON: fan_in is the orchestrator registry plus the harness and the
XDET-TC-009 gate; the deterministic activation boundary and the resampling
contract are what the grid-line residual judgment reads against.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy.ndimage import map_coordinates

from common.calibset import CalibSet
from common.contract import Params
from common.xframe import HistoryEntry, XFrame

MODULE_NAME = "geometry"
MODULE_VERSION = "1.0.0"

# CalibSet(OTHER) data payload keys.
K_COEFFS_X = "distortion_coeffs_x"  # (deg+1, deg+1) poly coeffs of D_x(u,v) [px]
K_COEFFS_Y = "distortion_coeffs_y"  # (deg+1, deg+1) poly coeffs of D_y(u,v) [px]
K_RESIDUAL = "calibration_residual"  # calibration residual scalar [px]

# Params keys.
P_DEGREE = "geometry_poly_degree"  # polynomial degree [B] (SWR-603, 2-6)
P_ACTIVATE_PX = "geometry_activation_residual_px"  # EV-106 min (external inject)
P_SPLINE_ORDER = "geometry_spline_order"  # resampling spline order [P]
P_INVERSE_ITERS = "geometry_inverse_iters"  # fixed-point inverse iterations [P]

_SPLINE_ORDER_DEFAULT = 3
_INVERSE_ITERS_DEFAULT = 8


def _require(params: Params, key: str) -> float:
    value = params.get(key)
    if value is None:
        raise ValueError(f"geometry: missing required parameter '{key}'")
    return float(value)


def _poly2d(coeffs: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Evaluate sum_ij coeffs[i,j] * u**i * v**j over grids u, v."""
    out = np.zeros_like(u, dtype=np.float64)
    ni, nj = coeffs.shape
    for i in range(ni):
        ui = u**i
        for j in range(nj):
            c = float(coeffs[i, j])
            if c != 0.0:
                out += c * ui * (v**j)
    return out


def _displacement(
    coeffs_x: np.ndarray,
    coeffs_y: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    ny: int,
    nx: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Forward displacement D at the given (row, col) coordinate arrays."""
    u = cols / max(nx - 1, 1)
    v = rows / max(ny - 1, 1)
    d_col = _poly2d(coeffs_x, u, v)  # displacement along columns (x)
    d_row = _poly2d(coeffs_y, u, v)  # displacement along rows (y)
    return d_row, d_col


def _invert_field(
    coeffs_x: np.ndarray,
    coeffs_y: np.ndarray,
    ny: int,
    nx: int,
    iters: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Fixed-point inverse displacement field E: E(p) = -D(p + E(p))."""
    rr, cc = np.mgrid[0:ny, 0:nx].astype(np.float64)
    e_row = np.zeros((ny, nx), dtype=np.float64)
    e_col = np.zeros((ny, nx), dtype=np.float64)
    for _ in range(max(1, iters)):
        d_row, d_col = _displacement(
            coeffs_x, coeffs_y, rr + e_row, cc + e_col, ny, nx
        )
        e_row = -d_row
        e_col = -d_col
    return e_row, e_col


def _resample(image: np.ndarray, e_row: np.ndarray, e_col: np.ndarray, order: int) -> np.ndarray:
    ny, nx = image.shape
    rr, cc = np.mgrid[0:ny, 0:nx].astype(np.float64)
    coords = np.stack([rr + e_row, cc + e_col], axis=0)
    return map_coordinates(image, coords, order=order, mode="reflect")


def _read_coeffs(calib: CalibSet, key: str, degree: int) -> np.ndarray:
    if key not in calib.data:
        raise ValueError(f"geometry: CalibSet(OTHER) missing data key '{key}'")
    coeffs = np.asarray(calib.data[key], dtype=np.float64)
    want = (degree + 1, degree + 1)
    if coeffs.shape != want:
        raise ValueError(
            f"geometry: {key} shape {coeffs.shape} != (degree+1)^2 {want}"
        )
    return coeffs


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Apply polynomial distortion correction when the calibration residual
    warrants it; otherwise identity passthrough (REQ-LNSG-GEOM-1/2).

    Returns a new XFrame; the input frame is treated as immutable (DATA-6). The
    noise model is preserved unchanged.
    """
    activate_px = _require(params, P_ACTIVATE_PX)
    if K_RESIDUAL not in calib.data:
        raise ValueError(
            f"geometry: CalibSet(OTHER) missing data key '{K_RESIDUAL}'"
        )
    residual = float(np.asarray(calib.data[K_RESIDUAL]).reshape(-1)[0])

    # GEOM-2 deterministic activation boundary.
    if residual < activate_px:
        entry = HistoryEntry(
            module_name=MODULE_NAME,
            module_version=MODULE_VERSION,
            params_hash=params.hash(),
            calibset_id=calib.calibset_id,
            extra={
                "active": "false",
                "reason": "calibration_residual<EV106min",
                "calibration_residual": residual,
            },
        )
        # Identity passthrough: return the input frame content unchanged.
        return frame.record_history(entry)

    degree = int(_require(params, P_DEGREE))
    order = params.get(P_SPLINE_ORDER)
    order = _SPLINE_ORDER_DEFAULT if order is None else int(order)
    iters = params.get(P_INVERSE_ITERS)
    iters = _INVERSE_ITERS_DEFAULT if iters is None else int(iters)

    coeffs_x = _read_coeffs(calib, K_COEFFS_X, degree)
    coeffs_y = _read_coeffs(calib, K_COEFFS_Y, degree)
    ny, nx = frame.shape
    e_row, e_col = _invert_field(coeffs_x, coeffs_y, ny, nx, iters)

    out_pixel = _resample(
        np.asarray(frame.pixel, dtype=np.float64), e_row, e_col, order
    ).astype(frame.pixel.dtype)

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64 = _resample(
            np.asarray(frame.pixel_f64, dtype=np.float64), e_row, e_col, order
        )

    new = frame.with_pixel(out_pixel, out_f64)
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra={
            "active": "true",
            "poly_degree": degree,
            "calibration_residual": residual,
        },
    )
    return new.record_history(entry)
