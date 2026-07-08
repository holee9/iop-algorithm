"""Line-noise module: Scenarios 1, 2, 6, 7, 11 + EC-3 (REQ-LNSG-LINE, VALIDATE)."""

from __future__ import annotations

import numpy as np

from common.xframe import MaskFlag, NoiseModel, new_frame
from metrics import nps
from modules import line_noise
from tests.modules.phantoms.linesat import (
    EV_LNSG,
    line_noise_calib,
    lnsg_params,
    make_line_noise_phantom,
    make_structure_phantom,
)


def test_scenario1_no_reference_highpass_subtraction_and_history():
    """REQ-LNSG-LINE-1: SWR-503 path selected when the CalibSet carries no
    reference region; low-frequency anatomy preserved, history updated,
    input immutable."""
    ph = make_line_noise_phantom(shape=(96, 96))
    frame = new_frame(ph.observed)
    calib = line_noise_calib(frame.shape)  # no reference -> SWR-503
    params = lnsg_params()

    out = line_noise.process(frame, calib, params)

    # Banding is suppressed: residual row/col profile variance drops sharply.
    before_var = float(np.var(ph.observed.mean(axis=1)))
    after_var = float(np.var(np.asarray(out.pixel).mean(axis=1)))
    assert after_var < 0.05 * before_var
    # Flat anatomy (background) preserved to within a few counts.
    assert abs(float(np.mean(out.pixel)) - float(np.mean(ph.clean))) < 5.0
    # Input immutability + history.
    assert np.array_equal(frame.pixel, ph.observed)
    assert out.history[-1].module_name == "line_noise"
    assert out.history[-1].calibset_id == calib.calibset_id
    assert out.history[-1].extra["path"] == "no_reference"


def test_scenario2_mask_exclusion_and_noise_model_unchanged():
    """REQ-LNSG-LINE-3: DEFECT/INTERPOLATION/SATURATION excluded from robust
    statistics; noise model (alpha, sigma) preserved."""
    ph = make_line_noise_phantom(shape=(80, 80))
    pix = ph.observed.copy()
    masks = np.zeros(pix.shape, dtype=np.uint8)
    # Contaminate a block with extreme values but flag it masked.
    pix[10:20, 10:20] = 60000.0
    masks[10:20, 10:20] = int(MaskFlag.DEFECT)
    noise = NoiseModel(alpha=0.7, sigma=12.0)
    frame = new_frame(pix, masks=masks, noise=noise)

    out = line_noise.process(frame, line_noise_calib(frame.shape), lnsg_params())

    assert out.noise == noise  # not re-estimated
    # The masked block did not bias the correction into the clean background:
    clean_region = np.asarray(out.pixel)[40:70, 40:70]
    assert abs(float(np.mean(clean_region)) - float(np.mean(ph.clean))) < 6.0


def test_ec3_mask_exclusion_negative_control():
    """EC-3: without exclusion the contaminated pixels bias the row profile;
    with exclusion the module prevents miscorrection."""
    ph = make_line_noise_phantom(shape=(80, 80), noise_sigma=1.0)
    pix = ph.observed.copy()
    # A bright contaminated row-segment that would drag the row median up.
    pix[30, 0:60] = 60000.0

    masks_excl = np.zeros(pix.shape, dtype=np.uint8)
    masks_excl[30, 0:60] = int(MaskFlag.SATURATION)
    frame_excl = new_frame(pix, masks=masks_excl)
    out_excl = line_noise.process(frame_excl, line_noise_calib(pix.shape), lnsg_params())

    frame_incl = new_frame(pix)  # no mask -> contamination NOT excluded
    out_incl = line_noise.process(frame_incl, line_noise_calib(pix.shape), lnsg_params())

    # On a clean neighbouring row (29) the excluded run leaves the background
    # far closer to truth than when contamination is allowed into the stats.
    bg = float(np.mean(ph.clean))
    err_excl = abs(float(np.mean(np.asarray(out_excl.pixel)[29])) - bg)
    err_incl = abs(float(np.mean(np.asarray(out_incl.pixel)[29])) - bg)
    assert err_excl < err_incl


def test_scenario6_detect_line_noise_before_after():
    """REQ-LNSG-VALIDATE-2: metrics.detect_line_noise flags the anomalous peak
    before correction and reports no detection after (row + column)."""
    ph = make_line_noise_phantom(shape=(128, 128))
    params = lnsg_params()
    before = new_frame(ph.observed)
    after = line_noise.process(before, line_noise_calib(before.shape), params)

    det_before = nps.detect_line_noise([before], params)
    det_after = nps.detect_line_noise([after], params)

    assert det_before.get("row_peak")["detected"]
    assert det_before.get("column_peak")["detected"]
    assert not det_after.get("row_peak")["detected"]
    assert not det_after.get("column_peak")["detected"]


def test_scenario7_structure_miscorrection_rate():
    """REQ-LNSG-VALIDATE-3: structure miscorrection rate <= EV-105 min (1%)."""
    ph = make_structure_phantom(shape=(128, 128))
    params = lnsg_params()
    tol = params.get("line_noise_miscorr_tol")

    frame = new_frame(ph.observed)
    out = line_noise.process(frame, line_noise_calib(frame.shape), params)

    corrected = np.asarray(out.pixel, dtype=np.float64)
    truth = np.asarray(ph.structure_true, dtype=np.float64)
    smask = ph.structure_mask
    err = np.abs(corrected[smask] - truth[smask])
    miscorr_rate = float(np.count_nonzero(err > tol)) / int(np.count_nonzero(smask))
    assert miscorr_rate <= EV_LNSG["ev105_miscorr_rate_max"], miscorr_rate


def test_scenario11_reference_path_contamination_exclusion():
    """REQ-LNSG-LINE-2 (Optional): reference-region path with k*MAD row
    exclusion, selected deterministically when a reference region is provided."""
    shape = (60, 40)
    ny, nx = shape
    rng = np.random.default_rng(3)
    background = 2000.0
    # Per-row line offset banding (the additive line noise captured by the
    # shielded reference region).
    row_off = 25.0 * np.sin(2.0 * np.pi * 5 * np.arange(ny) / ny)
    observed = np.zeros(shape, dtype=np.float64)
    # Irradiated region (cols 6+): background + line noise. Shielded reference
    # region (cols 0-5): line noise only (no X-ray signal).
    observed[:, 6:] = background + row_off[:, None]
    observed[:, :6] = row_off[:, None]
    observed += rng.normal(0.0, 1.0, size=shape)
    reference = np.zeros(shape, dtype=bool)
    reference[:, :6] = True
    # Contaminate one reference row with a metal structure spike (should be
    # k*MAD-excluded, not propagated as a bogus row correction).
    observed[25, :6] += 5000.0

    frame = new_frame(observed.astype(np.float32))
    calib = line_noise_calib(shape, reference=reference)
    out = line_noise.process(frame, calib, lnsg_params())
    corrected = np.asarray(out.pixel, dtype=np.float64)

    assert out.history[-1].extra["path"] == "reference"
    assert out.history[-1].extra["contaminated_rows"] >= 1.0
    # Reference subtraction recovers the irradiated background (line noise +
    # any dark removed). The contaminated row 25 was k*MAD-excluded and
    # interpolated, so its irradiated region is NOT corrupted by the spike.
    assert abs(float(np.mean(corrected[25, 6:])) - background) < 60.0
    # Banding removed across all rows: the irradiated-region row means are flat.
    row_means = corrected[:, 6:].mean(axis=1)
    assert float(np.var(row_means)) < 0.2 * float(
        np.var(observed[:, 6:].mean(axis=1))
    )
