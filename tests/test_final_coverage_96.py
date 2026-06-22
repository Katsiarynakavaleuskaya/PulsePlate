import os

"""
Final coverage tests to reach 96% target.
"""

from app.services.nutrition_targets import estimate_targets_from_profile


class TestFinalCoverage96:
    """Tests to reach final 96% coverage target."""

    def setup_method(self) -> None:
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_premium_week_estimate_targets_from_profile(self) -> None:
        """Test estimate_targets_from_profile function."""
        result = estimate_targets_from_profile(
            sex="male",
            age=30,
            height_cm=175.0,
            weight_kg=70.0,
            activity="moderate",
            goal="maintain",
        )

        assert result is not None
        assert "kcal" in result
        assert "macros" in result
        assert "micro" in result
        assert "water_ml" in result
        assert "activity_week" in result

    def test_premium_week_estimate_targets_from_profile_female(self) -> None:
        """Test estimate_targets_from_profile with female profile."""
        result = estimate_targets_from_profile(
            sex="female",
            age=25,
            height_cm=165.0,
            weight_kg=60.0,
            activity="active",
            goal="loss",
        )

        assert result is not None
        assert "kcal" in result
        assert "macros" in result
        assert "micro" in result

    def test_premium_week_estimate_targets_from_profile_elderly(self) -> None:
        """Test estimate_targets_from_profile with elderly profile."""
        result = estimate_targets_from_profile(
            sex="male",
            age=65,
            height_cm=170.0,
            weight_kg=75.0,
            activity="light",
            goal="maintain",
        )

        assert result is not None
        assert "kcal" in result
        assert "macros" in result
        assert "micro" in result

    def test_premium_week_estimate_targets_from_profile_teen(self) -> None:
        """Test estimate_targets_from_profile with teen profile."""
        result = estimate_targets_from_profile(
            sex="female",
            age=16,
            height_cm=160.0,
            weight_kg=55.0,
            activity="moderate",
            goal="gain",
        )

        assert result is not None
        assert "kcal" in result
        assert "macros" in result
        assert "micro" in result

    def test_premium_week_estimate_targets_from_profile_athlete(self) -> None:
        """Test estimate_targets_from_profile with athlete profile."""
        result = estimate_targets_from_profile(
            sex="male",
            age=28,
            height_cm=185.0,
            weight_kg=85.0,
            activity="very_active",
            goal="maintain",
        )

        assert result is not None
        assert "kcal" in result
        assert "macros" in result
        assert "micro" in result

    def test_premium_week_estimate_targets_from_profile_obese(self) -> None:
        """Test estimate_targets_from_profile with obese profile."""
        result = estimate_targets_from_profile(
            sex="female",
            age=40,
            height_cm=160.0,
            weight_kg=90.0,
            activity="light",
            goal="loss",
        )

        assert result is not None
        assert "kcal" in result
        assert "macros" in result
        assert "micro" in result

    def test_premium_week_estimate_targets_from_profile_underweight(self) -> None:
        """Test estimate_targets_from_profile with underweight profile."""
        result = estimate_targets_from_profile(
            sex="male",
            age=22,
            height_cm=180.0,
            weight_kg=60.0,
            activity="moderate",
            goal="gain",
        )

        assert result is not None
        assert "kcal" in result
        assert "macros" in result
        assert "micro" in result

    def test_premium_week_estimate_targets_from_profile_edge_cases(self) -> None:
        """Test estimate_targets_from_profile with edge case profiles."""
        # Test minimum age
        result = estimate_targets_from_profile(
            sex="male",
            age=11,
            height_cm=140.0,
            weight_kg=35.0,
            activity="moderate",
            goal="maintain",
        )
        assert result is not None

        # Test maximum age
        result = estimate_targets_from_profile(
            sex="female",
            age=89,
            height_cm=150.0,
            weight_kg=50.0,
            activity="light",
            goal="maintain",
        )
        assert result is not None

    def test_premium_week_estimate_targets_from_profile_all_activities(self) -> None:
        """Test estimate_targets_from_profile with all activity levels."""
        activities = ["sedentary", "light", "moderate", "active", "very_active"]

        for activity in activities:
            result = estimate_targets_from_profile(
                sex="male",
                age=30,
                height_cm=175.0,
                weight_kg=70.0,
                activity=activity,
                goal="maintain",
            )
            assert result is not None
            assert "kcal" in result

    def test_premium_week_estimate_targets_from_profile_all_goals(self) -> None:
        """Test estimate_targets_from_profile with all goal types."""
        goals = ["loss", "maintain", "gain"]

        for goal in goals:
            result = estimate_targets_from_profile(
                sex="female",
                age=30,
                height_cm=165.0,
                weight_kg=60.0,
                activity="moderate",
                goal=goal,
            )
            assert result is not None
            assert "kcal" in result
