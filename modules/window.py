"""Automatic windowing + GSDF presentation (SWR-901~903, T6/WP7).

Stateless, pure-functional display windowing (SPEC-POST-001). Four stages:

    (1) collimation-field recognition (common.histogram_fov.detect_collimation_field,
        SWR-901 step 1) excludes the unexposed collimated border.
    (2) direct-exposure separation (common.histogram_fov.separate_direct_exposure,
        SWR-901 step 2) removes the bright unattenuated mode.
    (3) VOI [p_low, p_high] on the effective-anatomy histogram from a region
        preset (SWR-901/902), with an optional manual override (SWR-902), then
        remap of the valid signal into the standard P-value scale (SWR-901 VOI
        apply, REQ-POST-WINDOW-4). This windowed P-value is the upstream trigger
        of the GSDF stage.
    (4) P-value -> DICOM PS3.14 GSDF JND-index LUT (SWR-903, [S]). The LUT is built
        deterministically from the parameterized display characteristic (min/max
        luminance) so equal P-value steps map to equal JND steps; a per-JND
        contrast-response deviation self-check is recorded (REQ-POST-GSDF-2).

The collimation / direct-exposure regions are stage-internal products; no new
mask flag is introduced (decision 5). Saturation pixel VALUES are preserved
unchanged (no restoration, REQ-POST-CONTRACT-6). Every tunable (presets, display
luminance, LUT sizes) is externalized via Params (no hardcoding); the GSDF
conformance pass/fail threshold is injected in tests only (measurement != judgment).

@MX:ANCHOR: [AUTO] `process` is the window pipeline stage entry point invoked via
the orchestrator registry (REQ-POST-CONTRACT-1/5).
@MX:REASON: fan_in is the orchestrator registry plus the harness and the
XDET-TC-013/014 window-fit and GSDF-conformance gates; the deterministic VOI, the
P-value remap, and the PS3.14 LUT construction are what those gates read against.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

import numpy as np

from common.calibset import CalibSet
from common.contract import Params
from common import histogram_fov
from common.xframe import HistoryEntry, MaskFlag, XFrame

MODULE_NAME = "window"
MODULE_VERSION = "1.0.0"

# -- Params keys (all externalized) --------------------------------------------
P_REGION = "window_region_code"  # anatomy region code selecting a preset (SWR-902)
P_PRESETS = "window_voi_presets"  # {region_code: (p_low, p_high)} preset table [T]/[P]
P_DEFAULT_VOI = "window_voi_default"  # fallback (p_low, p_high) percentiles [T]
P_OVERRIDE = "window_voi_override"  # manual (low_value, high_value) override (SWR-902)
P_PVALUE_MAX = "window_pvalue_levels"  # standard P-value scale size (e.g. 4096) [P]
P_COLLIM_REL = "window_collim_rel_threshold"  # collimation-field threshold frac [P]
P_DIRECT_FENCE = "window_direct_fence_k"  # direct-exposure robust upper-fence k [P]
# GSDF display characteristic (Params single source; SWR-903 [S]).
P_LUM_MIN = "gsdf_lum_min"  # display min luminance L_min (cd/m^2)
P_LUM_MAX = "gsdf_lum_max"  # display max luminance L_max (cd/m^2)
P_GSDF_JGRID = "gsdf_jnd_grid_size"  # internal JND inversion grid resolution [P]

_SATURATION = np.uint8(MaskFlag.SATURATION | MaskFlag.SATURATION_BAND)
_DEFECT = np.uint8(MaskFlag.DEFECT | MaskFlag.INTERPOLATION)

# DICOM PS3.14 GSDF forward polynomial: the JND index j as an 8th-order
# polynomial in log10(luminance), valid for L in [0.05, 4000] cd/m^2 (the Barten
# CSF fit). This is the standard, monotone-increasing form; the inverse L(j) is
# obtained numerically (below). Coefficients from DICOM PS3.14.
_GSDF_COEFFS = (
    71.498068,     # A
    94.593053,     # B * (log10 L)^1
    41.912053,     # C * (log10 L)^2
    9.8247004,     # D * (log10 L)^3
    0.28175407,    # E * (log10 L)^4
    -1.1878455,    # F * (log10 L)^5
    -0.18014349,   # G * (log10 L)^6
    0.14710899,    # H * (log10 L)^7
    -0.017046845,  # I * (log10 L)^8
)
# Valid GSDF luminance domain (cd/m^2) for the numeric inversion grid.
_GSDF_LUM_LO = 0.05
_GSDF_LUM_HI = 4000.0


class WindowError(ValueError):
    """Raised on an invalid windowing request or missing required parameter."""


def _require(params: Params, key: str, cast=float):
    value = params.get(key)
    if value is None:
        raise WindowError(f"window: missing required parameter '{key}'")
    return cast(value)


# -- DICOM PS3.14 GSDF (SWR-903, [S]) ------------------------------------------


def _gsdf_jnd_index(luminance: np.ndarray | float, grid_size: int = 0) -> np.ndarray:
    """DICOM PS3.14 GSDF JND index j as a function of luminance L (cd/m^2).

    j(L) = sum_n coeff_n * (log10 L)^n  (n = 0..8). Monotone increasing over the
    valid GSDF luminance domain. `grid_size` is accepted for signature symmetry
    with the numeric inverse but unused (the forward map is analytic).
    """
    log_l = np.log10(np.asarray(luminance, dtype=np.float64))
    return np.polynomial.polynomial.polyval(log_l, _GSDF_COEFFS)


def _gsdf_luminance(j: np.ndarray | float, grid_size: int = 8192) -> np.ndarray:
    """Invert j(L): luminance L (cd/m^2) for a JND index via monotone interpolation.

    A dense geometric luminance grid over the valid GSDF domain [0.05, 4000] is
    mapped through the analytic forward polynomial j(L) (monotone), then j -> L is
    interpolated. The interpolation residual is the genuine, bounded inversion
    error surfaced by the conformance self-check.
    """
    l_grid = np.geomspace(_GSDF_LUM_LO, _GSDF_LUM_HI, int(grid_size))
    j_grid = _gsdf_jnd_index(l_grid)  # monotone increasing in L
    return np.interp(np.asarray(j, dtype=np.float64), j_grid, l_grid)


def build_gsdf_lut(
    pvalue_levels: int,
    lum_min: float,
    lum_max: float,
    grid_size: int,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Build the P-value -> GSDF JND-index LUT and its conformance self-check.

    Equal P-value steps are mapped to equal JND-index steps between the display
    endpoints [L_min, L_max] so the presentation is perceptually linearized
    (SWR-903). Returns:
        jnd_index : (pvalue_levels,) target JND index per P-value.
        display   : (pvalue_levels,) normalized display value in [0, 1]
                    ((L(j_p) - L_min) / (L_max - L_min)).
        max_dev   : the per-JND contrast-response deviation self-check
                    (REQ-POST-GSDF-2): max over P-values of the normalized
                    difference between the JND index recovered from the realized
                    LUT luminance and the ideal equally-spaced JND index. Bounded
                    externally by the injected GSDF threshold in tests (XDET-TC-014).
    """
    if pvalue_levels < 2:
        raise WindowError("window: window_pvalue_levels must be >= 2")
    if not (0.0 < lum_min < lum_max):
        raise WindowError(
            f"window: require 0 < L_min < L_max, got L_min={lum_min}, L_max={lum_max}"
        )
    j_lo = float(_gsdf_jnd_index(lum_min, grid_size))
    j_hi = float(_gsdf_jnd_index(lum_max, grid_size))
    p = np.linspace(0.0, 1.0, int(pvalue_levels))
    jnd_index = j_lo + p * (j_hi - j_lo)  # ideal equally-spaced JND indices
    lum = _gsdf_luminance(jnd_index, grid_size)
    display = (lum - lum_min) / (lum_max - lum_min)
    # Self-check: recover the JND index from the realized luminance and compare to
    # the ideal linear schedule; the residual is the genuine LUT/interpolation
    # deviation (non-trivial, bounded by the injected GSDF threshold).
    recovered = _gsdf_jnd_index(lum, grid_size)
    span = abs(j_hi - j_lo) or 1.0
    max_dev = float(np.max(np.abs(recovered - jnd_index)) / span)
    return jnd_index, display, max_dev


