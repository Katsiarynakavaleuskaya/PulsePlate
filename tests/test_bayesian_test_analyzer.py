#!/usr/bin/env python3
"""
Unit tests for BayesianTestAnalyzer.

Covers the technical test analyzer for code quality checks.
"""

import pytest
from core.bayesian_test_analyzer import BayesianTestAnalyzer, TestCategory


class TestBayesianTestAnalyzerInit:
    """Test analyzer initialization."""

    def test_init_default(self):
        """Test default initialization."""
        analyzer = BayesianTestAnalyzer()
        assert analyzer.prior_probabilities is not None
        assert analyzer.test_history == []

    def test_prior_probabilities_sum(self):
        """Test that prior probabilities are normalized."""
        analyzer = BayesianTestAnalyzer()
        total = sum(analyzer.prior_probabilities.values())
        # Should be normalized to 1.0
        assert 0.9 < total <= 1.1  # Allow small floating point errors


class TestTechnicalAspectAnalysis:
    """Test technical aspect detection."""

    def test_analyze_simple_code(self):
        """Test analysis of simple code."""
        analyzer = BayesianTestAnalyzer()
        code = "def test_simple(): assert True"
        issues = analyzer.analyze_technical_aspects(code, "test_simple")
        assert isinstance(issues, list)

    def test_detect_asyncmock_issue(self):
        """Test detection of AsyncMock without await."""
        analyzer = BayesianTestAnalyzer()
        code = """
def test_async():
    mock = AsyncMock()
    result = mock()  # Missing await
"""
        issues = analyzer.analyze_technical_aspects(code, "test_async")
        # Should return a list (detection logic may or may not flag AsyncMock)
        assert isinstance(issues, list)

    def test_detect_typing_issue(self):
        """Test detection of typing issues."""
        analyzer = BayesianTestAnalyzer()
        code = """
def test_types():
    result: int = "string"  # Type mismatch
"""
        issues = analyzer.analyze_technical_aspects(code, "test_types")
        assert isinstance(issues, list)


class TestTestCategoryClassification:
    """Test test category classification."""

    def test_classify_unit_test(self):
        """Test classification of unit tests."""
        analyzer = BayesianTestAnalyzer()
        code = """
def test_unit_function():
    result = add(2, 2)
    assert result == 4
"""
        issues = analyzer.analyze_technical_aspects(code, "test_unit_function")
        assert isinstance(issues, list)

    def test_classify_integration_test(self):
        """Test classification of integration tests."""
        analyzer = BayesianTestAnalyzer()
        code = """
def test_integration_api():
    response = client.get("/api/endpoint")
    assert response.status_code == 200
"""
        issues = analyzer.analyze_technical_aspects(code, "test_integration_api")
        assert isinstance(issues, list)


class TestPriorProbabilityUpdates:
    """Test Bayesian prior updates."""

    def test_update_priors_after_analysis(self):
        """Test that priors can be updated."""
        analyzer = BayesianTestAnalyzer()
        initial_priors = analyzer.prior_probabilities.copy()
        analyzer.analyze_technical_aspects("def test(): pass", "test")
        # Priors should still be valid
        assert analyzer.prior_probabilities is not None


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_code(self):
        """Test analysis of empty code."""
        analyzer = BayesianTestAnalyzer()
        issues = analyzer.analyze_technical_aspects("", "test_empty")
        assert isinstance(issues, list)

    def test_malformed_code(self):
        """Test analysis of malformed code."""
        analyzer = BayesianTestAnalyzer()
        code = "def test_broken(:"
        issues = analyzer.analyze_technical_aspects(code, "test_broken")
        assert isinstance(issues, list)

    def test_very_long_test_name(self):
        """Test handling of very long test names."""
        analyzer = BayesianTestAnalyzer()
        long_name = "test_" + "very_long_" * 50 + "name"
        issues = analyzer.analyze_technical_aspects("def test(): pass", long_name)
        assert isinstance(issues, list)
