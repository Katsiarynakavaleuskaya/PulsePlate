"""
Tests for core.plate module

Tests core plate generation logic:
- Calorie target calculation
- Macro distribution rules
- Portion conversion (hand/cup method)
- Visual layout generation
- Diet flag meal modifications
- Edge cases and input validation
"""

import pytest

from core.plate import (
    apply_diet_flag_adjustments,
    macros_by_rules,
    make_plate,
    portions_from_macros,
    target_kcal,
)


class TestCorePlateLogic:
    """Test core plate generation logic."""

    def test_target_kcal_calculation(self) -> None:
        """Test target calorie calculation for different goals."""
        tdee = 2000

        # Test maintenance
        target = target_kcal(tdee, "maintain", None, None)
        assert target == 2000

        # Test weight loss with default deficit
        target = target_kcal(tdee, "loss", None, None)
        assert target == 1700  # 15% deficit

        # Test weight loss with custom deficit
        target = target_kcal(tdee, "loss", 20, None)
        assert target == 1600  # 20% deficit

        # Test weight gain with default surplus
        target = target_kcal(tdee, "gain", None, None)
        assert target == 2240  # 12% surplus

        # Test weight gain with custom surplus
        target = target_kcal(tdee, "gain", None, 15)
        assert target == 2300  # 15% surplus

        # Test minimum calorie floor
        very_low_tdee = 1000
        target = target_kcal(very_low_tdee, "loss", 25, None)
        assert target == 1200  # Should not go below 1200

    def testmacros_by_rules(self):
        """Test macro distribution rules for different goals."""
        weight = 70  # kg
        kcal = 2000

        # Test weight loss macros (higher protein)
        macros = macros_by_rules(weight, kcal, "loss")
        assert macros["protein_g"] >= 126  # At least 1.8g/kg
        assert macros["fat_g"] == 56  # 0.8g/kg
        assert macros["carbs_g"] >= 0
        assert macros["fiber_g"] in [25, 30]

        # Test maintenance macros
        macros = macros_by_rules(weight, kcal, "maintain")
        assert macros["protein_g"] == 119  # 1.7g/kg
        assert macros["fat_g"] == 63  # 0.9g/kg
        assert macros["carbs_g"] >= 0

        # Test weight gain macros
        macros = macros_by_rules(weight, kcal, "gain")
        assert macros["protein_g"] == 112  # 1.6g/kg
        assert macros["fat_g"] == 70  # 1.0g/kg
        assert macros["carbs_g"] >= 0

        # Verify calorie consistency (approximately)
        total_kcal = (macros["protein_g"] * 4) + (macros["fat_g"] * 9) + (macros["carbs_g"] * 4)
        assert abs(total_kcal - kcal) <= 20  # Allow small rounding differences

        # Test edge case: very low calories that require macro reduction
        low_kcal = 800  # Very low calories
        macros_low = macros_by_rules(weight, low_kcal, "loss")
        # Should still have reasonable macros, carbs should be at least 1
        assert macros_low["protein_g"] >= 1
        assert macros_low["fat_g"] >= 0.5 * weight  # Should not go below 0.5g/kg
        assert macros_low["carbs_g"] >= 1  # Minimum carbs
        # Total calories should be close to target
        total_kcal_low = (
            (macros_low["protein_g"] * 4) + (macros_low["fat_g"] * 9) + (macros_low["carbs_g"] * 4)
        )
        assert abs(total_kcal_low - low_kcal) <= 50  # Allow some tolerance for edge cases

    def test_portions_from_macros(self) -> None:
        """Test conversion of macros to hand/cup portions."""
        macros = {"protein_g": 120, "fat_g": 60, "carbs_g": 200, "fiber_g": 30}

        portions = portions_from_macros(macros, meals_per_day=3)

        # Check portion calculations
        expected_protein_palm = 120 / (30 * 3)  # protein_g / (protein_palm_g * meals)
        expected_fat_thumbs = 60 / (12 * 3)  # fat_g / (fat_thumb_g * meals)
        expected_carb_cups = 200 / (40 * 3)  # carbs_g / (carb_cup_g * meals)
        expected_veg_cups = (30 * 10) / (80 * 3)  # (fiber_g * 10) / (veg_cup_g * meals)

        assert portions["protein_palm"] == round(expected_protein_palm, 1)
        assert portions["fat_thumbs"] == round(expected_fat_thumbs, 1)
        assert portions["carb_cups"] == round(expected_carb_cups, 1)
        assert portions["veg_cups"] == round(expected_veg_cups, 1)
        # meals_per_day is metadata, no longer included in portions dict
        assert "meals_per_day" not in portions

    def test_visual_layout_structure(self) -> None:
        """Test visual layout generation via public API."""
        # Use make_plate to get layout through public API
        plate = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags=None,
        )

        layout = plate["layout"]

        # Should have 6 items: 4 sectors + 2 bowls
        assert len(layout) == 6

        # Check item types
        sectors = [item for item in layout if item["kind"] == "plate_sector"]
        bowls = [item for item in layout if item["kind"] == "bowl"]

        assert len(sectors) == 4
        assert len(bowls) == 2

        # Check all items have required fields
        for item in layout:
            assert "kind" in item
            assert "fraction" in item
            assert "label" in item
            assert "tooltip" in item

        # Check sector fractions sum appropriately (vegetables + energy macros)
        sector_fractions = [item["fraction"] for item in sectors]
        assert all(0 <= frac <= 1 for frac in sector_fractions)

        # Bowls should have fraction 1.0
        bowl_fractions = [item["fraction"] for item in bowls]
        assert all(frac == 1.0 for frac in bowl_fractions)

    def test_make_plate_integration(self) -> None:
        """Test complete plate generation integration."""
        plate = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags=None,
        )

        # Check response structure
        required_keys = {"kcal", "macros", "portions", "layout", "meals", "meals_per_day"}
        assert set(plate.keys()) == required_keys

        # Check kcal
        assert isinstance(plate["kcal"], int)
        assert 1500 <= plate["kcal"] <= 2500

        # Check macros
        macros = plate["macros"]
        assert all(k in macros for k in ["protein_g", "fat_g", "carbs_g", "fiber_g"])
        assert all(isinstance(v, int) for v in macros.values())

        # Check portions (meals_per_day is now metadata, not in portions)
        portions = plate["portions"]
        portion_keys = {
            "protein_palm",
            "fat_thumbs",
            "carb_cups",
            "veg_cups",
        }
        assert portion_keys.issubset(set(portions.keys()))
        # Check meals_per_day is at top level
        assert "meals_per_day" in plate
        assert plate["meals_per_day"] == 3

        # Check layout
        layout = plate["layout"]
        assert len(layout) == 6
        assert all("kind" in item for item in layout)

        # Check meals
        meals = plate["meals"]
        assert len(meals) == 3
        assert all("title" in meal and "kcal" in meal for meal in meals)

    def test_diet_flags_modifications(self) -> None:
        """Test diet flags modify meal suggestions."""
        base_plate = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags=None,
        )
        # Test VEG flag
        plate_veg = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"VEG"},
        )

        meals_text = " ".join([meal["title"] for meal in plate_veg["meals"]])
        assert "тофу" in meals_text or "нут" in meals_text

        # Test GF flag
        plate_gf = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"GF"},
        )

        meals_text = " ".join([meal["title"] for meal in plate_gf["meals"]])
        assert "Гречка" in meals_text or "гречка" in meals_text

        # Test LOW_COST flag
        plate_budget = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"LOW_COST"},
        )

        meals_text = " ".join([meal["title"] for meal in plate_budget["meals"]])
        assert "(бюджет)" in meals_text

        # Test HIGH_PROTEIN flag increases protein
        plate_high_protein = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"HIGH_PROTEIN"},
        )
        assert plate_high_protein["macros"]["protein_g"] > base_plate["macros"]["protein_g"]

        # Test LOW_CARB reduces carbs
        plate_low_carb = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"LOW_CARB"},
        )
        assert plate_low_carb["macros"]["carbs_g"] < base_plate["macros"]["carbs_g"]

        # Test MEDITERRANEAN increases healthy fats and fiber
        plate_med = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"MEDITERRANEAN"},
        )
        assert plate_med["macros"]["fat_g"] >= base_plate["macros"]["fat_g"]
        assert plate_med["macros"]["fiber_g"] >= base_plate["macros"]["fiber_g"]

        # Test VEGAN inherits vegetarian adjustments
        plate_vegan = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"VEGAN"},
        )
        vegan_meals = " ".join(meal["title"] for meal in plate_vegan["meals"])
        assert "тофу" in vegan_meals or "соевый" in vegan_meals or "нут" in vegan_meals

        # Test KETO applies both high-protein and low-carb adjustments
        plate_keto = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"KETO"},
        )
        assert plate_keto["macros"]["protein_g"] >= plate_high_protein["macros"]["protein_g"]
        assert plate_keto["macros"]["carbs_g"] <= plate_low_carb["macros"]["carbs_g"]
        assert any("кето-версия" in meal["title"] for meal in plate_keto["meals"])

        # Test PALEO boosts protein-focused meals with substitutions
        plate_paleo = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"PALEO"},
        )
        paleo_meals = " ".join(meal["title"] for meal in plate_paleo["meals"])
        assert "батат" in paleo_meals or "чиа" in paleo_meals
        assert plate_paleo["macros"]["protein_g"] >= base_plate["macros"]["protein_g"]

    def test_plate_goal_consistency(self) -> None:
        """Test different goals produce consistent results."""
        base_params: dict[str, float | None] = {
            "weight_kg": 70.0,
            "tdee_val": 2000.0,
            "diet_flags": None,
        }

        # Test loss goal
        plate_loss = make_plate(
            goal="loss", deficit_pct=15.0, surplus_pct=None, **base_params  # type: ignore[arg-type]
        )
        assert plate_loss["kcal"] < 2000  # Should be below TDEE

        # Test maintain goal
        plate_maintain = make_plate(
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            **base_params,  # type: ignore[arg-type]
        )
        assert plate_maintain["kcal"] == 2000  # Should equal TDEE

        # Test gain goal
        plate_gain = make_plate(
            goal="gain", deficit_pct=None, surplus_pct=12.0, **base_params  # type: ignore[arg-type]
        )
        assert plate_gain["kcal"] > 2000  # Should be above TDEE

        # Loss should have relatively more protein
        loss_protein_ratio = plate_loss["macros"]["protein_g"] / plate_loss["kcal"]
        maintain_protein_ratio = plate_maintain["macros"]["protein_g"] / plate_maintain["kcal"]
        assert loss_protein_ratio >= maintain_protein_ratio

    def test_edge_cases(self) -> None:
        """Test edge cases and boundary conditions."""
        # Test very low TDEE
        plate_low = make_plate(
            weight_kg=50,
            tdee_val=1000,
            goal="loss",
            deficit_pct=20,
            surplus_pct=None,
            diet_flags=None,
        )
        assert plate_low["kcal"] >= 1200  # Should enforce minimum

        # Test very high TDEE
        plate_high = make_plate(
            weight_kg=100,
            tdee_val=4000,
            goal="gain",
            deficit_pct=None,
            surplus_pct=15,
            diet_flags=None,
        )
        assert plate_high["kcal"] > 4000

        # Test zero macros scenario (should not crash)
        # Use make_plate with very low TDEE to test edge case
        try:
            plate = make_plate(
                weight_kg=50,
                tdee_val=1000,
                goal="loss",
                deficit_pct=50,  # Very aggressive deficit
                surplus_pct=None,
                diet_flags=None,
            )
            layout = plate["layout"]
            assert len(layout) == 6  # Should still return proper layout
        except ZeroDivisionError:
            pytest.fail("Visual layout should handle zero macros gracefully")

    def test_meals_per_day_validation(self) -> None:
        """Test meals_per_day parameter validation."""
        base_params: dict[str, float | str | None] = {
            "weight_kg": 70.0,
            "tdee_val": 2000.0,
            "goal": "maintain",
            "deficit_pct": None,
            "surplus_pct": None,
            "diet_flags": None,
        }

        # Test valid values at boundaries
        plate_min = make_plate(**base_params, meals_per_day=1)  # type: ignore[arg-type]
        assert plate_min["meals_per_day"] == 1

        plate_max = make_plate(**base_params, meals_per_day=12)  # type: ignore[arg-type]
        assert plate_max["meals_per_day"] == 12

        plate_default = make_plate(**base_params)  # type: ignore[arg-type]  # Should default to 3
        assert plate_default["meals_per_day"] == 3

        # Test invalid type - should raise ValueError
        with pytest.raises(ValueError, match="must be an integer"):
            make_plate(**base_params, meals_per_day="3")  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="must be an integer"):
            make_plate(**base_params, meals_per_day=3.5)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="must be an integer"):
            make_plate(**base_params, meals_per_day=None)  # type: ignore[arg-type]

        # Test invalid range - should raise ValueError
        with pytest.raises(ValueError, match="must be between 1 and 12"):
            make_plate(**base_params, meals_per_day=0)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="must be between 1 and 12"):
            make_plate(**base_params, meals_per_day=-1)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="must be between 1 and 12"):
            make_plate(**base_params, meals_per_day=13)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="must be between 1 and 12"):
            make_plate(**base_params, meals_per_day=100)  # type: ignore[arg-type]

        # Test that valid meals_per_day affects portion calculations
        plate_1_meal = make_plate(**base_params, meals_per_day=1)  # type: ignore[arg-type]
        plate_6_meals = make_plate(**base_params, meals_per_day=6)  # type: ignore[arg-type]

        # With 1 meal per day, portions should be larger
        assert plate_1_meal["portions"]["protein_palm"] > plate_6_meals["portions"]["protein_palm"]
        assert plate_1_meal["portions"]["carb_cups"] > plate_6_meals["portions"]["carb_cups"]

    def test_multiple_diet_flags(self) -> None:
        """Test combining multiple diet flags."""
        plate = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"VEG", "GF", "LOW_COST"},
        )

        meals_text = " ".join([meal["title"] for meal in plate["meals"]])

        # Should contain vegetarian proteins
        assert "тофу" in meals_text or "нут" in meals_text
        # Should use gluten-free grains
        assert "Гречка" in meals_text or "гречка" in meals_text
        # Should mark as budget
        assert "(бюджет)" in meals_text


