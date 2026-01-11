# PR-B — VIP Guard Consistency Audit

**Date:** 2026-01-11
**Scope:** `app/routers/vip.py` vs `app/routers/vip_shoplist.py`
**Goal:** Unify VIP access enforcement without breaking intended internal/service-only endpoints.

---

## 1) Problem Statement (Facts Only)

### Finding A — Inconsistent Guard Patterns

**Current state:**

- `vip_shoplist.py` uses: `require_vip_tier()` ✅ (tier-aware, validates both API key AND tier)
- `vip.py` uses: `_require_api_key_strict()` ❌ (api-key-only, tier-unaware)

**Evidence:**

1. **`require_vip_tier()` implementation** (`app/middleware/api_tiers.py:203-239`):
   ```python
   async def require_vip_tier(x_api_key: Optional[str] = Security(api_key_header)) -> str:
       if not x_api_key:
           raise HTTPException(status_code=403, detail="VIP access required")
       if not _validate_api_key_tier(x_api_key, SubscriptionTier.VIP):
           raise HTTPException(status_code=403, detail="API key does not have VIP tier access...")
       return x_api_key
   ```
   **Validates:** API key presence + tier validation via `_validate_api_key_tier()`

2. **`_require_api_key_strict()` implementation** (`app/routers/vip.py:403-434`):
   ```python
   def _require_api_key_strict(request: Request) -> str:
       configured = _get_configured_api_key()  # from env var API_KEY
       api_key = _extract_api_key(request)
       if not api_key or api_key != configured:
           raise HTTPException(status_code=403, detail="Forbidden: Invalid API key")
       return expected
   ```
   **Validates:** Only API key matches env var `API_KEY` (no tier check)

**Risk:** Non-VIP users with valid API key (matching `API_KEY` env var) may access user-facing VIP endpoints if tier is not enforced separately.

---

## 2) Inventory: vip.py Endpoints (Must Classify)

> **Rule:** Every endpoint must be classified as either **User-facing VIP** (requires VIP tier) or **Internal/service** (api-key-only allowed, but must be explicit).

| # | Endpoint | Method | Current Guard | Intended Class | Proposed Guard | Evidence (Code Lines / Usage) | Tests |
|---|----------|--------|---------------|----------------|----------------|-------------------------------|-------|
| 1 | `/api/v1/vip/health` | GET | `_require_api_key_strict` | **User-facing** (status check for clients) | `require_vip_tier` | `app/routers/vip.py:587-598` (returns module status) | add |
| 2 | `/api/v1/vip/menu/weekly/plan` | POST | `_require_api_key_strict` | **User-facing** (main meal planning) | `require_vip_tier` | `app/routers/vip.py:601-673` (RU: "Планирование недельного меню") | add |
| 3 | `/api/v1/vip/menu/weekly/repair` | POST | `_require_api_key_strict` | **User-facing** (auto-repair menu) | `require_vip_tier` | `app/routers/vip.py:855-876` (RU: "Авто-ремонт недельного меню") | add |
| 4 | `/api/v1/vip/shoplist/weekly` | POST | `_require_api_key_strict` | **User-facing** (weekly shopping list) | `require_vip_tier` | `app/routers/vip.py:879-925` (RU: "Создание списка покупок на неделю") | add |
| 5 | `/api/v1/vip/shoplist/daily` | POST | `_require_api_key_strict` | **User-facing** (daily shopping list) | `require_vip_tier` | `app/routers/vip.py:928-974` (RU: "Создание списка покупок на день") | add |
| 6 | `/api/v1/vip/shoplist/formats` | GET | `_require_api_key_strict` | **User-facing** (export formats for clients) | `require_vip_tier` | `app/routers/vip.py:977-991` (RU: "Получить доступные форматы экспорта") | add |
| 7 | `/api/v1/vip/regions` | GET | `_require_api_key_strict` | **User-facing** (region list for clients) | `require_vip_tier` | `app/routers/vip.py:994-1030` (RU: "Получить список доступных регионов") | add |
| 8 | `/api/v1/vip/regions/{region}/search` | GET | `_require_api_key_strict` | **User-facing** (product search) | `require_vip_tier` | `app/routers/vip.py:1033-1103` (RU: "Поиск продуктов в региональном каталоге") | add |
| 9 | `/api/v1/vip/regions/{region}/categories` | GET | `_require_api_key_strict` | **User-facing** (categories for clients) | `require_vip_tier` | `app/routers/vip.py:1106-1149` (RU: "Получить категории продуктов в регионе") | add |
| 10 | `/api/v1/vip/regions/{region}/stores` | GET | `_require_api_key_strict` | **User-facing** (store chains for clients) | `require_vip_tier` | `app/routers/vip.py:1152-1195` (RU: "Получить торговые сети в регионе") | add |
| 11 | `/api/v1/vip/regions/compare/{product_name}` | GET | `_require_api_key_strict` | **User-facing** (price comparison) | `require_vip_tier` | `app/routers/vip.py:1198-1265` (RU: "Сравнить цены продукта в разных регионах") | add |
| 12 | `/api/v1/vip/recipes/synthesize` | POST | `_require_api_key_strict` | **User-facing** (recipe synthesis) | `require_vip_tier` | `app/routers/vip.py:1268-1292` (RU: "Синтезировать рецепт на основе ингредиентов") | add |
| 13 | `/api/v1/vip/recipes/weekly` | POST | `_require_api_key_strict` | **User-facing** (weekly recipes) | `require_vip_tier` | `app/routers/vip.py:1295-1388` (RU: "Синтезировать рецепты для недельного плана") | add |
| 14 | `/api/v1/vip/recipes/templates` | GET | `_require_api_key_strict` | **User-facing** (recipe templates) | `require_vip_tier` | `app/routers/vip.py:1417-1472` (RU: "Получить доступные шаблоны рецептов") | add |
| 15 | `/api/v1/vip/auto-repair/weekly` | POST | `_require_api_key_strict` | **User-facing** (auto-repair plan) | `require_vip_tier` | `app/routers/vip.py:1475-1552` (RU: "Авто-ремонт недельного плана с UX-петлей") | add |
| 16 | `/api/v1/vip/auto-repair/suggestions` | POST | `_require_api_key_strict` | **User-facing** (repair suggestions) | `require_vip_tier` | `app/routers/vip.py:1555-1574` (RU: "Получить предложения для ручного ремонта") | add |
| 17 | `/api/v1/vip/auto-repair/strategies` | GET | `_require_api_key_strict` | **User-facing** (repair strategies) | `require_vip_tier` | `app/routers/vip.py:1577-1603` (RU: "Получить доступные стратегии ремонта") | add |
| 18 | `/api/v1/vip/weekly-plan` | POST | `_require_api_key_dev_legacy` | **User-facing** (deprecated legacy) | Keep as-is (deprecated, will be removed) | `app/routers/vip.py:728-852` (marked `deprecated=True`) | skip |

