from __future__ import annotations

from typing import Any


def json_response_payload(response: Any) -> dict[str, Any]:
    """Return JSON payload from API response with deterministic content-type assertion."""
    assert response.headers.get("content-type", "").startswith("application/json"), response.text
    payload: dict[str, Any] = response.json()
    return payload
