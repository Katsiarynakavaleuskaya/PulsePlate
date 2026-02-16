"""
app/openapi/orm_imports.py

RU: Import-safe ORM model resolvers for runtime code paths (incl. OpenAPI generation),
where module import-time must not trigger ORM side effects.

EN: Import-safe ORM model resolvers for runtime paths where import-time must not trigger
ORM side effects.
"""

from __future__ import annotations

import importlib
from typing import Final

# Import-safe cache: values are model classes or other resolved objects.
# We intentionally avoid `Any` in core/openapi logic.
_ORM_IMPORT_CACHE: dict[str, object] = {}

# Canonical cache keys (stable string literals).
_NUTRITION_EVENT_KEY: Final[str] = "nutrition_event_model"


def clear_orm_import_cache() -> None:
    """Clear cached ORM imports (test helper).

    RU: Сбрасывает кэш import-safe ORM-резолвера. Используется только в тестах,
    чтобы избежать зависимостей от порядка импортов.
    """
    _ORM_IMPORT_CACHE.clear()


def _lazy_import_attr(module_path: str, attr_name: str) -> object:
    """Import `module_path` lazily and return `attr_name`.

    RU: Ленивый импорт без side effects на уровне модуля. ORM-модели не должны
    импортироваться при генерации OpenAPI / schema-only режимах.
    """
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


def get_nutrition_event_model() -> object:
    """Return the NutritionEvent ORM model class (import-safe).

    RU: Возвращает ORM-модель NutritionEvent лениво, чтобы не регистрировать
    ORM на этапе импорта роутеров.
    EN: Returns NutritionEvent ORM model lazily to avoid ORM registration at
    router module import time.
    """
    cached = _ORM_IMPORT_CACHE.get(_NUTRITION_EVENT_KEY)
    if cached is not None:
        return cached

    model = _lazy_import_attr("app.models", "NutritionEvent")
    _ORM_IMPORT_CACHE[_NUTRITION_EVENT_KEY] = model
    return model
