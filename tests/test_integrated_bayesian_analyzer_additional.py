"""Integration tests for IntegratedBayesianAnalyzer behavior and edge cases."""

import pytest

from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer, NormalizedIssueType
from core.nutrition_bayesian_analyzer import (
    NutritionCategory,
    NutritionErrorType,
    NutritionTestResult,
)


def test_is_in_test_or_mock_context_variants() -> None:
    """Verify detection of test/mock contexts via AST and regex fallback."""
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

    # Unsafe open without context manager or closing() should be flagged
    unsafe_code = """
def bad():
    f = open("x.txt")
    data = f.read()
"""
    assert analyzer._check_unsafe_file_opens(unsafe_code) is True

    # Open wrapped by contextlib.closing should be treated as safe
    safe_closing_code = """
import contextlib

def good():
    with contextlib.closing(open("y.txt")) as f:
        data = f.read()
"""
    assert analyzer._check_unsafe_file_opens(safe_closing_code) is False


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

    # Constant string containing sensitive keyword
    code_constant = """
import logging
logger = logging.getLogger(__name__)
logger.warning("secret_key is set")
"""
    assert analyzer._check_sensitive_data_logging(code_constant) is True

    # Name argument containing sensitive keyword
    code_name_arg = """
import logging
password = "abc"
logger = logging.getLogger(__name__)
logger.error(password)
"""
    assert analyzer._check_sensitive_data_logging(code_name_arg) is True

    code_joined = """
import logging
token = "abc"
logger.info("token=" f"{token}")
"""
    assert analyzer._check_sensitive_data_logging(code_joined) is True


def test_analyze_safety_aspects_password_sql_and_context() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    # Non-test context: should flag both password and SQL injection
    code = """
password = "abc"
query = "SELECT * FROM users" + user_input
cursor.execute(query)
"""
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


def test_analyze_safety_aspects_sensitive_logging() -> None:
    """Ensure _analyze_safety_aspects reports sensitive logging issues."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
import logging
logger = logging.getLogger(__name__)
logger.info("password reset token leak")
"""
    issues = analyzer._analyze_safety_aspects(code, "prod_logging")
    assert any("logging sensitive data" in msg.lower() for msg in issues)


def test_check_potential_sql_injection_various_patterns() -> None:
    """Exercise multiple dynamic SQL construction patterns and execution contexts."""
    analyzer = IntegratedBayesianAnalyzer()

    # BinOp concatenation with assignment and positional execute()
    code_concat = """
user_input = "abc"
query = "SELECT * FROM users WHERE name=" + user_input
cursor.execute(query)
"""
    assert analyzer._check_potential_sql_injection(code_concat) is True

    # f-string passed directly to execute()
    code_fstring = """
user_id = "42"
cursor.execute(f"SELECT * FROM users WHERE id={user_id}")
"""
    assert analyzer._check_potential_sql_injection(code_fstring) is True

    # .format() assignment used as keyword argument in execute()
    code_format_kw = """
user_id = "42"
query = "SELECT * FROM users WHERE id={}".format(user_id)
cursor.execute(sql=query)
"""
    assert analyzer._check_potential_sql_injection(code_format_kw) is True

    # AugAssign building of SQL followed by execute()
    code_augassign = """
user_id = "42"
query = "SELECT * FROM users"
query += " SELECT * FROM logs" + user_id
cursor.execute(query)
"""
    assert analyzer._check_potential_sql_injection(code_augassign) is True

    # Annotated assignment followed by execute()
    code_annassign = """
user_input = "abc"
query: str = "SELECT * FROM users" + user_input
cursor.execute(query)
"""
    assert analyzer._check_potential_sql_injection(code_annassign) is True

    # Keyword argument with dynamic SQL expression passed directly
    code_kw_dynamic = """
user_input = "abc"
cursor.execute(sql="SELECT * FROM users" + user_input)
"""
    assert analyzer._check_potential_sql_injection(code_kw_dynamic) is True

    # Logging-only helper where logger is reached via attribute chain
    code_attr_logger_logging_only = """
import logging

class Wrapper:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

wrapper = Wrapper()
user_id = "42"
query = "SELECT * FROM users" + user_id
wrapper.logger.info(query)
"""
    assert analyzer._check_potential_sql_injection(code_attr_logger_logging_only) is False

    # Logging callable style (logger(...) / log(...)) should also be treated as logging
    code_callable_logging_only = """
def logger(message):
    pass

user_id = "42"
query = "SELECT * FROM users" + user_id
logger(query)
"""
    assert analyzer._check_potential_sql_injection(code_callable_logging_only) is False


def test_check_potential_sql_injection_ignores_logging_only() -> None:
    """Dynamic SQL used only in logging should not be flagged."""
    analyzer = IntegratedBayesianAnalyzer()

    code_logging_only = """
import logging
logger = logging.getLogger(__name__)
user_id = "42"
query = "SELECT * FROM users WHERE id=" + user_id
logger.info(query)
"""
    assert analyzer._check_potential_sql_injection(code_logging_only) is False


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


