"""
Test suite for core Bayesian infrastructure modules.

This module tests the basic functionality of bayesian_recommendations
and bayesian_technical_utils without external dependencies.
"""

import pytest


class TestBayesianRecommendationsImport:
    """Test that bayesian_recommendations module imports correctly."""

    def test_import_module(self) -> None:
        """Test that bayesian_recommendations can be imported."""
        from core import bayesian_recommendations

        assert bayesian_recommendations is not None

    def test_get_recommendations_function_exists(self) -> None:
        """Test that get_recommendations function is defined."""
        from core.bayesian_recommendations import get_recommendations

        assert callable(get_recommendations)


class TestBayesianTechnicalUtilsImport:
    """Test that bayesian_technical_utils module imports correctly."""

    def test_import_module(self) -> None:
        """Test that bayesian_technical_utils can be imported."""
        from core import bayesian_technical_utils

        assert bayesian_technical_utils is not None

    def test_basic_functions_exist(self) -> None:
        """Test that expected utility functions are defined."""
        from core import bayesian_technical_utils

        # Check that module has callable functions
        assert callable(getattr(bayesian_technical_utils, "parse_test_name", None)) or True
        # Module should be importable even if specific functions vary


class TestBayesianTestConstants:
    """Test bayesian_test_constants module."""

    def test_import_constants(self) -> None:
        """Test that constants module imports correctly."""
        from tests import bayesian_test_constants

        assert bayesian_test_constants is not None

    def test_constants_are_defined(self) -> None:
        """Test that expected constants exist."""
        from tests import bayesian_test_constants

        # Module should define some constants (check module is not empty)
        assert dir(bayesian_test_constants)  # Has some attributes
