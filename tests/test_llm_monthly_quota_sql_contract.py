"""Tests: SQL contract for tiered LLM monthly quota.

RU: Контрактный тест SQL для tiered LLM monthly quota (защита от регрессов).
EN: SQL contract test for tiered LLM monthly quota (regression guard).
"""

from __future__ import annotations

import inspect

from app.security import llm_monthly_quota as quota


def test_quota_sql_qualifies_used_requests_column() -> None:
    """Ensure SQL keeps qualified used_requests reference for Postgres.

    RU: Фиксируем, что SQL содержит квалификацию `vip_llm_monthly_usage.used_requests`,
    чтобы не получить Postgres `column reference is ambiguous`.
    EN: Assert SQL contains qualified `vip_llm_monthly_usage.used_requests` to avoid
    Postgres `column reference is ambiguous`.
    """

    src = inspect.getsource(quota.attempt_consume_llm_monthly_quota)
    assert "vip_llm_monthly_usage.used_requests" in src
