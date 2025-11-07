"""
Unit tests for IntegratedBayesianAnalyzer.

Tests the comprehensive analysis combining technical, nutrition, safety,
and philosophy compliance checks.
"""

from core.integrated_bayesian_analyzer import (
    IntegratedBayesianAnalyzer,
    IntegratedTestResult,
    SystemPhilosophy,
)


def test_init() -> None:
    """Test analyzer initialization."""
    analyzer = IntegratedBayesianAnalyzer()

    assert analyzer.technical_analyzer is not None
    assert analyzer.nutrition_analyzer is not None
    assert analyzer.integrated_results == []
    assert analyzer.system_philosophy is not None
    assert "core_principles" in analyzer.system_philosophy
    assert "safety_requirements" in analyzer.system_philosophy
    assert "quality_standards" in analyzer.system_philosophy


def test_load_system_philosophy() -> None:
    """Test system philosophy loading."""
    analyzer = IntegratedBayesianAnalyzer()
    philosophy = analyzer._load_system_philosophy()

    assert len(philosophy["core_principles"]) == 7
    assert len(philosophy["safety_requirements"]) == 5
    assert len(philosophy["quality_standards"]) == 4
    assert "Здоровье пользователя превыше всего" in philosophy["core_principles"]


def test_analyze_technical_aspects_async_without_await() -> None:
    """Test detection of async functions without await."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    async def test_function():
        result = some_sync_call()
        return result
    """

    issues = analyzer._analyze_technical_aspects(code, "test_async")
    assert "Async function without await usage" in issues


def test_analyze_technical_aspects_mock_with_async() -> None:
    """Test detection of Mock() used with async code."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    async def test_function():
        mock = Mock()
        await some_async_function()
    """

    issues = analyzer._analyze_technical_aspects(code, "test_mock")
    assert "Using Mock instead of AsyncMock for async methods" in issues


def test_analyze_technical_aspects_raise_without_try() -> None:
    """Test detection of raise without try/except."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_function():
        raise ValueError("test")
    """

    issues = analyzer._analyze_technical_aspects(code, "test_raise")
    assert "Exception raised without handling" in issues


def test_analyze_technical_aspects_missing_return_type() -> None:
    """Test detection of missing return type annotations."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_function():
        return 42
    """

    issues = analyzer._analyze_technical_aspects(code, "test_types")
    assert "Missing return type annotations" in issues


def test_analyze_technical_aspects_clean_code() -> None:
    """Test clean code with no technical issues."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    async def test_function() -> int:
        result = await some_async_function()
        return result
    """

    issues = analyzer._analyze_technical_aspects(code, "test_clean")
    assert len(issues) == 0


def test_analyze_safety_aspects_hardcoded_password() -> None:
    """Test detection of hardcoded passwords."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_login():
        password = "secret123"
        login(password)
    """

    issues = analyzer._analyze_safety_aspects(code, "test_password")
    assert "Hardcoded password in code" in issues


def test_analyze_safety_aspects_sql_injection() -> None:
    """Test detection of potential SQL injection."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_query():
        query = "SELECT * FROM users WHERE name = '" + user_input + "'"
    """

    issues = analyzer._analyze_safety_aspects(code, "test_sql")
    assert "Potential SQL injection" in issues


def test_analyze_safety_aspects_unsafe_file_open() -> None:
    """Test detection of unsafe file handling."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_file():
        f = open("file.txt")
        data = f.read()
    """

    issues = analyzer._analyze_safety_aspects(code, "test_file")
    assert "Unsafe file open without context manager" in issues


def test_analyze_safety_aspects_logging_sensitive_data() -> None:
    """Test detection of sensitive data logging."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_logging():
        logger.info(f"User password: {password}")
    """

    issues = analyzer._analyze_safety_aspects(code, "test_logging")
    assert "Logging sensitive data" in issues


