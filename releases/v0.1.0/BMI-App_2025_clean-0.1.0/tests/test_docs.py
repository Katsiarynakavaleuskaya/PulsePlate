# -*- coding: utf-8 -*-
import importlib

from fastapi.testclient import TestClient

app_module = importlib.import_module("app")
client = TestClient(app_module.app)


def test_openapi_json_available():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    body = r.json()
    assert "paths" in body
    assert "/api/v1/bmi" in body["paths"]


def test_docs_available():
    r = client.get("/docs")
    assert r.status_code == 200
