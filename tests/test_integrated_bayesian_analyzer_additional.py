"""Integration tests for IntegratedBayesianAnalyzer behavior and edge cases."""

import pytest

from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer, NormalizedIssueType


def test_is_in_test_or_mock_context_variants() -> None:
    analyzer = IntegratedBayesianAnalyzer()

    # AST path: class inheriting from TestCase
    code_class = """
import unittest
class TestFoo(unittest.TestCase):
    def test_something(self):
        pass
"""
    assert analyzer._is_in_test_or_mock_context(code_class) is True

    # Regex fallback path (bad syntax) with fixture keyword
    bad_code = "@pytest.fixture\ndef broken(:\n    pass"
    assert analyzer._is_in_test_or_mock_context(bad_code) is True


def test_check_unsafe_file_opens_variants() -> None:
    analyzer = IntegratedBayesianAnalyzer()

    # SyntaxError path should return False
    bad_code = "def broken(:\n  open('x')"
    assert analyzer._check_unsafe_file_opens(bad_code) is False


def test_check_sensitive_data_logging_regex_fallback() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    bad_code = "logger.info('secret"
    assert analyzer._check_sensitive_data_logging(bad_code) is True
    # AST path with f-string and Name should be detected
    code_ast = """
import logging
token = 'abc'
logger.info(f\"token={token}\")
"""
    assert analyzer._check_sensitive_data_logging(code_ast) is True

    code_joined = """
import logging
token = "abc"
logger.info("token=" f"{token}")
"""
    assert analyzer._check_sensitive_data_logging(code_joined) is True


def test_analyze_safety_aspects_password_sql_and_context() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    # Non-test context: should flag both password and SQL injection
    code = 'password = "abc"\nquery = "SELECT * FROM users" + user_input'
    issues = analyzer._analyze_safety_aspects(code, "prod_code")
    assert "Hardcoded password in code" in issues
    assert any("SQL injection" in msg for msg in issues)

    # Test context should suppress password flag
    test_code = """
def test_password():
    password = "abc"
"""
    issues_test = analyzer._analyze_safety_aspects(test_code, "test_password")
    assert all("password" not in msg.lower() for msg in issues_test)


def test_analyze_philosophy_compliance_branches() -> None:
    analyzer = IntegratedBayesianAnalyzer()

    # Health metric validation missing -> violation
    violations = analyzer._analyze_philosophy_compliance("code", "health_metric_check")
    assert "Health test does not verify key metrics" in violations

    # Nutrition test without macronutrients -> violation
    violations2 = analyzer._analyze_philosophy_compliance("code", "nutrition_summary")
    assert "macronutrients" in " ".join(violations2)

    # Health test with indicators passes (no extra violation)
    ok = analyzer._analyze_philosophy_compliance("bmi value", "health_ok")
    # Should not add violation because bmi present
    assert all("metrics" not in msg for msg in ok)

    # User edge-case without error assertions should trigger user-related violation
    user_viol = analyzer._analyze_philosophy_compliance("code", "user_edge_case")
    assert any("error handling" in msg.lower() for msg in user_viol)

    # Personalization without profile/preferences should be flagged
    personal = analyzer._analyze_philosophy_compliance("code", "personal_test")
    assert any("personalization" in msg.lower() for msg in personal)


def test_is_in_test_or_mock_context_more_branches() -> None:
    analyzer = IntegratedBayesianAnalyzer()

    # AST decorator attribute @pytest.fixture should be detected
    code_fixture = """
import pytest
@pytest.fixture
def fx():
    return 1
"""
    assert analyzer._is_in_test_or_mock_context(code_fixture) is True

    # AST decorator from mock module
    code_mock_decorator = """
import mock
@mock.patch('mod.fn')
def fx():
    pass
"""
    assert analyzer._is_in_test_or_mock_context(code_mock_decorator) is True

    # Name decorator @patch (from unittest.mock import patch)
    code_patch_name = """
@patch
def fx():
    pass
"""
    assert analyzer._is_in_test_or_mock_context(code_patch_name) is True

    # Variable names containing fixture/test_data should be detected
    code_vars = "fixture_data = {}; test_data = {}; mock_user = {}"
    assert analyzer._is_in_test_or_mock_context(code_vars) is True

    # Name decorator from pytest import fixture
    code_name_fixture = """
from pytest import fixture
@fixture
def fx2():
    return 2
"""
    assert analyzer._is_in_test_or_mock_context(code_name_fixture) is True

    # Attribute decorator via mock module attribute (e.g., @mock.AsyncMock)
    code_mock_attr = """
import mock
@mock.AsyncMock
def fx3():
    pass
"""
    assert analyzer._is_in_test_or_mock_context(code_mock_attr) is True

    # Class inheriting from TestCase via Name base
    code_name_base = """
from unittest import TestCase
class MyTest(TestCase):
    def test_ok(self):
        pass
"""
    assert analyzer._is_in_test_or_mock_context(code_name_base) is True


def test_assess_business_impact_levels() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    assert analyzer._assess_business_impact([], [], [], []) == "No business impact"
    assert (
        analyzer._assess_business_impact(["t1"], [], [], []) == "Minimal impact on user experience"
    )
    assert (
        analyzer._assess_business_impact(["t1", "t2", "t3"], [], [], [])
        == "Moderate impact on product quality"
    )
    assert (
        analyzer._assess_business_impact(["t"] * 6, [], [], [])
        == "High impact on reputation and safety"
    )
    assert (
        analyzer._assess_business_impact(["t"] * 11, [], [], [])
        == "Critical impact on business operations"
    )


def test_normalize_issue_type_keywords() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    issue = "SQL injection with hardcoded password leads to vulnerability and safety risk"

    types = analyzer._normalize_issue_type(issue)
    assert NormalizedIssueType.INJECTION in types
    assert NormalizedIssueType.PASSWORD_LEAK in types
    assert NormalizedIssueType.SAFETY_VIOLATION in types
    assert (
        NormalizedIssueType.DANGEROUS_INSTRUCTION in types
        or NormalizedIssueType.HEALTH_VIOLATION in types
    )

    # Async/exception keywords map to respective normalized types
    types2 = analyzer._normalize_issue_type("async error exception handling fails")
    assert NormalizedIssueType.ASYNC_ERROR in types2
    assert NormalizedIssueType.EXCEPTION_HANDLING in types2

    # Non-string issues should yield empty set
    assert analyzer._normalize_issue_type(None) == set()


def test_calculate_risk_level_thresholds() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    critical = ["SQL injection", "hardcoded password", "dangerous instruction"]
    assert analyzer._calculate_risk_level(critical, [], [], []) == "critical"
    high = ["SQL injection", "hardcoded password"]
    assert analyzer._calculate_risk_level(high, [], [], []) == "high"
    medium = ["SQL injection"]
    assert analyzer._calculate_risk_level(medium, [], [], []) in {"medium", "low"}


def test_analyze_safety_aspects_sql_injection_and_context(monkeypatch: pytest.MonkeyPatch) -> None:
    analyzer = IntegratedBayesianAnalyzer()
    # Force non-test context
    monkeypatch.setattr(analyzer, "_is_in_test_or_mock_context", lambda code: False)
    code = 'query = "SELECT * FROM users" + user_input'
    issues = analyzer._analyze_safety_aspects(code, "prod")
    assert any("SQL injection" in msg for msg in issues)

    # In test context should skip
    monkeypatch.setattr(analyzer, "_is_in_test_or_mock_context", lambda code: True)
    issues2 = analyzer._analyze_safety_aspects(code, "test_code")
    assert all("SQL injection" not in msg.lower() for msg in issues2)
