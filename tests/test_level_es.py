"""
Tests for Fitness Levels in Spanish

This test ensures that fitness level descriptions are correctly localized
in Spanish and other supported languages.

NOTE: estimate_level function was removed with bmi_core.py.
This test file is disabled until a canonical equivalent is available.
"""

import pytest

pytestmark = pytest.mark.skip(
    "estimate_level removed with bmi_core.py - no canonical equivalent yet"
)
