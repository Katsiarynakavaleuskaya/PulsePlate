"""
app/openapi/orm_imports.py

RU: Import-safe ORM model resolvers for runtime code paths (incl. OpenAPI generation),
where module import-time must not trigger ORM side effects.

EN: Import-safe ORM model resolvers for runtime paths where import-time must not trigger
ORM side effects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:  # pragma: no cover
    from app.models import NutritionEvent  # noqa: F401


def get_nutrition_event_model() -> Type["NutritionEvent"]:
    """Return NutritionEvent ORM model via runtime import.

    RU: runtime import, чтобы избежать import-time side effects.
    EN: runtime import to avoid import-time side effects.
    """
    from app.models import NutritionEvent

    return NutritionEvent
