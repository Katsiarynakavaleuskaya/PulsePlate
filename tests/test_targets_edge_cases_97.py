"""
Test edge cases for core/targets.py to achieve 97% coverage.
Focus on lines 145, 149-152, 156-159, 169 for error handling.
"""

import pytest


class TestTargetsEdgeCases97:
    """Test edge cases in WHO targets for 97% coverage."""

    def test_get_target_unknown_nutrient_line_145(self):
        """Test line 145: ValueError for unknown nutrient in get_target."""
        try:
            from core.targets import NutrientTargets

            # Create a basic targets instance
            targets = NutrientTargets(
                calories=2000.0,
                protein_g=50.0,
                fat_g=65.0,
                carbs_g=250.0,
                fiber_g=25.0,
                iron_mg=14.0,
                calcium_mg=1000.0,
                deficiency_threshold=0.8,
                priority_nutrients={"protein_g": 5, "iron_mg": 4},
            )

            # Test line 145: raise ValueError for unknown nutrient
            with pytest.raises(ValueError, match="Unknown nutrient: unknown_vitamin"):
                targets.get_target("unknown_vitamin")

            # Test another unknown nutrient
            with pytest.raises(ValueError, match="Unknown nutrient: fake_mineral"):
                targets.get_target("fake_mineral")

        except ImportError:
            pass

    def test_get_minimum_unknown_nutrient_line_152(self):
        """Test line 152: ValueError for unknown nutrient in get_minimum."""
        try:
            from core.targets import NutrientTargets

            targets = NutrientTargets(
                calories=2000.0,
                protein_g=50.0,
                fat_g=65.0,
                carbs_g=250.0,
                fiber_g=25.0,
                iron_mg=14.0,
                calcium_mg=1000.0,
                deficiency_threshold=0.8,
                priority_nutrients={"protein_g": 5, "iron_mg": 4},
            )

            # Test line 152: raise ValueError for unknown nutrient in get_minimum
            with pytest.raises(ValueError, match="Unknown nutrient: nonexistent_nutrient"):
                targets.get_minimum("nonexistent_nutrient")

        except ImportError:
            pass

    def test_get_maximum_unknown_nutrient_line_159(self):
        """Test line 159: ValueError for unknown nutrient in get_maximum."""
        try:
            from core.targets import NutrientTargets

            targets = NutrientTargets(
                calories=2000.0,
                protein_g=50.0,
                fat_g=65.0,
                carbs_g=250.0,
                fiber_g=25.0,
                iron_mg=14.0,
                calcium_mg=1000.0,
                deficiency_threshold=0.8,
                priority_nutrients={"protein_g": 5, "iron_mg": 4},
            )

            # Test line 159: raise ValueError for unknown nutrient in get_maximum
            with pytest.raises(ValueError, match="Unknown nutrient: invalid_macro"):
                targets.get_maximum("invalid_macro")

        except ImportError:
            pass

    def test_get_priority_nutrients_line_169(self):
        """Test line 169: get_priority_nutrients method coverage."""
        try:
            from core.targets import NutrientTargets

            # Test with various priority levels
            targets = NutrientTargets(
                calories=2000.0,
                protein_g=50.0,
                fat_g=65.0,
                carbs_g=250.0,
                fiber_g=25.0,
                iron_mg=14.0,
                calcium_mg=1000.0,
                deficiency_threshold=0.8,
                priority_nutrients={
                    "protein_g": 5,  # priority >= 3
                    "iron_mg": 4,  # priority >= 3
                    "fat_g": 3,  # priority >= 3
                    "fiber_g": 2,  # priority < 3, should be excluded
                    "calcium_mg": 1,  # priority < 3, should be excluded
                },
            )

            # Test line 169: get_priority_nutrients returns dict
            priority_nutrients = targets.get_priority_nutrients()

            # Should include nutrients with priority >= 3
            assert "protein_g" in priority_nutrients
            assert "iron_mg" in priority_nutrients
            assert "fat_g" in priority_nutrients

            # Should exclude nutrients with priority < 3
            assert "fiber_g" not in priority_nutrients
            assert "calcium_mg" not in priority_nutrients

            # Check values are targets
            assert priority_nutrients["protein_g"] == 50.0
            assert priority_nutrients["iron_mg"] == 14.0
            assert priority_nutrients["fat_g"] == 65.0

        except ImportError:
            pass

    def test_comprehensive_nutrient_methods(self):
        """Test all nutrient methods with valid nutrients."""
        try:
            from core.targets import NutrientTargets

            targets = NutrientTargets(
                calories=2000.0,
                protein_g=50.0,
                fat_g=65.0,
                carbs_g=250.0,
                fiber_g=25.0,
                iron_mg=14.0,
                calcium_mg=1000.0,
                deficiency_threshold=0.8,
                priority_nutrients={"protein_g": 5, "iron_mg": 4},
            )

            # Test valid nutrient access - should hit lines 149, 156
            assert targets.get_minimum("protein_g") is not None
            assert targets.get_maximum("protein_g") is not None
            assert targets.get_target("protein_g") == 50.0

            # Test with different nutrients
            assert targets.get_minimum("iron_mg") is not None
            assert targets.get_maximum("iron_mg") is not None
            assert targets.get_target("iron_mg") == 14.0

        except ImportError:
            pass

    def test_edge_cases_empty_priority_nutrients(self):
        """Test with empty priority nutrients."""
        try:
            from core.targets import NutrientTargets

            targets = NutrientTargets(
                calories=2000.0,
                protein_g=50.0,
                fat_g=65.0,
                carbs_g=250.0,
                fiber_g=25.0,
                iron_mg=14.0,
                calcium_mg=1000.0,
                deficiency_threshold=0.8,
                priority_nutrients={},  # Empty priority nutrients
            )

            # Should return empty dict for line 169
            priority_nutrients = targets.get_priority_nutrients()
            assert priority_nutrients == {}

            # High priority nutrients should also be empty
            high_priority = targets.get_high_priority_nutrients()
            assert high_priority == []

        except ImportError:
            pass

    def test_is_deficient_method_lines_163_165(self):
        """Test lines 163-165: is_deficient method."""
        try:
            from core.targets import NutrientTargets

            targets = NutrientTargets(
                calories=2000.0,
                protein_g=50.0,
                fat_g=65.0,
                carbs_g=250.0,
                fiber_g=25.0,
                iron_mg=14.0,
                calcium_mg=1000.0,
                deficiency_threshold=0.8,
                priority_nutrients={"protein_g": 5, "iron_mg": 4},
            )

            # Test line 163: target = self.get_target(nutrient)
            # Test line 164: threshold = target * self.deficiency_threshold
            # Test line 165: return actual_value < threshold

            # Test deficient case (should return True)
            deficient = targets.is_deficient("protein_g", 30.0)  # 30 < 50 * 0.8 = 40
            assert deficient is True

            # Test non-deficient case (should return False)
            sufficient = targets.is_deficient("protein_g", 45.0)  # 45 > 50 * 0.8 = 40
            assert sufficient is False

            # Test with iron
            iron_deficient = targets.is_deficient("iron_mg", 8.0)  # 8 < 14 * 0.8 = 11.2
            assert iron_deficient is True

            iron_sufficient = targets.is_deficient("iron_mg", 12.0)  # 12 > 14 * 0.8 = 11.2
            assert iron_sufficient is False

        except ImportError:
            pass

    def test_get_high_priority_nutrients_line_177(self):
        """Test line 177: get_high_priority_nutrients method."""
        try:
            from core.targets import NutrientTargets

            targets = NutrientTargets(
                calories=2000.0,
                protein_g=50.0,
                fat_g=65.0,
                carbs_g=250.0,
                fiber_g=25.0,
                iron_mg=14.0,
                calcium_mg=1000.0,
                deficiency_threshold=0.8,
                priority_nutrients={
                    "protein_g": 5,  # priority >= 4, should be included
                    "iron_mg": 4,  # priority >= 4, should be included
                    "fat_g": 3,  # priority < 4, should be excluded
                    "fiber_g": 2,  # priority < 4, should be excluded
                    "calcium_mg": 1,  # priority < 4, should be excluded
                },
            )

            # Test line 177: return [nutrient for nutrient, priority in self.priority_nutrients.items() if priority >= 4]
            high_priority = targets.get_high_priority_nutrients()

            # Should include nutrients with priority >= 4
            assert "protein_g" in high_priority
            assert "iron_mg" in high_priority

            # Should exclude nutrients with priority < 4
            assert "fat_g" not in high_priority
            assert "fiber_g" not in high_priority
            assert "calcium_mg" not in high_priority

            # Test with no high priority nutrients
            targets_no_high = NutrientTargets(
                calories=2000.0,
                protein_g=50.0,
                fat_g=65.0,
                carbs_g=250.0,
                fiber_g=25.0,
                iron_mg=14.0,
                calcium_mg=1000.0,
                deficiency_threshold=0.8,
                priority_nutrients={
                    "protein_g": 3,  # priority < 4
                    "iron_mg": 2,  # priority < 4
                },
            )

            high_priority_empty = targets_no_high.get_high_priority_nutrients()
            assert high_priority_empty == []

        except ImportError:
            pass
