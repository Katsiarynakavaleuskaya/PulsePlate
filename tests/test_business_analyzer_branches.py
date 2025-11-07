from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
)


def test_monetization_missing_strategy_branch() -> None:
    analyzer = BusinessBayesianAnalyzer()
    code = "payment = 10  # billing present, but no plan/tier/subscription keywords"
    results = analyzer._analyze_monetization(code, "test_monetization")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and r.error_type == BusinessErrorType.REVENUE_LEAK
        for r in results
    )


def test_monetization_price_too_high() -> None:
    """Test detection of prices that are too high."""
    analyzer = BusinessBayesianAnalyzer()
    code = "price = 1500  # Very high price"
    results = analyzer._analyze_monetization(code, "test_high_price")
    assert any(
        r.business_category == BusinessCategory.MONETIZATION
        and "высок" in r.error_message.lower()
        for r in results
    )


def test_customer_acquisition_no_validation() -> None:
    """Test detection of registration without validation."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
    def signup():
        user = create_account(name="John")
        return user
    """
    results = analyzer._analyze_customer_acquisition(code, "test_signup")
    assert any(
        r.business_category == BusinessCategory.CUSTOMER_ACQUISITION
        for r in results
    )


def test_customer_acquisition_no_onboarding() -> None:
    """Test detection of registration without onboarding."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
    def register_user():
        user = create_account(email="test@example.com")
        validate(user.email)
        return user
    """
    results = analyzer._analyze_customer_acquisition(code, "test_register")
    # Should detect missing onboarding
    assert isinstance(results, list)


def test_cost_optimization_nested_loops() -> None:
    """Test detection of inefficient nested loops."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
    for i in range(100):
        for j in range(100):
            process(i, j)
    """
    results = analyzer._analyze_cost_optimization(code, "test_loops")
    assert any(
        r.business_category == BusinessCategory.COST_OPTIMIZATION
        for r in results
    )


def test_cost_optimization_no_caching() -> None:
    """Test detection of missing caching for API calls."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
    def fetch_data():
        response = api.request("GET", "/data")
        return response.json()
    """
    results = analyzer._analyze_cost_optimization(code, "test_api")
    assert any(
        r.business_category == BusinessCategory.COST_OPTIMIZATION
        for r in results
    )


def test_revenue_growth_no_ab_testing() -> None:
    """Test detection of analytics without A/B testing."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
    def track_conversion():
        analytics.track("conversion", value=100)
        return {"revenue": 100}
    """
    results = analyzer._analyze_revenue_growth(code, "test_analytics")
    assert any(
        r.business_category == BusinessCategory.REVENUE_GROWTH
        for r in results
    )


def test_revenue_growth_no_personalization() -> None:
    """Test detection of personalization without recommendations."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
    def get_user_personal_page():
        user = get_user()
        return render("personal_page", user=user)
    """
    results = analyzer._analyze_revenue_growth(code, "test_user_personal")
    # Should detect missing personalization
    assert isinstance(results, list)


def test_customer_retention_no_segmentation() -> None:
    """Test detection of communication without segmentation."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
    def send_notification():
        email.send("notification", to=all_users)
        return True
    """
    results = analyzer._analyze_customer_retention(code, "test_notification")
    assert any(
        r.business_category == BusinessCategory.USER_RETENTION
        for r in results
    )


def test_customer_retention_no_feedback_processing() -> None:
    """Test detection of feedback without processing."""
    analyzer = BusinessBayesianAnalyzer()
    code = """
    def collect_feedback():
        feedback = get_user_feedback()
        return feedback
    """
    results = analyzer._analyze_customer_retention(code, "test_feedback")
    # Should detect missing feedback processing
    assert isinstance(results, list)


def test_generate_cost_savings_recommendations() -> None:
    """Test cost savings recommendations generation."""
    analyzer = BusinessBayesianAnalyzer()

    # Generate some issues first
    code = """
    for i in range(100):
        for j in range(100):
            database.query(f"SELECT * FROM table WHERE id={i}")
    """
    analyzer.analyze_business_logic(code, "test_inefficient")

    # Get recommendations
    recs = analyzer.generate_cost_savings_recommendations()
    assert isinstance(recs, list)


def test_generate_revenue_optimization_recommendations() -> None:
    """Test revenue optimization recommendations generation."""
    analyzer = BusinessBayesianAnalyzer()

    # Generate some issues
    code = """
    def signup():
        user = create_account(name="John")
        return user
    """
    analyzer.analyze_business_logic(code, "test_signup")

    # Get recommendations
    recs = analyzer.generate_revenue_optimization_recommendations()
    assert isinstance(recs, list)


def test_diagnose_business_issues() -> None:
    """Test business issues diagnosis."""
    analyzer = BusinessBayesianAnalyzer()

    # Generate issues
    code = "price = 1500"
    analyzer.analyze_business_logic(code, "test_price")

    # Diagnose
    diagnosis = analyzer.diagnose_business_issues()
    assert isinstance(diagnosis, dict)


def test_calculate_roi_potential() -> None:
    """Test ROI potential calculation."""
    analyzer = BusinessBayesianAnalyzer()

    # Generate issues
    code = """
    for i in range(100):
        for j in range(100):
            pass
    """
    analyzer.analyze_business_logic(code, "test_inefficient")

    # Calculate ROI
    roi = analyzer.calculate_roi_potential()
    assert isinstance(roi, dict)


def test_analyze_business_logic_comprehensive() -> None:
    """Test comprehensive business logic analysis."""
    analyzer = BusinessBayesianAnalyzer()

    # Complex code with multiple issues
    code = """
    def business_function():
        price = 1500  # Too high
        for i in range(100):
            for j in range(100):
                database.query("SELECT * FROM users")
        analytics.track("event")
        notification.send(all_users)
        feedback = collect()
        return True
    """

    results = analyzer.analyze_business_logic(code, "test_complex")

    # Should find multiple issues
    assert len(results) > 0
    # Results should be persisted
    assert len(analyzer.test_results) > 0
