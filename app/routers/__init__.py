"""Router exports for FastAPI application.

RU: Экспорт маршрутов приложения.
EN: Export FastAPI routers for app package imports.
"""

# Import all routers directly to avoid mypy duplicate module issues
from . import bmi_pro, foods, premium_week, recipes, users, vip


__all__ = [
    "bmi_pro",
    "foods",
    "premium_week",
    "recipes",
    "users",
    "vip",
]
