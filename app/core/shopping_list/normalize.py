"""Normalization Helpers.

RU: Нормализация ключей и названий ингредиентов.
EN: Normalize ingredient keys and titles.

This module provides simple, deterministic normalization for ingredient keys.
"""


def normalize_key(raw_key: str) -> str:
    """Normalize ingredient key to lowercase snake_case.

    Args:
        raw_key: Raw ingredient key from plan_data

    Returns:
        Normalized key (lowercase, spaces replaced with underscores)

    Examples:
        "Chicken Breast" -> "chicken_breast"
        "olive_oil" -> "olive_oil"
        "  Rice  " -> "rice"
    """
    return raw_key.strip().lower().replace(" ", "_")


def humanize_title(key: str) -> str:
    """Convert normalized key to human-readable title.

    Args:
        key: Normalized ingredient key

    Returns:
        Title-cased display name

    Examples:
        "chicken_breast" -> "Chicken Breast"
        "olive_oil" -> "Olive Oil"
    """
    return key.replace("_", " ").title()
