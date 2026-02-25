# -*- coding: utf-8 -*-
"""
Tests for planner_engines facade functions coverage.

RU: Тесты для покрытия фасадных функций planner_engines.
EN: Tests for planner_engines facade function coverage.
"""

import pytest


class TestTargetsFacades:
    """Tests for core/targets.py facade functions."""

    def test_calculate_bmr_valid_male(self) -> None:
        """Test BMR calculation for valid male input."""
        from core.targets import calculate_bmr

        result = calculate_bmr(age=30, gender="M", weight=70, height=175)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_calculate_bmr_valid_female(self) -> None:
        """Test BMR calculation for valid female input."""
        from core.targets import calculate_bmr

        result = calculate_bmr(age=25, gender="female", weight=60, height=165)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_calculate_bmr_gender_aliases(self) -> None:
        """Test BMR calculation with different gender aliases."""
        from core.targets import calculate_bmr

        # Test various gender formats
        for gender in ["m", "M", "male", "MALE", "Male"]:
            result = calculate_bmr(age=30, gender=gender, weight=70, height=175)
            assert result is not None

        for gender in ["f", "F", "female", "FEMALE", "Female"]:
            result = calculate_bmr(age=30, gender=gender, weight=60, height=165)
            assert result is not None

    def test_calculate_tdee_valid(self) -> None:
        """Test TDEE calculation for valid input."""
        from core.targets import calculate_tdee

        result = calculate_tdee(bmr=1500, activity="moderate")
        assert result is not None
        assert isinstance(result, float)
        assert result > 1500  # TDEE should be higher than BMR

    def test_calculate_tdee_all_activity_levels(self) -> None:
        """Test TDEE calculation with all activity levels."""
        from core.targets import calculate_tdee

        activities = ["sedentary", "light", "moderate", "active", "very_active"]
        for activity in activities:
            result = calculate_tdee(bmr=1500, activity=activity)
            assert result is not None
            assert result > 0

    def test_calculate_tdee_invalid_bmr(self) -> None:
        """Test TDEE calculation with invalid BMR."""
        from core.targets import calculate_tdee

        assert calculate_tdee(bmr=0, activity="moderate") is None
        assert calculate_tdee(bmr=-100, activity="moderate") is None

    def test_calculate_tdee_invalid_activity(self) -> None:
        """Test TDEE calculation with invalid activity level."""
        from core.targets import calculate_tdee

        assert calculate_tdee(bmr=1500, activity="invalid") is None
        assert calculate_tdee(bmr=1500, activity="super_active") is None

    def test_get_nutrient_dri_stub(self) -> None:
        """Test DRI stub function returns None."""
        from core.targets import get_nutrient_dri

        result = get_nutrient_dri("protein", age=30, gender="M")
        assert result is None

    def test_validate_user_data_valid(self) -> None:
        """Test user data validation with valid data."""
        from core.targets import validate_user_data

        assert validate_user_data({"age": 30, "weight": 70, "height": 175}) is True

    def test_validate_user_data_missing_keys(self) -> None:
        """Test user data validation with missing keys."""
        from core.targets import validate_user_data

        assert validate_user_data({"age": 30}) is False
        assert validate_user_data({"weight": 70}) is False
        assert validate_user_data({}) is False

    def test_validate_user_data_invalid_values(self) -> None:
        """Test user data validation with invalid values."""
        from core.targets import validate_user_data

        assert validate_user_data({"age": 0, "weight": 70, "height": 175}) is False
        assert validate_user_data({"age": 30, "weight": -5, "height": 175}) is False
        assert validate_user_data({"age": 30, "weight": 70, "height": "tall"}) is False

    def test_adjust_for_activity_level_stub(self) -> None:
        """Test adjust_for_activity_level stub returns base value."""
        from core.targets import adjust_for_activity_level

        result = adjust_for_activity_level(100.0, "moderate")
        assert result == 100.0

    def test_get_who_recommendations_stub(self) -> None:
        """Test WHO recommendations stub returns None."""
        from core.targets import get_who_recommendations

        result = get_who_recommendations(30, "M")
        assert result is None

    def test_calculate_daily_targets_stub(self) -> None:
        """Test daily targets stub returns None."""
        from core.targets import calculate_daily_targets

        result = calculate_daily_targets({})
        assert result is None


