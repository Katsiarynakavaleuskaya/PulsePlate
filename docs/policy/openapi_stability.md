# OpenAPI Stability Policy

**Date:** 2026-01-12
**Status:** ✅ Active policy
**Purpose:** Prevent breaking changes in OpenAPI consumers (web SDK generation, unknown external clients)

---

## OpenAPI Stability Rules

### Deprecated Aliases Policy

**Rule:** Deprecated aliases (e.g., `/api/v1/premium/*`) remain in OpenAPI schema until all known clients migrate.

**Rationale:**
- ✅ Web frontend generates types from OpenAPI (`openapi.json` → `schema.ts`).
- ✅ External OpenAPI consumers are unknown.
- ✅ iOS is manual today (does not depend on OpenAPI), but schema removal is still unsafe due to the above.
- ❌ Providers are not OpenAPI consumers (not wired into runtime), so they do not affect OpenAPI stability policy.

**Implementation:**
- Use vendor extensions (`x-alias-of`, `x-migration-path`) to document canonical replacements
- Mark endpoints as `deprecated: true` but keep `include_in_schema=True` (default)
- Hide deprecated in Swagger UI (optional), but keep in schema

**Migration Order (Hard Rule):**
1. **Client migration first** (frontend/iOS migrate to canonical endpoints)
2. **Schema visibility tightening second** (vendor extensions, then optionally `include_in_schema=False`)

**Never:** Hide endpoints from schema before clients migrate (breaks SDK generation).

### When `include_in_schema=False` is Safe

**Conditions (all must be true):**
- ✅ All known clients migrated to canonical endpoints
- ✅ Web frontend migrated (uses canonical endpoints, not deprecated)
- ✅ External clients confirmed: none exist (or all migrated)
- ✅ Ready to accept: possible break of unknown external SDK generation

**Note:**
- iOS is manual today (does not depend on OpenAPI), but this alone does not justify `include_in_schema=False` because web uses OpenAPI and external consumers are unknown.
- Providers exist but are not wired into runtime and are not OpenAPI consumers today; therefore they do not affect OpenAPI stability policy (see `docs/architecture/providers_implementation.md` for details).

**Until conditions met:** Use vendor extensions only.

---

## Frontend Contracts & Types (OpenAPI)

### Canonical Sources

- **OpenAPI truth:** Backend app (`app.main.app`) is the canonical source of the OpenAPI spec.
- **Generated artifacts:** `frontend/src/api/openapi.json` and `frontend/src/api/schema.ts` are generated outputs.

### Generation Workflow (Frontend)

- **Do not edit** `frontend/src/api/openapi.json` or `frontend/src/api/schema.ts` manually.
- Regenerate via the canonical Make target: `make openapi` (do not run `scripts/generate_openapi.py` directly).
- PR rule: if backend changes any schema/route, the PR must include regenerated OpenAPI artifacts *or* an explicit note why schema is intentionally unchanged.

### Type Usage Rules

- **API types:** Must be imported from `frontend/src/api/schema.ts` (openapi-typescript output).
  - Example: `components["schemas"]["PlateResponse"]`
- **Client exports:** Production code may re-export stable aliases (e.g. `export type PlateResponse = ...`) to avoid repeating `components[...]` everywhere.
- **Mapping layers:** UI-only view models are allowed, must be explicitly named:
  - ✅ `PlateVM`, `TargetsFormModel`
  - ❌ `PlateApiResponse`, `TargetsResponse` (if it duplicates backend schema)

### Contract Drift Safeguards

- **Compile-time checks:** Add/keep `expectTypeOf()` tests against exported API types.
- **Runtime shape checks (optional):** For mocked responses in integration tests, prefer typing:
  - `const mock: PlateResponse = {...}` to fail fast on schema changes.
- **Path constants:** If an endpoint path is asserted in tests/mocks, prefer shared exported constants to prevent drift.

### Migration Rules (/premium → /pro)

- `/api/v1/premium/*` is a **deprecated namespace** (aliases).
- Canonical frontend clients must target `/api/v1/pro/*` (or `/api/v1/vip/*`) endpoints.
- During migration, `frontend/src/api/premium/*` may exist as a compatibility layer, but:
  - it must call canonical `/pro/*` paths,
  - it must not define duplicate request/response types,
  - tests should assert canonical paths.

### Breaking Change Definition (Frontend)

A frontend-breaking contract change includes:
- Schema changes in `components.schemas.*` used by the frontend,
- Path changes for endpoints consumed by the frontend,
- Behavior changes that alter error envelope or auth requirements.

---

## References

- Root: `AGENTS.md` → "OpenAPI generation (determinism requirement)"
- Frontend: `frontend/AGENTS.md`
- Contracts: `docs/contracts/OPENAPI_VISIBILITY_MATRIX.md`

---

**Last updated:** 2026-01-12
