"""
Edge case tests for core/metabolism.py to boost coverage to 97%+.
Focus on validation, error paths, and boundary conditions.
"""

import pytest
from core.metabolism import (
    calculate_bmr,
    get_bmr_formula,
    adjust_for_activity,
    calculate_tdee,
    get_macro_ratios,
    calculate_macros,
    adjust_calories_for_goal,
    calculate_deficit_surplus,
    calculate_all_bmr,
    calculate_all_tdee,
    ACTIVITY_MULTIPLIERS,
)


class TestBMRValidation:
    """Test BMR calculation validation and error handling"""

    def test_bmr_negative_age(self) -> None:
        """Test BMR raises ValueError for negative age"""
        with pytest.raises(ValueError, match="Age must be positive"):
            calculate_bmr(age=-5, weight=70, height=175, gender="male")

    def test_bmr_zero_age(self) -> None:
        """Test BMR raises ValueError for zero age"""
        with pytest.raises(ValueError, match="Age must be positive"):
            calculate_bmr(age=0, weight=70, height=175, gender="male")

    def test_bmr_negative_weight(self) -> None:
        """Test BMR raises ValueError for negative weight"""
        with pytest.raises(ValueError, match="Weight must be positive"):
            calculate_bmr(age=30, weight=-70, height=175, gender="male")

    def test_bmr_zero_weight(self) -> None:
        """Test BMR raises ValueError for zero weight"""
        with pytest.raises(ValueError, match="Weight must be positive"):
            calculate_bmr(age=30, weight=0, height=175, gender="male")

    def test_bmr_negative_height(self) -> None:
        """Test BMR raises ValueError for negative height"""
        with pytest.raises(ValueError, match="Height must be positive"):
            calculate_bmr(age=30, weight=70, height=-175, gender="male")

    def test_bmr_zero_height(self) -> None:
        """Test BMR raises ValueError for zero height"""
        with pytest.raises(ValueError, match="Height must be positive"):
            calculate_bmr(age=30, weight=70, height=0, gender="male")

    def test_bmr_invalid_body_fat_negative(self) -> None:
        """Test BMR raises ValueError for negative body fat"""
        with pytest.raises(ValueError, match="Body fat percentage must be between 0 and 100"):
            calculate_bmr(age=30, weight=70, height=175, gender="male", body_fat=-5)

    def test_bmr_invalid_body_fat_over_100(self) -> None:
        """Test BMR raises ValueError for body fat > 100"""
        with pytest.raises(ValueError, match="Body fat percentage must be between 0 and 100"):
            calculate_bmr(age=30, weight=70, height=175, gender="male", body_fat=105)

    def test_bmr_invalid_gender(self) -> None:
        """Test BMR raises ValueError for invalid gender"""
        with pytest.raises(ValueError, match="Gender must be 'male' or 'female'"):
            calculate_bmr(age=30, weight=70, height=175, gender="other")

    def test_bmr_invalid_gender_empty(self) -> None:
        """Test BMR raises ValueError for empty gender string"""
        with pytest.raises(ValueError, match="Gender must be 'male' or 'female'"):
            calculate_bmr(age=30, weight=70, height=175, gender="")

    def test_bmr_harris_benedict_male(self) -> None:
        """Test Harris-Benedict formula for males"""
        bmr = calculate_bmr(age=30, weight=80, height=180, gender="male", formula="harris")
        # Harris-Benedict: 66.5 + (13.75 × 80) + (5.003 × 180) - (6.755 × 30)
        expected = 66.5 + 13.75 * 80 + 5.003 * 180 - 6.755 * 30
        assert abs(bmr - expected) < 0.1

    def test_bmr_harris_benedict_female(self) -> None:
        """Test Harris-Benedict formula for females"""
        bmr = calculate_bmr(age=25, weight=60, height=165, gender="female", formula="harris")
        # Harris-Benedict: 655.1 + (9.563 × 60) + (1.85 × 165) - (4.676 × 25)
        expected = 655.1 + 9.563 * 60 + 1.85 * 165 - 4.676 * 25
        assert abs(bmr - expected) < 0.1

    def test_bmr_cunningham_with_body_fat(self) -> None:
        """Test Cunningham formula with body fat"""
        bmr = calculate_bmr(
            age=30, weight=80, height=180, gender="male", body_fat=15, formula="cunningham"
        )
        lean_mass = 80 * (1 - 15 / 100)
        expected = 500 + 22 * lean_mass
        assert abs(bmr - expected) < 0.1

    def test_bmr_katch_without_body_fat(self) -> None:
        """Test Katch-McArdle formula raises error without body fat"""
        with pytest.raises(ValueError, match="body_fat required for katch formula"):
            calculate_bmr(age=30, weight=80, height=180, gender="male", formula="katch")

    def test_bmr_cunningham_without_body_fat(self) -> None:
        """Test Cunningham formula raises error without body fat"""
        with pytest.raises(ValueError, match="body_fat required for cunningham formula"):
            calculate_bmr(age=30, weight=80, height=180, gender="male", formula="cunningham")


