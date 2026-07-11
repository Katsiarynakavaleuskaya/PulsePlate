from __future__ import annotations

import inspect
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.params import Depends as DependsParam
from fastapi.testclient import TestClient
import pytest

import app as app_package
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_methods,
    route_path,
)
import app.main as app_main
from app.routers import api_key as canonical_api_key
import legacy_app

REPO_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_PROTECTED_ROUTES = frozenset(
    {
        ("POST", "/api/v1/export/sign"),
        ("GET", "/api/v1/plan/week/export.csv"),
        ("GET", "/api/v1/plan/week/export.pdf"),
        ("POST", "/api/v1/premium/bmr"),
        ("POST", "/api/v1/premium/gaps"),
        ("POST", "/api/v1/premium/plan/week"),
        ("POST", "/api/v1/premium/plate"),
        ("POST", "/api/v1/premium/targets"),
        ("PATCH", "/api/v1/restaurants/submissions/{submission_id}/status"),
        ("GET", "/api/v1/shoplist"),
        ("GET", "/api/v1/shoplist/export.csv"),
        ("GET", "/api/v1/shoplist/export.pdf"),
        ("POST", "/premium_targets"),
    }
)
_CONDITIONAL_PROTECTED_ROUTES = frozenset(
    (method, path) for path, method, _include_in_schema in app_main._LEGACY_EXPORT_ALIAS_ROUTE_SPECS
)


def _matching_routes(method: str, path: str) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(app_main.app.routes)
        if is_api_route_candidate(route)
        and route_path(route) == path
        and method in route_methods(route)
    ]


def _dependency_calls_by_identity(route: object) -> tuple[object, ...]:
    roots = [
        getattr(route, "dependant", None),
        getattr(getattr(route, "original_route", None), "dependant", None),
    ]
    stack = [root for root in roots if root is not None]
    seen: set[int] = set()
    calls: list[object] = []
    while stack:
        dependant = stack.pop()
        if id(dependant) in seen:
            continue
        seen.add(id(dependant))
        call = getattr(dependant, "call", None)
        if callable(call):
            calls.append(call)
        stack.extend(getattr(dependant, "dependencies", ()) or ())
    return tuple(calls)


def test_api_key_dependencies_have_one_canonical_owner_and_exact_aliases() -> None:
    assert canonical_api_key.get_api_key.__module__ == "app.routers.api_key"
    assert canonical_api_key._get_api_key_dynamic.__module__ == "app.routers.api_key"
    assert app_package.get_api_key is canonical_api_key.get_api_key
    assert legacy_app.get_api_key is canonical_api_key.get_api_key
    assert app_package._get_api_key_dynamic is canonical_api_key._get_api_key_dynamic
    assert legacy_app._get_api_key_dynamic is canonical_api_key._get_api_key_dynamic


