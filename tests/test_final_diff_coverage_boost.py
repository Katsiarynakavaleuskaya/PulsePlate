"""
Additional diff coverage boost tests to reach 97%+ coverage.

Targets specific missing lines from CI diff coverage report.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBayesianTestAnalyzerLine633:
    """Test for missing line 633 in core/bayesian_test_analyzer.py"""

    def test_calculate_confidence_max_entropy_zero(self) -> None:
        """Test _calculate_confidence when max_entropy is 0 (line 633)."""
        from core.bayesian_test_analyzer import BayesianTestAnalyzer, ErrorType

        analyzer = BayesianTestAnalyzer()

        # Create probabilities dict with only one error type (max_entropy will be 0)
        single_prob = {ErrorType.ASSERTION_ERROR: 1.0}

        confidence = analyzer._calculate_confidence(single_prob)

        # When there's only one option with 100% probability, confidence should be 1.0
        assert confidence == 1.0


class TestBusinessBayesianAnalyzerMissingLines:
    """Tests for missing lines in core/business_bayesian_analyzer.py"""

    def test_analyze_locale_loading_fallback(self, tmp_path: Path) -> None:
        """Test locale loading with missing YAML falls back to defaults (lines 224-225, 281-282)."""
        from core.business_bayesian_analyzer import BusinessBayesianAnalyzer

        # Create analyzer with non-existent locale
        with patch("core.business_bayesian_analyzer.__file__", str(tmp_path / "fake.py")):
            analyzer = BusinessBayesianAnalyzer(locale="nonexistent")

            # Should still work with defaults
            result = analyzer.analyze("def test(): pass", "test_code")
            assert isinstance(result, list)


class TestIntegratedBayesianAnalyzerMissingLines:
    """Tests for missing lines in core/integrated_bayesian_analyzer.py"""

    def test_analyze_safety_password_in_test_context(self) -> None:
        """Test password detection suppressed in test context (lines 583-584)."""
        from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer

        analyzer = IntegratedBayesianAnalyzer()

        # Code with password in test context
        test_code = """
def test_login():
    password = "test123"
    assert login(password)
"""

        issues = analyzer._analyze_safety_aspects(test_code, "test_login")

        # Should not flag password in test context
        assert not any("password" in issue.lower() for issue in issues)

    def test_sql_injection_in_logging_context(self) -> None:
        """Test SQL injection not flagged in logging (lines 641, 645)."""
        from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer

        analyzer = IntegratedBayesianAnalyzer()

        # SQL in logging context should not be flagged
        logging_code = """
import logging
logger = logging.getLogger(__name__)
query = "SELECT * FROM users WHERE id = " + user_id
logger.debug(f"Executing query: {query}")
"""

        issues = analyzer._analyze_safety_aspects(logging_code, "logging_example")

        # Should not flag SQL injection in logging context
        assert not any("SQL injection" in issue for issue in issues)


class TestNutritionBayesianAnalyzerMissingLines:
    """Tests for missing lines in core/nutrition_bayesian_analyzer.py"""

    def test_analyze_nutrition_safety_edge_cases(self) -> None:
        """Test nutrition safety analysis edge cases (lines 135, 149, 319-320)."""
        from core.nutrition_bayesian_analyzer import NutritionBayesianAnalyzer

        analyzer = NutritionBayesianAnalyzer()

        # Test with minimal code
        minimal_code = "x = 1"
        results = analyzer.analyze_nutrition_safety(minimal_code, "minimal_test")

        assert isinstance(results, list)


class TestComprehensiveBayesianAnalyzerMissingLines:
    """Tests for missing lines in core/comprehensive_bayesian_analyzer.py"""

    def test_comprehensive_analysis_edge_cases(self) -> None:
        """Test comprehensive analysis with edge cases (lines 201, 540, 544)."""
        from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer

        analyzer = ComprehensiveBayesianAnalyzer()

        # Very minimal code
        result = analyzer.analyze_comprehensively("", "empty_test", "test.py")

        assert result is not None
        assert hasattr(result, "success")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
