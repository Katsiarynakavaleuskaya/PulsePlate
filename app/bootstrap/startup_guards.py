"""Startup guard orchestration for canonical app bootstrap.

RU: Собирает fail-closed startup guards в одном bootstrap seam.
EN: Centralizes fail-closed startup guards in one bootstrap seam.
"""

from __future__ import annotations

import os

from app.security.llm_monthly_quota import (
    require_pro_llm_monthly_limit,
    require_vip_llm_monthly_limit,
)
from app.security.server_salt import require_server_salt
from settings import (
    get_runtime_env_name,
    is_production_like_env,
    is_truthy_env_var,
    validate_api_key_toggle_guard,
    validate_apple_receipt_verification_config,
)


def _require_subscription_db_in_production_like_env() -> None:
    """Fail closed when paid entitlement mode lacks DB-backed subscription truth.

    RU: В production/staging платный authz должен опираться на persisted entitlement truth.
    EN: In production/staging, paid authz must rely on persisted entitlement truth.
    """

    if not is_production_like_env():
        return
    if is_truthy_env_var("SUBSCRIPTION_DB_ENABLED", "false"):
        return

    runtime_env = get_runtime_env_name()
    raise RuntimeError(
        "SUBSCRIPTION_DB_ENABLED must be true in production/staging environments "
        f"(current env: {runtime_env or os.getenv('APP_ENV', 'unknown')})."
    )


def run_startup_guards() -> None:
    """Execute startup-time hard guards before the app serves traffic.

    RU: Выполняет обязательные startup guards до начала обработки запросов.
    EN: Runs required startup guards before request handling begins.
    """

    require_server_salt()
    require_pro_llm_monthly_limit()
    require_vip_llm_monthly_limit()
    validate_apple_receipt_verification_config()
    validate_api_key_toggle_guard()
    _require_subscription_db_in_production_like_env()
