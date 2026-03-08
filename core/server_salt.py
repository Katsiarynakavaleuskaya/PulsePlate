"""Shared SERVER_SALT access helper.

RU: Нейтральный helper для SERVER_SALT, доступный core/app слоям.
EN: Domain-neutral SERVER_SALT helper shared across core/app layers.
"""

from __future__ import annotations

import os

SERVER_SALT_ENV = "SERVER_SALT"


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
    return salt
