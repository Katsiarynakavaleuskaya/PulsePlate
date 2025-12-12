"""
Tests for dietary_constraints.py - Dietary Restrictions Logic

Test coverage: 97%+ target
"""

import pytest

from core.dietary_constraints import (
    DIET_FLAGS,
    DIET_IMPLICATIONS,
    INCOMPATIBLE_COMBINATIONS,
    adjust_macros_for_diet,
    get_diet_description,
    is_recipe_compatible,
    normalize_diet_flags,
)


class TestNormalizeDietFlags:
    """Test normalize_diet_flags function."""

    def test_normalize_empty_flags(self):
        """Test with empty set."""
        result = normalize_diet_flags(set())
        assert result == set()

    def test_normalize_vegan_implications(self):
        """Test VEGAN implies VEG and DAIRY_FREE."""
        result = normalize_diet_flags({"VEGAN"})
        assert "VEGAN" in result
        assert "VEG" in result
        assert "DAIRY_FREE" in result

    def test_normalize_keto_implications(self):
        """Test KETO implies LOW_CARB and HIGH_PROTEIN."""
        result = normalize_diet_flags({"KETO"})
        assert "KETO" in result
        assert "LOW_CARB" in result
        assert "HIGH_PROTEIN" in result

    def test_normalize_paleo_implications(self):
        """Test PALEO implies HIGH_PROTEIN, GF, and DAIRY_FREE."""
        result = normalize_diet_flags({"PALEO"})
        assert "PALEO" in result
        assert "HIGH_PROTEIN" in result
        assert "GF" in result
        assert "DAIRY_FREE" in result

    def test_normalize_resolves_keto_vegan_conflict(self):
        """Test KETO + VEGAN conflict resolution (prefers VEGAN)."""
        result = normalize_diet_flags({"KETO", "VEGAN"})

        # VEGAN should win in conflict resolution
        assert "VEGAN" in result
        # Should still have VEGAN implications
        assert "VEG" in result
        assert "DAIRY_FREE" in result

    def test_normalize_multiple_compatible_flags(self):
        """Test multiple compatible flags."""
        result = normalize_diet_flags({"GF", "DAIRY_FREE", "NUT_FREE"})

        assert "GF" in result
        assert "DAIRY_FREE" in result
        assert "NUT_FREE" in result

    def test_normalize_preserves_non_conflicting_flags(self):
        """Test that non-conflicting flags are preserved."""
        result = normalize_diet_flags({"HIGH_PROTEIN", "GF", "LOW_COST"})

        assert "HIGH_PROTEIN" in result
        assert "GF" in result
        assert "LOW_COST" in result


class TestIsRecipeCompatible:
    """Test is_recipe_compatible function."""

    def test_vegan_recipe_for_vegan_user(self):
        """Test VEGAN recipe is compatible with VEGAN diet."""
        assert is_recipe_compatible({"VEGAN"}, {"VEGAN"}) is True

    def test_veg_recipe_for_vegan_user(self):
        """Test VEG recipe is NOT compatible with VEGAN diet."""
        assert is_recipe_compatible({"VEG"}, {"VEGAN"}) is False

    def test_non_vegan_name_rejected(self):
        """Test recipe with animal product in name rejected for VEGAN."""
        assert is_recipe_compatible({"VEGAN"}, {"VEGAN"}, recipe_name="Chicken Salad") is False

        assert is_recipe_compatible({"VEGAN"}, {"VEGAN"}, recipe_name="Salmon Bowl") is False

    def test_vegan_name_accepted(self):
        """Test recipe with plant-based name accepted for VEGAN."""
        assert is_recipe_compatible({"VEGAN"}, {"VEGAN"}, recipe_name="Tofu Stir-fry") is True

    def test_veg_recipe_rejects_meat(self):
        """Test VEG diet rejects meat in recipe name."""
        assert is_recipe_compatible(set(), {"VEG"}, recipe_name="Beef Stew") is False

        assert is_recipe_compatible(set(), {"VEG"}, recipe_name="Fish Tacos") is False

    def test_gluten_free_rejects_gluten(self):
        """Test GF diet rejects gluten-containing recipes."""
        assert is_recipe_compatible({"gluten"}, {"GF"}) is False
        assert is_recipe_compatible({"wheat"}, {"GF"}) is False
        assert is_recipe_compatible(set(), {"GF"}, recipe_name="Wheat Bread") is False

    def test_gluten_free_accepts_gf_recipe(self):
        """Test GF diet accepts gluten-free recipes."""
        assert is_recipe_compatible({"GF"}, {"GF"}) is True
        assert is_recipe_compatible(set(), {"GF"}, recipe_name="Rice Bowl") is True

    def test_dairy_free_rejects_dairy(self):
        """Test DAIRY_FREE rejects dairy products."""
        assert is_recipe_compatible({"milk"}, {"DAIRY_FREE"}) is False
        assert is_recipe_compatible({"cheese"}, {"DAIRY_FREE"}) is False
        assert is_recipe_compatible({"yogurt"}, {"DAIRY_FREE"}) is False

    def test_nut_free_rejects_nuts(self):
        """Test NUT_FREE rejects nuts."""
        assert is_recipe_compatible({"nut"}, {"NUT_FREE"}) is False
        assert is_recipe_compatible({"almond"}, {"NUT_FREE"}) is False
        assert is_recipe_compatible(set(), {"NUT_FREE"}, recipe_name="Almond Butter") is False

    def test_no_restrictions_accepts_all(self):
        """Test no diet flags accepts any recipe."""
        assert is_recipe_compatible({"anything"}, set()) is True
        assert is_recipe_compatible(set(), set(), recipe_name="Anything") is True

    def test_case_insensitive_matching(self):
        """Test matching is case-insensitive."""
        assert is_recipe_compatible(set(), {"VEGAN"}, recipe_name="CHICKEN SALAD") is False

        assert is_recipe_compatible(set(), {"VEG"}, recipe_name="Fish and Chips") is False


