"""
Base Classes for Bayesian Methods

RU: Базовые классы и интерфейсы для байесовских методов.
EN: Core classes and interfaces for Bayesian inference.

This module defines fundamental abstractions used throughout the Bayesian subsystem:
- Prior distributions (population-level knowledge)
- Likelihood functions (user-specific evidence)
- Posterior distributions (personalized beliefs)
- Bayesian predictions with uncertainty quantification
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar

import numpy as np
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """
    RU: Уровни уверенности в предсказаниях.
    EN: Confidence levels for predictions.
    """

    LOW = "low"  # < 0.7
    MEDIUM = "medium"  # 0.7 - 0.85
    HIGH = "high"  # 0.85 - 0.95
    VERY_HIGH = "very_high"  # > 0.95


class ValidationStatus(str, Enum):
    """
    RU: Статусы валидации данных.
    EN: Data validation status codes.
    """

    VALID = "valid"  # Data appears normal
    WARNING = "warning"  # Data unusual but plausible
    ANOMALY = "anomaly"  # Data highly unlikely
    ERROR = "error"  # Data impossible/dangerous


@dataclass(frozen=True)
class BayesianPrediction:
    """
    RU: Байесовское предсказание с неопределённостью.
    EN: Bayesian prediction with uncertainty quantification.

    Encapsulates a probabilistic prediction including:
    - Point estimate (mean/mode)
    - Uncertainty bounds (credible intervals)
    - Confidence level
    - Human-readable explanation
    """

    value: float  # Point estimate (mean, median, or mode)
    confidence: float  # Probability that prediction is correct (0-1)
    confidence_level: ConfidenceLevel
    lower_bound: Optional[float] = None  # 95% credible interval lower
    upper_bound: Optional[float] = None  # 95% credible interval upper
    explanation: Optional[str] = None  # Human-readable rationale
    metadata: Dict[str, Any] = None  # Additional context

    def __post_init__(self):
        """Validate prediction consistency."""
        if not (0 <= self.confidence <= 1):
            raise ValueError("Confidence must be between 0 and 1")
        if self.lower_bound is not None and self.upper_bound is not None:
            if self.lower_bound > self.upper_bound:
                raise ValueError("Lower bound must be <= upper bound")

    @classmethod
    def from_confidence(cls, value: float, confidence: float, **kwargs) -> BayesianPrediction:
        """
        RU: Создать предсказание автоматически определив уровень уверенности.
        EN: Create prediction with auto-determined confidence level.
        """
        if confidence < 0.7:
            level = ConfidenceLevel.LOW
        elif confidence < 0.85:
            level = ConfidenceLevel.MEDIUM
        elif confidence < 0.95:
            level = ConfidenceLevel.HIGH
        else:
            level = ConfidenceLevel.VERY_HIGH

        return cls(value=value, confidence=confidence, confidence_level=level, **kwargs)


@dataclass(frozen=True)
class ValidationResult:
    """
    RU: Результат валидации данных с байесовским скорингом.
    EN: Data validation result with Bayesian anomaly scoring.

    Provides:
    - Status code (valid/warning/anomaly/error)
    - Anomaly probability (0-1)
    - Suggested correction (if applicable)
    - Human-readable message
    """

    status: ValidationStatus
    anomaly_probability: float  # P(data is anomalous | evidence)
    confidence: float  # Confidence in the validation result
    message: str
    suggested_value: Optional[float] = None  # Recommended correction
    explanation: Optional[str] = None  # Why this is anomalous
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate result consistency."""
        if not (0 <= self.anomaly_probability <= 1):
            raise ValueError("Anomaly probability must be between 0 and 1")
        if not (0 <= self.confidence <= 1):
            raise ValueError("Confidence must be between 0 and 1")


T = TypeVar("T")


class Prior(ABC, Generic[T]):
    """
    RU: Абстрактный базовый класс для априорных распределений.
    EN: Abstract base class for prior distributions.

    A prior represents population-level knowledge before observing user-specific data.
    Examples:
    - Normal prior for calorie intake (μ=2000, σ=500)
    - Beta prior for conversion rates (α=1, β=1 for uniform)
    """

    @abstractmethod
    def sample(self, n: int = 1) -> np.ndarray:
        """
        RU: Сэмплировать из априорного распределения.
        EN: Draw random samples from the prior distribution.
        """
        pass

    @abstractmethod
    def pdf(self, x: T) -> float:
        """
        RU: Плотность вероятности в точке x.
        EN: Probability density function at x.
        """
        pass

    @abstractmethod
    def mean(self) -> float:
        """
        RU: Математическое ожидание распределения.
        EN: Expected value of the distribution.
        """
        pass

    @abstractmethod
    def std(self) -> float:
        """
        RU: Стандартное отклонение распределения.
        EN: Standard deviation of the distribution.
        """
        pass


