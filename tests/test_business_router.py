from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


@dataclass
class _EnumLike:
    """Minimal stand-in for enum-like objects with a .value attribute."""

    value: str


@dataclass
class _AnalyzerResult:
    """Minimal result object compatible with business router mapping."""

    test_name: str
    success: bool
    business_category: _EnumLike
    error_type: Optional[_EnumLike]
    error_message: Optional[str]
    revenue_impact: str
    cost_impact: str
    customer_impact: str
    optimization_potential: Optional[str]


class TestBusinessRouterIsolated:
    """Isolated TestClient tests for app/routers/business.py endpoints."""

    def setup_method(self) -> None:
        """Set up isolated FastAPI app with only the business router."""
        from app.routers import business as business_mod

        self.mod = business_mod
        self.app = FastAPI()
        self.app.include_router(self.mod.router)
        self.client = TestClient(self.app)

    def teardown_method(self) -> None:
        """Clean up client and dependency overrides between tests."""
        self.client.close()
        self.app.dependency_overrides.clear()

    def _auth_ok(self) -> None:
        """Override API key dependency to bypass real auth checks."""
        from app.routers.api_key import require_app_api_key

        self.app.dependency_overrides[require_app_api_key] = lambda: "test_key"

    def _auth_forbidden(self, detail: str = "Invalid API Key") -> None:
        """Override API key dependency to enforce fail-closed auth in isolated tests."""
        from app.routers.api_key import require_app_api_key

        def _raise_forbidden() -> str:
            raise HTTPException(status_code=403, detail=detail)

        self.app.dependency_overrides[require_app_api_key] = _raise_forbidden

    def test_status_enabled_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(self.mod, "BUSINESS_MODULE_ENABLED", True)

        resp = self.client.get("/api/v1/business/status")
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"enabled": True, "module": "business_analysis"}

    def test_status_enabled_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(self.mod, "BUSINESS_MODULE_ENABLED", False)

        resp = self.client.get("/api/v1/business/status")
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"enabled": False, "module": "business_analysis"}

    def test_analyze_422_missing_code(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._auth_ok()
        monkeypatch.setattr(self.mod, "BUSINESS_MODULE_ENABLED", True)

        resp = self.client.post("/api/v1/business/analyze", json={"test_name": "t1"})
        assert resp.status_code == 422

    def test_analyze_403_when_api_key_guard_rejects(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._auth_forbidden()
        monkeypatch.setattr(self.mod, "BUSINESS_MODULE_ENABLED", True)

        resp = self.client.post(
            "/api/v1/business/analyze",
            json={"code": "print('x')", "test_name": "t1"},
        )
        assert resp.status_code == 403
        assert resp.json() == {"detail": "Invalid API Key"}

    def test_require_app_api_key_accepts_valid_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.routers import api_key as api_key_mod

        def _resolve_attr(name: str, default: object) -> object:
            if name == "get_api_key":
                return lambda api_key: api_key.strip()
            return default

        monkeypatch.setattr(api_key_mod, "resolve_attr", _resolve_attr)

        assert api_key_mod.require_app_api_key(" expected-key ") == "expected-key"

    def test_require_app_api_key_rejects_invalid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.routers import api_key as api_key_mod

        def _raise_invalid(_api_key: str) -> str:
            raise HTTPException(status_code=403, detail="Invalid API Key")

        def _resolve_attr(name: str, default: object) -> object:
            if name == "get_api_key":
                return _raise_invalid
            return default

        monkeypatch.setattr(api_key_mod, "resolve_attr", _resolve_attr)

        with pytest.raises(HTTPException) as exc_info:
            api_key_mod.require_app_api_key("wrong-key")

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Invalid API Key"

    def test_require_app_api_key_rejects_missing_validator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.routers import api_key as api_key_mod

        monkeypatch.setattr(api_key_mod, "resolve_attr", lambda _name, default: default)

        with pytest.raises(HTTPException) as exc_info:
            api_key_mod.require_app_api_key("test-key")

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "API key validation unavailable"

    def test_require_app_api_key_rejects_non_string_result(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        from app.routers import api_key as api_key_mod

        def _resolve_attr(name: str, default: object) -> object:
            if name == "get_api_key":
                return lambda _api_key: object()
            return default

        monkeypatch.setattr(api_key_mod, "resolve_attr", _resolve_attr)

        with pytest.raises(HTTPException) as exc_info:
            api_key_mod.require_app_api_key("test-key")

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "API key validation unavailable"
        assert "App API key guard returned non-string result" in caplog.text

    def test_require_app_api_key_rejects_missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.routers import api_key as api_key_mod

        def _raise_missing(_api_key: str) -> str:
            raise HTTPException(status_code=403, detail="Missing API Key")

        def _resolve_attr(name: str, default: object) -> object:
            if name == "get_api_key":
                return _raise_missing
            return default

        monkeypatch.setattr(api_key_mod, "resolve_attr", _resolve_attr)

        with pytest.raises(HTTPException) as exc_info:
            api_key_mod.require_app_api_key("")

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Missing API Key"

    def test_analyze_503_when_module_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._auth_ok()
        monkeypatch.setattr(self.mod, "BUSINESS_MODULE_ENABLED", False)
        monkeypatch.setattr(
            self.mod,
            "_localized_error",
            lambda _locale, _key: "business_module_disabled",
        )

        resp = self.client.post(
            "/api/v1/business/analyze",
            json={"code": "print('x')", "test_name": "t1", "locale": "en"},
        )
        assert resp.status_code == 503, resp.text
        assert resp.json()["detail"] == "business_module_disabled"

    def test_analyze_413_payload_too_large(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._auth_ok()
        monkeypatch.setattr(self.mod, "BUSINESS_MODULE_ENABLED", True)
        monkeypatch.setattr(
            self.mod,
            "_localized_error",
            lambda _locale, _key: "business_payload_too_large",
        )

        big_code = "a" * 100_001
        resp = self.client.post(
            "/api/v1/business/analyze",
            json={"code": big_code, "test_name": "t1", "locale": "en"},
        )
        assert resp.status_code == 413, resp.text
        assert resp.json()["detail"] == "business_payload_too_large"

    def test_analyze_200_payload_at_size_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Exact 100KB payload should be accepted (boundary test for < vs <=)."""
        self._auth_ok()
        monkeypatch.setattr(self.mod, "BUSINESS_MODULE_ENABLED", True)

        expected = [
            _AnalyzerResult(
                test_name="t1",
                success=True,
                business_category=_EnumLike("monetization"),
                error_type=None,
                error_message=None,
                revenue_impact="high",
                cost_impact="low",
                customer_impact="medium",
                optimization_potential=None,
            )
        ]

        class _FakeAnalyzer:
            def __init__(self, locale: Optional[str] = None) -> None:
                self.locale = locale

            def analyze(self, code: str, test_name: str) -> list[_AnalyzerResult]:
                assert len(code.encode("utf-8")) == 100_000
                return expected

        monkeypatch.setattr(self.mod, "BusinessBayesianAnalyzer", _FakeAnalyzer)

        code_at_limit = "a" * 100_000
        resp = self.client.post(
            "/api/v1/business/analyze",
            json={"code": code_at_limit, "test_name": "t1", "locale": "en"},
        )
        assert resp.status_code == 200, resp.text

    def test_analyze_happy_path_maps_results(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._auth_ok()
        monkeypatch.setattr(self.mod, "BUSINESS_MODULE_ENABLED", True)

        expected = [
            _AnalyzerResult(
                test_name="t1",
                success=True,
                business_category=_EnumLike("monetization"),
                error_type=None,
                error_message=None,
                revenue_impact="high",
                cost_impact="low",
                customer_impact="medium",
                optimization_potential="ship paywall A/B",
            )
        ]

        class _FakeAnalyzer:
            def __init__(self, locale: Optional[str] = None) -> None:
                self.locale = locale

            def analyze(self, code: str, test_name: str) -> list[_AnalyzerResult]:
                assert code == "print('x')"
                assert test_name == "t1"
                return expected

        monkeypatch.setattr(self.mod, "BusinessBayesianAnalyzer", _FakeAnalyzer)

        resp = self.client.post(
            "/api/v1/business/analyze",
            json={"code": "print('x')", "test_name": "t1", "locale": "en"},
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["test_name"] == "t1"
        assert data[0]["success"] is True
        assert data[0]["business_category"] == "monetization"
        assert data[0]["error_type"] == "unknown"
        assert data[0]["error_message"] is None
        assert data[0]["revenue_impact"] == "high"
        assert data[0]["cost_impact"] == "low"
        assert data[0]["customer_impact"] == "medium"
        assert data[0]["optimization_potential"] == "ship paywall A/B"

    def test_analyze_500_on_analyzer_exception_localized(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._auth_ok()
        monkeypatch.setattr(self.mod, "BUSINESS_MODULE_ENABLED", True)
        monkeypatch.setattr(
            self.mod,
            "_localized_error",
            lambda _locale, _key: "business_analysis_failed",
        )

        class _BoomAnalyzer:
            def __init__(self, locale: Optional[str] = None) -> None:
                self.locale = locale

            def analyze(self, code: str, test_name: str) -> list[Any]:
                raise RuntimeError("boom")

        monkeypatch.setattr(self.mod, "BusinessBayesianAnalyzer", _BoomAnalyzer)

        resp = self.client.post(
            "/api/v1/business/analyze",
            json={
                "code": "print('x')",
                "test_name": "evil\nname\t",
                "locale": "ru",
            },
        )
        assert resp.status_code == 500, resp.text
        assert resp.json()["detail"] == "business_analysis_failed"
