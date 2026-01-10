# API Compatibility Policy (premium/* legacy)

**Status:** Baseline policy (PR-508)
**Time window:** 3 months from merge date (target: until 2026-04-09)

## What is "legacy" here?

Endpoints under:
- `/api/v1/premium/*`

They exist to avoid breaking already released clients, but they are not the canonical contracts.

## Canonical source of truth

OpenAPI schema generated from `app.main.app`:
- generator: `scripts/generate_openapi.py`
- CI gates: `openapi-sync` job + FE sync check

## Rules for legacy endpoints

**Allowed:**
1. **Delegation only** (compat alias -> canonical handler)
2. Mark as **deprecated** in OpenAPI where possible
3. Small adapters (e.g., POST body -> GET query mapping) to preserve behavior

**Forbidden:**
1. Adding new business logic to legacy routes
2. Changing request/response schemas in legacy without versioning plan
3. Adding new endpoints only in legacy

## Deprecation communication

- Legacy routes must be explicitly documented as deprecated.
- If/when we add response warnings:
  - Use structured format: `{code, message, severity}`.

## Removal plan

At end of the window:
1. Confirm FE + iOS migrated to canonical routes
2. Remove legacy routes in a dedicated PR with changelog and release notes