class TestActivityValidation:
    """Test activity level validation and TDEE calculations"""

    def test_invalid_activity_level(self) -> None:
        """Test adjust_for_activity raises ValueError for invalid activity"""
        with pytest.raises(ValueError, match="Invalid activity"):
            adjust_for_activity(bmr=1700, activity="invalid_activity")  # type: ignore

    def test_all_activity_multipliers(self) -> None:
        """Test all predefined activity multipliers"""
        bmr = 1700
        for activity, multiplier in ACTIVITY_MULTIPLIERS.items():
            tdee = adjust_for_activity(bmr, activity)  # type: ignore
            expected = bmr * multiplier
            assert abs(tdee - expected) < 0.01

    def test_tdee_with_body_fat(self) -> None:
        """Test TDEE calculation with body fat percentage"""
        tdee = calculate_tdee(
            age=30,
            weight=80,
            height=180,
            gender="male",
            activity="moderate",
            body_fat=18,
            formula="katch",
        )
        assert tdee > 0
        # Should use Katch-McArdle formula
        lean_mass = 80 * (1 - 18 / 100)
        bmr = 370 + 21.6 * lean_mass
        expected_tdee = bmr * ACTIVITY_MULTIPLIERS["moderate"]
        assert abs(tdee - expected_tdee) < 1.0


class TestMacroCalculations:
    """Test macronutrient calculation edge cases"""

    def test_invalid_goal(self) -> None:
        """Test get_macro_ratios raises ValueError for invalid goal"""
        with pytest.raises(ValueError, match="Invalid goal"):
            get_macro_ratios("invalid_goal")  # type: ignore

    def test_macro_ratios_sum_to_one(self) -> None:
        """Test that macro ratios sum to 1.0 for all goals"""
        for goal in ["loss", "maintain", "gain"]:
            ratios = get_macro_ratios(goal)  # type: ignore
            total = ratios["protein"] + ratios["carbs"] + ratios["fat"]
            assert abs(total - 1.0) < 0.01

    def test_calculate_macros_with_custom_protein(self) -> None:
        """Test macro calculation with custom protein requirement"""
        # For "loss" goal, body_weight-based protein calculation is used
        macros = calculate_macros(tdee=2500, goal="loss", protein_grams_per_kg=2.0, body_weight=80)
        # 2.0 g/kg * 80 kg = 160g protein
        assert macros["protein_g"] == 160.0

    def test_calculate_macros_without_body_weight(self) -> None:
        """Test macro calculation without body weight falls back to ratio"""
        macros = calculate_macros(tdee=2000, goal="maintain")
        # Should use default protein calculation or ratios
        assert "protein_g" in macros
        assert "carbs_g" in macros
        assert "fat_g" in macros
        # Verify calories approximately match TDEE
        total_kcal = macros["protein_g"] * 4 + macros["carbs_g"] * 4 + macros["fat_g"] * 9
        assert abs(total_kcal - 2000) < 50


class TestCalorieAdjustments:
    """Test calorie adjustment validation and edge cases"""

    def test_adjust_calories_maintain(self) -> None:
        """Test that 'maintain' goal returns TDEE unchanged"""
        tdee = 2000
        adjusted = adjust_calories_for_goal(tdee, "maintain")
        assert adjusted == tdee

    def test_adjust_calories_loss_with_custom_deficit(self) -> None:
        """Test calorie adjustment with custom deficit percentage"""
        tdee = 2000
        adjusted = adjust_calories_for_goal(tdee, "loss", deficit_pct=20)
        expected = tdee * (1 - 20 / 100)
        assert abs(adjusted - expected) < 0.1

    def test_adjust_calories_gain_with_custom_surplus(self) -> None:
        """Test calorie adjustment with custom surplus percentage"""
        tdee = 2000
        adjusted = adjust_calories_for_goal(tdee, "gain", surplus_pct=15)
        expected = tdee * (1 + 15 / 100)
        assert abs(adjusted - expected) < 0.1

    def test_adjust_calories_deficit_too_low(self) -> None:
        """Test that deficit < 5% raises ValueError"""
        with pytest.raises(ValueError, match="Deficit percentage must be between 5 and 25"):
            adjust_calories_for_goal(2000, "loss", deficit_pct=3)

    def test_adjust_calories_deficit_too_high(self) -> None:
        """Test that deficit > 25% raises ValueError"""
        with pytest.raises(ValueError, match="Deficit percentage must be between 5 and 25"):
            adjust_calories_for_goal(2000, "loss", deficit_pct=30)

    def test_adjust_calories_surplus_too_low(self) -> None:
        """Test that surplus < 5% raises ValueError"""
        with pytest.raises(ValueError, match="Surplus percentage must be between 5 and 20"):
            adjust_calories_for_goal(2000, "gain", surplus_pct=3)

    def test_adjust_calories_surplus_too_high(self) -> None:
        """Test that surplus > 20% raises ValueError"""
        with pytest.raises(ValueError, match="Surplus percentage must be between 5 and 20"):
            adjust_calories_for_goal(2000, "gain", surplus_pct=25)

    def test_adjust_calories_invalid_goal(self) -> None:
        """Test that invalid goal raises ValueError"""
        with pytest.raises(ValueError, match="Unknown goal"):
            adjust_calories_for_goal(2000, "invalid")  # type: ignore


