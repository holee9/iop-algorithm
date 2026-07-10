"""XDET processing-modules layer.

Modules may import from `common` only; they must NOT import each other
(horizontal independence) nor `pipeline`/`metrics` (enforced by import-linter,
SWR-000-8). The T0 reference passthrough module lives under `tests/` fixtures,
never here (SPEC decision 1, REQ-INFRA-CONTRACT-3).

Curated public re-exports + `__all__` (SPEC-ERGO-001 REQ-ERGO-EXPORTS): the 12
processing module objects and the `default_registry` convenience lookup. The
submodules are imported first so `registry` (which does `from modules import
...`) resolves cleanly; the `independence` contract governs leaf-to-leaf imports,
not this package `__init__`, so re-exporting here introduces no violation. Existing
deep-path imports (e.g. `from modules import gain`) keep working unchanged.
"""

from modules import (
    defect,
    denoise,
    gain,
    geometry,
    grid,
    lag,
    line_noise,
    mse,
    offset,
    saturation,
    virtual_grid,
    window,
)
from modules.registry import default_registry

__all__ = [
    "offset",
    "gain",
    "defect",
    "lag",
    "line_noise",
    "saturation",
    "geometry",
    "grid",
    "virtual_grid",
    "denoise",
    "mse",
    "window",
    "default_registry",
]
