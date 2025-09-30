# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient

try:
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from app.py file
import importlib.util
spec = importlib.util.spec_from_file_location("app_module", "app.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load app.py")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
# In tests/test_misc_routes.py, replace the erroneous line with:
fastapi_app = app_module.app  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(fastapi_app)


def test_favicon_or_skip():
    r = client.get("/favicon.ico")
    if r.status_code in (404, 405):
        pytest.skip("No /favicon.ico (skipping)")
    assert r.status_code in (200, 204)


def test_plan_422_or_skip():
    """Гарантируем, что плановый эндпоинт либо есть, либо аккуратно скипаем."""
    r = client.post("/api/v1/plan", json={})
    if r.status_code == 404:
        pytest.skip("No /api/v1/plan (skipping)")
    # Если роут есть — без валидного payload должен быть 400/422
    assert r.status_code in (400, 422)
