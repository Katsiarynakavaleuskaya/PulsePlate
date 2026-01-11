# API Alignment PR Template

**Use this template when PR touches API contracts, endpoints, or OpenAPI schema.**

---

## Contract Impact

- [ ] **OpenAPI schema changes:** Yes / No
- [ ] **Endpoint paths changed:** Yes / No
- [ ] **Request/response models changed:** Yes / No
- [ ] **VIP/PRO/premium mapping affected:** Yes / No

**If any "Yes":**
- Link to `docs/audit/API_ALIGNMENT_CHECKLIST.md` section that applies
- Link to `docs/contracts/PRODUCT_TIER_MAP.md` (or note if it needs update)

---

## Pre-merge Checks

- [ ] `make openapi && git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts`
- [ ] `pytest` + `diff-cover` ≥97%
- [ ] Schema-only guards applied (if adding conditional routers)
- [ ] Admin/test/export endpoints excluded from schema (if public schema)

---

## VIP-first / Premium-shim Policy

- [ ] New endpoint is canonical (VIP/PRO) **or** premium shim (delegates only)
- [ ] No business logic duplication between premium and canonical
- [ ] Frontend types use generated `schema.ts` (no manual types)

---

**See:** `docs/audit/API_ALIGNMENT_CHECKLIST.md` for full protocol.
