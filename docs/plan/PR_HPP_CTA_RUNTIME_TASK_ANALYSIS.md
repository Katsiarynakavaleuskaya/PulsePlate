# Task Analysis: P1 Home/Plate/Progress CTA Runtime Remediation

---

## Task Analysis

**Task:** Execute runtime remediation for Home/Plate/Progress CTA flows
using the visual matrix as source of truth.

**Domain(s):** Multiple (Frontend | iOS | QA | Design Docs)

**Complexity:** Moderate

**Priority:** P1

- **Priority track (P0-A / P0-B / P1):** P1

**Expected Outcome:**

- Remove placeholder CTA destinations on iOS Home/Plate/Progress paths.
- Add deterministic CTA-level tests for critical web+iOS flows.
- Define production-ready web paywall CTA wiring with explicit success/failure handling.
- Keep matrix status synchronized with runtime reality.

**Invariants Affected:**

- [ ] Layer Separation
- [x] Contract-First
- [x] Deterministic tests
- [x] Thin HTTP Adapter Policy
- [ ] One BMI Engine

**Risks:**

1. CTA remediation expands into broad navigation refactor (scope creep).
2. iOS placeholder replacement introduces behavior divergence from web.
3. Paywall CTA wiring is shipped without deterministic error handling tests.
4. Matrix doc drifts from actual runtime implementation.

**Proposed Approach:**

1. Lock exact CTA set from matrix and map to canonical destinations.
2. Implement runtime fixes in smallest possible slices
   (iOS destination parity, then web paywall wiring).
3. Add deterministic CTA tests and keep transport logic in thin adapters.
4. Update matrix statuses only after runtime evidence is green.

**Agent Assignment:**

- **Primary:** `frontend-engineer`, `creative-designer`
- **Secondary:** `backend-engineer`, `bug-hunter`, `dev-operator`
- **Dependencies:** Existing matrix doc and platform AGENTS invariants.

**Constraints:**

- No business logic duplication on clients.
- No direct fetch/URLSession drift outside approved adapters.
- Keep scope to Home/Plate/Progress CTA paths.
- Record explicit evidence anchors for each remediated CTA.

---

**Analysis by:** agent-coordinator (synthesized)
**Date:** 2026-02-18
