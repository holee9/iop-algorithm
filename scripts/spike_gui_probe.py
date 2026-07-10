"""SPEC-VIEWER-001 Phase 0 spike: napari SG-1/SG-2/SG-3 headless measurement.

Run with: QT_QPA_PLATFORM=offscreen uv run python scripts/spike_gui_probe.py

Measures (spec.md REQ-VIEW-SPIKE-1, docs/GUI_CRITERIA.md §2.3):
  SG-1: hover pixel probe exposes stored float32 raw value (not 8-bit display value)
  SG-2: W/L (contrast_limits) update latency on a 3072x3072 float32 frame, [T] <= 100ms
  SG-3: cold start (import + viewer creation) to interactive, [T] <= 10s

This script is a Phase 0 spike tool, not part of the P1 golden model pipeline
(common/modules/pipeline/metrics). It intentionally lives outside those
packages and is not wired into the import-linter contracts.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

import numpy as np


def measure_sg3_cold_start() -> dict:
    """SG-3: cold start (import napari + create embedded viewer) in a fresh subprocess."""
    probe_code = (
        "import time; t0 = time.perf_counter();"
        "import napari;"
        "t1 = time.perf_counter();"
        "viewer = napari.Viewer(show=False);"
        "t2 = time.perf_counter();"
        "viewer.close();"
        "print(f'{t1 - t0:.4f} {t2 - t0:.4f}')"
    )
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-c", probe_code],
        capture_output=True,
        text=True,
        env={"QT_QPA_PLATFORM": "offscreen", **__import__("os").environ},
        timeout=60,
    )
    wall = time.perf_counter() - start
    if result.returncode != 0:
        return {
            "status": "ERROR",
            "wall_seconds": wall,
            "stderr": result.stderr[-4000:],
        }
    import_s, viewer_ready_s = (float(x) for x in result.stdout.strip().split())
    return {
        "status": "OK",
        "import_seconds": import_s,
        "viewer_ready_seconds": viewer_ready_s,
        "wall_seconds": wall,
    }


def measure_sg1_and_sg2() -> dict:
    """SG-1 (float32 raw value probe) and SG-2 (contrast_limits update latency)."""
    import napari

    rng = np.random.default_rng(0)
    frame = rng.standard_normal((3072, 3072)).astype(np.float32)

    viewer = napari.Viewer(show=False)
    layer = viewer.add_image(frame, name="spike_frame")

    # --- SG-1: stored float32 raw value at an arbitrary pixel ---------------
    probe_coords = [(0, 0), (1536, 1536), (3071, 3071), (777, 2222)]
    sg1_results = []
    for row, col in probe_coords:
        expected = float(frame[row, col])
        # napari's Image layer exposes the untouched data array; a "hover" is
        # equivalent to indexing layer.data at the world/data coordinate under
        # the cursor. get_value() is napari's documented API for this lookup
        # (used internally by the QtStatusBar coordinate/value display).
        probed = layer.get_value(position=(row, col), world=False)
        probed_f = float(probed) if probed is not None else None
        exact_match = probed_f is not None and probed_f == expected
        sg1_results.append(
            {
                "coord": [row, col],
                "expected_float32": expected,
                "probed_value": probed_f,
                "exact_match": exact_match,
                "is_8bit_display_value": (
                    probed_f is not None and probed_f == round(probed_f) and 0 <= probed_f <= 255
                    and probed_f != expected
                ),
            }
        )
    sg1_pass = all(r["exact_match"] for r in sg1_results)

    # --- SG-2: contrast_limits update latency --------------------------------
    limit_pairs = [(-3.0, 3.0), (-1.0, 1.0), (-2.5, 2.5), (0.0, 4.0), (-4.0, 0.5)]
    durations_ms = []
    for lo, hi in limit_pairs:
        t0 = time.perf_counter()
        layer.contrast_limits = (lo, hi)
        # Force any lazy recompute (e.g. colormap LUT application) to happen now.
        _ = layer._data_view if hasattr(layer, "_data_view") else layer.data
        t1 = time.perf_counter()
        durations_ms.append((t1 - t0) * 1000.0)

    viewer.close()

    return {
        "sg1": {
            "probes": sg1_results,
            "pass": sg1_pass,
        },
        "sg2": {
            "durations_ms": durations_ms,
            "mean_ms": sum(durations_ms) / len(durations_ms),
            "max_ms": max(durations_ms),
        },
    }


def main() -> None:
    report = {"frame_shape": [3072, 3072], "dtype": "float32"}

    report["sg3"] = measure_sg3_cold_start()
    report["sg1_sg2"] = measure_sg1_and_sg2()

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