class TestAutoRepairFacades:
    """Tests for core/auto_repair.py facade functions."""

    def test_analyze_deficiencies_basic(self) -> None:
        """Test basic deficiency analysis."""
        from core.auto_repair import analyze_deficiencies

        current = {"protein": 50, "carbs": 200}
        target = {"protein": 80, "carbs": 250, "fat": 70}

        result = analyze_deficiencies(current, target)
        assert isinstance(result, dict)
        assert "protein" in result
        assert "carbs" in result
        assert "fat" in result  # Not in current, so it's deficient

    def test_analyze_deficiencies_no_deficiencies(self) -> None:
        """Test when there are no deficiencies."""
        from core.auto_repair import analyze_deficiencies

        current = {"protein": 100, "carbs": 300}
        target = {"protein": 80, "carbs": 250}

        result = analyze_deficiencies(current, target)
        assert isinstance(result, dict)
        assert len(result) == 0  # No deficiencies

    def test_analyze_deficiencies_non_numeric(self) -> None:
        """Test with non-numeric values."""
        from core.auto_repair import analyze_deficiencies

        current = {"protein": "high", "carbs": 200}
        target = {"protein": 80, "carbs": "medium"}

        result = analyze_deficiencies(current, target)
        assert isinstance(result, dict)

    def test_get_repair_suggestions_basic(self) -> None:
        """Test basic repair suggestions."""
        from core.auto_repair import get_repair_suggestions

        deficiencies = {"protein": {"deficit": 30}}
        foods = [{"name": "chicken", "protein": 25}]

        result = get_repair_suggestions(deficiencies, foods)
        assert isinstance(result, list)

    def test_get_repair_suggestions_empty(self) -> None:
        """Test repair suggestions with empty inputs."""
        from core.auto_repair import get_repair_suggestions

        result = get_repair_suggestions({}, [])
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_repair_suggestions_no_matching_foods(self) -> None:
        """Test repair suggestions when no foods match."""
        from core.auto_repair import get_repair_suggestions

        deficiencies = {"vitamin_d": {"deficit": 10}}
        foods = [{"name": "apple", "fiber": 3}]

        result = get_repair_suggestions(deficiencies, foods)
        assert isinstance(result, list)

    def test_calculate_repair_priority_dict_inputs(self) -> None:
        """Test priority calculation with dict inputs."""
        from core.auto_repair import calculate_repair_priority

        result = calculate_repair_priority({"deficit": 20}, {"protein": 80})
        assert isinstance(result, float)

    def test_calculate_repair_priority_zero_target(self) -> None:
        """Test priority calculation with zero target."""
        from core.auto_repair import calculate_repair_priority

        result = calculate_repair_priority({"deficit": 20}, {"protein": 0})
        assert result == 0.0

    def test_find_suitable_foods_stub(self) -> None:
        """Test find_suitable_foods stub returns None."""
        from core.auto_repair import find_suitable_foods

        result = find_suitable_foods()
        assert result is None

    def test_optimize_meal_plan_stub(self) -> None:
        """Test optimize_meal_plan stub returns None."""
        from core.auto_repair import optimize_meal_plan

        result = optimize_meal_plan()
        assert result is None


class TestMenuEngineFacades:
    """Tests for core/menu_engine.py facade functions."""

    def test_calculate_nutrition_totals_basic(self) -> None:
        """Test basic nutrition totals calculation."""
        from core.menu_engine import calculate_nutrition_totals

        meal_plan = {
            "meals": [
                {"name": "breakfast", "calories": 300, "protein": 15},
                {"name": "lunch", "calories": 500, "protein": 25},
            ]
        }

        result = calculate_nutrition_totals(meal_plan)
        assert isinstance(result, dict)
        assert result.get("calories", 0) == 800
        assert result.get("protein", 0) == 40

    def test_calculate_nutrition_totals_empty(self) -> None:
        """Test nutrition totals with empty meals."""
        from core.menu_engine import calculate_nutrition_totals

        result = calculate_nutrition_totals({"meals": []})
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_calculate_nutrition_totals_no_meals_key(self) -> None:
        """Test nutrition totals without meals key."""
        from core.menu_engine import calculate_nutrition_totals

        result = calculate_nutrition_totals({})
        assert isinstance(result, dict)

    def test_generate_shopping_list_basic(self) -> None:
        """Test basic shopping list generation."""
        from core.menu_engine import generate_shopping_list

        meal_plan = {
            "meals": [
                {"name": "oatmeal"},
                {"name": "salad"},
            ]
        }

        result = generate_shopping_list(meal_plan)
        assert isinstance(result, list)

    def test_generate_shopping_list_empty(self) -> None:
        """Test shopping list with empty meals."""
        from core.menu_engine import generate_shopping_list

        result = generate_shopping_list({"meals": []})
        assert isinstance(result, list)

    def test_optimize_meals_returns_input(self) -> None:
        """Test optimize_meals returns input plan."""
        from core.menu_engine import optimize_meals

        meal_plan = {"breakfast": "oatmeal"}
        result = optimize_meals(meal_plan, {"calories": 2000})
        assert result == meal_plan

    def test_validate_meal_plan_valid(self) -> None:
        """Test meal plan validation with valid plan."""
        from core.menu_engine import validate_meal_plan

        assert validate_meal_plan({"meals": []}) is True
        assert validate_meal_plan({"breakfast": [], "lunch": []}) is True
        assert validate_meal_plan({"days": []}) is True

    def test_validate_meal_plan_invalid(self) -> None:
        """Test meal plan validation with invalid plan."""
        from core.menu_engine import validate_meal_plan

        assert validate_meal_plan({}) is False
        assert validate_meal_plan({"random_key": []}) is False
        assert validate_meal_plan("not a dict") is False

    def test_suggest_meal_improvements_stub(self) -> None:
        """Test suggest_meal_improvements returns empty list."""
        from core.menu_engine import suggest_meal_improvements

        result = suggest_meal_improvements({}, {})
        assert isinstance(result, list)
        assert len(result) == 0