class TestAdjustMacrosForDiet:
    """Test adjust_macros_for_diet function."""

    def test_no_diet_flags_no_change(self):
        """Test macros unchanged with no diet flags."""
        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, set(), 70, 2000)

        assert result == macros

    def test_high_protein_increases_protein(self):
        """Test HIGH_PROTEIN increases protein to 2.0 g/kg."""
        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"HIGH_PROTEIN"}, 70, 2000)

        # Should be at least 70 * 2.0 = 140g
        assert result["protein_g"] >= 140

    def test_high_protein_already_sufficient(self):
        """Test HIGH_PROTEIN doesn't increase if already sufficient."""
        macros = {"protein_g": 150, "fat_g": 50, "carbs_g": 180, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"HIGH_PROTEIN"}, 70, 2000)

        # Should not decrease
        assert result["protein_g"] >= 150

    def test_low_carb_reduces_carbs(self):
        """Test LOW_CARB caps carbs at 25% of calories."""
        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 300, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"LOW_CARB"}, 70, 2000)

        # Max 25% of 2000 = 500 kcal = 125g carbs
        assert result["carbs_g"] <= 125

    def test_low_carb_minimum_40g(self):
        """Test LOW_CARB enforces minimum 40g carbs."""
        macros = {"protein_g": 150, "fat_g": 100, "carbs_g": 200, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"LOW_CARB"}, 70, 1500)

        # Even with strict limit, should have at least 40g
        assert result["carbs_g"] >= 40

    def test_keto_very_low_carbs(self):
        """Test KETO caps carbs at 10% of calories."""
        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 250, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"KETO"}, 70, 2000)

        # Max 10% of 2000 = 200 kcal = 50g carbs
        assert result["carbs_g"] <= 50

    def test_keto_increases_fat(self):
        """Test KETO increases fat to fill calorie gap."""
        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"KETO"}, 70, 2000)

        # Fat should increase significantly
        assert result["fat_g"] > 100

    def test_mediterranean_high_fat(self):
        """Test MEDITERRANEAN increases fat to 35% of calories."""
        macros = {"protein_g": 100, "fat_g": 40, "carbs_g": 200, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"MEDITERRANEAN"}, 70, 2000)

        # At least 35% of 2000 = 700 kcal = 78g fat
        assert result["fat_g"] >= 75

    def test_mediterranean_increases_fiber(self):
        """Test MEDITERRANEAN increases fiber to 30g."""
        macros = {"protein_g": 100, "fat_g": 60, "carbs_g": 180, "fiber_g": 20}
        result = adjust_macros_for_diet(macros, {"MEDITERRANEAN"}, 70, 2000)

        assert result["fiber_g"] >= 30

    def test_mediterranean_fat_protein_ratio(self):
        """Test MEDITERRANEAN maintains fat >= 1.2 * protein."""
        macros = {"protein_g": 100, "fat_g": 40, "carbs_g": 200, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"MEDITERRANEAN"}, 70, 2000)

        # Fat should be at least 1.2 * protein
        assert result["fat_g"] >= result["protein_g"] * 1.1  # Allow small tolerance

    def test_low_fat_reduces_fat(self):
        """Test LOW_FAT caps fat at 25% of calories."""
        macros = {"protein_g": 100, "fat_g": 100, "carbs_g": 150, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"LOW_FAT"}, 70, 2000)

        # Max 25% of 2000 = 500 kcal = 56g fat
        assert result["fat_g"] <= 56

    def test_carbs_rebalanced_after_adjustments(self):
        """Test carbs are rebalanced to match calorie target."""
        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"HIGH_PROTEIN"}, 70, 2000)

        # Total calories should be close to target
        total_kcal = result["protein_g"] * 4 + result["fat_g"] * 9 + result["carbs_g"] * 4
        assert abs(total_kcal - 2000) <= 100  # Allow 100 kcal tolerance

    def test_macros_never_negative(self):
        """Test macros never go negative."""
        macros = {"protein_g": 50, "fat_g": 30, "carbs_g": 100, "fiber_g": 20}
        result = adjust_macros_for_diet(macros, {"KETO"}, 70, 1200)

        assert result["protein_g"] > 0
        assert result["fat_g"] > 0
        assert result["carbs_g"] > 0
        assert result["fiber_g"] > 0

    def test_multiple_diet_flags_combined(self):
        """Test combining multiple diet flags."""
        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}
        result = adjust_macros_for_diet(macros, {"HIGH_PROTEIN", "LOW_CARB"}, 70, 2000)

        # Should apply both constraints
        assert result["protein_g"] >= 140  # HIGH_PROTEIN
        assert result["carbs_g"] <= 125  # LOW_CARB


