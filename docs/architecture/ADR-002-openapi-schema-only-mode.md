# ADR-002: OpenAPI Schema-only Mode (Temporary) + Exit Criteria

**Status:** Proposed (PR-630 evidence pack)
**Date:** 2026-02-02
**Context:** OpenAPI determinism and thin-client contract velocity.

## Anchors (stable)

- [Schema-only OpenAPI contract](#schema-only-openapi-contract)
- [Exit criteria](#exit-criteria)

## Decision

Keep a **temporary schema-only mode** for OpenAPI generation to avoid import-time ORM/model double-loading, while explicitly documenting:
- what is disabled,
- why it is disabled (technical root cause),
- and the **exit criteria** to remove schema-only mode.

## Context / Problem

OpenAPI generation must be deterministic (CI enforces this). Importing the full FastAPI app during schema generation can trigger SQLAlchemy model imports and double-load side effects (“Table already defined”), especially when routers import ORM models at module level.

## Evidence (current implementation)

- Generator sets schema-only mode + disables some routers:
  - `scripts/generate_openapi.py:94-113`
- Schema-only is honored only in generation/test context (must not accidentally activate in prod):
  - `app/routers/pro_registration.py:26-36`
- PRO route registration avoids importing routers in schema-only mode:
  - `app/routers/pro_registration.py:76-105`
- CI determinism gate:
  - `tests/test_openapi_determinism.py:16-64`

<a id="schema-only-openapi-contract"></a>
## Schema-only OpenAPI contract (single source of truth)

This section is the **canonical documentation** for schema-only OpenAPI generation behavior.
Other docs should **link here** instead of duplicating env/flag lists.

**Activation (must all be true):**

- `PULSEPLATE_OPENAPI=1`
- `APP_ENV=test`
- `ENVIRONMENT=test`

**Generator invariants (must happen before importing `app.main:app`):**

- `PULSEPLATE_OPENAPI` **must be set before** importing `app.main:app` to prevent import-time ORM
  double-loading ("Table already defined").
- The generator pins env to a safe non-prod context:
  - `APP_ENV=test`
  - `ENVIRONMENT=test`
  - `ENABLE_TEST_ROUTES=1` (set by generator; not part of schema-only activation check)

**Forced feature flags (temporary, schema-only only):**

The generator forces these to disable routers that import SQLAlchemy models at module import time:

- `FEATURE_PREMIUM_WEEK_ENABLED=false`
- `FEATURE_BMI_PRO_ENABLED=false`
- `BUSINESS_MODULE_ENABLED=false`

**Implementation notes:**

- Activation/guard is enforced in `app/routers/pro_registration.py:_is_openapi_schema_only_mode()`; it will
  **not** activate in production unless all activation env vars are simultaneously mis-set.
- Source of truth for env/flag values is `scripts/generate_openapi.py` (sets env + flags, then imports
  `app.main:app`).

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

- Restore full OpenAPI schema (remove schema-only mode): `docs/roadmap/BACKLOG_LEDGER.md`
- Eliminate import-time ORM/model imports in routers included in OpenAPI generation: `docs/roadmap/BACKLOG_LEDGER.md`
