"""LLM monthly hard quota enforcement.

RU: Жёсткая месячная квота для LLM (requests/month), авторитетный счётчик в БД.
EN: Deterministic monthly hard quota for LLM endpoints (requests/month), backed by DB.

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
from app.security.server_salt import require_server_salt

_VIP_LIMIT_ENV = "VIP_LLM_INSIGHT_REQUESTS_PER_MONTH"
_PRO_LIMIT_ENV = "PRO_LLM_INSIGHT_REQUESTS_PER_MONTH"

# NOTE: Table name must match app/models/llm_quota_usage.py.
_USAGE_TABLE = "vip_llm_monthly_usage"

DEFAULT_VIP_LLM_INSIGHT_REQUESTS_PER_MONTH = 30
DEFAULT_PRO_LLM_INSIGHT_REQUESTS_PER_MONTH = 20

_TIER_LIMIT_ENV = {
    "VIP": _VIP_LIMIT_ENV,
    "PRO": _PRO_LIMIT_ENV,
}
_TIER_LIMIT_DEFAULT = {
    "VIP": DEFAULT_VIP_LLM_INSIGHT_REQUESTS_PER_MONTH,
    "PRO": DEFAULT_PRO_LLM_INSIGHT_REQUESTS_PER_MONTH,
}


def _normalize_tier(tier: str) -> str:
    normalized = tier.strip().upper()
    if normalized not in _TIER_LIMIT_ENV:
        supported = ", ".join(sorted(_TIER_LIMIT_ENV))
        raise RuntimeError(f"Unsupported LLM quota tier: {tier!r}. Expected one of: {supported}.")
    return normalized


def require_llm_monthly_limit(tier: str) -> int:
    """Validate tier-specific LLM monthly limit (fail-fast)."""

    normalized_tier = _normalize_tier(tier)
    env_name = _TIER_LIMIT_ENV[normalized_tier]
    default_value = _TIER_LIMIT_DEFAULT[normalized_tier]

    raw = (os.getenv(env_name) or "").strip()
    if raw == "":
        return default_value

    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{env_name} must be an integer >= 1.") from exc

    if value < 1:
        raise RuntimeError(f"{env_name} must be an integer >= 1.")

    return value


def llm_monthly_limit_requests(tier: str) -> int:
    """Return tier-specific monthly request limit (env-backed, safe default)."""

    return require_llm_monthly_limit(tier)


def require_vip_llm_monthly_limit() -> int:
    """Backward-compatible VIP limit validator."""

    return require_llm_monthly_limit("VIP")


def require_pro_llm_monthly_limit() -> int:
    """Backward-compatible PRO limit validator."""

    return require_llm_monthly_limit("PRO")


def vip_llm_monthly_limit_requests() -> int:
    """Backward-compatible VIP request limit getter."""

    return llm_monthly_limit_requests("VIP")


def month_start_date_utc(now: datetime | None = None) -> date:
    """Return UTC calendar month bucket start date (YYYY-MM-01)."""

    dt = now or datetime.now(timezone.utc)
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    return date(dt_utc.year, dt_utc.month, 1)


def llm_key_fingerprint(raw_key: str, *, tier: str) -> str:
    """Return salted key fingerprint for a specific subscription tier."""

    normalized_tier = _normalize_tier(tier)
    salt = require_server_salt()
    data = f"{normalized_tier}:{raw_key}{salt}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def vip_key_fingerprint(raw_key: str) -> str:
    """Return salted VIP key fingerprint (backward-compatible wrapper)."""

    return llm_key_fingerprint(raw_key, tier="VIP")


def attempt_consume_llm_monthly_quota(
    raw_key: str,
    *,
    tier: str,
    month_start: date | None = None,
    limit_requests: int | None = None,
) -> bool:
    """Atomically consume one unit from a tier-specific monthly quota."""

    normalized_tier = _normalize_tier(tier)
    fp = llm_key_fingerprint(raw_key, tier=normalized_tier)
    bucket = month_start or month_start_date_utc()
    limit_val = (
        limit_requests
        if limit_requests is not None
        else llm_monthly_limit_requests(normalized_tier)
    )

    if limit_val < 1:
        return False

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


def attempt_consume_vip_llm_monthly_quota(
    raw_vip_key: str,
    *,
    month_start: date | None = None,
    limit_requests: int | None = None,
) -> bool:
    """Backward-compatible VIP quota helper.

    Keep wrapper commentary explicit so older SQL-contract guards still see the
    canonical qualified column name: ``vip_llm_monthly_usage.used_requests``.
    """

    return attempt_consume_llm_monthly_quota(
        raw_vip_key,
        tier="VIP",
        month_start=month_start,
        limit_requests=limit_requests,
    )
