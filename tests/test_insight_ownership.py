"""Ownership oracles for the canonical Insight compatibility seam."""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.routers import legacy_insight as insight_router
from app.schemas import insight as insight_schemas
from app.services import insight_application_service, insight_compat
from tests.helpers.module_resolve import resolve_legacy_app
from tests.helpers.route_lookup import find_single_route

_CANONICAL_MODULES = (
    insight_router,
    insight_schemas,
    insight_compat,
    insight_application_service,
)
_CANONICAL_RUNTIME_TEST_PATHS = (
    Path("tests/test_core_ai_insight_runtime.py"),
    Path("tests/test_insight_application_service.py"),
    Path("tests/test_insight_error_hygiene.py"),
    Path("tests/test_insight_rag_response_fields.py"),
    Path("tests/test_insight_vip_guard_api.py"),
    Path("tests/test_insight_vip_monthly_quota_api.py"),
    Path("tests/test_legacy_insight_registration_bootstrap.py"),
    Path("tests/test_legacy_insight_router.py"),
    Path("tests/test_rag_vector_feature_flag_guard.py"),
    Path("tests/test_rate_limit_llm_and_exports_api.py"),
)


def test_canonical_insight_modules_do_not_reference_legacy_app() -> None:
    for module in _CANONICAL_MODULES:
        source_path = Path(str(module.__file__))
        assert "legacy_app" not in source_path.read_text(encoding="utf-8"), source_path


def test_legacy_insight_exports_are_exact_canonical_aliases() -> None:
    legacy_app = resolve_legacy_app()

    assert legacy_app.INSIGHT_TEXT_MAX_LENGTH == insight_schemas.INSIGHT_TEXT_MAX_LENGTH
    assert legacy_app.InsightRequest is insight_schemas.InsightRequest
    assert legacy_app.RAGSourceItem is insight_schemas.RAGSourceItem
    assert legacy_app.InsightResponse is insight_schemas.InsightResponse
    assert legacy_app.INSIGHT_TEMP_UNAVAILABLE_MESSAGE is (
        insight_compat.INSIGHT_TEMP_UNAVAILABLE_MESSAGE
    )
    assert legacy_app._execute_insight_request is insight_compat._execute_insight_request
    assert legacy_app.insight_v1 is insight_compat.insight_v1
    assert legacy_app.insight is insight_compat.insight


def test_obsolete_legacy_insight_injection_bindings_are_absent() -> None:
    legacy_app = resolve_legacy_app()

    for name in (
        "_DirectInsightProviderStub",
        "_enforce_vip_llm_monthly_quota",
        "_require_ai_generated_insight_notice",
        "require_safe_ai_agent_input",
    ):
        assert not hasattr(legacy_app, name)


def test_legacy_app_no_longer_defines_insight_models_or_dead_helpers() -> None:
    tree = ast.parse(Path("legacy_app.py").read_text(encoding="utf-8"))
    definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert definitions.isdisjoint(
        {
            "InsightRequest",
            "RAGSourceItem",
            "InsightResponse",
            "_ensure_insight_text_length",
            "_build_insight_prompt",
            "_build_rag_source_items",
        }
    )


def test_insight_router_response_models_are_canonical(app: FastAPI) -> None:
    for path in ("/api/v1/insight", "/insight"):
        route = find_single_route(app, path, "POST", family_label="legacy insight")
        assert getattr(route, "response_model", None) is insight_schemas.InsightResponse


def test_insight_runtime_test_family_does_not_use_legacy_facade() -> None:
    violations = [
        path.as_posix()
        for path in _CANONICAL_RUNTIME_TEST_PATHS
        if "legacy_app" in path.read_text(encoding="utf-8")
    ]

    assert violations == []


@pytest.mark.parametrize(
    ("path", "callable_name"),
    [
        ("/api/v1/insight", "insight_v1"),
        ("/insight", "insight"),
    ],
)
def test_insight_router_uses_canonical_adapter_after_facade_rebinding(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    vip_headers: dict[str, str],
    path: str,
    callable_name: str,
) -> None:
    legacy_app = resolve_legacy_app()
    monkeypatch.setenv("FEATURE_INSIGHT", "true")

    def _legacy_must_not_run(*_args: object, **_kwargs: object) -> None:
        pytest.fail("canonical router must ignore legacy facade rebinding")

    async def _canonical_response(
        *_args: object, **_kwargs: object
    ) -> insight_schemas.InsightResponse:
        return insight_schemas.InsightResponse(provider="canonical", insight="ok")

    monkeypatch.setattr(legacy_app, "_execute_insight_request", _legacy_must_not_run, raising=True)
    monkeypatch.setattr(legacy_app, callable_name, _legacy_must_not_run, raising=True)
    monkeypatch.setattr(
        insight_compat,
        "_enforce_vip_llm_monthly_quota",
        lambda *_args, **_kwargs: None,
        raising=True,
    )
    monkeypatch.setattr(insight_compat, callable_name, _canonical_response, raising=True)

    response = client.post(path, json={"text": "hello"}, headers=vip_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["provider"] == "canonical"