def test_analyze_safety_aspects_clean_code() -> None:
    """Test clean code with no safety issues."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_safe():
        with open("file.txt") as f:
            data = f.read()
        return data
    """

    issues = analyzer._analyze_safety_aspects(code, "test_safe")
    assert len(issues) == 0


def test_analyze_philosophy_compliance_health_without_metrics() -> None:
    """Test detection of health tests without key metrics."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_health_check():
        assert True
    """

    violations = analyzer._analyze_philosophy_compliance(code, "test_health_check")
    assert "Health test does not verify key metrics" in violations


def test_analyze_philosophy_compliance_nutrition_without_macros() -> None:
    """Test detection of nutrition tests without macronutrients."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_nutrition_data():
        assert nutrition_data is not None
    """

    violations = analyzer._analyze_philosophy_compliance(code, "test_nutrition_data")
    assert "Nutrition test does not validate macronutrients" in violations


def test_analyze_philosophy_compliance_user_without_error_handling() -> None:
    """Test detection of user tests without error handling."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_user_login():
        user = login("username")
        assert user is not None
    """

    violations = analyzer._analyze_philosophy_compliance(code, "test_user_login")
    assert "User-related test does not validate error handling" in violations


def test_analyze_philosophy_compliance_personal_without_profile() -> None:
    """Test detection of personalization tests without profile."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_personal_recommendations():
        recommendations = get_recommendations()
        assert recommendations
    """

    violations = analyzer._analyze_philosophy_compliance(code, "test_personal_recommendations")
    assert "Personalization test does not use user profile/preferences" in violations


def test_analyze_philosophy_compliance_clean_code() -> None:
    """Test clean code with no philosophy violations."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    def test_standard_function():
        result = calculate(1, 2)
        assert result == 3
    """

    violations = analyzer._analyze_philosophy_compliance(code, "test_standard_function")
    assert len(violations) == 0


def test_assess_business_impact_no_issues() -> None:
    """Test business impact assessment with no issues."""
    analyzer = IntegratedBayesianAnalyzer()
    impact = analyzer._assess_business_impact([], [], [], [])
    assert impact == "No business impact"


def test_assess_business_impact_minimal() -> None:
    """Test business impact assessment with minimal issues."""
    analyzer = IntegratedBayesianAnalyzer()
    impact = analyzer._assess_business_impact(["issue1"], [], [], ["issue2"])
    assert impact == "Minimal impact on user experience"


def test_assess_business_impact_moderate() -> None:
    """Test business impact assessment with moderate issues."""
    analyzer = IntegratedBayesianAnalyzer()
    impact = analyzer._assess_business_impact(
        ["issue1", "issue2"], ["issue3"], [], ["issue4", "issue5"]
    )
    assert impact == "Moderate impact on product quality"


def test_assess_business_impact_high() -> None:
    """Test business impact assessment with high issues."""
    analyzer = IntegratedBayesianAnalyzer()
    issues = ["issue"] * 8
    impact = analyzer._assess_business_impact(issues[:3], issues[3:5], issues[5:7], issues[7:8])
    assert impact == "High impact on reputation and safety"


def test_assess_business_impact_critical() -> None:
    """Test business impact assessment with critical issues."""
    analyzer = IntegratedBayesianAnalyzer()
    issues = ["issue"] * 15
    impact = analyzer._assess_business_impact(issues[:5], issues[5:9], issues[9:12], issues[12:])
    assert impact == "Critical impact on business operations"


def test_calculate_risk_level_low() -> None:
    """Test risk level calculation with no critical issues."""
    analyzer = IntegratedBayesianAnalyzer()
    risk = analyzer._calculate_risk_level([], [], [], [])
    assert risk == "low"


def test_calculate_risk_level_medium() -> None:
    """Test risk level calculation with one critical issue."""
    analyzer = IntegratedBayesianAnalyzer()
    risk = analyzer._calculate_risk_level(["Using AsyncMock issue"], [], [], [])
    assert risk == "medium"


