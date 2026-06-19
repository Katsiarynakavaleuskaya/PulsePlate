from __future__ import annotations

from fastapi import FastAPI

from tests.security._api_authz_contracts import (
    API_AUTHZ_CONTRACTS,
    CONTRACT_BY_KEY,
    EXPECTED_DEPENDENCY_BY_AUTH_CLASS,
    ApiExposure,
    OwnershipPolicy,
    _contains_dependency,
    _flatten_dependency_calls,
    _load_routes,
    routes_by_key,
    sensitive_route_keys,
)


def _has_object_identifier(path: str) -> bool:
    object_params = {
        "activation_id",
        "intent_id",
        "order_id",
        "share_id",
        "submission_id",
        "user_id",
        "plan_id",
    }
    return any(f"{{{param}}}" in path for param in object_params)


def test_sensitive_api_routes_are_registered_in_authz_contract_pack(app: FastAPI) -> None:
    routes = _load_routes(app)
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


def test_contract_exposure_matches_live_openapi_visibility(app: FastAPI) -> None:
    grouped_routes = routes_by_key(_load_routes(app))
    mismatches: list[str] = []

    for contract in API_AUTHZ_CONTRACTS:
        expected_visible = contract.exposure in {
            ApiExposure.PUBLIC_OPENAPI,
            ApiExposure.DEPRECATED_ALIAS,
        }
        for route in grouped_routes[contract.key]:
            if bool(route.include_in_schema) != expected_visible:
                mismatches.append(
                    f"{contract.method} {contract.path}: "
                    f"expected include_in_schema={expected_visible}, "
                    f"got {route.include_in_schema}"
                )

    assert not mismatches, "OpenAPI exposure drift:\n" + "\n".join(mismatches)


def test_contract_auth_classes_match_live_dependency_graph(app: FastAPI) -> None:
    grouped_routes = routes_by_key(_load_routes(app))
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


def test_object_identifier_routes_have_non_empty_ownership_policy() -> None:
    object_routes_without_policy = [
        contract
        for contract in API_AUTHZ_CONTRACTS
        if _has_object_identifier(contract.path)
        and contract.ownership_policy is OwnershipPolicy.NONE
    ]

    assert (
        not object_routes_without_policy
    ), "Object identifier routes must classify ownership policy:\n" + "\n".join(
        f"{contract.method} {contract.path}" for contract in object_routes_without_policy
    )


def test_foreign_object_routes_document_negative_status() -> None:
    missing_status = [
        contract
        for contract in API_AUTHZ_CONTRACTS
        if contract.ownership_policy is OwnershipPolicy.AUTHENTICATED_SUBJECT
        and _has_object_identifier(contract.path)
        and contract.foreign_object_status is None
    ]

    assert (
        not missing_status
    ), "Subject-owned object routes must document foreign-object status evidence:\n" + "\n".join(
        f"{contract.method} {contract.path}" for contract in missing_status
    )
