"""Declarative models for the core application domain."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    """RU: Пользователь приложения. EN: Application user entity."""

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MealEntry(Base):
    """
    RU: Запись о приёме пищи пользователя.
    EN: User meal entry for nutrition tracking.

    Stores normalized meal data for Bayesian analysis:
    - Anomaly detection (unusual calorie values)
    - Pattern analysis (eating habits)
    - Deficiency risk assessment
    """

    __tablename__ = "meal_entries"
    __table_args__ = (
        Index("ix_meal_entries_user_timestamp", "user_id", "timestamp"),
        Index("ix_meal_entries_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Meal identification
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(50), nullable=True)  # breakfast, lunch, etc.

    # Macronutrients
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Micronutrients (optional for basic entries)
    iron_mg: Mapped[float] = mapped_column(Float, nullable=True)
    calcium_mg: Mapped[float] = mapped_column(Float, nullable=True)
    vitamin_d_iu: Mapped[float] = mapped_column(Float, nullable=True)

    # Validation metadata
    was_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # valid, warning, anomaly
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecommendationFeedback(Base):
    """
    RU: Обратная связь по рекомендациям для Thompson Sampling.
    EN: User feedback on recommendations for adaptive learning.

    Stores user interactions with recommendations for:
    - Thompson Sampling multi-armed bandit
    - A/B testing of recommendation strategies
    - Personalization optimization
    """

    __tablename__ = "recommendation_feedback"
    __table_args__ = (
        Index("ix_recommendation_feedback_user_timestamp", "user_id", "timestamp"),
        Index("ix_recommendation_feedback_strategy", "strategy_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Recommendation details
    recommendation_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # UUID or identifier
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Examples: "high_protein", "balanced", "low_carb", "mediterranean"

    # Context (for contextual bandits in future)
    context: Mapped[str] = mapped_column(Text, nullable=True)  # JSON-serialized context

    # User response
    was_shown: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    was_clicked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    was_followed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Did user follow through?

    # Engagement metrics
    time_to_click_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    session_duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


__all__ = ["User", "MealEntry", "RecommendationFeedback"]