class Likelihood(ABC):
    """
    RU: Абстрактный базовый класс для функций правдоподобия.
    EN: Abstract base class for likelihood functions.

    A likelihood quantifies how probable the observed data is,
    given a specific hypothesis/parameter value.
    """

    @abstractmethod
    def compute(self, data: Any, parameter: Any) -> float:
        """
        RU: Вычислить правдоподобие данных при заданном параметре.
        EN: Compute P(data | parameter).
        """
        pass


class Posterior(ABC, Generic[T]):
    """
    RU: Абстрактный базовый класс для апостериорных распределений.
    EN: Abstract base class for posterior distributions.

    A posterior combines prior knowledge with observed data via Bayes' theorem:
    P(parameter | data) ∝ P(data | parameter) * P(parameter)
    """

    @abstractmethod
    def sample(self, n: int = 1) -> np.ndarray:
        """
        RU: Сэмплировать из апостериорного распределения.
        EN: Draw samples from the posterior.
        """
        pass

    @abstractmethod
    def mean(self) -> float:
        """
        RU: Апостериорное математическое ожидание.
        EN: Posterior expected value.
        """
        pass

    @abstractmethod
    def credible_interval(self, alpha: float = 0.05) -> tuple[float, float]:
        """
        RU: Вычислить байесовский доверительный интервал.
        EN: Compute Bayesian credible interval.

        Args:
            alpha: Significance level (default 0.05 for 95% CI)

        Returns:
            (lower_bound, upper_bound) such that P(lower < θ < upper | data) = 1-alpha
        """
        pass


class BayesianModel(ABC):
    """
    RU: Абстрактный базовый класс для байесовских моделей.
    EN: Abstract base class for Bayesian models.

    A Bayesian model encapsulates:
    - Prior distribution
    - Likelihood function
    - Posterior inference
    - Prediction generation
    """

    @abstractmethod
    def update(self, data: Any) -> None:
        """
        RU: Обновить модель новыми данными (Bayesian update).
        EN: Update model with new evidence (Bayesian update).
        """
        pass

    @abstractmethod
    def predict(self, context: Optional[Dict[str, Any]] = None) -> BayesianPrediction:
        """
        RU: Генерировать предсказание с неопределённостью.
        EN: Generate prediction with uncertainty quantification.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        RU: Сбросить модель к априорному состоянию.
        EN: Reset model to prior state.
        """
        pass


# Pydantic schemas for API contracts


class BayesianPredictionSchema(BaseModel):
    """Pydantic schema for API responses with Bayesian predictions."""

    value: float = Field(..., description="Point estimate (mean/median/mode)")
    confidence: float = Field(..., ge=0, le=1, description="Prediction confidence (0-1)")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence category")
    lower_bound: Optional[float] = Field(None, description="95% CI lower bound")
    upper_bound: Optional[float] = Field(None, description="95% CI upper bound")
    explanation: Optional[str] = Field(None, description="Human-readable explanation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ValidationResultSchema(BaseModel):
    """Pydantic schema for validation results."""

    status: ValidationStatus = Field(..., description="Validation status code")
    anomaly_probability: float = Field(
        ..., ge=0, le=1, description="P(anomalous | evidence)"
    )
    confidence: float = Field(..., ge=0, le=1, description="Validation confidence")
    message: str = Field(..., description="Human-readable message")
    suggested_value: Optional[float] = Field(None, description="Suggested correction")
    explanation: Optional[str] = Field(None, description="Anomaly explanation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context")


__all__ = [
    # Enums
    "ConfidenceLevel",
    "ValidationStatus",
    # Data classes
    "BayesianPrediction",
    "ValidationResult",
    # Abstract base classes
    "Prior",
    "Likelihood",
    "Posterior",
    "BayesianModel",
    # Pydantic schemas
    "BayesianPredictionSchema",
    "ValidationResultSchema",
]
