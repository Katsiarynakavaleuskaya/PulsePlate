"""
Targeted coverage tests for comprehensive and integrated Bayesian analyzers.

RU: Проверяем критические ветки комплексного и интегрированного анализаторов,
чтобы зафиксировать расчёт рисков, приоритетов и детекцию утечек.
EN: Exercise high-impact branches in the comprehensive and integrated analyzers
covering risk calculations, priority handling, and sensitive-data detection.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List, cast

import pytest

from core.business_bayesian_analyzer import BusinessCategory, BusinessErrorType, BusinessTestResult
from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer
from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer, NormalizedIssueType
from core.nutrition_bayesian_analyzer import NutritionCategory, NutritionTestResult


def _make_nutrition_result(message: str, success: bool = False) -> NutritionTestResult:
    """RU/EN: Helper to create nutrition results with bilingual comment."""

    return NutritionTestResult(
        test_name="suite::test_case",
        success=success,
        nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
        error_type=None,
        error_message=message,
        business_impact="impact",
        safety_level="dangerous",
    )


def test_comprehensive_analyzer_handles_critical_nutrition(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: Critical nutrition issues should zero the overall score."""

    analyzer = ComprehensiveBayesianAnalyzer()

    analyzer.technical_analyzer = cast(
        Any,
        SimpleNamespace(
            analyze_technical_aspects=lambda code, name: [
                "AsyncMock missing",
                "Cache invalidation",
                "Проблемы производительности",
                "Неэффективный сервис",
                "Пользователь жалуется",
            ]
        ),
    )

    analyzer.nutrition_analyzer = cast(
        Any,
        SimpleNamespace(
            analyze_nutrition_safety=lambda code, name: [
                _make_nutrition_result("Опасно низкий BMI"),
                _make_nutrition_result("dangerous calorie deficit"),
            ],
            get_safety_score=lambda: 0.2,
        ),
    )

    analyzer.business_analyzer = cast(
        Any,
        SimpleNamespace(
            analyze_business_logic=lambda code, name: [
                BusinessTestResult(
                    test_name=name,
                    success=False,
                    business_category=BusinessCategory.MONETIZATION,
                    error_type=BusinessErrorType.REVENUE_LEAK,
                    error_message="Падение доходов и рост затрат",
                    revenue_impact="loss",
                    cost_impact="high spend",
                    customer_impact="churn",
                    optimization_potential="raise price",
                ),
                BusinessTestResult(
                    test_name=name,
                    success=False,
                    business_category=BusinessCategory.CUSTOMER_ACQUISITION,
                    error_type=BusinessErrorType.CUSTOMER_CHURN,
                    error_message="Клиент уходит без онбординга",
                    customer_impact="retention",
                ),
            ],
            generate_cost_savings_recommendations=lambda: ["Оптимизировать инфраструктуру"],
            generate_revenue_optimization_recommendations=lambda: ["Добавить A/B тестирование цен"],
        ),
    )

    result = analyzer.analyze_comprehensively(
        "password = 'secret'", "suite::test_case", "tests/sample.py"
    )

    assert result.overall_score == 0.0
    assert any(issue.startswith("HEALTH") for issue in result.critical_issues)
    assert result.risk_level
    assert result.priority
    assert any(
        "кэш" in rec.lower() or "ценообразования" in rec.lower()
        for rec in result.optimization_opportunities
    )
    diagnosis = analyzer.get_comprehensive_diagnosis()
    assert diagnosis["status"] == "analyzed"
    action_plan = analyzer.generate_action_plan()
    assert action_plan["immediate_actions"]


def test_has_critical_business_issues_detects_prefix() -> None:
    """RU/EN: helper should detect prefixed business issues."""

    analyzer = ComprehensiveBayesianAnalyzer()
    assert analyzer._has_critical_business_issues(["BUSINESS: Revenue drop"])
    assert analyzer._has_critical_business_issues([]) is False


def test_integrated_analyzer_detects_sensitive_patterns() -> None:
    """RU/EN: Integrated analyzer should catch unsafe logging and open()."""

    analyzer = IntegratedBayesianAnalyzer()

    unsafe_code = """
import logging
logger = logging.getLogger(__name__)

def leak(api_key, path):
    logger.error("API_KEY leaked: %s", api_key)
    data = open(path)
    return data.read()
"""
    assert analyzer._check_sensitive_data_logging(unsafe_code) is True
    assert analyzer._check_unsafe_file_opens(unsafe_code) is True

    safe_code = """
def load(path):
    with open(path) as handle:
        return handle.read()
"""
    assert analyzer._check_unsafe_file_opens(safe_code) is False


