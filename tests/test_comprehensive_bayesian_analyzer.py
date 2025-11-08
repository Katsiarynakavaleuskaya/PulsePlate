#!/usr/bin/env python3
"""
Тесты для комплексного байесовского анализатора.
"""

import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.comprehensive_bayesian_analyzer import (
    ComprehensiveBayesianAnalyzer,
    ComprehensiveCategory,
    ComprehensiveTestResult,
)


class TestComprehensiveBayesianAnalyzer:
    """Тесты для комплексного байесовского анализатора."""

    def test_init(self) -> None:
        """Тест инициализации анализатора."""
        analyzer = ComprehensiveBayesianAnalyzer()
        assert analyzer is not None
        assert len(analyzer.comprehensive_results) == 0

    def test_analyze_comprehensively_technical_issues(self) -> None:
        """Тест анализа технических проблем."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Тест с техническими проблемами
        test_code = """
        async def test_something():
            mock = Mock()  # Должен быть AsyncMock
            result = mock.some_method()  # Должен быть await
            return result
        """

        result = analyzer.analyze_comprehensively(
            test_code, "test_technical_issues", "tests/test_example.py"
        )

        assert result.test_name == "test_technical_issues"
        assert result.technical_score < 1.0
        # Тест может быть успешным, если общий балл >= 0.8
        assert result.overall_score >= 0.8

    def test_analyze_comprehensively_nutrition_issues(self) -> None:
        """Тест анализа проблем питания."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Тест с проблемами питания
        test_code = """
        def test_nutrition():
            calories = 50  # Опасно низкое количество калорий
            bmi = 15.0  # Опасно низкий BMI
            return {"calories": calories, "bmi": bmi}
        """

        result = analyzer.analyze_comprehensively(
            test_code, "test_nutrition_issues", "tests/test_nutrition.py"
        )

        assert result.test_name == "test_nutrition_issues"
        # Critical nutrition issues should be detected
        assert len(result.critical_issues) > 0
        assert any(
            "калорий" in issue.lower() or "bmi" in issue.lower() for issue in result.critical_issues
        )
        # Health First policy: critical nutrition issues must cause failure
        assert result.success is False, "Critical nutrition issues should cause test failure"
        assert (
            result.overall_score < 0.8
        ), "Critical nutrition issues should reduce overall score below threshold"

    def test_analyze_comprehensively_business_issues(self) -> None:
        """Тест анализа бизнес-проблем."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Тест с бизнес-проблемами
        test_code = """
        def test_pricing():
            price = 0.5  # Слишком низкая цена
            subscription = 0.1  # Слишком низкая подписка
            return {"price": price, "subscription": subscription}
        """

        result = analyzer.analyze_comprehensively(
            test_code, "test_business_issues", "tests/test_business.py"
        )

        assert result.test_name == "test_business_issues"
        assert result.success is False
        assert result.business_score < 1.0
        assert len(result.optimization_opportunities) > 0

    def test_analyze_comprehensively_success(self) -> None:
        """Тест успешного анализа."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Тест без проблем
        test_code = """
        async def test_success():
            mock = AsyncMock()
            result = await mock.some_method()
            assert result is not None
            return result
        """

        result = analyzer.analyze_comprehensively(
            test_code, "test_success", "tests/test_success.py"
        )

        assert result.test_name == "test_success"
        assert result.success is True
        assert result.technical_score >= 0.8
        assert result.nutrition_score >= 0.8
        assert result.business_score >= 0.8
        assert result.overall_score >= 0.8
        assert len(result.critical_issues) == 0

    def test_get_comprehensive_diagnosis(self) -> None:
        """Тест получения комплексного диагноза."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Добавляем несколько результатов
        test_code1 = """
        async def test_technical():
            mock = Mock()  # Проблема
            return mock.method()
        """

        test_code2 = """
        def test_nutrition():
            calories = 30  # Проблема
            return calories
        """

        analyzer.analyze_comprehensively(test_code1, "test_technical", "tests/test1.py")
        analyzer.analyze_comprehensively(test_code2, "test_nutrition", "tests/test2.py")

        diagnosis = analyzer.get_comprehensive_diagnosis()

        assert diagnosis["status"] == "analyzed"
        assert diagnosis["total_tests"] == 2
        assert "average_scores" in diagnosis
        assert "risk_distribution" in diagnosis
        assert "optimization_opportunities" in diagnosis

    def test_generate_action_plan(self) -> None:
        """Тест генерации плана действий."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Добавляем проблемный результат
        test_code = """
        async def test_problematic():
            mock = Mock()  # Критическая проблема
            calories = 20  # Критическая проблема
            price = 0.1  # Критическая проблема
            return {"mock": mock, "calories": calories, "price": price}
        """

        analyzer.analyze_comprehensively(test_code, "test_problematic", "tests/test_problematic.py")

        action_plan = analyzer.generate_action_plan()

        assert "immediate_actions" in action_plan
        assert "short_term_actions" in action_plan
        assert "long_term_actions" in action_plan
        assert "cost_optimization" in action_plan
        assert "revenue_growth" in action_plan

        # План действий должен быть сгенерирован
        assert isinstance(action_plan["cost_optimization"], list)
        assert isinstance(action_plan["revenue_growth"], list)

    def test_calculate_technical_score(self) -> None:
        """Тест расчета технического балла."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Тест с разными типами проблем
        issues = [
            "Асинхронный метод без await",
            "Использование Mock вместо AsyncMock для асинхронных методов",
            "Отсутствует типизация возвращаемого значения",
        ]

        score = analyzer._calculate_technical_score(issues)
        assert score < 1.0
        assert score > 0.0

    def test_calculate_business_score(self) -> None:
        """Тест расчета бизнес-балла."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Тест с разными типами бизнес-проблем
        issues = [
            "Слишком низкая цена: $0.5",
            "Регистрация без валидации данных",
            "Отсутствует кэширование для частых запросов",
        ]

        score = analyzer._calculate_business_score(issues)
        assert score < 1.0
        assert score > 0.0

    def test_identify_critical_issues(self) -> None:
        """Тест идентификации критических проблем."""
        analyzer = ComprehensiveBayesianAnalyzer()

        technical_issues = ["Асинхронный метод без await", "Исключение без обработки"]
        nutrition_issues = ["Опасно низкое количество калорий: 30"]
        business_issues = ["Слишком низкая цена: $0.1", "Потеря потенциального дохода"]

        critical = analyzer._identify_critical_issues(
            technical_issues, nutrition_issues, business_issues
        )

        assert len(critical) > 0
        assert any("TECH:" in issue for issue in critical)
        assert any("HEALTH:" in issue for issue in critical)
        assert any("BUSINESS:" in issue for issue in critical)

    def test_assess_revenue_impact(self) -> None:
        """Тест оценки влияния на доходы."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Тест с проблемами, влияющими на доходы
        technical_issues = ["Проблема производительности"]
        nutrition_issues = ["Проблема безопасности"]
        business_issues = ["Проблема дохода", "Проблема дохода", "Проблема дохода"]

        impact = analyzer._assess_revenue_impact(
            technical_issues, nutrition_issues, business_issues
        )

        assert "влияние на доходы" in impact.lower()

    def test_calculate_risk_level(self) -> None:
        """Тест расчета уровня риска."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Тест с критическими проблемами
        critical_issues = [
            "TECH: Критическая проблема",
            "HEALTH: Критическая проблема",
            "BUSINESS: Критическая проблема",
        ]
        overall_score = 0.2

        risk_level = analyzer._calculate_risk_level(critical_issues, overall_score)

        assert risk_level in ["low", "medium", "high", "critical"]
        assert (
            risk_level == "critical"
        )  # Должен быть критический из-за множества проблем и низкого балла

    def test_calculate_priority(self) -> None:
        """Тест расчета приоритета."""
        analyzer = ComprehensiveBayesianAnalyzer()

        # Тест с критическими проблемами
        critical_issues = ["HEALTH: Критическая проблема здоровья"]
        revenue_impact = "Критическое влияние на доходы"
        health_impact = "Критическое влияние на здоровье"

        priority = analyzer._calculate_priority(critical_issues, revenue_impact, health_impact)

        assert priority in ["low", "medium", "high", "urgent"]
        assert priority == "urgent"  # Должен быть срочный из-за критических проблем здоровья
