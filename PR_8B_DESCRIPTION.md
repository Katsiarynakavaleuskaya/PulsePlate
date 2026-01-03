# PR-8b: Product-quality PDF export for VIP shoplist

## What
Product-quality PDF export for VIP shoplist endpoint (`/api/v1/vip/shoplist/export?export_format=pdf`).

## How

### Architecture improvements
- **Lazy import reportlab**: Module is now import-safe (no import-time side effects)
- **Pure data preparation**: Separated `build_pdf_lines()` function (no reportlab dependency)
- **PdfLine dataclass**: Deterministic row representation for testing without PDF rendering
- **Product layout**: Store→aisle grouping with subtotals and grand total
- **Currency formatting**: Proper money formatting via `catalog.price.currency` (CurrencyDTO enum)

### Security
- **No exception detail leaks**: Removed exception details from error messages
- **ImportError handling**: Preserved ImportError→501 invariant (handled at endpoint level)

### Code quality
- **Deterministic ordering**: `(store_id, aisle, food_id)` - same as CSV export
- **Type safety**: Proper type annotations, no `Any` except for reportlab components
- **Test coverage**: Comprehensive unit and API tests

## Invariants preserved

✅ **ImportError → 501**: Handled at endpoint level (`vip_shoplist_export`), not in `pdf_export.py`
✅ **No exception detail leaks**: Generic error messages in production
✅ **Deterministic ordering**: `store_id → aisle → food_id` (non-empty values first)
✅ **VIP error contract**: Frozen contract shape maintained (if envelope present: `status`, `detail==message`, `error==code`)

## Tests

### Unit tests (`tests/vip/test_pdf_export_pr8b.py`)
- ✅ Deterministic ordering: `(store_id, aisle, food_id)`
- ✅ Store→aisle grouping logic
- ✅ Subtotal/total calculations (Decimal precision)
- ✅ Currency code handling

### API tests
- ✅ PDF bytes generation: `%PDF` header + non-empty content (`len > 500`)
- ✅ ImportError → 501: Frozen error contract validation (supports both default FastAPI and VIP envelope)
- ✅ Content-type check: Not `application/pdf` for 501 responses

### Diff-coverage tests (`tests/vip/test_pdf_export_diff_coverage.py`)
- ✅ Updated exception wrapping test for lazy import pattern

### Guard tests (branch coverage)
- ✅ `test_pdf_export_rows_guard.py`: Deterministic structure and totals (single aisle)
- ✅ `test_pdf_export_rows_guard_multi_aisle.py`: Multi-aisle subtotal flush (one store, two aisles)
- ✅ `test_pdf_export_rows_guard_store_change.py`: Store-change subtotal flush (two stores, one aisle)
- ✅ `test_pdf_export_layout_table.py`: Table layout via FakeTable (no PDF parsing)

**Branch coverage**: Added guard tests to cover both outcomes of `if line.catalog` (Codecov `branch=True`) and to lock subtotal flush on aisle/store transitions.

## Files changed

```text
app/services/shoplist_export/pdf_export.py  | 442 ++++++++++++++++++++++++-----
tests/vip/test_pdf_export_pr8b.py          | 362 +++++++++++++++++++++++
tests/vip/test_pdf_export_diff_coverage.py |  35 ++-
app/AGENTS.md                              |  35 +++
tests/AGENTS.md                            |  31 ++
```

## Documentation

- Updated `app/AGENTS.md`: PDF export invariants, product layout rules, `build_pdf_lines()` pattern
- Updated `tests/AGENTS.md`: PDF export test guidelines (no snapshots, test data prep separately)

## CI Checklist

- [x] All pre-commit hooks passed (black, ruff, mypy, pip-audit, bandit)
- [x] Docker build test passed
- [x] Import-safety verified (module imports without reportlab)
- [x] Type annotations complete
- [x] No exception detail leaks
- [x] Tests cover all new code paths

## Summary

PR-8b delivers product-quality VIP shoplist PDF export (store→aisle grouping, subtotals, grand total) while preserving frozen VIP contracts. Reportlab remains lazy-imported (import-safe). ImportError is mapped to 501 at router level as invariant. Added guard tests to satisfy Codecov branch coverage for `if line.catalog` and to lock aisle/store subtotal flush behavior.

## Related

- PR-8c (#456): VIP router registration and error contract (frozen)
- Maintains compatibility with existing VIP endpoints
