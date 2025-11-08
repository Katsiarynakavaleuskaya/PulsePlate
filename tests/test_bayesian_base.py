"""
Tests for Bayesian Base Classes and Infrastructure

RU: Тесты базовых классов байесовских методов.
EN: Tests for Bayesian methods base classes.

Tests:
- BayesianPrediction validation and creation
- ValidationResult validation
- ConfidenceLevel classification
- Data class consistency
"""

from __future__ import annotations

import pytest

from core.bayesian.base import (
    BayesianPrediction,
    ConfidenceLevel,
    ValidationResult,
    ValidationStatus,
)


class TestBayesianPrediction:
    """Tests for BayesianPrediction dataclass."""

    def test_create_valid_prediction(self):
        """RU: Создание валидного предсказания. EN: Create valid prediction."""
        pred = BayesianPrediction(
            value=72.5,
            confidence=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            lower_bound=70.0,
            upper_bound=75.0,
            explanation="Expected weight based on current trend",
        )

        assert pred.value == 72.5
        assert pred.confidence == 0.85
        assert pred.confidence_level == ConfidenceLevel.HIGH
        assert pred.lower_bound == 70.0
        assert pred.upper_bound == 75.0

    def test_prediction_from_confidence_low(self):
        """RU: Автоопределение LOW уверенности. EN: Auto-classify LOW confidence."""
        pred = BayesianPrediction.from_confidence(value=100.0, confidence=0.65)
        assert pred.confidence_level == ConfidenceLevel.LOW

    def test_prediction_from_confidence_medium(self):
        """RU: Автоопределение MEDIUM уверенности. EN: Auto-classify MEDIUM confidence."""
        pred = BayesianPrediction.from_confidence(value=100.0, confidence=0.75)
        assert pred.confidence_level == ConfidenceLevel.MEDIUM

    def test_prediction_from_confidence_high(self):
        """RU: Автоопределение HIGH уверенности. EN: Auto-classify HIGH confidence."""
        pred = BayesianPrediction.from_confidence(value=100.0, confidence=0.90)
        assert pred.confidence_level == ConfidenceLevel.HIGH

    def test_prediction_from_confidence_very_high(self):
        """RU: Автоопределение VERY_HIGH уверенности. EN: Auto-classify VERY_HIGH confidence."""
        pred = BayesianPrediction.from_confidence(value=100.0, confidence=0.99)
        assert pred.confidence_level == ConfidenceLevel.VERY_HIGH

    def test_prediction_invalid_confidence(self):
        """RU: Отклонение невалидной уверенности. EN: Reject invalid confidence."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            BayesianPrediction(
                value=100.0,
                confidence=1.5,  # Invalid!
                confidence_level=ConfidenceLevel.HIGH,
            )

    def test_prediction_invalid_bounds(self):
        """RU: Отклонение некорректных границ. EN: Reject invalid bounds."""
        with pytest.raises(ValueError, match="Lower bound must be <= upper bound"):
            BayesianPrediction(
                value=100.0,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                lower_bound=150.0,  # Lower > upper!
                upper_bound=50.0,
            )


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_valid_result(self):
        """RU: Создание валидного результата. EN: Create valid validation result."""
        result = ValidationResult(
            status=ValidationStatus.WARNING,
            anomaly_probability=0.75,
            confidence=0.85,
            message="Unusually high calorie value",
            suggested_value=2000.0,
            explanation="Apple typically has 52 kcal per 100g",
        )

        assert result.status == ValidationStatus.WARNING
        assert result.anomaly_probability == 0.75
        assert result.confidence == 0.85
        assert result.suggested_value == 2000.0

    def test_validation_result_invalid_anomaly_probability(self):
        """RU: Отклонение невалидной вероятности. EN: Reject invalid anomaly probability."""
        with pytest.raises(ValueError, match="Anomaly probability must be between 0 and 1"):
            ValidationResult(
                status=ValidationStatus.ANOMALY,
                anomaly_probability=1.5,  # Invalid!
                confidence=0.9,
                message="Test",
            )

    def test_validation_result_invalid_confidence(self):
        """RU: Отклонение невалидной уверенности. EN: Reject invalid confidence."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            ValidationResult(
                status=ValidationStatus.VALID,
                anomaly_probability=0.1,
                confidence=-0.5,  # Invalid!
                message="Test",
            )


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_confidence_levels_exist(self):
        """RU: Все уровни определены. EN: All confidence levels are defined."""
        assert ConfidenceLevel.LOW == "low"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.VERY_HIGH == "very_high"


class TestValidationStatus:
    """Tests for ValidationStatus enum."""

    def test_validation_statuses_exist(self):
        """RU: Все статусы определены. EN: All validation statuses are defined."""
        assert ValidationStatus.VALID == "valid"
        assert ValidationStatus.WARNING == "warning"
        assert ValidationStatus.ANOMALY == "anomaly"
        assert ValidationStatus.ERROR == "error"