def test_integrated_analyzer_comprehensive_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: analyze_test_comprehensively aggregates issues and recommendations."""

    analyzer = IntegratedBayesianAnalyzer()

    analyzer.technical_analyzer = cast(
        Any,
        SimpleNamespace(
            _analyze_technical_aspects=lambda code, name: [
                "Mock usage without AsyncMock",
                "SQL injection risk",
                "dangerous instruction logged",
            ]
        ),
    )
    analyzer.nutrition_analyzer = cast(
        Any,
        SimpleNamespace(
            analyze_nutrition_safety=lambda code, name: [
                _make_nutrition_result("dangerous allergen")
            ],
        ),
    )
    cast(Any, analyzer)._analyze_safety_aspects = lambda code, name: ["Hardcoded password detected"]
    cast(Any, analyzer)._analyze_philosophy_compliance = lambda code, name: [
        "Нарушение философии бренда",
        "Логирование чувствительных данных",
    ]
    cast(Any, analyzer)._assess_business_impact = lambda *args: {
        "revenue": "risk",
        "customers": "drop",
    }

    result = analyzer.analyze_test_comprehensively(
        "password = '1234'\nlogger.info('token=%s', token)\n", "suite::test_phi", "tests/phi.py"
    )

    assert result.business_impact
    assert result.recommendations
    assert result.overall_risk_level
    system_diagnosis = analyzer.get_comprehensive_diagnosis()
    assert system_diagnosis["status"] == "analyzed"
    recs = analyzer._generate_system_recommendations()
    assert recs


def test_comprehensive_assessment_levels() -> None:
    """RU/EN: Ensure assessment helpers cover multiple severity levels."""

    analyzer = ComprehensiveBayesianAnalyzer()
    assert analyzer._assess_revenue_impact([], [], []) == "Нет влияния на доходы"
    assert (
        analyzer._assess_revenue_impact(["производительность сервиса низкая"], [], [])
        == "Минимальное влияние на доходы"
    )
    assert (
        analyzer._assess_revenue_impact(
            ["производительность сервиса низкая", "производительность системы"],
            ["безопасность питания нарушена", "безопасность процессов нарушена"],
            ["Loss of revenue", "доход падает", "revenue decline", "revenue loss"],
        )
        == "Критическое влияние на доходы"
    )

    assert analyzer._assess_cost_impact([], [], []) == "Нет влияния на затраты"
    assert (
        analyzer._assess_cost_impact(["Неэффективный сервис"], [], ["Рост затрат"])
        == "Минимальное влияние на затраты"
    )

    assert analyzer._assess_customer_impact([], [], []) == "Нет влияния на клиентов"
    assert (
        analyzer._assess_customer_impact(
            ["Пользователь недоволен"],
            ["здоровье под угрозой"],
            ["Клиент уходит", "customer churn"],
        )
        == "Среднее влияние на клиентов"
    )

    assert (
        analyzer._assess_health_impact(["Опасно низкие калории"])
        == "Минимальное влияние на здоровье"
    )
    assert analyzer._calculate_risk_level(["critical_issue"] * 3, 0.6) == "high"
    assert analyzer._calculate_risk_level([], 0.95) == "low"
    assert (
        analyzer._calculate_priority(["crit1", "crit2", "crit3"], "мин", "критическое") == "urgent"
    )
    assert analyzer._calculate_system_health(0.95, {"low": 2}) == "excellent"
    assert analyzer._calculate_system_health(0.85, {"high": 2}) == "good"
    assert analyzer._calculate_system_health(0.65, {"critical": 1}) == "fair"


def test_integrated_normalize_issue_type_variants() -> None:
    """RU/EN: Normalization should detect multiple issue categories."""

    analyzer = IntegratedBayesianAnalyzer()
    normalized = analyzer._normalize_issue_type(
        "SQL injection causes password leak and unsafe operation"
    )
    assert NormalizedIssueType.INJECTION in normalized
    assert NormalizedIssueType.PASSWORD_LEAK in normalized
    assert NormalizedIssueType.DANGEROUS_INSTRUCTION in normalized

    normalized_extra = analyzer._normalize_issue_type(
        "async error triggers exception and violates safety and health nutrition checks"
    )
    assert NormalizedIssueType.ASYNC_ERROR in normalized_extra
    assert NormalizedIssueType.EXCEPTION_HANDLING in normalized_extra
    assert NormalizedIssueType.SAFETY_VIOLATION in normalized_extra
    assert NormalizedIssueType.HEALTH_VIOLATION in normalized_extra

    risk_critical = analyzer._calculate_risk_level(
        ["SQL injection", "dangerous instruction", "password leak"],
        [],
        [],
        [],
    )
    assert risk_critical == "critical"
    risk_low = analyzer._calculate_risk_level([], [], [], [])
    assert risk_low == "low"


def test_integrated_syntax_fallbacks() -> None:
    """RU/EN: Ensure syntax fallbacks return safe defaults."""

    analyzer = IntegratedBayesianAnalyzer()
    assert analyzer._check_unsafe_file_opens("def broken(:\n    pass") is False
    assert analyzer._check_sensitive_data_logging('logger.info("token"') is True
    safe_code = """
import contextlib
def safe():
    with contextlib.closing(open("file.txt")) as handle:
        return handle
