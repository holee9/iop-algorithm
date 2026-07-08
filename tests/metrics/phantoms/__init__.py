"""Synthetic phantom generators with injected known values (plan.md section 5).

These live in tests/ only (production tree stays measurement-pure). Each factory
returns a synthetic input plus the analytic known value(s) the engine must
reproduce within a [T] tolerance.
"""
