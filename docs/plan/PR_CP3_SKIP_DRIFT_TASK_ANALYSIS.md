# Task Analysis: P1 CP3 Skip-Drift Cleanup

---

## Task Analysis

**Task:** Execute CP3 skip-drift cleanup with deterministic test contracts.

**Domain(s):** Multiple (Architecture | Backend | QA | Docs)

**Complexity:** Moderate

**Priority:** P1

- **Priority track (P0-A / P0-B / P1):** P1

**Expected Outcome:**

- Reduce skip-heavy drift in CP3 target test files.
- Keep skip protocol canonical: `feature_disabled:<key>`.
- Document intentional skips as product decisions only.
- Preserve merge-safe scope and keep gates green.

**Invariants Affected:**

- [x] Layer Separation
- [x] Contract-First
- [x] Deterministic tests (no ad-hoc skip reasons)
- [ ] One BMI Engine
- [ ] Thin HTTP Adapter Policy

**Risks:**

1. Scope creep into runtime behavior outside test contract cleanup.
2. Ad-hoc skip strings reintroduced by local fixes.
3. False green from skip refactors without contract assertions.
4. Diff-coverage drop on touched tests/helpers.

**Proposed Approach:**

1. Lock CP3 scope to listed test files and skip protocol.
2. Build explicit mapping from skip bucket to canonical feature key.
3. Add deterministic assertions for skip-reason consistency.
4. Run targeted tests + `make verify`; capture evidence in audit doc.

**Agent Assignment:**

- **Primary:** `backend-engineer` - implement narrow CP3 test cleanup.
- **Secondary:** `bug-hunter`, `architecture-specialist`, `dev-operator`
  - validate risk boundaries and deterministic gate checks.
- **Dependencies:** Existing product/runtime behavior remains unchanged.

**Constraints:**

- Do not expand scope into API/runtime features.
- No ad-hoc skip reasons.
- No changes in other worktrees/branches.
- Keep docs evidence-ready with explicit `file:line` anchors.

---

**Analysis by:** agent-coordinator (synthesized)
**Date:** 2026-02-18
