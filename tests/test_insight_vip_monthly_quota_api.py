"""P0 tests: VIP LLM monthly hard quota (requests/month).

RU: P0 тесты: жёсткая месячная квота для VIP LLM (requests/month).
EN: P0 tests: deterministic monthly hard quota for VIP LLM (requests/month).
"""

from __future__ import annotations

import concurrent.futures
import threading
from datetime import date
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.middleware.api_tiers import TEST_KEY_VIP
from app.security.llm_monthly_quota import (
    attempt_consume_vip_llm_monthly_quota,
    month_start_date_utc,
    vip_key_fingerprint,
)


class _FailIfCalledProvider:
    """Provider that fails test if generate() is called.

    RU: Провайдер, который валит тест если generate() вызывается.
    EN: Provider that fails the test if generate() is called.
    """

    name: str = "should_not_be_called"

    async def generate(self, text: str) -> str:  # pragma: no cover
        raise AssertionError("provider.generate() must not be called when quota is exceeded")


def _seed_usage_row(
    db_module: object,
    *,
    key_fp: str,
    month_start: date,
    used_requests: int,
) -> None:
    session_scope = getattr(db_module, "session_scope")
    with session_scope() as session:
        session.execute(text("DELETE FROM vip_llm_monthly_usage"))
        session.execute(
            text("""
                INSERT INTO vip_llm_monthly_usage (key_fingerprint, month_start_date, used_requests)
                VALUES (:fp, :month_start, :used_requests)
                """),
            {"fp": key_fp, "month_start": month_start, "used_requests": used_requests},
        )


@patch("llm.get_provider", return_value=_FailIfCalledProvider())
def test_insight_v1_over_quota_hard_stops_before_provider_call(
    mock_get_provider: Mock,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    vip_headers: dict[str, str],
    configure_sqlite_database: object,
) -> None:
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", "1")

    month_start = month_start_date_utc()
    key_fp = vip_key_fingerprint(TEST_KEY_VIP)
    _seed_usage_row(
        configure_sqlite_database,
        key_fp=key_fp,
        month_start=month_start,
        used_requests=1,
    )

    r = client.post("/api/v1/insight", json={"text": "hello"}, headers=vip_headers)
    assert r.status_code == 429
    assert r.headers.get("content-type", "").startswith("application/json")
    assert r.json() == {"detail": "quota_exceeded"}


def test_vip_llm_monthly_quota_atomicity_limit_1_two_parallel_attempts(
    monkeypatch: pytest.MonkeyPatch,
    configure_sqlite_database: object,
) -> None:
    monkeypatch.setenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", "1")

    # Clean bucket for deterministic test.
    month_start = month_start_date_utc()
    key_fp = vip_key_fingerprint(TEST_KEY_VIP)
    _seed_usage_row(
        configure_sqlite_database,
        key_fp=key_fp,
        month_start=month_start,
        used_requests=0,
    )

    barrier = threading.Barrier(2)

    def _attempt() -> bool:
        barrier.wait(timeout=5)
        return attempt_consume_vip_llm_monthly_quota(
            TEST_KEY_VIP, month_start=month_start, limit_requests=1
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: _attempt(), range(2)))

    assert sorted(results) == [False, True]
