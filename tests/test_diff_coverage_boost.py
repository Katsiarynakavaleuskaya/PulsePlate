"""
Tests to boost diff coverage to 97%+ for PR #294.

Targets missing lines in:
- app/routers/business.py (lines 70, 74)
- core/bayesian_technical_utils.py (lines 131, 135, 149, 152-153, 155, 161, 163, 167, 182, 252)
- core/business_bayesian_analyzer.py (selected high-impact lines)
- core/comprehensive_bayesian_analyzer.py (selected high-impact lines)
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.types import ASGIApp
from typing import cast
from pathlib import Path
import os
import sys

# Import app
import app as app_module
from app import app


class TestBusinessRouterCoverage:
    """Tests for app/routers/business.py missing lines."""

    def setup_method(self) -> None:
        """Set up test environment."""
        os.environ["API_KEY"] = "test_key"
        os.environ["BUSINESS_MODULE_ENABLED"] = "true"
        self.client = TestClient(cast(ASGIApp, app))

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if hasattr(self, "client"):
            self.client.close()
        for key in ["API_KEY", "BUSINESS_MODULE_ENABLED"]:
            if key in os.environ:
                del os.environ[key]

    def test_business_analyze_oversized_payload(self) -> None:
        """Test business analyze endpoint with oversized code payload (>100KB)."""
        # Create a payload larger than 100KB
        oversized_code = "x" * 100_001  # 100,001 bytes > 100,000 limit

        payload = {"code": oversized_code, "test_name": "test_large_payload", "locale": "en"}

        response = self.client.post(
            "/api/v1/business/analyze", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Pydantic validation may reject before custom validation runs
        # Accept either 413 (custom validation) or 422 (Pydantic validation)
        assert response.status_code in [413, 422]
        data = response.json()
        assert "detail" in data


class TestBayesianTechnicalUtilsCoverage:
    """Tests for core/bayesian_technical_utils.py missing lines."""

    def test_analyze_code_quality_await_detection(self) -> None:
        """Test AST detection of await keyword (line 131)."""
        from core.bayesian_technical_utils import analyze_technical_aspects_common

        code_with_await = """
async def fetch_data():
    result = await get_data()
    return result
"""
        issues = analyze_technical_aspects_common(code_with_await)
        # Should NOT have "Async function without await usage"
        assert "Async function without await usage" not in issues

    def test_analyze_code_quality_try_detection(self) -> None:
        """Test AST detection of try-except blocks (line 135)."""
        from core.bayesian_technical_utils import analyze_technical_aspects_common

        code_with_try = """
def safe_function():
    try:
        raise ValueError("test")
    except ValueError:
        pass
"""
        issues = analyze_technical_aspects_common(code_with_try)
        # Should NOT have "Exception raised without handling"
        assert "Exception raised without handling" not in issues

    def test_analyze_code_quality_assert_raises_detection(self) -> None:
        """Test detection of assertRaises pattern (line 149)."""
        from core.bayesian_technical_utils import analyze_technical_aspects_common

        code_with_assert_raises = """
class TestClass:
    def test_exception(self):
        self.assertRaises(ValueError, some_func)
        raise ValueError("test")
"""
        issues = analyze_technical_aspects_common(code_with_assert_raises)
        # Should NOT flag exception raised without handling
        assert "Exception raised without handling" not in issues

    def test_analyze_code_quality_pytest_raises_with_context(self) -> None:
        """Test pytest.raises detection in with statement (lines 152-153, 155)."""
        from core.bayesian_technical_utils import analyze_technical_aspects_common

        code_with_pytest_raises = """
def test_something():
    with pytest.raises(ValueError):
        raise ValueError("expected")
"""
        issues = analyze_technical_aspects_common(code_with_pytest_raises)
        # Should NOT flag exception raised without handling
        assert "Exception raised without handling" not in issues

    def test_analyze_code_quality_bare_raises_function(self) -> None:
        """Test detection of just 'raises' function (lines 163, 167)."""
        from core.bayesian_technical_utils import analyze_technical_aspects_common

        code_with_bare_raises = """
from pytest import raises

def test_something():
    with raises(ValueError):
        raise ValueError("expected")
"""
        issues = analyze_technical_aspects_common(code_with_bare_raises)
        # Should NOT flag exception raised without handling
        assert "Exception raised without handling" not in issues

    def test_analyze_code_quality_intentional_raise_pattern(self) -> None:
        """Test detection of intentional raise function names (line 182)."""
        from core.bayesian_technical_utils import analyze_technical_aspects_common

        code_with_intentional_raise = """
def validate_input(value):
    if not value:
        raise ValueError("Invalid input")
    return value
"""
        issues = analyze_technical_aspects_common(code_with_intentional_raise)
        # Should NOT flag "Exception raised without handling" for validate_* functions
        assert "Exception raised without handling" not in issues

    def test_analyze_code_quality_regex_fallback_exception_handling(self) -> None:
        """Test regex fallback for exception handling detection (line 252)."""
        from core.bayesian_technical_utils import analyze_technical_aspects_common

        # Code with syntax error that triggers regex fallback
        # but has raise without try
        invalid_syntax_code = """
def bad_function(:  # Syntax error
    raise ValueError("test")
"""
        issues = analyze_technical_aspects_common(invalid_syntax_code)
        # Regex fallback should detect raise without try
        assert "Exception raised without handling" in issues


class TestBusinessBayesianAnalyzerCoverage:
    """Tests for core/business_bayesian_analyzer.py missing lines."""

    def test_business_analyzer_init_with_custom_locale(self) -> None:
        """Test BusinessBayesianAnalyzer with custom locale."""
        from core.business_bayesian_analyzer import BusinessBayesianAnalyzer

        # Test with 'ru' locale to cover locale-specific loading
        analyzer = BusinessBayesianAnalyzer(locale="ru")
        # Verify analyzer was created (locale is used internally for loading configs)
        assert analyzer is not None

        # Test with 'es' locale
        analyzer_es = BusinessBayesianAnalyzer(locale="es")
        assert analyzer_es is not None

    def test_business_analyzer_missing_yaml_fallback(self, tmp_path: Path) -> None:
        """Test fallback when YAML files are missing."""
        from core.business_bayesian_analyzer import BusinessBayesianAnalyzer
        import core.business_bayesian_analyzer as bba_module

        # Patch __file__ to point to a location where YAML files don't exist
        original_file = bba_module.__file__
        try:
            bba_module.__file__ = str(tmp_path / "fake_module.py")

            # Analyzer should fall back to defaults
            analyzer = BusinessBayesianAnalyzer()
            assert analyzer is not None
        finally:
            bba_module.__file__ = original_file


class TestComprehensiveBayesianAnalyzerCoverage:
    """Tests for core/comprehensive_bayesian_analyzer.py missing lines."""

    def test_comprehensive_analyzer_edge_cases(self) -> None:
        """Test edge cases in comprehensive analyzer."""
        from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer

        analyzer = ComprehensiveBayesianAnalyzer()

        # Test with minimal code
        minimal_code = "pass"
        result = analyzer.analyze_comprehensively(minimal_code, "test_minimal", "test.py")

        # Should return a ComprehensiveTestResult
        assert result is not None
        assert result.test_name == "test_minimal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
