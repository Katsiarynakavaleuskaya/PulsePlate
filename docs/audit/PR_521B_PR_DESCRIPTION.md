# PR-521B: Backend OpenAPI Vendor Extensions

> ℹ️ This document summarizes the PR description for GitHub.
> Canonical scope, gaps, and verification live in:
> **docs/audit/PR_521B_FINAL_PLAN.md**

## Scope

**Metadata-only OpenAPI changes** — add vendor extensions (`x-alias-of`, `x-migration-path`) to deprecated premium alias endpoints to document canonical replacements.

**No runtime behavior changes.** No contract changes. OpenAPI metadata only.

---

## Changes

### Endpoints Updated

| Deprecated Alias | Canonical Endpoint | File | OpenAPI Visible |
|------------------|-------------------|------|-----------------|
| `/api/v1/premium/plate` | `/api/v1/pro/nutrition/plate` | `legacy_app.py` | ✅ Yes |
| `/api/v1/premium/targets` | `/api/v1/pro/nutrition/targets` | `legacy_app.py` | ✅ Yes |
| `/api/v1/premium/plan/week-flexible` | `/api/v1/pro/meal/weekly` | `app/routers/premium_week.py` | ⚠️ No (excluded by design) |

**Known gap:** `/api/v1/premium/plan/week-flexible` is annotated in code but excluded from generated OpenAPI due to current schema-gating (feature flag `FEATURE_PREMIUM_WEEK_ENABLED=false` in `scripts/generate_openapi.py`). This PR does not change schema inclusion policy; it only adds metadata where endpoints are present in the schema. Vendor extensions will appear in OpenAPI when this exclusion is lifted in a future PR (per current OpenAPI policy).

### Files Changed (5)

1. `app/routers/premium_week.py` — added `openapi_extra` to `/plan/week-flexible`
2. `legacy_app.py` — added `openapi_extra` to `/api/v1/premium/plate` and `/api/v1/premium/targets`
3. `frontend/src/api/openapi.json` — regenerated (includes vendor extensions for `/premium/plate` and `/premium/targets`)
4. `docs/audit/PR_521B_FINAL_PLAN.md` — implementation plan (status updated to "Implemented")
5. `docs/audit/PR_521B_PR_DESCRIPTION.md` — PR description

---

## Verification

- ✅ `make openapi-check` — passes (generated artifacts committed)
- ✅ `pytest tests/test_openapi_determinism.py` — passes (determinism preserved)
- ✅ `make verify` — passes (lint, typecheck, test-fast, diff-cov)

---

## Review Order (Recommended)

1. **Code changes** — verify `openapi_extra` added only to deprecated aliases
2. **OpenAPI artifacts** — verify vendor extensions appear in `openapi.json`
3. **Determinism** — verify no drift in schema generation

---

## Why Not Split PR?

This PR is already minimal (metadata-only, 5 files). Splitting would require:
- Separate PR for each endpoint (overhead)
- Or separate PR for code vs artifacts (breaks atomicity)

Current scope is optimal: all alias metadata in one atomic change.

## Known Gap / Future Work

`/api/v1/premium/plan/week-flexible` is annotated in code but excluded from generated OpenAPI due to schema-gating (feature flag). This PR does not change schema inclusion policy; it only adds metadata where endpoints are present in the schema. The question of whether deprecated aliases should always appear in OpenAPI (even when gated) is deferred to a future PR that addresses schema inclusion policy.

---

## Risks / Mitigations

**Risk:** Vendor extensions might not be supported by OpenAPI tooling.

**Mitigation:** Vendor extensions are standard OpenAPI 3.0+ feature. FastAPI supports `openapi_extra` natively. If tooling doesn't support, extensions are ignored (no breaking change).

**Risk:** Schema determinism might break.

**Mitigation:** `pytest tests/test_openapi_determinism.py` passes, confirming deterministic output.

---

## How to Test

```bash
# Verify OpenAPI generation
make openapi
make openapi-check

# Verify determinism
pytest tests/test_openapi_determinism.py

# Verify no runtime changes
make test-fast
```

---

## Related PRs

- **PR-521A** (merged): Frontend migration from `/premium/*` to `/pro/*`
- **PR-521B** (this PR): Backend OpenAPI metadata for aliases

---

**Last updated:** 2026-01-13
