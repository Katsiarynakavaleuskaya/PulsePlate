#!/usr/bin/env python3
"""Compatibility wrapper for the canonical Python dependency surface validator."""

from __future__ import annotations

import sys
from typing import cast

from scripts.ci.check_python_dependency_surfaces import main as check_python_dependency_surfaces


def main(argv: list[str] | None = None) -> int:
    """Delegate to scripts/ci/check_python_dependency_surfaces.py."""
    return cast(int, check_python_dependency_surfaces(argv))


if __name__ == "__main__":
    sys.exit(main())
