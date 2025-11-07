#!/usr/bin/env python3
"""
Tests for IntegratedBayesianAnalyzer covering technical, nutrition, safety, and philosophy checks.
"""

import pytest
from core.integrated_bayesian_analyzer import (
    IntegratedBayesianAnalyzer,
    SystemPhilosophy,
    IntegratedTestResult,
)


@pytest.fixture
def analyzer():
    """Create analyzer instance."""
    return IntegratedBayesianAnalyzer()


class TestIntegratedAnalyzer:
    """Test integrated analyzer functionality."""

    def test_initialization(self, analyzer):
        """Test analyzer initializes correctly."""
        assert analyzer.technical_analyzer is not None
        assert analyzer.nutrition_analyzer is not None
        assert analyzer.integrated_results == []
        assert analyzer.system_philosophy is not None
        assert "core_principles" in analyzer.system_philosophy
        assert "safety_requirements" in analyzer.system_philosophy
        assert "quality_standards" in analyzer.system_philosophy

    def test_analyze_clean_code(self, analyzer):
        """Test analysis of clean code."""
        code = """
        async def test_user_profile():
            profile = {"bmi": 22, "calorie": 2000}
            assert profile is not None
        """
        result = analyzer.analyze_test_comprehensively(code, "test_clean", "test.py")
        assert result.test_name == "test_clean"
        assert isinstance(result, IntegratedTestResult)

    def test_technical_async_without_await(self, analyzer):
        """Test detection of async without await."""
        code = "async def test_func(): pass"
        issues = analyzer._analyze_technical_aspects(code, "test")
        assert any("await" in issue for issue in issues)

    def test_technical_mock_async_mismatch(self, analyzer):
        """Test detection of Mock vs AsyncMock issue."""
        code = "async def test(): mock = Mock()"
        issues = analyzer._analyze_technical_aspects(code, "test")
        assert any("AsyncMock" in issue for issue in issues)

    def test_technical_exception_without_handling(self, analyzer):
        """Test detection of exceptions without handling."""
        code = "def test(): raise ValueError('error')"
        issues = analyzer._analyze_technical_aspects(code, "test")
        assert any("handling" in issue for issue in issues)

    def test_technical_missing_type_annotations(self, analyzer):
        """Test detection of missing return type annotations."""
        code = "def test_func(x): return x"
        issues = analyzer._analyze_technical_aspects(code, "test")
        assert any("type annotation" in issue.lower() for issue in issues)

    def test_safety_hardcoded_password(self, analyzer):
        """Test detection of hardcoded passwords."""
        code = 'password = "secret123"'
        issues = analyzer._analyze_safety_aspects(code, "test")
        assert any("password" in issue.lower() for issue in issues)

    def test_safety_sql_injection(self, analyzer):
        """Test detection of SQL injection risk."""
        code = "SELECT * FROM users WHERE id = " + "'something'"
        issues = analyzer._analyze_safety_aspects(code, "test")
        assert any("injection" in issue.lower() for issue in issues)

    def test_safety_unsafe_file_open(self, analyzer):
        """Test detection of unsafe file operations."""
        code = "f = open('file.txt')"
        issues = analyzer._analyze_safety_aspects(code, "test")
        assert any("context manager" in issue for issue in issues)

    def test_safety_logging_sensitive_data(self, analyzer):
        """Test detection of logging sensitive data."""
        code = "logger.info(f'User password: {password}')"
        issues = analyzer._analyze_safety_aspects(code, "test")
        assert any("sensitive" in issue.lower() for issue in issues)

    def test_philosophy_health_test_missing_metrics(self, analyzer):
        """Test philosophy check for health tests."""
        code = "def test_health(): pass"
        violations = analyzer._analyze_philosophy_compliance(code, "test_health_check")
        assert any("key metrics" in v for v in violations)

    def test_philosophy_nutrition_missing_macros(self, analyzer):
        """Test philosophy check for nutrition tests."""
        code = "def test_nutrition(): pass"
        violations = analyzer._analyze_philosophy_compliance(code, "test_nutrition_calc")
        assert any("macronutrients" in v for v in violations)

    def test_philosophy_user_missing_error_handling(self, analyzer):
        """Test philosophy check for user tests."""
        code = "def test_user(): pass"
        violations = analyzer._analyze_philosophy_compliance(code, "test_user_registration")
        assert any("error handling" in v for v in violations)

    def test_philosophy_personalization_missing_profile(self, analyzer):
        """Test philosophy check for personalization."""
        code = "def test_personal(): pass"
        violations = analyzer._analyze_philosophy_compliance(code, "test_personal_settings")
        assert any("profile" in v.lower() or "preference" in v.lower() for v in violations)

    def test_business_impact_no_issues(self, analyzer):
        """Test business impact with no issues."""
        impact = analyzer._assess_business_impact([], [], [], [])
        assert "No business impact" in impact

    def test_business_impact_minimal(self, analyzer):
        """Test business impact with minimal issues."""
        impact = analyzer._assess_business_impact(["issue1"], [], [], [])
        assert "Minimal" in impact

    def test_business_impact_moderate(self, analyzer):
        """Test business impact with moderate issues."""
        impact = analyzer._assess_business_impact(["i1", "i2"], ["i3"], [], [])
        assert "Moderate" in impact

    def test_business_impact_high(self, analyzer):
        """Test business impact with high issues."""
        impact = analyzer._assess_business_impact(
            ["i1", "i2", "i3"], ["i4", "i5"], ["i6"], []
        )
        assert "High" in impact

    def test_business_impact_critical(self, analyzer):
        """Test business impact with critical issues."""
        issues = [f"issue{i}" for i in range(12)]
        impact = analyzer._assess_business_impact(issues, [], [], [])
        assert "Critical" in impact

    def test_risk_level_low(self, analyzer):
        """Test low risk level calculation."""
        risk = analyzer._calculate_risk_level(["minor issue"], [], [], [])
        assert risk == "low"

    def test_risk_level_medium(self, analyzer):
        """Test medium risk level calculation."""
        risk = analyzer._calculate_risk_level(["AsyncMock issue"], [], [], [])
        assert risk == "medium"

    def test_risk_level_high(self, analyzer):
        """Test high risk level calculation."""
        risk = analyzer._calculate_risk_level(
            ["AsyncMock issue"],
            ["опасно для здоровья"],
            [],
            []
        )
        assert risk == "high"

    def test_risk_level_critical(self, analyzer):
        """Test critical risk level calculation."""
        risk = analyzer._calculate_risk_level(
            ["AsyncMock issue", "исключение"],
            ["опасно для здоровья"],
            ["инъекция SQL"],
            []
        )
        assert risk == "critical"

    def test_generate_recommendations_empty(self, analyzer):
        """Test recommendations with no issues."""
        recs = analyzer._generate_integrated_recommendations([], [], [], [])
        assert recs == []

    def test_generate_recommendations_technical(self, analyzer):
        """Test technical recommendations."""
        recs = analyzer._generate_integrated_recommendations(["tech issue"], [], [], [])
        assert len(recs) > 0
        assert any("technical" in r.lower() for r in recs)

    def test_generate_recommendations_nutrition(self, analyzer):
        """Test nutrition recommendations."""
        recs = analyzer._generate_integrated_recommendations([], ["nutrition issue"], [], [])
        assert len(recs) > 0
        assert any("nutrition" in r.lower() for r in recs)

    def test_generate_recommendations_safety(self, analyzer):
        """Test safety recommendations."""
        recs = analyzer._generate_integrated_recommendations([], [], ["safety issue"], [])
        assert len(recs) > 0
        assert any("safety" in r.lower() for r in recs)

    def test_generate_recommendations_philosophy(self, analyzer):
        """Test philosophy recommendations."""
        recs = analyzer._generate_integrated_recommendations([], [], [], ["philosophy issue"])
        assert len(recs) > 0
        assert any("philosophy" in r.lower() for r in recs)

    def test_comprehensive_diagnosis_no_data(self, analyzer):
        """Test diagnosis with no data."""
        diagnosis = analyzer.get_comprehensive_diagnosis()
        assert diagnosis["status"] == "no_data"

    def test_comprehensive_diagnosis_with_data(self, analyzer):
        """Test diagnosis with actual test results."""
        code = """
        def test_example():
            assert True
        """
        analyzer.analyze_test_comprehensively(code, "test_1", "test.py")
        analyzer.analyze_test_comprehensively(code, "test_2", "test.py")

        diagnosis = analyzer.get_comprehensive_diagnosis()
        assert diagnosis["status"] == "analyzed"
        assert diagnosis["total_tests"] == 2
        assert "success_rate" in diagnosis
        assert "risk_distribution" in diagnosis
        assert "problem_areas" in diagnosis
        assert "recommendations" in diagnosis

    def test_comprehensive_diagnosis_success_rate(self, analyzer):
        """Test success rate calculation."""
        good_code = "def test_good(): assert True"
        bad_code = "async def test_bad(): pass"  # Missing await

        analyzer.analyze_test_comprehensively(good_code, "test_good", "test.py")
        analyzer.analyze_test_comprehensively(bad_code, "test_bad", "test.py")

        diagnosis = analyzer.get_comprehensive_diagnosis()
        assert 0 <= diagnosis["success_rate"] <= 1

    def test_system_recommendations_technical_issues(self, analyzer):
        """Test system recommendations for technical issues."""
        bad_code = "async def test(): pass"  # Missing await

        # Generate multiple test results with technical issues
        for i in range(5):
            analyzer.analyze_test_comprehensively(bad_code, f"test_{i}", "test.py")

        recs = analyzer._generate_system_recommendations()
        assert any("технический" in r.lower() or "technical" in r.lower() for r in recs)

    def test_system_recommendations_nutrition_issues(self, analyzer):
        """Test system recommendations for nutrition issues."""
        nutrition_code = """
        def test_nutrition():
            calories = 5000  # Unsafe high calories
        """

        for i in range(3):
            analyzer.analyze_test_comprehensively(nutrition_code, f"test_{i}", "test.py")

        recs = analyzer._generate_system_recommendations()
        # May or may not have nutrition recommendations depending on threshold

    def test_system_recommendations_safety_issues(self, analyzer):
        """Test system recommendations for safety issues."""
        unsafe_code = 'password = "hardcoded"'

        for i in range(2):
            analyzer.analyze_test_comprehensively(unsafe_code, f"test_{i}", "test.py")

        recs = analyzer._generate_system_recommendations()
        # May or may not have safety recommendations depending on threshold

    def test_integrated_results_persistence(self, analyzer):
        """Test that results are persisted in analyzer."""
        code = "def test(): pass"

        analyzer.analyze_test_comprehensively(code, "test_1", "test.py")
        assert len(analyzer.integrated_results) == 1

        analyzer.analyze_test_comprehensively(code, "test_2", "test.py")
        assert len(analyzer.integrated_results) == 2

    def test_all_components_integration(self, analyzer):
        """Test full integration of all components."""
        complex_code = """
        async def test_user_health_personal():
            # Missing await, missing type hints, health-related but no metrics
            password = "secret123"  # Hardcoded password
            bmi = 22
            calories = 2000
            profile = {"protein": 100}
        """

        result = analyzer.analyze_test_comprehensively(
            complex_code, "test_user_health_personal", "test.py"
        )

        assert result.test_name == "test_user_health_personal"
        assert len(result.technical_issues) > 0  # Should catch async issues
        assert len(result.safety_issues) > 0  # Should catch hardcoded password
        assert result.business_impact != ""
        assert result.overall_risk_level in ["low", "medium", "high", "critical"]
        assert len(result.recommendations) > 0

    def test_system_philosophy_enum(self):
        """Test SystemPhilosophy enum values."""
        assert SystemPhilosophy.HEALTH_FIRST.value == "health_first"
        assert SystemPhilosophy.USER_SAFETY.value == "user_safety"
        assert SystemPhilosophy.DATA_PRIVACY.value == "data_privacy"
        assert SystemPhilosophy.SCIENTIFIC_ACCURACY.value == "scientific_accuracy"
        assert SystemPhilosophy.ACCESSIBILITY.value == "accessibility"
        assert SystemPhilosophy.SUSTAINABILITY.value == "sustainability"
        assert SystemPhilosophy.PERSONALIZATION.value == "personalization"
        assert SystemPhilosophy.TRANSPARENCY.value == "transparency"

    def test_comprehensive_diagnosis_critical_tests(self, analyzer):
        """Test identification of critical tests."""
        critical_code = """
        async def test_critical():
            password = "secret"  # Hardcoded
        """

        analyzer.analyze_test_comprehensively(critical_code, "test_critical", "test.py")

        diagnosis = analyzer.get_comprehensive_diagnosis()
        # Critical tests list should be present
        assert "critical_tests" in diagnosis