def test_is_in_test_or_mock_context_import_from_and_mock_calls() -> None:
    """Cover 'from mock import' and Mock/MagicMock/AsyncMock call patterns."""
    analyzer = IntegratedBayesianAnalyzer()

    code_from_mock = """
from mock import patch

@patch("mod.fn")
def fx():
    pass
"""
    assert analyzer._is_in_test_or_mock_context(code_from_mock) is True

    code_mock_calls = """
from unittest.mock import Mock, MagicMock, AsyncMock

def fx():
    m1 = Mock()
    m2 = MagicMock()
    m3 = AsyncMock()
"""
    assert analyzer._is_in_test_or_mock_context(code_mock_calls) is True


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
    # Both types should be present in a comprehensive safety violation
    assert NormalizedIssueType.DANGEROUS_INSTRUCTION in types
    assert NormalizedIssueType.HEALTH_VIOLATION in types

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
    # Document the expected behavior or fix the threshold logic
    assert analyzer._calculate_risk_level(medium, [], [], []) == "medium"


def test_comprehensive_analysis_and_diagnosis(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end smoke test for integrated analysis and diagnosis helpers."""
    analyzer = IntegratedBayesianAnalyzer()

    # Force deterministic technical issues
    monkeypatch.setattr(analyzer, "_analyze_technical_aspects", lambda code, name: ["tech-issue"])

    # Prepare structured dangerous nutrition result to exercise _last_nutrition_results path
    dangerous_result = NutritionTestResult(
        test_name="test_case",
        success=False,
        nutrition_category=NutritionCategory.BMI_SAFETY,
        error_type=NutritionErrorType.BMI_DANGEROUS,
        error_message="BMI dangerous",
        safety_level="dangerous",
    )
    safe_result = NutritionTestResult(
        test_name="test_case",
        success=True,
        nutrition_category=NutritionCategory.BMI_SAFETY,
    )
    monkeypatch.setattr(
        analyzer.nutrition_analyzer,
        "analyze_nutrition_safety",
        lambda code, name: [dangerous_result, safe_result],
    )

    # Deterministic safety/philosophy issues
    monkeypatch.setattr(analyzer, "_analyze_safety_aspects", lambda code, name: ["safety-issue"])
    monkeypatch.setattr(
        analyzer,
        "_analyze_philosophy_compliance",
        lambda code, name: ["philosophy-violation"],
    )

    # Run full analysis and ensure result is aggregated correctly
    result = analyzer.analyze_test_comprehensively("code", "test_case")
    assert result.test_name == "test_case"
    assert result.success is False
    assert result.technical_issues == ["tech-issue"]
    assert "BMI dangerous" in result.nutrition_issues[0]
    assert result.safety_issues == ["safety-issue"]
    assert result.philosophy_violations == ["philosophy-violation"]

    # get_comprehensive_diagnosis should summarize integrated_results and invoke
    # _generate_system_recommendations, exercising aggregation logic.
    diagnosis = analyzer.get_comprehensive_diagnosis()
    assert diagnosis["status"] == "analyzed"
    assert diagnosis["total_tests"] == 1
    assert diagnosis["successful_tests"] == 0
    assert diagnosis["risk_distribution"][result.overall_risk_level] == 1
    assert diagnosis["problem_areas"]["technical"] == len(result.technical_issues)
    assert diagnosis["problem_areas"]["nutrition"] == len(result.nutrition_issues)
    assert diagnosis["problem_areas"]["safety"] == len(result.safety_issues)
    assert diagnosis["problem_areas"]["philosophy"] == len(result.philosophy_violations)
    # System-wide recommendations should be non-empty when all categories have issues
    assert diagnosis["recommendations"]


@pytest.mark.parametrize(
    "is_test_context,code,expected_sql_injection,expected_other_checks",
    [
        (
            False,  # Non-test context
            'query = "SELECT * FROM users" + user_input\ncursor.execute(query)',
            True,  # Should detect SQL injection
            True,  # Other safety checks should be active
        ),
        (
            True,  # Test context
            'query = "SELECT * FROM users" + user_input\ncursor.execute(query)',
            False,  # Should NOT detect SQL injection in test context
            True,  # Other safety checks should still be active
        ),
    ],
)
def test_analyze_safety_aspects_sql_injection_context(
    monkeypatch: pytest.MonkeyPatch,
    is_test_context: bool,
    code: str,
    expected_sql_injection: bool,
    expected_other_checks: bool,
) -> None:
    """Test SQL injection detection respects test/mock context.

    In non-test context, SQL injection should be detected.
    In test context, SQL injection checks are skipped but other safety checks remain active.
    """
    analyzer = IntegratedBayesianAnalyzer()
    monkeypatch.setattr(analyzer, "_is_in_test_or_mock_context", lambda code: is_test_context)

    issues = analyzer._analyze_safety_aspects(code, "test_code" if is_test_context else "prod")

    has_sql_injection = any("sql injection" in msg.lower() for msg in issues)
    assert has_sql_injection == expected_sql_injection, (
        f"Expected SQL injection={'present' if expected_sql_injection else 'absent'} "
        f"in {'test' if is_test_context else 'non-test'} context, but got {issues}"
    )

    # Ensure other safety checks are still active (non-vacuous test)
    if expected_other_checks:
        # Test with code that should trigger other checks (e.g., command injection)
        other_code = 'os.system("rm -rf " + user_input)'
        other_issues = analyzer._analyze_safety_aspects(
            other_code, "test_code" if is_test_context else "prod"
        )
        assert len(other_issues) > 0, "Other safety checks should remain active"
