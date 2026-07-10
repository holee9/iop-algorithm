"""Core-layer analog that deliberately imports `apps.gui` (forbidden direction).

@MX:NOTE: [AUTO] Canary fixture only -- lives outside the production tree
(this package is never referenced by `common/modules/pipeline/metrics`, so the
production `[tool.importlinter]` forbidden contract for `apps.gui` (REQ-VIEW-ARCH-1)
is entirely unaffected by this file). Its sole purpose is to prove that
import-linter's `forbidden` contract type actually detects the mirrored
core -> apps.gui violation shape when a SEPARATE, narrowly-scoped temp config
is pointed at it (REQ-VIEW-ARCH-2, EC-2, lesson #1 vacuous-pass guard) --
mirroring the `tests/fixtures/badlayers/low.py` negative-control precedent.
"""

from apps.gui import config  # noqa: F401 (intentional core -> apps.gui violation)
