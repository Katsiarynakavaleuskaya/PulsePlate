"""Compatibility shim for the shared SERVER_SALT helper.

RU: Совместимый shim для общего helper'а SERVER_SALT.
EN: Compatibility shim for the shared SERVER_SALT helper.
"""

from __future__ import annotations

from core.server_salt import require_server_salt

__all__ = ["require_server_salt"]
