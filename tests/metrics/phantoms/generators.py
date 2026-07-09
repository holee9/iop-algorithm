"""Synthetic phantom factories with analytic known values (plan.md section 5).

Each factory returns (input, known-values). Inputs are XFrames (or lists /
profiles); known values are what the engine must reproduce within a [T]
tolerance under the synthetic-validation context.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import erf

from common.xframe import new_frame
from metrics.ndt import WireElement, WirePair

# ---------------------------------------------------------------------------
# MTF: ideal slanted edge with a known Gaussian blur -> analytic MTF.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EdgePhantom:
    frame: object
    angle_deg: float
    sigma_px: float
    pitch_mm: float
    low: float
    high: float

    def analytic_mtf(self, freq_lpmm: np.ndarray) -> np.ndarray:
        """Gaussian-blur MTF: exp(-2 (pi sigma_px f_cyc_px)^2)."""
        f_cyc_px = np.asarray(freq_lpmm) * self.pitch_mm
        return np.exp(-2.0 * (np.pi * self.sigma_px * f_cyc_px) ** 2)


def make_slanted_edge(
    shape: tuple[int, int] = (128, 128),
    angle_deg: float = 2.0,
    sigma_px: float = 0.6,
    pitch_mm: float = 0.14,
    low: float = 1000.0,
    high: float = 5000.0,
    seed: int | None = None,
    edge_pos_frac: float = 0.5,
) -> EdgePhantom:
    """Render a near-vertical edge blurred by a known Gaussian.

    The pixel value is the analytic error-function step (integral of the
    Gaussian LSF) of the signed perpendicular distance to the tilted edge, so
    the presampled MTF equals the pure Gaussian MTF (no pixel-aperture sinc).

    `edge_pos_frac` places the edge centre at that fraction of the ROI width
    (default 0.5 = centred); an off-centre value exercises the LSF-peak-centred
    window (code-review finding #4).
    """
    ny, nx = shape
    slope = np.tan(np.radians(angle_deg))
    x0 = nx * edge_pos_frac
    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    x_edge = x0 + slope * ys
    theta = np.arctan(slope)
    dist = (xs - x_edge) * np.cos(theta)  # signed perpendicular distance (px)
    step = 0.5 * (1.0 + erf(dist / (sigma_px * np.sqrt(2.0))))
    pixel = (low + (high - low) * step).astype(np.float32)
    if seed is not None:
        rng = np.random.default_rng(seed)
        pixel = pixel + rng.normal(0.0, 1.0, size=pixel.shape).astype(np.float32)
    return EdgePhantom(new_frame(pixel), angle_deg, sigma_px, pitch_mm, low, high)


# ---------------------------------------------------------------------------
# NPS: white / colored noise uniform frames -> analytic flat / shaped NPS.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NoisePhantom:
    frames: list
    mean_signal: float
    variance: float
    pitch_mm: float

    @property
    def flat_nps_level(self) -> float:
        """White-noise NPS level: var * dx * dy."""
        return self.variance * self.pitch_mm * self.pitch_mm

    @property
    def flat_nnps_level(self) -> float:
        return self.flat_nps_level / (self.mean_signal**2)


def make_white_noise_frames(
    shape: tuple[int, int] = (512, 512),
    n_frames: int = 16,
    mean_signal: float = 2000.0,
    sigma: float = 50.0,
    pitch_mm: float = 0.14,
    seed: int = 0,
) -> NoisePhantom:
    """Uniform frames of Gaussian white noise with a known variance."""
    rng = np.random.default_rng(seed)
    frames = [
        new_frame((mean_signal + rng.normal(0.0, sigma, size=shape)).astype(np.float32))
        for _ in range(n_frames)
    ]
    return NoisePhantom(frames, mean_signal, sigma**2, pitch_mm)


def make_colored_noise_frames(
    shape: tuple[int, int] = (512, 512),
    n_frames: int = 16,
    mean_signal: float = 2000.0,
    sigma: float = 50.0,
    pitch_mm: float = 0.14,
    seed: int = 1,
) -> NoisePhantom:
    """Uniform frames of low-pass (spatially correlated) noise.

    A 3x3 smoothing kernel injects positive spatial correlation, so the NPS is
    shaped low-pass (higher at DC than at Nyquist) — the shape check.
    """
    rng = np.random.default_rng(seed)
    kernel = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=np.float64)
    kernel /= kernel.sum()
    frames = []
    for _ in range(n_frames):
        white = rng.normal(0.0, sigma, size=shape)
        # Separable-ish smoothing via FFT convolution (wrap) for correlation.
        from scipy.ndimage import convolve

        colored = convolve(white, kernel, mode="wrap")
        frames.append(new_frame((mean_signal + colored).astype(np.float32)))
    return NoisePhantom(frames, mean_signal, sigma**2, pitch_mm)


def make_line_noise_frames(
    shape: tuple[int, int] = (256, 256),
    n_frames: int = 8,
    mean_signal: float = 2000.0,
    sigma: float = 20.0,
    line_period_px: int = 8,
    line_amp: float = 40.0,
    pitch_mm: float = 0.14,
    seed: int = 2,
) -> tuple[list, float]:
    """Uniform frames with an injected periodic column (vertical-line) pattern.

    Returns (frames, expected_column_peak_freq_lpmm).
    """
    rng = np.random.default_rng(seed)
    ny, nx = shape
    x = np.arange(nx)
    column_pattern = line_amp * np.sin(2.0 * np.pi * x / line_period_px)
    frames = []
    for _ in range(n_frames):
        img = mean_signal + rng.normal(0.0, sigma, size=shape) + column_pattern[None, :]
        frames.append(new_frame(img.astype(np.float32)))
    expected_freq = (1.0 / line_period_px) / pitch_mm
    return frames, expected_freq


# ---------------------------------------------------------------------------
# lag: exponential-sum IRF sequence + ghost residual frame.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LagPhantom:
    frames: list
    known_lag_pct: float
    offset: float
    exposed_amp: float


def make_lag_sequence(
    shape: tuple[int, int] = (32, 32),
    offset: float = 1000.0,
    exposed_amp: float = 4000.0,
    amps: tuple[float, ...] = (0.03, 0.02),
    taus: tuple[float, ...] = (1.0, 3.0),
    n_residual: int = 6,
) -> LagPhantom:
    """Exposure frame followed by an exponential-sum residual decay (M=2..4).

    residual[m] = offset + exposed_amp * sum_k a_k exp(-m / tau_k), m=1..N.
    first-frame lag % = (residual[1]-offset)/exposed_amp*100.
    """
    frames = [new_frame(np.full(shape, offset + exposed_amp, dtype=np.float32))]
    residual_amps = []
    for m in range(1, n_residual + 1):
        frac = sum(a * np.exp(-m / t) for a, t in zip(amps, taus))
        residual_amps.append(frac)
        frames.append(new_frame(np.full(shape, offset + exposed_amp * frac, dtype=np.float32)))
    # Append a settled dark frame so the baseline estimator sees the offset.
    frames.append(new_frame(np.full(shape, offset, dtype=np.float32)))
    known_lag_pct = residual_amps[0] * 100.0
    return LagPhantom(frames, known_lag_pct, offset, exposed_amp)


@dataclass(frozen=True)
class GhostPhantom:
    frame: object
    foreground_roi: tuple[int, int, int, int]
    background_roi: tuple[int, int, int, int]
    known_cnr: float


def make_ghost_frame(
    shape: tuple[int, int] = (64, 64),
    background: float = 1000.0,
    residual_delta: float = 50.0,
    noise_sigma: float = 10.0,
    seed: int = 3,
) -> GhostPhantom:
    """Uniform ghost frame with a residual foreground box (known CNR)."""
    rng = np.random.default_rng(seed)
    img = background + rng.normal(0.0, noise_sigma, size=shape)
    fg = (10, 10, 16, 16)
    bg = (40, 40, 16, 16)
    t, l, h, w = fg
    img[t : t + h, l : l + w] += residual_delta
    frame = new_frame(img.astype(np.float32))
    known_cnr = residual_delta / noise_sigma
    return GhostPhantom(frame, fg, bg, known_cnr)


# ---------------------------------------------------------------------------
# defect: dark/flat stacks with planted E2597 defects + ground-truth map.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DefectPhantom:
    dark_frames: list
    flat_frames: list
    truth_map: np.ndarray
    planted: dict


def make_defect_stacks(
    shape: tuple[int, int] = (32, 32),
    n_frames: int = 10,
    dark_level: float = 1000.0,
    gain: float = 3000.0,
    seed: int = 4,
) -> DefectPhantom:
    """Dark/flat stacks with one planted pixel of each of the 7 E2597 classes."""
    from metrics.defect_stats import DefectClass

    rng = np.random.default_rng(seed)
    ny, nx = shape
    dark = rng.normal(dark_level, 2.0, size=(n_frames, ny, nx))
    flat = dark + gain + rng.normal(0.0, 2.0, size=(n_frames, ny, nx))
    truth = np.full(shape, DefectClass.GOOD, dtype=np.int8)

    planted = {
        (2, 2): DefectClass.OVER_RANGE,
        (3, 3): DefectClass.UNDER_RANGE,
        (4, 4): DefectClass.NOISY,
        (5, 5): DefectClass.UNSTABLE,
        (6, 6): DefectClass.LAG,
        (7, 7): DefectClass.DEAD,
        (8, 8): DefectClass.NON_UNIFORM,
    }
    for (r, c), kind in planted.items():
        if kind == DefectClass.OVER_RANGE:
            flat[:, r, c] = 65535.0
        elif kind == DefectClass.UNDER_RANGE:
            flat[:, r, c] = 0.0
        elif kind == DefectClass.NOISY:
            flat[:, r, c] = dark_level + gain + rng.normal(0.0, 200.0, size=n_frames)
        elif kind == DefectClass.UNSTABLE:
            # Dark is temporally unstable; flat stays stable so this pixel is
            # UNSTABLE (dark std), not NOISY (flat std).
            dark[:, r, c] = dark_level + rng.normal(0.0, 50.0, size=n_frames)
            flat[:, r, c] = dark_level + gain
        elif kind == DefectClass.LAG:
            dark[:, r, c] = dark_level + 1000.0
            flat[:, r, c] = dark[:, r, c] + gain
        elif kind == DefectClass.DEAD:
            flat[:, r, c] = dark[:, r, c]  # no gain
        elif kind == DefectClass.NON_UNIFORM:
            flat[:, r, c] = dark[:, r, c] + 1.5 * gain
        truth[r, c] = kind

    dark_frames = [new_frame(dark[i].astype(np.float32)) for i in range(n_frames)]
    flat_frames = [new_frame(flat[i].astype(np.float32)) for i in range(n_frames)]
    return DefectPhantom(dark_frames, flat_frames, truth, planted)


# ---------------------------------------------------------------------------
# NDT: duplex-wire profile with controlled dips + uniform SNR frame.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DuplexPhantom:
    profile: np.ndarray
    pairs: list
    known_srb_um: float
    known_first_unresolved: int


def make_duplex_profile() -> DuplexPhantom:
    """Profile of three wire pairs: two resolved, the third unresolved (<20%)."""
    profile = np.full(200, 1000.0, dtype=np.float64)
    pairs = []
    # (peak1, valley, peak2, srb_um, valley_value)
    specs = [
        (10, 15, 20, 260.0, 400.0),  # dip 0.6 resolved
        (60, 65, 70, 180.0, 700.0),  # dip 0.3 resolved
        (110, 115, 120, 130.0, 920.0),  # dip 0.08 unresolved
    ]
    for p1, v, p2, srb, valley in specs:
        profile[p1] = 1000.0
        profile[p2] = 1000.0
        profile[v] = valley
        pairs.append(WirePair(peak1_index=p1, valley_index=v, peak2_index=p2, srb_um=srb))
    return DuplexPhantom(profile, pairs, known_srb_um=130.0, known_first_unresolved=2)


def make_flat_duplex_profile() -> DuplexPhantom:
    """Flat profile: no resolvable dip -> read failure (EC-5)."""
    profile = np.full(200, 1000.0, dtype=np.float64)
    pairs = [
        WirePair(peak1_index=10, valley_index=15, peak2_index=20, srb_um=260.0),
        WirePair(peak1_index=60, valley_index=65, peak2_index=70, srb_um=180.0),
    ]
    return DuplexPhantom(profile, pairs, known_srb_um=float("nan"), known_first_unresolved=-1)


@dataclass(frozen=True)
class UniformPhantom:
    frame: object
    roi: tuple[int, int, int, int]
    known_snr: float
    mean: float
    sigma: float


def make_uniform_snr_frame(
    shape: tuple[int, int] = (128, 128),
    mean: float = 2000.0,
    sigma: float = 20.0,
    seed: int = 5,
) -> UniformPhantom:
    """Uniform frame with injected mean/sigma -> known SNR = mean/sigma."""
    rng = np.random.default_rng(seed)
    img = mean + rng.normal(0.0, sigma, size=shape)
    frame = new_frame(img.astype(np.float32))
    roi = (16, 16, 96, 96)
    return UniformPhantom(frame, roi, known_snr=mean / sigma, mean=mean, sigma=sigma)


# ---------------------------------------------------------------------------
# NDT T9 (SPEC-NDT-001): Welford streaming sequence, real-time SNRn sequence,
# single-wire IQI profile, thickness step-wedge (edge + gradient + defect).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WelfordPhantom:
    """Frame sequence + the full stack for the batch reference."""

    frames: list  # list of 2D float64 arrays fed one-by-one to the accumulator
    stack: np.ndarray  # (n_frames, Ny, Nx) for temporal_mean_std batch reference


def make_welford_sequence(
    shape: tuple[int, int] = (16, 24),
    mean: float = 1500.0,
    sigma: float = 25.0,
    n_frames: int = 12,
    seed: int = 7,
) -> WelfordPhantom:
    """Independent noisy frames; the accumulator must match the batch stack.

    Returns the per-frame 2D arrays (streamed one at a time, whole stack never
    held by the accumulator) and the full stack for the batch reference
    (``temporal_mean_std``). float64 so the equivalence is a pure numerics gate.
    """
    rng = np.random.default_rng(seed)
    stack = mean + rng.normal(0.0, sigma, size=(n_frames,) + shape)
    frames = [stack[i].copy() for i in range(n_frames)]
    return WelfordPhantom(frames, stack)


@dataclass(frozen=True)
class SnrnSeqPhantom:
    frames: list  # XFrames of a uniform ROI region, streamed one at a time
    roi: tuple[int, int, int, int]
    known_snr1: float  # single-frame SNR = mean / sigma
    srb_um: float  # known SRb for the SNRn normalization
    mean: float
    sigma: float
    n_frames: int

    def known_snr(self, k: int) -> float:
        """Averaging k independent frames reduces noise by sqrt(k)."""
        return self.known_snr1 * float(np.sqrt(k))

    def known_snrn(self, k: int, norm_um: float = 88.6) -> float:
        return self.known_snr(k) * norm_um / self.srb_um


def make_snrn_sequence(
    shape: tuple[int, int] = (112, 112),
    mean: float = 2000.0,
    sigma: float = 25.0,
    n_frames: int = 16,
    srb_um: float = 150.0,
    seed: int = 11,
) -> SnrnSeqPhantom:
    """Sequence of independent uniform frames -> known SNR(k) = (mean/sigma)*sqrt(k).

    As the accumulator averages more frames the temporal noise drops as
    1/sqrt(k), so the running spatial SNR grows as sqrt(k) — an analytic known
    progression the streaming SNRn must reproduce.
    """
    rng = np.random.default_rng(seed)
    frames = [
        new_frame((mean + rng.normal(0.0, sigma, size=shape)).astype(np.float32))
        for _ in range(n_frames)
    ]
    roi = (8, 8, 96, 96)
    return SnrnSeqPhantom(
        frames, roi, known_snr1=mean / sigma, srb_um=srb_um, mean=mean, sigma=sigma,
        n_frames=n_frames,
    )


@dataclass(frozen=True)
class SingleWirePhantom:
    profile: np.ndarray
    wires: list  # WireElement(number, index)
    known_min_visible_wire: int  # finest (highest-numbered) still-visible wire
    visibility_threshold: float


def make_single_wire_iqi(
    background: float = 1000.0,
    visibility_threshold: float = 0.20,
) -> SingleWirePhantom:
    """Single-wire (ISO 19232 wire-type) IQI: dips of decreasing contrast.

    Wires 10..16 have contrasts 0.50..0.03. At the 0.20 visibility threshold
    wires 10,11,12,13 are visible (contrast >= 0.20) and 14,15,16 are not, so
    the finest visible wire is 13.
    """
    n = 220
    profile = np.full(n, background, dtype=np.float64)
    # (wire number, sample index, dip contrast)
    specs = [
        (10, 20, 0.50),
        (11, 50, 0.40),
        (12, 80, 0.30),
        (13, 110, 0.22),
        (14, 140, 0.12),
        (15, 170, 0.06),
        (16, 200, 0.03),
    ]
    wires = []
    for number, index, contrast in specs:
        profile[index] = background * (1.0 - contrast)
        wires.append(WireElement(number=number, index=index))
    visible = [num for num, _, c in specs if c >= visibility_threshold]
    return SingleWirePhantom(
        profile, wires, known_min_visible_wire=max(visible),
        visibility_threshold=visibility_threshold,
    )


@dataclass(frozen=True)
class ThicknessEdgePhantom:
    """Edge on a smooth thickness gradient — for MTF@Nyquist / SRb protection."""

    frame: object  # XFrame (edge + cosine gradient + noise)
    band: tuple  # (row slice, col slice) narrow cross-edge ROI for MTF
    pitch_mm: float


def make_thickness_edge_phantom(
    shape: tuple[int, int] = (128, 128),
    angle_deg: float = 2.0,
    sigma_px: float = 0.6,
    low: float = 2000.0,
    high: float = 6000.0,
    grad_amp: float = 3000.0,
    noise_sigma: float = 4.0,
    pitch_mm: float = 0.14,
    seed: int = 19,
) -> ThicknessEdgePhantom:
    """Near-vertical edge + smooth (cosine) low-frequency thickness gradient.

    The gradient varies only along y (orthogonal to the near-vertical edge). A
    large-scale low-pass subtraction must flatten the gradient while preserving
    the edge's high-frequency transition (measured on the narrow cross-edge
    band).
    """
    ny, nx = shape
    slope = np.tan(np.radians(angle_deg))
    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    dist = (xs - (nx * 0.5 + slope * ys)) * np.cos(np.arctan(slope))
    edge = low + (high - low) * 0.5 * (1.0 + erf(dist / (sigma_px * np.sqrt(2.0))))
    grad = grad_amp * (0.5 - 0.5 * np.cos(np.pi * ys / (ny - 1)))
    rng = np.random.default_rng(seed)
    img = edge + grad + rng.normal(0.0, noise_sigma, size=shape)
    band = (slice(16, 112), slice(52, 76))
    return ThicknessEdgePhantom(new_frame(img.astype(np.float32)), band, pitch_mm)


@dataclass(frozen=True)
class ThicknessDefectPhantom:
    """Linear thickness ramp + injected high-frequency defect + noise."""

    frame: object  # XFrame
    defect_center: tuple[int, int]
    known_defect_amp: float
    flat_roi: tuple  # (row slice, col slice) defect-free flat region (CSa)
    signal_level: float  # known signal level in the flat region (CSa denominator)

    def defect_amplitude(self, image: np.ndarray) -> float:
        r, c = self.defect_center
        patch = image[r - 4 : r + 5, c - 4 : c + 5]
        base = np.median(
            np.concatenate(
                [
                    image[r - 4 : r + 5, c - 8 : c - 4].ravel(),
                    image[r - 4 : r + 5, c + 5 : c + 9].ravel(),
                ]
            )
        )
        return float(patch.max() - base)


def make_thickness_defect_phantom(
    shape: tuple[int, int] = (128, 128),
    base: float = 2000.0,
    grad_amp: float = 3000.0,
    defect_amp: float = 300.0,
    defect_sigma_px: float = 0.9,
    noise_sigma: float = 4.0,
    seed: int = 23,
) -> ThicknessDefectPhantom:
    """Linear vertical thickness ramp with a small high-frequency defect bump.

    A linear ramp has zero curvature, so a low-pass estimate removes it down to
    the noise floor in the interior — giving a clean CSa (residual-noise/signal)
    proxy — while the tight defect bump (high frequency) survives.
    """
    ny, nx = shape
    ys, xs = np.mgrid[0:ny, 0:nx].astype(np.float64)
    grad = base + grad_amp * (ys / (ny - 1))
    dr, dc = 64, 96
    defect = defect_amp * np.exp(
        -(((ys - dr) ** 2 + (xs - dc) ** 2) / (2.0 * defect_sigma_px**2))
    )
    rng = np.random.default_rng(seed)
    img = grad + defect + rng.normal(0.0, noise_sigma, size=shape)
    flat_roi = (slice(40, 88), slice(30, 66))
    signal_level = float(np.median(grad[flat_roi]))
    return ThicknessDefectPhantom(
        new_frame(img.astype(np.float32)),
        defect_center=(dr, dc),
        known_defect_amp=defect_amp,
        flat_roi=flat_roi,
        signal_level=signal_level,
    )


def make_flat_frame(
    shape: tuple[int, int] = (128, 128),
    level: float = 3000.0,
    noise_sigma: float = 4.0,
    seed: int = 31,
) -> object:
    """Gradient-free uniform frame (EC-2: no low-frequency gradient present)."""
    rng = np.random.default_rng(seed)
    img = level + rng.normal(0.0, noise_sigma, size=shape)
    return new_frame(img.astype(np.float32))
