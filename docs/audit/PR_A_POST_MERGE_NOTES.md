# PR-A Post-Merge Notes — Key Findings for PR-B/PR-C

**PR-A merged:** 2026-01-11
**Purpose:** Document key findings from PR-A audit that inform subsequent runtime PRs

---

## Key Findings (Fixed in PR-A)

### 1. `/premium/*` Namespace Status

**Finding:**
- `/premium/*` is a **deprecated namespace**, not a product tier
- Endpoints under `/premium/*` may require **PRO tier** OR **VIP tier** (depends on endpoint)
- `/api/v1/premium/plan/week` requires **VIP tier** but lives under `/premium/*` → **broken naming** (architectural confusion)

**Impact for PR-B/PR-C:**
- PR-B: Hide `/premium/*` from OpenAPI schema (all endpoints, regardless of tier)
- PR-C: Fix `/premium/plan/week` → delegate to `/vip/menu/weekly/plan` (VIP canonical)

**Source:** `docs/contracts/PRODUCT_TIER_MAP.md` (canonical tier mapping)

---

### 2. VIP Shoplist Code References

**Finding:**
- VIP shoplist endpoints are canonical in `app/routers/vip_shoplist.py`
- Line references updated in PR-A (preview:299, generate:364, daily:402, weekly:442)

**Impact for PR-B/PR-C:**
- These line references can be used as "code clues" for future audits
- **Note:** Line numbers are brittle; prefer symbol/function names or anchor comments in future docs

**Source:** `docs/contracts/PRODUCT_TIER_MAP.md` (VIP shoplist table)

---

## Product Tier Model (Canonical)

**Tiers (per `SubscriptionTier` enum):**
- FREE
- PRO
- VIP

**Namespaces:**
- `/api/v1/bmi/*` → FREE (canonical)
- `/api/v1/pro/*` → PRO (canonical)
- `/api/v1/vip/*` → VIP (canonical)
- `/api/v1/premium/*` → deprecated aliases (hide from OpenAPI)

**Source:** `AGENTS.md` section "Product tiers and API namespaces"

---

## Next Steps (PR-B/PR-C)

### PR-B: Schema Hygiene
- Hide all `/premium/*` endpoints from OpenAPI (`include_in_schema=False`)
- Verify: `make openapi` → zero `/premium/*` paths
- Runtime: endpoints still work (backward compatible)

### PR-C: VIP Alignment
- Fix `/premium/plan/week` → delegate to `/vip/menu/weekly/plan`
- Parity test: responses equivalent
- Remove VIP business logic from premium endpoint

---

## Documentation Improvements (Future)

**Line-number proofs in docs are brittle:**
- Prefer linking to symbol/function name or anchor comment
- Avoid hard line numbers in canonical documentation
- Use line numbers only for "code clues" in audit documents

**Status:** Noted for future docs PR (out of scope for PR-A)

---

**See also:**
- `docs/contracts/PRODUCT_TIER_MAP.md` — canonical tier mapping
- `docs/contracts/OPENAPI_PATHS_AUDIT.md` — factual inventory
- `docs/contracts/OPENAPI_VISIBILITY_MATRIX.md` — visibility rules
