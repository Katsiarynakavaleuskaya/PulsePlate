# -*- coding: utf-8 -*-
import importlib
from tests._client import get_client

from fastapi.testclient import TestClient

app_module = importlib.import_module("app")
client = get_client()


def test_openapi_json_available():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    body = r.json()
    assert "paths" in body
    assert "/api/v1/bmi" in body["paths"]


def test_docs_available():
    r = client.get("/docs")
    assert r.status_code == 200
