"""Saturation handling: mask consumption + boundary band, NO restoration
(SWR-601~602, FR-C008).

This module consumes the SATURATION mask accumulated upstream (offset raw
detection I_raw >= S_th, SPEC-CORR-001 REQ-CORR-OFFSET-4, UNION gain-clamp
65535, REQ-CORR-GAIN-2) and hands it downstream as the denoiser / contrast-
enhancement exclusion substrate. It marks a boundary band (width W_band, SWR-602
2px) around saturated regions by dilating the SATURATION mask (spec decision 3:
dilation is a conservative approximation of the graded buffer weighting the T5
denoiser will apply).

REQ-LNSG-SAT-3 (SWR-602 [HARD] no restoration) postconditions, exact:
  (1) saturated pixel VALUES are unchanged (no extrapolation / reconstruction),
  (2) the SATURATION flag is retained,
  (3) the module does NOT newly set INTERPOLATION (pre-existing INTERPOLATION
      from the upstream defect stage is preserved -- lawful coexistence).
There is a single deterministic path -- no conditional restoration branch.

@MX:ANCHOR: [AUTO] `process` is the saturation pipeline stage entry point invoked
via the orchestrator registry (REQ-LNSG-CONTRACT-1/6).
@MX:REASON: fan_in is the orchestrator registry plus the harness and the
XDET-TC-008 T3 partial gate; the no-restoration postcondition and the boundary-
band substrate are safety-critical (SWR-602 [HARD]) and read by every downstream
noise-weighted stage.

Accuracy is the single goal; no speed optimization (P2).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from common.calibset import CalibSet
from common.contract import Params
from common.mask_ops import dilate_mask
from common.xframe import HistoryEntry, MaskFlag, XFrame

MODULE_NAME = "saturation"
MODULE_VERSION = "1.0.0"

# Params keys.
P_BAND_WIDTH = "saturation_band_width"  # boundary band W_band (SWR-602 val 2)

# SWR-602 boundary-band width default when not injected (documented, not a magic
# literal -- callers override via Params `saturation_band_width`). Appendix A
# registration pending (spec decision 6).
_BAND_WIDTH_DEFAULT = 2


def process(frame: XFrame, calib: CalibSet, params: Params) -> XFrame:
    """Consume the accumulated SATURATION mask, mark the boundary band; NEVER
    restore saturated pixels.

    Returns a new XFrame; pixel values and the noise model are unchanged. The
    input frame is treated as immutable (DATA-6).
    """
    band_val = params.get(P_BAND_WIDTH)
    band_width = _BAND_WIDTH_DEFAULT if band_val is None else int(band_val)

    masks_in = np.asarray(frame.masks, dtype=np.uint8)
    sat = (masks_in & np.uint8(MaskFlag.SATURATION)) != 0

    # Boundary band = dilation of the saturated region minus the core itself
    # (SWR-602 W_band). The band pixels are flagged SATURATION as the
    # conservative buffer-weighting substrate (spec decision 3).
    dilated = dilate_mask(sat, band_width)
    band = dilated & ~sat

    new_masks = masks_in.copy()
    new_masks[band] |= np.uint8(MaskFlag.SATURATION)
    # No INTERPOLATION is set here and no pixel value is touched (SAT-3).

    new = replace(frame, masks=new_masks)

    n_sat = int(np.count_nonzero(sat))
    entry = HistoryEntry(
        module_name=MODULE_NAME,
        module_version=MODULE_VERSION,
        params_hash=params.hash(),
        calibset_id=calib.calibset_id,
        extra={
            "saturated_pixels": n_sat,
            "saturated_rate": float(n_sat) / sat.size,
            "boundary_band_pixels": int(np.count_nonzero(band)),
        },
    )
    return new.record_history(entry)