class TestDeficitSurplusCalculations:
    """Test deficit/surplus calculation edge cases"""

    def test_calculate_deficit(self) -> None:
        """Test deficit calculation when target < current"""
        result = calculate_deficit_surplus(current_kcal=2000, target_kcal=1800)
        assert result["kcal_difference"] == -200
        assert result["is_deficit"] is True
        assert result["is_surplus"] is False
        assert abs(result["pct_difference"] - (-10.0)) < 0.01

    def test_calculate_surplus(self) -> None:
        """Test surplus calculation when target > current"""
        result = calculate_deficit_surplus(current_kcal=2000, target_kcal=2300)
        assert result["kcal_difference"] == 300
        assert result["is_deficit"] is False
        assert result["is_surplus"] is True
        assert abs(result["pct_difference"] - 15.0) < 0.01

    def test_calculate_no_change(self) -> None:
        """Test when current equals target"""
        result = calculate_deficit_surplus(current_kcal=2000, target_kcal=2000)
        assert result["kcal_difference"] == 0
        assert result["is_deficit"] is False
        assert result["is_surplus"] is False
        assert result["pct_difference"] == 0.0


class TestBMRFormulaSelection:
    """Test BMR formula selection logic"""

    def test_get_bmr_formula_with_body_fat(self) -> None:
        """Test formula selection returns 'katch' when body_fat is present"""
        user_data = {"body_fat": 15}
        assert get_bmr_formula(user_data) == "katch"

    def test_get_bmr_formula_without_body_fat(self) -> None:
        """Test formula selection returns 'mifflin' when body_fat is missing"""
        user_data = {"age": 30, "weight": 70}
        assert get_bmr_formula(user_data) == "mifflin"

    def test_get_bmr_formula_body_fat_none(self) -> None:
        """Test formula selection returns 'mifflin' when body_fat is None"""
        user_data = {"body_fat": None}
        assert get_bmr_formula(user_data) == "mifflin"


class TestHighLevelConvenienceFunctions:
    """Test calculate_all_bmr and calculate_all_tdee"""

    def test_calculate_all_bmr_without_body_fat(self) -> None:
        """Test calculate_all_bmr without body fat"""
        results = calculate_all_bmr(weight=80, height=180, age=30, sex="male")
        assert "mifflin" in results
        assert "harris" in results
        assert "katch" not in results  # Should not be present without body fat
        assert results["mifflin"] > 0
        assert results["harris"] > 0

    def test_calculate_all_bmr_with_body_fat(self) -> None:
        """Test calculate_all_bmr with body fat"""
        results = calculate_all_bmr(weight=80, height=180, age=30, sex="male", bodyfat_percent=18)
        assert "mifflin" in results
        assert "harris" in results
        assert "katch" in results  # Should be present with body fat
        assert results["mifflin"] > 0
        assert results["harris"] > 0
        assert results["katch"] > 0

    def test_calculate_all_tdee(self) -> None:
        """Test calculate_all_tdee with multiple BMR results"""
        bmr_results = {"mifflin": 1700, "harris": 1720, "katch": 1680}
        tdee_results = calculate_all_tdee(bmr_results, activity="moderate")
        assert "mifflin" in tdee_results
        assert "harris" in tdee_results
        assert "katch" in tdee_results
        # Each TDEE should be BMR * activity multiplier
        for formula, tdee in tdee_results.items():
            expected = bmr_results[formula] * ACTIVITY_MULTIPLIERS["moderate"]
            assert abs(tdee - expected) < 0.01

    def test_calculate_all_tdee_sedentary(self) -> None:
        """Test calculate_all_tdee with sedentary activity"""
        bmr_results = {"mifflin": 1700}
        tdee_results = calculate_all_tdee(bmr_results, activity="sedentary")
        expected = 1700 * ACTIVITY_MULTIPLIERS["sedentary"]
        assert abs(tdee_results["mifflin"] - expected) < 0.01
