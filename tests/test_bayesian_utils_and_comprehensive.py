from pathlib import Path
from types import SimpleNamespace

import pytest

from core import bayesian_technical_utils as tech_utils
from core.business_bayesian_analyzer import BusinessBayesianAnalyzer
from core.comprehensive_bayesian_analyzer import (
    ComprehensiveBayesianAnalyzer,
    ComprehensiveTestResult,
)
from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer
from core.nutrition_constants import is_meal_level_value


def test_has_explicit_return_or_yield_variants() -> None:
    code = """
def with_return():
    return 1

def with_yield():
    yield 1

def bare_return():
    return

def outer():
    def inner():
        return 5
"""
    tree = tech_utils.ast.parse(code)
    funcs = {node.name: node for node in tree.body if isinstance(node, tech_utils.ast.FunctionDef)}

    assert tech_utils._has_explicit_return_or_yield(funcs["with_return"]) is True
    assert tech_utils._has_explicit_return_or_yield(funcs["with_yield"]) is True
    # Bare return should not count as explicit value
    assert tech_utils._has_explicit_return_or_yield(funcs["bare_return"]) is False
    # Nested function return should not influence outer
    assert tech_utils._has_explicit_return_or_yield(funcs["outer"]) is False


def test_has_explicit_return_or_yield_with_handlers() -> None:
    code = """
def with_try():
    try:
        return 2
    except Exception:
        return 1
"""
    tree = tech_utils.ast.parse(code)
    func = tree.body[0]
    assert tech_utils._has_explicit_return_or_yield(func) is True


def test_has_explicit_return_in_except_only_triggers_handlers_walk() -> None:
    code = """
def only_except():
    try:
        pass
    except Exception:
        return 3
"""
    tree = tech_utils.ast.parse(code)
    func = tree.body[0]
    # Return lives in except handler, so handler traversal must occur
    assert tech_utils._has_explicit_return_or_yield(func) is True


def test_analyze_technical_aspects_common_regex_fallback_and_ast_branch() -> None:
    # AST path: async without await + Mock instead of AsyncMock
    code_ast = """
import asyncio

async def fetch():
    Mock()
"""
    issues_ast = tech_utils.analyze_technical_aspects_common(code_ast)
    assert "Async function without await usage" in issues_ast
    assert "Using Mock instead of AsyncMock for async methods" in issues_ast

    # Regex fallback path triggered via syntax error
    bad_code = "async def broken(:\n    Mock()\n"
    issues_regex = tech_utils.analyze_technical_aspects_common(bad_code)
    assert "Async function without await usage" in issues_regex
    assert "Using Mock instead of AsyncMock for async methods" in issues_regex

    # Exception without handling should be reported
    raise_code = """
def bad():
    raise ValueError("oops")
"""
    issues_raise = tech_utils.analyze_technical_aspects_common(raise_code)
    assert "Exception raised without handling" in issues_raise

    # Missing return type annotation (AST path)
    missing_return = """
def foo():
    return 1
"""
    issues_missing = tech_utils.analyze_technical_aspects_common(missing_return)
    assert "Missing return type annotations" in issues_missing

    # Missing return type annotation (regex fallback path)
    bad_syntax = "def broken(:\n    return 1\n"
    issues_fallback = tech_utils.analyze_technical_aspects_common(bad_syntax)
    assert "Missing return type annotations" in issues_fallback


def test_business_load_business_knowledge_from_yaml(tmp_path, monkeypatch) -> None:
    # Use tmp_path to avoid modifying production config directory
    config_dir = tmp_path / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "business_knowledge.yaml"
    yaml_path.write_text(
        """revenue_streams:
  custom:
    foo: 1
""",
        encoding="utf-8",
    )

    # Monkeypatch __file__ to point to tmp_path so config path resolution uses tmp_path
    import core.business_bayesian_analyzer as bba_module

    original_file = bba_module.__file__
    mock_file = str(tmp_path / "core" / "business_bayesian_analyzer.py")
    monkeypatch.setattr(bba_module, "__file__", mock_file)

    monkeypatch.setattr(
        BusinessBayesianAnalyzer,
        "_import_yaml_module",
        staticmethod(
            lambda: SimpleNamespace(safe_load=lambda f: {"revenue_streams": {"custom": {"foo": 1}}})
        ),
    )
    analyzer = BusinessBayesianAnalyzer()
    data = analyzer._load_business_knowledge()
    assert "revenue_streams" in data

    # Restore original __file__
    monkeypatch.setattr(bba_module, "__file__", original_file)


