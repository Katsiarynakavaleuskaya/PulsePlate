"""
Memory (Memori) Configuration Module

RU: Модуль конфигурации для Memori - SQL-native memory engine для AI агентов.
EN: Configuration module for Memori - SQL-native memory engine for AI agents.

Memori автоматически сохраняет контекст взаимодействий и позволяет AI агентам
запоминать предыдущие диалоги и предпочтения пользователей.
"""

import os
from typing import Optional

from memori import Memori


def get_memori_instance(
    user_id: Optional[str] = None,
    database_url: Optional[str] = None,
    conscious_ingest: bool = False,
    auto_ingest: bool = False,
) -> Memori:
    """
    Создает и возвращает настроенный экземпляр Memori.

    RU: Создает экземпляр Memori с настройками из переменных окружения.
    EN: Creates Memori instance with configuration from environment variables.

    Args:
        user_id: Идентификатор пользователя (опционально)
        database_url: URL базы данных (по умолчанию: SQLite)
        conscious_ingest: Включить сознательное извлечение сущностей (требует OpenAI API)
        auto_ingest: Автоматически извлекать информацию из диалогов

    Returns:
        Настроенный экземпляр Memori

    Environment Variables:
        MEMORI_DATABASE_URL: URL базы данных (например, postgresql://user:pass@host/db)
        OPENAI_API_KEY: API ключ OpenAI (требуется для conscious_ingest=True)
        MEMORI_USER_ID: Идентификатор пользователя по умолчанию
        MEMORI_CONSCIOUS_INGEST: Включить conscious_ingest (true/false)
        MEMORI_AUTO_INGEST: Включить auto_ingest (true/false)
    """
    # Получаем настройки из переменных окружения
    db_url = database_url or os.getenv("MEMORI_DATABASE_URL", "sqlite:///memori.db")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    default_user_id = user_id or os.getenv("MEMORI_USER_ID")

    # Парсим boolean флаги из окружения
    conscious = conscious_ingest or os.getenv("MEMORI_CONSCIOUS_INGEST", "false").lower() == "true"
    auto = auto_ingest or os.getenv("MEMORI_AUTO_INGEST", "false").lower() == "true"

    # Создаем экземпляр Memori
    memori = Memori(
        database_connect=db_url,
        conscious_ingest=conscious,
        auto_ingest=auto,
        user_id=default_user_id,
        openai_api_key=openai_api_key,
        verbose=os.getenv("MEMORI_VERBOSE", "false").lower() == "true",
    )

    # Включаем Memori (активирует автоматическое сохранение контекста)
    memori.enable()

    return memori


# Глобальный экземпляр (ленивая инициализация)
_memori_instance: Optional[Memori] = None


def get_global_memori() -> Optional[Memori]:
    """
    Получить глобальный экземпляр Memori (ленивая инициализация).

    RU: Возвращает глобальный экземпляр Memori, создавая его при первом вызове.
    EN: Returns global Memori instance, creating it on first call.

    Returns:
        Экземпляр Memori или None, если не настроен
    """
    global _memori_instance
    if _memori_instance is None:
        try:
            _memori_instance = get_memori_instance()
        except Exception:
            # Если Memori не настроен, возвращаем None
            # Приложение может работать без памяти
            return None
    return _memori_instance