class TestPlateFacades:
    """Tests for core/plate.py facade functions."""

    def test_create_nutrition_plate_basic(self) -> None:
        """Test basic plate creation."""
        from core.plate import create_nutrition_plate

        foods = [
            {"name": "chicken", "protein": 30, "calories": 200},
            {"name": "rice", "carbs": 45, "calories": 200},
        ]

        result = create_nutrition_plate(foods)
        assert isinstance(result, dict)
        assert "kcal" in result
        assert result["kcal"] == 400

    def test_create_nutrition_plate_empty(self) -> None:
        """Test plate creation with empty foods."""
        from core.plate import create_nutrition_plate

        result = create_nutrition_plate([])
        assert isinstance(result, dict)

    def test_create_nutrition_plate_with_all_macros(self) -> None:
        """Test plate creation with all macros."""
        from core.plate import create_nutrition_plate

        foods = [
            {"protein": 30, "carbs": 50, "fat": 20, "fiber": 5, "calories": 500},
        ]

        result = create_nutrition_plate(foods)
        assert result["protein_g"] == 30
        assert result["carbs_g"] == 50
        assert result["fat_g"] == 20

    def test_analyze_plate_balance_balanced(self) -> None:
        """Test plate balance analysis with balanced plate."""
        from core.plate import analyze_plate_balance

        foods = [
            {"protein": 30, "carbs": 100, "fat": 30, "calories": 800},
        ]

        result = analyze_plate_balance(foods)
        assert isinstance(result, dict)
        assert "status" in result
        assert "protein_ratio" in result

    def test_analyze_plate_balance_low_protein(self) -> None:
        """Test plate balance analysis with low protein."""
        from core.plate import analyze_plate_balance

        foods = [
            {"protein": 5, "carbs": 100, "fat": 30, "calories": 700},
        ]

        result = analyze_plate_balance(foods)
        assert result["status"] == "low_protein"

    def test_analyze_plate_balance_empty(self) -> None:
        """Test plate balance with empty foods."""
        from core.plate import analyze_plate_balance

        result = analyze_plate_balance([])
        assert isinstance(result, dict)

    def test_get_plate_recommendations_low_protein(self) -> None:
        """Test recommendations for low protein plate."""
        from core.plate import get_plate_recommendations

        foods = [
            {"protein": 5, "carbs": 100, "fat": 30, "calories": 700},
        ]

        result = get_plate_recommendations(foods)
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["type"] == "increase_protein"

    def test_get_plate_recommendations_empty(self) -> None:
        """Test recommendations with empty foods."""
        from core.plate import get_plate_recommendations

        result = get_plate_recommendations([])
        assert isinstance(result, list)

    def test_calculate_plate_score_balanced(self) -> None:
        """Test plate score calculation for balanced plate."""
        from core.plate import calculate_plate_score

        # Balanced plate: ~20% protein, ~50% carbs, ~30% fat
        foods = [
            {"protein": 40, "carbs": 100, "fat": 30, "calories": 820},
        ]

        result = calculate_plate_score(foods)
        assert isinstance(result, float)
        assert 0 <= result <= 100

    def test_calculate_plate_score_empty(self) -> None:
        """Test plate score with empty foods."""
        from core.plate import calculate_plate_score

        result = calculate_plate_score([])
        assert result == 0.0

    def test_visualize_plate_data_basic(self) -> None:
        """Test plate visualization data."""
        from core.plate import visualize_plate_data

        foods = [
            {"protein": 30, "carbs": 50, "fat": 20, "calories": 500},
        ]

        result = visualize_plate_data(foods)
        assert isinstance(result, dict)
        assert "sectors" in result
        assert "type" in result
        assert result["type"] == "pie"

    def test_visualize_plate_data_empty(self) -> None:
        """Test visualization with empty foods."""
        from core.plate import visualize_plate_data

        result = visualize_plate_data([])
        assert isinstance(result, dict)

    def test_analyze_plate_balance_high_fat(self) -> None:
        """Test plate balance analysis with high fat (covers line 510)."""
        from core.plate import analyze_plate_balance

        # High fat plate: fat > 40% of calories but adequate protein and carbs
        # Need: protein >= 15%, carbs >= 40%, fat > 40%
        # protein: 30*4=120, carbs: 60*4=240, fat: 50*9=450, total=810
        # protein%=14.8%, carbs%=29.6%, fat%=55.5% -> still low_protein first
        # Need protein >= 15%: 30*4/810 = 14.8% -> need more protein
        # Let's use: protein: 40, carbs: 60, fat: 50, cal=900
        # 40*4=160, 60*4=240, 50*9=450 = 850
        # 160/850=18.8% protein, 240/850=28.2% carbs (low!), 450/850=52.9% fat
        # Still hits low_carbs first. Need carbs >= 40% too.
        # Let's use: protein: 35, carbs: 100, fat: 50, cal=930
        # 35*4=140, 100*4=400, 50*9=450 = 990
        # 140/990=14.1% protein (low!)
        # Need careful balance: protein >= 15%, carbs >= 40%, fat > 40%
        # protein: 40, carbs: 110, fat: 45, cal=1005
        # 40*4=160, 110*4=440, 45*9=405 = 1005
        # 160/1005=15.9%, 440/1005=43.8%, 405/1005=40.3% -> high_fat!
        foods = [
            {"protein": 40, "carbs": 110, "fat": 45, "calories": 1005},
        ]

        result = analyze_plate_balance(foods)
        assert result["status"] == "high_fat"

    def test_analyze_plate_balance_low_carbs(self) -> None:
        """Test plate balance analysis with low carbs."""
        from core.plate import analyze_plate_balance

        # Low carbs: carbs < 40% of calories
        foods = [
            {"protein": 40, "carbs": 20, "fat": 30, "calories": 500},
        ]

        result = analyze_plate_balance(foods)
        assert result["status"] == "low_carbs"

    def test_get_plate_recommendations_high_fat(self) -> None:
        """Test recommendations for high fat plate (covers lines 553-554)."""
        from core.plate import get_plate_recommendations

        # Same balanced high-fat plate as above
        foods = [
            {"protein": 40, "carbs": 110, "fat": 45, "calories": 1005},
        ]

        result = get_plate_recommendations(foods)
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["type"] == "reduce_fat"

    def test_get_plate_recommendations_low_carbs(self) -> None:
        """Test recommendations for low carbs plate."""
        from core.plate import get_plate_recommendations

        foods = [
            {"protein": 40, "carbs": 20, "fat": 30, "calories": 500},
        ]

        result = get_plate_recommendations(foods)
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["type"] == "increase_carbs"

    def test_calculate_plate_score_high_protein(self) -> None:
        """Test plate score with high protein (covers line 591)."""
        from core.plate import calculate_plate_score

        # High protein > 25%
        foods = [
            {"protein": 80, "carbs": 50, "fat": 20, "calories": 700},
        ]

        result = calculate_plate_score(foods)
        assert isinstance(result, float)
        assert 0 <= result <= 100

    def test_calculate_plate_score_low_carbs(self) -> None:
        """Test plate score with low carbs (covers line 594)."""
        from core.plate import calculate_plate_score

        # Low carbs < 45%
        foods = [
            {"protein": 50, "carbs": 30, "fat": 40, "calories": 700},
        ]

        result = calculate_plate_score(foods)
        assert isinstance(result, float)

    def test_calculate_plate_score_high_carbs(self) -> None:
        """Test plate score with high carbs (covers line 596)."""
        from core.plate import calculate_plate_score

        # High carbs > 65%
        foods = [
            {"protein": 10, "carbs": 150, "fat": 10, "calories": 740},
        ]

        result = calculate_plate_score(foods)
        assert isinstance(result, float)

    def test_calculate_plate_score_low_fat(self) -> None:
        """Test plate score with low fat (covers line 599)."""
        from core.plate import calculate_plate_score

        # Low fat < 20%
        foods = [
            {"protein": 40, "carbs": 100, "fat": 5, "calories": 605},
        ]

        result = calculate_plate_score(foods)
        assert isinstance(result, float)

    def test_calculate_plate_score_high_fat(self) -> None:
        """Test plate score with high fat (covers line 601)."""
        from core.plate import calculate_plate_score

        # High fat > 35%
        foods = [
            {"protein": 20, "carbs": 50, "fat": 50, "calories": 730},
        ]

        result = calculate_plate_score(foods)
        assert isinstance(result, float)

    def test_create_nutrition_plate_type_error(self) -> None:
        """Test plate creation with invalid type (covers lines 471-472)."""
        from core.plate import create_nutrition_plate

        # Pass food with a non-numeric string value that causes TypeError on addition
        # "abc" or 0 -> "abc" (truthy), then 0 += "abc" raises TypeError
        foods = [{"calories": "not_a_number"}]

        result = create_nutrition_plate(foods)
        assert result is None


