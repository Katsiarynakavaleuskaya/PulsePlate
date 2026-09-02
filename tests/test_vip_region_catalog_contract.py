"""Bounded runtime and OpenAPI contract tests for VIP regional catalogs."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.effective_routes import (
    iter_effective_route_candidates,
    route_methods,
    route_path,
)
from app.main import app as canonical_app
from app.routers.vip import router as vip_router
from app.schemas.vip import (
    VipPriceComparisonErrorResponse,
    VipPriceComparisonResponse,
    VipPriceComparisonSuccessResponse,
    VipRegionCategoriesErrorResponse,
    VipRegionCategoriesResponse,
    VipRegionCategoriesSuccessResponse,
    VipRegionSearchErrorResponse,
    VipRegionSearchResponse,
    VipRegionSearchSuccessResponse,
    VipRegionsErrorResponse,
    VipRegionsResponse,
    VipRegionsSuccessResponse,
    VipRegionStoresErrorResponse,
    VipRegionStoresResponse,
    VipRegionStoresSuccessResponse,
)
from core.region_catalog import RegionalProduct, RegionCatalog
from tests._route_patch import patch_route_dependency

_RAW_PROVIDER_SENTINEL = "raw-provider-secret:/tmp/vip-region-catalog"
_MALFORMED_SUCCESS_TOKEN = "not-an-integer-total-count"

_MILK_PRODUCT: dict[str, object] = {
    "product_id": "5",
    "name_es": "Leche",
    "name_en": "Milk",
    "category": "dairy",
    "unit": "ml",
    "typical_package_size": 1000.0,
    "price_eur": 0.95,
    "price_usd": None,
    "store_chain": "Día",
    "region": "Valencia",
}

_NULL_COMPARISON_ENTRY: dict[str, object] = {
    "product_id": None,
    "name_es": None,
    "name_en": None,
    "category": None,
    "unit": None,
    "typical_package_size": None,
    "price_eur": None,
    "price_usd": None,
    "store_chain": None,
    "region": None,
}

_REGIONS_SUCCESS: dict[str, object] = {
    "status": "success",
    "regions": ["ES", "US"],
    "total_regions": 2,
    "message": "Available regions retrieved successfully",
    "echo": {},
}

_SEARCH_SUCCESS: dict[str, object] = {
    "status": "success",
    "region": "ES",
    "query": "milk",
    "category": "",
    "products": [_MILK_PRODUCT],
    "total_count": 1,
    "returned_count": 1,
    "message": "Found 1 products in ES",
}

_CATEGORIES_SUCCESS: dict[str, object] = {
    "status": "success",
    "region": "ES",
    "categories": [
        "bakery",
        "dairy",
        "fish",
        "fruits",
        "grains",
        "meat",
        "oils",
        "protein",
        "vegetables",
    ],
    "total_categories": 9,
    "message": "Retrieved 9 categories for ES",
}

_STORES_SUCCESS: dict[str, object] = {
    "status": "success",
    "region": "ES",
    "stores": [
        "Alcampo",
        "Carrefour",
        "Consum",
        "Día",
        "El Corte Inglés",
        "Eroski",
        "Hipercor",
        "Lidl",
        "Mercadona",
    ],
    "total_stores": 9,
    "message": "Retrieved 9 store chains for ES",
}

_COMPARISON_SUCCESS: dict[str, object] = {
    "status": "success",
    "product_name": "milk",
    "regions": ["ES", "US"],
    "comparison": {
        "ES": _MILK_PRODUCT,
        "US": _NULL_COMPARISON_ENTRY,
    },
    "message": "Price comparison for 'milk' across 2 regions",
}

_COMPARISON_DEDUPE_CASES: tuple[tuple[str, list[str], list[str]], ...] = (
    ("ES,es", ["ES"], ["ES"]),
    (" ES , ES ", ["ES"], ["ES"]),
    ("XX,xx", ["XX"], []),
    ("ES,US", ["ES", "US"], ["ES", "US"]),
)


def _json_payload(response: Any) -> dict[str, Any]:
    """Parse a response only after proving the JSON media contract."""

    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def _catalog_with_milk() -> RegionCatalog:
    """Return one deterministic catalog for normalization unit tests."""

    catalog = RegionCatalog(data_dir="missing-region-catalog-fixture")
    catalog.regions = {
        "es": [
            RegionalProduct(
                product_id="5",
                name_es="Leche",
                name_en="Milk",
                category="dairy",
                unit="ml",
                typical_package_size=1000.0,
                price_eur=0.95,
                store_chain="Día",
                region="Valencia",
            )
        ],
        "us": [],
    }
    return catalog


def _raise_provider_error(*args: object, **kwargs: object) -> object:
    """Raise one uniquely identifiable provider failure for hygiene assertions."""

    del args, kwargs
    raise RuntimeError(_RAW_PROVIDER_SENTINEL)


class _MalformedSearchResult:
    """Provider result whose formatting succeeds but response validation must fail."""

    products: tuple[object, ...] = ()
    total_count = _MALFORMED_SUCCESS_TOKEN


def _malformed_search_success(
    query: str,
    region: str,
    category: str | None,
    max_results: int,
) -> _MalformedSearchResult:
    del query, region, category, max_results
    return _MalformedSearchResult()


class _AlwaysInvalidSuccessModel:
    """Replacement success model that deterministically raises ValidationError."""

    @classmethod
    def model_validate(cls, value: object) -> object:
        del cls, value
        return VipRegionsSuccessResponse.model_validate({"status": "success"})


def test_region_lookup_normalizes_every_catalog_consumer() -> None:
    catalog = _catalog_with_milk()

    assert [product.product_id for product in catalog.search_products("milk", " ES ").products] == [
        "5"
    ]
    assert catalog.get_product_by_id("5", "ES") is not None
    assert [
        product.product_id for product in catalog.get_products_by_category(" DAIRY ", " ES ")
    ] == ["5"]
    assert catalog.get_products_by_category("   ", "ES") == []
    assert catalog.get_store_chains(" ES ") == ["Día"]
    assert catalog.get_categories("ES") == ["dairy"]


@pytest.mark.parametrize("category", [None, "", "   "])
def test_optional_blank_search_category_means_no_filter(category: str | None) -> None:
    result = _catalog_with_milk().search_products("milk", "ES", category=category)

    assert result.total_count == 1
    assert [product.product_id for product in result.products] == ["5"]


def test_explicit_search_category_remains_case_insensitive_and_filtering() -> None:
    catalog = _catalog_with_milk()

    assert catalog.search_products("milk", "ES", category=" DAIRY ").total_count == 1
    assert catalog.search_products("milk", "ES", category="meat").total_count == 0


def test_real_es_catalog_finds_milk_without_category() -> None:
    result = RegionCatalog().search_products("milk", "ES")

    assert result.total_count == 1
    assert result.products[0].product_id == "5"


def test_unknown_region_remains_a_deterministic_empty_result() -> None:
    catalog = _catalog_with_milk()

    result = catalog.search_products("milk", " unknown ")
    assert result.products == []
    assert result.total_count == 0
    assert result.region == " unknown "
    assert catalog.get_product_by_id("5", "unknown") is None
    assert catalog.get_products_by_category("dairy", "unknown") == []
    assert catalog.get_store_chains("unknown") == []
    assert catalog.get_categories("unknown") == []


def test_price_comparison_normalizes_lookup_and_preserves_stripped_labels() -> None:
    comparison = _catalog_with_milk().get_price_comparison("milk", [" ES ", " US "])

    assert list(comparison) == ["ES", "US"]
    assert comparison["ES"]["product"].product_id == "5"
    assert comparison["US"] == {
        "product": None,
        "price_eur": None,
        "price_usd": None,
        "store_chain": None,
        "region": None,
    }


def test_uppercase_catalog_filename_is_normalized_at_load_and_reachable_over_http(
    tmp_path: Path,
    test_client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "ES_products.csv").write_text(
        "product_id,name_es,name_en,category,unit,typical_package_size,"
        "price_eur,price_usd,store_chain,region\n"
        "5,Leche,Milk,dairy,ml,1000,0.95,,Día,Valencia\n",
        encoding="utf-8",
    )
    catalog = RegionCatalog(str(tmp_path))

    assert list(catalog.regions) == ["es"]
    assert catalog.get_available_regions() == ["es"]
    assert catalog.search_products("milk", "es").products[0].product_id == "5"
    assert catalog.search_products("milk", "ES").products[0].product_id == "5"

    patch_route_dependency(
        app=canonical_app,
        monkeypatch=monkeypatch,
        path="/api/v1/vip/regions",
        method="GET",
        symbol="get_available_regions",
        value=catalog.get_available_regions,
    )
    patch_route_dependency(
        app=canonical_app,
        monkeypatch=monkeypatch,
        path="/api/v1/vip/regions/{region}/search",
        method="GET",
        symbol="search_products",
        value=catalog.search_products,
    )

    regions_response = test_client.get("/api/v1/vip/regions", headers=vip_headers)
    lowercase_response = test_client.get(
        "/api/v1/vip/regions/es/search?query=milk",
        headers=vip_headers,
    )
    uppercase_response = test_client.get(
        "/api/v1/vip/regions/ES/search?query=milk",
        headers=vip_headers,
    )

    assert regions_response.status_code == 200
    assert _json_payload(regions_response)["regions"] == ["ES"]
    assert lowercase_response.status_code == uppercase_response.status_code == 200
    assert _json_payload(lowercase_response)["products"][0]["product_id"] == "5"
    assert _json_payload(uppercase_response)["products"][0]["product_id"] == "5"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("/api/v1/vip/regions", _REGIONS_SUCCESS),
        ("/api/v1/vip/regions/ES/search?query=milk", _SEARCH_SUCCESS),
        ("/api/v1/vip/regions/ES/categories", _CATEGORIES_SUCCESS),
        ("/api/v1/vip/regions/ES/stores", _STORES_SUCCESS),
        (
            "/api/v1/vip/regions/compare/milk?regions=ES%2CUS",
            _COMPARISON_SUCCESS,
        ),
    ],
)
def test_five_region_routes_return_exact_success_contracts(
    test_client: TestClient,
    vip_headers: dict[str, str],
    url: str,
    expected: dict[str, object],
) -> None:
    response = test_client.get(url, headers=vip_headers)

    assert response.status_code == 200
    assert _json_payload(response) == expected


@pytest.mark.parametrize(
    ("raw_regions", "expected_labels", "expected_comparison_keys"),
    _COMPARISON_DEDUPE_CASES,
)
def test_comparison_http_deduplicates_by_catalog_identity_with_first_label(
    test_client: TestClient,
    vip_headers: dict[str, str],
    raw_regions: str,
    expected_labels: list[str],
    expected_comparison_keys: list[str],
) -> None:
    response = test_client.get(
        "/api/v1/vip/regions/compare/milk",
        params={"regions": raw_regions},
        headers=vip_headers,
    )

    assert response.status_code == 200
    payload = _json_payload(response)
    assert payload["status"] == "success"
    assert payload["regions"] == expected_labels
    assert list(payload["comparison"]) == expected_comparison_keys
    assert payload["message"] == (
        f"Price comparison for 'milk' across {len(expected_labels)} regions"
    )


@pytest.mark.parametrize(
    ("raw_regions", "expected_labels", "_expected_comparison_keys"),
    _COMPARISON_DEDUPE_CASES,
)
@pytest.mark.parametrize("branch", ["success", "provider_unavailable", "internal_error"])
def test_comparison_deduped_labels_are_shared_by_provider_and_every_response_branch(
    test_client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    raw_regions: str,
    expected_labels: list[str],
    _expected_comparison_keys: list[str],
    branch: str,
) -> None:
    provider_calls: list[tuple[str, list[str]]] = []

    def comparison_provider(product_name: str, regions: list[str]) -> dict[str, object]:
        provider_calls.append((product_name, list(regions)))
        if branch == "internal_error":
            raise RuntimeError(_RAW_PROVIDER_SENTINEL)
        return {}

    patch_route_dependency(
        app=canonical_app,
        monkeypatch=monkeypatch,
        path="/api/v1/vip/regions/compare/{product_name}",
        method="GET",
        symbol="get_price_comparison",
        value=None if branch == "provider_unavailable" else comparison_provider,
    )

    response = test_client.get(
        "/api/v1/vip/regions/compare/milk",
        params={"regions": raw_regions},
        headers=vip_headers,
    )

    assert response.status_code == 200
    payload = _json_payload(response)
    assert payload["regions"] == expected_labels
    assert payload["comparison"] == {}
    if branch == "success":
        assert payload == {
            "status": "success",
            "product_name": "milk",
            "regions": expected_labels,
            "comparison": {},
            "message": f"Price comparison for 'milk' across {len(expected_labels)} regions",
        }
    elif branch == "provider_unavailable":
        message = "Price comparison provider is not available"
        assert payload == {
            "status": "error",
            "code": "price_comparison_provider_unavailable",
            "message": message,
            "detail": message,
            "error": "price_comparison_provider_unavailable",
            "product_name": "milk",
            "regions": expected_labels,
            "comparison": {},
        }
    else:
        message = "Error comparing prices"
        assert payload == {
            "status": "error",
            "code": "internal_error",
            "message": message,
            "detail": message,
            "error": "internal_error",
            "product_name": "milk",
            "regions": expected_labels,
            "comparison": {},
        }
        assert _RAW_PROVIDER_SENTINEL not in response.text

    if branch == "provider_unavailable":
        assert provider_calls == []
    else:
        assert provider_calls == [("milk", expected_labels)]


@pytest.mark.parametrize("suffix", ["search?query=milk", "categories", "stores"])
def test_uppercase_and_lowercase_region_requests_share_catalog_data_but_keep_echo(
    test_client: TestClient,
    vip_headers: dict[str, str],
    suffix: str,
) -> None:
    lowercase = test_client.get(f"/api/v1/vip/regions/es/{suffix}", headers=vip_headers)
    uppercase = test_client.get(f"/api/v1/vip/regions/ES/{suffix}", headers=vip_headers)

    assert lowercase.status_code == uppercase.status_code == 200
    lowercase_payload = _json_payload(lowercase)
    uppercase_payload = _json_payload(uppercase)
    assert lowercase_payload.pop("region") == "es"
    assert uppercase_payload.pop("region") == "ES"
    lowercase_payload.pop("message")
    uppercase_payload.pop("message")
    assert lowercase_payload == uppercase_payload


@pytest.mark.parametrize("product_name", ["search", "categories", "stores"])
def test_comparison_special_paths_dispatch_to_comparison_handler(
    test_client: TestClient,
    vip_headers: dict[str, str],
    product_name: str,
) -> None:
    response = test_client.get(
        f"/api/v1/vip/regions/compare/{product_name}",
        headers=vip_headers,
    )

    assert response.status_code == 200
    payload = _json_payload(response)
    assert payload["status"] == "success"
    assert payload["product_name"] == product_name
    assert payload["regions"] == ["es", "us"]
    assert "query" not in payload
    assert "categories" not in payload
    assert "stores" not in payload


_PROVIDER_UNAVAILABLE_CASES: tuple[tuple[str, str, str, str, dict[str, object]], ...] = (
    (
        "/api/v1/vip/regions",
        "/api/v1/vip/regions",
        "get_available_regions",
        "region_provider_unavailable",
        {"regions": []},
    ),
    (
        "/api/v1/vip/regions/{region}/search",
        "/api/v1/vip/regions/ES/search?query=milk",
        "search_products",
        "search_provider_unavailable",
        {"region": "ES", "query": "milk", "products": []},
    ),
    (
        "/api/v1/vip/regions/{region}/categories",
        "/api/v1/vip/regions/ES/categories",
        "get_region_catalog",
        "categories_provider_unavailable",
        {"region": "ES", "categories": []},
    ),
    (
        "/api/v1/vip/regions/{region}/stores",
        "/api/v1/vip/regions/ES/stores",
        "get_region_catalog",
        "stores_provider_unavailable",
        {"region": "ES", "stores": []},
    ),
    (
        "/api/v1/vip/regions/compare/{product_name}",
        "/api/v1/vip/regions/compare/milk?regions=%20ES%20%2C%20US%20",
        "get_price_comparison",
        "price_comparison_provider_unavailable",
        {"product_name": "milk", "regions": ["ES", "US"], "comparison": {}},
    ),
)

_PROVIDER_MESSAGES = {
    "region_provider_unavailable": "Region provider is not available",
    "search_provider_unavailable": "Search provider is not available",
    "categories_provider_unavailable": "Categories provider is not available",
    "stores_provider_unavailable": "Stores provider is not available",
    "price_comparison_provider_unavailable": "Price comparison provider is not available",
}


@pytest.mark.parametrize(
    ("route_path_value", "url", "symbol", "code", "extra"),
    _PROVIDER_UNAVAILABLE_CASES,
)
def test_five_region_routes_return_exact_provider_unavailable_contracts(
    test_client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    route_path_value: str,
    url: str,
    symbol: str,
    code: str,
    extra: dict[str, object],
) -> None:
    patch_route_dependency(
        app=canonical_app,
        monkeypatch=monkeypatch,
        path=route_path_value,
        method="GET",
        symbol=symbol,
        value=None,
    )

    response = test_client.get(url, headers=vip_headers)

    assert response.status_code == 200
    message = _PROVIDER_MESSAGES[code]
    assert _json_payload(response) == {
        "status": "error",
        "code": code,
        "message": message,
        "detail": message,
        "error": code,
        **extra,
    }


_INTERNAL_ERROR_CASES: tuple[tuple[str, str, str, str, dict[str, object]], ...] = (
    (
        "/api/v1/vip/regions",
        "/api/v1/vip/regions",
        "get_available_regions",
        "Error retrieving regions",
        {"regions": []},
    ),
    (
        "/api/v1/vip/regions/{region}/search",
        "/api/v1/vip/regions/ES/search?query=milk",
        "search_products",
        "Error searching products",
        {"region": "ES", "query": "milk", "products": []},
    ),
    (
        "/api/v1/vip/regions/{region}/categories",
        "/api/v1/vip/regions/ES/categories",
        "get_region_catalog",
        "Error retrieving categories",
        {"region": "ES", "categories": []},
    ),
    (
        "/api/v1/vip/regions/{region}/stores",
        "/api/v1/vip/regions/ES/stores",
        "get_region_catalog",
        "Error retrieving stores",
        {"region": "ES", "stores": []},
    ),
    (
        "/api/v1/vip/regions/compare/{product_name}",
        "/api/v1/vip/regions/compare/milk?regions=%20ES%20%2C%20US%20",
        "get_price_comparison",
        "Error comparing prices",
        {"product_name": "milk", "regions": ["ES", "US"], "comparison": {}},
    ),
)


@pytest.mark.parametrize(
    ("route_path_value", "url", "symbol", "message", "extra"),
    _INTERNAL_ERROR_CASES,
)
def test_five_region_routes_return_sanitized_internal_error_contracts(
    test_client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    route_path_value: str,
    url: str,
    symbol: str,
    message: str,
    extra: dict[str, object],
) -> None:
    patch_route_dependency(
        app=canonical_app,
        monkeypatch=monkeypatch,
        path=route_path_value,
        method="GET",
        symbol=symbol,
        value=_raise_provider_error,
    )

    response = test_client.get(url, headers=vip_headers)

    assert response.status_code == 200
    payload = _json_payload(response)
    assert payload == {
        "status": "error",
        "code": "internal_error",
        "message": message,
        "detail": message,
        "error": "internal_error",
        **extra,
    }
    assert _RAW_PROVIDER_SENTINEL not in response.text


def test_malformed_provider_success_is_not_downgraded_to_internal_error(
    test_client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_route_dependency(
        app=canonical_app,
        monkeypatch=monkeypatch,
        path="/api/v1/vip/regions/{region}/search",
        method="GET",
        symbol="search_products",
        value=_malformed_search_success,
    )

    with pytest.raises(ValidationError) as exc_info:
        test_client.get(
            "/api/v1/vip/regions/ES/search?query=milk",
            headers=vip_headers,
        )

    assert "total_count" in str(exc_info.value)
    assert _MALFORMED_SUCCESS_TOKEN in str(exc_info.value)


@pytest.mark.parametrize(
    ("route_path_value", "url", "success_model_symbol"),
    [
        (
            "/api/v1/vip/regions",
            "/api/v1/vip/regions",
            "VipRegionsSuccessResponse",
        ),
        (
            "/api/v1/vip/regions/{region}/search",
            "/api/v1/vip/regions/ES/search?query=milk",
            "VipRegionSearchSuccessResponse",
        ),
        (
            "/api/v1/vip/regions/{region}/categories",
            "/api/v1/vip/regions/ES/categories",
            "VipRegionCategoriesSuccessResponse",
        ),
        (
            "/api/v1/vip/regions/{region}/stores",
            "/api/v1/vip/regions/ES/stores",
            "VipRegionStoresSuccessResponse",
        ),
        (
            "/api/v1/vip/regions/compare/{product_name}",
            "/api/v1/vip/regions/compare/milk?regions=ES%2CUS",
            "VipPriceComparisonSuccessResponse",
        ),
    ],
)
def test_success_validation_errors_surface_from_all_five_handlers(
    test_client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    route_path_value: str,
    url: str,
    success_model_symbol: str,
) -> None:
    patch_route_dependency(
        app=canonical_app,
        monkeypatch=monkeypatch,
        path=route_path_value,
        method="GET",
        symbol=success_model_symbol,
        value=_AlwaysInvalidSuccessModel,
    )

    with pytest.raises(ValidationError):
        test_client.get(url, headers=vip_headers)


def test_vip_access_denial_keeps_exact_canonical_payload(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/vip/regions")

    assert response.status_code == 403
    assert _json_payload(response) == {"detail": "VIP access required"}


_SCHEMA_BRANCH_CASES: tuple[tuple[TypeAdapter[Any], dict[str, object], type[BaseModel]], ...] = (
    (TypeAdapter(VipRegionsResponse), _REGIONS_SUCCESS, VipRegionsSuccessResponse),
    (
        TypeAdapter(VipRegionsResponse),
        {
            "status": "error",
            "code": "internal_error",
            "message": "Error retrieving regions",
            "detail": "Error retrieving regions",
            "error": "internal_error",
            "regions": [],
        },
        VipRegionsErrorResponse,
    ),
    (
        TypeAdapter(VipRegionSearchResponse),
        _SEARCH_SUCCESS,
        VipRegionSearchSuccessResponse,
    ),
    (
        TypeAdapter(VipRegionSearchResponse),
        {
            "status": "error",
            "code": "internal_error",
            "message": "Error searching products",
            "detail": "Error searching products",
            "error": "internal_error",
            "region": "ES",
            "query": "milk",
            "products": [],
        },
        VipRegionSearchErrorResponse,
    ),
    (
        TypeAdapter(VipRegionCategoriesResponse),
        _CATEGORIES_SUCCESS,
        VipRegionCategoriesSuccessResponse,
    ),
    (
        TypeAdapter(VipRegionCategoriesResponse),
        {
            "status": "error",
            "code": "internal_error",
            "message": "Error retrieving categories",
            "detail": "Error retrieving categories",
            "error": "internal_error",
            "region": "ES",
            "categories": [],
        },
        VipRegionCategoriesErrorResponse,
    ),
    (
        TypeAdapter(VipRegionStoresResponse),
        _STORES_SUCCESS,
        VipRegionStoresSuccessResponse,
    ),
    (
        TypeAdapter(VipRegionStoresResponse),
        {
            "status": "error",
            "code": "internal_error",
            "message": "Error retrieving stores",
            "detail": "Error retrieving stores",
            "error": "internal_error",
            "region": "ES",
            "stores": [],
        },
        VipRegionStoresErrorResponse,
    ),
    (
        TypeAdapter(VipPriceComparisonResponse),
        _COMPARISON_SUCCESS,
        VipPriceComparisonSuccessResponse,
    ),
    (
        TypeAdapter(VipPriceComparisonResponse),
        {
            "status": "error",
            "code": "internal_error",
            "message": "Error comparing prices",
            "detail": "Error comparing prices",
            "error": "internal_error",
            "product_name": "milk",
            "regions": ["ES", "US"],
            "comparison": {},
        },
        VipPriceComparisonErrorResponse,
    ),
)


@pytest.mark.parametrize(("adapter", "payload", "expected_type"), _SCHEMA_BRANCH_CASES)
def test_response_aliases_accept_exact_success_and_error_branches(
    adapter: TypeAdapter[Any],
    payload: dict[str, object],
    expected_type: type[BaseModel],
) -> None:
    result = adapter.validate_python(payload)

    assert isinstance(result, expected_type)


def test_response_aliases_reject_ambiguous_or_drifting_payloads() -> None:
    missing_status = deepcopy(_REGIONS_SUCCESS)
    missing_status.pop("status")

    wrong_status = deepcopy(_REGIONS_SUCCESS)
    wrong_status["status"] = "pending"

    alias_mismatch = deepcopy(_SCHEMA_BRANCH_CASES[1][1])
    alias_mismatch["detail"] = "different"

    unknown_field = deepcopy(_REGIONS_SUCCESS)
    unknown_field["unexpected"] = True

    missing_required_nullable = deepcopy(_COMPARISON_SUCCESS)
    comparison = missing_required_nullable["comparison"]
    assert isinstance(comparison, dict)
    es_entry = comparison["ES"]
    assert isinstance(es_entry, dict)
    es_entry.pop("region")

    invalid_cases = (
        (TypeAdapter(VipRegionsResponse), missing_status),
        (TypeAdapter(VipRegionsResponse), wrong_status),
        (TypeAdapter(VipRegionsResponse), alias_mismatch),
        (TypeAdapter(VipRegionsResponse), unknown_field),
        (TypeAdapter(VipPriceComparisonResponse), missing_required_nullable),
        (TypeAdapter(VipRegionsResponse), _SEARCH_SUCCESS),
    )

    for adapter, payload in invalid_cases:
        with pytest.raises(ValidationError):
            adapter.validate_python(payload)


_OPENAPI_CASES = {
    "/api/v1/vip/regions": (
        "get_regions_api_v1_vip_regions_get",
        "VipRegionsSuccessResponse",
        "VipRegionsErrorResponse",
    ),
    "/api/v1/vip/regions/{region}/search": (
        "search_region_products_api_v1_vip_regions__region__search_get",
        "VipRegionSearchSuccessResponse",
        "VipRegionSearchErrorResponse",
    ),
    "/api/v1/vip/regions/{region}/categories": (
        "get_region_categories_api_v1_vip_regions__region__categories_get",
        "VipRegionCategoriesSuccessResponse",
        "VipRegionCategoriesErrorResponse",
    ),
    "/api/v1/vip/regions/{region}/stores": (
        "get_region_stores_api_v1_vip_regions__region__stores_get",
        "VipRegionStoresSuccessResponse",
        "VipRegionStoresErrorResponse",
    ),
    "/api/v1/vip/regions/compare/{product_name}": (
        "compare_product_prices_api_v1_vip_regions_compare__product_name__get",
        "VipPriceComparisonSuccessResponse",
        "VipPriceComparisonErrorResponse",
    ),
}


def test_openapi_exposes_exact_discriminated_contracts_and_existing_parameters() -> None:
    schema = canonical_app.openapi()

    for path, (operation_id, success_name, error_name) in _OPENAPI_CASES.items():
        path_item = schema["paths"][path]
        assert set(path_item) == {"get"}
        operation = path_item["get"]
        assert operation["operationId"] == operation_id
        response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert response_schema["oneOf"] == [
            {"$ref": f"#/components/schemas/{success_name}"},
            {"$ref": f"#/components/schemas/{error_name}"},
        ]
        assert response_schema["discriminator"] == {
            "propertyName": "status",
            "mapping": {
                "success": f"#/components/schemas/{success_name}",
                "error": f"#/components/schemas/{error_name}",
            },
        }
        assert operation["responses"]["403"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/VipAccessErrorResponse"
        }

    search_parameters = {
        parameter["name"]: parameter["schema"]
        for parameter in schema["paths"]["/api/v1/vip/regions/{region}/search"]["get"]["parameters"]
    }
    assert search_parameters["region"]["type"] == "string"
    assert search_parameters["query"]["type"] == "string"
    assert search_parameters["category"]["default"] == ""
    assert search_parameters["max_results"]["default"] == 20

    comparison_parameters = {
        parameter["name"]: parameter["schema"]
        for parameter in schema["paths"]["/api/v1/vip/regions/compare/{product_name}"]["get"][
            "parameters"
        ]
    }
    assert comparison_parameters["product_name"]["type"] == "string"
    assert comparison_parameters["regions"]["default"] == "es,us"


def test_live_and_source_route_tables_have_one_owner_and_safe_precedence() -> None:
    for path in _OPENAPI_CASES:
        matches = [
            candidate
            for candidate in iter_effective_route_candidates(canonical_app.routes)
            if route_path(candidate) == path and "GET" in route_methods(candidate)
        ]
        assert len(matches) == 1

    source_paths = [getattr(route, "path", None) for route in vip_router.routes]
    comparison_index = source_paths.index("/api/v1/vip/regions/compare/{product_name}")
    for dynamic_path in (
        "/api/v1/vip/regions/{region}/search",
        "/api/v1/vip/regions/{region}/categories",
        "/api/v1/vip/regions/{region}/stores",
    ):
        assert source_paths.count(dynamic_path) == 1
        assert comparison_index < source_paths.index(dynamic_path)


def test_generated_types_use_status_narrowable_success_error_unions() -> None:
    generated_types = Path("frontend/src/api/schema.ts").read_text(encoding="utf-8")

    for _operation_id, success_name, error_name in _OPENAPI_CASES.values():
        assert (
            f'components["schemas"]["{success_name}"] ' f'| components["schemas"]["{error_name}"]'
        ) in generated_types
    assert 'status: "success";' in generated_types
    assert 'status: "error";' in generated_types
