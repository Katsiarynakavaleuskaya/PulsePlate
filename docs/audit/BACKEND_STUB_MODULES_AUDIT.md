# Backend Stub Modules & Incomplete Implementations Audit

**Date:** 2026-01-15
**Scope:** Modules marked as stub, incomplete, or not fully implemented
**Purpose:** Track modules that need completion

---

## 📊 Summary

**Total stub modules:** 5
**Total incomplete modules:** 2

---

## 🔴 Critical Stub Modules (P0)

### 1. `core/bmi/engine.py` — BMI Engine (Incomplete)

**Status:** Stub implementation

**Comment:**
```python
"""
This module will be fully implemented in PR-455.
Currently provides a stub implementation for development/testing.
"""
```

**Current State:**
- ✅ Core functions implemented (`_compute_bmi`, `_compute_wht_ratio`, `calculate_bmi_result`)
- ✅ Group/category logic implemented
- ✅ Validation and normalization implemented
- ⚠️ Marked as "stub" but appears functional

**Impact:** Medium
- Module works but marked as incomplete
- May need additional features from PR-455

**Recommendation:**
- Verify if PR-455 is complete
- Remove "stub" comment if implementation is complete
- Or document what's missing from PR-455

**File:** `core/bmi/engine.py:1-9`

---

## ⚠️ Stub Modules (P1)

### 2. `core/log_retention.py` — Log Cleanup (Stub)

**Status:** Stub implementation

**Function:** `cleanup_expired_logs()`

**Current State:**
- Returns `0` (no files deleted)
- Logs warning that cleanup is not implemented
- TODO comment with full implementation plan

**Impact:** Medium
- Log files may accumulate over time
- No automatic cleanup

**Recommendation:**
- Implement file deletion logic
- Add dry-run mode
- Add safeguards

**File:** `core/log_retention.py:100-115`

---

### 3. `core/catalog/` — Catalog System (Stub Sources Only)

**Status:** Stub implementations only

**Modules:**
- `core/catalog/sources/off_stub.py` — Open Food Facts stub
- `core/catalog/sources/carrefour_stub.py` — Carrefour stub
- `core/catalog/sources/walmart_stub.py` — Walmart stub

**Current State:**
- All sources are offline stubs
- No real network calls
- Deterministic test data only

**Comment:**
```python
"""
This package intentionally contains only deterministic, offline stubs for now.
No real provider integrations or network calls should live here yet.
"""
```

**Impact:** Low (by design)
- Catalog system is intentionally stubbed
- Real integrations planned for future

**Recommendation:**
- Document when real integrations will be added
- Keep stubs for testing

**Files:**
- `core/catalog/__init__.py:3-5`
- `core/catalog/sources/*.py`

---

### 4. `core/exports_simple.py` — PDF Export (Placeholder)

**Status:** Placeholder when reportlab unavailable

**Functions:**
- `export_to_pdf()` — Falls back to placeholder file
- `generate_pdf_report()` — Falls back to placeholder

**Current State:**
- Writes placeholder file: `b"PDF generation unavailable; placeholder file"`
- Returns success but file is not a real PDF

**Impact:** Low (graceful degradation)
- Feature works when reportlab is available
- Gracefully degrades when unavailable

**Recommendation:**
- Document reportlab as optional dependency
- Consider making PDF export a feature flag

**File:** `core/exports_simple.py:69, 138, 146, 183`

---

### 5. `core/food_apis/update_manager.py` — Fallback Serialization

**Status:** Placeholder fallback

**Code:**
```python
# Fallback: return a dict with all expected keys and placeholder values
# Fallback: return a dict with all required keys and placeholder values
```

**Impact:** Low (error handling)
- Fallback for serialization errors
- Prevents crashes but data may be incomplete

**Recommendation:**
- Improve error handling
- Log serialization failures
- Consider validation before serialization

**File:** `core/food_apis/update_manager.py:872, 895, 902`

---

## 📋 Complete List

### Stub Modules

1. **`core/bmi/engine.py`** — Marked as stub (but appears functional)
2. **`core/log_retention.py`** — Log cleanup not implemented
3. **`core/catalog/sources/*`** — All catalog sources are stubs (by design)
4. **`core/exports_simple.py`** — PDF placeholder when reportlab unavailable
5. **`core/food_apis/update_manager.py`** — Fallback serialization placeholders

### Incomplete Features

1. **Log cleanup** — Returns 0, doesn't delete files
2. **PDF export** — Placeholder when reportlab unavailable

---

## 🎯 Recommendations

### P0 (Verify Status)

1. **Verify `core/bmi/engine.py` status**
   - Check if PR-455 is complete
   - Remove "stub" comment if implementation is done
   - Or document what's missing

### P1 (Implement)

2. **Implement log cleanup** (`core/log_retention.py`)
   - File deletion logic
   - Dry-run mode
   - Safeguards

### P2 (Document/Enhance)

3. **Document catalog stub strategy**
   - When will real integrations be added?
   - Keep stubs for testing

4. **Improve PDF export fallback**
   - Better error messages
   - Feature flag for PDF export

5. **Improve serialization fallback**
   - Better error logging
   - Validation before serialization

---

**Last updated:** 2026-01-15
