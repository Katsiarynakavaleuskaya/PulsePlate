from __future__ import annotations

from typing import Generator

from tests._client import get_client

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide a fresh TestClient per test for isolation."""
    test_client = get_client()
    try:
        yield test_client
    finally:
        test_client.close()


def test_openapi_json_available(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    body = r.json()
    assert "paths" in body
    assert "/api/v1/bmi" in body["paths"]


def test_docs_available(client: TestClient) -> None:
    r = client.get("/docs")
    assert r.status_code == 200
