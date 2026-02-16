from __future__ import annotations

from typing import Final

# RU: Единый дефолт языка для унифицированной БД.
# EN: Unified default language for unified DB surface.
DEFAULT_UNIFIED_DB_LANGUAGE: Final[str] = "en"


def normalize_unified_db_language(language: str | None) -> str:
    """Normalize language tag to a stable base language.

    Examples:
    - "es-ES" -> "es"
    - "ru_RU" -> "ru"
    - None / "" -> "en"
    """
    raw = (language or "").strip().lower()
    if not raw:
        return DEFAULT_UNIFIED_DB_LANGUAGE
    base = raw.split("-", 1)[0].split("_", 1)[0]
    return base or DEFAULT_UNIFIED_DB_LANGUAGE
