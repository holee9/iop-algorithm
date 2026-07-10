"""XDET-TC-050 / XDET-TC-054 — package public-surface re-exports + additive contract.

SPEC-ERGO-001 (REQ-ERGO-EXPORTS-1/2/3, REQ-ERGO-CONTRACT-3, REQ-ERGO-VALIDATE-1/5b).

Consumer-ergonomics gap #1: `common`/`modules`/`metrics` expose curated
re-exports + `__all__` (pipeline/__init__ precedent) WITHOUT inverting the
dependency direction or introducing an import cycle. Every assertion is real
execution evidence (lesson L#1): `__all__` names are resolved via getattr, the
deep-path imports are exercised, a FRESH interpreter imports all four packages
without a cycle, and `lint-imports` is run as a subprocess and asserted 0 broken.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent

# The names the metrics/__init__ docstring already enumerated as the intended
# export surface (spec: result/mtf/nps/dqe/lag/defect_stats/ndt) + new metric_view.
_METRICS_DOC_ENUMERATED = (
    "MetricResult",
    "MetricCondition",
    "MetricReadError",
    "require_param",
    "compute_mtf",
    "compute_nps",
    "detect_line_noise",
    "compute_dqe",
    "compute_first_frame_lag",
    "compute_ghost_cnr",
    "classify_defects",
    "read_duplex_srb",
    "compute_snrn",
)


# -- XDET-TC-050: curated re-exports + __all__ introspection ------------------


def test_tc_050_each_package_exposes_nonempty_all():
    import common
    import metrics
    import modules

    for pkg in (common, modules, metrics):
        names = getattr(pkg, "__all__", None)
        assert names, f"{pkg.__name__}.__all__ must be a non-empty sequence"
        assert all(isinstance(n, str) for n in names)


def test_tc_050_every_all_name_resolves():
    import common
    import metrics
    import modules

    for pkg in (common, modules, metrics):
        for name in pkg.__all__:
            assert hasattr(pkg, name), (
                f"{pkg.__name__}.__all__ lists '{name}' but it does not resolve"
            )


def test_tc_050_metrics_all_contains_metric_view_and_doc_list():
    import metrics

    assert "metric_view" in metrics.__all__
    # Document-code parity: every symbol the docstring enumerated is exported.
    missing = [n for n in _METRICS_DOC_ENUMERATED if n not in metrics.__all__]
    assert not missing, f"metrics.__all__ missing docstring-enumerated names: {missing}"


def test_tc_050_deep_path_imports_still_work():
    # Additive: existing deep-path imports keep working with unchanged meaning.
    from common.contract import Params
    from metrics.mtf import compute_mtf
    from modules import gain

    # And the re-export resolves to the SAME object as the deep path.
    import common
    import metrics

    assert common.Params is Params
    assert metrics.compute_mtf is compute_mtf
    assert gain.__name__ == "modules.gain"


# -- XDET-TC-054: no cycle, no upward import, lint-imports 0 broken -----------


def test_tc_054_fresh_interpreter_imports_without_cycle():
    # A brand-new interpreter must import all four packages with no circular
    # import (real execution evidence, not a description).
    proc = subprocess.run(
        [sys.executable, "-c", "import common; import modules; import metrics; import pipeline"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"fresh-interpreter import failed (possible cycle):\n{proc.stderr}"
    )


def test_tc_054_common_init_does_not_import_upward():
    # Negative control: the foundational package must not re-export upward layers.
    src = (_ROOT / "common" / "__init__.py").read_text(encoding="utf-8")
    for upper in ("modules", "pipeline", "metrics"):
        assert f"import {upper}" not in src, (
            f"common/__init__.py must not import '{upper}' (upward import)"
        )
        assert f"from {upper}" not in src


def test_tc_054_lint_imports_zero_broken():
    exe = shutil.which("lint-imports")
    if exe is None:
        pytest.skip("lint-imports console script not on PATH")
    proc = subprocess.run(
        [exe],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, f"lint-imports reported broken contracts:\n{combined}"
    assert "Contracts:" in combined  # non-vacuous: the linter actually ran