def test_business_load_business_knowledge_invalid_yaml(monkeypatch, tmp_path) -> None:
    # Use tmp_path to avoid modifying production config directory
    config_dir = tmp_path / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "business_knowledge.yaml"
    yaml_path.write_text(
        """:
  bad: [
""",
        encoding="utf-8",
    )

    # Monkeypatch __file__ to point to tmp_path so config path resolution uses tmp_path
    import core.business_bayesian_analyzer as bba_module

    original_file = bba_module.__file__
    mock_file = str(tmp_path / "core" / "business_bayesian_analyzer.py")
    monkeypatch.setattr(bba_module, "__file__", mock_file)

    monkeypatch.setattr(
        BusinessBayesianAnalyzer,
        "_import_yaml_module",
        staticmethod(
            lambda: SimpleNamespace(
                safe_load=lambda f: (_ for _ in ()).throw(ValueError("invalid")),
                YAMLError=ValueError,
            )
        ),
    )
    analyzer = BusinessBayesianAnalyzer()
    data = analyzer._load_business_knowledge()
    assert "subscription" in data["revenue_streams"]

    # Restore original __file__
    monkeypatch.setattr(bba_module, "__file__", original_file)


def test_comprehensive_scoring_and_impacts() -> None:
    analyzer = ComprehensiveBayesianAnalyzer()

    tech_issues = ["AsyncMock missing", "производительность низкая", "типизация отсутствует"]
    nutrition_issues = ["опасно высокие калории", "здоровье риск"]
    business_issues = ["revenue drop", "customer churn"]

    assert analyzer._calculate_technical_score(tech_issues) < 1.0
    assert analyzer._calculate_business_score(business_issues) < 1.0

    critical = analyzer._identify_critical_issues(tech_issues, nutrition_issues, business_issues)
    assert any(item.startswith("TECH") for item in critical)
    assert any(item.startswith("HEALTH") for item in critical)
    assert any(item.lower().startswith("business:") for item in critical)

    opportunities = analyzer._identify_optimization_opportunities(
        ["cache layer", "async calls"], ["аллерген найден", "BMI high"], ["price high", "customer"]
    )
    assert any("кэш" in opt or "cache" in opt for opt in opportunities)
    assert any("аллерген" in opt for opt in opportunities)
    assert any("ценообраз" in opt.lower() or "цена" in opt.lower() for opt in opportunities)

    assert analyzer._assess_revenue_impact(
        tech_issues, nutrition_issues, business_issues
    ).startswith("Критическое") or "влияние" in analyzer._assess_revenue_impact(
        tech_issues, nutrition_issues, business_issues
    )
    assert analyzer._assess_cost_impact(tech_issues, nutrition_issues, business_issues) != ""
    assert analyzer._assess_customer_impact(tech_issues, nutrition_issues, business_issues) != ""
    assert analyzer._assess_health_impact(nutrition_issues) != ""

    risk_level = analyzer._calculate_risk_level(critical, overall_score=0.4)
    assert risk_level in {"critical", "high", "medium", "low"}

    priority = analyzer._calculate_priority(critical, "критическое влияние", "минимальное влияние")
    assert priority in {"urgent", "high", "medium", "low"}

    # Zero-issue branches for assess_* helpers
    assert analyzer._assess_revenue_impact([], [], []) == "Нет влияния на доходы"
    assert analyzer._assess_cost_impact([], [], []) == "Нет влияния на затраты"
    assert analyzer._assess_customer_impact([], [], []) == "Нет влияния на клиентов"
    assert analyzer._assess_health_impact([]) == "Нет влияния на здоровье"
    assert analyzer._has_critical_business_issues(["business: revenue"]) is True

    # Medium and critical impact branches
    med_revenue = analyzer._assess_revenue_impact(
        ["производительность", "производительность"], ["безопасность"], ["revenue"]
    )
    assert "Среднее" in med_revenue

    crit_revenue = analyzer._assess_revenue_impact(
        ["производительность"] * 6, ["безопасность"] * 2, ["revenue"]
    )
    assert "Критическое" in crit_revenue

    med_cost = analyzer._assess_cost_impact(["неэффективность", "неэффективность"], [], ["cost"])
    assert "Среднее" in med_cost

    crit_customer = analyzer._assess_customer_impact(
        ["пользователь"] * 3, ["здоровье"] * 3, ["customer"]
    )
    assert "Критическое" in crit_customer

    crit_health = analyzer._assess_health_impact(["опасно"] * 6)
    assert "Критическое" in crit_health


