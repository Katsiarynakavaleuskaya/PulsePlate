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

## Evidence Anchors (file:line)
- OpenAPI canonical filter and temporary exact allowlist (`/api/v1/bmi`, `/ws`):
  `legacy_app.py:708`, `legacy_app.py:718`.
- OpenAPI builder installation:
  `legacy_app.py:741`.
- Legacy runtime routes kept but hidden from schema:
  `legacy_app.py:884`, `legacy_app.py:886`.
- Runtime WebSocket seam (`/ws`) remains active:
  `app/main.py:25`, `app/main.py:36`.
- Namespace guards:
  `tests/test_openapi_namespace_guards.py:39`,
  `tests/test_openapi_namespace_guards.py:45`,
  `tests/test_openapi_namespace_guards.py:51`.
- OpenAPI determinism guard:
  `tests/test_openapi_determinism.py:67`.

## Exit Criteria / Definition of Done
- [ ] `P0-2` migration merged: canonical WebSocket endpoint `/api/v1/pro/ws` is live and documented.
- [ ] Transition window closed for `/api/v1/foods/*` and `/api/v1/restaurants/*` runtime aliases (removed or redirected with documented policy).
- [ ] Namespace guards remain green after seam retirement (`tests/test_openapi_namespace_guards.py`).
- [ ] OpenAPI regeneration remains deterministic after seam retirement:
  `make openapi` and `make openapi-check`.
- [ ] Backlog closure captured in `docs/roadmap/BACKLOG_LEDGER.md` with owner, target PR, and merge evidence.

## Validation
- Guard test: `tests/test_openapi_namespace_guards.py`
- Determinism: `tests/test_openapi_determinism.py`
- OpenAPI generation/check: `make openapi && make openapi-check`
