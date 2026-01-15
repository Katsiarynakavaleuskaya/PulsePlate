# Backend Complete Audit Index

**Date:** 2026-01-15
**Purpose:** Index of all backend audit documents

---

## 📚 Audit Documents

### 1. xfailed Tests Audit
**File:** `BACKEND_XFAILED_TESTS_AUDIT.md`

**Contents:**
- 2 xfailed tests with root causes
- Skipped tests (conditional)
- Action items for fixes

**Key Findings:**
- `test_no_calculate_all_bmr` — Module reload issue
- `test_bmi_visualization_endpoint_with_api_key` — Test isolation issue

---

### 2. TODO/FIXME Audit
**File:** `BACKEND_TODO_FIXME_AUDIT.md`

**Contents:**
- 28 TODOs across core/ and app/
- Prioritized by impact (P0/P1/P2)
- Implementation recommendations

**Key Findings:**
- Log cleanup not implemented (stub)
- Database lookup for API tiers (placeholder)
- i18n error messages (13 TODOs)
- Function duplication (estimate_targets_minimal)

---

### 3. Stub Modules Audit
**File:** `BACKEND_STUB_MODULES_AUDIT.md`

**Contents:**
- 5 stub modules
- 2 incomplete features
- Status and recommendations

**Key Findings:**
- `core/bmi/engine.py` — Marked as stub but appears functional
- `core/log_retention.py` — Log cleanup stub
- `core/catalog/` — Stub sources (by design)

---

### 4. Code Duplication Audit
**File:** `BACKEND_DUPLICATION_AUDIT.md`

**Contents:**
- Critical duplications (P0)
- Medium priority duplications (P1)
- Verification commands

**Key Findings:**
- BMI calculation — Legacy vs canonical (critical)
- BMI extras — 3 duplicate modules (critical)
- estimate_targets_minimal — Duplicated in routers (P1)

---

### 5. Business Logic Audit
**File:** `BACKEND_BUSINESS_LOGIC_AUDIT.md`

**Contents:**
- BMI formula verification
- Threshold verification
- Business logic issues

**Key Findings:**
- ✅ All formulas correct
- ✅ All thresholds correct (with documented variations)
- ⚠️ Legacy dependency in `core/bmi/risk.py`

---

### 6. External APIs Audit
**File:** `BACKEND_EXTERNAL_APIS_AUDIT.md`

**Contents:**
- Food database APIs (USDA, OpenFoodFacts)
- LLM providers (Ollama, Grok, Pico)
- Product base (catalog stubs)
- Error handling patterns

**Key Findings:**
- ✅ All external APIs properly implemented
- ✅ Error handling and retry logic in place
- ⚠️ Catalog system stubbed (by design)

---

### 7. Audit Summary
**File:** `BACKEND_AUDIT_SUMMARY.md`

**Contents:**
- Executive summary
- Overall status (75%)
- Priority action plan
- Complete findings

---

## 🎯 Quick Reference

### Critical Issues (P0)

1. **Legacy BMI dependency** — `core/bmi/risk.py` imports from `bmi_core.py`
2. **BMI extras duplication** — 3 modules with identical functions

### High Priority (P1)

3. **xfailed tests** — 2 tests need dependency override fixes
4. **Log cleanup** — Not implemented (stub)
5. **Database lookup** — API tiers need DB integration
6. **Function duplication** — `estimate_targets_minimal` in routers

### Medium Priority (P2)

7. **i18n error messages** — 13 TODOs
8. **BMI engine status** — Verify if PR-455 complete
9. **Telemetry integration** — 2 TODOs

---

## 📊 Overall Metrics

| Category | Status | Score |
|----------|--------|-------|
| **Business Logic** | ✅ Excellent | 95% |
| **External APIs** | ✅ Good | 90% |
| **Code Quality** | ⚠️ Needs work | 70% |
| **Test Coverage** | ✅ Good | 85% |
| **Technical Debt** | ⚠️ Moderate | 60% |

**Overall: 75%**

---

## 🔗 Related Documents

- `AGENTS.md` — Project rules and policies
- `RUNBOOK_AGENT.md` — CI/debug procedures
- `docs/ENGINEERING_LESSONS.md` — Project-level lessons

---

**Last updated:** 2026-01-15
