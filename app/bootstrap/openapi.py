"""Canonical OpenAPI visibility, generation, and builder lifecycle policy."""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from typing import Any, cast

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
    route_include_in_schema,
    route_methods,
    route_path,
    route_responses,
)

_CANONICAL_BUILDER_STATE_ATTR = "_canonical_openapi_builder"
_LEGACY_BOOLEAN_MARKER_ATTR = "_canonical_openapi_builder_installed"
_INPUT_FINGERPRINT_ATTR = "_canonical_openapi_input_fingerprint"
_CANONICAL_BUILDER_PROTOCOL_VERSION = 2


@dataclass(frozen=True, slots=True)
class PublicOpenAPIPolicy:
    """Immutable allowlist for the externally documented API surface."""

    allowed_prefixes: tuple[str, ...]
    allowed_exact: frozenset[str]


PUBLIC_OPENAPI_POLICY = PublicOpenAPIPolicy(
    allowed_prefixes=(
        "/api/v1/bmi/",
        "/api/v1/billing/",
        "/api/v1/insight/",
        "/api/v1/pro/",
        "/api/v1/vip/",
    ),
    allowed_exact=frozenset({"/api/v1/bmi", "/api/v1/insight"}),
)

_OPENAPI_ALLOWED_PREFIXES = PUBLIC_OPENAPI_POLICY.allowed_prefixes
_OPENAPI_ALLOWED_EXACT = PUBLIC_OPENAPI_POLICY.allowed_exact


def _is_openapi_public_path(path: str) -> bool:
    """Return whether a path belongs to the canonical public OpenAPI surface."""

    if path in PUBLIC_OPENAPI_POLICY.allowed_exact:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_OPENAPI_POLICY.allowed_prefixes)


def _collect_schema_refs(node: Any, refs: set[str]) -> None:
    """Collect schema component names referenced from an OpenAPI subtree."""

    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            refs.add(ref.rsplit("/", 1)[-1])
        for value in node.values():
            _collect_schema_refs(value, refs)
        return

    if isinstance(node, list):
        for item in node:
            _collect_schema_refs(item, refs)


def _prune_unreferenced_schema_components(schema: dict[str, Any]) -> None:
    """Drop schemas unreachable from the filtered public OpenAPI surface."""

    components = schema.get("components")
    if not isinstance(components, dict):
        return

    schemas = components.get("schemas")
    if not isinstance(schemas, dict):
        return

    referenced_names: set[str] = set()
    schema_without_defs = dict(schema)
    if isinstance(schema_without_defs.get("components"), dict):
        component_copy = dict(cast(dict[str, Any], schema_without_defs["components"]))
        component_copy.pop("schemas", None)
        schema_without_defs["components"] = component_copy

    _collect_schema_refs(schema_without_defs, referenced_names)

    retained_schemas: dict[str, Any] = {}
    queue = list(referenced_names)
    while queue:
        schema_name = queue.pop()
        if schema_name in retained_schemas:
            continue
        schema_node = schemas.get(schema_name)
        if not isinstance(schema_node, dict):
            continue
        retained_schemas[schema_name] = schema_node
        nested_refs: set[str] = set()
        _collect_schema_refs(schema_node, nested_refs)
        queue.extend(nested_ref for nested_ref in nested_refs if nested_ref not in retained_schemas)

    components["schemas"] = dict(sorted(retained_schemas.items()))


def _generate_canonical_openapi(target_app: FastAPI) -> dict[str, Any]:
    """Build a fresh filtered schema without reading or mutating the live cache."""

    _ensure_no_webhooks(target_app)

    schema: dict[str, Any] = get_openapi(
        title=target_app.title,
        version=target_app.version,
        openapi_version=target_app.openapi_version,
        summary=target_app.summary,
        description=target_app.description,
        terms_of_service=target_app.terms_of_service,
        contact=target_app.contact,
        license_info=target_app.license_info,
        routes=target_app.routes,
        webhooks=(),
        tags=target_app.openapi_tags,
        servers=target_app.servers,
        separate_input_output_schemas=target_app.separate_input_output_schemas,
        external_docs=target_app.openapi_external_docs,
    )
    all_paths = schema.get("paths", {})
    filtered_paths = {
        path: value for path, value in all_paths.items() if _is_openapi_public_path(path)
    }
    schema["paths"] = dict(sorted(filtered_paths.items()))
    _prune_unreferenced_schema_components(schema)
    return schema


def _ensure_no_webhooks(target_app: FastAPI) -> None:
    if target_app.webhooks.routes:
        raise RuntimeError("OpenAPI builder state invalid: webhooks_not_supported")


