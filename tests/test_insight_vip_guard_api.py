"""P0 tests: LLM insight must be VIP-only.

RU: P0 тесты: insight endpoint должен быть строго VIP-only.
EN: P0 tests: insight endpoint must be strictly VIP-only.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_insight_v1_requires_vip_tier(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
) -> None:
    """FREE/PRO are rejected; VIP can call /api/v1/insight.

    Note: VIP guard returns 403 for missing key by policy (VIP is a feature-gate).
    """
    import llm

    class EchoProvider:
        name = "echo"

        async def generate(self, text: str) -> str:
            return f"ok:{text}"

    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setattr(llm, "get_provider", lambda: EchoProvider(), raising=True)

    payload = {"text": "hello"}

    r_free = client.post("/api/v1/insight", json=payload)
    assert r_free.status_code == 403

    r_pro = client.post("/api/v1/insight", json=payload, headers=pro_headers)
    assert r_pro.status_code == 403

    r_vip = client.post("/api/v1/insight", json=payload, headers=vip_headers)
    assert r_vip.status_code == 200
    assert r_vip.headers.get("content-type", "").startswith("application/json")
    data = r_vip.json()
    assert data["provider"] == "echo"
    assert data["insight"].startswith("ok:")


# End of file
