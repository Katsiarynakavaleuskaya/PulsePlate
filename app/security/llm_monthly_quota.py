"""VIP LLM monthly hard quota enforcement.

RU: Жёсткая месячная квота для VIP LLM (requests/month), авторитетный счётчик в БД.
EN: VIP monthly hard quota for LLM endpoints (requests/month), authoritative DB counter.

Design goals (P0):
- Deterministic hard-stop before provider call
- Atomic check+increment (parallel-safe)
- No raw key storage (fingerprint only, salted)
"""

from __future__ import annotations

import hashlib
import os
from datetime import date, datetime, timezone

from sqlalchemy import text

from core.db import session_scope

from app.models.llm_quota_usage import VipLlmMonthlyUsage  # noqa: F401  # register table metadata

_SERVER_SALT_ENV = "SERVER_SALT"
_VIP_LIMIT_ENV = "VIP_LLM_INSIGHT_REQUESTS_PER_MONTH"

# NOTE: Table name must match app/models/llm_quota_usage.py.
_USAGE_TABLE = "vip_llm_monthly_usage"

DEFAULT_VIP_LLM_INSIGHT_REQUESTS_PER_MONTH = 30


def require_server_salt() -> str:
    """Return SERVER_SALT or raise (fail-fast contract).

    RU: Возвращает SERVER_SALT или падает (fail-fast).
    EN: Returns SERVER_SALT or raises (fail-fast).
    """

    salt = (os.getenv(_SERVER_SALT_ENV) or "").strip()
    if not salt:
        raise RuntimeError(
            "SERVER_SALT is required for VIP LLM monthly quota enforcement. "
            "Set SERVER_SALT to a non-empty secret value."
        )
    return salt


def require_vip_llm_monthly_limit() -> int:
    """Validate VIP LLM monthly limit at startup (fail-fast).

    RU: Валидируем лимит на старте. Падаем сразу при некорректном значении.
    EN: Validate quota limit at startup. Fail fast on invalid config.
    """

    raw = (os.getenv(_VIP_LIMIT_ENV) or "").strip()
    if raw == "":
        return DEFAULT_VIP_LLM_INSIGHT_REQUESTS_PER_MONTH

    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{_VIP_LIMIT_ENV} must be an integer >= 1.") from exc

    if value < 1:
        raise RuntimeError(f"{_VIP_LIMIT_ENV} must be an integer >= 1.")

    return value


def vip_llm_monthly_limit_requests() -> int:
    """Return VIP monthly request limit (env-backed, safe default)."""

    # Keep this helper stable: runtime code may call it outside startup.
    # Startup validation is enforced by require_vip_llm_monthly_limit().
    return require_vip_llm_monthly_limit()


def month_start_date_utc(now: datetime | None = None) -> date:
    """Return UTC calendar month bucket start date (YYYY-MM-01)."""

    dt = now or datetime.now(timezone.utc)
    # RU: Наивные datetime трактуем как UTC (а не local time), иначе astimezone() может сместить месяц.
    # EN: Treat naive datetimes as UTC (not local time) to avoid month bucket drift.
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    return date(dt_utc.year, dt_utc.month, 1)


def vip_key_fingerprint(raw_key: str) -> str:
    """Return salted VIP key fingerprint (hex sha256).

    RU: Никогда не хранить raw ключ; используем sha256(key + SERVER_SALT).
    EN: Never store raw keys; fingerprint is sha256(key + SERVER_SALT).
    """

    salt = require_server_salt()
    data = (raw_key + salt).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def attempt_consume_vip_llm_monthly_quota(
    raw_vip_key: str,
    *,
    month_start: date | None = None,
    limit_requests: int | None = None,
) -> bool:
    """Atomically consume one unit from the VIP monthly quota.

    Returns:
        True if quota was consumed (request may proceed),
        False if quota is exceeded (hard stop).
    """

    fp = vip_key_fingerprint(raw_vip_key)
    bucket = month_start or month_start_date_utc()
    limit_val = limit_requests if limit_requests is not None else vip_llm_monthly_limit_requests()

    if limit_val < 1:
        # RU: Fail closed — неверная конфигурация/параметр не должен давать доступ.
        # EN: Fail closed — invalid config/param must not grant access.
        return False

    # Single-statement upsert with guard:
    # - First request: insert (used_requests=1)
    # - Subsequent: update (used_requests += 1) only if current used_requests < limit
    # NOTE: Keep table name as a literal string to satisfy Bandit B608.
    # The table name is a fixed internal constant, not user input.
    sql = text("""
        INSERT INTO vip_llm_monthly_usage (key_fingerprint, month_start_date, used_requests)
        VALUES (:fp, :month_start, 1)
        ON CONFLICT(key_fingerprint, month_start_date)
        DO UPDATE SET used_requests = vip_llm_monthly_usage.used_requests + 1
        WHERE vip_llm_monthly_usage.used_requests < :limit_val
        RETURNING used_requests
        """)

    with session_scope() as session:
        row = session.execute(
            sql,
            {"fp": fp, "month_start": bucket, "limit_val": limit_val},
        ).first()
        return row is not None
