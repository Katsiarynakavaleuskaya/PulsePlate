# ADR-002: OpenAPI Schema-only Mode (Temporary) + Exit Criteria

**Status:** Superseded (removed by PR-631; full-schema is canonical)
**Date:** 2026-02-02
**Context:** OpenAPI determinism and thin-client contract velocity.

## Anchors (stable)

- [Schema-only OpenAPI contract](#schema-only-openapi-contract)
- [Exit criteria](#exit-criteria)

## Resolution (current state)

Schema-only mode has been removed. OpenAPI generation runs in **full-schema mode** and remains deterministic.

Canonical docs for current behavior (recommended first read):
- `docs/architecture/system_overview.md#openapi-generation-mode-current`
- `docs/architecture/backend_routing_map.md#openapi-generation-behavior-important`

**Evidence (file:line):**

- Anchor (stable): `scripts/generate_openapi.py -> main()` (FULL schema mode + env pinning)
  - Evidence: `scripts/generate_openapi.py:94`
- Anchor (stable): `tests/test_openapi_determinism.py -> test_openapi_and_schema_ts_are_deterministic()`
  - Evidence: `tests/test_openapi_determinism.py:17`

## Decision (historical; pre-PR-631)

Keep a **temporary schema-only mode** for OpenAPI generation to avoid import-time ORM/model double-loading, while explicitly documenting:
- what is disabled,
- why it is disabled (technical root cause),
- and the **exit criteria** to remove schema-only mode.

## Context / Problem

OpenAPI generation must be deterministic (CI enforces this). Importing the full FastAPI app during schema generation can trigger SQLAlchemy model imports and double-load side effects (“Table already defined”), especially when routers import ORM models at module level.

## Evidence (historical implementation; no longer current)

- Prior art / original seam: see PR-630 evidence pack (kept for archaeology).
- CI determinism gate (still current):
  - Anchor (stable): `tests/test_openapi_determinism.py -> test_openapi_and_schema_ts_are_deterministic()`
  - Evidence: `tests/test_openapi_determinism.py:17`

<a id="schema-only-openapi-contract"></a>
## Schema-only OpenAPI contract (historical; removed)

This section is kept for historical context only.

Former activation relied on `PULSEPLATE_OPENAPI=1` + test env pinning. This is no longer used.

## Consequences

**Positive**
- Deterministic OpenAPI generation stays reliable (CI stays meaningful).
- Avoids import-time ORM hazards during schema generation.

**Negative**
- Contract velocity suffers: schema excludes PRO/premium/business routes in schema-only mode (by forced flags).
- Increased risk of “silent drift” for excluded endpoints.

## Exit criteria (remove schema-only mode)

<a id="exit-criteria"></a>
Schema-only mode can be removed when all are true:

1) Routers imported by `app.main:app` do **not** import SQLAlchemy models at module import time.
2) `make openapi` succeeds without forcing `FEATURE_*_ENABLED=false` in the generator.
3) `tests/test_openapi_determinism.py` remains green.

## Follow-ups (Backlog)

- ✅ Closed in PR-631; see `docs/roadmap/BACKLOG_LEDGER.md` entries for closure notes.
