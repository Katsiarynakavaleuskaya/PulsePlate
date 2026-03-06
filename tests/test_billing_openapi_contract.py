from __future__ import annotations

from typing import Any

import app
from app.main import app as canonical_app


def _paths() -> dict[str, Any]:
    return canonical_app.openapi()["paths"]


def _op(path: str, method: str) -> dict[str, Any]:
    paths = _paths()
    assert path in paths, f"Missing path in OpenAPI: {path}"
    assert method in paths[path], f"Missing method {method} for path {path}"
    op_data: dict[str, Any] = paths[path][method]
    return op_data


def test_billing_paths_registered_in_openapi() -> None:
    paths = _paths()
    assert "/api/v1/pro/payments/apple/verify-receipt" in paths
    assert "/api/v1/pro/payments/ru-by/manual-intent" in paths
    assert "/api/v1/pro/payments/ru-by/reconcile" in paths
    assert "/api/v1/pro/payments/ru-by/reconcile/{intent_id}" in paths


def test_billing_request_schema_refs() -> None:
    apple_ref = _op("/api/v1/pro/payments/apple/verify-receipt", "post")["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    manual_ref = _op("/api/v1/pro/payments/ru-by/manual-intent", "post")["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    reconcile_ref = _op("/api/v1/pro/payments/ru-by/reconcile", "post")["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert apple_ref == "#/components/schemas/AppleReceiptVerificationRequest"
    assert manual_ref == "#/components/schemas/ManualRailIntentRequest"
    assert reconcile_ref == "#/components/schemas/ManualRailReconcileRequest"


def test_billing_security_contract_uses_api_key_header() -> None:
    security = _op("/api/v1/pro/payments/apple/verify-receipt", "post")["security"]
    assert {"APIKeyHeader": []} in security


def test_manual_intent_source_is_manual_only_in_openapi() -> None:
    schema = _op("/api/v1/pro/payments/ru-by/manual-intent", "post")["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert schema["$ref"] == "#/components/schemas/ManualRailIntentRequest"

    components = canonical_app.openapi()["components"]["schemas"]
    manual_schema = components["ManualRailIntentRequest"]
    source_prop = manual_schema["properties"]["source"]
    assert source_prop["$ref"] == "#/components/schemas/ManualPaymentSource"


def test_reconcile_422_openapi_allows_validation_and_domain_errors() -> None:
    responses = _op("/api/v1/pro/payments/ru-by/reconcile", "post")["responses"]
    schema = responses["422"]["content"]["application/json"]["schema"]
    refs = {entry["$ref"] for entry in schema["oneOf"]}
    assert "#/components/schemas/HTTPValidationError" in refs
    assert "#/components/schemas/PaymentErrorResponse" in refs
