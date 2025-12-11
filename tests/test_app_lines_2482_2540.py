"""
Targeted tests for app.py lines 2482-2540 to reach 97% coverage.

Covers:
- WHOTargetsRequest model validator (_normalize_values)
- _macros_to_kcal function error paths
- calculate_heuristic_macros edge cases
"""

import pytest

import app


class TestAppLines2482_2540:
    """Tests for app.py lines 2482-2540."""

    def test_who_targets_request_normalize_goal_synonyms(self) -> None:
        """WHOTargetsRequest normalizes goal synonyms (lose -> loss, etc)."""
        # Test "lose" -> "loss"
        req = app.WHOTargetsRequest(
            sex="male",
            age=30,
            height_cm=180,
            weight_kg=75,
            activity="moderate",
            goal="lose",
        )
        assert req.goal == "loss"

        # Test "weight_loss" -> "loss"
        req = app.WHOTargetsRequest(
            sex="female",
            age=25,
            height_cm=165,
            weight_kg=60,
            activity="light",
            goal="weight_loss",
        )
        assert req.goal == "loss"

        # Test "maintenance" -> "maintain"
        req = app.WHOTargetsRequest(
            sex="male",
            age=35,
            height_cm=175,
            weight_kg=80,
            activity="active",
            goal="maintenance",
        )
        assert req.goal == "maintain"

        # Test "weight_gain" -> "gain"
        req = app.WHOTargetsRequest(
            sex="female",
            age=28,
            height_cm=170,
            weight_kg=55,
            activity="moderate",
            goal="weight_gain",
        )
        assert req.goal == "gain"

    def test_who_targets_request_normalize_preserves_valid_goal(self) -> None:
        """WHOTargetsRequest preserves already-valid goal values."""

        req = app.WHOTargetsRequest(
            sex="male",
            age=30,
            height_cm=180,
            weight_kg=75,
            activity="moderate",
            goal="maintain",
        )
        assert req.goal == "maintain"

    def test_macros_to_kcal_invalid_types(self) -> None:
        """_macros_to_kcal returns None for invalid macro types."""

        # Non-numeric values
        result = app._macros_to_kcal({"protein_g": "invalid", "fat_g": 10, "carbs_g": 50})
        assert result is None

        # None values
        result = app._macros_to_kcal({"protein_g": None, "fat_g": 10, "carbs_g": 50})
        assert result is None

    def test_macros_to_kcal_valid_conversion(self) -> None:
        """_macros_to_kcal correctly converts macros to kcal."""

        macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200}
        # 100*4 + 50*9 + 200*4 = 400 + 450 + 800 = 1650
        result = app._macros_to_kcal(macros)
        assert result == 1650

    def test_calculate_heuristic_macros_1200_floor(self) -> None:
        """calculate_heuristic_macros enforces 1200 kcal minimum."""

        # Request 800 kcal, should be clamped to 1200
        prot, fat, carbs = app.calculate_heuristic_macros(800, 70.0)
        total = app._macros_to_kcal({"protein_g": prot, "fat_g": fat, "carbs_g": carbs})
        assert total is not None
        # Should be close to 1200 (within rounding tolerance)
        assert 1199 <= total <= 1201

    def test_calculate_heuristic_macros_scaling_edge_case(self) -> None:
        """calculate_heuristic_macros scales protein/fat when they exceed kcal budget."""

        # Very low kcal with high weight should trigger scaling
        prot, fat, carbs = app.calculate_heuristic_macros(1200, 200.0)

        # Verify we get valid non-negative values
        assert prot >= 0
        assert fat >= 0
        assert carbs >= 1  # Minimum 1g carbs

        # Verify total is reasonable
        total = app._macros_to_kcal({"protein_g": prot, "fat_g": fat, "carbs_g": carbs})
        assert total is not None
        assert 1190 <= total <= 1210

    def test_calculate_heuristic_macros_normal_case(self) -> None:
        """calculate_heuristic_macros works correctly for normal inputs."""

        prot, fat, carbs = app.calculate_heuristic_macros(2000, 70.0)

        # Verify reasonable macro distribution
        assert prot > 0
        assert fat > 0
        assert carbs > 0

        # Verify total kcal matches target
        total = app._macros_to_kcal({"protein_g": prot, "fat_g": fat, "carbs_g": carbs})
        assert total is not None
        assert 1990 <= total <= 2010  # Allow small rounding difference