def test_calculate_risk_level_high() -> None:
    """Test risk level calculation with two critical issues."""
    analyzer = IntegratedBayesianAnalyzer()
    risk = analyzer._calculate_risk_level(["Using AsyncMock issue"], [], ["пароль in code"], [])
    assert risk == "high"


def test_calculate_risk_level_critical() -> None:
    """Test risk level calculation with three+ critical issues."""
    analyzer = IntegratedBayesianAnalyzer()
    risk = analyzer._calculate_risk_level(
        ["Using AsyncMock issue"], ["dangerous nutrition issue"], ["пароль in code"], []
    )
    assert risk == "critical"


def test_generate_integrated_recommendations_no_issues() -> None:
    """Test recommendations generation with no issues."""
    analyzer = IntegratedBayesianAnalyzer()
    recs = analyzer._generate_integrated_recommendations([], [], [], [])
    assert len(recs) == 0


def test_generate_integrated_recommendations_technical() -> None:
    """Test recommendations with technical issues."""
    analyzer = IntegratedBayesianAnalyzer()
    recs = analyzer._generate_integrated_recommendations(["issue1", "issue2"], [], [], [])
    assert len(recs) == 1
    assert "Fix technical issues" in recs[0]


def test_generate_integrated_recommendations_nutrition() -> None:
    """Test recommendations with nutrition issues."""
    analyzer = IntegratedBayesianAnalyzer()
    recs = analyzer._generate_integrated_recommendations([], ["nutr_issue1", "nutr_issue2"], [], [])
    assert len(recs) == 1
    assert "Improve nutrition safety" in recs[0]


def test_generate_integrated_recommendations_safety() -> None:
    """Test recommendations with safety issues."""
    analyzer = IntegratedBayesianAnalyzer()
    recs = analyzer._generate_integrated_recommendations([], [], ["safety_issue1"], [])
    assert len(recs) == 1
    assert "Strengthen data safety" in recs[0]


def test_generate_integrated_recommendations_philosophy() -> None:
    """Test recommendations with philosophy violations."""
    analyzer = IntegratedBayesianAnalyzer()
    recs = analyzer._generate_integrated_recommendations([], [], [], ["phil_violation1"])
    assert len(recs) == 1
    assert "Align with system philosophy" in recs[0]


def test_generate_integrated_recommendations_all_issues() -> None:
    """Test recommendations with all types of issues."""
    analyzer = IntegratedBayesianAnalyzer()
    recs = analyzer._generate_integrated_recommendations(
        ["tech1"], ["nutr1"], ["safety1"], ["phil1"]
    )
    assert len(recs) == 4


def test_analyze_test_comprehensively_clean() -> None:
    """Test comprehensive analysis of clean code."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    async def test_standard() -> None:
        result = await some_function()
        assert result is not None
    """

    result = analyzer.analyze_test_comprehensively(code, "test_standard", "tests/test_file.py")

    assert result.test_name == "test_standard"
    assert result.success is True
    assert len(result.technical_issues) == 0
    assert len(result.nutrition_issues) == 0
    assert len(result.safety_issues) == 0
    assert result.business_impact == "No business impact"
    assert result.overall_risk_level == "low"
    assert len(analyzer.integrated_results) == 1


def test_analyze_test_comprehensively_with_issues() -> None:
    """Test comprehensive analysis with multiple issues."""
    analyzer = IntegratedBayesianAnalyzer()
    code = """
    async def test_health_login():
        password = "test123"
        mock = Mock()
        raise ValueError("error")
        result = login(password)
    """

    result = analyzer.analyze_test_comprehensively(
        code, "test_health_login", "tests/test_health.py"
    )

    assert result.test_name == "test_health_login"
    assert result.success is False
    assert len(result.technical_issues) > 0
    assert len(result.safety_issues) > 0
    assert result.business_impact != "No business impact"
    assert result.overall_risk_level != "low"
    assert len(analyzer.integrated_results) == 1


