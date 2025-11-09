#!/usr/bin/env python3
"""Secure stdin-based API key updater. / Безопасный обновитель API-ключа через stdin."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from update_api_key import DEFAULT_PROFILE, update_api_key  # noqa: E402


def _read_api_key() -> str:
    """Read API key from stdin or API_KEY env var. / Читает API-ключ из stdin или переменной окружения API_KEY."""
    env_key = os.environ.get("API_KEY", "").strip()
    if env_key:
        os.environ.pop("API_KEY", None)
        return env_key

    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        return stdin_data

    raise RuntimeError(
        "API key not provided via stdin or API_KEY environment variable."
        " / API-ключ не передан через stdin или переменную окружения API_KEY."
    )


def main() -> None:
    """Entrypoint for secure key update flow. / Точка входа для безопасного обновления ключа."""
    try:
        api_key = _read_api_key()
    except RuntimeError as error:
        print(f"❌ {error}")
        sys.exit(1)

    if not update_api_key(api_key, profile=DEFAULT_PROFILE, use_encryption=True):
        sys.exit(1)


if __name__ == "__main__":
    main()
