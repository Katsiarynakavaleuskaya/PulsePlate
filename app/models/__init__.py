"""Shared models for the application."""

from __future__ import annotations

from typing import Any

from app.models.events import JSONEncodedDict, NutritionEvent
from app.models.llm_quota_usage import VipLlmMonthlyUsage
from app.models.paywall_analytics import PaywallExposureLedger
from app.models.plans import DayPlan, WeeklyPlan
from app.models.rag_feedback import RAGFeedback, UserKnowledge
from app.models.subscriptions import Subscription, SubscriptionActivationAudit


def __getattr__(name: str) -> Any:
    """Keep the new outcome ORM owner lazy on OpenAPI import paths."""

    if name == "FitChefSupportOutcomeEvent":
        from app.models.fitchef_support_outcomes import FitChefSupportOutcomeEvent

        return FitChefSupportOutcomeEvent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DayPlan",
    "FitChefSupportOutcomeEvent",
    "JSONEncodedDict",
    "NutritionEvent",
    "PaywallExposureLedger",
    "RAGFeedback",
    "Subscription",
    "SubscriptionActivationAudit",
    "UserKnowledge",
    "VipLlmMonthlyUsage",
    "WeeklyPlan",
]
