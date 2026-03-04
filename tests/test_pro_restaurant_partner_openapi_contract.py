from __future__ import annotations

from typing import Any

from app.main import app

PARTNER_PATHS: set[str] = {
    "/api/v1/pro/restaurants/partner/orders/preview",
    "/api/v1/pro/restaurants/partner/orders/adapt/preview",
    "/api/v1/pro/restaurants/partner/orders",
    "/api/v1/pro/restaurants/partner/orders/{order_id}",
    "/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
    "/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
    "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
    "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
}


def _schema() -> dict[str, Any]:
    return app.openapi()


def _op(path: str, method: str) -> dict[str, Any]:
    return _schema()["paths"][path][method]


def _json_schema(path: str, method: str, status_code: str) -> dict[str, Any]:
    return _op(path, method)["responses"][status_code]["content"]["application/json"]["schema"]


def test_partner_openapi_paths_are_present() -> None:
    paths = set(_schema()["paths"].keys())
    assert PARTNER_PATHS <= paths


def test_partner_openapi_security_is_api_key_on_all_operations() -> None:
    for path in sorted(PARTNER_PATHS):
        for method, operation in _schema()["paths"][path].items():
            security = operation.get("security")
            assert security == [{"APIKeyHeader": []}], f"{method.upper()} {path} missing API key"


def test_partner_openapi_response_codes_contract() -> None:
    expected_codes: dict[tuple[str, str], set[str]] = {
        ("/api/v1/pro/restaurants/partner/orders/preview", "post"): {"200", "422"},
        ("/api/v1/pro/restaurants/partner/orders/adapt/preview", "post"): {
            "200",
            "422",
            "429",
        },
        ("/api/v1/pro/restaurants/partner/orders", "post"): {"200", "201", "409", "422"},
        ("/api/v1/pro/restaurants/partner/orders/{order_id}", "get"): {
            "200",
            "403",
            "404",
            "410",
            "422",
        },
        ("/api/v1/pro/restaurants/partner/orders/{order_id}/confirm", "post"): {
            "200",
            "403",
            "404",
            "409",
            "410",
            "422",
        },
        ("/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares", "post"): {
            "201",
            "403",
            "404",
            "422",
        },
        ("/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status", "get"): {
            "200",
            "403",
            "404",
            "410",
            "422",
        },
        ("/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke", "post"): {
            "200",
            "403",
            "404",
            "422",
        },
    }
    for (path, method), expected in expected_codes.items():
        actual = set(_op(path, method)["responses"].keys())
        assert actual == expected, f"{method.upper()} {path} responses mismatch"


def test_partner_openapi_request_body_schemas() -> None:
    assert (
        _op("/api/v1/pro/restaurants/partner/orders/preview", "post")["requestBody"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/PartnerOrderPreviewRequest"
    )
    assert (
        _op("/api/v1/pro/restaurants/partner/orders/adapt/preview", "post")["requestBody"][
            "content"
        ]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PartnerOrderWeeklyAdapterRequest"
    )
    assert (
        _op("/api/v1/pro/restaurants/partner/orders", "post")["requestBody"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/PartnerOrderCreateRequest"
    )
    assert (
        _op("/api/v1/pro/restaurants/partner/orders/{order_id}/confirm", "post")["requestBody"][
            "content"
        ]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PartnerOrderConfirmRequest"
    )
    assert (
        _op(
            "/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
            "post",
        )[
            "requestBody"
        ]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PartnerHandoffShareIssueRequest"
    )


def test_partner_openapi_response_schemas_contract() -> None:
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/preview", "post", "200") == {
        "$ref": "#/components/schemas/PartnerOrderPreviewResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/preview", "post", "422") == {
        "$ref": "#/components/schemas/PartnerOrderErrorResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/adapt/preview", "post", "200") == {
        "$ref": "#/components/schemas/PartnerOrderPreviewResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/adapt/preview", "post", "422") == {
        "$ref": "#/components/schemas/PartnerOrderErrorResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/adapt/preview", "post", "429") == {
        "$ref": "#/components/schemas/RateLimitErrorResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders", "post", "201") == {
        "$ref": "#/components/schemas/PartnerOrderResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders", "post", "200") == {
        "$ref": "#/components/schemas/PartnerOrderResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders", "post", "409") == {
        "$ref": "#/components/schemas/PartnerOrderErrorResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders", "post", "422") == {
        "$ref": "#/components/schemas/PartnerOrderErrorResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/{order_id}", "get", "200") == {
        "$ref": "#/components/schemas/PartnerOrderResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/{order_id}", "get", "403") == {
        "$ref": "#/components/schemas/PartnerOrderErrorResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/{order_id}", "get", "404") == {
        "$ref": "#/components/schemas/PartnerOrderErrorResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/{order_id}", "get", "410") == {
        "$ref": "#/components/schemas/PartnerOrderErrorResponse"
    }
    assert _json_schema("/api/v1/pro/restaurants/partner/orders/{order_id}", "get", "422") == {
        "$ref": "#/components/schemas/HTTPValidationError"
    }
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        "post",
        "200",
    ) == {"$ref": "#/components/schemas/PartnerOrderResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        "post",
        "403",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        "post",
        "404",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        "post",
        "409",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        "post",
        "410",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        "post",
        "422",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        "post",
        "201",
    ) == {"$ref": "#/components/schemas/PartnerHandoffShareResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        "post",
        "403",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        "post",
        "404",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}

    issue_422 = _json_schema(
        "/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        "post",
        "422",
    )
    assert "oneOf" in issue_422
    issue_422_refs = {entry.get("$ref") for entry in issue_422["oneOf"]}
    assert issue_422_refs == {
        "#/components/schemas/PartnerOrderErrorResponse",
        "#/components/schemas/HTTPValidationError",
    }

    assert _json_schema(
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        "get",
        "200",
    ) == {"$ref": "#/components/schemas/PartnerHandoffShareResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        "get",
        "403",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        "get",
        "404",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        "get",
        "410",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        "get",
        "422",
    ) == {"$ref": "#/components/schemas/HTTPValidationError"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
        "post",
        "200",
    ) == {"$ref": "#/components/schemas/PartnerHandoffShareResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
        "post",
        "403",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
        "post",
        "404",
    ) == {"$ref": "#/components/schemas/PartnerOrderErrorResponse"}
    assert _json_schema(
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
        "post",
        "422",
    ) == {"$ref": "#/components/schemas/HTTPValidationError"}


def test_partner_openapi_component_schemas_exist() -> None:
    schemas = set(_schema()["components"]["schemas"].keys())
    required = {
        "HTTPValidationError",
        "PartnerHandoffShareIssueRequest",
        "PartnerHandoffShareResponse",
        "PartnerOrderConfirmRequest",
        "PartnerOrderCreateRequest",
        "PartnerOrderErrorResponse",
        "PartnerOrderPreviewRequest",
        "PartnerOrderWeeklyAdapterRequest",
        "PartnerOrderPreviewResponse",
        "PartnerOrderResponse",
        "RateLimitErrorResponse",
    }
    assert required <= schemas