def _routes_version(target_app: FastAPI) -> int:
    get_routes_version = getattr(target_app.router, "_get_routes_version", None)
    if not callable(get_routes_version):
        raise RuntimeError("OpenAPI builder state invalid: route_version_unavailable")
    version = get_routes_version()
    if not isinstance(version, int):
        raise RuntimeError("OpenAPI builder state invalid: route_version_invalid")
    return version


def _callable_identity(value: object) -> tuple[str, str]:
    return (
        str(getattr(value, "__module__", "")),
        str(getattr(value, "__qualname__", getattr(value, "__name__", ""))),
    )


def _openapi_input_fingerprint(target_app: FastAPI) -> str:
    """Fingerprint the bounded metadata and APIRoute inputs used by OpenAPI."""

    route_contracts: list[dict[str, Any]] = []
    for route in iter_effective_route_candidates(target_app.routes):
        if not is_api_route_candidate(route):
            continue
        owner = cast(APIRoute, getattr(route, "original_route", route))
        route_contracts.append(
            {
                "path": route_path(route),
                "methods": sorted(route_methods(route)),
                "include_in_schema": route_include_in_schema(route),
                "name": getattr(route, "name", owner.name),
                "tags": list(getattr(route, "tags", owner.tags) or ()),
                "summary": getattr(route, "summary", owner.summary),
                "description": getattr(route, "description", owner.description),
                "operation_id": getattr(route, "operation_id", owner.operation_id),
                "openapi_extra": jsonable_encoder(
                    getattr(route, "openapi_extra", owner.openapi_extra)
                ),
                "status_code": getattr(route, "status_code", owner.status_code),
                "response_status_codes": sorted(str(code) for code in route_responses(route)),
                "endpoint": _callable_identity(route_endpoint(route)),
            }
        )

    inputs = {
        "public_openapi_policy": {
            "allowed_prefixes": PUBLIC_OPENAPI_POLICY.allowed_prefixes,
            "allowed_exact": sorted(PUBLIC_OPENAPI_POLICY.allowed_exact),
        },
        "title": target_app.title,
        "version": target_app.version,
        "openapi_version": target_app.openapi_version,
        "summary": target_app.summary,
        "description": target_app.description,
        "terms_of_service": target_app.terms_of_service,
        "contact": target_app.contact,
        "license_info": target_app.license_info,
        "openapi_tags": target_app.openapi_tags,
        "servers": target_app.servers,
        "separate_input_output_schemas": target_app.separate_input_output_schemas,
        "external_docs": target_app.openapi_external_docs,
        "routes": route_contracts,
    }
    try:
        serialized = json.dumps(
            inputs,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "OpenAPI builder state invalid: input_fingerprint_unserializable"
        ) from exc
    return hashlib.sha256(serialized).hexdigest()


def _build_canonical_openapi(target_app: FastAPI) -> dict[str, Any]:
    """Return the cached schema, regenerating after recursive route changes."""

    _ensure_no_webhooks(target_app)
    routes_version = _routes_version(target_app)
    cached_version = getattr(target_app, "_openapi_routes_version", None)
    input_fingerprint = _openapi_input_fingerprint(target_app)
    cached_fingerprint = getattr(target_app, _INPUT_FINGERPRINT_ATTR, None)
    if (
        not target_app.openapi_schema
        or cached_version != routes_version
        or cached_fingerprint != input_fingerprint
    ):
        schema = _generate_canonical_openapi(target_app)
        target_app.openapi_schema = schema
        setattr(target_app, "_openapi_routes_version", routes_version)
        setattr(target_app, _INPUT_FINGERPRINT_ATTR, input_fingerprint)
    cached_schema: dict[str, Any] = target_app.openapi_schema
    return cached_schema


class _CanonicalOpenAPIBuilder:
    """Named same-app callable used as the canonical OpenAPI method."""

    _pulseplate_openapi_builder_protocol = _CANONICAL_BUILDER_PROTOCOL_VERSION

    def __init__(self, target_app: FastAPI) -> None:
        self._pulseplate_target_app = target_app

    def __call__(self) -> dict[str, Any]:
        return _build_canonical_openapi(self._pulseplate_target_app)


def _is_default_openapi_builder(target_app: FastAPI, live_builder: object) -> bool:
    return (
        inspect.ismethod(live_builder)
        and getattr(live_builder, "__self__", None) is target_app
        and getattr(live_builder, "__func__", None) is FastAPI.openapi
    )


