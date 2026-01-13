# PR-521B Reviewer Checklist

## Quick Review (2-3 minutes)

### ✅ Scope Check

- [ ] **Metadata-only changes** — verify no runtime behavior changes (guards, handlers, response models unchanged)
- [ ] **Vendor extensions added** — verify `openapi_extra` with `x-alias-of` and `x-migration-path` only on deprecated `/premium/*` aliases
- [ ] **Generated artifacts committed** — verify `frontend/src/api/openapi.json` includes vendor extensions and `make openapi-check` passes

### ⚠️ Known Gap (Not a Bug)

**Do not flag as issue:** `/api/v1/premium/plan/week-flexible` is annotated in code but excluded from OpenAPI generation due to feature flag gating. This is by design per current OpenAPI policy. Schema inclusion policy is out of scope for this PR.

### 🚫 Out of Scope (Do Not Request)

- Changing schema inclusion policy (feature flags)
- Adding week-flexible to OpenAPI schema
- Runtime behavior changes
- Guard/response model changes

---

## Verification Commands

```bash
# Verify OpenAPI artifacts are in sync
make openapi-check

# Verify determinism
pytest -q tests/test_openapi_determinism.py

# Verify no runtime regressions
make verify
```

---

## Review Focus

**What to review:**
- Vendor extension keys (`x-alias-of`, `x-migration-path`) are correct
- Canonical paths match actual endpoints
- Generated `openapi.json` includes extensions

**What NOT to review:**
- Why week-flexible is not in OpenAPI (feature flag, by design)
- Schema inclusion policy (separate concern)

---

**Last updated:** 2026-01-13
