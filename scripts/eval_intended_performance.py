"""XDET P1 INTENDED-PERFORMANCE evaluation harness (synthetic phantoms only).

For each golden metric this harness:
  1. Generates the EXISTING synthetic phantom (with a KNOWN injected physical
     value) — never touches real acquisition data (images/에드로지16BIT is
     QUARANTINED and is not read here).
  2. Runs the REAL metric engine exactly as the pytest suite wires it.
  3. Computes the ACTUAL reproduced value and reports:
        target | achieved | abs error | rel error | declared [T] tolerance |
        margin (error as a fraction of tolerance) | PASS/MARGINAL verdict.

It reuses the project's phantom generators (tests/metrics/phantoms,
tests/modules/phantoms) and metric engines (metrics/*, modules/*) — no physics
is reinvented. If a metric cannot be wired it is reported as NOT MEASURED with a
reason rather than fabricating a number.

Run:  uv run python scripts/eval_intended_performance.py
"""

from __future__ import annotations

import os
import sys
import traceback

import numpy as np

# Make the repo root importable (common/, metrics/, modules/, tests/ are packages).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Windows consoles default to cp949 here; force UTF-8 so report glyphs survive.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - best-effort; ASCII fallback below
        pass


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

_GOLDEN_ROWS: list[dict] = []
_EV_ROWS: list[dict] = []
_NOT_MEASURED: list[tuple[str, str]] = []


def _fmt(x) -> str:
    if isinstance(x, str):
        return x
    if x is None:
        return "-"
    ax = abs(x)
    if x != 0 and (ax < 1e-3 or ax >= 1e5):
        return f"{x:.3e}"
    return f"{x:.4g}"


def add_golden(
    metric: str,
    ident: str,
    target,
    achieved,
    tol: float,
    tol_kind: str,  # "abs" or "rel"
    *,
    bounded: float | None = None,
    abs_err: float | None = None,
    rel_err: float | None = None,
):
    """Register one golden-reproduction row.

    bounded = the error quantity that is actually compared against `tol`
    (defaults to abs_err for tol_kind=="abs", rel_err for "rel").
    """
    if abs_err is None and isinstance(target, (int, float)) and isinstance(achieved, (int, float)):
        abs_err = abs(achieved - target)
    if rel_err is None and abs_err is not None and isinstance(target, (int, float)) and target != 0:
        rel_err = abs_err / abs(target)
    if bounded is None:
        bounded = abs_err if tol_kind == "abs" else rel_err
    # Ratio = error as a fraction of tolerance. For an exact-match metric (tol==0)
    # a zero error is a perfect PASS (ratio 0); any nonzero error is FAIL (inf).
    if bounded is None:
        ratio = float("inf")
    elif tol and tol > 0:
        ratio = bounded / tol
    else:  # tol == 0 (exact-match gate)
        ratio = 0.0 if bounded == 0 else float("inf")
    if bounded is None:
        verdict = "?"
    elif ratio <= 0.75:
        verdict = "PASS"
    elif ratio <= 1.0:
        verdict = "MARGINAL"
    else:
        verdict = "FAIL"
    _GOLDEN_ROWS.append(
        dict(
            metric=metric, ident=ident, target=target, achieved=achieved,
            abs_err=abs_err, rel_err=rel_err, tol=tol, tol_kind=tol_kind,
            bounded=bounded, ratio=ratio, verdict=verdict,
        )
    )


def add_ev(metric: str, ident: str, achieved, bar, direction: str, note: str = ""):
    """Register one EV-threshold-gated row (clears / does not clear a min/max bar).

    direction: ">=" (achieved must be at least bar) or "<=" (at most bar).
    """
    if direction == ">=":
        clears = achieved >= bar
    else:
        clears = achieved <= bar
    _EV_ROWS.append(
        dict(metric=metric, ident=ident, achieved=achieved, bar=bar,
             direction=direction, clears=clears, note=note)
    )


def not_measured(metric: str, reason: str):
    _NOT_MEASURED.append((metric, reason))


