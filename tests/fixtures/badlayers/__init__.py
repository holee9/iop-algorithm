"""Self-contained fixture package with a deliberate layering violation (EC-5).

Not part of pyproject `root_packages`, so the project's real import-linter
contract ignores it. A dedicated negative test points a temporary import-linter
config at this package and asserts the upward-import violation is detected.
"""