class TestAutoRepairEdgeCases:
    """Additional edge case tests for auto_repair.py coverage."""

    def test_get_repair_suggestions_non_dict_info(self) -> None:
        """Test repair suggestions when info is not a dict (covers line 467)."""
        from core.auto_repair import get_repair_suggestions

        # deficiencies where info is not a dict
        deficiencies = {"protein": "not_a_dict", "carbs": 123}
        foods = [{"name": "chicken", "protein": 25}]

        result = get_repair_suggestions(deficiencies, foods)
        assert isinstance(result, list)

    def test_get_repair_suggestions_zero_deficit(self) -> None:
        """Test repair suggestions when deficit is zero or negative (covers line 471)."""
        from core.auto_repair import get_repair_suggestions

        deficiencies = {
            "protein": {"deficit": 0},
            "carbs": {"deficit": -10},
        }
        foods = [{"name": "chicken", "protein": 25}]

        result = get_repair_suggestions(deficiencies, foods)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_calculate_repair_priority_nested_dict(self) -> None:
        """Test priority with nested deficit dict (covers line 509)."""
        from core.auto_repair import calculate_repair_priority

        # Nested dict where deficit is itself a dict
        deficiency = {"deficit": {"deficit": 30}}
        target = {"protein": 100}

        result = calculate_repair_priority(deficiency, target)
        assert isinstance(result, float)

    def test_calculate_repair_priority_numeric_inputs(self) -> None:
        """Test priority with numeric inputs (covers lines 519-520)."""
        from core.auto_repair import calculate_repair_priority

        # Pass numeric values instead of dicts
        result = calculate_repair_priority(20, 100)  # type: ignore[arg-type]
        assert isinstance(result, float)
        assert result == 20.0  # 20/100 * 100 = 20


