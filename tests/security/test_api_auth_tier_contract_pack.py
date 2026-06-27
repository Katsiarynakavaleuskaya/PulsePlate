from __future__ import annotations

import re

import pytest
from fastapi import FastAPI

from app.main import _TEST_ROUTE_SPECS
from tests.security._api_authz_contracts import (
    API_AUTHZ_CONTRACTS,
    CONTRACT_BY_KEY,
    EXPECTED_DEPENDENCY_BY_AUTH_CLASS,
    ApiExposure,
    AuthClass,
    MinimumTier,
    OwnershipPolicy,
    PrincipalSource,
    _contains_dependency,
    _flatten_dependency_calls,
    _load_routes,
    routes_by_key,
    sensitive_route_keys,
)


@pytest.fixture
def contract_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("APP_ENV", "test")

    import app.main as app_main

    return app_main.ensure_canonical_app_bootstrap(app_main.app)


def _path_parameters(path: str) -> set[str]:
    return set(re.findall(r"{([^{}]+)}", path))


def _has_path_parameter(path: str) -> bool:
    return bool(_path_parameters(path))


def _has_foreign_object_parameter(path: str) -> bool:
    return any(param.endswith("_id") for param in _path_parameters(path))


def test_sensitive_api_routes_are_registered_in_authz_contract_pack(
    contract_app: FastAPI,
) -> None:
    routes = _load_routes(contract_app)
    live_sensitive_keys = sensitive_route_keys(routes)

    missing_contracts = sorted(live_sensitive_keys - set(CONTRACT_BY_KEY))
    stale_contracts = sorted(set(CONTRACT_BY_KEY) - live_sensitive_keys)

    assert not missing_contracts, (
        "Sensitive API routes must be classified in tests/security/_api_authz_contracts.py:\n"
        + "\n".join(f"{method} {path}" for method, path in missing_contracts)
    )
    assert (
        not stale_contracts
    ), "Authz contract entries no longer map to live FastAPI routes:\n" + "\n".join(
        f"{method} {path}" for method, path in stale_contracts
    )


def test_authz_contracts_are_unique_by_method_and_path() -> None:
    keys = [contract.key for contract in API_AUTHZ_CONTRACTS]
    duplicates = sorted(key for key in set(keys) if keys.count(key) > 1)

    assert (
        not duplicates
    ), "Authz contract registry must classify each method/path exactly once:\n" + "\n".join(
        f"{method} {path}" for method, path in duplicates
    )


def test_hidden_mutating_test_routes_are_classified_as_non_production() -> None:
    hidden_mutating_test_route_keys = {
        (method, path)
        for path, method, include_in_schema in _TEST_ROUTE_SPECS
        if not include_in_schema and method in {"POST", "PUT", "PATCH", "DELETE"}
    }
    assert hidden_mutating_test_route_keys

    for key in hidden_mutating_test_route_keys:
        contract = CONTRACT_BY_KEY[key]
        assert contract.auth_class is AuthClass.NON_PRODUCTION_TEST_GUARD
        assert contract.minimum_tier is MinimumTier.NONE
        assert contract.principal_source is PrincipalSource.INTERNAL_OPTIONAL
        assert contract.ownership_policy is OwnershipPolicy.INTERNAL_OPTIONAL
        assert contract.exposure is ApiExposure.HIDDEN_RUNTIME
        assert EXPECTED_DEPENDENCY_BY_AUTH_CLASS[contract.auth_class] is not None


def test_contract_exposure_matches_live_openapi_visibility(contract_app: FastAPI) -> None:
    grouped_routes = routes_by_key(_load_routes(contract_app))
    openapi_paths = contract_app.openapi().get("paths", {})
    mismatches: list[str] = []

    for contract in API_AUTHZ_CONTRACTS:
        expected_visible = contract.exposure in {
            ApiExposure.PUBLIC_OPENAPI,
            ApiExposure.DEPRECATED_ALIAS,
        }
        for route in grouped_routes[contract.key]:
            actual_visible = bool(route.include_in_schema)
            if not expected_visible and actual_visible:
                actual_visible = contract.method.lower() in openapi_paths.get(contract.path, {})
            if actual_visible != expected_visible:
                mismatches.append(
                    f"{contract.method} {contract.path}: "
                    f"expected include_in_schema={expected_visible}, "
                    f"got {route.include_in_schema}"
                )

    assert not mismatches, "OpenAPI exposure drift:\n" + "\n".join(mismatches)


def test_contract_auth_classes_match_live_dependency_graph(contract_app: FastAPI) -> None:
    grouped_routes = routes_by_key(_load_routes(contract_app))
    missing: list[str] = []

    for contract in API_AUTHZ_CONTRACTS:
        expected_dependency = EXPECTED_DEPENDENCY_BY_AUTH_CLASS[contract.auth_class]
        if expected_dependency is None:
            continue
        for route in grouped_routes[contract.key]:
            flattened_calls = _flatten_dependency_calls(route)
            if not _contains_dependency(flattened_calls, expected_dependency):
                names = ", ".join(
                    getattr(call, "__name__", type(call).__name__) for call in flattened_calls
                )
                missing.append(
                    f"{contract.method} {contract.path} missing "
                    f"{getattr(expected_dependency, '__name__', type(expected_dependency).__name__)}; "
                    f"got [{names}]"
                )

    assert not missing, "Auth dependency drift:\n" + "\n".join(missing)


def test_path_parameter_routes_have_non_empty_ownership_policy() -> None:
    path_parameter_routes_without_policy = [
        contract
        for contract in API_AUTHZ_CONTRACTS
        if _has_path_parameter(contract.path) and contract.ownership_policy is OwnershipPolicy.NONE
    ]

    assert (
        not path_parameter_routes_without_policy
    ), "Path-parameter routes must classify ownership policy:\n" + "\n".join(
        f"{contract.method} {contract.path}" for contract in path_parameter_routes_without_policy
    )


def test_foreign_object_routes_document_negative_status() -> None:
    policies_requiring_foreign_object_status = {
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
        OwnershipPolicy.ISSUER_SCOPED,
        OwnershipPolicy.LEGACY_HIDDEN,
    }
    missing_status = [
        contract
        for contract in API_AUTHZ_CONTRACTS
        if contract.ownership_policy in policies_requiring_foreign_object_status
        and _has_foreign_object_parameter(contract.path)
        and contract.foreign_object_status is None
    ]

    assert (
        not missing_status
    ), "Foreign-object routes must document negative status evidence:\n" + "\n".join(
        f"{contract.method} {contract.path}" for contract in missing_status
    )