def test_comprehensive_get_diagnosis_and_action_plan() -> None:
    analyzer = ComprehensiveBayesianAnalyzer()
    empty = analyzer.get_comprehensive_diagnosis()
    assert empty["status"] == "no_data"

    analyzer.comprehensive_results.append(
        ComprehensiveTestResult(
            test_name="t1",
            success=False,
            technical_score=0.6,
            nutrition_score=1.0,
            business_score=0.5,
            overall_score=0.7,
            revenue_impact="Среднее влияние на доходы",
            cost_impact="Минимальное влияние на затраты",
            customer_impact="Минимальное влияние на клиентов",
            health_impact="Минимальное влияние на здоровье",
            risk_level="high",
            priority="high",
            critical_issues=["BUSINESS: revenue"],
            optimization_opportunities=["Оптимизировать стратегию ценообразования"],
        )
    )

    diagnosis = analyzer.get_comprehensive_diagnosis()
    assert diagnosis["status"] == "analyzed"
    assert diagnosis["total_tests"] == 1
    action_plan = analyzer.generate_action_plan()
    assert "immediate_actions" in action_plan
    assert "cost_optimization" in action_plan
    assert analyzer._has_critical_nutrition_issues(["dangerous calories"]) is True


@pytest.mark.parametrize(
    "value,context,expected",
    [
        (200, "meal plan", True),
        (400, "daily total", False),
        (50, "", True),
    ],
)
def test_is_meal_level_value_basic(value, context, expected) -> None:
    assert is_meal_level_value(value, context) is expected


def test_is_meal_level_value_validation_errors() -> None:
    with pytest.raises(TypeError):
        is_meal_level_value("not_number")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        is_meal_level_value(float("inf"))
    with pytest.raises(ValueError):
        is_meal_level_value(-5)


def test_integrated_analyzer_sensitive_logging_and_unsafe_open() -> None:
    analyzer = IntegratedBayesianAnalyzer()

    code_sensitive = """
import logging
logger.info("user password", token="abc")
"""
    assert analyzer._check_sensitive_data_logging(code_sensitive) is True

    code_safe = """
from contextlib import closing
f = open("foo.txt")
with closing(open("bar")) as fh:
    fh.read()
"""
    # open() without context manager should be flagged
    assert analyzer._check_unsafe_file_opens(code_safe) is True

    code_safe_context = """
with open("foo.txt") as fh:
    fh.read()
"""
    assert analyzer._check_unsafe_file_opens(code_safe_context) is False

    code_safe_closing = """
from contextlib import closing
with closing(open("bar.txt")) as fh:
    fh.read()
"""
    assert analyzer._check_unsafe_file_opens(code_safe_closing) is False

    test_ctx_code = """
import pytest
from unittest.mock import patch, Mock

@patch("mod.fn")
def helper():
    m = Mock()
    return m
"""
    assert analyzer._is_in_test_or_mock_context(test_ctx_code) is True


def test_comprehensive_analyze_comprehensively_paths(monkeypatch) -> None:
    analyzer = ComprehensiveBayesianAnalyzer()

    class StubResult:
        def __init__(self, success: bool, error_message: str | None = None) -> None:
            self.success = success
            self.error_message = error_message

    # Stub technical and business analyzers
    monkeypatch.setattr(analyzer.technical_analyzer, "analyze_technical_aspects", lambda c, t: [])
    monkeypatch.setattr(analyzer.business_analyzer, "analyze_business_logic", lambda c, t: [])

    # No nutrition results -> fallback contribution branch
    monkeypatch.setattr(analyzer.nutrition_analyzer, "analyze_nutrition_safety", lambda c, t: [])
    res_empty = analyzer.analyze_comprehensively("code", "test_no_nutrition", "file")
    assert res_empty.nutrition_score == 1.0

    # Critical nutrition issue forces overall_score to zero
    crit = StubResult(False, "dangerous bmi value")
    monkeypatch.setattr(
        analyzer.nutrition_analyzer, "analyze_nutrition_safety", lambda c, t: [crit]
    )
    res_crit = analyzer.analyze_comprehensively("code", "test_crit", "file")
    assert res_crit.overall_score == 0.0
