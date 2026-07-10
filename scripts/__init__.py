"""XDET tooling scripts (not processing modules).

Scripts under this package are DEV/CI tooling — they do NOT expose the
`process(XFrame, CalibSet, Params) -> XFrame` module contract, add no
`CANONICAL_ORDER` stage, and are one-way consumers of the core 4 layers
(`common`/`modules`/`pipeline`/`metrics`). SPEC-REALDATA-001 REQ-CONTRACT-1.
"""
