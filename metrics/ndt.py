"""NDT metrics: duplex-wire SRb and SNRn (REQ-METRICS-NDT, §2, SWR-1201/1202).

SRb_image is auto-read from a duplex-wire IQI profile using the ISO 20% dip
criterion (REQ-METRICS-NDT-1). SNRn = SNR * 88.6[um] / SRb_image
(REQ-METRICS-NDT-2); 88.6 is the standard normalization constant [S], injected
via Params. When no resolvable dip is found the read fails explicitly — the
engine never substitutes a default SRb estimate (REQ-METRICS-NDT-4 / EC-5).

@MX:ANCHOR: [AUTO] `read_duplex_srb` and `compute_snrn` are the NDT-group public
entry points (acceptance Scenario 7, XDET-TC-018 decision engine).
@MX:REASON: the SRb read-failure contract and the SNRn normalization are
consumed by EV-301 gating; silent estimation would corrupt the NDT verdict.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter, grey_opening

from common import robust_stats
from common.contract import Params
from common.xframe import XFrame, new_frame
from metrics.result import MetricCondition, MetricReadError, MetricResult, require_param

P_DIP_THRESHOLD = "ndt_dip_threshold"  # ISO 20% dip criterion (fraction) [P]
P_SRB_NORM_UM = "ndt_srb_norm_um"  # 88.6 um normalization constant [S]

# -- NDT T9 (SPEC-NDT-001) externalized parameter keys (no hardcoded literals) --
P_TARGET_SNRN = "ndt_target_snrn"  # acquisition-termination target SNRn [S]/[P]
P_MIN_ROI_PIXELS = "ndt_min_roi_pixels"  # minimum valid uniform pixels [P]
P_THICKNESS_METHOD = "ndt_thickness_method"  # "morphological_opening" | "gaussian" [C]
P_THICKNESS_SCALE = "ndt_thickness_scale_px"  # low-freq profile scale [T]
P_THICKNESS_GRAD_MIN = "ndt_thickness_gradient_min_frac"  # gradient-presence floor [T]
P_WIRE_VISIBILITY = "ndt_wire_visibility_threshold"  # single-wire visibility [T]/[P]
P_CLASS_A_SNRN = "ndt_class_a_snrn_min"  # Class A SNRn minimum [S]/[P]
P_CLASS_A_WIRE = "ndt_class_a_required_wire"  # Class A required wire number [S]/[P]
P_CLASS_B_SNRN = "ndt_class_b_snrn_min"  # Class B SNRn minimum [S]/[P]
P_CLASS_B_WIRE = "ndt_class_b_required_wire"  # Class B required wire number [S]/[P]


@dataclass(frozen=True)
class WirePair:
    """One duplex-wire pair: the two peak positions, the valley, and its SRb.

    Args:
        peak1_index / peak2_index: sample indices of the two wire peaks.
        valley_index: sample index of the valley between them.
        srb_um: basic spatial resolution (unsharpness) this pair marks, in um.
    """

    peak1_index: int
    valley_index: int
    peak2_index: int
    srb_um: float


def _dip(profile: np.ndarray, pair: WirePair) -> float:
    """Relative modulation (dip) of a wire pair: 1 - valley / mean(peaks)."""
    peak = 0.5 * (profile[pair.peak1_index] + profile[pair.peak2_index])
    valley = profile[pair.valley_index]
    if peak <= 0:
        return 0.0
    return float(1.0 - valley / peak)


def read_duplex_srb(
    profile: np.ndarray,
    pairs: list[WirePair],
    params: Params,
    *,
    calibset_id: str | None = None,
) -> MetricResult:
    """Auto-read SRb_image from a duplex-wire profile (20% dip criterion).

    Pairs are scanned in the given (coarse -> fine) order. SRb is the srb_um of
    the first unresolved pair (dip < threshold). If no pair is resolvable at all
    (no dip pattern found), the read fails explicitly.

    Args:
        profile: 1D intensity profile along the duplex-wire IQI.
        pairs: ordered wire pairs with known element geometry.
        params: externalized 20% dip threshold.
        calibset_id: consumed CalibSet id (metadata).

    Raises:
        MetricReadError: no resolvable dip found (REQ-METRICS-NDT-4 / EC-5).
    """
    prof = np.asarray(profile, dtype=np.float64)
    threshold = require_param(params, P_DIP_THRESHOLD, float)
    if not pairs:
        raise MetricReadError("duplex SRb: no wire pairs provided")

    dips = [_dip(prof, p) for p in pairs]
    resolved = [d >= threshold for d in dips]
    if not any(resolved):
        raise MetricReadError(
            "duplex SRb: no resolvable dip found (no 20% dip pattern) — "
            "read failure, no SRb estimate substituted"
        )

    warnings: list[str] = []
    first_unresolved = next((i for i, r in enumerate(resolved) if not r), None)
    if first_unresolved is None:
        # Every pair resolved: the resolution limit is beyond the finest pair.
        srb_pair = pairs[-1]
        warnings.append(
            "duplex SRb: all pairs resolved; SRb taken at the finest pair "
            "(true limit is finer than the IQI)"
        )
    else:
        srb_pair = pairs[first_unresolved]

    return MetricResult(
        name="duplex_srb",
        values={
            "srb_um": srb_pair.srb_um,
            "dips": np.asarray(dips),
            "first_unresolved_pair": first_unresolved,
        },
        condition=MetricCondition(params_hash=params.hash(), calibset_id=calibset_id),
        warnings=tuple(warnings),
    )


def compute_snr(
    frame: XFrame,
    roi: tuple[int, int, int, int],
    params: Params,
) -> tuple[float, float, float]:
    """Robust SNR of a uniform ROI: (snr, mean, std)."""
    t, l, h, w = roi
    region = np.asarray(frame.pixel, dtype=np.float64)[t : t + h, l : l + w]
    mean = robust_stats.robust_mean(region)
    std = robust_stats.robust_std(region)
    if std == 0:
        raise MetricReadError("SNR: zero noise in the uniform region")
    return float(mean / std), float(mean), float(std)


def compute_snrn(
    frame: XFrame,
    roi: tuple[int, int, int, int],
    srb_um: float,
    params: Params,
    *,
    calibset_id: str | None = None,
) -> MetricResult:
    """Compute SNRn = SNR * 88.6[um] / SRb_image (REQ-METRICS-NDT-2/3).

    Args:
        frame: uniform-exposure frame (consumed read-only).
        roi: (top, left, height, width) of the uniform region.
        srb_um: SRb_image (um) from `read_duplex_srb`.
        params: externalized 88.6 um normalization constant.
        calibset_id: consumed CalibSet id (metadata).
    """
    snr, mean, std = compute_snr(frame, roi, params)
    norm_um = require_param(params, P_SRB_NORM_UM, float)
    snrn = snr * norm_um / srb_um
    return MetricResult(
        name="SNRn",
        values={
            "snrn": snrn,
            "snr": snr,
            "mean": mean,
            "std": std,
            "srb_um": srb_um,
        },
        condition=MetricCondition(
            roi=roi,
            params_hash=params.hash(),
            calibset_id=calibset_id,
            beam_quality=params.get("beam_quality"),
        ),
    )


# ---------------------------------------------------------------------------
# T9 WP10 (SPEC-NDT-001): real-time SNRn accumulation (SWR-1201).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShotLogEntry:
    """One ISO 17636-2 acquisition log entry (SWR-1201 shot-by-shot record).

    Args:
        shot_index: 1-based index of this accumulation step.
        frame_count: total frames folded into the running average so far.
        snrn: running normalized SNR at this step.
        srb_um: SRb_image consumed for the normalization (um).
        snr: running (un-normalized) spatial SNR of the accumulated frame.
    """

    shot_index: int
    frame_count: int
    snrn: float
    srb_um: float
    snr: float


class SNRnAccumulator:
    """Streaming real-time SNRn over a uniform ROI (SWR-1201, REQ-NDT-ACCUM).

    @MX:ANCHOR: [AUTO] T9 NDT streaming SNRn entry point — consumes the shared
    Welford accumulator (common.robust_stats) to update the running SNR /
    SNRn = SNR * 88.6 / SRb per frame, emit the acquisition-termination signal
    on reaching the target, and record the per-shot ISO 17636-2 log.
    @MX:REASON: fan_in spans the IQI report driver, XDET-TC-018, and acceptance
    Scenario 3; it reuses T1 ``compute_snrn`` for the normalization formula so a
    divergent local formula here would double-source SNRn (SWR-000-9).

    This is a metrics-layer stateful *measurement* tool, NOT a pipeline
    processing module: it does not follow ``process(XFrame, CalibSet, Params) ->
    XFrame`` and never touches the orchestrator (REQ-NDT-CONTRACT-1/-2).
    """

    def __init__(
        self,
        roi: tuple[int, int, int, int],
        srb_um: float,
        params: Params,
        *,
        target_snrn: float | None = None,
        calibset_id: str | None = None,
    ) -> None:
        if srb_um <= 0:
            raise MetricReadError("SNRn accumulator: SRb_image must be positive")
        top, left, height, width = roi
        if height <= 0 or width <= 0 or top < 0 or left < 0:
            raise MetricReadError(f"SNRn accumulator: invalid ROI {roi}")
        self._roi = roi
        self._srb = float(srb_um)
        self._params = params
        self._calibset_id = calibset_id
        self._norm = require_param(params, P_SRB_NORM_UM, float)
        self._min_pixels = int(params.get(P_MIN_ROI_PIXELS, 1) or 1)
        self._target = (
            float(target_snrn)
            if target_snrn is not None
            else (float(params.get(P_TARGET_SNRN)) if params.get(P_TARGET_SNRN) is not None else None)
        )
        self._acc = robust_stats.WelfordAccumulator()
        self._log: list[ShotLogEntry] = []
        self._reached = False
        self._reached_index: int | None = None

    def update(self, frame: XFrame) -> ShotLogEntry:
        """Fold one new frame in and return this shot's log entry.

        Raises:
            MetricReadError: ROI out of the frame bounds, too few valid uniform
                pixels, or a degenerate (zero-noise) accumulated region — no
                silent SNR is produced (REQ-NDT-ACCUM-6 / EC-1).
        """
        top, left, height, width = self._roi
        pixels = np.asarray(frame.pixel, dtype=np.float64)
        ny, nx = pixels.shape
        if top + height > ny or left + width > nx:
            raise MetricReadError(
                f"SNRn accumulator: ROI {self._roi} exceeds frame bounds {(ny, nx)}"
            )
        region = pixels[top : top + height, left : left + width]
        if region.size < self._min_pixels:
            raise MetricReadError(
                f"SNRn accumulator: ROI has {region.size} pixels, "
                f"below the minimum {self._min_pixels}"
            )
        # Peek the accumulated per-pixel running average WITHOUT mutating the
        # shared Welford accumulator, so a rejected frame is a true no-op on
        # accumulator state (code-review defect 2). The peek reproduces the exact
        # Welford mean recurrence mean_k = mean_{k-1} + (region - mean_{k-1})/k.
        count = self._acc.count
        if count == 0:
            accumulated = region.astype(np.float64, copy=True)
        else:
            prev = self._acc.mean
            accumulated = prev + (region - prev) / (count + 1)
        # Single source of truth for the SNR -> SNRn normalization: reuse the T1
        # compute_snrn definition on the accumulated ROI (code-review defect 5).
        # It also enforces the zero-noise rejection contract (compute_snr raises
        # on a degenerate region), which — evaluated on the PEEK before the
        # commit below — keeps rejection a no-op (REQ-NDT-ACCUM-6 / EC-1).
        try:
            result = compute_snrn(
                new_frame(accumulated),
                (0, 0, accumulated.shape[0], accumulated.shape[1]),
                self._srb,
                self._params,
                calibset_id=self._calibset_id,
            )
        except MetricReadError as exc:
            raise MetricReadError(
                "SNRn accumulator: zero noise in the accumulated uniform region"
            ) from exc
        # Frame accepted: commit it to the shared accumulator.
        self._acc.update(region)
        snrn = float(result.get("snrn"))
        snr = float(result.get("snr"))
        count = self._acc.count
        entry = ShotLogEntry(
            shot_index=count, frame_count=count, snrn=snrn, srb_um=self._srb, snr=snr
        )
        self._log.append(entry)
        if self._target is not None and not self._reached and snrn >= self._target:
            self._reached = True
            self._reached_index = count
        return entry

    @property
    def shot_log(self) -> tuple[ShotLogEntry, ...]:
        """The per-shot ISO 17636-2 acquisition log accumulated so far."""
        return tuple(self._log)

    @property
    def target_reached(self) -> bool:
        """Acquisition-termination decision (target SNRn reached)."""
        return self._reached

    @property
    def target_frame_index(self) -> int | None:
        """1-based frame index at which the target was first reached (or None)."""
        return self._reached_index

    @property
    def current(self) -> ShotLogEntry | None:
        """The most recent shot log entry (None before the first frame)."""
        return self._log[-1] if self._log else None


# ---------------------------------------------------------------------------
# T9 WP10: thickness correction (SWR-1203, REQ-NDT-THICK).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ThicknessResult:
    """Measurement-local flattened copy (NOT a pipeline-flowing XFrame).

    Args:
        flattened: the flattened pixel array (float64), consumed only by the
            downstream SRb-protection / CSa measurement — it never re-enters the
            pipeline as a processing-stage output (SPEC decision 1).
        low_freq: the subtracted large-scale low-frequency thickness profile.
        method: the estimator used ("morphological_opening" | "gaussian").
        scale_px: the low-frequency scale applied.
        changed: False when the input passed through numerically unchanged.
        warnings: non-fatal advisories (no-gradient / oversized-scale passthrough).
    """

    flattened: np.ndarray
    low_freq: np.ndarray
    method: str
    scale_px: float
    changed: bool
    warnings: tuple[str, ...] = ()


def _disk_footprint(radius: int) -> np.ndarray:
    """Boolean disk (circular) structuring element of the given radius.

    @MX:NOTE: [AUTO] plan.md THICK HOW mandates a large-diameter CIRCULAR
    structuring element for the opening estimator, not a square — so the
    low-frequency thickness profile is flattened isotropically.
    """
    r = max(int(radius), 0)
    yy, xx = np.ogrid[-r : r + 1, -r : r + 1]
    return (yy * yy + xx * xx) <= r * r


def correct_thickness(
    frame: XFrame,
    params: Params,
    *,
    calibset_id: str | None = None,
) -> ThicknessResult:
    """Flatten a thickness-derived low-frequency gradient (SWR-1203).

    Subtracts a large-scale low-frequency profile (Params ``thickness_method``:
    ``morphological_opening`` default, or ``gaussian``; scale via
    ``thickness_scale_px`` [T]) so the thickness gradient is removed while the
    high-frequency defect band is preserved. The input XFrame is consumed
    read-only and the flattened result is a measurement-local copy.

    A flat input (no low-frequency gradient) or an oversized scale passes
    through numerically unchanged with a warning — never a silent high-frequency
    distortion (REQ-NDT-THICK-3 / EC-2).

    Raises:
        MetricReadError: unknown ``thickness_method`` value.
    """
    image = np.asarray(frame.pixel, dtype=np.float64)
    method = str(params.get(P_THICKNESS_METHOD, "morphological_opening"))
    scale = require_param(params, P_THICKNESS_SCALE, float)
    grad_min = float(params.get(P_THICKNESS_GRAD_MIN, 0.0) or 0.0)
    ny, nx = image.shape
    warnings: list[str] = []

    # Method-specific effective kernel span (linear support in px). The oversized
    # guard must compare the ACTUAL structuring support against the frame, not the
    # raw scale (code-review defect 1): grayscale opening builds a DOUBLE-width
    # kernel (2*scale+1), so a scale well under the frame size can still yield a
    # structuring element that spans the whole frame and degenerates the flatten.
    if method == "gaussian":
        # A Gaussian low-pass is well defined for any sigma below the frame
        # extent; its effective radius is the characteristic scale sigma.
        radius = None
        kernel_span = scale
    elif method == "morphological_opening":
        radius = int(round(scale))
        kernel_span = 2 * radius + 1  # full circular structuring-element diameter
    else:
        raise MetricReadError(
            f"thickness: unknown method '{method}' "
            "(expected 'morphological_opening' or 'gaussian')"
        )

    if kernel_span >= min(ny, nx):
        return ThicknessResult(
            flattened=image.copy(),
            low_freq=np.zeros_like(image),
            method=method,
            scale_px=scale,
            changed=False,
            warnings=(
                f"thickness: scale {scale} gives {method} kernel span "
                f"{kernel_span} >= frame size {min(ny, nx)}; passthrough "
                "numerically unchanged (no subtraction)",
            ),
        )

    if method == "gaussian":
        low = gaussian_filter(image, sigma=scale, mode="nearest")
    else:  # morphological_opening: large-diameter CIRCULAR (disk) SE (plan.md HOW)
        low = grey_opening(image, footprint=_disk_footprint(radius), mode="nearest")

    prof_mean = float(np.mean(low))
    prof_range = float(low.max() - low.min())
    frac = prof_range / prof_mean if prof_mean > 0 else 0.0
    if frac < grad_min:
        warnings.append(
            f"thickness: low-frequency gradient range/mean {frac:.4f} below "
            f"threshold {grad_min}; passthrough numerically unchanged"
        )
        return ThicknessResult(
            flattened=image.copy(),
            low_freq=low,
            method=method,
            scale_px=scale,
            changed=False,
            warnings=tuple(warnings),
        )

    flattened = image - low + prof_mean
    return ThicknessResult(
        flattened=flattened,
        low_freq=low,
        method=method,
        scale_px=scale,
        changed=True,
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# T9 WP10: single-wire IQI auto-read + Class A/B report (SWR-1204, REQ-NDT-IQI).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WireElement:
    """One single-wire (ISO 19232 wire-type) IQI element.

    Args:
        number: the IQI wire number (higher number = thinner wire = finer detail).
        index: sample index of the wire's dip in the 1D profile.
    """

    number: int
    index: int


def read_single_wire_iqi(
    profile: np.ndarray,
    wires: list[WireElement],
    params: Params,
    *,
    calibset_id: str | None = None,
) -> MetricResult:
    """Auto-detect single-wire IQI elements and the minimum visible wire.

    A wire is *visible* when its dip contrast (1 - valley / background) meets the
    externalized visibility threshold. ``min_visible_wire`` is the finest
    (highest-numbered) still-visible wire — the wire-type IQI sensitivity readout
    (SWR-1204). The visibility threshold is a Params [T]/[P] value, never baked in.

    Raises:
        MetricReadError: no wire elements, non-positive background, or no wire
            visible at all (no silent default sensitivity is substituted).
    """
    prof = np.asarray(profile, dtype=np.float64)
    threshold = require_param(params, P_WIRE_VISIBILITY, float)
    if not wires:
        raise MetricReadError("single-wire IQI: no wire elements provided")
    background = float(np.median(prof))
    if background <= 0:
        raise MetricReadError("single-wire IQI: non-positive background")

    contrasts: dict[int, float] = {}
    visible: dict[int, bool] = {}
    for wire in wires:
        if wire.index < 0 or wire.index >= prof.size:
            raise MetricReadError(
                f"single-wire IQI: wire {wire.number} index {wire.index} out of "
                f"range [0, {prof.size}) — no silent wrap-around read"
            )
        valley = float(prof[wire.index])
        contrast = (background - valley) / background
        contrasts[wire.number] = contrast
        visible[wire.number] = contrast >= threshold

    visible_numbers = [n for n, v in visible.items() if v]
    if not visible_numbers:
        raise MetricReadError(
            "single-wire IQI: no visible wire (all dips below the visibility "
            "threshold) — no minimum-visible-wire substituted"
        )
    min_visible_wire = max(visible_numbers)
    return MetricResult(
        name="single_wire_iqi",
        values={
            "min_visible_wire": min_visible_wire,
            "contrasts": contrasts,
            "visible": visible,
            "background": background,
        },
        condition=MetricCondition(params_hash=params.hash(), calibset_id=calibset_id),
    )


@dataclass(frozen=True)
class IqiShot:
    """Combined per-shot inputs to the Class A/B report.

    Args:
        shot_index: 1-based shot index.
        snrn: normalized SNR for this shot (from SNRnAccumulator).
        srb_um: duplex-wire SRb_image (from read_duplex_srb reuse).
        min_visible_wire: finest visible single-wire number (read_single_wire_iqi).
    """

    shot_index: int
    snrn: float
    srb_um: float
    min_visible_wire: int


@dataclass(frozen=True)
class ShotVerdict:
    """Per-shot Class A/B verdict row of the inspection report."""

    shot_index: int
    snrn: float
    srb_um: float
    min_visible_wire: int
    class_a_pass: bool
    class_b_pass: bool
    verdict: str  # "A" | "B" | "FAIL"


def build_iqi_report(
    shots: list[IqiShot],
    params: Params,
    *,
    calibset_id: str | None = None,
) -> MetricResult:
    """Combine SNRn + duplex SRb + min-visible-wire into a Class A/B report.

    Each shot is graded against the ISO 17636-2 Class A/B requirements (SNRn
    minimum + required wire number), all Params-injected [S]/[P] and consumed
    only to PRODUCE the report — the EV-301 test pass line stays outside the
    engine (measurement != judgment, REQ-NDT-CONTRACT-4). Class B is the more
    demanding class; a shot's verdict is the most demanding class it satisfies.

    Args:
        shots: per-shot combined inputs (SNRn, SRb, min visible wire).
        params: externalized Class A/B requirements.
    """
    a_snrn = require_param(params, P_CLASS_A_SNRN, float)
    a_wire = require_param(params, P_CLASS_A_WIRE, int)
    b_snrn = require_param(params, P_CLASS_B_SNRN, float)
    b_wire = require_param(params, P_CLASS_B_WIRE, int)

    verdicts: list[ShotVerdict] = []
    for shot in shots:
        a_ok = shot.snrn >= a_snrn and shot.min_visible_wire >= a_wire
        b_ok = shot.snrn >= b_snrn and shot.min_visible_wire >= b_wire
        if b_ok:
            verdict = "B"
        elif a_ok:
            verdict = "A"
        else:
            verdict = "FAIL"
        verdicts.append(
            ShotVerdict(
                shot_index=shot.shot_index,
                snrn=shot.snrn,
                srb_um=shot.srb_um,
                min_visible_wire=shot.min_visible_wire,
                class_a_pass=a_ok,
                class_b_pass=b_ok,
                verdict=verdict,
            )
        )
    return MetricResult(
        name="iqi_report",
        values={
            "shots": tuple(verdicts),
            "class_a_snrn_min": a_snrn,
            "class_a_required_wire": a_wire,
            "class_b_snrn_min": b_snrn,
            "class_b_required_wire": b_wire,
        },
        condition=MetricCondition(params_hash=params.hash(), calibset_id=calibset_id),
    )
