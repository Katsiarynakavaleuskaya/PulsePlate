"""Shared SERVER_SALT access helper (domain-neutral).

RU: Нейтральный helper для SERVER_SALT, без привязки к конкретному домену.
EN: Domain-neutral SERVER_SALT helper shared across security-sensitive modules.
"""

from __future__ import annotations

import os

_SERVER_SALT_ENV = "SERVER_SALT"


def require_server_salt() -> str:
    """Return SERVER_SALT or raise (fail-fast contract).

    RU: Возвращает SERVER_SALT или падает (fail-fast).
    EN: Returns SERVER_SALT or raises (fail-fast).
    """

    salt = (os.getenv(_SERVER_SALT_ENV) or "").strip()
    if not salt:
        raise RuntimeError(
            "SERVER_SALT is required for security-sensitive hashing. "
            "Set SERVER_SALT to a non-empty secret value."
        )
    return salt
