"""Low layer (analogous to `common`). Deliberately imports upward -> violation.

This mirrors the forbidden `common -> modules/pipeline` direction so the
import-linter layers contract fails on it (EC-5, REQ-INFRA-STATIC-2).
"""

from tests.fixtures.badlayers import high  # noqa: F401  (intentional violation)
