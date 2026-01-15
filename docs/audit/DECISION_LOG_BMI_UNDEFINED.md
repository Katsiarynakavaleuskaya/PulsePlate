# Decision Log: BMI Undefined Root Cause Analysis

**Date:** 2026-01-15
**Context:** Root cause analysis for non-deterministic BMI results
**Method:** Logical analysis based on backend audit findings

---

## 🎯 Problem Context

**Symptom:** BMI and related fields sometimes become `undefined / null / inconsistent`.

**Characteristics:**
- Non-deterministic (sometimes works, sometimes doesn't)
- Not a crash or validation error
- Appears in API responses (not just UI)

---

## 📋 Decision Log

### Decision 1: Root Cause Classification

**Question:** Is this an implementation bug or architectural defect?

**Decision:** **Architectural defect**

**Rationale:**
- Multiple calculation paths exist (legacy + canonical)
- Result assembly depends on import order / code path
- Non-determinism indicates architectural issue, not single bug

**Alternatives Considered:**
- Implementation bug in specific function → Rejected (symptom is non-deterministic)
- Frontend parsing issue → Rejected (would be consistent, not non-deterministic)

**Impact:** Fix requires architectural remediation, not just code changes.

**Confidence:** High

---

### Decision 2: Primary Source Identification

**Question:** What is the strongest candidate for primary source of non-determinism?

**Decision:** **Legacy dependency in `core/bmi/risk.py`**

**Rationale:**
- Direct evidence: `risk.py` imports from `bmi_core.py` (legacy) instead of `core/bmi/engine` (canonical)
- Creates path divergence: BMI via canonical, WHtR/risk via legacy
- Explains non-deterministic behavior (import order / environment dependent)

**Alternatives Considered:**
- Duplicate extras modules → Rejected (contributing factor, not primary)
- Frontend parsing → Rejected (downstream, not source)
- Formula error → Rejected (audit confirms formulas are correct)

**Impact:** Fixing this will eliminate primary source of non-determinism.

**Confidence:** High (direct evidence from audit)

---

### Decision 3: Contributing Factors

**Question:** What other factors contribute to the problem?

**Decision:** **Duplicate extras modules (×3) and metadata confusion**

**Rationale:**
- Three identical modules create ambiguity in code paths
- Engine marked as "stub" encourages bypassing canonical path
- Both amplify non-determinism created by legacy dependency

**Alternatives Considered:**
- Test infrastructure → Rejected (doesn't affect runtime)
- External APIs → Rejected (BMI has zero external dependencies)

**Impact:** These must be fixed to fully eliminate non-determinism.

**Confidence:** Medium (indirect evidence)

---

### Decision 4: Frontend Status

**Question:** Is frontend the primary source or secondary manifestation?

**Decision:** **Secondary manifestation**

**Rationale:**
- Symptom is non-deterministic (indicates upstream issue)
- Frontend would cause consistent errors (422, NaN), not non-deterministic results
- Frontend may have issues (locale, units), but they are downstream

**Alternatives Considered:**
- Frontend is primary source → Rejected (logical exclusion)
- Frontend has no issues → Rejected (may have locale/unit issues, but not primary)

**Impact:** Frontend fixes are valid only after backend is deterministic.

**Confidence:** High (logical exclusion)

---

### Decision 5: Corrective Action Order

**Question:** What is the correct order of corrective actions?

**Decision:** **Backend P0 remediation → Backend re-validation → Frontend audit**

**Rationale:**
- Backend must be deterministic before frontend can be audited
- Fixing frontend before backend = treating symptoms, not cause
- Single source of truth principle requires backend first

**Alternatives Considered:**
- Fix frontend first → Rejected (invalid diagnosis until backend is deterministic)
- Fix in parallel → Rejected (frontend diagnosis depends on deterministic backend)

**Impact:** Backend P0 remediation is blocking for frontend work.

**Confidence:** High (architectural principle)

---

### Decision 6: What to Exclude

**Question:** What can we definitively exclude as source?

**Decisions:**

1. **Formula errors** → Excluded
   - Evidence: `BACKEND_BUSINESS_LOGIC_AUDIT.md` confirms all formulas correct
   - Confidence: High

2. **External API issues** → Excluded
   - Evidence: BMI has zero external dependencies
   - Confidence: High

3. **Test infrastructure** → Excluded
   - Evidence: xfailed tests concern isolation, not runtime
   - Confidence: High

4. **Frontend as primary** → Excluded
   - Evidence: Non-deterministic symptom indicates upstream issue
   - Confidence: High

---

## 🔗 Related Decisions

### Decision 7: Backend Health Assessment

**Question:** What is the current backend health status?

**Decision:** **~75% (Good foundation, some tech debt)**

**Rationale:**
- Business logic: 95% (formulas correct)
- External APIs: 90% (well implemented)
- Code quality: 70% (some duplication, legacy dependencies)
- Technical debt: 60% (28 TODOs, some stub modules)

**Impact:** Backend is functional but not fully deterministic.

**Confidence:** High (based on audit summary)

---

### Decision 8: PR-525 Status

**Question:** Should PR-525 (frontend BMI fix) proceed before backend remediation?

**Decision:** **No — Backend P0 remediation must come first**

**Rationale:**
- Frontend diagnosis is invalid until backend is deterministic
- PR-525 may fix symptoms but not root cause
- Correct order: Backend P0 → Frontend audit

**Impact:** PR-525 should be deferred until backend P0 is complete.

**Confidence:** High (based on root cause analysis)

---

## 📊 Decision Summary

| Decision | Status | Confidence | Impact |
|----------|--------|------------|--------|
| Root cause classification | Architectural defect | High | High |
| Primary source | Legacy dependency | High | Critical |
| Contributing factors | Duplicates + metadata | Medium | Medium |
| Frontend status | Secondary | High | Medium |
| Corrective order | Backend first | High | Critical |
| Formula errors | Excluded | High | N/A |
| External APIs | Excluded | High | N/A |
| Test infrastructure | Excluded | High | N/A |

---

## 🎯 Key Principles Established

1. **Non-determinism = upstream issue**
   - Non-deterministic symptoms indicate architectural problems, not implementation bugs

2. **Architecture before implementation**
   - Fix architectural defects before fixing implementation bugs

3. **Single source of truth**
   - Backend must be deterministic before frontend can be audited

4. **Downstream manifestations**
   - UI manifests problems but rarely causes systemic failures

---

## 📝 Next Steps

### Decision 9: Implementation Order

**Question:** Should we start with guards or remediation?

**Decision:** **Guard Policy First**

**Rationale:**
1. Root cause is proven (not hypothesis)
2. Remediation without guards = high regression risk
3. Guards turn architectural decision into enforceable rule
4. Guards will fail initially (expected) — we're setting "red fence"
5. Guards prevent regression during remediation

**Alternatives Considered:**
- Remediation first → Rejected (high risk of regression)
- Parallel work → Rejected (guards must be in place before remediation)

**Impact:** Guards must be implemented and integrated into CI before remediation begins.

**Confidence:** High (best practice for architectural fixes)

---

### Corrective Action Order (Updated)

**Phase 0: Guard Policy** (Current)
- Implement guard tests
- Integrate into CI
- Update AGENTS.md
- **Guards will fail initially** (expected — we're setting "red fence")

**Phase 1: Backend P0 Remediation** (After Phase 0)
- Remove legacy dependency
- Consolidate duplicates
- Fix metadata
- **Guards should turn green** after each step

**Phase 2: Backend Re-Validation** (After Phase 1)
- Run comprehensive tests
- Verify result consistency
- Confirm: backend = single source of truth

**Phase 3: Frontend Audit** (Only After Phase 1-2)
- Diagnose with deterministic backend
- Fix locale/units/errors
- Verify no "undefined" in UI

---

## 🎯 Key Invariant

**Architectural Invariant:**
> *"One BMI Engine must be the sole calculation path for all BMI-related computations."*

**Current Status:** ❌ **Violated**

**Point of No-Return:**
> *"Until legacy dependency is removed, any downstream fixes (frontend, API contracts) are considered unreliable. The system cannot be diagnosed or fixed reliably until the invariant is restored."*

---

**Last updated:** 2026-01-15
**Status:** Decisions documented, corrective plan defined
