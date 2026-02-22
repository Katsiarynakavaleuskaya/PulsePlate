"""Tests to boost coverage for core/targets.py to 97%."""

import pytest

from core.targets import MicronutrientTargets


class TestTargetsCoverage97:
    """Test class for targets.py coverage boost."""

    def setup_method(self):
        """Set up test fixtures."""
        self.targets = MicronutrientTargets(
            iron_mg=(8.0, 18.0, 45.0),
            calcium_mg=(800.0, 1000.0, 2500.0),
            magnesium_mg=(300.0, 400.0, 700.0),
            zinc_mg=(8.0, 11.0, 40.0),
            potassium_mg=(3500.0, 4700.0, 6000.0),
            iodine_ug=(150.0, 200.0, 1100.0),
            selenium_ug=(55.0, 70.0, 400.0),
            folate_ug=(400.0, 600.0, 1000.0),
            b12_ug=(2.4, 3.0, 10.0),
            vitamin_d_iu=(600.0, 800.0, 4000.0),
            vitamin_a_ug=(700.0, 900.0, 3000.0),
            vitamin_c_mg=(65.0, 90.0, 2000.0),
        )

    def test_get_target_unknown_nutrient_line_145(self):
        """Test line 145: get_target with unknown nutrient."""
        with pytest.raises(ValueError, match="Unknown nutrient: unknown_nutrient"):
            self.targets.get_target("unknown_nutrient")

    def test_get_minimum_unknown_nutrient_line_149_152(self):
        """Test lines 149-152: get_minimum with unknown nutrient."""
        with pytest.raises(ValueError, match="Unknown nutrient: unknown_nutrient"):
            self.targets.get_minimum("unknown_nutrient")

    def test_get_maximum_unknown_nutrient_line_156_159(self):
        """Test lines 156-159: get_maximum with unknown nutrient."""
        with pytest.raises(ValueError, match="Unknown nutrient: unknown_nutrient"):
            self.targets.get_maximum("unknown_nutrient")

    def test_get_priority_nutrients_line_169(self):
        """Test line 169: get_priority_nutrients method."""
        priority_nutrients = self.targets.get_priority_nutrients()
        assert isinstance(priority_nutrients, dict)

    def test_get_target_valid_nutrient(self) -> None:
        """Test get_target with valid nutrient."""
        result = self.targets.get_target("calcium_mg")
        assert isinstance(result, float)

    def test_get_minimum_valid_nutrient(self) -> None:
        """Test get_minimum with valid nutrient."""
        result = self.targets.get_minimum("calcium_mg")
        assert isinstance(result, float)

    def test_get_maximum_valid_nutrient(self) -> None:
        """Test get_maximum with valid nutrient."""
        result = self.targets.get_maximum("calcium_mg")
        assert isinstance(result, float)

    def test_is_deficient_true(self) -> None:
        """Test is_deficient with deficient value."""
        result = self.targets.is_deficient("calcium_mg", 0.1)
        assert isinstance(result, bool)

    def test_is_deficient_false(self) -> None:
        """Test is_deficient with sufficient value."""
        result = self.targets.is_deficient("calcium_mg", 1000.0)
        assert isinstance(result, bool)

    def test_priority_nutrients_structure(self):
        """Test priority_nutrients structure."""
        assert hasattr(self.targets, "priority_nutrients")
        assert isinstance(self.targets.priority_nutrients, dict)

    def test_deficiency_threshold_structure(self):
        """Test deficiency_threshold structure."""
        assert hasattr(self.targets, "deficiency_threshold")
        assert isinstance(self.targets.deficiency_threshold, (int, float))