def safe(metric: str, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - harness must not abort on one metric
        not_measured(metric, f"{type(exc).__name__}: {exc}")
        # Keep a short traceback tail for diagnosis (stderr only).
        tb = traceback.format_exc().strip().splitlines()
        sys.stderr.write(f"[NOT MEASURED] {metric}\n  " + "\n  ".join(tb[-3:]) + "\n")


# ---------------------------------------------------------------------------
# GOLDEN metric measurements
# ---------------------------------------------------------------------------


def m_mtf():
    from metrics import mtf
    from tests.metrics.phantoms import generators as gen
    from tests.metrics.phantoms.params import TOLERANCES, make_params

    params = make_params()
    ph = gen.make_slanted_edge(angle_deg=2.0, sigma_px=0.6)
    res = mtf.compute_mtf(ph.frame, params)
    freqs = res.get("frequencies_lpmm")
    got = res.get("mtf")
    nyq = res.get("nyquist_lpmm")
    band = freqs <= nyq
    expected = ph.analytic_mtf(freqs)
    max_curve_err = float(np.max(np.abs(got[band] - expected[band])))
    add_golden(
        "MTF curve (edge, Gaussian sigma=0.6px)", "MTF / Scen2",
        "analytic MTF(f)", f"max|Δ|={_fmt(max_curve_err)}",
        TOLERANCES["mtf_abs"], "abs",
        bounded=max_curve_err, abs_err=max_curve_err,
        rel_err=None,
    )
    # MTF @ Nyquist (separate, looser tolerance).
    ph2 = gen.make_slanted_edge(angle_deg=2.2, sigma_px=0.6)
    res2 = mtf.compute_mtf(ph2.frame, params)
    nyq2 = res2.get("nyquist_lpmm")
    exp_nyq = float(ph2.analytic_mtf(np.array([nyq2]))[0])
    got_nyq = float(res2.get("mtf_at_nyquist"))
    add_golden(
        "MTF @ Nyquist (3.57 lp/mm)", "MTF@Nyq / Scen2",
        exp_nyq, got_nyq, TOLERANCES["mtf_nyquist_abs"], "abs",
    )


def m_nps():
    from metrics import nps
    from tests.metrics.phantoms import generators as gen
    from tests.metrics.phantoms.params import TOLERANCES, make_params

    def midband(freqs, values, nyq):
        b = (freqs > 0.2 * nyq) & (freqs < 0.8 * nyq)
        return float(np.mean(values[b]))

    ph = gen.make_white_noise_frames()  # sigma=50 -> var=2500
    res = nps.compute_nps(ph.frames, make_params())
    freqs = res.get("frequencies_lpmm")
    nyq = 1.0 / (2.0 * 0.14)
    nps_level = midband(freqs, res.get("nps"), nyq)
    add_golden(
        "NPS flat level (white noise var*dx*dy)", "NPS / Scen3",
        ph.flat_nps_level, nps_level, TOLERANCES["nps_rel"], "rel",
    )
    nnps_level = midband(freqs, res.get("nnps"), nyq)
    add_golden(
        "NNPS flat level (NPS / mean^2)", "NNPS / Scen3",
        ph.flat_nnps_level, nnps_level, TOLERANCES["nnps_rel"], "rel",
    )


def m_dqe():
    from metrics import dqe, nps
    from tests.metrics.phantoms.params import TOLERANCES, make_params
    from common.xframe import new_frame

    def ideal_frames(fluence_per_mm2, pitch_mm, shape, n_frames, seed):
        rng = np.random.default_rng(seed)
        n_mean = fluence_per_mm2 * (pitch_mm * pitch_mm)
        return [new_frame(rng.poisson(n_mean, size=shape).astype(np.float32)) for _ in range(n_frames)]

    def ideal_dqe_mid(params, pitch_mm, seed):
        q = params.get("dqe_q")
        ka = params.get("dqe_ka")
        frames = ideal_frames(q * ka, pitch_mm, (512, 512), 24, seed)
        nres = nps.compute_nps(frames, params)
        freqs = nres.get("frequencies_lpmm")
        nnps = nres.get("nnps")
        mtf_ideal = np.ones_like(freqs)
        res = dqe.compute_dqe(freqs, mtf_ideal, nnps, params)
        got = res.get("dqe")
        nyq = 1.0 / (2.0 * pitch_mm)
        b = (freqs > 0.2 * nyq) & (freqs < 0.8 * nyq)
        return float(np.mean(got[b]))

    params = make_params()
    pitch = params.get("pixel_pitch_mm")
    dqe_mid = ideal_dqe_mid(params, pitch, seed=0)
    add_golden(
        "DQE mid-band (ideal Poisson detector)", "DQE / Scen3",
        1.0, dqe_mid, TOLERANCES["dqe_ideal_abs"], "abs",
    )
    dqe_1x = ideal_dqe_mid(make_params(), pitch, seed=1)
    dqe_2x = ideal_dqe_mid(make_params(dqe_ka=params.get("dqe_ka") * 2.0), pitch, seed=2)
    dev = abs(dqe_1x - dqe_2x)
    add_golden(
        "DQE dose invariance |DQE(1x)-DQE(2x)|", "DQE 1x/2x",
        0.0, dev, TOLERANCES["dqe_ideal_abs"], "abs",
        bounded=dev, abs_err=dev, rel_err=None,
    )
    # Annotate the actual 1x / 2x values on stderr for the report.
    sys.stderr.write(f"[DQE] mid={dqe_mid:.4f} 1x={dqe_1x:.4f} 2x={dqe_2x:.4f}\n")


def m_lag():
    from metrics import lag
    from tests.metrics.phantoms import generators as gen
    from tests.metrics.phantoms.params import TOLERANCES, make_params

    ph = gen.make_lag_sequence()
    res = lag.compute_first_frame_lag(ph.frames, make_params())
    got = float(res.get("first_frame_lag_pct"))
    add_golden(
        "First-frame lag % (exp-sum IRF)", "LAG / Scen5",
        ph.known_lag_pct, got, TOLERANCES["lag_rel"], "rel",
    )


def m_ghost():
    from metrics import lag
    from tests.metrics.phantoms import generators as gen
    from tests.metrics.phantoms.params import TOLERANCES, make_params

    ph = gen.make_ghost_frame()
    res = lag.compute_ghost_cnr(ph.frame, ph.foreground_roi, ph.background_roi, make_params())
    got = float(res.get("ghost_cnr"))
    add_golden(
        "Ghost CNR (Δ/σ)", "Ghost / Scen8",
        ph.known_cnr, got, TOLERANCES["ghost_cnr_rel"], "rel",
    )


def m_irf():
    from modules.lag import K_IRF_A, K_IRF_B
    from metrics.lag_irf import StepResponse, fit_lag_irf
    from tests.modules.phantoms.lag_seq import IRF_A, IRF_B

    def synth_residual(amp, a, b, n=12):
        m = np.arange(1, n + 1, dtype=np.float64)
        a_arr = np.asarray(a)[:, None]
        b_arr = np.asarray(b)[:, None]
        return amp * (a_arr * b_arr ** m[None, :]).sum(axis=0)

    responses = [
        StepResponse(amplitude=amp, residual=synth_residual(amp, IRF_A, IRF_B))
        for amp in (1000.0, 2500.0, 4000.0)
    ]
    calib = fit_lag_irf(
        responses, m_terms=3, panel_id="PANEL-A", resolution=(8, 8),
        valid_from="2026-01-01", valid_until="2027-01-01",
    )
    a_fit = np.asarray(calib.data[K_IRF_A], dtype=np.float64)
    b_fit = np.asarray(calib.data[K_IRF_B], dtype=np.float64)
    m = np.arange(1, 13, dtype=np.float64)
    known = (np.asarray(IRF_A)[:, None] * np.asarray(IRF_B)[:, None] ** m[None, :]).sum(0)
    got = (a_fit[:, None] * b_fit[:, None] ** m[None, :]).sum(0)
    max_dev = float(np.max(np.abs(got - known)))
    add_golden(
        "IRF fit reconstruction (a,b -> curve)", "LAG-IRF / Scen6",
        "known afterglow curve", f"max|Δ|={_fmt(max_dev)}",
        1e-4, "abs", bounded=max_dev, abs_err=max_dev, rel_err=None,
    )


def m_defect():
    from metrics import defect_stats
    from metrics.defect_stats import DefectClass
    from tests.metrics.phantoms import generators as gen
    from tests.metrics.phantoms.params import make_params

    ph = gen.make_defect_stacks()
    res = defect_stats.classify_defects(
        ph.dark_frames, ph.flat_frames, make_params(), truth_map=ph.truth_map
    )
    class_map = res.get("class_map")
    correct = sum(1 for (r, c), kind in ph.planted.items() if class_map[r, c] == kind)
    miss_rate = float(res.get("miss_rate"))
    add_golden(
        f"Bad-pixel E2597 miss-rate ({correct}/{len(ph.planted)} classes ok)",
        "Defect / Scen6",
        0.0, miss_rate, 0.0, "abs",
        bounded=miss_rate, abs_err=miss_rate, rel_err=None,
    )


def m_srb_snrn():
    from metrics import ndt
    from tests.metrics.phantoms import generators as gen
    from tests.metrics.phantoms.params import TOLERANCES, make_params

    params = make_params()
    duplex = gen.make_duplex_profile()
    srb = float(ndt.read_duplex_srb(duplex.profile, duplex.pairs, params).get("srb_um"))
    add_golden(
        "Duplex-wire SRb (first unresolved pair)", "SRb / Scen7",
        duplex.known_srb_um, srb, 1e-9, "abs",
        bounded=abs(srb - duplex.known_srb_um), abs_err=abs(srb - duplex.known_srb_um),
        rel_err=None,
    )
    uni = gen.make_uniform_snr_frame()
    res = ndt.compute_snrn(uni.frame, uni.roi, srb, params)
    expected_snrn = uni.known_snr * 88.6 / srb
    got = float(res.get("snrn"))
    add_golden(
        "SNRn = SNR*88.6/SRb", "SNRn / Scen7",
        expected_snrn, got, TOLERANCES["snrn_rel"], "rel",
    )


def m_single_wire():
    from metrics.ndt import read_single_wire_iqi
    from tests.metrics.phantoms import generators as gen
    from tests.metrics.phantoms.params import make_params

    ph = gen.make_single_wire_iqi()
    res = read_single_wire_iqi(ph.profile, ph.wires, make_params())
    got = int(res.get("min_visible_wire"))
    err = abs(got - ph.known_min_visible_wire)
    add_golden(
        "Single-wire IQI min-visible-wire", "IQI-wire",
        ph.known_min_visible_wire, got, 0.0, "abs",
        bounded=float(err), abs_err=float(err), rel_err=None,
    )


def m_welford():
    from common.robust_stats import WelfordAccumulator, temporal_mean_std
    from tests.metrics.phantoms import generators as gen
    from tests.metrics.phantoms.params import TOLERANCES

    ph = gen.make_welford_sequence()
    acc = WelfordAccumulator()
    for frame in ph.frames:
        acc.update(frame)
    batch_mean, batch_std = temporal_mean_std(ph.stack)
    mean_dev = float(np.max(np.abs(acc.mean - batch_mean)))
    std_dev = float(np.max(np.abs(acc.std(ddof=0) - batch_std)))
    worst = max(mean_dev, std_dev)
    add_golden(
        "Welford online == batch mean/std", "Welford",
        "batch temporal_mean_std", f"max|Δ|={_fmt(worst)}",
        TOLERANCES["welford_atol"], "abs",
        bounded=worst, abs_err=worst, rel_err=None,
    )


def m_streaming_snrn():
    from metrics.ndt import SNRnAccumulator
    from tests.metrics.phantoms import generators as gen
    from tests.metrics.phantoms.params import TOLERANCES, make_params

    seq = gen.make_snrn_sequence()
    acc = SNRnAccumulator(seq.roi, seq.srb_um, make_params())
    for frame in seq.frames:
        acc.update(frame)
    rels = []
    for k in (1, 4, 9, 16):
        entry = acc.shot_log[k - 1]
        expected = seq.known_snrn(k, norm_um=88.6)
        rels.append(abs(entry.snrn - expected) / expected)
    worst = float(max(rels))
    add_golden(
        "Streaming SNRn sqrt(k) progression", "SNRn-stream",
        "(mean/sigma)*sqrt(k)*88.6/SRb", f"max rel={_fmt(worst)}",
        TOLERANCES["snrn_progression_rel"], "rel",
        bounded=worst, rel_err=worst, abs_err=None,
    )


def m_noise_model():
    from metrics.noise_model import DoseLevel, fit_noise_model
    from common.calibset import K_NOISE_ALPHA, K_NOISE_SIGMA
    from tests.modules.phantoms.denoise_syn import ALPHA, SIGMA, sample_pg

    def dose_levels(levels, shape=(96, 96), seed=1, n_frames=8):
        rng = np.random.default_rng(seed)
        out = []
        for lvl in levels:
            frames = np.stack([sample_pg(np.full(shape, lvl), ALPHA, SIGMA, rng) for _ in range(n_frames)])
            out.append(DoseLevel(frames=frames))
        return out

    calib = fit_noise_model(
        dose_levels([20.0, 50.0, 100.0, 200.0, 400.0]),
        panel_id="PANEL-A", resolution=(96, 96),
        valid_from="2026-01-01", valid_until="2027-01-01",
    )
    alpha = float(np.asarray(calib.data[K_NOISE_ALPHA]))
    sigma = float(np.asarray(calib.data[K_NOISE_SIGMA]))
    add_golden("Noise-model alpha (var=alpha*mu+sigma^2)", "Noise-a / Scen10",
               ALPHA, alpha, 0.10, "rel")
    add_golden("Noise-model sigma (read noise)", "Noise-s / Scen10",
               SIGMA, sigma, 0.15, "rel")


def m_vst():
    from modules import denoise
    from tests.modules.phantoms.denoise_syn import ALPHA, EPS_UNBIAS, LAMBDA_FLOOR, SIGMA, sample_pg

    lambdas = [1.0, 2.0, 3.0, 5.0, 10.0, 30.0, 80.0, 200.0]
    patch = 100_000
    rng = np.random.default_rng(0)
    lut = denoise._build_inverse_lut(ALPHA, SIGMA, 300.0, 2048, 32)
    m_grid, lam_grid = lut
    norm_bias = []
    for lam in lambdas:
        z = sample_pg(np.full(patch, lam), ALPHA, SIGMA, rng)
        f, _ = denoise._gat_forward(z, ALPHA, SIGMA)
        d = float(f.mean())
        exact = float(denoise._gat_inverse(np.array([d]), m_grid, lam_grid)[0])
        norm_bias.append(abs(exact - lam) / max(lam, LAMBDA_FLOOR))
    worst = float(max(norm_bias))
    add_golden(
        "VST round-trip unbiasedness (exact inverse)", "VST-RT / TC-011",
        "lambda (swept 1..200)", f"max norm-bias={_fmt(worst)}",
        EPS_UNBIAS, "abs", bounded=worst, abs_err=worst, rel_err=None,
    )


def m_scatter():
    from modules import virtual_grid as vg
    from tests.modules.phantoms.scatter_syn import (
        EV, KERNEL_AMP, KERNEL_SIGMA_DOWN, make_smooth_scatter_phantom,
    )

    _, observed, s_inj = make_smooth_scatter_phantom((96, 96))
    s_hat = vg.estimate_scatter(observed, KERNEL_AMP, KERNEL_SIGMA_DOWN, 3, 3)
    rel_err = float(np.linalg.norm(s_hat - s_inj) / np.linalg.norm(s_inj))
    add_golden(
        "Virtual-grid scatter estimate S_hat vs S_inj", "Scatter-S / TC-017",
        "injected S_inj", f"rel L2={_fmt(rel_err)}",
        EV["scatter_rel_err_tol"], "rel",
        bounded=rel_err, rel_err=rel_err, abs_err=None,
    )


def m_grid_freq():
    from modules import grid
    from tests.modules.phantoms.grid_syn import (
        F_GRID_ALIASED, F_GRID_BELOW, F_GRID_NEAR, fold_frequency, grid_params, make_grid_phantom,
    )

    classes = [("below", F_GRID_BELOW), ("near", F_GRID_NEAR), ("aliased", F_GRID_ALIASED)]
    for name, f_grid in classes:
        _, img = make_grid_phantom((128, 128), f_grid, direction="vertical")
        analysis = grid.analyze(img, grid_params())
        if not analysis.detected:
            add_golden(f"Grid freq detect [{name}]", "Grid-freq / TC-015",
                       fold_frequency(f_grid), "NOT DETECTED", 0.12, "abs",
                       bounded=float("inf"), abs_err=float("inf"), rel_err=None)
            continue
        observed = float(analysis.peaks[0].freq_lpmm)
        expected = float(fold_frequency(f_grid))
        add_golden(
            f"Grid freq detect [{name}] (observed peak)", "Grid-freq / TC-015",
            expected, observed, 0.12, "abs",
        )


def m_gsdf():
    from modules import window
    from tests.modules.phantoms.post_syn import EV

    _, _, max_dev = window.build_gsdf_lut(4096, 0.5, 400.0, 8192)
    max_dev = float(max_dev)
    add_golden(
        "GSDF PS3.14 per-JND conformance deviation", "GSDF / TC-014",
        0.0, max_dev, EV["eps_gsdf"], "abs",
        bounded=max_dev, abs_err=max_dev, rel_err=None,
    )


# ---------------------------------------------------------------------------
# EV-THRESHOLD-gated measurements (clears an externally-set minimum, NOT a
# known-value reproduction).
# ---------------------------------------------------------------------------


def ev_denoise_snr():
    from common.xframe import new_frame
    from metrics import ndt
    from modules import denoise
    from tests.metrics.phantoms.params import make_params
    from tests.modules.phantoms.denoise_syn import EV, denoise_params, make_uniform_field, noise_calib

    clean, noisy = make_uniform_field((96, 96), level=400.0)
    calib = noise_calib((96, 96))
    params = denoise_params(
        k_s=0.8, denoise_inv_lut_nodes=1024, denoise_inv_lut_gh_nodes=16,
        denoise_inv_lut_lambda_max=3000.0,
    )
    out = denoise.process(new_frame(noisy.astype(np.float32)), calib, params)
    roi = (16, 16, 64, 64)
    mp = make_params()
    before, *_ = ndt.compute_snr(new_frame(noisy.astype(np.float32)), roi, mp)
    after, *_ = ndt.compute_snr(out, roi, mp)
    improvement = after / before - 1.0
    add_ev("Denoise SNR improvement (BM3D k_s=0.8)", "EV-201 / TC-010",
           improvement, EV["ev201_snr_improve_min_frac"], ">=",
           note=f"SNR {before:.2f}->{after:.2f}")


def ev_grid_suppression():
    from modules import grid
    from tests.modules.phantoms.grid_syn import (
        EV, F_GRID_BELOW, F_NYQUIST, fold_frequency, grid_params, make_frame, make_grid_phantom, other_calib,
    )

    params = grid_params()
    _, img = make_grid_phantom((128, 128), F_GRID_BELOW, direction="vertical")
    analysis = grid.analyze(img, params)
    gain_nyq = float(grid.notch_gain_1d([F_NYQUIST], analysis.peaks, params)[0])
    add_ev("Grid MTF@Nyquist retention (notch gain)", "EV-102 / TC-015",
           gain_nyq, EV["ev102_mtf_retention_min"], ">=")
    # Residual grid-line significance after suppression.
    out = grid.process(make_frame(img), other_calib((128, 128)), params)
    after = grid.analyze(np.asarray(out.pixel), params)
    expected = fold_frequency(F_GRID_BELOW)
    residual = [p for p in after.peaks if abs(p.freq_lpmm - expected) < 0.15]
    worst_db = max((p.significance_db for p in residual), default=0.0)
    add_ev("Grid residual peak significance (post-notch)", "EV residual_db / TC-015",
           float(worst_db), EV["residual_db"], "<=",
           note="0 dB = no residual peak at the suppressed freq")


def ev_mse_iqa():
    from common import pyramid
    from modules import mse
    from tests.modules.phantoms.post_syn import (
        EV, make_bone_soft_phantom, make_noise_frame, mse_params, other_calib,
    )

    clean, noisy = make_bone_soft_phantom(shape=(96, 96), detail_amp=400.0, seed=11)
    out = mse.process(make_noise_frame(noisy), other_calib(noisy.shape), mse_params())
    op = np.asarray(out.pixel, np.float64)

    def detail_rms(a):
        a = (a - a.mean()) / a.std()
        bands = pyramid.build_pyramid(a, 3)[:-1]
        return float(np.sqrt(np.mean([np.mean(b ** 2) for b in bands])))

    local_gain = detail_rms(op) / detail_rms(np.asarray(noisy, np.float64))
    out_clean = mse.process(make_noise_frame(clean), other_calib(clean.shape), mse_params())
    oc = np.asarray(out_clean.pixel, np.float64)
    oc = (oc - oc.mean()) / oc.std()
    cn = (clean - clean.mean()) / clean.std()
    e_in = sum(float(np.sum(b ** 2)) for b in pyramid.build_pyramid(cn, 3)[:-1])
    e_out = sum(float(np.sum(b ** 2)) for b in pyramid.build_pyramid(oc, 3)[:-1])
    retention = e_out / e_in
    add_ev("MSE-DRC local contrast gain", "EV local_contrast / TC-012",
           float(local_gain), EV["local_contrast_min_gain"], ">=")
    add_ev("MSE-DRC detail-energy retention", "EV detail_energy / TC-012",
           float(retention), EV["detail_energy_retention_min"], ">=")


def ev_vgrid_cnr():
    from modules import virtual_grid as vg
    from tests.modules.phantoms.scatter_syn import EV, cnr, make_cnr_phantom, make_frame, scatter_calib, vgrid_params

    _, observed, _, feat_roi, bg_roi = make_cnr_phantom((96, 96))
    out = vg.process(make_frame(observed), scatter_calib((96, 96)), vgrid_params())
    corrected = np.asarray(out.pixel, dtype=np.float64)
    cnr_before = cnr(observed, feat_roi, bg_roi)
    cnr_after = cnr(corrected, feat_roi, bg_roi)
    improvement = cnr_after / cnr_before - 1.0
    add_ev("Virtual-grid CNR improvement", "EV-202 / TC-017",
           float(improvement), EV["ev202_cnr_improvement_min"], ">=",
           note=f"CNR {cnr_before:.3f}->{cnr_after:.3f}")


def ev_geometry_residual():
    from common.xframe import new_frame
    from modules import geometry
    from tests.modules.phantoms.linesat import (
        EV_LNSG, dot_centroids, geometry_calib, lnsg_params, make_grid_phantom, max_grid_residual,
    )

    ph = make_grid_phantom(a=6.0, degree=2)
    pre = max_grid_residual(dot_centroids(ph.observed), ph.centers)
    frame = new_frame(ph.observed)
    calib = geometry_calib(frame.shape, ph.coeffs_x, ph.coeffs_y, ph.residual_px)
    out = geometry.process(frame, calib, lnsg_params())
    post = max_grid_residual(dot_centroids(np.asarray(out.pixel)), ph.centers)
    add_ev("Geometry grid residual after correction (px)", "EV-106 / Scen9a",
           float(post), EV_LNSG["ev106_residual_px_max"], "<=",
           note=f"pre={pre:.3f}px -> post={post:.3f}px")


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------


def print_golden_table():
    hdr = (
        f"{'METRIC':<44}{'ID':<20}{'TARGET':>16}{'ACHIEVED':>18}"
        f"{'ABS_ERR':>11}{'REL_ERR':>10}{'TOL':>12}{'MARGIN':>9}{'VERDICT':>10}"
    )
    print("=" * len(hdr))
    print("GOLDEN METRICS — KNOWN-VALUE REPRODUCTION (synthetic phantoms)")
    print("=" * len(hdr))
    print(hdr)
    print("-" * len(hdr))
    for r in _GOLDEN_ROWS:
        tol_lbl = f"{_fmt(r['tol'])}({r['tol_kind']})"
        margin = f"{r['ratio'] * 100:.0f}%" if np.isfinite(r["ratio"]) else "inf"
        abs_e = _fmt(r["abs_err"]) if r["abs_err"] is not None else "-"
        rel_e = _fmt(r["rel_err"]) if r["rel_err"] is not None else "-"
        print(
            f"{r['metric']:<44.43}{r['ident']:<20.19}{_fmt(r['target']):>16.15}"
            f"{_fmt(r['achieved']):>18.17}{abs_e:>11}{rel_e:>10}{tol_lbl:>12}"
            f"{margin:>9}{r['verdict']:>10}"
        )
    print("-" * len(hdr))
    print("MARGIN = bounded error as % of the declared [T] tolerance "
          "(PASS <=75%, MARGINAL 75-100%, FAIL >100%).")
    print()


def print_ev_table():
    hdr = f"{'EV-GATED METRIC':<44}{'ID':<24}{'ACHIEVED':>14}{'EV BAR':>12}{'DIR':>5}{'RESULT':>14}"
    print("=" * len(hdr))
    print("EV-THRESHOLD-GATED METRICS — clears an externally-set minimum (NOT a known-value reproduction)")
    print("=" * len(hdr))
    print(hdr)
    print("-" * len(hdr))
    for r in _EV_ROWS:
        result = "CLEARS" if r["clears"] else "DOES NOT CLEAR"
        print(
            f"{r['metric']:<44.43}{r['ident']:<24.23}{_fmt(r['achieved']):>14}"
            f"{_fmt(r['bar']):>12}{r['direction']:>5}{result:>14}"
        )
        if r["note"]:
            print(f"    note: {r['note']}")
    print("-" * len(hdr))
    print()


def print_summary():
    verdicts = [r["verdict"] for r in _GOLDEN_ROWS]
    n = len(verdicts)
    n_pass = verdicts.count("PASS")
    n_marg = verdicts.count("MARGINAL")
    n_fail = verdicts.count("FAIL")
    within = n_pass + n_marg
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(
        f"Golden metrics measured: {n}  |  within tolerance: {within}/{n} "
        f"(PASS={n_pass}, MARGINAL={n_marg}, FAIL={n_fail})"
    )
    ev_clear = sum(1 for r in _EV_ROWS if r["clears"])
    print(f"EV-gated metrics measured: {len(_EV_ROWS)}  |  clear bar: {ev_clear}/{len(_EV_ROWS)}")
    if _NOT_MEASURED:
        print(f"\nNOT MEASURED ({len(_NOT_MEASURED)}):")
        for metric, reason in _NOT_MEASURED:
            print(f"  - {metric}: {reason}")
    else:
        print("\nNOT MEASURED: none")
    print("=" * 70)


def main():
    golden = [
        ("MTF", m_mtf),
        ("NPS/NNPS", m_nps),
        ("DQE", m_dqe),
        ("First-frame lag", m_lag),
        ("Ghost CNR", m_ghost),
        ("IRF fit", m_irf),
        ("Bad-pixel E2597", m_defect),
        ("SRb / SNRn", m_srb_snrn),
        ("Single-wire IQI", m_single_wire),
        ("Welford accumulator", m_welford),
        ("Streaming SNRn", m_streaming_snrn),
        ("Noise model (alpha,sigma)", m_noise_model),
        ("VST round-trip", m_vst),
        ("Scatter kernel S_hat", m_scatter),
        ("Grid-line frequency", m_grid_freq),
        ("GSDF PS3.14", m_gsdf),
    ]
    ev = [
        ("Denoise SNR improvement", ev_denoise_snr),
        ("Grid suppression", ev_grid_suppression),
        ("MSE-DRC IQA", ev_mse_iqa),
        ("Virtual-grid CNR", ev_vgrid_cnr),
        ("Geometry residual", ev_geometry_residual),
    ]
    for label, fn in golden:
        safe(label, fn)
    for label, fn in ev:
        safe(label, fn)

    print()
    print_golden_table()
    print_ev_table()
    print_summary()


if __name__ == "__main__":
    main()