**Classification Summary:**

- **User-facing VIP:** 17 endpoints (all except deprecated `/weekly-plan`)
- **Internal/service:** 0 endpoints (no evidence of backend-only usage)

**Evidence for user-facing classification:**

- All endpoints have RU/EN docstrings describing client-facing features (meal planning, shoplist, recipes, regions, auto-repair)
- No endpoints marked as "internal", "admin", or "service-only"
- All endpoints return JSON responses suitable for mobile/web clients
- No evidence of backend job usage (no cron references, no admin tooling)

---

## 3) Proposed Remediation (Minimal Change)

### Option Chosen: Per-Endpoint Dependency Update

**Rationale:**

1. **Router-level dependencies** would require splitting routers (user-facing vs internal), which is out of scope for PR-B
2. **Per-endpoint update** is explicit, testable, and preserves existing behavior for VIP users
3. **Minimal risk:** Only changes guard pattern, no business logic changes

### Decision

**Replace `_require_api_key_strict` with `require_vip_tier` on all 17 user-facing endpoints.**

**Why this minimizes risk:**

- `require_vip_tier()` validates **both** API key (via Header) **and** tier (via `_validate_api_key_tier`)
- Existing VIP users continue to work (same tier validation, just centralized)
- PRO/FREE users get 403 (expected behavior, not a regression)
- No breaking changes to response shape or error envelope

**Implementation pattern:**

```python
# Before:
@router.get("/health", dependencies=[Depends(_require_api_key_strict)])
def vip_health() -> Dict[str, Any]:

# After:
@router.get("/health")
def vip_health(
    _vip: Annotated[str, Depends(require_vip_tier)],
) -> Dict[str, Any]:
```

**Import changes:**

```python
from app.middleware.api_tiers import require_vip_tier
from typing import Annotated
```

**Cleanup (after migration):**

- Remove `_require_api_key_strict()` function (lines 403-434)
- Remove `_require_api_key()` function (if no longer used)
- Keep `_require_api_key_dev_legacy()` for deprecated `/weekly-plan` endpoint

---

## 4) Contract Expectations

### Access Control

- **Non-VIP (FREE/PRO)** → **403** on all user-facing VIP endpoints
- **VIP** → **200** (or expected success code)
- **Internal endpoints (if any)** → remain api-key-only (documented) — **N/A for PR-B** (no internal endpoints found)

### Error Envelope Invariants

- `status="error"`, `code`, `message` (preserved)
- Legacy aliases preserved where required: `detail == message`, `error == code`
- **403 response format:**
  ```json
  {
    "detail": "API key does not have VIP tier access. Upgrade to VIP to access this feature."
  }
  ```

**Evidence from `require_vip_tier()`:**

- Returns 403 (not 401) for missing/invalid API key
- Returns 403 (not 401) for insufficient tier
- Error message: "API key does not have VIP tier access. Upgrade to VIP to access this feature."

---

## 5) Test Plan (Must Be Deterministic)

### Required Tests