class TestDietFlagAdjustments:
    """Test diet flag macro adjustments."""

    def test_no_diet_flags_returns_original(self):
        """Test that no diet flags leaves macros unchanged."""
        macros = {"protein_g": 100, "fat_g": 70, "carbs_g": 200, "fiber_g": 25}

        result = apply_diet_flag_adjustments(macros, weight_kg=70, kcal=2000, diet_flags=None)

        assert result == macros

    def test_empty_diet_flags_returns_original(self):
        """Test that empty diet flags set leaves macros unchanged."""
        macros = {"protein_g": 100, "fat_g": 70, "carbs_g": 200, "fiber_g": 25}

        result = apply_diet_flag_adjustments(macros, weight_kg=70, kcal=2000, diet_flags=set())

        assert result == macros

    def test_high_protein_flag_increases_protein(self):
        """Test HIGH_PROTEIN flag increases protein to at least 2.0g/kg."""
        macros = {"protein_g": 100, "fat_g": 70, "carbs_g": 200, "fiber_g": 25}

        result = apply_diet_flag_adjustments(
            macros, weight_kg=70, kcal=2000, diet_flags={"HIGH_PROTEIN"}
        )

        # Should increase protein to at least 70kg * 2.0g = 140g
        assert result["protein_g"] >= 140
        assert result["protein_g"] > macros["protein_g"]  # Should be increased

    def test_high_protein_flag_preserves_if_already_high(self):
        """Test HIGH_PROTEIN flag doesn't decrease already high protein."""
        macros = {"protein_g": 200, "fat_g": 70, "carbs_g": 200, "fiber_g": 25}

        result = apply_diet_flag_adjustments(
            macros, weight_kg=70, kcal=2000, diet_flags={"HIGH_PROTEIN"}
        )

        # Should preserve existing high protein (200 > 140 required)
        assert result["protein_g"] == 200

    def test_low_carb_flag_limits_carbs(self):
        """Test LOW_CARB flag limits carbs to maximum values."""
        # Test with high carb intake
        macros = {"protein_g": 100, "fat_g": 70, "carbs_g": 300, "fiber_g": 25}

        result = apply_diet_flag_adjustments(
            macros, weight_kg=70, kcal=2000, diet_flags={"LOW_CARB"}
        )

        # Should limit carbs to max(40, kcal * 0.25 / 4)
        expected_cap = max(40, (2000 * 0.25) / 4)
        assert result["carbs_g"] <= expected_cap

    def test_mediterranean_flag_adjusts_ratios(self):
        """Test MEDITERRANEAN flag adjusts macro ratios."""
        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 250, "fiber_g": 25}

        result = apply_diet_flag_adjustments(
            macros, weight_kg=70, kcal=2000, diet_flags={"MEDITERRANEAN"}
        )

        # Should increase fat to at least 35% of calories and ≥1.2x protein
        expected_fat = max(macros["fat_g"], (2000 * 0.35) / 9, macros["protein_g"] * 1.2)
        assert result["fat_g"] >= expected_fat
        assert result["fiber_g"] >= 30

    def test_multiple_diet_flags_combined(self):
        """Test multiple diet flags work together."""
        macros = {"protein_g": 80, "fat_g": 50, "carbs_g": 300, "fiber_g": 25}

        result = apply_diet_flag_adjustments(
            macros, weight_kg=70, kcal=2000, diet_flags={"HIGH_PROTEIN", "LOW_CARB"}
        )

        # Should apply both adjustments
        assert result["protein_g"] >= 140  # HIGH_PROTEIN effect
        expected_cap = max(40, (2000 * 0.25) / 4)
        assert result["carbs_g"] <= expected_cap  # LOW_CARB effect

    def test_mediterranean_with_high_protein(self):
        """Mediterranean combined with High-Protein keeps both targets."""
        macros = {"protein_g": 110, "fat_g": 60, "carbs_g": 220, "fiber_g": 25}

        result = apply_diet_flag_adjustments(
            macros, weight_kg=80, kcal=2200, diet_flags={"MEDITERRANEAN", "HIGH_PROTEIN"}
        )

        assert result["protein_g"] >= 160  # 80kg * 2 g/kg
        assert result["fat_g"] >= result["protein_g"] * 1.2
        assert result["fiber_g"] >= 30

    @pytest.mark.parametrize("weight_kg", [50, 70, 90, 100])
    def test_high_protein_scales_with_weight(self, weight_kg):
        """Test HIGH_PROTEIN adjustment scales with body weight."""
        macros = {"protein_g": 50, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}

        result = apply_diet_flag_adjustments(
            macros, weight_kg=weight_kg, kcal=2000, diet_flags={"HIGH_PROTEIN"}
        )

        # Should set protein to at least weight_kg * 2.0
        expected_min = weight_kg * 2.0
        assert result["protein_g"] >= expected_min

    def test_diet_adjustments_with_kcal_overflow(self):
        """Test that diet adjustments handle kcal overflow by reducing macros."""
        # Create a scenario where HIGH_PROTEIN + MEDITERRANEAN would exceed kcal
        macros = {"protein_g": 50, "fat_g": 50, "carbs_g": 150, "fiber_g": 25}

        result = apply_diet_flag_adjustments(
            macros, weight_kg=70, kcal=1500, diet_flags={"HIGH_PROTEIN", "MEDITERRANEAN"}
        )

        # Should honor high-protein and mediterranean constraints even if kcal rises
        assert result["protein_g"] >= 140  # HIGH_PROTEIN target (70kg * 2g/kg)
        assert result["fat_g"] >= result["protein_g"] * 1.2

        # Should maintain protein minimum, but fat may be reduced to meet kcal constraints
        # Note: Mediterranean keeps fat ≥ 1.2× protein; protein may be reduced next if still over kcal

    def test_high_protein_trims_fat_to_meet_calorie_target(self):
        """HIGH_PROTEIN should shave excess fat to stay within calorie budget."""
        macros = {"protein_g": 100, "fat_g": 200, "carbs_g": 50, "fiber_g": 25}
        weight_kg = 70

        result = apply_diet_flag_adjustments(
            macros, weight_kg=weight_kg, kcal=1500, diet_flags={"HIGH_PROTEIN"}
        )

        # Protein should be raised to 2 g/kg while fat is reduced but kept above the healthy floor.
        assert result["protein_g"] == int(weight_kg * 2.0)
        assert result["fat_g"] < macros["fat_g"]
        assert result["fat_g"] >= int(0.7 * weight_kg)
        # Calories are fully consumed, so carbs drop to the default floor of 30 g.
        assert result["carbs_g"] == 30

    def test_mediterranean_reduces_protein_when_calories_exceeded(self):
        """Mediterranean adjustments should dial protein back if fat increase breaks the budget."""
        macros = {"protein_g": 180, "fat_g": 150, "carbs_g": 50, "fiber_g": 25}
        weight_kg = 70

        result = apply_diet_flag_adjustments(
            macros, weight_kg=weight_kg, kcal=1600, diet_flags={"MEDITERRANEAN"}
        )

        # Fat rises to the Mediterranean preference, which forces protein to the minimum of 1.6 g/kg.
        assert result["fat_g"] > macros["fat_g"]
        assert result["protein_g"] == int(weight_kg * 1.6)
        assert result["carbs_g"] == 30  # Carb floor applies when calories are exhausted.
        assert result["fiber_g"] == 30  # Mediterranean raises fiber minimum.

    def test_diet_adjustments_kcal_underflow(self):
        """Test diet adjustments handle extreme macro increases."""
        # Very high protein that would make carbs negative
        macros = {"protein_g": 300, "fat_g": 100, "carbs_g": 50, "fiber_g": 25}

        result = apply_diet_flag_adjustments(
            macros, weight_kg=70, kcal=2000, diet_flags={"LOW_CARB"}
        )

        # Should still have minimum carbs (40g for LOW_CARB)
        assert result["carbs_g"] >= 40

        # Total kcal should be reasonable
        total_kcal = (result["protein_g"] * 4) + (result["fat_g"] * 9) + (result["carbs_g"] * 4)
        assert total_kcal <= 2500  # Allow some flexibility


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
