"""Shared SERVER_SALT access helper.

RU: Нейтральный helper для SERVER_SALT, доступный core/app слоям.
EN: Domain-neutral SERVER_SALT helper shared across core/app layers.
"""

from __future__ import annotations

import os

SERVER_SALT_ENV = "SERVER_SALT"
MIN_SERVER_SALT_LENGTH = 32
_WEAK_SERVER_SALT_VALUES = frozenset({"default", "changeme", "password", "secret", "1234"})


def require_server_salt() -> str:
    """Return SERVER_SALT or raise (fail-fast contract).

    RU: Возвращает SERVER_SALT или падает (fail-fast).
    EN: Returns SERVER_SALT or raises (fail-fast).
    """

    salt = (os.getenv(SERVER_SALT_ENV) or "").strip()
    if not salt:
        raise RuntimeError(
            "SERVER_SALT is required for security-sensitive hashing. "
            "Set SERVER_SALT to a non-empty secret value."
        )
    if salt.casefold() in _WEAK_SERVER_SALT_VALUES:
        raise RuntimeError(
            f"{SERVER_SALT_ENV} must not use a default or guessable placeholder value."
        )
    if len(salt) < MIN_SERVER_SALT_LENGTH:
        raise RuntimeError(
            f"{SERVER_SALT_ENV} must be a strong secret with at least "
            f"{MIN_SERVER_SALT_LENGTH} characters."
        )
    character_classes = sum(
        (
            any(ch.islower() for ch in salt),
            any(ch.isupper() for ch in salt),
            any(ch.isdigit() for ch in salt),
            any(not ch.isalnum() for ch in salt),
        )
    )
    if character_classes < 2:
        raise RuntimeError(
            f"{SERVER_SALT_ENV} must include at least two character classes "
            "(lower/upper/digit/symbol)."
        )
    return salt
