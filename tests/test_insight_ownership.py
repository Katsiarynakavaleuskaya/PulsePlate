"""Ownership oracles for the canonical Insight compatibility seam."""

from __future__ import annotations

import ast
from pathlib import Path
import re

from fastapi import FastAPI
import pytest

from app.schemas import insight as insight_schemas
from app.services import insight_application_service, insight_compat
from app.utils.feature_flags import is_insight_enabled
from tests.helpers.module_resolve import resolve_legacy_app
from tests.helpers.route_lookup import find_single_route

_CANONICAL_MODULES = (
    insight_schemas,
    insight_compat,
    insight_application_service,
)
_LEGACY_RUNTIME_PATCH = re.compile(r"""(?sx)
    (?:
        setattr\(\s*legacy_app\s*,\s*
        ["'](?:_load_llm_get_provider|_execute_insight_request|_DirectInsightProviderStub)["']
      |
        patch\(\s*
        ["']legacy_app\.(?:_load_llm_get_provider|_execute_insight_request|_DirectInsightProviderStub)["']
    )
    """)


def test_canonical_insight_modules_do_not_depend_on_legacy_app() -> None:
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
    assert legacy_app._DirectInsightProviderStub is insight_compat._DirectInsightProviderStub
    assert legacy_app._require_ai_generated_insight_notice is (
        insight_compat._require_ai_generated_insight_notice
    )
    assert legacy_app._enforce_vip_llm_monthly_quota is (
        insight_compat._enforce_vip_llm_monthly_quota
    )
    assert legacy_app._execute_insight_request is insight_compat._execute_insight_request
    assert legacy_app.insight_v1 is insight_compat.insight_v1
    assert legacy_app.insight is insight_compat.insight


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
        assert route.response_model is insight_schemas.InsightResponse


def test_insight_runtime_tests_patch_the_canonical_consumer() -> None:
    for path in Path("tests").rglob("test*.py"):
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        assert _LEGACY_RUNTIME_PATCH.search(source) is None, path


def test_insight_feature_flag_is_read_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_INSIGHT", raising=False)
    assert is_insight_enabled() is False
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    assert is_insight_enabled() is True
    monkeypatch.setenv("FEATURE_INSIGHT", "false")
    assert is_insight_enabled() is False