class TestMenuEngineEdgeCases:
    """Additional edge case tests for menu_engine.py coverage."""

    def test_calculate_nutrition_totals_type_error(self) -> None:
        """Test nutrition totals with invalid type (covers lines 842-843)."""
        from core.menu_engine import calculate_nutrition_totals

        # Pass None which should trigger exception handling
        result = calculate_nutrition_totals(None)  # type: ignore[arg-type]
        assert result is None

    def test_generate_shopping_list_type_error(self) -> None:
        """Test shopping list with invalid type (covers lines 871-872)."""
        from core.menu_engine import generate_shopping_list

        # Pass None which should trigger exception handling
        result = generate_shopping_list(None)  # type: ignore[arg-type]
        assert result is None


class TestTargetsEdgeCases:
    """Additional edge case tests for targets.py coverage."""

    def test_calculate_bmr_type_error(self) -> None:
        """Test BMR with invalid types (covers lines 510-511)."""
        from core.targets import calculate_bmr

        # Pass invalid types that should trigger exception
        result = calculate_bmr(age="thirty", gender="M", weight=70, height=175)  # type: ignore[arg-type]
        assert result is None

    def test_calculate_tdee_exception(self) -> None:
        """Test TDEE with edge cases (covers lines 541-542)."""
        from core.targets import calculate_tdee

        # Pass None as bmr
        result = calculate_tdee(bmr=None, activity="moderate")  # type: ignore[arg-type]
        assert result is None
