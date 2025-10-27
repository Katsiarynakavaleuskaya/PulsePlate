"""
Tests for update_manager exception handling

RU: Тесты для обработки исключений в update_manager
EN: Tests for exception handling in update_manager
"""

import pytest
from unittest.mock import Mock, patch

from core.food_apis.update_manager import DatabaseUpdateManager


class TestUpdateManagerExceptionHandling:
    """Test exception handling in UpdateManager."""

    def test_food_to_dict_with_exception(self) -> None:
        """Test _food_to_dict handles serialization exceptions."""
        manager = DatabaseUpdateManager()

        # Create a mock food object that will raise an exception
        mock_food = Mock()
        mock_food.name = "Test Food"
        # Set fallback attributes to proper types
        mock_food.nutrients_per_100g = {}
        mock_food.cost_per_100g = 0.0
        mock_food.tags = []
        mock_food.availability_regions = []
        mock_food.source = "unknown"
        mock_food.source_id = "unknown"

        # Mock the methods to raise exceptions
        mock_food.to_dict.side_effect = Exception("Serialization failed")
        mock_food.model_dump.side_effect = Exception("Model dump failed")

        # This should not crash and should return fallback data
        result = manager._food_to_dict(mock_food)

        # Should return fallback dict with name
        assert isinstance(result, dict)
        assert result["name"] == "Test Food"
        # Verify all fallback keys are present
        assert "nutrients_per_100g" in result
        assert "cost_per_100g" in result
        assert "tags" in result
        assert "availability_regions" in result
        assert "source" in result
        assert "source_id" in result
        # Verify fallback types
        assert isinstance(result["nutrients_per_100g"], dict)
        assert isinstance(result["tags"], list)
        assert isinstance(result["availability_regions"], list)
        assert isinstance(result["cost_per_100g"], (int, float))
        assert isinstance(result["source"], str)
        assert isinstance(result["source_id"], str)

    def test_food_to_dict_with_partial_failure(self) -> None:
        """Test _food_to_dict handles partial serialization failure."""
        manager = DatabaseUpdateManager()

        # Create a mock food object
        mock_food = Mock()
        mock_food.name = "Test Food"

        # Mock to_dict to fail but model_dump to succeed
        mock_food.to_dict.side_effect = Exception("to_dict failed")
        mock_food.model_dump.return_value = {"name": "Test Food", "calories": 100}

        # This should use model_dump successfully
        result = manager._food_to_dict(mock_food)

        # Should return the model_dump result
        assert isinstance(result, dict)
        assert result["name"] == "Test Food"
        assert result["calories"] == 100
