# PR-8b: Product-quality PDF export for VIP shoplist

## What
Product-quality PDF export for VIP shoplist endpoint (`/api/v1/vip/shoplist/export?export_format=pdf`).

## Scope
This PR contains two tightly related tracks:

### A) PR-8b core: VIP Shoplist PDF (product-quality)
- Deterministic PDF layout (store → aisle grouping)
- Subtotals per aisle + grand total
- Currency formatting (incl. zero-decimal currencies like JPY/KRW)
- Import-safe reportlab lazy loading (ImportError → 501 remains in caller)
- Guard tests & diff-coverage closure for pdf_export.py

**Zero-decimal currencies**: Currently special-cased: JPY, KRW (most expected). Mapping is intentionally minimal and can be extended later (e.g. VND/CLP/ISK) if/when supported in catalog sources.

### B) Infrastructure safety (supports PR-8b workflow)
- Pre-push backend-tests hook robustness (shallow/new repos, no Bash-4-only features)
- Documentation updates (AGENTS)
- Coverage boost / legacy test assertion clarified for VIP regions contract

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

## Invariants preserved (frozen)
- VIP auth remains 403 feature-gate (no changes)
- VIP error contract unchanged
- ImportError → 501 for PDF export handled in router caller
- No import-time side effects in PDF module
- Deterministic ordering: `store_id → aisle → food_id` (non-empty values first)
- No exception detail leaks: Generic error messages in production

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

## Tests
- ✅ `make test-fast` passed
- ✅ Total coverage ≥ 97% (97.18% locally)
- ✅ diff-cover for pdf_export.py: 100%
- ✅ Guard tests cover branch/ordering/grouping
- ✅ Pre-push hook robustness verified (shallow repos, Bash-3 compatibility)

## CI Checklist

- [x] All pre-commit hooks passed (black, ruff, mypy, pip-audit, bandit)
- [x] Docker build test passed
- [x] Import-safety verified (module imports without reportlab)
- [x] Type annotations complete
- [x] No exception detail leaks
- [x] Tests cover all new code paths
- [x] Pre-push hook handles shallow/new repos correctly
- [x] No Bash-4-only features (mapfile removed)

## Summary

PR-8b delivers product-quality VIP shoplist PDF export (store→aisle grouping, subtotals, grand total) while preserving frozen VIP contracts. Reportlab remains lazy-imported (import-safe). ImportError is mapped to 501 at router level as invariant. Added guard tests to satisfy Codecov branch coverage for `if line.catalog` and to lock aisle/store subtotal flush behavior.

**Infrastructure changes** (track B) ensure pre-push hooks work reliably on shallow/new repos and maintain Bash-3 compatibility, which is critical for strict coverage gates enforced in this PR.

## Decision log

- **Infra changes included in PR-8b**: Intentionally kept together because pre-push hook robustness directly supports the strict coverage requirements of this PR. Previously, hooks could silently skip tests on shallow repos, which is unacceptable given 97% coverage gate. This PR makes test execution deterministic on push and documents it. No runtime behavior is changed by infra parts.
- **Future cleanup**: After PR-8b merge, infra/hooks improvements can be extracted to a separate PR for cleaner history.

## Why not split into two PRs?
This branch already had active collaborative review and multiple dependent commits.
To avoid history rewriting and review churn, infra safety fixes are included here but clearly isolated in Scope section.
A follow-up cleanup PR can later extract infra improvements if desired.

## Review order (recommended)
1) `app/services/shoplist_export/pdf_export.py` — core PDF logic (layout, totals, currencies, lazy import)
2) `tests/vip/test_pdf_export_*` + `_pdf_rows_assert.py` — guards & diff-coverage
3) `scripts/run-backend-tests-pre-commit.sh` + `.pre-commit-config.yaml` — infra safety (portable + shallow-safe)
4) `tests/test_vip_coverage_boost.py` — contract assertion clarification

## Related

- PR-8c (#456): VIP router registration and error contract (frozen)
- Maintains compatibility with existing VIP endpoints
