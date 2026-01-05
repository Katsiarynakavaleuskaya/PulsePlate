# PR-5 Review Checklist

> **PR:** `docs(vip): freeze shoplist contract + OpenAPI alignment + iOS DTOs`
> **Branch:** `docs/pr-5-vip-shoplist-contract`

---

## ✅ Pre-Merge Checklist (5 minutes)

### 1. Swagger UI Sanity Check

**Run locally:**
```bash
make dev
# Open http://localhost:8000/docs
```

**Verify:**

- [ ] **Tags section**: `VIP Shoplist` tag exists and contains:
  - [ ] `POST /api/v1/vip/shoplist/generate`
  - [ ] `POST /api/v1/vip/shoplist/daily`
  - [ ] `POST /api/v1/vip/shoplist/weekly`
  - [ ] `GET /api/v1/vip/shoplist/preview`

- [ ] **Each endpoint "Responses" section** shows:
  - [ ] `200` (success)
  - [ ] `401` (Unauthorized: missing/invalid API key)
  - [ ] `403` (Forbidden: insufficient VIP tier)
  - [ ] `404` (VIP module disabled)
  - [ ] `422` (Validation error)
  - [ ] `500` (Invariant violation)

- [ ] **Schema definitions**:
  - [ ] `PackedLineDTO.reasons` shown as `array[string]` with example
  - [ ] `UnpackedLineDTO.reason` has default `"no_packaging_rule"` (or example)
  - [ ] `ShoplistAnalyticsDTO.total_overage_by_unit` shown as `object` (map)
  - [ ] `QuantityDTO.value` description mentions "serialized as string"

- [ ] **Examples**:
  - [ ] Request examples render (not empty) for `/generate`, `/daily`, `/weekly`
  - [ ] Response example renders for `ShoplistGenerateResponse`

### 2. CI Risk-Spot Check

**Before pushing, verify:**

- [ ] **MyPy**: No type errors on `responses=` parameter
  ```bash
  mypy app/routers/vip_shoplist.py
  ```
  _Note: file paths are examples. Run from the repository root (or via CI scripts) and adjust paths for your branch/layout._

- [ ] **Black/Ruff**: No formatting issues
  ```bash
  black --check app/schemas/vip_shoplist.py app/routers/vip_shoplist.py
  ruff check app/schemas/vip_shoplist.py app/routers/vip_shoplist.py
  ```
  _Note: file paths are examples. Run from the repository root (or via CI scripts) and adjust paths for your branch/layout._

- [ ] **Pre-commit**: All hooks pass
  ```bash
  pre-commit run --all-files
  ```

### 3. Documentation Hygiene

- [ ] **File locations**:
  - [ ] `docs/VIP_Shoplist_API.md` exists (main contract doc)
  - [ ] `docs/ios/VIPShoplistDTO.swift` exists (Swift models)
  - [ ] `docs/ios/VIP_Shoplist_iOS_Mapping.md` exists (iOS mapping table)

- [ ] **README.md**: Link to `docs/VIP_Shoplist_API.md` added in "API Documentation" section

- [ ] **iOS docs**: No hardcoded production URLs (use `BASE_URL` or placeholders)

### 4. Code Review Focus Areas

**For reviewers:**

- [ ] **OpenAPI alignment**: Schema descriptions match frozen contract
- [ ] **Type safety**: `COMMON_VIP_SHOPLIST_RESPONSES` properly typed
- [ ] **Examples**: No real API keys or sensitive data
- [ ] **Consistency**: All endpoints use same response contract

---

## 🚨 Common Issues & Fixes

### Issue: MyPy error on `responses=` parameter

**Fix:**
```python
COMMON_VIP_SHOPLIST_RESPONSES: dict[int | str, dict[str, Any]] = {
    # ...
}
```

### Issue: Swagger shows `Decimal` as `number` instead of `string`

**Fix:** Pydantic v2 automatically serializes `Decimal` as string in JSON. If Swagger shows `number`, check that `Field(description=...)` mentions "serialized as string".

### Issue: Examples not rendering in Swagger

**Fix:** Ensure `model_config = {"json_schema_extra": {"examples": [...]}}` is properly formatted (no trailing commas, valid JSON structure).

---

## ✅ Post-Merge Verification

After merge, verify:

- [ ] CI passes (coverage, lint, tests)
- [ ] Swagger UI on staging/prod shows updated schemas
- [ ] iOS team can access `docs/ios/VIPShoplistDTO.swift`

---

**Status:** ✅ Ready for review / ⚠️ Needs fixes / ❌ Blocked
