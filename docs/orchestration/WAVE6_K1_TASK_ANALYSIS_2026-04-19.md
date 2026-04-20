# WAVE6 K1 Task Analysis

## Task Analysis

**Task:** Implement `PR-K1` as a bounded post-A5 runtime slice for knowledge contracts and promotion from validated RAG evidence only.

**Domain(s):** AI/ML | Architecture | Security | Multiple

**Complexity:** Complex

**Priority:** P1

- **Priority track (P0-A / P0-B / P1):** P1

**Expected Outcome:** Internal knowledge promotion contracts land without route/public schema drift, DB/storage rollout, or semantic-cache expansion.

**Invariants Affected:**
- [ ] One BMI Engine
- [x] Thin HTTP Adapter Policy
- [x] Layer Separation
- [x] Contract-First
- [x] Other: bounded post-A5 product-AI runtime rail

**Risks:**
1. Promotion drift could canonicalize raw retrieval artifacts; mitigate by fail-closed policy and evidence-envelope candidates only.
2. Scope drift could leak into route or storage lanes; mitigate by restricting edits to declared runtime seams and updating packet if one thin tracing seam is required.
3. Degraded retrieval could poison knowledge; mitigate by denying promotion on every degraded reason and sub-threshold confidence path.

**Proposed Approach:**
1. Add `core/knowledge/*` contracts/policy/promotion/store with no FastAPI imports.
2. Thread `KnowledgePolicy` through the existing runtime/orchestration seams.
3. Keep application service thin and allow only protocol-based store handoff.
4. Add narrow deterministic tests for policy, promotion, and non-persistent recursive behavior.
5. Record coordinator-first governance artifacts for the lane.

**Agent Assignment:**
- **Primary:** `agent-coordinator` - owns scope, role order, synthesis, and DoD.
- **Secondary:** `architecture-specialist` - enforces bounded seam and anti-drift review.
- **Secondary:** `data-scientist-agent` - validates promotion semantics and evidence grade.
- **Secondary:** `backend-engineer` - implements the runtime/core changes.
- **Secondary:** `security-auditor` - verifies fail-closed and scope isolation.
- **Secondary:** `qa-engineer-agent` - adds deterministic tests.
- **Secondary:** `bug-hunter` - mandatory final defect pass.
- **Dependencies:** preflight and agent consistency must pass before edits.

**Constraints:**
- No `legacy_app.py`, `app/routers/*`, OpenAPI, DB migration, or semantic-cache rollout.
- Promotion source of truth is validated RAG evidence only.
- `DEEP_REASONING` stays promotion-denied by default.

---

**Analysis by:** agent-coordinator
**Date:** 2026-04-19