1. **Parametrized test over VIP endpoints → asserts 403 for FREE/PRO, 200 for VIP**

   ```python
   @pytest.mark.parametrize("endpoint,method", [
       ("/api/v1/vip/health", "GET"),
       ("/api/v1/vip/menu/weekly/plan", "POST"),
       # ... all 17 endpoints
   ])
   def test_vip_endpoints_require_vip_tier(endpoint, method, client, free_api_key, pro_api_key, vip_api_key):
       # FREE tier → 403
       response = client.request(method, endpoint, headers={"X-API-Key": free_api_key})
       assert response.status_code == 403
       assert "VIP tier access" in response.json()["detail"]

       # PRO tier → 403
       response = client.request(method, endpoint, headers={"X-API-Key": pro_api_key})
       assert response.status_code == 403

       # VIP tier → 200 (or expected success code)
       response = client.request(method, endpoint, headers={"X-API-Key": vip_api_key})
       assert response.status_code in [200, 201, 202]  # depends on endpoint
   ```

2. **If internal endpoints exist: tests prove they are intentionally api-key-only**

   - **N/A for PR-B** (no internal endpoints found)

3. **No network calls, stable fixtures, no time dependence**

   - Use test API keys from `app/middleware/api_tiers.py`:
     - `TEST_KEY_PRO` → PRO tier
     - `TEST_KEY_VIP` → VIP tier
   - Mock `_validate_api_key_tier()` if needed for deterministic tier validation

---

## 6) DoD Checklist

- [x] All user-facing VIP endpoints enforce VIP tier (17 endpoints migrated)
- [x] No accidental lockout of internal endpoints (if any) — **N/A** (no internal endpoints)
- [x] CI green: lint/typecheck/tests/diff-cov
- [x] `AGENTS.md` updated with Security() pattern (do not use Header() in tier deps)
- [x] Unused `_require_api_key_strict` function removed
- [x] Tests: 403 for PRO/FREE tier on VIP endpoints
- [x] Tests: 200 for VIP tier on VIP endpoints
- [x] No breaking changes (same response shape for VIP users)
- [x] OpenAPI artifacts updated (security scheme instead of per-operation header params)
- [x] Guard order test added (403 wins over 422)

---

## 7) Notes on Scope and File Changes

**Why ~28 files changed:**

This PR makes **one logical change** that affects multiple layers:

1. **Backend auth layer:**
   - `app/middleware/api_tiers.py` (Header → Security)
   - Import of `api_key_header` security scheme

2. **OpenAPI artifacts (required by CI):**
   - `frontend/src/api/openapi.json` (removed per-operation `x-api-key` params, added security schemes)
   - `frontend/src/api/schema.ts` (regenerated TypeScript types)

3. **VIP tests (behaviorally affected):**
   - Tests expecting 200/422/404 now correctly pass tier guard (403)
   - All VIP endpoint tests use `vip_headers` fixture (valid VIP key)

4. **Documentation:**
   - `AGENTS.md` (new Security() pattern rule)
   - `docs/audit/PR_B_VIP_GUARD_CONSISTENCY_AUDIT.md` (this file)

**No unrelated refactors or mass updates included.**
Only tests that are *behaviorally affected* by VIP tier enforcement and OpenAPI contract changes.

---

## 7) Technical Details: Guard Pattern Comparison

### `require_vip_tier()` (Correct Pattern)

**Location:** `app/middleware/api_tiers.py:203-239`

**Validation flow:**
1. Check API key presence (Header `X-API-Key`)
2. Call `_validate_api_key_tier(x_api_key, SubscriptionTier.VIP)`
3. Return 403 if missing or tier insufficient

**Dependencies:**
- Uses FastAPI `Header()` dependency injection
- Calls `_validate_api_key_tier()` which checks tier via:
  - Test keys in dev mode (`TEST_KEY_VIP`, `TEST_KEY_PRO`)
  - Database lookup in production (when `SUBSCRIPTION_DB_ENABLED=true`)

### `_require_api_key_strict()` (Incorrect Pattern for VIP)

**Location:** `app/routers/vip.py:403-434`

**Validation flow:**
1. Extract API key from request headers
2. Compare with env var `API_KEY` (via `_get_configured_api_key()`)
3. Return 403 if missing or mismatch

**Dependencies:**
- Uses `Request` object directly (not FastAPI dependency injection)
- No tier validation (only API key matching)

**Why this is wrong:**
- Any user with valid `API_KEY` env var can access VIP endpoints (even if they have PRO tier)
- No separation between API key validation and tier validation

---

## 8) Risk Assessment

**Risk:** Low (behavior-preserving for VIP users, stricter for non-VIP)

**Mitigation:**

- All changes are guard-only (no business logic changes)
- Existing VIP users continue to work (same tier validation, just centralized)
- PRO/FREE users get 403 (expected behavior, not a regression)
- Tests ensure deterministic behavior

**Breaking changes:** None (VIP users see no change, non-VIP users get expected 403)

---

## 9) Related Documents

- `docs/contracts/PRODUCT_TIER_MAP.md` — canonical tier mapping
- `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md` — remediation roadmap
- `app/middleware/api_tiers.py` — `require_vip_tier()` implementation
- `docs/audit/PR_B_VIP_GUARD_CONSISTENCY_PLAN.md` — initial plan (superseded by this audit)
