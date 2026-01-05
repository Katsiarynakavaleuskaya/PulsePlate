# PR-8c: DRY refactor for `/daily` endpoint + PDF export foundation

## Summary

Refactors VIP shoplist endpoints to eliminate code duplication and establishes clean architecture for CSV/PDF export. Uses Protocol-based shared generator for `/generate`, `/daily`, and `/export` endpoints.

## Changes

### 1. DRY: Shared generator with Protocol (`vip_shoplist.py`)

- **Added `_ShoplistLikeRequest` Protocol**: Minimal contract for shoplist generation (items + packaging_rules)
- **Extracted `_generate_vip_shoplist()`**: Internal async function shared by `/generate`, `/daily`, and `/export`
- **Refactored `/daily` endpoint**: Now reuses shared generator instead of duplicating logic
- **Benefits**: Single source of truth, easier maintenance, consistent behavior

### 2. PDF export foundation (`vip_shoplist.py`, `shoplist_export/`)

- **Added `_export_shoplist_to_pdf()` helper**: Encapsulates PDF import in one place (≈L69)
- **Lazy PDF dependency import**: PDF deps only imported when `/vip/shoplist/export` is actually called
- **Clean `__init__.py`**: Removed try/except magic, exports only CSV (no side effects)
- **Hardened error handling**: `logger.exception(...)` with generic client message, preserves exception chaining
- **Type safety**: Uses typed local variable pattern (same as `foods.py`) for mypy compatibility

### 3. VIP router registration (`vip_registration.py`, `legacy_app.py`)

- **Centralized registration**: New `register_vip_routes()` function eliminates import-side-effects
- **Backward compatibility**: `vip_router` still accessible for tests/introspection
- **Simplified test setup**: `_enable_vip()` now side-effect free (no route re-registration)

### 4. Code quality improvements (`vip.py`)

- **Removed self-import indirection**: `get_regions()` and `search_region_products()` now use module-scope functions directly
- **Simplified control flow**: No `importlib.import_module("app.routers.vip")` indirection
- **Type assertions**: Added assertions to help type checker understand None checks

## Technical Details

### Protocol-based shared generator

```python
@runtime_checkable
class _ShoplistLikeRequest(Protocol):
    items: list[ShoplistItemDTO]
    packaging_rules: list[PackageRuleDTO] | None

async def _generate_vip_shoplist(
    payload: _ShoplistLikeRequest,
    *,
    region_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> ShoplistGenerateResponse:
    # Shared logic for /generate, /daily, /export
```

### PDF export encapsulation

```python
def _export_shoplist_to_pdf(result: ShoplistGenerateResponse) -> bytes:
    from app.services.shoplist_export.pdf_export import export_shoplist_to_pdf
    pdf_data: bytes = export_shoplist_to_pdf(result)  # Typed local for mypy
    return pdf_data
```

## Testing

- ✅ All existing tests pass
- ✅ Test setup simplified (no route re-registration)
- ✅ PDF unavailable test updated to simulate missing reportlab
- ✅ Coverage maintained

## CI Status

- ✅ mypy passes (with typed local variable pattern)
- ✅ Docker build passes
- ✅ All pre-push hooks pass
- ✅ No import-side-effects

## Risk & Impact

**Low risk**:
- No API contract changes
- Backward compatible
- Tests validate behavior

**Impact**:
- Cleaner architecture (DRY principle)
- Easier to extend (PDF export foundation)
- More maintainable (single source of truth)

## Reviewer Checklist

- [ ] Protocol-based shared generator follows project patterns
- [ ] PDF export encapsulation is clean (no magic in `__init__.py`)
- [ ] VIP router registration is centralized and testable
- [ ] No import-side-effects introduced
- [ ] All tests pass

## Related

- PR-8a: CSV export (already merged)
- PR-8b: PDF export (next, after this PR)
