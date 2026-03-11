from __future__ import annotations

from typing import Any


def _paths() -> dict[str, Any]:
    import app

    return app.app.openapi()["paths"]


def _op(path: str, method: str) -> dict[str, Any]:
    paths = _paths()
    assert path in paths, f"Missing path in OpenAPI: {path}"
    assert method in paths[path], f"Missing method {method} for path {path}"
    op_data: dict[str, Any] = paths[path][method]
    return op_data


def _schema(path: str, method: str, status_code: str) -> dict[str, Any]:
    op_data = _op(path, method)
    schema: dict[str, Any] = op_data["responses"][status_code]["content"]["application/json"][
        "schema"
    ]
    return schema


def test_pro_payments_paths_registered_in_openapi() -> None:
    paths = _paths()
    assert "/api/v1/pro/payments/activate" in paths
    assert "/api/v1/pro/payments/activations/{activation_id}" in paths


def test_pro_payments_response_codes_contract() -> None:
    expected = {
        ("/api/v1/pro/payments/activate", "post"): {"200", "401", "409", "422"},
        ("/api/v1/pro/payments/activations/{activation_id}", "get"): {
            "200",
            "401",
            "403",
            "404",
            "422",
        },
    }
    for (path, method), codes in expected.items():
        responses = _op(path, method)["responses"]
        assert codes.issubset(set(responses.keys()))


def test_pro_payments_request_schema_refs() -> None:
    activate_req_ref = _op("/api/v1/pro/payments/activate", "post")["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert activate_req_ref == "#/components/schemas/ActivateSubscriptionRequest"


def test_pro_payments_response_schema_refs() -> None:
    activate_schema = _schema("/api/v1/pro/payments/activate", "post", "200")
    get_schema = _schema("/api/v1/pro/payments/activations/{activation_id}", "get", "200")
    assert activate_schema == {"$ref": "#/components/schemas/SubscriptionActivationResponse"}
    assert get_schema == {"$ref": "#/components/schemas/SubscriptionActivationResponse"}


def test_pro_payments_error_schema_refs() -> None:
    payment_error_ref = "#/components/schemas/PaymentErrorResponse"
    validation_error_ref = "#/components/schemas/HTTPValidationError"

    assert _schema("/api/v1/pro/payments/activate", "post", "401")["$ref"] == payment_error_ref
    assert _schema("/api/v1/pro/payments/activate", "post", "409")["$ref"] == payment_error_ref
    assert _schema("/api/v1/pro/payments/activate", "post", "422")["$ref"] == validation_error_ref
    assert (
        _schema("/api/v1/pro/payments/activations/{activation_id}", "get", "401")["$ref"]
        == payment_error_ref
    )
    assert (
        _schema("/api/v1/pro/payments/activations/{activation_id}", "get", "403")["$ref"]
        == payment_error_ref
    )
    assert (
        _schema("/api/v1/pro/payments/activations/{activation_id}", "get", "404")["$ref"]
        == payment_error_ref
    )
    assert (
        _schema("/api/v1/pro/payments/activations/{activation_id}", "get", "422")["$ref"]
        == validation_error_ref
    )
