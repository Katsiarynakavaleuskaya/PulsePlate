# Backend TODO/FIXME Audit

**Date:** 2026-01-15
**Scope:** All TODO, FIXME, XXX, HACK comments in `core/` and `app/`
**Purpose:** Track incomplete implementations and technical debt

---

## 📊 Summary

**Total TODOs:** 13 (core) + 15 (app) = 28
**Total FIXMEs:** 0 explicit
**Total HACKs:** 0 explicit

---

## 🔴 Critical TODOs (P0 — Blocking)

### None

All current TODOs are P1 or P2 (enhancements, not blockers).

---

## ⚠️ High Priority TODOs (P1)

### 1. Log Retention Implementation (core/log_retention.py:100)

**Status:** Stub implementation

**Code:**
```python
def cleanup_expired_logs(self, data_class: Optional[DataClass] = None) -> int:
    # TODO: Implement actual deletion logic:
    # - Iterate over files in the configured log directory
    # - For each file, determine its data_class (if applicable) and age
    # - Compare file age to retention_periods (and optional data_class filter)
    # - Safely delete files that exceed their retention window
    # - Support safety features (e.g., dry‑run mode, backups, safeguards)
    # - Update and return the number of deleted files
    return 0  # Stub: no files deleted
```

**Impact:** Medium
- Log cleanup not implemented
- May accumulate log files over time
- Currently returns 0 (safe default)

**Recommendation:**
- Implement file deletion logic
- Add dry-run mode for safety
- Add safeguards (backup, confirmation)

**File:** `core/log_retention.py:100-115`

---

### 2. Database Lookup for API Tiers (app/middleware/api_tiers.py:146, 284)

**Status:** Placeholder comments

**Code:**
```python
# TODO: Implement database lookup for production when SUBSCRIPTION_DB_ENABLED=true
# TODO: Implement database lookup
```

**Impact:** Medium
- Currently uses in-memory/static tier mapping
- Production may need database-backed tier lookup

**Recommendation:**
- Implement database lookup when `SUBSCRIPTION_DB_ENABLED=true`
- Keep in-memory fallback for development

**File:** `app/middleware/api_tiers.py:146, 284`

---

### 3. i18n Support for Error Messages (Multiple files)

**Status:** Missing localization

**Files:**
- `core/data_sanitizer.py:371`
- `app/routers/users.py:134`
- `app/routers/premium_week.py:97`
- `app/routers/pro.py:152`

**Code pattern:**
```python
# TODO: Localize error messages using t(lang, "translation_key") for i18n support
```

**Impact:** Low (UX enhancement)
- Error messages are English-only
- Should support RU/EN/ES

**Recommendation:**
- Add i18n keys for error messages
- Use `t(lang, "error_key")` pattern

---

## 📝 Medium Priority TODOs (P2)

### 4. Deduplicate `estimate_targets_minimal` (app/routers/premium_week.py:127, pro.py:182)

**Status:** Code duplication

**Code:**
```python
# TODO(#286): Deduplicate estimate_targets_minimal by moving it into app/services/nutrition_targets.py
```

**Impact:** Low (code quality)
- Function duplicated in multiple routers
- Should be moved to shared service

**Recommendation:**
- Move to `app/services/nutrition_targets.py`
- Update all call sites

**Files:**
- `app/routers/premium_week.py:127`
- `app/routers/pro.py:182`

---

### 5. Integrate Telemetry/Metrics (core/business_bayesian_analyzer.py:146, 1068)

**Status:** Placeholder metrics

**Code:**
```python
# TODO: Replace with actual metrics from telemetry/analytics once available
# TODO: Integrate actual telemetry/metrics once available (e.g., error frequency, fix time)
```

**Impact:** Low (observability)
- Currently uses placeholder/stub metrics
- Should integrate real telemetry

**Recommendation:**
- Integrate telemetry service
- Replace placeholder metrics

**File:** `core/business_bayesian_analyzer.py:146, 1068`

---

### 6. System Philosophy Integration (core/integrated_bayesian_analyzer.py:87)

**Status:** Missing integration

**Code:**
```python
# TODO: Integrate system_philosophy into _analyze_philosophy_compliance or recommendations
```

**Impact:** Low (feature enhancement)
- System philosophy not fully integrated
- May affect recommendation quality

**Recommendation:**
- Integrate system_philosophy into analysis
- Update recommendations accordingly

**File:** `core/integrated_bayesian_analyzer.py:87`

