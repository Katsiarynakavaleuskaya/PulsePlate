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
    _macros_by_rules,
    _portions_from_macros,
    _target_kcal,
    _visual_layout,
    make_plate,
)


class TestCorePlateLogic:
    """Test core plate generation logic."""

    def test_target_kcal_calculation(self):
        """Test target calorie calculation for different goals."""
        tdee = 2000

        # Test maintenance
        target = _target_kcal(tdee, "maintain", None, None)
        assert target == 2000

        # Test weight loss with default deficit
        target = _target_kcal(tdee, "loss", None, None)
        assert target == 1700  # 15% deficit

        # Test weight loss with custom deficit
        target = _target_kcal(tdee, "loss", 20, None)
        assert target == 1600  # 20% deficit

        # Test weight gain with default surplus
        target = _target_kcal(tdee, "gain", None, None)
        assert target == 2240  # 12% surplus

        # Test weight gain with custom surplus
        target = _target_kcal(tdee, "gain", None, 15)
        assert target == 2300  # 15% surplus

        # Test minimum calorie floor
        very_low_tdee = 1000
        target = _target_kcal(very_low_tdee, "loss", 25, None)
        assert target == 1200  # Should not go below 1200

    def test_macros_by_rules(self):
        """Test macro distribution rules for different goals."""
        weight = 70  # kg
        kcal = 2000

        # Test weight loss macros (higher protein)
        macros = _macros_by_rules(weight, kcal, "loss")
        assert macros["protein_g"] >= 126  # At least 1.8g/kg
        assert macros["fat_g"] == 56      # 0.8g/kg
        assert macros["carbs_g"] >= 0
        assert macros["fiber_g"] in [25, 30]

        # Test maintenance macros
        macros = _macros_by_rules(weight, kcal, "maintain")
        assert macros["protein_g"] == 119  # 1.7g/kg
        assert macros["fat_g"] == 63       # 0.9g/kg
        assert macros["carbs_g"] >= 0

        # Test weight gain macros
        macros = _macros_by_rules(weight, kcal, "gain")
        assert macros["protein_g"] == 112  # 1.6g/kg
        assert macros["fat_g"] == 70       # 1.0g/kg
        assert macros["carbs_g"] >= 0

        # Verify calorie consistency (approximately)
        total_kcal = (macros["protein_g"] * 4) + (macros["fat_g"] * 9) + (macros["carbs_g"] * 4)
        assert abs(total_kcal - kcal) <= 20  # Allow small rounding differences

    def test_portions_from_macros(self):
        """Test conversion of macros to hand/cup portions."""
        macros = {
            "protein_g": 120,
            "fat_g": 60,
            "carbs_g": 200,
            "fiber_g": 30
        }

        portions = _portions_from_macros(macros, meals_per_day=3)

        # Check portion calculations
        expected_protein_palm = 120 / (30 * 3)  # protein_g / (protein_palm_g * meals)
        expected_fat_thumbs = 60 / (12 * 3)     # fat_g / (fat_thumb_g * meals)
        expected_carb_cups = 200 / (40 * 3)     # carbs_g / (carb_cup_g * meals)
        expected_veg_cups = (30 * 10) / (80 * 3)  # (fiber_g * 10) / (veg_cup_g * meals)

        assert portions["protein_palm"] == round(expected_protein_palm, 1)
        assert portions["fat_thumbs"] == round(expected_fat_thumbs, 1)
        assert portions["carb_cups"] == round(expected_carb_cups, 1)
        assert portions["veg_cups"] == round(expected_veg_cups, 1)
        assert portions["meals_per_day"] == 3

    def test_visual_layout_structure(self):
        """Test visual layout generation."""
        macros = {
            "protein_g": 120,
            "fat_g": 60,
            "carbs_g": 200,
            "fiber_g": 30
        }

        layout = _visual_layout(macros)

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

    def test_make_plate_integration(self):
        """Test complete plate generation integration."""
        plate = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags=None
        )

        # Check response structure
        required_keys = {"kcal", "macros", "portions", "layout", "meals"}
        assert set(plate.keys()) == required_keys

        # Check kcal
        assert isinstance(plate["kcal"], int)
        assert 1500 <= plate["kcal"] <= 2500

        # Check macros
        macros = plate["macros"]
        assert all(k in macros for k in ["protein_g", "fat_g", "carbs_g", "fiber_g"])
        assert all(isinstance(v, int) for v in macros.values())

        # Check portions
        portions = plate["portions"]
        portion_keys = {"protein_palm", "fat_thumbs", "carb_cups", "veg_cups", "meals_per_day"}
        assert portion_keys.issubset(set(portions.keys()))

        # Check layout
        layout = plate["layout"]
        assert len(layout) == 6
        assert all("kind" in item for item in layout)

        # Check meals
        meals = plate["meals"]
        assert len(meals) == 3
        assert all("title" in meal and "kcal" in meal for meal in meals)

    def test_diet_flags_modifications(self):
        """Test diet flags modify meal suggestions."""
        # Test VEG flag
        plate_veg = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"VEG"}
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
            diet_flags={"GF"}
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
            diet_flags={"LOW_COST"}
        )

        meals_text = " ".join([meal["title"] for meal in plate_budget["meals"]])
        assert "(бюджет)" in meals_text

    def test_plate_goal_consistency(self):
        """Test different goals produce consistent results."""
        base_params = {
            "weight_kg": 70,
            "tdee_val": 2000,
            "diet_flags": None
        }

        # Test loss goal
        plate_loss = make_plate(goal="loss", deficit_pct=15, surplus_pct=None, **base_params)
        assert plate_loss["kcal"] < 2000  # Should be below TDEE

        # Test maintain goal
        plate_maintain = make_plate(goal="maintain", deficit_pct=None, surplus_pct=None, **base_params)
        assert plate_maintain["kcal"] == 2000  # Should equal TDEE

        # Test gain goal
        plate_gain = make_plate(goal="gain", deficit_pct=None, surplus_pct=12, **base_params)
        assert plate_gain["kcal"] > 2000  # Should be above TDEE

        # Loss should have relatively more protein
        loss_protein_ratio = plate_loss["macros"]["protein_g"] / plate_loss["kcal"]
        maintain_protein_ratio = plate_maintain["macros"]["protein_g"] / plate_maintain["kcal"]
        assert loss_protein_ratio >= maintain_protein_ratio

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test very low TDEE
        plate_low = make_plate(
            weight_kg=50,
            tdee_val=1000,
            goal="loss",
            deficit_pct=20,
            surplus_pct=None,
            diet_flags=None
        )
        assert plate_low["kcal"] >= 1200  # Should enforce minimum

        # Test very high TDEE
        plate_high = make_plate(
            weight_kg=100,
            tdee_val=4000,
            goal="gain",
            deficit_pct=None,
            surplus_pct=15,
            diet_flags=None
        )
        assert plate_high["kcal"] > 4000

        # Test zero macros scenario (should not crash)
        try:
            layout = _visual_layout({"protein_g": 0, "fat_g": 0, "carbs_g": 0, "fiber_g": 0})
            assert len(layout) == 6  # Should still return proper layout
        except ZeroDivisionError:
            pytest.fail("Visual layout should handle zero macros gracefully")

    def test_multiple_diet_flags(self):
        """Test combining multiple diet flags."""
        plate = make_plate(
            weight_kg=70,
            tdee_val=2000,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            diet_flags={"VEG", "GF", "LOW_COST"}
        )

        meals_text = " ".join([meal["title"] for meal in plate["meals"]])

        # Should contain vegetarian proteins
        assert "тофу" in meals_text or "нут" in meals_text
        # Should use gluten-free grains
        assert "Гречка" in meals_text or "гречка" in meals_text
        # Should mark as budget
        assert "(бюджет)" in meals_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