def test_get_comprehensive_diagnosis_no_data() -> None:
    """Test comprehensive diagnosis with no results."""
    analyzer = IntegratedBayesianAnalyzer()
    diagnosis = analyzer.get_comprehensive_diagnosis()

    assert diagnosis["status"] == "no_data"


def test_get_comprehensive_diagnosis_with_data() -> None:
    """Test comprehensive diagnosis with results."""
    analyzer = IntegratedBayesianAnalyzer()

    # Add some test results
    code1 = """
    async def test_clean() -> None:
        result = await function()
        assert result
    """
    analyzer.analyze_test_comprehensively(code1, "test_clean", "tests/test1.py")

    code2 = """
    async def test_issues():
        password = "test"
        mock = Mock()
    """
    analyzer.analyze_test_comprehensively(code2, "test_issues", "tests/test2.py")

    diagnosis = analyzer.get_comprehensive_diagnosis()

    assert diagnosis["status"] == "analyzed"
    assert diagnosis["total_tests"] == 2
    assert diagnosis["successful_tests"] == 1
    assert diagnosis["success_rate"] == 0.5
    assert "risk_distribution" in diagnosis
    assert "problem_areas" in diagnosis
    assert "critical_tests" in diagnosis
    assert "recommendations" in diagnosis


def test_generate_system_recommendations_no_issues() -> None:
    """Test system recommendations with no frequent issues."""
    analyzer = IntegratedBayesianAnalyzer()

    # Add one clean result
    code = """
    async def test_function() -> None:
        result = await call()
        assert result
    """
    analyzer.analyze_test_comprehensively(code, "test_func", "tests/test.py")

    recs = analyzer._generate_system_recommendations()
    assert len(recs) == 0


def test_generate_system_recommendations_technical_issues() -> None:
    """Test system recommendations with frequent technical issues."""
    analyzer = IntegratedBayesianAnalyzer()

    # Add multiple results with technical issues (>50% have issues)
    for i in range(3):
        code = f"""
        async def test_{i}():
            result = sync_call()
        """
        analyzer.analyze_test_comprehensively(code, f"test_{i}", f"tests/test_{i}.py")

    recs = analyzer._generate_system_recommendations()
    assert any("технический рефакторинг" in rec for rec in recs)


def test_generate_system_recommendations_safety_issues() -> None:
    """Test system recommendations with safety issues."""
    analyzer = IntegratedBayesianAnalyzer()

    # Add results with safety issues (>20% have issues)
    for i in range(5):
        code = f"""
        def test_{i}():
            password = "test{i}"
        """
        analyzer.analyze_test_comprehensively(code, f"test_{i}", f"tests/test_{i}.py")

    recs = analyzer._generate_system_recommendations()
    assert any("аудит безопасности" in rec for rec in recs)


def test_generate_system_recommendations_philosophy_violations() -> None:
    """Test system recommendations with philosophy violations."""
    analyzer = IntegratedBayesianAnalyzer()

    # Add results with philosophy violations (>40% have violations)
    for i in range(5):
        code = f"""
        def test_health_{i}():
            assert True
        """
        analyzer.analyze_test_comprehensively(code, f"test_health_{i}", f"tests/test_{i}.py")

    recs = analyzer._generate_system_recommendations()
    assert any("философией системы" in rec for rec in recs)


def test_system_philosophy_enum() -> None:
    """Test SystemPhilosophy enum values."""
    assert SystemPhilosophy.HEALTH_FIRST.value == "health_first"
    assert SystemPhilosophy.USER_SAFETY.value == "user_safety"
    assert SystemPhilosophy.DATA_PRIVACY.value == "data_privacy"
    assert SystemPhilosophy.SCIENTIFIC_ACCURACY.value == "scientific_accuracy"
    assert SystemPhilosophy.ACCESSIBILITY.value == "accessibility"
    assert SystemPhilosophy.SUSTAINABILITY.value == "sustainability"
    assert SystemPhilosophy.PERSONALIZATION.value == "personalization"
    assert SystemPhilosophy.TRANSPARENCY.value == "transparency"