---

### 7. File Path Logging/Telemetry (core/integrated_bayesian_analyzer.py:128)

**Status:** Missing telemetry

**Code:**
```python
# TODO: Use file_path for logging/telemetry in future implementation
```

**Impact:** Low (observability)
- File path not used for logging/telemetry
- May help with debugging

**Recommendation:**
- Add file_path to telemetry events
- Use for logging context

**File:** `core/integrated_bayesian_analyzer.py:128`

---

### 8. Make BMI Function Public API (app/routers/bmi.py:54)

**Status:** Internal function

**Code:**
```python
# TODO(PR-456): Consider making this public API (remove underscore).
```

**Impact:** Low (API design)
- Function is currently private (underscore prefix)
- May need to be public API

**Recommendation:**
- Review if function should be public
- Remove underscore if needed

**File:** `app/routers/bmi.py:54`

---

### 9. Integrate Meal Logging (app/routers/pro.py:529, 537)

**Status:** Placeholder values

**Code:**
```python
current_value=0.0,  # TODO: Integrate with meal logging
total_progress=0.0,  # TODO: Calculate from actual meal logging
```

**Impact:** Medium (feature completeness)
- Progress tracking uses placeholder values
- Should integrate with meal logging system

**Recommendation:**
- Integrate with meal logging service
- Calculate real progress values

**File:** `app/routers/pro.py:529, 537`

---

### 10. Fetch Plan Data from Database (app/routers/shopping_list_pro.py:66)

**Status:** Missing database integration

**Code:**
```python
# TODO(future): Fetch plan_data from database using weekly_plan_id
```

**Impact:** Low (feature enhancement)
- Currently uses in-memory/request data
- Should fetch from database

**Recommendation:**
- Implement database lookup for plan_data
- Use weekly_plan_id as key

**File:** `app/routers/shopping_list_pro.py:66`

---

### 11. Rate Limiting for Bayes Adherence (app/schemas/bayes_adherence.py:29)

**Status:** Security enhancement

**Code:**
```python
# TODO(SEC-001): Mitigation plan - add per-API-key rate limiting, stricter input
```

**Impact:** Medium (security)
- No rate limiting currently
- May be vulnerable to abuse

**Recommendation:**
- Implement per-API-key rate limiting
- Add stricter input validation

**File:** `app/schemas/bayes_adherence.py:29`

---

## 📋 Complete TODO List

### Core TODOs

1. `core/log_retention.py:100` — Log cleanup implementation
2. `core/data_sanitizer.py:371` — i18n error messages
3. `core/integrated_bayesian_analyzer.py:87` — System philosophy integration
4. `core/integrated_bayesian_analyzer.py:128` — File path telemetry
5. `core/business_bayesian_analyzer.py:146` — Telemetry metrics
6. `core/business_bayesian_analyzer.py:1068` — Telemetry integration
7. `core/bmi/engine.py:147` — Age bands documentation (not a TODO, just a comment)

### App TODOs

1. `app/middleware/api_tiers.py:146` — Database lookup for tiers
2. `app/middleware/api_tiers.py:284` — Database lookup
3. `app/routers/users.py:134` — i18n error messages
4. `app/routers/premium_week.py:97` — i18n error messages
5. `app/routers/premium_week.py:127` — Deduplicate estimate_targets_minimal
6. `app/routers/pro.py:152` — i18n error messages
7. `app/routers/pro.py:182` — Deduplicate estimate_targets_minimal
8. `app/routers/pro.py:529` — Integrate meal logging
9. `app/routers/pro.py:537` — Calculate progress from meal logging
10. `app/routers/bmi.py:54` — Make function public API
11. `app/routers/shopping_list_pro.py:66` — Fetch plan_data from database
12. `app/schemas/bayes_adherence.py:29` — Rate limiting

---

## 🎯 Priority Recommendations

### P1 (High Priority)

1. **Log cleanup implementation** — Prevents log file accumulation
2. **Database lookup for API tiers** — Needed for production
3. **Meal logging integration** — Feature completeness

### P2 (Medium Priority)

4. **i18n error messages** — UX enhancement
5. **Deduplicate estimate_targets_minimal** — Code quality
6. **Rate limiting** — Security enhancement

### P3 (Low Priority)

7. **Telemetry integration** — Observability
8. **System philosophy integration** — Feature enhancement
9. **Public API design** — API evolution

---

**Last updated:** 2026-01-15
