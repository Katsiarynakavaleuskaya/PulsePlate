"""Startup guard orchestration for canonical app bootstrap.

RU: Собирает fail-closed startup guards в одном bootstrap seam.
EN: Centralizes fail-closed startup guards in one bootstrap seam.
"""

from __future__ import annotations

from app.security.llm_monthly_quota import require_vip_llm_monthly_limit
from app.security.server_salt import require_server_salt
from settings import require_apple_shared_secret, validate_api_key_toggle_guard


def run_startup_guards() -> None:
    """Execute startup-time hard guards before the app serves traffic.

    RU: Выполняет обязательные startup guards до начала обработки запросов.
    EN: Runs required startup guards before request handling begins.
    """

    require_server_salt()
    require_vip_llm_monthly_limit()
    require_apple_shared_secret()
    validate_api_key_toggle_guard()
