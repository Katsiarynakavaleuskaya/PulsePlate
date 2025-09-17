"""Router exports for FastAPI application.

RU: Экспорт маршрутов приложения.
EN: Export FastAPI routers for app package imports.
"""

from . import bmi_pro, foods, premium_week, recipes, users, vip  # noqa: F401

__all__ = [
    "bmi_pro",
    "foods",
    "premium_week",
    "recipes",
    "users",
    "vip",
]