def _is_structurally_canonical_builder(target_app: FastAPI, builder: object) -> bool:
    builder_type = type(builder)
    builder_call = getattr(builder_type, "__call__", None)
    return (
        callable(builder)
        and builder_type.__module__ == __name__
        and builder_type.__qualname__ == _CanonicalOpenAPIBuilder.__qualname__
        and getattr(builder_call, "__module__", None) == __name__
        and getattr(builder_call, "__qualname__", None)
        == _CanonicalOpenAPIBuilder.__call__.__qualname__
        and getattr(builder, "_pulseplate_openapi_builder_protocol", None)
        == _CANONICAL_BUILDER_PROTOCOL_VERSION
        and getattr(builder, "_pulseplate_target_app", None) is target_app
    )


def validate_openapi_builder_state(target_app: FastAPI) -> None:
    """Fail closed unless the live OpenAPI callable has one valid ownership state."""

    _ensure_no_webhooks(target_app)
    live_builder = target_app.openapi
    marker_present = hasattr(target_app.state, _CANONICAL_BUILDER_STATE_ATTR)
    marker = getattr(target_app.state, _CANONICAL_BUILDER_STATE_ATTR, None)
    legacy_marker_present = hasattr(target_app.state, _LEGACY_BOOLEAN_MARKER_ATTR)

    if legacy_marker_present:
        raise RuntimeError("OpenAPI builder state invalid: stale_legacy_marker")

    if not marker_present:
        if _is_default_openapi_builder(target_app, live_builder):
            return
        raise RuntimeError("OpenAPI builder state invalid: foreign_builder")

    if marker is None:
        raise RuntimeError("OpenAPI builder state invalid: canonical_marker_invalid")
    if live_builder is not marker:
        raise RuntimeError("OpenAPI builder state invalid: live_marker_mismatch")
    if not _is_structurally_canonical_builder(target_app, marker):
        raise RuntimeError("OpenAPI builder state invalid: canonical_binding_invalid")


def install_canonical_openapi_builder(target_app: FastAPI) -> None:
    """Atomically install the current builder and reconcile any existing cache."""

    validate_openapi_builder_state(target_app)
    live_builder = target_app.openapi
    marker = getattr(target_app.state, _CANONICAL_BUILDER_STATE_ATTR, None)
    default_state = marker is None
    existing_schema = target_app.openapi_schema
    candidate = _generate_canonical_openapi(target_app) if existing_schema is not None else None
    cached_version = getattr(target_app, "_openapi_routes_version", None)
    cached_fingerprint = getattr(target_app, _INPUT_FINGERPRINT_ATTR, None)
    routes_version = _routes_version(target_app)
    input_fingerprint = _openapi_input_fingerprint(target_app)
    inputs_changed = cached_version != routes_version or cached_fingerprint != input_fingerprint

    current_builder = (
        marker
        if marker is not None and type(marker) is _CanonicalOpenAPIBuilder
        else _CanonicalOpenAPIBuilder(target_app)
    )

    if existing_schema is not None and candidate is not None:
        if default_state or inputs_changed or candidate != existing_schema:
            target_app.openapi_schema = candidate

    if current_builder is not live_builder:
        setattr(target_app, "openapi", current_builder)
        setattr(target_app.state, _CANONICAL_BUILDER_STATE_ATTR, current_builder)

    setattr(target_app, "_openapi_routes_version", routes_version)
    setattr(target_app, _INPUT_FINGERPRINT_ATTR, input_fingerprint)


def apply_public_openapi_input_policy(target_app: FastAPI) -> bool:
    """Internalize legacy users metadata without mutating the OpenAPI cache."""

    changed = False
    for route in iter_effective_route_candidates(target_app.routes):
        if not route_path(route).startswith("/api/v1/users"):
            continue
        owner = getattr(route, "original_route", route)
        if bool(getattr(route, "include_in_schema", True)):
            setattr(route, "include_in_schema", False)
            changed = True
        if owner is not route and bool(getattr(owner, "include_in_schema", True)):
            setattr(owner, "include_in_schema", False)
            changed = True

    if target_app.openapi_tags:
        public_tags = [tag for tag in target_app.openapi_tags if tag.get("name") != "users"]
        if public_tags != target_app.openapi_tags:
            target_app.openapi_tags = public_tags
            changed = True

    if target_app.description:
        public_description = target_app.description.replace(", user management", "").replace(
            "User management endpoints (FREE tier)", ""
        )
        if public_description != target_app.description:
            target_app.description = public_description
            changed = True

    return changed


_install_openapi_builder = install_canonical_openapi_builder