@pytest.mark.parametrize(
    (
        "environment",
        "submitted",
        "expected_result",
        "expected_detail",
        "warning_expected",
    ),
    [
        pytest.param(
            {"APP_ENV": "dev", "API_KEY": "configured"},  # pragma: allowlist secret
            "configured",
            "configured",
            None,
            True,
            id="configured-exact",
        ),
        pytest.param(
            {"APP_ENV": "dev", "API_KEY": "configured"},  # pragma: allowlist secret
            "wrong-value",
            None,
            "Invalid API Key",
            True,
            id="configured-invalid",
        ),
        pytest.param(
            {"APP_ENV": "dev"},
            None,
            None,
            "Missing API Key",
            True,
            id="developer-missing",
        ),
        pytest.param(
            {"APP_ENV": "dev", "API_KEY_REQUIRED": "true"},  # pragma: allowlist secret
            "acceptable-token",
            None,
            "API key required but not configured",
            True,
            id="required-without-configured-key",
        ),
        pytest.param(
            {"APP_ENV": "production"},
            "acceptable-token",
            None,
            "API key required but not configured",
            False,
            id="production-fail-closed",
        ),
        pytest.param(
            {"APP_ENV": "staging", "ENVIRONMENT": "dev"},
            "acceptable-token",
            None,
            "API key required but not configured",
            False,
            id="production-like-app-env-wins",
        ),
        pytest.param(
            {"APP_ENV": "dev", "ENVIRONMENT": "production"},
            "acceptable-token",
            None,
            "API key required but not configured",
            False,
            id="environment-wins-over-non-production-app-env",
        ),
        pytest.param(
            {  # pragma: allowlist secret
                "ENVIRONMENT": "dev",
                "ALLOW_DEV_API_KEY": "false",  # pragma: allowlist secret
            },
            "acceptable-token",
            None,
            "API key required but not configured",
            False,
            id="developer-leniency-disabled",
        ),
        pytest.param(
            {"ENVIRONMENT": "dev"},
            "wrong",
            None,
            "Invalid API Key",
            True,
            id="developer-forbidden-token",
        ),
        pytest.param(
            {"ENVIRONMENT": "dev", "API_KEY": "abc_def"},  # pragma: allowlist secret
            "abc-def",
            None,
            "Invalid API Key",
            True,
            id="normalization-disabled",
        ),
        pytest.param(
            {
                "ENVIRONMENT": "dev",
                "API_KEY": "abc_def",  # pragma: allowlist secret
                "ALLOW_DEV_API_KEY_NORMALIZE": "true",  # pragma: allowlist secret
            },
            "abc-def",
            "abc_def",
            None,
            True,
            id="normalization-enabled",
        ),
        pytest.param(
            {"ENVIRONMENT": "dev"},
            "  acceptable-token  ",
            "acceptable-token",
            None,
            True,
            id="developer-token-trimmed",
        ),
    ],
)
def test_get_api_key_exact_behavior_matrix(
    environment: dict[str, str],
    submitted: str | None,
    expected_result: str | None,
    expected_detail: str | None,
    warning_expected: bool,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    for name in (
        "APP_ENV",
        "ENVIRONMENT",
        "API_KEY",
        "API_KEY_REQUIRED",
        "ALLOW_DEV_API_KEY",
        "ALLOW_DEV_API_KEY_NORMALIZE",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    canonical_api_key._reset_lenient_mode_warning_for_tests()
    caplog.clear()

    try:
        with caplog.at_level("WARNING", logger="app.routers.api_key"):
            if expected_detail is None:
                assert canonical_api_key.get_api_key(submitted) == expected_result
            else:
                with pytest.raises(HTTPException) as exc_info:
                    canonical_api_key.get_api_key(submitted)
                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == expected_detail
    finally:
        canonical_api_key._reset_lenient_mode_warning_for_tests()

    warning_count = sum(
        "Lenient API key mode enabled" in record.message for record in caplog.records
    )
    assert warning_count == int(warning_expected)


def test_all_default_protected_routes_use_canonical_dynamic_dependency() -> None:
    for method, path in sorted(_DEFAULT_PROTECTED_ROUTES):
        matching = _matching_routes(method, path)
        assert len(matching) == 1, f"expected one protected route for {method} {path}"
        assert any(
            call is canonical_api_key._get_api_key_dynamic
            for call in _dependency_calls_by_identity(matching[0])
        ), f"missing canonical API-key dependency on {method} {path}"


def test_conditional_export_aliases_use_canonical_dynamic_dependency_when_enabled() -> None:
    if not legacy_app.EXPORTS_ENABLED:
        pytest.skip("legacy export aliases are disabled by the runtime dependency profile")

    for method, path in sorted(_CONDITIONAL_PROTECTED_ROUTES):
        matching = _matching_routes(method, path)
        assert len(matching) == 1, f"expected one protected alias for {method} {path}"
        assert any(
            call is canonical_api_key._get_api_key_dynamic
            for call in _dependency_calls_by_identity(matching[0])
        ), f"missing canonical API-key dependency on {method} {path}"


def test_public_premium_bmr_exception_remains_unprotected() -> None:
    matching = _matching_routes("POST", "/premium_bmr")
    assert len(matching) == 1
    assert all(
        call is not canonical_api_key._get_api_key_dynamic
        for call in _dependency_calls_by_identity(matching[0])
    )


def test_dynamic_dependency_honors_app_facade_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replacement_calls: list[str | None] = []

    def replacement(value: str | None) -> str:
        replacement_calls.append(value)
        return "facade-override"

    monkeypatch.setattr(app_package, "get_api_key", replacement)

    assert canonical_api_key._get_api_key_dynamic("submitted") == "facade-override"
    assert replacement_calls == ["submitted"]


def test_fastapi_dependency_override_uses_canonical_callable_identity() -> None:
    target_app = FastAPI()

    @target_app.get("/protected", dependencies=[Depends(canonical_api_key._get_api_key_dynamic)])
    def protected() -> dict[str, str]:
        return {"status": "ok"}

    def override_api_key() -> str:
        return "override"

    target_app.dependency_overrides[canonical_api_key._get_api_key_dynamic] = override_api_key

    response = TestClient(target_app).get("/protected")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "guard",
    [canonical_api_key._get_api_key_dynamic, canonical_api_key.require_app_api_key],
)
def test_unexpected_guard_errors_do_not_log_exception_messages(
    guard: Callable[[str | None], str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_marker = "credential-like-secret-marker"  # pragma: allowlist secret

    class CredentialLikeError(RuntimeError):
        pass

    def fail(_value: str | None) -> str:
        raise CredentialLikeError(secret_marker)

    monkeypatch.setattr(app_package, "get_api_key", fail)

    with caplog.at_level("ERROR", logger="app.routers.api_key"):
        with pytest.raises(HTTPException) as exc_info:
            guard("submitted")

    assert exc_info.value.status_code == 500
    assert secret_marker not in caplog.text
    assert "CredentialLikeError" in caplog.text


@pytest.mark.parametrize("invalid_result", [object(), "", " ", "\t\n"])
def test_dynamic_guard_rejects_invalid_override_result_without_value_leak(
    invalid_result: object,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(app_package, "get_api_key", lambda _value: invalid_result)

    with caplog.at_level("ERROR", logger="app.routers.api_key"):
        with pytest.raises(HTTPException) as exc_info:
            canonical_api_key._get_api_key_dynamic("submitted")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Authentication service error"
    assert repr(invalid_result) not in caplog.text


def test_clean_import_process_preserves_dependency_identity_and_ownership() -> None:
    script = """
import app
import app.main as app_main
from app.routers import api_key
import legacy_app

assert app.get_api_key is api_key.get_api_key is legacy_app.get_api_key
assert app._get_api_key_dynamic is api_key._get_api_key_dynamic
assert legacy_app._get_api_key_dynamic is api_key._get_api_key_dynamic
assert api_key._get_api_key_dynamic.__module__ == "app.routers.api_key"
assert all(
    getattr(call, "__module__", None) != "legacy_app"
    for route in app_main.app.routes
    for dependant in getattr(route, "dependencies", ())
    for call in (getattr(dependant, "dependency", None),)
    if callable(call)
)
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_dynamic_dependency_signature_keeps_shared_header_contract() -> None:
    parameter = inspect.signature(canonical_api_key._get_api_key_dynamic).parameters["api_key"]
    assert isinstance(parameter.default, DependsParam)
    assert parameter.default.dependency is canonical_api_key.api_key_header
