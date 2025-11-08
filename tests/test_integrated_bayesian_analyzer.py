#!/usr/bin/env python3
"""
Тесты для IntegratedBayesianAnalyzer.

Покрытие для файла core/integrated_bayesian_analyzer.py
"""

import pytest
from core.integrated_bayesian_analyzer import (
    IntegratedBayesianAnalyzer,
    SystemPhilosophy,
    IntegratedTestResult,
)


class TestIntegratedBayesianAnalyzer:
    """Тесты для интегрированного байесовского анализатора."""

    def test_init(self):
        """Тест инициализации анализатора."""
        analyzer = IntegratedBayesianAnalyzer()
        assert analyzer.technical_analyzer is not None
        assert analyzer.nutrition_analyzer is not None
        assert analyzer.system_philosophy is not None
        assert len(analyzer.system_philosophy["core_principles"]) > 0
        assert len(analyzer.system_philosophy["safety_requirements"]) > 0
        assert len(analyzer.system_philosophy["quality_standards"]) > 0

    def test_load_system_philosophy(self):
        """Тест загрузки философии системы."""
        analyzer = IntegratedBayesianAnalyzer()
        philosophy = analyzer._load_system_philosophy()

        assert "core_principles" in philosophy
        assert "safety_requirements" in philosophy
        assert "quality_standards" in philosophy
        assert len(philosophy["core_principles"]) == 7
        assert "97% покрытие тестами" in philosophy["quality_standards"]

    def test_analyze_test_comprehensively_simple(self):
        """Тест комплексного анализа простого теста."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_simple():
    assert True
"""
        result = analyzer.analyze_test_comprehensively(test_code, "test_simple", "test_file.py")

        assert isinstance(result, IntegratedTestResult)
        assert result.test_name == "test_simple"
        assert result.success is True  # no issues
        assert result.overall_risk_level in ["low", "medium", "high", "critical"]

    def test_analyze_test_comprehensively_with_issues(self):
        """Тест анализа теста с проблемами."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_with_hardcoded_password():
    password = "admin123"
    assert True
"""
        result = analyzer.analyze_test_comprehensively(
            test_code, "test_with_hardcoded_password", "test_file.py"
        )

        assert isinstance(result, IntegratedTestResult)
        assert len(result.safety_issues) > 0
        assert any("password" in issue.lower() for issue in result.safety_issues)

    def test_analyze_technical_aspects(self):
        """Тест анализа технических аспектов."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
async def test_async_function():
    result = await some_function()
    assert result == expected
"""
        issues = analyzer._analyze_technical_aspects(test_code, "test_async_function")

        assert isinstance(issues, list)

    def test_analyze_safety_aspects_hardcoded_password(self):
        """Тест обнаружения хардкоженного пароля."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_login():
    password = "secret123"
    assert True
"""
        issues = analyzer._analyze_safety_aspects(test_code, "test_login")

        assert len(issues) > 0
        assert any("password" in issue.lower() for issue in issues)

    def test_analyze_safety_aspects_sql_injection(self):
        """Тест обнаружения потенциальной SQL инъекции."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_query():
    user_id = get_user_id()
    query = "SELECT * FROM users WHERE id = " + user_id
    result = execute_query(query)
    assert result is not None
"""
        issues = analyzer._analyze_safety_aspects(test_code, "test_query")

        assert len(issues) > 0
        assert any("sql" in issue.lower() or "injection" in issue.lower() for issue in issues)

    def test_analyze_safety_aspects_unsafe_file_open(self):
        """Тест обнаружения небезопасного открытия файлов."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_file():
    f = open("file.txt")
    data = f.read()
    f.close()
"""
        issues = analyzer._analyze_safety_aspects(test_code, "test_file")

        assert len(issues) > 0
        assert any("file" in issue.lower() or "context" in issue.lower() for issue in issues)

    def test_analyze_safety_aspects_logging_sensitive_data(self):
        """Тест обнаружения логирования чувствительных данных."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_logging():
    logger.info(f"User password: {password}")
    assert True
"""
        issues = analyzer._analyze_safety_aspects(test_code, "test_logging")

        assert len(issues) > 0
        assert any("sensitive" in issue.lower() or "logging" in issue.lower() for issue in issues)

    def test_analyze_philosophy_compliance_health_test(self):
        """Тест проверки соответствия философии для health-теста."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_health_metrics():
    user = get_user()
    assert user.name == "John"
    assert user.age == 30
"""
        violations = analyzer._analyze_philosophy_compliance(test_code, "test_health_metrics")

        assert len(violations) > 0
        assert any("health" in v.lower() or "metric" in v.lower() for v in violations)

    def test_analyze_philosophy_compliance_nutrition_test(self):
        """Тест проверки соответствия философии для nutrition-теста."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_nutrition_plan():
    plan = get_nutrition_plan()
    assert plan.name == "Plan A"
    assert plan.duration == 30
"""
        violations = analyzer._analyze_philosophy_compliance(test_code, "test_nutrition_plan")

        assert len(violations) > 0
        assert any("nutrition" in v.lower() or "macronutrient" in v.lower() for v in violations)

    def test_analyze_philosophy_compliance_user_test(self):
        """Тест проверки соответствия философии для user-теста."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_user_profile():
    user = get_user()
    assert user is not None
    assert user.name == "John"
"""
        violations = analyzer._analyze_philosophy_compliance(test_code, "test_user_profile")

        assert len(violations) > 0
        assert any("error" in v.lower() or "handling" in v.lower() for v in violations)

    def test_analyze_philosophy_compliance_personalization_test(self):
        """Тест проверки соответствия философии для personalization-теста."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = """
def test_personalization():
    result = personalize()
    assert result is not None
    assert result.user_id == 123
"""
        violations = analyzer._analyze_philosophy_compliance(test_code, "test_personalization")

        assert len(violations) > 0
        assert any(
            "personal" in v.lower() or "profile" in v.lower() or "preference" in v.lower()
            for v in violations
        )

    def test_assess_business_impact_no_issues(self):
        """Тест оценки бизнес-воздействия без проблем."""
        analyzer = IntegratedBayesianAnalyzer()
        impact = analyzer._assess_business_impact([], [], [], [])

        assert impact == "No business impact"

    def test_assess_business_impact_minimal(self):
        """Тест оценки минимального бизнес-воздействия."""
        analyzer = IntegratedBayesianAnalyzer()
        impact = analyzer._assess_business_impact(["issue1"], [], [], ["issue2"])

        assert impact == "Minimal impact on user experience"

    def test_assess_business_impact_moderate(self):
        """Тест оценки умеренного бизнес-воздействия."""
        analyzer = IntegratedBayesianAnalyzer()
        impact = analyzer._assess_business_impact(["i1", "i2"], ["i3"], ["i4"], ["i5"])

        assert impact == "Moderate impact on product quality"

    def test_assess_business_impact_high(self):
        """Тест оценки высокого бизнес-воздействия."""
        analyzer = IntegratedBayesianAnalyzer()
        impact = analyzer._assess_business_impact(
            ["i1", "i2", "i3"], ["i4", "i5"], ["i6"], ["i7", "i8"]
        )

        assert impact == "High impact on reputation and safety"

    def test_assess_business_impact_critical(self):
        """Тест оценки критического бизнес-воздействия."""
        analyzer = IntegratedBayesianAnalyzer()
        impact = analyzer._assess_business_impact(
            ["i1", "i2", "i3", "i4"], ["i5", "i6", "i7"], ["i8", "i9"], ["i10", "i11", "i12"]
        )

        assert impact == "Critical impact on business operations"

    def test_calculate_risk_level_low(self):
        """Тест расчета низкого уровня риска."""
        analyzer = IntegratedBayesianAnalyzer()
        risk = analyzer._calculate_risk_level([], [], [], [])

        assert risk == "low"

    def test_calculate_risk_level_medium(self):
        """Тест расчета среднего уровня риска."""
        analyzer = IntegratedBayesianAnalyzer()
        risk = analyzer._calculate_risk_level(["AsyncMock issue"], [], [], [])

        assert risk == "medium"

    def test_calculate_risk_level_high(self):
        """Тест расчета высокого уровня риска."""
        analyzer = IntegratedBayesianAnalyzer()
        risk = analyzer._calculate_risk_level(
            ["AsyncMock issue"], ["опасно высокие калории"], [], []
        )

        assert risk == "high"

    def test_calculate_risk_level_critical(self):
        """Тест расчета критического уровня риска."""
        analyzer = IntegratedBayesianAnalyzer()
        risk = analyzer._calculate_risk_level(
            ["AsyncMock issue"],
            ["опасно высокие калории"],
            ["SQL injection"],
            ["здоровье под угрозой"],
        )

        assert risk == "critical"

    def test_generate_integrated_recommendations(self):
        """Тест генерации интегрированных рекомендаций."""
        analyzer = IntegratedBayesianAnalyzer()
        recommendations = analyzer._generate_integrated_recommendations(
            ["tech1", "tech2"], ["nutr1"], ["safe1"], ["phil1"]
        )

        assert len(recommendations) == 4
        assert any("technical" in r.lower() for r in recommendations)
        assert any("nutrition" in r.lower() for r in recommendations)
        assert any("safety" in r.lower() for r in recommendations)
        assert any("philosophy" in r.lower() for r in recommendations)

    def test_get_comprehensive_diagnosis_no_data(self):
        """Тест получения диагноза без данных."""
        analyzer = IntegratedBayesianAnalyzer()
        diagnosis = analyzer.get_comprehensive_diagnosis()

        assert diagnosis["status"] == "no_data"

    def test_get_comprehensive_diagnosis_with_data(self):
        """Тест получения диагноза с данными."""
        analyzer = IntegratedBayesianAnalyzer()

        # Add some test results
        test_code = "def test_simple(): assert True"
        analyzer.analyze_test_comprehensively(test_code, "test_1", "test.py")
        analyzer.analyze_test_comprehensively(test_code, "test_2", "test.py")

        diagnosis = analyzer.get_comprehensive_diagnosis()

        assert diagnosis["status"] == "analyzed"
        assert diagnosis["total_tests"] == 2
        assert "success_rate" in diagnosis
        assert "risk_distribution" in diagnosis
        assert "problem_areas" in diagnosis
        assert "recommendations" in diagnosis

    def test_generate_system_recommendations_no_issues(self):
        """Тест генерации системных рекомендаций без проблем."""
        analyzer = IntegratedBayesianAnalyzer()

        test_code = "def test_simple(): assert True"
        analyzer.analyze_test_comprehensively(test_code, "test_1", "test.py")

        recommendations = analyzer._generate_system_recommendations()

        assert isinstance(recommendations, list)

    def test_generate_system_recommendations_with_technical_issues(self):
        """Тест генерации рекомендаций с техническими проблемами."""
        analyzer = IntegratedBayesianAnalyzer()

        # Create multiple tests with technical issues
        for i in range(5):
            result = IntegratedTestResult(
                test_name=f"test_{i}",
                success=False,
                technical_issues=["AsyncMock issue", "Type error"],
                nutrition_issues=[],
                safety_issues=[],
                philosophy_violations=[],
                business_impact="moderate",
                overall_risk_level="medium",
                recommendations=[],
            )
            analyzer.integrated_results.append(result)

        recommendations = analyzer._generate_system_recommendations()

        assert any("рефакторинг" in r.lower() or "refactor" in r.lower() for r in recommendations)

    def test_system_philosophy_enum(self):
        """Тест enum SystemPhilosophy."""
        assert SystemPhilosophy.HEALTH_FIRST.value == "health_first"
        assert SystemPhilosophy.USER_SAFETY.value == "user_safety"
        assert SystemPhilosophy.DATA_PRIVACY.value == "data_privacy"
        assert SystemPhilosophy.SCIENTIFIC_ACCURACY.value == "scientific_accuracy"
        assert SystemPhilosophy.ACCESSIBILITY.value == "accessibility"
        assert SystemPhilosophy.SUSTAINABILITY.value == "sustainability"
        assert SystemPhilosophy.PERSONALIZATION.value == "personalization"
        assert SystemPhilosophy.TRANSPARENCY.value == "transparency"

    def test_integrated_test_result_dataclass(self):
        """Тест dataclass IntegratedTestResult."""
        result = IntegratedTestResult(
            test_name="test_example",
            success=True,
            technical_issues=[],
            nutrition_issues=[],
            safety_issues=[],
            philosophy_violations=[],
            business_impact="No business impact",
            overall_risk_level="low",
            recommendations=[],
        )

        assert result.test_name == "test_example"
        assert result.success is True
        assert result.business_impact == "No business impact"
        assert result.overall_risk_level == "low"
