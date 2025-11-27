import builtins
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


def test_has_explicit_return_or_yield_variants():
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


def test_analyze_technical_aspects_common_regex_fallback_and_ast_branch():
    # AST path: async without await + Mock instead of AsyncMock
    code_ast = """
import asyncio

async def fetch():
    Mock()
"""
    issues_ast = tech_utils.analyze_technical_aspects_common(code_ast, "ast_path")
    assert "Async function without await usage" in issues_ast
    assert "Using Mock instead of AsyncMock for async methods" in issues_ast

    # Regex fallback path triggered via syntax error
    bad_code = "async def broken(:\n    Mock()\n"
    issues_regex = tech_utils.analyze_technical_aspects_common(bad_code, "regex_path")
    assert "Async function without await usage" in issues_regex
    assert "Using Mock instead of AsyncMock for async methods" in issues_regex


def test_business_load_business_knowledge_from_yaml(tmp_path, monkeypatch):
    config_dir = Path(__file__).resolve().parent.parent / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "business_knowledge.yaml"
    yaml_path.write_text("revenue_streams:\n  custom:\n    foo: 1\n", encoding="utf-8")

    monkeypatch.setattr(
        BusinessBayesianAnalyzer,
        "_import_yaml_module",
        staticmethod(lambda: SimpleNamespace(safe_load=lambda f: {"revenue_streams": {"custom": {"foo": 1}}})),
    )
    analyzer = BusinessBayesianAnalyzer()
    data = analyzer._load_business_knowledge()
    assert "revenue_streams" in data

    yaml_path.unlink()


def test_business_load_business_knowledge_invalid_yaml(monkeypatch, tmp_path):
    config_dir = Path(__file__).resolve().parent.parent / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "business_knowledge.yaml"
    yaml_path.write_text(":\n  bad: [", encoding="utf-8")

    monkeypatch.setattr(
        BusinessBayesianAnalyzer,
        "_import_yaml_module",
        staticmethod(
            lambda: SimpleNamespace(
                safe_load=lambda f: (_ for _ in ()).throw(ValueError("invalid")), YAMLError=ValueError
            )
        ),
    )
    analyzer = BusinessBayesianAnalyzer()
    data = analyzer._load_business_knowledge()
    assert "subscription" in data["revenue_streams"]

    yaml_path.unlink()


def test_comprehensive_scoring_and_impacts():
    analyzer = ComprehensiveBayesianAnalyzer()

    tech_issues = ["AsyncMock missing", "производительность низкая", "типизация отсутствует"]
    nutrition_issues = ["опасно высокие калории", "здоровье риск"]
    business_issues = ["revenue drop", "customer churn"]

    assert analyzer._calculate_technical_score(tech_issues) < 1.0
    assert analyzer._calculate_business_score(business_issues) < 1.0

    critical = analyzer._identify_critical_issues(tech_issues, nutrition_issues, business_issues)
    assert any(item.startswith("TECH") for item in critical)
    assert any(item.startswith("HEALTH") for item in critical)
    assert any(item.startswith("BUSINESS") for item in critical)

    opportunities = analyzer._identify_optimization_opportunities(
        ["cache layer", "async calls"], ["аллерген найден", "BMI high"], ["price high", "customer"]
    )
    assert any("кэш" in opt or "cache" in opt for opt in opportunities)
    assert any("аллерген" in opt for opt in opportunities)
    assert any("ценообраз" in opt.lower() or "цена" in opt.lower() for opt in opportunities)

    assert analyzer._assess_revenue_impact(tech_issues, nutrition_issues, business_issues).startswith(
        "Критическое"
    ) or "влияние" in analyzer._assess_revenue_impact(
        tech_issues, nutrition_issues, business_issues
    )
    assert analyzer._assess_cost_impact(tech_issues, nutrition_issues, business_issues) != ""
    assert analyzer._assess_customer_impact(tech_issues, nutrition_issues, business_issues) != ""
    assert analyzer._assess_health_impact(nutrition_issues) != ""

    risk_level = analyzer._calculate_risk_level(critical, overall_score=0.4)
    assert risk_level in {"critical", "high", "medium", "low"}

    priority = analyzer._calculate_priority(critical, "критическое влияние", "минимальное влияние")
    assert priority in {"urgent", "high", "medium", "low"}


def test_comprehensive_get_diagnosis_and_action_plan():
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


@pytest.mark.parametrize(
    "value,context,expected",
    [
        (200, "meal plan", True),
        (400, "daily total", False),
        (50, "", True),
    ],
)
def test_is_meal_level_value_basic(value, context, expected):
    assert is_meal_level_value(value, context) is expected


def test_is_meal_level_value_validation_errors():
    with pytest.raises(TypeError):
        is_meal_level_value("not_number")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        is_meal_level_value(float("inf"))
    with pytest.raises(ValueError):
        is_meal_level_value(-5)


def test_integrated_analyzer_sensitive_logging_and_unsafe_open():
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
