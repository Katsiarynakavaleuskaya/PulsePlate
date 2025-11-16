"""
Memory (Memori) Configuration Module

RU: Модуль конфигурации для Memori - SQL-native memory engine для AI агентов.
EN: Configuration module for Memori - SQL-native memory engine for AI agents.

Memori автоматически сохраняет контекст взаимодействий и позволяет AI агентам
запоминать предыдущие диалоги и предпочтения пользователей.
"""

import logging
import os
from typing import Optional

from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memori import Memori as MemoriType
else:
    MemoriType = Any  # type: ignore[misc]

try:
    from memori import Memori as _MemoriRuntime
except ImportError:  # pragma: no cover - optional dependency
    _MemoriRuntime = None

# Expose runtime class for tests/monkeypatching
# Use MemoriType for type annotations, Memori for runtime
Memori = _MemoriRuntime

logger = logging.getLogger(__name__)


def get_memori_instance(
    user_id: Optional[str] = None,
    database_url: Optional[str] = None,
    conscious_ingest: Optional[bool] = None,
    auto_ingest: Optional[bool] = None,
) -> MemoriType:
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
    # RU: Явные аргументы переопределяют переменные окружения
    # EN: Explicit arguments override environment variables
    db_url = (
        database_url
        if database_url is not None
        else os.getenv("MEMORI_DATABASE_URL", "sqlite:///memori.db")
    )
    openai_api_key = os.getenv("OPENAI_API_KEY")
    default_user_id = user_id if user_id is not None else os.getenv("MEMORI_USER_ID")

    # Парсим boolean флаги из окружения
    # RU: Если явно передан аргумент (True или False), используем его, иначе берем из env
    # EN: If argument is explicitly provided (True or False), use it, otherwise use env
    if conscious_ingest is not None:
        conscious = conscious_ingest
    else:
        conscious = os.getenv("MEMORI_CONSCIOUS_INGEST", "false").lower() == "true"

    if auto_ingest is not None:
        auto = auto_ingest
    else:
        auto = os.getenv("MEMORI_AUTO_INGEST", "false").lower() == "true"

    # Создаем экземпляр Memori
    memori_cls = Memori if Memori is not None else _MemoriRuntime
    if memori_cls is None:
        raise RuntimeError(
            "memori package is not installed. Install 'memori' to enable memory integration."
        )

    memori = memori_cls(
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
_memori_instance: Optional[MemoriType] = None


def get_global_memori() -> Optional[MemoriType]:
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
        except (ImportError, RuntimeError, ValueError) as e:
            # Если Memori не настроен, возвращаем None
            # Приложение может работать без памяти
            logger.exception("Memori initialization failed: %s", e)
            return None
    return _memori_instance
