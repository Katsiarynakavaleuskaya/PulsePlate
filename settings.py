"""Application configuration values."""

from __future__ import annotations

import os

_EXPORT_SIGNING_PLACEHOLDERS = frozenset(
    {
        "__set_me__",
        "replace_me",
        "replace_me_with_export_secret",
    }
)


def get_runtime_env_name() -> str:
    """Return canonical runtime environment label.

    RU: Канонизирует имя окружения из APP_ENV/ENVIRONMENT.
    EN: Canonicalizes runtime environment from APP_ENV/ENVIRONMENT.
    """

    return (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "local").strip().lower()


def is_private_exports_enabled() -> bool:
    """Return whether signed private exports are enabled.

    RU: Определяет, включены ли приватные export-ссылки.
    EN: Returns whether private export links are enabled.
    """

    raw_value = os.getenv("PRIVATE_EXPORTS_ENABLED", "1")
    return (raw_value or "").strip().lower() not in {"0", "false"}


def get_export_token_secret() -> str:
    """Return export signing secret or raise on unsafe production config.

    RU: Возвращает секрет подписи export-ссылок и падает на небезопасном prod-like конфиге.
    EN: Returns export-signing secret and fails on unsafe production-like config.
    """

    secret = os.getenv("EXPORT_TOKEN_SECRET", "__set_me__").strip()
    normalized_secret = secret.lower()
    runtime_env = get_runtime_env_name()
    if is_private_exports_enabled() and runtime_env in {"production", "prod", "staging"}:
        if not secret or normalized_secret in _EXPORT_SIGNING_PLACEHOLDERS:
            raise RuntimeError(
                "EXPORT_TOKEN_SECRET must be set to a non-default secret when "
                "PRIVATE_EXPORTS_ENABLED=true in production/staging."
            )
    return secret


def get_export_token_ttl_seconds() -> int:
    """Return export-signing TTL or raise on invalid config.

    RU: Валидирует TTL подписанных export-ссылок и запрещает нулевые/отрицательные значения.
    EN: Validates signed-export TTL and rejects zero/negative values.
    """

    ttl_seconds = int(os.getenv("EXPORT_TOKEN_TTL_SECONDS", "900").strip())
    if ttl_seconds <= 0:
        raise RuntimeError("EXPORT_TOKEN_TTL_SECONDS must be a positive integer.")
    return ttl_seconds


EXPORT_TOKEN_SECRET: str = get_export_token_secret()
EXPORT_TOKEN_TTL_SECONDS: int = get_export_token_ttl_seconds()
PRIVATE_EXPORTS_ENABLED: bool = is_private_exports_enabled()