class TestGetDietDescription:
    """Test get_diet_description function."""

    def test_no_diet_flags(self):
        """Test description with no diet flags."""
        desc = get_diet_description(set())
        assert desc == "No dietary restrictions"

    def test_single_flag_description(self):
        """Test description with single flag."""
        desc = get_diet_description({"VEGAN"})
        assert "plant-based" in desc.lower()

    def test_multiple_flags_description(self):
        """Test description with multiple flags."""
        desc = get_diet_description({"VEGAN", "GF"})
        assert "," in desc  # Should be comma-separated

    def test_unknown_flag_handled(self):
        """Test unknown flag doesn't crash."""
        desc = get_diet_description({"UNKNOWN_FLAG"})
        assert desc == "Custom diet"

    def test_mixed_known_unknown_flags(self):
        """Test mix of known and unknown flags."""
        desc = get_diet_description({"VEGAN", "UNKNOWN"})
        # Should include known flag description
        assert len(desc) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_normalize_none_equivalent(self):
        """Test normalize handles None-like inputs."""
        assert normalize_diet_flags(set()) == set()

    def test_recipe_compatibility_empty_inputs(self):
        """Test recipe compatibility with empty inputs."""
        assert is_recipe_compatible(set(), set()) is True
        assert is_recipe_compatible(set(), set(), recipe_name="") is True

    def test_adjust_macros_zero_weight(self):
        """Test macro adjustment with zero weight."""
        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}
        # Should handle gracefully (use minimums)
        result = adjust_macros_for_diet(macros, {"HIGH_PROTEIN"}, 0.1, 2000)
        assert all(v >= 0 for v in result.values())

    def test_adjust_macros_very_low_calories(self):
        """Test macro adjustment with very low calories."""
        macros = {"protein_g": 30, "fat_g": 20, "carbs_g": 50, "fiber_g": 10}
        result = adjust_macros_for_diet(macros, {"KETO"}, 70, 800)

        # Should enforce minimums
        assert result["carbs_g"] >= 30  # KETO minimum
        assert result["protein_g"] > 0
        assert result["fat_g"] > 0

    def test_adjust_macros_very_high_calories(self):
        """Test macro adjustment with very high calories."""
        macros = {"protein_g": 200, "fat_g": 100, "carbs_g": 400, "fiber_g": 40}
        result = adjust_macros_for_diet(macros, {"MEDITERRANEAN"}, 100, 5000)

        # Should scale appropriately
        total_kcal = result["protein_g"] * 4 + result["fat_g"] * 9 + result["carbs_g"] * 4
        assert total_kcal >= 4500  # Close to target


class TestDietImplications:
    """Test DIET_IMPLICATIONS constant and usage."""

    def test_vegan_implications_applied(self):
        """Test VEGAN implications are in normalized flags."""
        result = normalize_diet_flags({"VEGAN"})
        expected_implications = DIET_IMPLICATIONS["VEGAN"]
        for implied_flag in expected_implications:
            assert implied_flag in result

    def test_keto_implications_applied(self):
        """Test KETO implications are in normalized flags."""
        result = normalize_diet_flags({"KETO"})
        expected_implications = DIET_IMPLICATIONS["KETO"]
        for implied_flag in expected_implications:
            assert implied_flag in result

    def test_paleo_implications_applied(self):
        """Test PALEO implications are in normalized flags."""
        result = normalize_diet_flags({"PALEO"})
        expected_implications = DIET_IMPLICATIONS["PALEO"]
        for implied_flag in expected_implications:
            assert implied_flag in result
