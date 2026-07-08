"""XDET processing-modules layer (empty at T0).

No algorithm modules exist yet — offset/gain/defect/... arrive at T2+. Modules
may import from `common` only; they must NOT import each other (horizontal
independence) nor `pipeline`/`metrics` (enforced by import-linter, SWR-000-8).
The T0 reference passthrough module lives under `tests/` fixtures, never here
(SPEC decision 1, REQ-INFRA-CONTRACT-3).
"""
