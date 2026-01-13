# AGENTS.md Additions: OpenAPI Stability Rules

**Date:** 2026-01-12
**Status:** 📋 Proposed additions to AGENTS.md
**Purpose:** Document OpenAPI stability policy to prevent breaking changes

---

## Proposed Additions to AGENTS.md

### Section: OpenAPI generation (determinism requirement)

**Add after existing OpenAPI section:**

---

## OpenAPI Stability Rules (PR-521)

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
- Providers exist but are not wired into runtime and are not OpenAPI consumers today; therefore they do not affect OpenAPI stability policy (see `docs/audit/PROVIDERS_IMPLEMENTATION.md` for details).

**Until conditions met:** Use vendor extensions only.

---

**See also:**
- `docs/audit/PR_521A_FINAL_PLAN.md` — frontend migration plan
- `docs/audit/PR_521B_FINAL_PLAN.md` — OpenAPI visibility plan
- `docs/contracts/OPENAPI_VISIBILITY_MATRIX.md` — visibility rules

---

**Last updated:** 2026-01-12
**Next:** Add to AGENTS.md in next docs/policy PR
