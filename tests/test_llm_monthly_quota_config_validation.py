"""Tests: VIP LLM monthly quota config validation (fail-fast).

RU: Тесты валидации конфигурации квоты (fail-fast) для VIP LLM.
EN: Tests for VIP LLM monthly quota config validation (fail-fast).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.security import llm_monthly_quota as quota


def test_require_server_salt_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERVER_SALT", raising=False)
    with pytest.raises(RuntimeError, match=r"SERVER_SALT is required"):
        quota.require_server_salt()


def test_require_vip_llm_monthly_limit_uses_default_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", raising=False)
    assert quota.require_vip_llm_monthly_limit() == quota.DEFAULT_VIP_LLM_INSIGHT_REQUESTS_PER_MONTH


def test_require_vip_llm_monthly_limit_raises_on_non_int(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", "nope")
    with pytest.raises(
        RuntimeError, match=r"VIP_LLM_INSIGHT_REQUESTS_PER_MONTH must be an integer >= 1"
    ):
        quota.require_vip_llm_monthly_limit()


def test_require_vip_llm_monthly_limit_raises_on_lt_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", "0")
    with pytest.raises(
        RuntimeError, match=r"VIP_LLM_INSIGHT_REQUESTS_PER_MONTH must be an integer >= 1"
    ):
        quota.require_vip_llm_monthly_limit()


def test_month_start_date_utc_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    # Cover month_start_date_utc(now=...) deterministic path.
    now = datetime(2026, 2, 5, 12, 30, tzinfo=timezone.utc)
    assert str(quota.month_start_date_utc(now)) == "2026-02-01"
