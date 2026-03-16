# PR-5: Contract Freeze + OpenAPI Alignment + iOS DTOs

## Summary

Freezes VIP Shoplist API contract and aligns OpenAPI documentation with frozen contract. Adds iOS integration support with ready-to-use Swift DTOs.

## Changes

### 1. Contract Freeze Documentation

- **`docs/VIP_Shoplist_API.md`**: Complete API contract documentation
  - Endpoint specifications (generate/daily/weekly)
  - Gating matrix (401/403/404/422/500)
  - Explainability guarantees (reasons/reason)
  - Analytics contract
  - cURL examples (EN/RU/ES)
  - Determinism and Decimal-as-string semantics

### 2. OpenAPI Schema Alignment

**`app/schemas/vip_shoplist.py`:**
- Added `Field` descriptions for all DTOs
- Added examples for enums and fields
- Added `model_config.json_schema_extra` with request/response examples
- Clarified Decimal serialization (as string in JSON)

**`app/routers/vip_shoplist.py`:**
- Created `COMMON_VIP_SHOPLIST_RESPONSES` dict for gating matrix
- Added `responses=...` to all endpoints (401/403/404/422/500)
- Added `tags=["VIP Shoplist"]` for grouping
- Added `summary` and `description` for each endpoint
- Emphasized determinism, explainability, and analytics in descriptions

### 3. iOS Integration Support

**`docs/ios/VIPShoplistDTO.swift`:**
- Complete Codable DTOs matching API contract
- Enums: `Unit`, `FoodForm`, `RoundingMode`
- Request/Response models with proper `CodingKeys`
- Decimal parsing utilities (`asDecimal()` extension)

**`docs/ios/VIP_Shoplist_iOS_Mapping.md`:**
- JSON ↔ Swift type mapping table
- Usage examples
- Error handling guidance (HTTP status codes)
- Determinism guarantees

### 4. README Update

- Added link to `docs/VIP_Shoplist_API.md` in "API Documentation" section

## Non-Goals / Out of Scope

- ❌ No engine changes (core logic untouched)
- ❌ No Region/Catalog enrichment (future PR)
- ❌ No UI changes
- ❌ No breaking API changes

## How to Verify

### Local Swagger UI

```bash
make dev
# Open http://localhost:8000/docs
```

**Check:**
- `VIP Shoplist` tag contains all 4 endpoints
- Each endpoint shows gating matrix (401/403/404/422/500) in Responses
- Request/response examples render correctly
- Schema shows `reasons` as `array[string]`, `total_overage_by_unit` as `object`

### CI

- [ ] All tests pass
- [ ] Coverage ≥ 97%
- [ ] MyPy type checks pass
- [ ] Black/Ruff formatting checks pass

## Security Notes

- ✅ Examples contain only dummy keys (`test_key`)
- ✅ 500 documented as invariant violation (internal error), not user error
- ✅ No new privileged behavior added (documentation only)
- ✅ No sensitive data in examples

## Marketing & GTM

- **Contract freeze** reduces integration bugs and accelerates iOS-first rollout
- **Swagger examples** make explainability + analytics "discoverable" → easier VIP demo
- **iOS-ready DTOs** enable faster mobile integration

## Related

- PR-3: Router hardening (gating, error handling)
- PR-4: Daily/Weekly endpoint standardization
- Future PR (TBD): Region/Catalog adapter (out of scope for this PR). PR-6 = iOS Keychain conformance.

## Files Changed


---

**Ready for review** ✅
