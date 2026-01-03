# -*- coding: utf-8 -*-
"""
Tests for tests/_route_patch.py helper.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI

from tests._route_patch import find_route_endpoint, patch_endpoint_global


def dep() -> str:
    return "ok"


def test_find_route_endpoint_finds_registered_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastAPI()

    @app.get("/x")
    def handler() -> dict[str, str]:
        return {"v": dep()}

    endpoint = find_route_endpoint(app=app, path="/x", method="GET")
    assert callable(endpoint)

    patch_endpoint_global(
        monkeypatch=monkeypatch, endpoint=endpoint, name="dep", value=lambda: "patched"
    )
    # напрямую вызываем endpoint, чтобы убедиться что глобалка реально заменена
    out = endpoint()
    assert out == {"v": "patched"}


def test_find_route_endpoint_errors_on_missing_route() -> None:
    app = FastAPI()
    with pytest.raises(AssertionError, match=r"Route not found"):
        _ = find_route_endpoint(app=app, path="/missing", method="GET")