"""
    assert analyzer._check_unsafe_file_opens(safe_code) is False


def test_sensitive_logging_variants() -> None:
    """RU/EN: Detect sensitive data across constant, name, and f-string usages."""

    analyzer = IntegratedBayesianAnalyzer()
    code = """
import logging
logger = logging.getLogger(__name__)
password = "hunter2"
token_value = get_token()
logger.debug("Password leaked: %s", password)
logger.info("Token %s", token_value)
logger.warning(f"secret: {password}")
"""
    assert analyzer._check_sensitive_data_logging(code) is True


def test_comprehensive_score_defaults() -> None:
    """RU/EN: Verify score helpers default to perfect score without issues."""

    analyzer = ComprehensiveBayesianAnalyzer()
    assert analyzer._calculate_technical_score([]) == 1.0
    assert analyzer._calculate_business_score([]) == 1.0
    assert analyzer._assess_revenue_impact([], [], []) == "Нет влияния на доходы"


def test_identify_optimization_opportunities_full() -> None:
    """RU/EN: Ensure optimization detector aggregates across categories."""

    analyzer = ComprehensiveBayesianAnalyzer()
    opportunities = analyzer._identify_optimization_opportunities(
        ["Нужно кэширование", "async tasks pending"],
        ["аллерген не проверен", "bmi issues"],
        ["цена завышена", "клиент уходит"],
    )
    assert "Добавить кэширование для повышения производительности" in opportunities
    assert "Оптимизировать асинхронные операции" in opportunities
    assert "Улучшить систему проверки аллергенов" in opportunities
    assert "Добавить расширенную аналитику BMI" in opportunities
    assert "Оптимизировать стратегию ценообразования" in opportunities
    assert "Улучшить процесс привлечения клиентов" in opportunities


def test_cost_impact_thresholds() -> None:
    """RU/EN: Cover each cost impact classification branch."""

    analyzer = ComprehensiveBayesianAnalyzer()
    assert analyzer._assess_cost_impact([], [], []) == "Нет влияния на затраты"

    minimal = analyzer._assess_cost_impact(
        ["неэффективный код"],
        [],
        ["Снижение затрат на поддержку"],
    )
    assert minimal == "Минимальное влияние на затраты"

    medium = analyzer._assess_cost_impact(
        ["неэффективный алгоритм", "неэффективный кэш", "неэффективная БД"],
        [],
        [],
    )
    assert medium == "Среднее влияние на затраты"

    critical = analyzer._assess_cost_impact(
        ["неэффективный сервис"] * 3,
        [],
        ["Рост затрат"] * 3,
    )
    assert critical == "Критическое влияние на затраты"


def test_health_impact_critical_branch() -> None:
    """RU/EN: Health impact escalates to critical with many dangerous issues."""

    analyzer = ComprehensiveBayesianAnalyzer()
    assert (
        analyzer._assess_health_impact(
            ["Опасно низкие калории", "Dangerous sugar intake", "Опасно высокий холестерин"]
        )
        == "Среднее влияние на здоровье"
    )
    assert analyzer._assess_health_impact(["опасно"] * 6) == "Критическое влияние на здоровье"


def test_action_plan_handles_no_data() -> None:
    """RU/EN: Action plan should return empty actions without data."""

    analyzer = ComprehensiveBayesianAnalyzer()
    assert analyzer.generate_action_plan() == {
        "immediate_actions": [],
        "short_term_actions": [],
        "long_term_actions": [],
        "cost_optimization": [],
        "revenue_growth": [],
    }


def test_unsafe_open_detector_handles_async_and_closing() -> None:
    """RU/EN: Async contexts and contextlib.closing should not raise warnings."""

    analyzer = IntegratedBayesianAnalyzer()
    async_code = """
import contextlib

@contextlib.asynccontextmanager
async def guard():
    yield

async def use_async():
    async with guard():
        open("file.txt")
"""
    assert analyzer._check_unsafe_file_opens(async_code) is False

    closing_code_attr = """
import contextlib

def use_closing_attr():
    handle = contextlib.closing(open("file.txt"))
    return handle
"""
    assert analyzer._check_unsafe_file_opens(closing_code_attr) is False

    closing_code_direct = """
from contextlib import closing

def use_closing_import():
    resource = closing(open("data.csv"))
    return resource
"""
    assert analyzer._check_unsafe_file_opens(closing_code_direct) is False


def test_sensitive_logging_fallbacks_and_formats() -> None:
    """RU/EN: Syntax fallback and formatted strings should detect leaks."""

    analyzer = IntegratedBayesianAnalyzer()
    syntax_error_code = 'logger.info("token"'
    assert analyzer._check_sensitive_data_logging(syntax_error_code) is True

    formatted_code = """
import logging
logger = logging.getLogger(__name__)
api_key = "abc123"
logger.warning(f"leak: {api_key}")
"""
    assert analyzer._check_sensitive_data_logging(formatted_code) is True
