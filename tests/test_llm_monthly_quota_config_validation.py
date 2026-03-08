"""Tests: VIP LLM monthly quota config validation (fail-fast).

RU: Тесты валидации конфигурации квоты (fail-fast) для VIP LLM.
EN: Tests for VIP LLM monthly quota config validation (fail-fast).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.security.server_salt import require_server_salt as shim_require_server_salt
from app.security import llm_monthly_quota as quota


def test_require_server_salt_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERVER_SALT", raising=False)
    with pytest.raises(RuntimeError, match=r"SERVER_SALT is required"):
        quota.require_server_salt()


def test_server_salt_shim_delegates_to_shared_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER_SALT", "shared-secret")
    assert shim_require_server_salt() == "shared-secret"


def test_require_vip_llm_monthly_limit_uses_default_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", raising=False)
    assert quota.require_vip_llm_monthly_limit() == quota.DEFAULT_VIP_LLM_INSIGHT_REQUESTS_PER_MONTH


def test_require_pro_llm_monthly_limit_uses_default_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", raising=False)
    assert (
        quota.require_llm_monthly_limit("PRO") == quota.DEFAULT_PRO_LLM_INSIGHT_REQUESTS_PER_MONTH
    )


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


def test_require_pro_llm_monthly_limit_raises_on_non_int(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "bad")
    with pytest.raises(
        RuntimeError, match=r"PRO_LLM_INSIGHT_REQUESTS_PER_MONTH must be an integer >= 1"
    ):
        quota.require_llm_monthly_limit("PRO")


def test_require_llm_monthly_limit_rejects_unknown_tier() -> None:
    with pytest.raises(RuntimeError, match="Unsupported LLM quota tier"):
        quota.require_llm_monthly_limit("ENTERPRISE")


def test_llm_key_fingerprint_is_tier_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER_SALT", "test-server-salt")
    assert quota.llm_key_fingerprint("same-key", tier="PRO") != quota.llm_key_fingerprint(
        "same-key",
        tier="VIP",
    )


def test_month_start_date_utc_bucket() -> None:
    # Cover month_start_date_utc(now=...) deterministic path.
    now = datetime(2026, 2, 5, 12, 30, tzinfo=timezone.utc)
    assert str(quota.month_start_date_utc(now)) == "2026-02-01"


def test_month_start_date_utc_naive_datetime_treated_as_utc() -> None:
    naive = datetime(2026, 2, 15, 12, 0, 0)  # no tzinfo
    assert quota.month_start_date_utc(now=naive) == date(2026, 2, 1)


def test_vip_limit_wrapper_matches_generic_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", raising=False)
    assert quota.vip_llm_monthly_limit_requests() == quota.llm_monthly_limit_requests("VIP")