# -- windowing (SWR-901~902) ---------------------------------------------------


def _resolve_voi(
    image: np.ndarray, anatomy: np.ndarray, params: Params
) -> tuple[float, float, bool]:
    """Resolve the window [low, high] signal bounds; returns (low, high, overridden).

    Manual override (REQ-POST-WINDOW-3) takes precedence; otherwise the region
    preset percentiles (REQ-POST-WINDOW-1/2) are applied to the anatomy histogram.
    """
    override = params.get(P_OVERRIDE)
    if override is not None:
        low, high = float(override[0]), float(override[1])
        if high <= low:
            raise WindowError(f"window: override high {high} <= low {low}")
        return low, high, True

    presets = params.get(P_PRESETS)
    region = params.get(P_REGION)
    voi_pct = None
    if presets is not None and region is not None and region in presets:
        voi_pct = presets[region]
    if voi_pct is None:
        voi_pct = params.get(P_DEFAULT_VOI)
    if voi_pct is None:
        raise WindowError(
            "window: no VOI available — provide window_voi_override, a matching "
            "window_voi_presets entry, or window_voi_default (SWR-902)"
        )
    p_low, p_high = float(voi_pct[0]), float(voi_pct[1])
    sample = image[anatomy] if anatomy.any() else image.ravel()
    low = float(np.percentile(sample, p_low))
    high = float(np.percentile(sample, p_high))
    if high <= low:
        high = low + 1.0
    return low, high, False


