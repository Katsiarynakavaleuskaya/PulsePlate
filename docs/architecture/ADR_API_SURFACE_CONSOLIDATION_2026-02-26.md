# ADR: API Surface Consolidation (2026-02-26)

## Status
Accepted

## Context
Public API surface drifted across mixed namespaces (`/api/v1/foods/*`, `/api/v1/restaurants/*`, `/api/v1/premium/*`, root utility paths). This creates schema instability for generated clients and weakens tier governance.

Current strategy keeps runtime backward compatibility while restoring canonical public namespaces for schema-driven clients.

## Decision
Canonical public API namespaces are strictly:
- `/api/v1/bmi/*` (FREE)
- `/api/v1/pro/*` (PRO)
- `/api/v1/vip/*` (VIP)

Transitional legacy namespaces:
- `/api/v1/foods/*`
- `/api/v1/restaurants/*`
- `/ws`

Rules for transitional endpoints:
- They may remain available at runtime for compatibility.
- They must not appear in OpenAPI public schema.
- They must be treated as deprecated surface and migrated/removed in follow-up PRs.

## Rationale
- Protects product tier discipline (FREE/PRO/VIP).
- Prevents OpenAPI drift and accidental client generation from legacy namespaces.
- Reduces risk of uncontrolled route growth.
- Preserves runtime stability by avoiding hard endpoint removals in the same step.

## Consequences
- New public endpoints must be added only under canonical namespaces.
- OpenAPI namespace guards are mandatory in tests.
- Legacy food/restaurant routers stay runtime-available but hidden from schema.
- WebSocket migration to `/api/v1/pro/ws` is tracked as follow-up (`P0-2 WS namespace migration`).

## Validation
- Guard test: `tests/test_openapi_namespace_guards.py`
- Determinism: `tests/test_openapi_determinism.py`
- OpenAPI generation/check: `make openapi && make openapi-check`