def remap_to_pvalue(
    signal: np.ndarray, low: float, high: float, pvalue_levels: int
) -> np.ndarray:
    """Linearly remap the window [low, high] onto the P-value scale (REQ-POST-WINDOW-4).

    Values below `low` map to 0, at/above `high` to `pvalue_levels - 1`; the result
    is a float P-value (fractional) suitable for LUT interpolation.
    """
    span = high - low if high > low else 1.0
    normalized = np.clip((np.asarray(signal, dtype=np.float64) - low) / span, 0.0, 1.0)
    return normalized * (int(pvalue_levels) - 1)


def _run(
    pixel: np.ndarray,
    masks_u8: np.ndarray,
    params: Params,
    lut_display: np.ndarray,
) -> tuple[np.ndarray, dict[str, float]]:
    """Full windowing + GSDF mapping for one buffer; returns (out, diagnostics)."""
    z = np.asarray(pixel, dtype=np.float64)
    rel = _require(params, P_COLLIM_REL, float)
    fence_k = _require(params, P_DIRECT_FENCE, float)
    pmax = _require(params, P_PVALUE_MAX, int)

    field = histogram_fov.detect_collimation_field(z, rel_threshold=rel)
    anatomy = histogram_fov.separate_direct_exposure(z, field, fence_k=fence_k)
    # Exclude saturation/defect pixels from the anatomy histogram (stats only).
    anatomy = anatomy & ((masks_u8 & (_SATURATION | _DEFECT)) == 0)

    low, high, overridden = _resolve_voi(z, anatomy, params)
    pvalue = remap_to_pvalue(z, low, high, pmax)
    # GSDF LUT lookup by interpolation over the P-value index grid.
    idx = np.arange(len(lut_display), dtype=np.float64)
    out = np.interp(pvalue, idx, lut_display)

    # Preserve saturation pixel VALUES unchanged (no restoration, REQ-POST-CONTRACT-6).
    preserve = (masks_u8 & _SATURATION) != 0
    out[preserve] = z[preserve]

    diagnostics = {
        "voi_low": float(low),
        "voi_high": float(high),
        "override": 1.0 if overridden else 0.0,
        "anatomy_fraction": float(np.count_nonzero(anatomy)) / float(anatomy.size),
    }
    return out, diagnostics


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Automatic windowing + GSDF; return a new XFrame (input treated immutable).

    Builds the deterministic PS3.14 GSDF LUT from the parameterized display
    characteristic, records the VOI, override flag, and GSDF conformance
    self-check deviation on the history chain (REQ-POST-CONTRACT-2, GSDF-2).
    """
    lum_min = _require(params, P_LUM_MIN, float)
    lum_max = _require(params, P_LUM_MAX, float)
    pmax = _require(params, P_PVALUE_MAX, int)
    grid_size = int(params.get(P_GSDF_JGRID, 4096))

    _, lut_display, gsdf_max_dev = build_gsdf_lut(pmax, lum_min, lum_max, grid_size)

    masks_u8 = np.asarray(frame.masks, dtype=np.uint8)
    out_pixel, diag = _run(frame.pixel, masks_u8, params, lut_display)

    out_f64: np.ndarray | None = None
    if frame.pixel_f64 is not None:
        out_f64, _ = _run(frame.pixel_f64, masks_u8, params, lut_display)

    new = frame.with_pixel(out_pixel.astype(frame.pixel.dtype), out_f64)
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra={
            "gsdf_max_dev": float(gsdf_max_dev),
            "gsdf_lum_min": float(lum_min),
            "gsdf_lum_max": float(lum_max),
            **diag,
        },
    )
    return new.record_history(entry)
